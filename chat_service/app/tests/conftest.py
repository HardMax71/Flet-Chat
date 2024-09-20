# app/tests/conftest.py
import random
import string

import pytest
from app.config import AppConfig
from app.domain import models
from app.infrastructure.database import Base, Database
from app.infrastructure.security import SecurityService
from app.main import Application
from fakeredis import aioredis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def app_config(tmp_path):
    return AppConfig(
        DATABASE_URL=f"sqlite+aiosqlite:///:memory:",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        SECRET_KEY="test_secret_key",
        REFRESH_SECRET_KEY="test_refresh_secret_key",
        PROJECT_NAME="Test Chat API",
        PROJECT_VERSION="1.0.0",
        PROJECT_DESCRIPTION="Test Chat API",
        API_V1_STR="/api/v1",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )


@pytest.fixture(scope="function")
async def mock_redis():
    """Provide a fake Redis client for testing."""
    redis = aioredis.FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest.fixture(scope="function")
async def engine(app_config):
    """Create a SQLAlchemy engine for testing."""
    engine = create_async_engine(
        app_config.DATABASE_URL,
        connect_args={"check_same_thread": False, "uri": True},  # Enable URI parsing for shared cache
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine):
    """Provide a SQLAlchemy session for testing."""
    TestingSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def override_get_db(db_session):
    """Override the get_session dependency to use the test session."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture(scope="function")
async def app(app_config, mock_redis, engine):
    """Create the FastAPI app with the test database."""
    # Initialize Database with the test engine
    database = Database(engine=engine)
    application = Application(config=app_config, database=database)
    application.redis_client.client = mock_redis

    app_instance = application.create_app()

    return app_instance


@pytest.fixture(scope="function")
async def app_with_db(app, override_get_db):
    """Override dependencies to use the test database session."""
    app.dependency_overrides[Database.get_session] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(app_with_db):
    """Provide an HTTP client with the test app."""
    async with AsyncClient(app=app_with_db, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_user(db_session, app_config):
    """Create a test user in the database."""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    security_service = SecurityService(app_config)
    user = models.User(
        username=f"testuser_{random_string}",
        email=f"testuser_{random_string}@example.com",
        hashed_password=security_service.get_password_hash("testpassword"),
        is_active=True,  # Ensure the user is active
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_user2(db_session, app_config):
    """Create a second test user in the database."""
    security_service = SecurityService(app_config)
    user = models.User(
        username=f"testuser2_{random.randint(1, 1000)}",
        email=f"testuser2_{random.randint(1, 1000)}@example.com",
        hashed_password=security_service.get_password_hash("testpassword2"),
        is_active=True,  # Ensure the user is active
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def auth_header(client, test_user):
    """Provide an authorization header for authenticated requests."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}  # Use JSON payload
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
