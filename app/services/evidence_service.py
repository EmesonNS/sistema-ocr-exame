"""
Serviço para geração de evidências visuais (crops) de biomarcadores extraídos.
"""

import os
import io
import logging
from typing import Optional, Tuple
from pdf2image import convert_from_path
from app.models.exame import ResultadoBiomarcador, Exame
from app.core.cache import get_redis_client
from app.services.storage_service import ExamStorageService

logger = logging.getLogger(__name__)

class EvidenceService:
    """Gerencia a extração e o cache de recortes visuais do documento original."""

    def __init__(self) -> None:
        self.storage_service = ExamStorageService()

    async def get_visual_evidence(self, exame: Exame, resultado: ResultadoBiomarcador) -> Optional[bytes]:
        """
        Gera um recorte (crop) da página do exame onde o biomarcador foi encontrado.
        
        Args:
            exame: Objeto do exame
            resultado: Resultado do biomarcador com bounding_box e page_number
            
        Returns:
            Bytes da imagem (PNG) ou None se falhar
        """
        if not resultado.bounding_box or not resultado.page_number:
            logger.warning(f"Resultado {resultado.id} não possui metadados de rastreabilidade.")
            return None

        # 1. Tentar Cache no Redis primeiro
        cache_key = f"evidence_crop:{resultado.id}"
        redis = get_redis_client()
        cached_img = await redis.get(cache_key)
        if cached_img:
            logger.info(f"Evidência visual para {resultado.id} carregada do cache.")
            return cached_img

        # 2. Gerar Crop
        try:
            with self.storage_service.materialize_to_temp_path(exame) as file_path:
                if not os.path.exists(file_path):
                    logger.error(f"Arquivo do exame não encontrado: {file_path}")
                    return None

                images = convert_from_path(
                    file_path,
                    dpi=200,
                    first_page=resultado.page_number,
                    last_page=resultado.page_number
                )
                
                if not images:
                    return None
                
                full_page = images[0]
                width, height = full_page.size

                # Bounding box no banco: [ymin, xmin, ymax, xmax] escala 0-1000
                ymin, xmin, ymax, xmax = resultado.bounding_box
                
                # Adicionar margem de contexto (15%)
                pad_h = (ymax - ymin) * 0.15
                pad_w = (xmax - xmin) * 0.10
                
                left = max(0, (xmin - pad_w) * width / 1000)
                top = max(0, (ymin - pad_h) * height / 1000)
                right = min(width, (xmax + pad_w) * width / 1000)
                bottom = min(height, (ymax + pad_h) * height / 1000)

                crop = full_page.crop((left, top, right, bottom))
            
            # Converter para bytes (PNG)
            img_byte_arr = io.BytesIO()
            crop.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # 3. Salvar no Cache (expira em 1 hora)
            await redis.set(cache_key, img_bytes, ex=3600)
            
            return img_bytes

        except Exception as e:
            logger.error(f"Erro ao gerar evidência visual para {resultado.id}: {e}")
            return None
