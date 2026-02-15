from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.ai_service import AIService
from app.repositories.exame_repo import ExameRepository
from typing import Dict, Any
import logging

# Configure logger
logger = logging.getLogger(__name__)

class DatabaseTask(Task):
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._db:
            self._db.close()

# Instantiate services
ai_service = AIService()
exame_repo = ExameRepository()

@celery_app.task(
    base=DatabaseTask, 
    bind=True, 
    name="processar_exame_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def processar_exame_task(self, exame_id: str, file_path: str):
    logger.info(f"Iniciando processamento do exame {exame_id}")
    try:
        # 1. Update status to 'processando'
        exame_repo.update_status(self.db, exame_id, "processando")
        
        # 2. Extract data using AI
        dados_extraidos = ai_service.extrair_dados_exame(file_path)
        
        # 3. Save results
        if dados_extraidos and 'resultados' in dados_extraidos:
            for resultado in dados_extraidos['resultados']:
                exame_repo.add_resultado(self.db, exame_id, resultado)
            
            exame_repo.update_status(self.db, exame_id, "concluido")
            logger.info(f"Exame {exame_id} concluído com sucesso")
        else:
            exame_repo.update_status(self.db, exame_id, "erro")
            logger.error(f"Nenhum dado extraído para o exame {exame_id}")

    except Exception as e:
        logger.exception(f"Erro ao processar exame {exame_id}: {e}")
        exame_repo.update_status(self.db, exame_id, "erro")
        raise e