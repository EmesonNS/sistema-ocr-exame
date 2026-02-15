from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.exame import Exame, ResultadoBiomarcador
from typing import List, Tuple
import uuid

class ExameRepository:
    def create_exame(self, db: Session, patient_id: int, user_id: int, file_path: str):
        db_exame = Exame(
            patient_id=patient_id,
            uploaded_by_user_id=user_id,
            url_documento=file_path,
            status_processamento="pendente"
        )
        db.add(db_exame)
        db.commit()
        db.refresh(db_exame)
        return db_exame

    def get_exame(self, db: Session, exame_id: uuid.UUID):
        return db.query(Exame).filter(Exame.id == exame_id).first()

    def list_by_patient_id(self, db: Session, patient_id: int, skip: int = 0, limit: int = 10) -> Tuple[List[Exame], int]:
        query = db.query(Exame).filter(Exame.patient_id == patient_id)
        total = query.count()
        items = query.order_by(desc(Exame.id)).offset(skip).limit(limit).all()
        return items, total

    def update_status(self, db: Session, exame_id: uuid.UUID, status: str):
        exame = self.get_exame(db, exame_id)
        if exame:
            exame.status_processamento = status
            db.commit()
            db.refresh(exame)
        return exame

    def add_resultado(self, db: Session, exame_id: uuid.UUID, resultado: dict):
        db_resultado = ResultadoBiomarcador(
            exame_id=exame_id,
            nome_marcador=resultado.get('nome'),
            valor_extraido=resultado.get('valor'),
            unidade_medida=resultado.get('unidade'),
            referencia_lab=resultado.get('referencia'),
            status_alerta=resultado.get('status_alerta')
        )
        db.add(db_resultado)
        db.commit()
        return db_resultado