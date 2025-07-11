# app/infrastructure/database.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.base import Base
from app.infrastructure.test_data import init_test_data


class Database:
    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.engine = engine
        self.SessionLocal = session_factory or async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def connect(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def init_test_data(self, security_service) -> None:
        """Initialize test users for development/testing purposes."""
        await init_test_data(self.session, security_service)

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
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> Database:
    return Database(engine, session_factory)
