import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models import Exame, ResultadoBiomarcador, ExameBatch
from app.repositories.exame_repo import ExameRepository
from app.core.celery_app import celery_app
from app.schemas.exame import ExameListResponse
from app.services.storage_service import (
    ExamStorageService,
    StorageUnavailableError,
    StoredFileMetadata,
)
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"

class ExameService:
    def __init__(self):
        self.exame_repo = ExameRepository()
        self.storage_service = ExamStorageService()

    def _salvar_arquivo(self, file: UploadFile) -> str:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_extension = os.path.splitext(file.filename or "")[1]
        novo_nome = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, novo_nome)
        
        file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path

    def _verificar_assinatura(self, file_path: str) -> bool:
        try:
            reader = PdfReader(file_path)
            fields = reader.get_fields() or {}
            for field in fields.values():
                if field.get("/FT") == "/Sig":
                    return True
        except Exception as e:
            logger.warning(f"Erro ao verificar assinatura no PDF {file_path}: {e}")
        return False

    def processar_upload(self, db: Session, patient_id: int, user_id: int, file: UploadFile, webhook_url: Optional[str] = None):
        # 1. Salvar Arquivo Temporario Local
        file_path = self._salvar_arquivo(file)
        stored_metadata: Optional[StoredFileMetadata] = None

        try:
            # Verificar se tem assinatura digital
            is_signed = self._verificar_assinatura(file_path)
            stored_metadata = self.storage_service.store_file(
                source_path=file_path,
                patient_id=patient_id,
                original_filename=file.filename,
                content_type=file.content_type,
            )

            # 2. Criar registro 'Pendente' no banco
            exame = self.exame_repo.create_exame(
                db,
                patient_id,
                user_id,
                stored_metadata.url_documento,
                original_filename=file.filename,
                storage_provider=stored_metadata.storage_provider,
                storage_bucket=stored_metadata.storage_bucket,
                storage_object_key=stored_metadata.storage_object_key,
                storage_content_type=stored_metadata.storage_content_type,
                storage_size_bytes=stored_metadata.storage_size_bytes,
                storage_checksum=stored_metadata.storage_checksum,
                storage_status=stored_metadata.storage_status,
                webhook_url=webhook_url,
                is_digitally_signed=is_signed,
            )

            # 3. Enviar task para o Celery
            celery_app.send_task(
                "processar_exame_task",
                args=[str(exame.id), file_path]
            )

            return exame
        except StorageUnavailableError as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Storage indisponível no upload do exame: {e}")
            raise HTTPException(status_code=503, detail="Storage de exames indisponível. Tente novamente.")
        except Exception as e:
            # Cleanup: Deletar arquivo órfão se o banco/celery falhar
            if stored_metadata:
                self.storage_service.delete_file(stored_metadata)
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Erro ao processar upload - arquivo removido: {e}")
            raise e

    def processar_upload_batch(self, db: Session, patient_id: int, user_id: int, files: List[UploadFile], webhook_url: Optional[str] = None):
        """Processa o upload de múltiplos exames em lote."""
        if not files:
            raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

        # 1. Criar o lote
        batch = self.exame_repo.create_batch(db, patient_id, total_files=len(files), webhook_url=webhook_url)

        # 2. Processar cada arquivo
        for file in files:
            file_path = self._salvar_arquivo(file)
            stored_metadata: Optional[StoredFileMetadata] = None
            
            try:
                is_signed = self._verificar_assinatura(file_path)
                stored_metadata = self.storage_service.store_file(
                    source_path=file_path,
                    patient_id=patient_id,
                    original_filename=file.filename,
                    content_type=file.content_type,
                )
                
                exame = self.exame_repo.create_exame(
                    db, 
                    patient_id, 
                    user_id, 
                    stored_metadata.url_documento,
                    original_filename=file.filename,
                    storage_provider=stored_metadata.storage_provider,
                    storage_bucket=stored_metadata.storage_bucket,
                    storage_object_key=stored_metadata.storage_object_key,
                    storage_content_type=stored_metadata.storage_content_type,
                    storage_size_bytes=stored_metadata.storage_size_bytes,
                    storage_checksum=stored_metadata.storage_checksum,
                    storage_status=stored_metadata.storage_status,
                    webhook_url=None,
                    is_digitally_signed=is_signed,
                    batch_id=batch.id
                )

                celery_app.send_task(
                    "processar_exame_task",
                    args=[str(exame.id), file_path]
                )
            except StorageUnavailableError as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.error(f"Storage indisponível no item do lote: {e}")
                continue
            except Exception as e:
                # Cleanup individual
                if stored_metadata:
                    self.storage_service.delete_file(stored_metadata)
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.error(f"Erro no item do lote - arquivo removido: {e}")
                # Continuar com os outros itens do lote? 
                # Sim, mas o total_files do batch ficará incorreto se não tratarmos.
                # Para simplificar agora, apenas logamos e removemos o arquivo.
                continue

        return batch

    def get_exame(self, db: Session, exame_id: uuid.UUID):
        return self.exame_repo.get_exame(db, exame_id)

    def get_batch(self, db: Session, batch_id: uuid.UUID):
        return self.exame_repo.get_batch(db, batch_id)
        
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
