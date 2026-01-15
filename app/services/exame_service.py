import os
import shutil
import uuid
from datetime import datetime
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models import ResultadoBiomarcador
from app.services import ai_service
from app.repositories.exame_repo import ExameRepository
from app.repositories.paciente_repo import PacienteRepository
from app.core.celery_app import celery_app

UPLOAD_DIR = "uploads"

class ExameService:
    def __init__(self):
        self.exame_repo = ExameRepository()
        self.paciente_repo = PacienteRepository()

    def processar_upload(self, db: Session, paciente_id: uuid.UUID, file: UploadFile):
        # 1. Validar Paciente
        paciente = self.paciente_repo.get_by_id(db, paciente_id)
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")

        # 2. Salvar Arquivo Local
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_extension = os.path.splitext(file.filename)[1]
        novo_nome = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, novo_nome)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Criar registro 'Pendente' no banco
        exame = self.exame_repo.create_exame(db, paciente_id, file_path)

        celery_app.send_task(
            "processar_exame_task",
            args=[str(exame.id), file_path]
        )

        return exame

    def _salvar_resultados_ia(self, db: Session, exame_id: uuid.UUID, dados: dict):
        if "exame" not in dados:
            return

        info = dados["exame"]
        
        # Parse Data
        data_coleta = None
        if info.get("data"):
            try:
                data_coleta = datetime.strptime(info.get("data"), "%Y-%m-%d").date()
            except:
                pass # Data inválida ou vazia
        
        # Atualiza Cabeçalho do Exame
        self.exame_repo.update_exame_status(
            db, 
            exame_id, 
            status="concluido", 
            laboratorio=info.get("laboratorio"), 
            data_coleta=data_coleta
        )

        # Salva Biomarcadores
        biomarcadores = info.get("biomarcadores", [])
        for item in biomarcadores:
            status_alerta = ai_service.classificar_status_alerta(
                item.get('valor'), 
                item.get('referencia')
            )
            
            resultado = ResultadoBiomarcador(
                exame_id=exame_id,
                nome_marcador=item.get('nome', 'Desconhecido'),
                valor_extraido=item.get('valor'),
                unidade_medida=item.get('unidade'),
                referencia_lab=item.get('referencia'),
                status_alerta=status_alerta
            )
            self.exame_repo.add_resultado(db, resultado)