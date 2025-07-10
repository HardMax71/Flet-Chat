# app/infrastructure/database.py
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ):
        self.engine = engine
        self.SessionLocal = session_factory or async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def connect(self) -> None:
        async with self.engine.begin() as conn:
            import app.infrastructure.models  # noqa: F401

            await conn.run_sync(Base.metadata.create_all)

    async def disconnect(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.SessionLocal() as session:
            yield session

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session() as session:
            yield session


# Factory function to create Database instance
def create_database(
    engine: AsyncEngine,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
) -> Database:
    return Database(engine, session_factory)
