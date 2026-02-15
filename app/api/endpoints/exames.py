from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.services.exame_service import ExameService
from app.schemas.exame import (
    ExameResponse,
    DetalheExameResponse,
    ExameListResponse,
    ExameStatusResponse,
)
from app.core.auth import get_current_user_id

router = APIRouter()
exame_service = ExameService()


@router.post(
    "/patients/{patient_id}/exames/upload",
    response_model=ExameResponse,
    summary="Upload de exame (PDF)",
    description=(
        "Faz upload de um arquivo PDF de exame laboratorial para um paciente. "
        "O arquivo é salvo e uma task assíncrona é disparada para extrair "
        "biomarcadores via Gemini AI. O exame inicia com status `pendente`."
    ),
    responses={
        200: {"description": "Exame criado e processamento iniciado"},
        400: {"description": "Arquivo não é PDF"},
        401: {"description": "Token JWT ausente ou inválido"},
    },
)
def upload_exame(
    patient_id: int = Path(..., description="ID do paciente no Storge", example=42),
    file: UploadFile = File(..., description="Arquivo PDF do exame laboratorial"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos")

    return exame_service.processar_upload(db, patient_id, user_id, file)


@router.get(
    "/patients/{patient_id}/exames",
    response_model=ExameListResponse,
    summary="Listar exames de um paciente",
    description=(
        "Retorna uma lista paginada de todos os exames de um paciente. "
        "Use `page` e `limit` para navegação."
    ),
    responses={
        200: {"description": "Lista paginada de exames"},
        401: {"description": "Token JWT ausente ou inválido"},
    },
)
def list_exames(
    patient_id: int = Path(..., description="ID do paciente no Storge", example=42),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return exame_service.list_by_patient(db, patient_id, page, limit)


@router.get(
    "/exames/{exame_id}",
    response_model=DetalheExameResponse,
    summary="Detalhes de um exame",
    description=(
        "Retorna os detalhes completos de um exame incluindo todos os "
        "biomarcadores extraídos pelo OCR."
    ),
    responses={
        200: {"description": "Detalhes do exame com biomarcadores"},
        401: {"description": "Token JWT ausente ou inválido"},
        404: {"description": "Exame não encontrado"},
    },
)
def get_exame_details(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    exame = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return exame


@router.get(
    "/exames/{exame_id}/status",
    response_model=ExameStatusResponse,
    summary="Status de processamento (polling)",
    description=(
        "Endpoint leve para polling do status de processamento de um exame. "
        "Valores possíveis: `pendente`, `processando`, `concluido`, `erro`. "
        "Recomendamos polling a cada 3-5 segundos."
    ),
    responses={
        200: {"description": "Status atual do processamento"},
        401: {"description": "Token JWT ausente ou inválido"},
        404: {"description": "Exame não encontrado"},
    },
)
def get_exame_status(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    exame = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return ExameStatusResponse(status=exame.status_processamento)