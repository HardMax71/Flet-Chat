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

    async def init_test_data(self, security_service) -> None:
        """Initialize test users for development/testing purposes."""
        from app.infrastructure.models import User
        from sqlalchemy import select

        async with self.session() as session:
            # Check if test users already exist
            test_user1 = await session.scalar(
                select(User).where(User.username == "test")
            )
            test_user2 = await session.scalar(
                select(User).where(User.username == "test2")
            )

            users_to_create = []

            if not test_user1:
                hashed_password1 = security_service.get_password_hash("password")
                test_user1 = User(
                    username="test",
                    email="test@test.com",
                    hashed_password=hashed_password1,
                    is_active=True,
                )
                users_to_create.append(test_user1)

            if not test_user2:
                hashed_password2 = security_service.get_password_hash("password")
                test_user2 = User(
                    username="test2",
                    email="test2@test.com",
                    hashed_password=hashed_password2,
                    is_active=True,
                )
                users_to_create.append(test_user2)

            if users_to_create:
                session.add_all(users_to_create)
                await session.commit()
                print(
                    f"Created {len(users_to_create)} test users: {[user.username for user in users_to_create]}"
                )
            else:
                print("Test users already exist, skipping creation")

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
