from datetime import datetime, timedelta, timezone
from pathlib import Path


class _FakeCreatedAtField:
    def isnot(self, value):
        return ("isnot", value)

    def __lt__(self, other):
        return ("lt", other)


class _FakeExameModel:
    created_at = _FakeCreatedAtField()


class _FakeQuery:
    def __init__(self, items):
        self.items = items
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def all(self):
        results = list(self.items)
        for criterion in self.criteria:
            op, value = criterion
            if op == "lt":
                results = [item for item in results if item.created_at < value]
            elif op == "isnot":
                results = [item for item in results if item.created_at is not None]
        return results


class _FakeDB:
    def __init__(self, items):
        self.items = items

    def query(self, model):
        return _FakeQuery(self.items)

    def commit(self):
        return None

    def refresh(self, item):
        return None


class _FakeExam:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_cleanup_old_exams_removes_only_expired_files(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services.retention_service import cleanup_old_exams
    from app.services.storage_service import ExamStorageService

    monkeypatch.setattr("app.services.retention_service._get_exame_model", lambda: _FakeExameModel)
    monkeypatch.setattr(settings, "OCR_STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "OCR_LOCAL_STORAGE_DIR", str(tmp_path / "storage"))

    storage_service = ExamStorageService()
    old_source = tmp_path / "old.pdf"
    old_source.write_bytes(b"old pdf")
    old_metadata = storage_service.store_file(
        source_path=str(old_source),
        patient_id=1,
        original_filename="old.pdf",
        content_type="application/pdf",
    )

    new_source = tmp_path / "new.pdf"
    new_source.write_bytes(b"new pdf")
    new_metadata = storage_service.store_file(
        source_path=str(new_source),
        patient_id=1,
        original_filename="new.pdf",
        content_type="application/pdf",
    )

    old_exam = _FakeExam(
        id="old",
        patient_id=1,
        uploaded_by_user_id=1,
        url_documento=old_metadata.url_documento,
        original_filename="old.pdf",
        storage_provider=old_metadata.storage_provider,
        storage_bucket=old_metadata.storage_bucket,
        storage_object_key=old_metadata.storage_object_key,
        storage_content_type=old_metadata.storage_content_type,
        storage_size_bytes=old_metadata.storage_size_bytes,
        storage_checksum=old_metadata.storage_checksum,
        storage_status="stored",
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
    )
    new_exam = _FakeExam(
        id="new",
        patient_id=1,
        uploaded_by_user_id=1,
        url_documento=new_metadata.url_documento,
        original_filename="new.pdf",
        storage_provider=new_metadata.storage_provider,
        storage_bucket=new_metadata.storage_bucket,
        storage_object_key=new_metadata.storage_object_key,
        storage_content_type=new_metadata.storage_content_type,
        storage_size_bytes=new_metadata.storage_size_bytes,
        storage_checksum=new_metadata.storage_checksum,
        storage_status="stored",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db = _FakeDB([old_exam, new_exam])

    result = cleanup_old_exams(db, older_than_days=30, storage_service=storage_service)

    assert result["exam_candidates"] == 1
    assert result["deleted_files"] == 1
    assert result["errors"] == 0
    assert not Path(old_metadata.storage_object_key).exists()
    assert Path(new_metadata.storage_object_key).exists()
    assert old_exam.storage_status == "deleted"
    assert new_exam.storage_status == "stored"
