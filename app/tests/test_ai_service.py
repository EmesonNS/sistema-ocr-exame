import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from types import ModuleType, SimpleNamespace
import runpy
import sys

try:
    from pypdf import PdfReader as RealPdfReader
except Exception:  # pragma: no cover - host fallback
    try:
        from PyPDF2 import PdfReader as RealPdfReader
    except Exception:  # pragma: no cover - defensive fallback
        RealPdfReader = None


def _load_ai_service_module(monkeypatch):
    fake_google = ModuleType("google")
    fake_genai = ModuleType("google.genai")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.files = SimpleNamespace(upload=lambda **_kwargs: "mock_file")
            self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=None))

    fake_genai.Client = FakeClient
    fake_google.genai = fake_genai

    fake_openai = ModuleType("openai")

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    fake_openai.OpenAI = FakeOpenAI
    fake_openai.AsyncOpenAI = FakeOpenAI

    fake_pdf2image = ModuleType("pdf2image")
    fake_pdf2image.convert_from_path = lambda *args, **kwargs: []

    fake_pypdf = ModuleType("pypdf")
    fake_pypdf.PdfReader = RealPdfReader

    fake_cache = ModuleType("app.core.cache")
    fake_cache.get_redis_client = lambda: SimpleNamespace()

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setitem(sys.modules, "pdf2image", fake_pdf2image)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "app.core.cache", fake_cache)

    return runpy.run_path(str(Path(__file__).resolve().parents[2] / "app/services/ai_service.py"))


class TestAIService:
    """Testes do serviço de IA"""

    @pytest.mark.asyncio
    @patch("google.genai.Client")
    async def test_extrair_biomarcadores_gemini_success(self, mock_genai_client_class):
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
        # Mock do aio (async) models do Gemini usando AsyncMock
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client.files.upload.return_value = "mock_file"
        mock_genai_client_class.return_value = mock_client

        service = AIService()
        resultados, data_coleta, laboratorio = await service.extrair_biomarcadores(
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

    @patch("google.genai.Client", side_effect=RuntimeError("gemini indisponivel"))
    def test_init_logs_gemini_failure(self, mock_genai_client_class, caplog):
        """Falha na inicialização do cliente Gemini deve ser observável no log."""
        from app.services.ai_service import AIService

        with caplog.at_level("WARNING"):
            service = AIService()

        assert service.google_client is None
        assert "Falha ao inicializar cliente Gemini" in caplog.text

    def test_normalizacao_percentual_vs_absoluto(self):
        """Normalização deve distinguir percentual de absoluto"""
        from app.services.biomarker_normalization import extrair_tipo_valor, TipoValor

        # Caso SEGMENTADOS (percentual)
        tipo = extrair_tipo_valor("49,0", "%")
        assert tipo == TipoValor.PERCENTUAL

        # Caso LEUCÓCITOS (absoluto)
        tipo = extrair_tipo_valor("5500", "/mm³")
        assert tipo == TipoValor.ABSOLUTO

    @patch("app.services.ai_service.AIService.extrair_biomarcadores", new_callable=AsyncMock)
    def test_extrair_dados_exame_sync_wrapper(self, mock_extrair_biomarcadores):
        """Wrapper síncrono legado deve funcionar fora de event loop."""
        from app.services.ai_service import AIService

        mock_extrair_biomarcadores.return_value = ([{"resultado": 1}], None, None)

        service = AIService()
        payload = service.extrair_dados_exame("fake_path.pdf")

        assert payload == {"resultados": [{"resultado": 1}]}

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.extrair_biomarcadores", new_callable=AsyncMock)
    async def test_extrair_dados_exame_rejeita_event_loop(self, mock_extrair_biomarcadores):
        """Wrapper síncrono legado deve falhar explicitamente dentro de loop async."""
        from app.services.ai_service import AIService

        mock_extrair_biomarcadores.return_value = ([{"resultado": 1}], None, None)

        service = AIService()

        with pytest.raises(RuntimeError, match="event loop"):
            service.extrair_dados_exame("fake_path.pdf")


@pytest.mark.asyncio
async def test_extrair_biomarcadores_uses_textual_fallback_on_golden_pdf(monkeypatch):
    module = _load_ai_service_module(monkeypatch)
    monkeypatch.setattr(module["settings"], "GEMINI_API_KEY", "")
    monkeypatch.setattr(module["settings"], "OPENROUTER_API_KEY", "")

    service = module["AIService"]()
    pdf_path = (
        Path(__file__).resolve().parents[2]
        / "amostras_exames/Laudo Completo 04_02_2026 (1).pdf"
    )

    resultados, data_coleta, laboratorio = await service.extrair_biomarcadores(
        str(pdf_path)
    )

    assert len(resultados) >= 15
    nomes = {resultado["nome_marcador_normalizado"] for resultado in resultados}
    assert {"CHCM", "FERRO"}.issubset(nomes)
    assert data_coleta in (None, "04/02/2026")
    assert laboratorio is None or isinstance(laboratorio, str)
