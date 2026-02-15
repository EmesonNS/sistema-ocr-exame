from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.services.exame_service import ExameService
from app.schemas.exame import ExameResponse, DetalheExameResponse, ExameListResponse
from app.core.auth import get_current_user_id

router = APIRouter()
exame_service = ExameService()

@router.post("/patients/{patient_id}/exames/upload", response_model=ExameResponse)
def upload_exame(
    patient_id: int = Path(..., title="Id do paciente no Storge"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos")
        
    return exame_service.processar_upload(db, patient_id, user_id, file)

@router.get("/patients/{patient_id}/exames", response_model=ExameListResponse)
def list_exames(
    patient_id: int = Path(..., title="Id do paciente no Storge"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    return exame_service.list_by_patient(db, patient_id, page, limit)

@router.get("/exames/{exame_id}", response_model=DetalheExameResponse)
def get_exame_details(
    exame_id: UUID,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    exame = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return exame

@router.get("/exames/{exame_id}/status", response_model=dict)
def get_exame_status(
    exame_id: UUID,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    exame = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return {"status": exame.status_processamento}