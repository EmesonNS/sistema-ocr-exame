from sqlalchemy.orm import Session
from app.models import Exame, ResultadoBiomarcador
import uuid
from datetime import date

class ExameRepository:
    def create_exame(self, db: Session, paciente_id: uuid.UUID, url_documento: str):
        novo_exame = Exame(
            paciente_id=paciente_id,
            url_documento=url_documento,
            status_processamento="pendente"
        )
        db.add(novo_exame)
        db.commit()
        db.refresh(novo_exame)
        return novo_exame

    def get_exame(self, db: Session, exame_id: uuid.UUID):
        return db.query(Exame).filter(Exame.id == exame_id).first()

    def list_by_paciente(self, db: Session, paciente_id: uuid.UUID):
        return db.query(Exame).filter(Exame.paciente_id == paciente_id).all()

    def update_exame_status(self, db: Session, exame_id: uuid.UUID, status: str, laboratorio: str = None, data_coleta: date = None):
        exame = self.get_exame(db, exame_id)
        if exame:
            exame.status_processamento = status
            if laboratorio:
                exame.laboratorio = laboratorio
            if data_coleta:
                exame.data_coleta = data_coleta
            db.commit()
            db.refresh(exame)
        return exame

    def add_resultado(self, db: Session, resultado: ResultadoBiomarcador):
        db.add(resultado)
        db.commit()