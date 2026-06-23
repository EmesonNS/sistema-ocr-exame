import redis.asyncio as redis
from app.core.config import settings

def get_redis_client():
    """Retorna um cliente Redis assíncrono configurado para uso como cache."""
    return redis.from_url(settings.cache_redis_url, decode_responses=True)
