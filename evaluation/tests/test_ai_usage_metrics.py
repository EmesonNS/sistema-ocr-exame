from types import ModuleType, SimpleNamespace
import runpy
import sys


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

    class FakePdfReader:
        def __init__(self, *args, **kwargs):
            self.pages = []

        def get_fields(self):
            return {}

    fake_pypdf.PdfReader = FakePdfReader
    fake_cache = ModuleType("app.core.cache")
    fake_cache.get_redis_client = lambda: SimpleNamespace()

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setitem(sys.modules, "pdf2image", fake_pdf2image)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "app.core.cache", fake_cache)

    return runpy.run_path("app/services/ai_service.py")


def test_ai_service_tracks_main_and_zoom_tokens(monkeypatch):
    module = _load_ai_service_module(monkeypatch)
    service = module["AIService"]()

    service.begin_usage_tracking()
    service._record_usage(SimpleNamespace(usage=SimpleNamespace(total_tokens=120)), "main")
    service._record_usage(
        SimpleNamespace(usage_metadata=SimpleNamespace(total_token_count=30)),
        "agentic_zoom",
    )
    service._record_usage(
        SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)),
        "main",
    )

    summary = service.consume_usage_summary()

    assert summary["total_tokens"] == 135
    assert summary["agentic_zoom_tokens"] == 30
    assert service.consume_usage_summary() == {"total_tokens": 0, "agentic_zoom_tokens": 0}


def test_ai_service_extracts_total_tokens_from_common_shapes(monkeypatch):
    module = _load_ai_service_module(monkeypatch)
    service = module["AIService"]()

    assert service._extract_total_tokens(SimpleNamespace(usage=SimpleNamespace(total_tokens=42))) == 42
    assert (
        service._extract_total_tokens(
            SimpleNamespace(usage_metadata=SimpleNamespace(total_token_count=17))
        )
        == 17
    )
    assert (
        service._extract_total_tokens(
            SimpleNamespace(usage=SimpleNamespace(prompt_tokens=7, completion_tokens=9))
        )
        == 16
    )
