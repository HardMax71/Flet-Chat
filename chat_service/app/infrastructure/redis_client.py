# app/infrastructure/redis_client.py
import logging

import redis.asyncio as redis


class RedisClient:
    def __init__(self, host: str, port: int, logger: logging.Logger):
        self.host = host
        self.port = port
        self.client: redis.Redis | None = None
        self.logger = logger

    async def connect(self):
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=0,
            decode_responses=True,
        )
        try:
            await self.client.ping()
            self.logger.info(
                f"Successfully connected to Redis at {self.host}:{self.port}"
            )
        except redis.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {e!s}")
            self.logger.error(f"Redis host: {self.host}, Redis port: {self.port}")
            raise e

    async def disconnect(self):
        if self.client:
            await self.client.close()
            self.logger.info("Disconnected from Redis")

    async def publish(self, channel: str, message: str) -> None:
        if self.client is None:
            raise RuntimeError("Redis client not connected")
        await self.client.publish(channel, message)
        self.logger.debug(f"Published message to channel {channel}")
