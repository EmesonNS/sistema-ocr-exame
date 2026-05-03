from celery import Celery
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
celery_app.autodiscover_tasks(["app.tasks"])