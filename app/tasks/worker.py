"""
Celery worker para processamento assíncrono de exames.

Processa exames laboratoriais usando AI service e normalização determinística.
"""

import os
import asyncio
import uuid
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.ai_service import AIService
from app.services.clinical_summary_service import ClinicalSummaryService
from app.services.webhook_service import WebhookService
from app.repositories.exame_repo import ExameRepository
from app.models.exame import ProcessingStage
from typing import Dict, Any
import logging

# Configure logger
logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Task base com gerenciamento de conexão DB."""

    _db = None

    @property
    def db(self):
        """Lazy loading da conexão DB."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Fecha conexão DB após task completar."""
        if self._db:
            self._db.close()


# Instantiate services
ai_service = AIService()
clinical_summary_service = ClinicalSummaryService()
webhook_service = WebhookService()
exame_repo = ExameRepository()


@celery_app.task(
    base=DatabaseTask,
    name="processar_exame_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def processar_exame_task(self, exame_id: str, file_path: str):
    """Orquestra o processamento do exame."""
    logger.info(f"Iniciando processamento do exame {exame_id}")

    try:
        # 1. Queued (0%)
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.QUEUED,
            0,
            "Processamento na fila",
        )

        # 2. Downloading (10%)
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.DOWNLOADING,
            10,
            "Preparando arquivo para análise",
        )

        # 3. OCR Extracting (30%)
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.OCR_EXTRACTING,
            30,
            "Extraindo texto via OCR",
        )

        # 4. AI Analyzing (50%)
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.AI_ANALYZING,
            50,
            "Analisando biomarcadores com IA",
        )

        # Extract data using AI com normalização
        resultados, data_coleta, laboratorio = asyncio.run(
            ai_service.extrair_biomarcadores(file_path)
        )

        # 5. Normalizing (80%)
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.NORMALIZING,
            80,
            "Normalizando valores e unidades",
        )

        # 6. Atualizar exame com metadados
        if data_coleta or laboratorio:
            exame_repo.update_exame_metadata(
                self.db,
                exame_id,
                data_coleta=data_coleta,
                laboratorio=laboratorio,
            )

        # 7. Salvar resultados
        if resultados:
            for res in resultados:
                exame_repo.add_resultado_normalizado(self.db, exame_id, res)

            # 8. Gerar resumo clínico (passo opcional/final)
            try:
                # Coerce ID for safe comparison/lookup
                coerced_id = None
                try:
                    coerced_id = uuid.UUID(exame_id) if isinstance(exame_id, str) else exame_id
                except ValueError:
                    coerced_id = None

                # Aqui o service já é async, então usamos asyncio.run
                asyncio.run(
                    clinical_summary_service.generate_clinical_summary(
                        self.db,
                        exame_id=coerced_id or exame_id,
                        biomarcadores=resultados,
                    )
                )
            except Exception as e:
                logger.exception(
                    f"Falha ao gerar resumo clínico para exame {exame_id}: {e}"
                )

            exame_repo.update_processing_progress(
                self.db,
                exame_id,
                ProcessingStage.COMPLETED,
                100,
                f"Processamento concluído - {len(resultados)} biomarcadores extraídos",
            )
            logger.info(
                f"Exame {exame_id} concluído com sucesso - {len(resultados)} biomarcadores"
            )

            # Enviar Webhook de Sucesso
            try:
                coerced_id = uuid.UUID(exame_id) if isinstance(exame_id, str) else exame_id
                exame = exame_repo.get_exame(self.db, coerced_id)
                if exame and exame.webhook_url:
                    webhook_service.send_notification_sync(
                        exame.webhook_url,
                        {
                            "exame_id": str(exame_id),
                            "status": "concluido",
                            "biomarcadores_count": len(resultados),
                            "patient_id": exame.patient_id,
                        }
                    )
                
                # Tratar Lote (Batch)
                if exame and exame.batch_id:
                    batch, just_completed = exame_repo.update_batch_progress(self.db, exame.batch_id, success=True)
                    if batch and just_completed and batch.webhook_url:
                        webhook_service.send_notification_sync(
                            batch.webhook_url,
                            {
                                "batch_id": str(batch.id),
                                "status": "concluido",
                                "total_files": batch.total_files,
                                "patient_id": batch.patient_id,
                            }
                        )

            except Exception as e:
                logger.error(f"Erro ao enviar webhook de sucesso ou atualizar lote: {e}")
        else:
            exame_repo.update_processing_progress(
                self.db,
                exame_id,
                ProcessingStage.FAILED,
                0,
                "Nenhum dado extraído do documento",
            )
            logger.error(f"Nenhum dado extraído para o exame {exame_id}")
            
            # Notificar erro no lote se houver
            try:
                coerced_id = uuid.UUID(exame_id) if isinstance(exame_id, str) else exame_id
                exame = exame_repo.get_exame(self.db, coerced_id)
                if exame and exame.batch_id:
                    batch, just_completed = exame_repo.update_batch_progress(self.db, exame.batch_id, success=False)
                    if batch and just_completed and batch.webhook_url:
                        webhook_service.send_notification_sync(
                            batch.webhook_url,
                            {
                                "batch_id": str(batch.id),
                                "status": "concluido_com_erros",
                                "total_files": batch.total_files,
                                "failed_files": batch.failed_files,
                                "patient_id": batch.patient_id,
                            }
                        )
            except:
                pass

    except Exception as e:
        logger.exception(f"Erro ao processar exame {exame_id}: {e}")
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.FAILED,
            0,
            f"Erro no processamento: {str(e)}",
        )

        # Enviar Webhook de Erro
        try:
            coerced_id = uuid.UUID(exame_id) if isinstance(exame_id, str) else exame_id
            exame = exame_repo.get_exame(self.db, coerced_id)
            if exame and exame.webhook_url:
                webhook_service.send_notification_sync(
                    exame.webhook_url,
                    {
                        "exame_id": str(exame_id),
                        "status": "erro",
                        "error_message": str(e),
                        "patient_id": exame.patient_id,
                    }
                )
            
            # Notificar erro no lote se houver
            if exame and exame.batch_id:
                batch, just_completed = exame_repo.update_batch_progress(self.db, exame.batch_id, success=False)
                if batch and just_completed and batch.webhook_url:
                    webhook_service.send_notification_sync(
                        batch.webhook_url,
                        {
                            "batch_id": str(batch.id),
                            "status": "concluido_com_erros",
                            "total_files": batch.total_files,
                            "failed_files": batch.failed_files,
                            "patient_id": batch.patient_id,
                        }
                    )
        except Exception as webhook_error:
            logger.error(f"Erro ao enviar webhook de erro: {webhook_error}")

        raise e

    finally:
        # Limpar arquivo temporário
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo temporário removido: {file_path}")
