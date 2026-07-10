import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.auth import hash_api_key
from app.models.api_key import ApiKey


class TestAPIKeyAuthentication:
    """Testes de autenticação via API Key"""

    def test_valid_api_key(self, client, auth_headers):
        """API key válida deve permitir acesso"""
        response = client.get("/api/v1/patients/1/exames", headers=auth_headers)
        # 200 ou 404 (paciente não existe) são aceitáveis
        assert response.status_code in [200, 404]

    def test_missing_api_key(self, client):
        """Ausência de API key deve retornar 401"""
        response = client.get("/api/v1/patients/1/exames")
        assert response.status_code == 401
        assert "API Key ausente" in response.json()["detail"]

    def test_invalid_api_key(self, client):
        """API key inválida deve retornar 401"""
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/api/v1/patients/1/exames", headers=headers)
        assert response.status_code == 401

    def test_inactive_api_key(self, client, db_session, test_api_key):
        """API key inativa deve retornar 401"""
        # Desativar a chave
        from app.models.api_key import ApiKey
        from app.core.auth import hash_api_key

        api_key_record = (
            db_session.query(ApiKey)
            .filter(ApiKey.key_hash == hash_api_key(test_api_key))
            .first()
        )
        api_key_record.is_active = False
        db_session.commit()

        headers = {"X-API-Key": test_api_key}
        response = client.get("/api/v1/patients/1/exames", headers=headers)
        assert response.status_code == 401


class TestMasterKeyAuthentication:
    """Testes de autenticação master para admin"""

    def test_master_key_required_for_api_keys(self, client):
        """Endpoints de API keys devem exigir master key"""
        response = client.post("/api/v1/api-keys", json={"name": "Test"})
        assert response.status_code == 422  # Missing header

    def test_invalid_master_key(self, client):
        """Master key inválida deve retornar 401 ou 503 (se serviço indisponível)"""
        headers = {"X-Master-Key": "wrong_key"}
        response = client.post(
            "/api/v1/api-keys", headers=headers, json={"name": "Test"}
        )
        # 401 = unauthorized, 503 = service unavailable (sem BD configurado)
        assert response.status_code in [401, 503]

    def test_rotate_api_key_creates_new_version(
        self, client, db_session, test_api_key, monkeypatch
    ):
        """Rotação deve desativar a chave atual e criar uma nova versão."""
        monkeypatch.setattr(settings, "MASTER_API_KEY", "test-master-key")

        original = (
            db_session.query(ApiKey)
            .filter(ApiKey.key_hash == hash_api_key(test_api_key))
            .first()
        )

        response = client.post(
            f"/api/v1/api-keys/{original.id}/rotate",
            headers={"X-Master-Key": "test-master-key"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["version"] == 2
        assert payload["rotated_from_id"] == str(original.id)
        assert payload["rotated_at"] is None

        db_session.refresh(original)
        assert original.is_active is False
        assert original.rotated_at is not None

        rotated = (
            db_session.query(ApiKey)
            .filter(ApiKey.id == payload["id"])
            .first()
        )
        assert rotated is not None
        assert rotated.version == 2
        assert rotated.rotated_from_id == original.id
        assert rotated.is_active is True

    def test_list_api_keys_exposes_version_metadata(
        self, client, master_headers, test_api_key, monkeypatch
    ):
        """Listagem deve expor versão e origem da rotação."""
        monkeypatch.setattr(settings, "MASTER_API_KEY", master_headers["X-Master-Key"])

        response = client.get("/api/v1/api-keys", headers=master_headers)

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["version"] == 1
        assert payload[0]["rotated_from_id"] is None
        assert payload[0]["rotated_at"] is None
