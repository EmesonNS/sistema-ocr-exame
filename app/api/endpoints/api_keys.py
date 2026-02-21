from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.api_key import ApiKey
from app.core.auth import hash_api_key
from app.core.admin_auth import require_master_key

router = APIRouter()


class ApiKeyCreate(BaseModel):
    """Schema para criação de nova API Key."""

    client_name: str = Field(..., description="Nome do cliente/aplicação")
    rate_limit_per_minute: int = Field(
        60, description="Limite de requisições por minuto"
    )


class ApiKeyResponse(BaseModel):
    """Schema de resposta com a API Key (mostrada apenas uma vez)."""

    id: UUID
    client_name: str
    api_key: str = Field(
        ..., description="API Key gerada (guarde-a, não será exibida novamente)"
    )
    rate_limit_per_minute: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyInfo(BaseModel):
    """Schema de informação sem expor a key."""

    id: UUID
    client_name: str
    is_active: bool
    rate_limit_per_minute: int
    created_at: datetime

    class Config:
        from_attributes = True


def generate_api_key() -> str:
    """Gera uma API Key aleatória de 32 bytes em hex."""
    import secrets

    return secrets.token_hex(32)


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    summary="Criar nova API Key",
    description="Gera uma nova API Key para um cliente. A key só é exibida uma vez. Requer X-Master-Key header.",
    responses={
        200: {"description": "API Key criada"},
        400: {"description": "Nome de cliente já existe"},
        401: {"description": "Chave mestra inválida"},
        503: {"description": "Admin desabilitado"},
    },
)
def create_api_key(
    data: ApiKeyCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(require_master_key),
):
    # Verifica se já existe uma key para este cliente
    existing = db.query(ApiKey).filter(ApiKey.client_name == data.client_name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma API Key para o cliente '{data.client_name}'",
        )

    # Gera a key e seu hash
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        key_hash=key_hash,
        client_name=data.client_name,
        rate_limit_per_minute=data.rate_limit_per_minute,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyResponse(
        id=api_key.id,
        client_name=api_key.client_name,
        api_key=raw_key,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        created_at=api_key.created_at,
    )


@router.get(
    "/api-keys",
    response_model=List[ApiKeyInfo],
    summary="Listar API Keys",
    description="Lista todas as API Keys cadastradas (sem expor as chaves). Requer X-Master-Key header.",
    responses={
        200: {"description": "Lista de API Keys"},
        401: {"description": "Chave mestra inválida"},
        503: {"description": "Admin desabilitado"},
    },
)
def list_api_keys(db: Session = Depends(get_db), _: bool = Depends(require_master_key)):
    keys = db.query(ApiKey).all()
    return [
        ApiKeyInfo(
            id=k.id,
            client_name=k.client_name,
            is_active=k.is_active,
            rate_limit_per_minute=k.rate_limit_per_minute,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete(
    "/api-keys/{key_id}",
    summary="Revogar API Key",
    description="Desativa uma API Key (soft delete). Requer X-Master-Key header.",
    responses={
        200: {"description": "API Key revogada"},
        401: {"description": "Chave mestra inválida"},
        404: {"description": "API Key não encontrada"},
        503: {"description": "Admin desabilitado"},
    },
)
def revoke_api_key(
    key_id: UUID, db: Session = Depends(get_db), _: bool = Depends(require_master_key)
):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key não encontrada")

    api_key.is_active = False
    db.commit()

    return {"message": f"API Key para '{api_key.client_name}' foi revogada"}


@router.post(
    "/api-keys/{key_id}/activate",
    summary="Reativar API Key",
    description="Reativa uma API Key previamente revogada. Requer X-Master-Key header.",
    responses={
        200: {"description": "API Key reativada"},
        401: {"description": "Chave mestra inválida"},
        404: {"description": "API Key não encontrada"},
        503: {"description": "Admin desabilitado"},
    },
)
def activate_api_key(
    key_id: UUID, db: Session = Depends(get_db), _: bool = Depends(require_master_key)
):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key não encontrada")

    api_key.is_active = True
    db.commit()

    return {"message": f"API Key para '{api_key.client_name}' foi reativada"}
