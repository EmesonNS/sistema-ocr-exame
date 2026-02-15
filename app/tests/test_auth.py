from fastapi import status
import jwt
import time
from app.core.config import settings

def test_upload_without_auth(client):
    response = client.post("/api/v1/patients/1/exames/upload")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_upload_with_invalid_token(client):
    response = client.post(
        "/api/v1/patients/1/exames/upload",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_upload_with_expired_token(client):
    payload = {
        "sub": "123",
        "exp": time.time() - 3600 # Expired
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    response = client.post(
        "/api/v1/patients/1/exames/upload",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
