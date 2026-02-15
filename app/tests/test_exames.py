from fastapi import status
import pytest
from app.models.exame import Exame
from uuid import uuid4

@pytest.fixture
def mock_upload_file(tmp_path):
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4 content")
    return file_path

def test_upload_exame_success(client, mock_jwt_token, mock_upload_file):
    with open(mock_upload_file, "rb") as f:
        response = client.post(
            "/api/v1/patients/123/exames/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["patient_id"] == 123
    assert data["status_processamento"] == "pendente"
    assert "id" in data

def test_upload_exame_invalid_file_type(client, mock_jwt_token, tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"text content")
    
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/v1/patients/123/exames/upload",
            files={"file": ("test.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_list_exames(client, db, mock_jwt_token):
    # Setup - create exam
    exame = Exame(
        patient_id=123,
        uploaded_by_user_id=1,
        url_documento="path/to/doc.pdf",
        status_processamento="concluido"
    )
    db.add(exame)
    db.commit()

    response = client.get(
        "/api/v1/patients/123/exames",
        headers={"Authorization": f"Bearer {mock_jwt_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["patient_id"] == 123

def test_get_exame_details(client, db, mock_jwt_token):
    exame_id = uuid4()
    exame = Exame(
        id=exame_id,
        patient_id=123,
        uploaded_by_user_id=1,
        url_documento="path/to/doc.pdf",
        status_processamento="concluido"
    )
    db.add(exame)
    db.commit()

    response = client.get(
        f"/api/v1/exames/{exame_id}",
        headers={"Authorization": f"Bearer {mock_jwt_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(exame_id)
    assert data["status_processamento"] == "concluido"
