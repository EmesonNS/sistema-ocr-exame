from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks.worker"]
)

celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True


def build_beat_schedule() -> dict:
    return {
        "cleanup-old-exams-nightly": {
            "task": "cleanup_old_exams_task",
            "schedule": crontab(hour=3, minute=0),
            "kwargs": {"older_than_days": settings.OCR_RETENTION_DAYS},
        }
    }


celery_app.conf.beat_schedule = build_beat_schedule()
celery_app.autodiscover_tasks(["app.tasks"])
