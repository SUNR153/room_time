import os
import redis

# единый доступ к Redis.

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(redis_url, decode_response = True)

