import pytest
from app.services.ai_service import AIService
from app.tasks.worker import processar_exame_task
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import uuid

@pytest.mark.asyncio
async def test_agentic_loop_full_integration():
    # 1. Setup Mock do Repo e DB
    mock_db = MagicMock()
    mock_repo = MagicMock()
    
    # Simular um resultado inicial "suspeito" (ex: valor com erro de OCR '10O' em vez de '100')
    resultado_inicial = {
        "nome_marcador_normalizado": "GLICOSE",
        "valor_raw": "10O", 
        "valor_numerico": None,
        "unidade_medida_normalizada": "mg/dL",
        "referencia_lab": "70 - 99",
        "page_number": 1,
        "bounding_box": [100, 100, 200, 200],
        "needs_review": True 
    }
    
    ai_service = AIService()
    
    # 2. Mock do Zoom (IA corrigindo para '100')
    mock_re_inspecao = {
        "valor_raw": "100",
        "confianca_reinspecao": 0.99
    }
    
    with patch('app.tasks.worker.exame_repo', mock_repo),          patch('app.tasks.worker.ai_service', ai_service),          patch('app.tasks.worker.asyncio.run') as mock_async_run:
        
        # O primeiro retorno de asyncio.run é a extração inicial
        # O segundo é o zoom do agentic loop
        mock_async_run.side_effect = [
            ([resultado_inicial], "10/05/2026", "Lab Test"), # Extração Inicial
            mock_re_inspecao, # Re-inspeção (Zoom)
            MagicMock(), # Mock para ClinicalSummary (asyncio.run interno)
            (MagicMock(), False) # Mock para update_batch_progress
        ]
        
        # Mock para evitar envio de webhooks reais
        with patch('app.tasks.worker.webhook_service'):
            # Executar a task
            processar_exame_task.run(exame_id=str(uuid.uuid4()), file_path="dummy.pdf")
            
            # 3. Verificações
            assert mock_repo.update_resultado_reinspecionado.called
            
            args, _ = mock_repo.update_resultado_reinspecionado.call_args
            resultado_final = args[2]
            
            assert resultado_final["valor_raw"] == "100"
            assert float(resultado_final["valor_numerico"]) == 100.0
            assert resultado_final["status_alerta"] == "alto" # 100 > 99

