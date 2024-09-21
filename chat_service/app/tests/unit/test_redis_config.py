# app/tests/unit/test_redis_config.py
from unittest.mock import AsyncMock, patch

import pytest
from app.infrastructure.redis_config import RedisClient


@pytest.fixture
def redis_client():
    return RedisClient(host="localhost", port=6379)


@pytest.mark.asyncio
async def test_redis_connect(redis_client):
    with patch('redis.asyncio.Redis', return_value=AsyncMock()) as mock_redis:
        mock_redis.return_value.ping.return_value = True
        await redis_client.connect()
        assert redis_client.client is not None


@pytest.mark.asyncio
async def test_redis_disconnect(redis_client):
    redis_client.client = AsyncMock()
    await redis_client.disconnect()
    redis_client.client.close.assert_called_once()


@pytest.mark.asyncio
async def test_redis_publish(redis_client):
    redis_client.client = AsyncMock()
    await redis_client.publish("test_channel", "test_message")
    redis_client.client.publish.assert_called_once_with("test_channel", "test_message")
