import redis.asyncio as aioredis
import os

from app.core.env import load_bridge_env

load_bridge_env()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis = aioredis.from_url(REDIS_URL, decode_responses=False)
