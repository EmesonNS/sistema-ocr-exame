import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    BigInteger,
    ForeignKey,
    Numeric,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.sa_types import GUID


class ProcessingStage:
    """Estágios do processamento de exame."""

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    OCR_EXTRACTING = "ocr_extracting"
    AI_ANALYZING = "ai_analyzing"
    NORMALIZING = "normalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExameBatch(Base):
    """Agrupamento de múltiplos exames para processamento em lote."""

    __tablename__ = "exame_batches"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id = Column(BigInteger, nullable=False, index=True)
    status = Column(String(20), default="pendente")  # pendente | processando | concluido | erro
    created_at = Column(DateTime, default=datetime.utcnow)
    webhook_url = Column(String, nullable=True)
    
    total_files = Column(Integer, default=0)
    completed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)

    exames = relationship("Exame", back_populates="batch")


class Exame(Base):
    __tablename__ = "exames"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id = Column(BigInteger, nullable=False, index=True)
    uploaded_by_user_id = Column(BigInteger, nullable=False)
    data_coleta = Column(Date)
    laboratorio = Column(String)
    url_documento = Column(String)
    status_processamento = Column(String, default="pendente")
    webhook_url = Column(String, nullable=True)
    is_digitally_signed = Column(Boolean, default=False)
    batch_id = Column(GUID(), ForeignKey("exame_batches.id"), nullable=True)

    # Progress tracking fields
    processing_stage = Column(String(50), nullable=True)
    processing_percent = Column(Integer, nullable=True)
    processing_message = Column(String(500), nullable=True)

    # Clinical summary fields (added by migration 005)
    clinical_summary = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    summary_generated_at = Column(DateTime(timezone=True), nullable=True)

    resultados = relationship("ResultadoBiomarcador", back_populates="exame")
    batch = relationship("ExameBatch", back_populates="exames")

    @property
    def has_summary(self) -> bool:
        return self.clinical_summary is not None


class ResultadoBiomarcador(Base):
    """Resultado de um biomarcador extraído de exame de laboratório.

    Campos normalizados pela camada de biomarker_normalization para
    garantir parsing determinístico e correção de erros de OCR.
    """

    __tablename__ = "resultados_biomarcadores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    exame_id = Column(GUID(), ForeignKey("exames.id"))

    # Identificação do marcador
    nome_marcador = Column(String, nullable=False)

    # Campos originais (para referência e debug)
    valor_extraido = Column(String(100), nullable=True)  # Valor formatado para exibição
    referencia_lab = Column(String(200), nullable=True)  # Referência original do lab

    # Campos normalizados (pela camada de normalização)
    valor_raw = Column(String(200), nullable=True)  # Valor original do OCR
    valor_numerico = Column(
        Numeric(10, 4), nullable=True
    )  # Para cálculos e comparações
    tipo_valor = Column(
        String(20), nullable=True
    )  # 'absoluto', 'percentual', 'textual'
    unidade_medida = Column(String(50), nullable=True)  # Normalizada (ex: "/mm³", "%")

    # Referência parseada
    referencia_min = Column(Numeric(10, 4), nullable=True)
    referencia_max = Column(Numeric(10, 4), nullable=True)

    # Classificação e metadados
    status_alerta = Column(
        String(20), default="indefinido"
    )  # 'baixo', 'normal', 'alto', 'indefinido'
    needs_review = Column(Boolean, default=False)  # Requer revisão manual
    correcao_aplicada = Column(String(500), nullable=True)  # Descrição da correção
    confianca = Column(Float, default=1.0)  # 0.0 a 1.0
    fonte_valor = Column(String(50), default="ocr")  # 'ocr', 'calculado', 'corrigido'

    exame = relationship("Exame", back_populates="resultados")
