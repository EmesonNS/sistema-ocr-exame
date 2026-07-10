import redis.asyncio as redis
import redis as redis_sync
from app.core.config import settings

def get_redis_client():
    """Retorna um cliente Redis assíncrono configurado para uso como cache."""
    return redis.from_url(settings.cache_redis_url, decode_responses=True)


def get_redis_client_sync():
    """Retorna um cliente Redis síncrono para caminhos de execução síncronos."""
    return redis_sync.Redis.from_url(settings.cache_redis_url, decode_responses=True)
