import pytest
from io import BytesIO
from datetime import datetime, timezone
from uuid import uuid4

from unittest.mock import patch, MagicMock

try:
    from unittest.mock import AsyncMock
except ImportError:
    AsyncMock = MagicMock


class TestExamesEndpoints:
    """Testes dos endpoints de exames"""

    def test_upload_pdf_success(self, client, auth_headers):
        """Upload de PDF válido deve criar exame"""
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_file = BytesIO(pdf_content)

        response = client.post(
            "/api/v1/patients/1/exames/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", pdf_file, "application/pdf")},
            params={"user_id": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status_processamento"] == "pendente"

    def test_upload_non_pdf_rejected(self, client, auth_headers):
        """Upload de arquivo não-PDF deve ser rejeitado"""
        text_file = BytesIO(b"text content")

        response = client.post(
            "/api/v1/patients/1/exames/upload",
            headers=auth_headers,
            files={"file": ("test.txt", text_file, "text/plain")},
            params={"user_id": 1},
        )

        assert response.status_code == 400

    def test_list_exames(self, client, auth_headers):
        """Listar exames deve retornar lista paginada"""
        response = client.get("/api/v1/patients/1/exames", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_exame_not_found(self, client, auth_headers):
        """Buscar exame inexistente deve retornar 404"""
        from uuid import uuid4

        fake_id = str(uuid4())

        response = client.get(f"/api/v1/exames/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    def test_status_endpoint_returns_progress_fields(self, client, auth_headers):
        """Status endpoint deve retornar campos de progresso"""
        # Upload a file first
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_file = BytesIO(pdf_content)

        upload_response = client.post(
            "/api/v1/patients/1/exames/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", pdf_file, "application/pdf")},
            params={"user_id": 1},
        )

        assert upload_response.status_code == 200
        exame_id = upload_response.json()["id"]

        # Check status endpoint
        status_response = client.get(
            f"/api/v1/exames/{exame_id}/status",
            headers=auth_headers,
        )

        assert status_response.status_code == 200
        data = status_response.json()

        # Verify response contains progress fields
        assert "status" in data
        assert "processing_stage" in data
        assert "processing_percent" in data
        assert "processing_message" in data

        # Initial status should be pending
        assert data["status"] == "pendente"

    def test_exame_response_includes_progress_fields(self, client, auth_headers):
        """ExameResponse deve incluir campos de progresso"""
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_file = BytesIO(pdf_content)

        response = client.post(
            "/api/v1/patients/1/exames/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", pdf_file, "application/pdf")},
            params={"user_id": 1},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response contains progress fields
        assert "processing_stage" in data
        assert "processing_percent" in data
        assert "processing_message" in data

    def test_get_resumo_clinico_success(self, client, auth_headers, db_session):
        from app.models.exame import Exame, ResultadoBiomarcador

        exame = Exame(
            id=uuid4(),
            patient_id=1,
            uploaded_by_user_id=1,
            url_documento="uploads/test.pdf",
            status_processamento="concluido",
            summary_generated_at=datetime.now(timezone.utc),
        )
        db_session.add(exame)
        db_session.commit()

        resultado = ResultadoBiomarcador(
            id=uuid4(),
            exame_id=exame.id,
            nome_marcador="LEUCÓCITOS",
            valor_extraido="12000",
            unidade_medida="/mm³",
            referencia_lab="4000-10000",
            referencia_min=4000,
            referencia_max=10000,
            status_alerta="alto",
        )
        db_session.add(resultado)
        db_session.commit()

        fake_summary = {
            "resumo_geral": "Resumo teste",
            "alertas": [],
            "recomendacoes": ["Recomendacao"],
            "destilacoes": ["Insight"],
            "proximos_passos": ["Passo"],
        }

        with patch(
            "app.api.endpoints.exames.clinical_summary_service.generate_clinical_summary",
            new=AsyncMock(return_value=fake_summary),
        ):
            response = client.get(
                f"/api/v1/exames/{exame.id}/resumo",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["resumo_geral"] == "Resumo teste"
        assert "generated_at" in data

    def test_regenerate_resumo_clinico_success(self, client, auth_headers, db_session):
        from app.models.exame import Exame, ResultadoBiomarcador

        exame = Exame(
            id=uuid4(),
            patient_id=1,
            uploaded_by_user_id=1,
            url_documento="uploads/test.pdf",
            status_processamento="concluido",
            clinical_summary={"resumo_geral": "Old"},
            summary_generated_at=datetime.now(timezone.utc),
        )
        db_session.add(exame)
        db_session.commit()

        resultado = ResultadoBiomarcador(
            id=uuid4(),
            exame_id=exame.id,
            nome_marcador="HEMOGLOBINA",
            valor_extraido="13.5",
            unidade_medida="g/dL",
            referencia_lab="12-16",
            referencia_min=12,
            referencia_max=16,
            status_alerta="normal",
        )
        db_session.add(resultado)
        db_session.commit()

        new_summary = {
            "resumo_geral": "Novo resumo",
            "alertas": [],
            "recomendacoes": [],
            "destilacoes": [],
            "proximos_passos": [],
        }

        async def _fake_regenerate(db, exame_id, biomarcadores):
            ex = db.query(Exame).filter(Exame.id == exame_id).first()
            ex.clinical_summary = new_summary
            ex.summary_generated_at = datetime.now(timezone.utc)
            db.commit()
            return new_summary

        with patch(
            "app.api.endpoints.exames.clinical_summary_service.regenerate_summary",
            new=AsyncMock(side_effect=_fake_regenerate),
        ):
            response = client.post(
                f"/api/v1/exames/{exame.id}/resumo/regenerate",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["resumo_geral"] == "Novo resumo"
        assert data["generated_at"] is not None
