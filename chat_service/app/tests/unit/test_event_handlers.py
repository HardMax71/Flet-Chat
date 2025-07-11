# app/tests/unit/test_event_handlers.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.events import (
    MessageCreated,
    MessageDeleted,
    MessageStatusUpdated,
    MessageUpdated,
    UnreadCountUpdated,
    UserInfo,
)
from app.infrastructure.event_handlers import EventHandlers


@pytest.fixture
def mock_redis_client():
    return AsyncMock()


@pytest.fixture
def event_handlers(mock_redis_client):
    return EventHandlers(mock_redis_client)


@pytest.mark.asyncio
async def test_publish_message_created(event_handlers, mock_redis_client):
    event = MessageCreated(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Test",
        created_at=datetime.now(UTC),
        user=UserInfo(id=1, username="testuser"),
        is_deleted=False,
    )
    await event_handlers.publish_message_created(event)
    mock_redis_client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_message_updated(event_handlers, mock_redis_client):
    event = MessageUpdated(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Updated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        user=UserInfo(id=1, username="testuser"),
        is_deleted=False,
    )
    await event_handlers.publish_message_updated(event)
    mock_redis_client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_message_deleted(event_handlers, mock_redis_client):
    event = MessageDeleted(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Deleted message",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        user=UserInfo(id=1, username="testuser"),
        is_deleted=True,
    )
    await event_handlers.publish_message_deleted(event)
    mock_redis_client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_message_status_updated(event_handlers, mock_redis_client):
    event = MessageStatusUpdated(
        message_id=1, chat_id=1, user_id=1, is_read=True, read_at="2023-01-01T00:00:00"
    )
    await event_handlers.publish_message_status_updated(event)
    mock_redis_client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_unread_count_updated(event_handlers, mock_redis_client):
    event = UnreadCountUpdated(chat_id=1, user_id=1, unread_count=5)
    await event_handlers.publish_unread_count_updated(event)
    mock_redis_client.publish.assert_called_once()
