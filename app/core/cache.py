import redis.asyncio as redis
from app.core.config import settings

def get_redis_client():
    """Retorna um cliente Redis assíncrono configurado para uso como cache."""
    return redis.from_url(f"redis://:{settings.REDIS_PASS}@redis:6379/1", decode_responses=True)
