import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models import Exame, ResultadoBiomarcador
from app.repositories.exame_repo import ExameRepository
from app.core.celery_app import celery_app
from app.schemas.exame import ExameListResponse

UPLOAD_DIR = "uploads"

class ExameService:
    def __init__(self):
        self.exame_repo = ExameRepository()

    def processar_upload(self, db: Session, patient_id: int, user_id: int, file: UploadFile):
        # 1. Salvar Arquivo Local
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_extension = os.path.splitext(file.filename)[1]
        novo_nome = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, novo_nome)
        
        # Reset file cursor (pode ter sido consumido pelo FastAPI)
        file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Criar registro 'Pendente' no banco
        exame = self.exame_repo.create_exame(db, patient_id, user_id, file_path)

        # 3. Enviar task para o Celery
        celery_app.send_task(
            "processar_exame_task",
            args=[str(exame.id), file_path]
        )

        return exame

    def get_exame(self, db: Session, exame_id: uuid.UUID):
        return self.exame_repo.get_exame(db, exame_id)
        
    def list_by_patient(self, db: Session, patient_id: int, page: int = 1, limit: int = 10) -> ExameListResponse:
        skip = (page - 1) * limit
        items, total = self.exame_repo.list_by_patient_id(db, patient_id, skip, limit)
        pages = (total + limit - 1) // limit
        
        return ExameListResponse(
            items=items,
            total=total,
            page=page,
            pages=pages
        )