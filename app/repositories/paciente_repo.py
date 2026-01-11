from sqlalchemy.orm import Session
from app.models import Paciente
from app.schemas import PacienteCreate
import uuid

class PacienteRepository:
    def get_by_cpf(self, db: Session, cpf: str):
        return db.query(Paciente).filter(Paciente.cpf == cpf).first()

    def get_by_id(self, db: Session, paciente_id: uuid.UUID):
        return db.query(Paciente).filter(Paciente.id == paciente_id).first()

    def list_all(self, db: Session):
        return db.query(Paciente).all()

    def create(self, db: Session, paciente: PacienteCreate):
        db_paciente = Paciente(
            nome=paciente.nome,
            cpf=paciente.cpf,
            data_nascimento=paciente.data_nascimento,
            sexo_biologico=paciente.sexo_biologico
        )
        db.add(db_paciente)
        db.commit()
        db.refresh(db_paciente)
        return db_paciente