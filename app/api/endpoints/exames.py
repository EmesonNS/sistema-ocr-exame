from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.schemas import DetalheExameResponse
from app.core.database import get_db
from app.services.exame_service import ExameService
from app.repositories.exame_repo import ExameRepository

router = APIRouter()
service = ExameService()
repo = ExameRepository()

@router.post("/pacientes/{paciente_id}/upload-exame/")
async def upload_exame(
    paciente_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    exame = service.processar_upload(db, paciente_id, file)

    return {
        "status": "processando",
        "mensagem": "Arquivo recebido. O processamento ocorrerá em segundo plano.",
        "exame_id": exame.id,
        "consultar_resultado": f"/api/v1/exames/{exame.id}"
    }

@router.get("/exames/{exame_id}", response_model=DetalheExameResponse)
def get_detalhe_exame(exame_id: uuid.UUID, db: Session = Depends(get_db)):
    exame = repo.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return exame