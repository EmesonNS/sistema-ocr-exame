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
from app.services.interoperability_service import InteroperabilityService
from app.services.biomarker_normalization import normalizar_resultado_biomarcador
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
interoperability_service = InteroperabilityService()
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
            # Mapeamento LOINC (Fase 7)
            for res in resultados:
                res["loinc_code"] = interoperability_service.map_to_loinc(
                    res.get("nome_marcador_normalizado")
                )
                exame_repo.add_resultado_normalizado(self.db, exame_id, res)

            # 7.1 Agentic Loop: Re-inspeção de valores suspeitos (Fase 7)
            suspeitos = [r for r in resultados if r.get("needs_review") and r.get("bounding_box")]
            if suspeitos:
                logger.info(f"Fase 7: {len(suspeitos)} biomarcadores suspeitos detectados. Iniciando Agentic Loop.")
                for res in suspeitos:
                    try:
                        # Executa re-extração focada
                        re_inspecao = asyncio.run(
                            ai_service.focar_extracao(
                                file_path=file_path,
                                page_number=res.get("page_number", 1),
                                bounding_box=res.get("bounding_box"),
                                nome_marcador=res.get("nome_marcador_normalizado")
                            )
                        )
                        
                        if re_inspecao and re_inspecao.get("valor_raw"):
                            logger.info(f"Re-inspeção concluída para {res.get('nome_marcador_normalizado')}. Novo valor: {re_inspecao['valor_raw']}")
                            
                            # Se o valor mudou, aplicamos re-normalização determinística (Fase 7.1)
                            if re_inspecao["valor_raw"] != res["valor_raw"]:
                                # Re-normalizar usando a camada determinística
                                normalizado_novo = normalizar_resultado_biomarcador(
                                    nome_marcador=res.get("nome_marcador_normalizado"),
                                    valor_raw=re_inspecao["valor_raw"],
                                    unidade_raw=res.get("unidade_medida_normalizada"),
                                    referencia_raw=res.get("referencia_lab"),
                                    contexto={} # Contexto pode ser expandido se necessário
                                )

                                # Atualiza o objeto de resultado com os novos valores processados
                                res["correcao_aplicada"] = (
                                    f"{res.get('correcao_aplicada', '')} | "
                                    f"Agentic Loop: Valor original '{res['valor_raw']}' corrigido para '{re_inspecao['valor_raw']}' após zoom."
                                )
                                res["valor_raw"] = re_inspecao["valor_raw"]
                                res["valor_numerico"] = normalizado_novo.get("valor_numerico")
                                res["valor_extraido"] = normalizado_novo.get("valor_extraido")
                                res["status_alerta"] = normalizado_novo.get("status_alerta")
                                res["confianca"] = max(res.get("confianca", 0), re_inspecao.get("confianca_reinspecao", 0))
                                
                                # Persistir atualização no banco
                                exame_repo.update_resultado_reinspecionado(self.db, exame_id, res)

                    except Exception as loop_error:
                        logger.error(f"Erro no Agentic Loop para {res.get('nome_marcador_normalizado')}: {loop_error}")

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
