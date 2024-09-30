# app/tests/conftest.py

import random
import string

import pytest
from app.api import dependencies
from app.config import AppConfig
from app.gateways.chat_gateway import ChatGateway
from app.gateways.token_gateway import TokenGateway
from app.gateways.user_gateway import UserGateway
from app.infrastructure import schemas
from app.infrastructure.database import create_database
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UnitOfWork
from app.main import Application
from fakeredis import aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="function")
def app_config(tmp_path):
    """
    Provide a test configuration with a shared in-memory SQLite database.
    """
    return AppConfig(
        DATABASE_URL="sqlite+aiosqlite:///:memory:?cache=shared",  # Enable shared cache
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
    """Create a SQLAlchemy engine for testing with shared in-memory SQLite."""
    engine = create_async_engine(
        app_config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Reuse the same connection
        echo=False
    )
    async with engine.begin() as conn:
        from app.infrastructure import models  # noqa: F401
        await conn.run_sync(models.Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine):
    """Provide a SQLAlchemy session for testing."""
    async_session_factory = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    session = async_session_factory()
    yield session
    await session.close()


@pytest.fixture(autouse=True)
def increase_token_expiration(app_config):
    original_expire_minutes = app_config.ACCESS_TOKEN_EXPIRE_MINUTES
    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = 5  # Set to 5 minutes for testing
    yield
    app_config.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire_minutes


@pytest.fixture(scope="function")
async def uow():
    """Provide a UnitOfWork instance for testing."""
    return UnitOfWork()


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override the get_session dependency to use the test session."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture(scope="function")
async def app(app_config, mock_redis, engine):
    """Create the FastAPI app with the test database."""
    database = create_database(engine)
    application = Application(config=app_config)
    application.database = database
    application.redis_client.client = mock_redis

    app_instance = application.create_app()

    return app_instance


@pytest.fixture(scope="function")
async def app_with_db(app, override_get_db):
    """Override dependencies to use the test database session."""
    app.dependency_overrides[dependencies.get_session] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(app_with_db):
    """Provide an HTTP client with the test app."""
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_user(db_session, app_config, uow):
    """Create a test user in the database."""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    security_service = SecurityService(app_config)
    user_create = schemas.UserCreate(
        username=f"testuser_{random_string}",
        email=f"testuser_{random_string}@example.com",
        password="testpassword"
    )
    user_gateway = UserGateway(db_session, uow)
    user = await user_gateway.create_user(user_create, security_service)
    await uow.commit()
    return user


@pytest.fixture(scope="function")
async def test_chat(db_session, test_user, uow):
    """Create a test chat in the database."""
    chat_create = schemas.ChatCreate(
        name=f"TestChat_{random.randint(1, 1000)}",
        member_ids=[test_user.id]
    )
    chat_gateway = ChatGateway(db_session, uow)
    chat = await chat_gateway.create_chat(chat_create, test_user.id)
    await uow.commit()
    return chat


@pytest.fixture(scope="function")
async def test_user2(db_session, app_config, uow):
    """Create a second test user in the database."""
    security_service = SecurityService(app_config)
    user_create = schemas.UserCreate(
        username=f"testuser2_{random.randint(1, 1000)}",
        email=f"testuser2_{random.randint(1, 1000)}@example.com",
        password="testpassword2"
    )
    user_gateway = UserGateway(db_session, uow)
    user = await user_gateway.create_user(user_create, security_service)
    await uow.commit()
    return user


@pytest.fixture(scope="function")
async def auth_header(client, test_user, db_session, uow):
    """Provide an authorization header for authenticated requests."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword"}  # Use form data
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.json().get("access_token")
    assert access_token is not None, "Access token was not returned in the response"

    # Verify token is stored in the database
    token_gateway = TokenGateway(db_session, uow)
    token = await token_gateway.get_by_access_token(access_token)
    assert token is not None, "Access token was not stored in the database"

    return {"Authorization": f"Bearer {access_token}"}
