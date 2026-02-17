from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.api_key import ApiKey
import hashlib


def hash_api_key(key: str) -> str:
    """Hash da API key usando SHA-256 para armazenamento seguro."""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_client(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Valida a API Key enviada no header X-API-Key.
    Retorna o nome do cliente autenticado.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key ausente. Envie o header X-API-Key.",
        )

    key_hash = hash_api_key(x_api_key)

    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida ou inativa.",
        )

    # Retorna um dict com informações do cliente para uso nos endpoints
    return {
        "client_name": api_key.client_name,
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
    }


# Para compatibilidade com endpoints que ainda esperam apenas validação
async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """Versão simplificada que apenas valida e retorna True."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key ausente. Envie o header X-API-Key.",
        )

    key_hash = hash_api_key(x_api_key)

    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida ou inativa.",
        )

    return True
