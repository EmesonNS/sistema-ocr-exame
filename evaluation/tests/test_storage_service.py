from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
import sys


def test_local_storage_roundtrip(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services.storage_service import ExamStorageService

    monkeypatch.setattr(settings, "OCR_STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "OCR_LOCAL_STORAGE_DIR", str(tmp_path / "storage"))

    source = tmp_path / "exam.pdf"
    source.write_bytes(b"%PDF-1.4 fake pdf content")

    service = ExamStorageService()
    metadata = service.store_file(
        source_path=str(source),
        patient_id=42,
        original_filename="exam.pdf",
        content_type="application/pdf",
    )

    stored_path = Path(metadata.storage_object_key)
    assert metadata.storage_provider == "local"
    assert stored_path.exists()
    assert metadata.url_documento.startswith("local://")

    exame = SimpleNamespace(
        storage_provider="local",
        storage_object_key=str(stored_path),
        storage_bucket=None,
        storage_content_type="application/pdf",
        storage_size_bytes=stored_path.stat().st_size,
        original_filename="exam.pdf",
        url_documento="",
    )

    download = service.stream_file(exame)
    assert b"".join(download.chunks) == b"%PDF-1.4 fake pdf content"
    assert download.content_type == "application/pdf"

    with service.materialize_to_temp_path(exame) as temp_path:
        assert Path(temp_path).exists()
        assert Path(temp_path).read_bytes() == b"%PDF-1.4 fake pdf content"

    service.delete_file(metadata)
    assert not stored_path.exists()


def test_s3_client_configuration_uses_endpoint_and_path_style(monkeypatch):
    from app.core.config import settings
    from app.services.storage_service import ExamStorageService

    monkeypatch.setattr(settings, "OCR_STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "OCR_STORAGE_ENDPOINT", "http://minio.local:9000")
    monkeypatch.setattr(settings, "OCR_STORAGE_ACCESS_KEY", "minio")
    monkeypatch.setattr(settings, "OCR_STORAGE_SECRET_KEY", "minio-secret")
    monkeypatch.setattr(settings, "OCR_STORAGE_REGION", "us-east-1")
    monkeypatch.setattr(settings, "OCR_STORAGE_FORCE_PATH_STYLE", True)

    captured = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured["kwargs"] = kwargs
        return object()

    fake_boto3 = ModuleType("boto3")
    fake_boto3.client = fake_client
    fake_botocore = ModuleType("botocore")
    fake_botocore_client = ModuleType("botocore.client")

    class FakeConfig:
        def __init__(self, s3):
            self.s3 = s3

    fake_botocore_client.Config = FakeConfig
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.client", fake_botocore_client)

    service = ExamStorageService()
    client = service._get_s3_client()

    assert client is not None
    assert captured["service_name"] == "s3"
    assert captured["kwargs"]["endpoint_url"] == "http://minio.local:9000"
    assert captured["kwargs"]["aws_access_key_id"] == "minio"
    assert captured["kwargs"]["aws_secret_access_key"] == "minio-secret"
    assert captured["kwargs"]["config"].s3["addressing_style"] == "path"
