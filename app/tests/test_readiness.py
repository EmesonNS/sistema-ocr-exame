from app.core import runtime_readiness


def test_secret_placeholder_detection():
    assert runtime_readiness._secret_is_placeholder("")
    assert runtime_readiness._secret_is_placeholder("password")
    assert runtime_readiness._secret_is_placeholder("sua_senha_segura_aqui")
    assert not runtime_readiness._secret_is_placeholder("valor_real")


def test_check_secrets_requires_gemini_key(monkeypatch):
    monkeypatch.setattr(runtime_readiness.settings, "DB_PASS", "real_db_pass")
    monkeypatch.setattr(runtime_readiness.settings, "REDIS_PASS", "real_redis_pass")
    monkeypatch.setattr(runtime_readiness.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(runtime_readiness.settings, "MASTER_API_KEY", "real_master_key")

    result = runtime_readiness.check_secrets()

    assert result.ok is False
    assert "GEMINI_API_KEY" in result.detail


def test_check_secrets_requires_master_key(monkeypatch):
    monkeypatch.setattr(runtime_readiness.settings, "DB_PASS", "real_db_pass")
    monkeypatch.setattr(runtime_readiness.settings, "REDIS_PASS", "real_redis_pass")
    monkeypatch.setattr(runtime_readiness.settings, "GEMINI_API_KEY", "real_gemini_key")
    monkeypatch.setattr(runtime_readiness.settings, "MASTER_API_KEY", "")
    monkeypatch.setattr(
        runtime_readiness.settings,
        "CORS_ORIGINS",
        ["https://app.storge.care"],
    )

    result = runtime_readiness.check_secrets()

    assert result.ok is False
    assert "MASTER_API_KEY" in result.detail


def test_check_secrets_requires_cors_origins(monkeypatch):
    monkeypatch.setattr(runtime_readiness.settings, "DB_PASS", "real_db_pass")
    monkeypatch.setattr(runtime_readiness.settings, "REDIS_PASS", "real_redis_pass")
    monkeypatch.setattr(runtime_readiness.settings, "GEMINI_API_KEY", "real_gemini_key")
    monkeypatch.setattr(runtime_readiness.settings, "MASTER_API_KEY", "real_master_key")
    monkeypatch.setattr(
        runtime_readiness.settings,
        "CORS_ORIGINS",
        ["http://localhost:5173", "https://app.storge.care"],
    )

    result = runtime_readiness.check_secrets()

    assert result.ok is False
    assert "CORS_ORIGINS" in result.detail


def test_build_runtime_readiness_report_ready(monkeypatch):
    monkeypatch.setattr(
        runtime_readiness.settings,
        "GEMINI_API_KEY",
        "real_gemini_key",
    )
    monkeypatch.setattr(
        runtime_readiness.settings,
        "MASTER_API_KEY",
        "real_master_key",
    )
    monkeypatch.setattr(
        runtime_readiness.settings,
        "CORS_ORIGINS",
        ["https://app.storge.care"],
    )
    monkeypatch.setattr(
        runtime_readiness,
        "check_secrets",
        lambda: runtime_readiness.CheckResult(ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        runtime_readiness,
        "check_database",
        lambda: runtime_readiness.CheckResult(ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        runtime_readiness,
        "check_redis",
        lambda: runtime_readiness.CheckResult(ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        runtime_readiness,
        "check_worker",
        lambda: runtime_readiness.CheckResult(ok=True, detail="ok"),
    )

    report = runtime_readiness.build_runtime_readiness_report()

    assert report["status"] == "ready"
    assert report["ready"] is True
    assert report["checks"]["database"]["ok"] is True
    assert report["checks"]["worker"]["ok"] is True


def test_ready_endpoint_returns_503_when_not_ready(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.build_runtime_readiness_report",
        lambda: {
            "status": "not_ready",
            "ready": False,
            "version": "1.0.0",
            "checks": {
                "secrets": {"ok": False, "detail": "segredos obrigatorios ausentes"},
                "database": {"ok": True, "detail": "ok"},
                "redis": {"ok": True, "detail": "ok"},
                "worker": {"ok": True, "detail": "ok"},
            },
        },
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "not_ready"


def test_ready_endpoint_returns_200_when_ready(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.build_runtime_readiness_report",
        lambda: {
            "status": "ready",
            "ready": True,
            "version": "1.0.0",
            "checks": {
                "secrets": {"ok": True, "detail": "ok"},
                "database": {"ok": True, "detail": "ok"},
                "redis": {"ok": True, "detail": "ok"},
                "worker": {"ok": True, "detail": "ok"},
            },
        },
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
