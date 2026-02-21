"""
Dependency de autenticação administrativa.

Protege endpoints de API Keys exigindo chave mestra no header.
"""

from fastapi import Header, HTTPException

from app.core.config import settings


async def require_master_key(
    master_key: str = Header(
        ..., alias="X-Master-Key", description="Chave mestra para operações admin"
    ),
) -> bool:
    """
    Dependency que exige chave mestra para operações administrativas.

    Use em endpoints que criam/gerenciam API Keys.

    Args:
        master_key: Valor do header X-Master-Key

    Returns:
        True se autenticado com sucesso

    Raises:
        HTTPException 503: Se MASTER_API_KEY não configurada
        HTTPException 401: Se chave inválida
    """
    # Early exit: admin desabilitado
    if not settings.MASTER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin access disabled: MASTER_API_KEY not configured in environment",
        )

    # Early exit: chave inválida
    if master_key != settings.MASTER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid master key")

    return True
