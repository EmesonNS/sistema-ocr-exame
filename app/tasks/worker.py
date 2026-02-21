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
exame_repo = ExameRepository()


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name="processar_exame_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def processar_exame_task(self, exame_id: str, file_path: str):
    """
    Processa exame assincronamente.

    Args:
        exame_id: UUID do exame
        file_path: Caminho do arquivo temporário
    """
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

        # 2. Downloading (10%) - arquivo already downloaded,
        # This is where the file was saved before triggering the task
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

        # 4. AI Analyzing (50%) - extract data using AI
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.AI_ANALYZING,
            50,
            "Analisando biomarcadores com IA",
        )

        # Extract data using AI com normalização
        resultados, data_coleta, laboratorio = ai_service.extrair_biomarcadores(
            file_path
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
                exame_id=exame_id,
                data_coleta=data_coleta,
                laboratorio=laboratorio,
            )

        # 7. Salvar resultados normalizados
        if resultados:
            for resultado in resultados:
                exame_repo.add_resultado_normalizado(self.db, exame_id, resultado)

            try:
                exame_repo.update_processing_progress(
                    self.db,
                    exame_id,
                    ProcessingStage.NORMALIZING,
                    90,
                    "Gerando resumo clínico",
                )

                coerced_id = None
                try:
                    coerced_id = uuid.UUID(exame_id)
                except ValueError:
                    coerced_id = None

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
        else:
            exame_repo.update_processing_progress(
                self.db,
                exame_id,
                ProcessingStage.FAILED,
                0,
                "Nenhum dado extraído do documento",
            )
            logger.error(f"Nenhum dado extraído para o exame {exame_id}")

    except Exception as e:
        logger.exception(f"Erro ao processar exame {exame_id}: {e}")
        exame_repo.update_processing_progress(
            self.db,
            exame_id,
            ProcessingStage.FAILED,
            0,
            f"Erro no processamento: {str(e)}",
        )
        raise e

    finally:
        # Limpar arquivo temporário
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo temporário removido: {file_path}")
