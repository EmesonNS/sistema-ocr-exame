from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.schemas import PacienteCreate, PacienteResponse, ExameResponse
from app.core.database import get_db
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.exame_repo import ExameRepository

router = APIRouter()
paciente_repo = PacienteRepository()
exame_repo = ExameRepository()

@router.post("/", response_model=PacienteResponse)
def create_paciente(paciente: PacienteCreate, db: Session = Depends(get_db)):
    if paciente_repo.get_by_cpf(db, paciente.cpf):
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    return paciente_repo.create(db, paciente)

@router.get("/", response_model=List[PacienteResponse])
def list_pacientes(db: Session = Depends(get_db)):
    return paciente_repo.list_all(db)

@router.get("/{paciente_id}", response_model=PacienteResponse)
def get_paciente(paciente_id: uuid.UUID, db: Session = Depends(get_db)):
    paciente = paciente_repo.get_by_id(db, paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return paciente

@router.get("/{paciente_id}/exames/", response_model=List[ExameResponse])
def get_exames_paciente(paciente_id: uuid.UUID, db: Session = Depends(get_db)):
    # Verifica se paciente existe
    if not paciente_repo.get_by_id(db, paciente_id):
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return exame_repo.list_by_paciente(db, paciente_id)