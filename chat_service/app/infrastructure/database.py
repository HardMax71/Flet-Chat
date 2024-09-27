# app/infrastructure/database.py
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import asynccontextmanager

Base = declarative_base()

class Database:
    def __init__(self, engine: AsyncEngine, session_factory: sessionmaker = None):
        self.engine = engine
        self.SessionLocal = session_factory or sessionmaker(
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

# Factory function to create Database instance
def create_database(engine: AsyncEngine, session_factory: sessionmaker = None) -> Database:
    return Database(engine, session_factory)