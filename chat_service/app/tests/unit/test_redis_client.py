# app/tests/unit/test_redis_client.py

import logging
from unittest.mock import AsyncMock, patch

import pytest
import redis
from app.infrastructure.redis_client import RedisClient


@pytest.fixture
def test_logger():
    logger = logging.getLogger('test_redis')
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def redis_client(test_logger):
    return RedisClient(host="localhost", port=6379, logger=test_logger)


@pytest.mark.asyncio
async def test_redis_connect(redis_client, caplog):
    caplog.set_level(logging.INFO)
    with patch('redis.asyncio.Redis', return_value=AsyncMock()) as mock_redis:
        mock_redis.return_value.ping.return_value = True
        await redis_client.connect()
        assert redis_client.client is not None
        assert f"Successfully connected to Redis at {redis_client.host}:{redis_client.port}" in caplog.text


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


@pytest.mark.asyncio
async def test_redis_publish(redis_client, caplog):
    caplog.set_level(logging.DEBUG)
    redis_client.client = AsyncMock()
    await redis_client.publish("test_channel", "test_message")
    redis_client.client.publish.assert_called_once_with("test_channel", "test_message")
    assert "Published message to channel test_channel" in caplog.text
