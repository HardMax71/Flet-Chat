import os
import redis.asyncio as redis

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

redis_client = None

async def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
            decode_responses=True,
        )
    try:
        await redis_client.ping()
        print(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {str(e)}")
        print(f"Redis host: {REDIS_HOST}, Redis port: {REDIS_PORT}")
        raise e
    return redis_client

