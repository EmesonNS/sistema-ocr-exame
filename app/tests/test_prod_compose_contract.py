from pathlib import Path


def test_production_compose_uses_local_storage():
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.prod.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "OCR_STORAGE_BACKEND: local" in content
    assert "OCR_LOCAL_STORAGE_DIR: ${OCR_LOCAL_STORAGE_DIR:-/code/uploads}" in content
    assert "minio:" not in content
