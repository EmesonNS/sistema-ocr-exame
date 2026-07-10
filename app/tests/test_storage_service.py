from types import SimpleNamespace

import pytest

from app.services.storage_service import ExamStorageService, FileDownload, StorageUnavailableError


class FakeS3Error(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def test_ensure_bucket_exists_creates_missing_bucket(monkeypatch):
    service = ExamStorageService()
    calls = []

    class FakeClient:
        def head_bucket(self, Bucket):
            raise FakeS3Error("404")

        def create_bucket(self, Bucket):
            calls.append(Bucket)

    service._ensure_bucket_exists(FakeClient())

    assert calls == [service.bucket]


def test_ensure_bucket_exists_raises_on_permission_error():
    service = ExamStorageService()

    class FakeClient:
        def head_bucket(self, Bucket):
            raise FakeS3Error("AccessDenied")

        def create_bucket(self, Bucket):
            raise AssertionError("create_bucket não deveria ser chamado")

    with pytest.raises(StorageUnavailableError, match="Falha ao validar bucket S3"):
        service._ensure_bucket_exists(FakeClient())


def test_ensure_bucket_exists_is_noop_when_bucket_is_present():
    service = ExamStorageService()
    calls = []

    class FakeClient:
        def head_bucket(self, Bucket):
            calls.append(("head", Bucket))

        def create_bucket(self, Bucket):
            calls.append(("create", Bucket))

    service._ensure_bucket_exists(FakeClient())

    assert calls == [("head", service.bucket)]


def test_materialize_to_temp_path_logs_when_tempfile_removal_fails(tmp_path, monkeypatch, caplog):
    service = ExamStorageService()

    source = tmp_path / "exam.pdf"
    source.write_bytes(b"%PDF-1.4 fake pdf content")

    exame = SimpleNamespace(
        storage_provider="s3",
        storage_object_key="bucket/exam.pdf",
        original_filename="exam.pdf",
    )

    def fake_remove(path):
        raise OSError("falha no remove")

    monkeypatch.setattr("os.remove", fake_remove)
    monkeypatch.setattr(
        service,
        "stream_file",
        lambda exame_obj: FileDownload(
            chunks=iter([source.read_bytes()]),
            content_type="application/pdf",
            size_bytes=source.stat().st_size,
            original_filename="exam.pdf",
        ),
    )

    with caplog.at_level("WARNING"):
        with service.materialize_to_temp_path(exame) as temp_path:
            assert temp_path.endswith(".pdf")

    assert "Falha ao remover arquivo temporario materializado" in caplog.text


def test_iter_streaming_body_logs_when_close_fails(caplog):
    service = ExamStorageService()

    class FakeBody:
        def __init__(self):
            self._reads = [b"abc", b""]

        def read(self, size):
            return self._reads.pop(0)

        def close(self):
            raise RuntimeError("close falhou")

    body = FakeBody()

    with caplog.at_level("WARNING"):
        assert b"".join(service._iter_streaming_body(body)) == b"abc"

    assert "Falha ao fechar body de streaming S3" in caplog.text
