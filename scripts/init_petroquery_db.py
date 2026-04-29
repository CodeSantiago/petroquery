import asyncio
import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.database import Base
import app.models  # noqa: F401 - registers models with Base.metadata


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://santiago:password123@localhost:5432/petroquery_db"
)


async def init_petroquery_db() -> None:
    """Initialize PetroQuery database: drop existing tables, create pgvector extension, create new schema."""
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)

    async with engine.begin() as conn:
        # Create pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Drop all existing tables in correct order to avoid FK constraint issues
        print("Dropping existing tables...")
        await conn.execute(text("DROP TABLE IF EXISTS query_audits CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS project_members CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS chats CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS projects CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS companies CASCADE"))

        # Create all tables from SQLAlchemy metadata
        print("Creating PetroQuery tables...")
        await conn.run_sync(Base.metadata.create_all)

        print("✅ PetroQuery database initialized successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_petroquery_db())
