from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import redis
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import engine

_SECRET_PLACEHOLDERS = {
    "",
    "password",
    "changeme",
    "change-me",
    "sua_senha_segura_aqui",
    "test_password",
    "test_redis_password",
}


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    detail: str


def _secret_is_placeholder(value: str | None) -> bool:
    return value is None or value.strip().lower() in _SECRET_PLACEHOLDERS


def _cors_origins_is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        default_origins = ["http://localhost:5173", "https://app.storge.care"]
        return value == default_origins
    if isinstance(value, str):
        normalized = value.strip()
        return not normalized
    return True


def check_secrets() -> CheckResult:
    invalid = []
    if _secret_is_placeholder(settings.DB_PASS):
        invalid.append("DB_PASS")
    if _secret_is_placeholder(settings.REDIS_PASS):
        invalid.append("REDIS_PASS")
    if _secret_is_placeholder(settings.GEMINI_API_KEY):
        invalid.append("GEMINI_API_KEY")
    if _secret_is_placeholder(settings.MASTER_API_KEY):
        invalid.append("MASTER_API_KEY")
    if _cors_origins_is_placeholder(settings.CORS_ORIGINS):
        invalid.append("CORS_ORIGINS")
    if invalid:
        return CheckResult(
            ok=False,
            detail=f"segredos obrigatorios ausentes ou inseguros: {', '.join(invalid)}",
        )
    return CheckResult(ok=True, detail="ok")


def check_database() -> CheckResult:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return CheckResult(ok=True, detail="ok")
    except Exception as exc:  # pragma: no cover - detail preserved in payload
        return CheckResult(ok=False, detail=f"database indisponivel: {exc}")


def check_redis() -> CheckResult:
    client = redis.Redis.from_url(settings.cache_redis_url, decode_responses=True)
    try:
        client.ping()
        return CheckResult(ok=True, detail="ok")
    except Exception as exc:  # pragma: no cover - detail preserved in payload
        return CheckResult(ok=False, detail=f"redis indisponivel: {exc}")
    finally:
        client.close()


def check_worker() -> CheckResult:
    try:
        inspector = celery_app.control.inspect(timeout=1.0)
        if inspector is None:
            return CheckResult(ok=False, detail="worker indisponivel: sem inspector")
        ping = inspector.ping() or {}
        if not ping:
            return CheckResult(ok=False, detail="worker indisponivel: sem resposta")
        return CheckResult(ok=True, detail="ok")
    except Exception as exc:  # pragma: no cover - detail preserved in payload
        return CheckResult(ok=False, detail=f"worker indisponivel: {exc}")


def build_runtime_readiness_report() -> dict[str, Any]:
    checks = {
        "secrets": check_secrets(),
        "database": check_database(),
        "redis": check_redis(),
        "worker": check_worker(),
    }
    ready = all(check.ok for check in checks.values())
    return {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "version": "1.0.0",
        "checks": {
            name: {"ok": result.ok, "detail": result.detail} for name, result in checks.items()
        },
    }
