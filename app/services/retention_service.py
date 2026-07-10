import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.services.storage_service import ExamStorageService, StoredFileMetadata

logger = logging.getLogger(__name__)


def cleanup_old_exams(
    db: Any,
    older_than_days: int | None = None,
    storage_service: ExamStorageService | None = None,
) -> dict[str, Any]:
    """Remove fisicamente arquivos antigos e marca os exames como removidos."""
    storage_service = storage_service or ExamStorageService()
    older_than_days = settings.OCR_RETENTION_DAYS if older_than_days is None else older_than_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    exame_model = _get_exame_model()
    candidates = (
        db.query(exame_model)
        .filter(exame_model.created_at.isnot(None))
        .filter(exame_model.created_at < cutoff)
        .all()
    )

    deleted = 0
    skipped = 0
    errors = 0

    for exame in candidates:
        if exame.storage_status == "deleted":
            skipped += 1
            continue

        storage_object_key = exame.storage_object_key or exame.url_documento or ""
        metadata = StoredFileMetadata(
            storage_provider=(exame.storage_provider or "local"),
            storage_bucket=exame.storage_bucket,
            storage_object_key=storage_object_key,
            storage_content_type=exame.storage_content_type or "application/pdf",
            storage_size_bytes=exame.storage_size_bytes or 0,
            storage_checksum=exame.storage_checksum or "",
            storage_status=exame.storage_status or "stored",
            url_documento=exame.url_documento or "",
        )

        try:
            storage_service.delete_file(metadata)
            exame.storage_status = "deleted"
            db.commit()
            db.refresh(exame)
            deleted += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("Falha ao remover exame antigo %s: %s", exame.id, exc)

    return {
        "cutoff": cutoff.isoformat(),
        "exam_candidates": len(candidates),
        "deleted_files": deleted,
        "skipped_files": skipped,
        "errors": errors,
    }


def _get_exame_model():
    from app.models.exame import Exame

    return Exame
