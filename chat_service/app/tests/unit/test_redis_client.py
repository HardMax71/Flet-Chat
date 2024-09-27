# app/tests/unit/test_redis_client.py

import json
import logging
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import redis
from app.domain.events import MessageCreated, MessageUpdated, MessageDeleted, MessageStatusUpdated, UnreadCountUpdated
from app.infrastructure.event_handlers import EventHandlers
from app.infrastructure.redis_client import RedisClient


@pytest.fixture
def test_logger():
    logger = logging.getLogger('test_redis')
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def redis_client(test_logger):
    return RedisClient(host="localhost", port=6379, logger=test_logger)


@pytest.fixture
def event_handlers(redis_client):
    return EventHandlers(redis_client)


@pytest.mark.asyncio
async def test_redis_connect_and_publish(redis_client, caplog):
    caplog.set_level(logging.DEBUG)
    with patch('redis.asyncio.Redis', return_value=AsyncMock()) as mock_redis:
        mock_redis.return_value.ping.return_value = True
        await redis_client.connect()
        assert redis_client.client is not None
        assert f"Successfully connected to Redis at {redis_client.host}:{redis_client.port}" in caplog.text

        await redis_client.publish("test_channel", "test_message")
        redis_client.client.publish.assert_called_once_with("test_channel", "test_message")
        assert "Published message to channel test_channel" in caplog.text


@pytest.mark.asyncio
async def test_redis_publish_message_created(redis_client, event_handlers, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()

    event = MessageCreated(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Test message",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        user={"id": 1, "username": "testuser"},
        is_deleted=False
    )
    await event_handlers.publish_message_created(event)

    expected_data = {
        "id": 1,
        "chat_id": 1,
        "user_id": 1,
        "content": "Test message",
        "created_at": "2023-01-01 12:00:00",
        "user": {"id": 1, "username": "testuser"},
        "is_deleted": False
    }
    redis_client.client.publish.assert_called_once()
    call_args = redis_client.client.publish.call_args
    assert call_args[0][0] == "chat:1"
    assert json.loads(call_args[0][1]) == expected_data
    assert "Published message to channel chat:1" in caplog.text


@pytest.mark.asyncio
async def test_redis_publish_message_updated(redis_client, event_handlers, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()

    event = MessageUpdated(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Updated message",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 13, 0, 0),
        user={"id": 1, "username": "testuser"},
        is_deleted=False
    )
    await event_handlers.publish_message_updated(event)

    expected_data = {
        "id": 1,
        "chat_id": 1,
        "user_id": 1,
        "content": "Updated message",
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 13:00:00",
        "user": {"id": 1, "username": "testuser"},
        "is_deleted": False
    }
    redis_client.client.publish.assert_called_once()
    call_args = redis_client.client.publish.call_args
    assert call_args[0][0] == "chat:1"
    assert json.loads(call_args[0][1]) == expected_data
    assert "Published message to channel chat:1" in caplog.text


@pytest.mark.asyncio
async def test_redis_publish_message_deleted(redis_client, event_handlers, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()

    event = MessageDeleted(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="<This message has been deleted>",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 13, 0, 0),
        user={"id": 1, "username": "testuser"},
        is_deleted=True
    )
    await event_handlers.publish_message_deleted(event)

    expected_data = {
        "id": 1,
        "chat_id": 1,
        "user_id": 1,
        "content": "<This message has been deleted>",
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 13:00:00",
        "user": {"id": 1, "username": "testuser"},
        "is_deleted": True
    }
    redis_client.client.publish.assert_called_once()
    call_args = redis_client.client.publish.call_args
    assert call_args[0][0] == "chat:1"
    assert json.loads(call_args[0][1]) == expected_data
    assert "Published message to channel chat:1" in caplog.text


@pytest.mark.asyncio
async def test_redis_publish_message_status_updated(redis_client, event_handlers, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()

    event = MessageStatusUpdated(
        message_id=1,
        chat_id=1,
        user_id=1,
        is_read=True,
        read_at=datetime(2023, 1, 1, 12, 0, 0)
    )
    await event_handlers.publish_message_status_updated(event)

    expected_data = {
        "message_id": 1,
        "user_id": 1,
        "is_read": True,
        "read_at": "2023-01-01 12:00:00"
    }
    redis_client.client.publish.assert_called_once()
    call_args = redis_client.client.publish.call_args
    assert call_args[0][0] == "chat:1:status"
    assert json.loads(call_args[0][1]) == expected_data
    assert "Published message to channel chat:1:status" in caplog.text


@pytest.mark.asyncio
async def test_redis_publish_unread_count_updated(redis_client, event_handlers, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()

    event = UnreadCountUpdated(chat_id=1, user_id=1, unread_count=5)
    await event_handlers.publish_unread_count_updated(event)

    expected_data = {
        "chat_id": 1,
        "user_id": 1,
        "unread_count": 5
    }
    redis_client.client.publish.assert_called_once()
    call_args = redis_client.client.publish.call_args
    assert call_args[0][0] == "chat:1:unread_count:1"
    assert json.loads(call_args[0][1]) == expected_data
    assert "Published message to channel chat:1:unread_count:1" in caplog.text


@pytest.mark.asyncio
async def test_redis_connect_fail(redis_client, caplog):
    caplog.set_level(logging.ERROR)
    with patch('redis.asyncio.Redis', return_value=AsyncMock()) as mock_redis:
        mock_redis.return_value.ping.side_effect = redis.ConnectionError("Connection failed")
        with pytest.raises(redis.ConnectionError):
            await redis_client.connect()
        assert "Failed to connect to Redis: Connection failed" in caplog.text
        assert f"Redis host: {redis_client.host}, Redis port: {redis_client.port}" in caplog.text


@pytest.mark.asyncio
async def test_redis_disconnect(redis_client, caplog):
    caplog.set_level(logging.INFO)
    redis_client.client = AsyncMock()
    await redis_client.disconnect()
    redis_client.client.close.assert_called_once()
    assert "Disconnected from Redis" in caplog.text
