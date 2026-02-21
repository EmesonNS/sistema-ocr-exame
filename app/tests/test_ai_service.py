import pytest
from unittest.mock import patch, MagicMock


class TestAIService:
    """Testes do serviço de IA"""

    @patch("google.genai.Client")
    def test_extrair_biomarcadores_gemini_success(self, mock_genai_client_class):
        """Extração via Gemini deve retornar biomarcadores normalizados"""
        from app.services.ai_service import AIService

        # Mock do cliente Gemini
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
        {
            "biomarcadores": [
                {"nome": "HEMOGLOBINA", "valor_raw": "13.5", "unidade": "g/dL", "tipo": "absoluto"},
                {"nome": "SEGMENTADOS", "valor_raw": "49,0", "unidade": "%", "tipo": "percentual"}
            ],
            "data_coleta": "15/02/2026",
            "laboratorio": "Lab Teste"
        }
        """
        mock_client.models.generate_content.return_value = mock_response
        mock_client.files.upload.return_value = "mock_file"
        mock_genai_client_class.return_value = mock_client

        service = AIService()
        resultados, data_coleta, laboratorio = service.extrair_biomarcadores(
            "fake_path.pdf"
        )

        assert len(resultados) == 2
        assert data_coleta == "15/02/2026"
        assert laboratorio == "Lab Teste"

        # Verificar normalização do SEGMENTADOS
        segmentados = next(
            r for r in resultados if "SEGMENTADO" in r["nome_marcador_normalizado"]
        )
        assert segmentados["tipo_valor"] == "percentual"
        assert segmentados["valor_numerico"] == 49.0

    def test_normalizacao_percentual_vs_absoluto(self):
        """Normalização deve distinguir percentual de absoluto"""
        from app.services.biomarker_normalization import extrair_tipo_valor, TipoValor

        # Caso SEGMENTADOS (percentual)
        tipo = extrair_tipo_valor("49,0", "%")
        assert tipo == TipoValor.PERCENTUAL

        # Caso LEUCÓCITOS (absoluto)
        tipo = extrair_tipo_valor("5500", "/mm³")
        assert tipo == TipoValor.ABSOLUTO
