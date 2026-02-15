from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks.worker"]
)

celery_app.autodiscover_tasks(["app.tasks"])