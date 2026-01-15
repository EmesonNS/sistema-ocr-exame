from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services import ai_service
from app.models.exame import Exame, ResultadoBiomarcador
from app.repositories.exame_repo import ExameRepository
import uuid
from datetime import datetime

exame_repo = ExameRepository()

@celery_app.task(name="processar_exame_task")
def processar_exame_task(exame_id_str: str, file_path: str):
    db: Session = SessionLocal()

    try:
        exame_id = uuid.UUID(exame_id_str)
        print(f"[worker] Iniciando processamento do exame: {exame_id}")

        dados_ia = ai_service.extrair_dados_exame(file_path)

        if "exame" in dados_ia:
            info = dados_ia["exame"]

            data_coleta = None
            if info.get("data"):
                try:
                    data_coleta = datetime.strptime(info.get("data"), "%Y-%m-%d").date()
                except:
                    pass
            
            exame_repo.update_exame_status(
                db,
                exame_id,
                status="concluido",
                laboratorio=info.get("laboratorio"),
                data_coleta=data_coleta
            )

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
                exame_repo.add_resultado(db, resultado)

            print(f"[worker] Exame {exame_id} concluído com sucesso.")
    except Exception as e:
        print(f"[Worker] Erro ao processar exame {exame_id_str}: {e}")
        exame_repo.update_exame_status(db, uuid.UUID(exame_id_str), "erro")
    finally:
        db.close()