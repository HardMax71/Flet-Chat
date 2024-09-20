# app/infrastructure/redis_config.py
import redis.asyncio as redis

class RedisClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client = None

    async def connect(self):
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=0,
            decode_responses=True,
        )
        try:
            await self.client.ping()
            print(f"Successfully connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {str(e)}")
            print(f"Redis host: {self.host}, Redis port: {self.port}")
            raise e

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)