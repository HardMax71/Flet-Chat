# app/tests/unit/test_unit_of_work.py
from unittest.mock import AsyncMock

import pytest
from app.config import AppConfig
from app.infrastructure.unit_of_work import UnitOfWork


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def config():
    return AppConfig(SECRET_KEY="test_secret", ALGORITHM="HS256")


@pytest.mark.asyncio
async def test_unit_of_work(mock_session, config):
    uow = UnitOfWork(mock_session, config)

    async with uow:
        assert uow.users is not None
        assert uow.chats is not None
        assert uow.messages is not None
        assert uow.tokens is not None

    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_unit_of_work_rollback(mock_session, config):
    uow = UnitOfWork(mock_session, config)

    try:
        async with uow:
            raise Exception("Test exception")
    except Exception:
        pass

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()
