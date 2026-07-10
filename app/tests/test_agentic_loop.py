import pytest
from app.tasks.worker import processar_exame_task
from unittest.mock import patch, MagicMock, AsyncMock
import uuid

def test_agentic_loop_full_integration():
    mock_repo = MagicMock()
    mock_repo.get_exame.return_value = MagicMock(
        batch_id=None,
        webhook_url=None,
        patient_id=42,
    )

    resultado_inicial = {
        "nome_marcador_normalizado": "GLICOSE",
        "valor_raw": "10O",
        "valor_numerico": None,
        "unidade_medida_normalizada": "mg/dL",
        "referencia_lab": "70 - 99",
        "page_number": 1,
        "bounding_box": [100, 100, 200, 200],
        "needs_review": True,
        "confianca": 0.5,
    }

    mock_re_inspecao = {
        "valor_raw": "100",
        "confianca_reinspecao": 0.99,
    }

    with (
        patch("app.tasks.worker.exame_repo", mock_repo),
        patch(
            "app.tasks.worker.ai_service.extrair_biomarcadores",
            new=AsyncMock(return_value=([resultado_inicial], "10/05/2026", "Lab Test")),
        ),
        patch(
            "app.tasks.worker.ai_service.focar_extracao",
            new=AsyncMock(return_value=mock_re_inspecao),
        ),
        patch(
            "app.tasks.worker.clinical_summary_service.generate_clinical_summary",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch("app.tasks.worker.webhook_service"),
    ):
        processar_exame_task.run(exame_id=str(uuid.uuid4()), file_path="dummy.pdf")

        assert mock_repo.update_resultado_reinspecionado.called

        args, _ = mock_repo.update_resultado_reinspecionado.call_args
        resultado_final = args[2]

        assert resultado_final["valor_raw"] == "100"
        assert float(resultado_final["valor_numerico"]) == 100.0
        assert resultado_final["status_alerta"] == "alto"
