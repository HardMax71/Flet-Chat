# app/tests/unit/test_security.py
import pytest

from app.config import AppConfig
from app.infrastructure.security import SecurityService


@pytest.fixture
def security_service():
    config = AppConfig(
        SECRET_KEY="test_secret",
        ALGORITHM="HS256",
        REFRESH_SECRET_KEY="test_refresh_secret",
    )
    return SecurityService(config)


def test_password_hashing(security_service):
    password = "testpassword"
    hashed = security_service.get_password_hash(password)
    assert security_service.verify_password(password, hashed)
    assert not security_service.verify_password("wrongpassword", hashed)


def test_token_creation(security_service):
    data = {"sub": "testuser"}
    access_token, _ = security_service.create_access_token(data)
    refresh_token, _ = security_service.create_refresh_token(data)
    assert access_token
    assert refresh_token


def test_token_decoding(security_service):
    data = {"sub": "testuser"}
    access_token, _ = security_service.create_access_token(data)
    refresh_token, _ = security_service.create_refresh_token(data)

    decoded_access = security_service.decode_access_token(access_token)
    decoded_refresh = security_service.decode_refresh_token(refresh_token)

    assert decoded_access == "testuser"
    assert decoded_refresh == "testuser"
