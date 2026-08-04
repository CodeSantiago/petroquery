from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.rate_limit import limiter
from app.schemas import Token, UserCreate, UserResponse
from app.services.security import (
    get_password_hash,
    verify_password,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_EXPIRE_SECONDS,
)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _secret_key() -> str:
    """Return the current signing secret.

    The value is resolved at call-time rather than captured at module
    import so that tests (and runtime secret rotation tools) can swap
    the underlying settings without having to reload the module.
    """
    return get_settings().secret_key


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    # datetime.utcnow() is deprecated in Python 3.12+. Use timezone-aware
    # datetime.now(timezone.utc) so JWT validation handles expiry correctly
    # across DST/offset transitions and the call is forward-compatible.
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # The JWT spec requires the subject claim ("sub") to be a string.
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def _set_auth_cookie(response: Response, token: str) -> None:
    """Attach the access token as an HttpOnly cookie when enabled.

    The cookie is opt-in via ``AUTH_COOKIE_ENABLED`` (default: true).
    In production the Secure flag is on; in development it is off so
    the local server (plain HTTP) keeps working.
    """
    settings = get_settings()
    if not settings.auth_cookie_enabled:
        return
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Remove the access-token cookie. Idempotent and safe to call always."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    """Resolve the current user from the Authorization header OR the cookie.

    Header takes precedence (so the existing JSON/Authorization clients
    keep working), but cookie-based auth lets SPAs drop ``localStorage``
    when they want to. The cookie is HttpOnly so XSS can't read it.
    """
    settings = get_settings()
    cookie_value = request.cookies.get(settings.auth_cookie_name)
    credential = token or cookie_value
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credential:
        raise credentials_exception

    try:
        payload = jwt.decode(credential, _secret_key(), algorithms=[ALGORITHM])
        # PASO 1: Extraemos el valor (puede venir como string "2" o int 2)
        raw_user_id = payload.get("sub")

        if raw_user_id is None:
            raise credentials_exception

        # PASO 2: Lo convertimos a entero explícitamente
        try:
            user_id = int(raw_user_id)
        except (ValueError, TypeError):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # PASO 3: Ahora la búsqueda no va a fallar por tipo de dato
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Si el token es válido pero el usuario ya no existe en la DB
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{get_settings().rate_limit_register_per_minute}/minute")
async def register(
    request: Request,  # injected by slowapi
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
@limiter.limit(f"{get_settings().rate_limit_login_per_minute}/minute")
async def login(
    request: Request,  # injected by slowapi
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.id, "role": user.role})

    # Set the HttpOnly cookie alongside the JSON response. Clients that
    # still want to use the Authorization header keep working.
    _set_auth_cookie(response, access_token)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> dict:
    """Clear the access-token cookie.

    Idempotent: a logged-out client that POSTs again still gets 200.
    The JWT itself is stateless so revocation has to be enforced by
    short expiry; for stronger guarantees the project should adopt
    Redis-backed blocklist or refresh-token rotation.
    """
    _clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
