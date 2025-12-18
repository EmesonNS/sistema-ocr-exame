from sqlalchemy import Column, String, Float, Date, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .database import Base

class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, index=True, nullable=False)
    data_nascimento = Column(Date)
    sexo_biologico = Column(String)

    exames = relationship("Exame", back_populates="paciente")

class Exame(Base):
    __tablename__ = "exames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id"))
    data_coleta = Column(Date)
    laboratorio = Column(String)
    url_documento = Column(String)
    status_processamento = Column(String, default="pendente")

    paciente = relationship("Paciente", back_populates="exames")
    resultados = relationship("ResultadoBiomarcador", back_populates="exame")

class ResultadoBiomarcador(Base):
    __tablename__ = "resultados_biomarcadores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exame_id = Column(UUID(as_uuid=True), ForeignKey("exames.id"))
    nome_marcador = Column(String, nullable=False)
    valor_extraido = Column(Float)
    unidade_medida = Column(String)
    referencia_lab = Column(String)
    status_alerta = Column(String)

    exame = relationship("Exame", back_populates="resultados")