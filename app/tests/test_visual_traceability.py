import pytest
from app.services.ai_service import AIService
from unittest.mock import patch, MagicMock
import asyncio

@pytest.mark.asyncio
async def test_extrair_biomarcadores_com_visual_traceability():
    # Mock do resultado da IA
    mock_ai_response = {
        "biomarcadores": [
            {
                "nome": "GLICOSE",
                "valor_raw": "95 mg/dL",
                "unidade": "mg/dL",
                "tipo": "absoluto",
                "page": 1,
                "bounding_box": [100, 200, 150, 400]
            }
        ],
        "data_coleta": "10/05/2026",
        "laboratorio": "Lab Test"
    }

    ai_service = AIService()
    
    with patch.object(ai_service, '_extrair_via_google_async', return_value=mock_ai_response):
        # O arquivo não importa por causa do mock
        resultados, data, lab = await ai_service.extrair_biomarcadores("dummy.pdf")
        
        assert len(resultados) == 1
        res = resultados[0]
        assert res["nome_marcador_normalizado"] == "GLICOSE"
        assert res["page_number"] == 1
        assert res["bounding_box"] == [100, 200, 150, 400]
        assert data == "10/05/2026"
        assert lab == "Lab Test"

