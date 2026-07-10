from datetime import datetime, timedelta, timezone

from app.core.config import settings


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


def test_beat_schedule_uses_configured_retention_days(monkeypatch):
    monkeypatch.setattr(settings, "OCR_RETENTION_DAYS", 12)

    from app.core.celery_app import build_beat_schedule

    schedule = build_beat_schedule()

    assert schedule["cleanup-old-exams-nightly"]["kwargs"]["older_than_days"] == 12


def test_cleanup_old_exams_uses_configured_default_when_days_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.services.retention_service._get_exame_model", lambda: _FakeExameModel)
    monkeypatch.setattr(settings, "OCR_STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "OCR_LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "OCR_RETENTION_DAYS", 15)

    from app.services.retention_service import cleanup_old_exams
    from app.services.storage_service import ExamStorageService

    storage_service = ExamStorageService()
    source = tmp_path / "old.pdf"
    source.write_bytes(b"old pdf")
    metadata = storage_service.store_file(
        source_path=str(source),
        patient_id=1,
        original_filename="old.pdf",
        content_type="application/pdf",
    )

    old_exam = _FakeExam(
        id="old",
        patient_id=1,
        uploaded_by_user_id=1,
        url_documento=metadata.url_documento,
        original_filename="old.pdf",
        storage_provider=metadata.storage_provider,
        storage_bucket=metadata.storage_bucket,
        storage_object_key=metadata.storage_object_key,
        storage_content_type=metadata.storage_content_type,
        storage_size_bytes=metadata.storage_size_bytes,
        storage_checksum=metadata.storage_checksum,
        storage_status="stored",
        created_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    db = _FakeDB([old_exam])

    result = cleanup_old_exams(db, storage_service=storage_service)

    assert result["exam_candidates"] == 1
    assert result["deleted_files"] == 1
    assert old_exam.storage_status == "deleted"
