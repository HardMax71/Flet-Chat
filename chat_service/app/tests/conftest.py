import asyncio
import random
import string

import pytest
from app.domain import models
from app.infrastructure.database import Base, get_session
from app.infrastructure.security import get_password_hash
from app.main import app
from fakeredis import aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.infrastructure import redis_config

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def engine():
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine):
    TestingSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    del app.dependency_overrides[get_session]


@pytest.fixture(scope="function")
async def test_user(db_session):
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    user = models.User(
        username=f"testuser_{random_string}",
        email=f"testuser_{random_string}@example.com",
        hashed_password=get_password_hash("testpassword")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_user2(db_session):
    user = models.User(
        username=f"testuser2_{random.randint(1, 1000)}",
        email=f"testuser2_{random.randint(1, 1000)}@example.com",
        hashed_password=get_password_hash("testpassword2")
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def auth_header(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
async def mock_redis():
    fake_redis = aioredis.FakeRedis()
    original_redis = redis_config.redis_client
    redis_config.redis_client = fake_redis
    yield fake_redis
    redis_config.redis_client = original_redis


@pytest.fixture(autouse=True)
def mock_redis_client(mock_redis):
    async def get_mock_redis_client():
        return mock_redis

    original_get_redis_client = redis_config.get_redis_client
    redis_config.get_redis_client = get_mock_redis_client
    yield
    redis_config.get_redis_client = original_get_redis_client