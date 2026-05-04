import pytest
from app.services.evidence_service import EvidenceService
from app.models.exame import ResultadoBiomarcador, Exame
from unittest.mock import patch, MagicMock, AsyncMock
import io

@pytest.mark.asyncio
async def test_evidence_service_crop():
    service = EvidenceService()
    
    # Mock do Resultado com metadados
    resultado = ResultadoBiomarcador(
        id="f1e2d3c4-b5a6-7890-fedc-ba0987654321",
        page_number=1,
        bounding_box=[100, 100, 200, 200]
    )
    
    exame = Exame(url_documento="dummy.pdf")
    
    # Mock do pdf2image e PIL
    with patch('app.services.evidence_service.os.path.exists', return_value=True),          patch('app.services.evidence_service.convert_from_path') as mock_convert,          patch('app.services.evidence_service.get_redis_client') as mock_redis:
        
        # Mock Redis para não pegar do cache
        mock_redis.return_value.get = AsyncMock(return_value=None)
        mock_redis.return_value.set = AsyncMock()
        
        # Mock Imagem
        mock_img = MagicMock()
        mock_img.size = (1000, 1000)
        mock_convert.return_value = [mock_img]
        
        # Mock do crop
        mock_crop = MagicMock()
        mock_img.crop.return_value = mock_crop
        
        result = await service.get_visual_evidence(exame, resultado)
        
        assert result is not None
        mock_img.crop.assert_called_once()
        # Verifica se o cache foi setado
        assert mock_redis.return_value.set.called

