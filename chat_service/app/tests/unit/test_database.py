# app/tests/unit/test_database.py
import pytest
from app.infrastructure.database import Database, Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    db = Database(engine=engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_connect(in_memory_db):
    await in_memory_db.connect()
    assert in_memory_db.engine is not None


@pytest.mark.asyncio
async def test_database_disconnect(in_memory_db):
    await in_memory_db.connect()
    await in_memory_db.disconnect()
    with pytest.raises(Exception):
        async with in_memory_db.engine.connect() as conn:
            await conn.execute("SELECT 1")


@pytest.mark.asyncio
async def test_database_session(in_memory_db):
    async for session in in_memory_db.get_session():
        assert isinstance(session, AsyncSession)
