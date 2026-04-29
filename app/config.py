import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://santiago:password123@localhost:5432/petroquery_db")
    db_echo: bool = os.getenv("DB_ECHO", "true").lower() == "true"
    huggingface_token: str = os.getenv("HUGGINGFACE_TOKEN", "")
    opencode_api_key: str = os.getenv("OPENCODE_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()