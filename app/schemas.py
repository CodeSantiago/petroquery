import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


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
        if not re.match(r"^[a-zA-Z0-9\s\-_.]+$", v):
            raise ValueError("Title must not contain special characters")
        return v

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=20)
    metadata: Optional[dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[a-zA-Z0-9\s\-_.]+$", v):
            raise ValueError("Title must not contain special characters")
        return v


class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def map_extra_data_to_metadata(cls, data: Any) -> Any:
        if hasattr(data, "extra_data"):
            return {
                "id": data.id,
                "user_id": data.user_id,
                "title": data.title,
                "content": data.content,
                "metadata": data.extra_data or {},
                "created_at": data.created_at,
            }
        return data


class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]
    chat_id: int