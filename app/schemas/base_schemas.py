from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.og_schemas import OGTMetadata


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserInvite(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    role: str = Field(default="operator", pattern="^(operator|engineer|admin)$")
    project_id: int


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9\s\-_.]+$", v):
            raise ValueError("Title must not contain special characters")
        return v

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DocumentCreate(DocumentBase):
    og_metadata: OGTMetadata = Field(default_factory=OGTMetadata)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=20)
    metadata: Optional[dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        import re
        if v is not None and not re.match(r"^[a-zA-Z0-9\s\-_.]+$", v):
            raise ValueError("Title must not contain special characters")
        return v


class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    project_id: int
    chat_id: Optional[int] = None
    created_at: datetime
    cuenca: Optional[str] = None
    tipo_documento: Optional[str] = None
    tipo_equipo: Optional[str] = None
    normativa_aplicable: Optional[str] = None
    processing_status: Optional[str] = None
    processing_progress: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def map_extra_data_to_metadata(cls, data: Any) -> Any:
        if hasattr(data, "extra_data"):
            return {
                "id": data.id,
                "user_id": data.user_id,
                "project_id": data.project_id,
                "chat_id": data.chat_id,
                "title": data.title,
                "content": data.content,
                "metadata": data.extra_data or {},
                "created_at": data.created_at,
                "cuenca": data.cuenca,
                "tipo_documento": data.tipo_documento,
                "tipo_equipo": data.tipo_equipo,
                "normativa_aplicable": data.normativa_aplicable,
                "processing_status": data.processing_status,
                "processing_progress": data.processing_progress,
            }
        return data


class ChatResponse(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    title: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime
    structured_response: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def map_structured_response(cls, data: Any) -> Any:
        if hasattr(data, "structured_response"):
            return {
                "id": data.id,
                "chat_id": data.chat_id,
                "role": data.role,
                "content": data.content,
                "created_at": data.created_at,
                "structured_response": data.structured_response,
            }
        return data


# Legacy answer response (kept for backward compatibility during transition)
class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]
    chat_id: int
