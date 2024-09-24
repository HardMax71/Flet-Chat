# app/infrastructure/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import asynccontextmanager

Base = declarative_base()

class Database:
    def __init__(self, database_url: str = None, engine=None):
        if engine:
            self.engine = engine
        elif database_url:
            self.engine = create_async_engine(database_url, echo=False)
        else:
            raise ValueError("Either database_url or engine must be provided")

        self.SessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def connect(self):
        async with self.engine.begin() as conn:
            import app.domain.models  # Ensure all models are imported
            await conn.run_sync(Base.metadata.create_all)

    async def disconnect(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self):
        async with self.SessionLocal() as session:
            yield session

    async def get_session(self) -> AsyncSession:
        async with self.session() as session:
            yield session