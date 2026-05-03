"""
Serviço para envio de notificações via Webhook.
"""

import httpx
import logging
import asyncio
import time
from typing import Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Serviço para disparar webhooks com retentativas automáticas."""

    async def send_notification(self, url: str, payload: Dict[str, Any], max_retries: int = 3):
        """
        Envia uma notificação POST com retentativas exponenciais.
        """
        if not url:
            return

        logger.info(f"Iniciando envio de webhook para: {url}")
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    logger.info(f"Webhook enviado com sucesso para {url} (Status: {response.status_code})")
                    return # Sucesso
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                wait_time = (2 ** attempt) # 1, 2, 4 segundos
                logger.warning(
                    f"Tentativa {attempt + 1}/{max_retries} falhou para {url}: {e}. "
                    f"Retentando em {wait_time}s..."
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Erro fatal não-transiente no webhook: {e}")
                break

        logger.error(f"Falha definitiva ao enviar webhook para {url} após {max_retries} tentativas.")

    def send_notification_sync(self, url: str, payload: Dict[str, Any], max_retries: int = 3):
        """
        Versão síncrona com retentativas para uso no Celery Worker.
        """
        if not url:
            return

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    logger.info(f"Webhook enviado com sucesso (sync) para {url} (Status: {response.status_code})")
                    return
            except Exception as e:
                wait_time = (2 ** attempt)
                logger.warning(f"Falha na tentativa {attempt + 1}/{max_retries} (sync) para {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
        
        logger.error(f"Falha definitiva (sync) no webhook para {url}.")
