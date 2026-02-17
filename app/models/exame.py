import uuid
from sqlalchemy import Column, String, Float, Date, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Exame(Base):
    __tablename__ = "exames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(BigInteger, nullable=False, index=True) # External FK to storge_app.patients.id
    uploaded_by_user_id = Column(BigInteger, nullable=False) # External FK to storge_app.users.id
    data_coleta = Column(Date)
    laboratorio = Column(String)
    url_documento = Column(String)
    status_processamento = Column(String, default="pendente")

    # paciente relationship removed
    resultados = relationship("ResultadoBiomarcador", back_populates="exame")

class ResultadoBiomarcador(Base):
    __tablename__ = "resultados_biomarcadores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exame_id = Column(UUID(as_uuid=True), ForeignKey("exames.id"))
    nome_marcador = Column(String, nullable=False)
    valor_extraido = Column(String)
    unidade_medida = Column(String)
    referencia_lab = Column(String)
    status_alerta = Column(String)

    exame = relationship("Exame", back_populates="resultados")