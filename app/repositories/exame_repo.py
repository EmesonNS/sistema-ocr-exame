"""
Repository para operações de banco de dados relacionadas a exames.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.exame import Exame, ResultadoBiomarcador, ProcessingStage
from typing import List, Tuple, Optional
import uuid
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class ExameRepository:
    """Repository para gerenciar exames e resultados de biomarcadores."""

    def _coerce_exame_id(self, exame_id) -> uuid.UUID | None:
        if isinstance(exame_id, uuid.UUID):
            return exame_id

        if isinstance(exame_id, str):
            try:
                return uuid.UUID(exame_id)
            except ValueError:
                return None

        return None

    def _parse_data_coleta(self, data_coleta: str) -> date | None:
        if not data_coleta:
            return None

        normalized = data_coleta.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        return None

    def create_exame(
        self, db: Session, patient_id: int, user_id: int, file_path: str
    ) -> Exame:
        """Cria um novo exame."""
        db_exame = Exame(
            patient_id=patient_id,
            uploaded_by_user_id=user_id,
            url_documento=file_path,
            status_processamento="pendente",
        )
        db.add(db_exame)
        db.commit()
        db.refresh(db_exame)
        return db_exame

    def get_exame(self, db: Session, exame_id: uuid.UUID) -> Optional[Exame]:
        """Busca exame por ID."""
        return db.query(Exame).filter(Exame.id == exame_id).first()

    def list_by_patient_id(
        self, db: Session, patient_id: int, skip: int = 0, limit: int = 10
    ) -> Tuple[List[Exame], int]:
        """Lista exames por paciente com paginação."""
        query = db.query(Exame).filter(Exame.patient_id == patient_id)
        total = query.count()
        items = query.order_by(desc(Exame.id)).offset(skip).limit(limit).all()
        return items, total

    def update_status(
        self, db: Session, exame_id: uuid.UUID, status: str
    ) -> Optional[Exame]:
        """Atualiza status de processamento do exame."""
        exame = self.get_exame(db, exame_id)
        if exame:
            exame.status_processamento = status
            db.commit()
            db.refresh(exame)
        return exame

    def update_processing_progress(
        self,
        db: Session,
        exame_id,
        stage: str,
        percent: int,
        message: str,
    ) -> Optional[Exame]:
        """
        Atualiza progress information for processing.

        Args:
            db: Database session
            exame_id: UUID of the exam (as string or UUID)
            stage: Processing stage name (queued, downloading, etc.)
            percent: Progress percentage (0-100)
            message: Human-readable progress message

        Returns:
            Updated Exame or None if not found
        """
        # Parse Don't Validate: accept string or UUID
        coerced_id = self._coerce_exame_id(exame_id) or exame_id
        exame = db.query(Exame).filter(Exame.id == coerced_id).first()
        if not exame:
            logger.warning(f"Exame {exame_id} not found for progress update")
            return None

        exame.processing_stage = stage
        exame.processing_percent = percent
        exame.processing_message = message

        # Map stage to status
        if stage == ProcessingStage.COMPLETED:
            exame.status_processamento = "concluido"
        elif stage == ProcessingStage.FAILED:
            exame.status_processamento = "erro"
        elif stage not in (ProcessingStage.QUEUED,):
            exame.status_processamento = "processando"

        db.commit()
        db.refresh(exame)
        logger.info(f"Exame {exame_id}: {stage} ({percent}%) - {message}")
        return exame

    def update_exame_metadata(
        self,
        db: Session,
        exame_id: str,
        data_coleta: Optional[str] = None,
        laboratorio: Optional[str] = None,
    ) -> Optional[Exame]:
        """
        Atualiza metadados do exame.

        Args:
            db: Sessão do banco
            exame_id: UUID do exame (como string)
            data_coleta: Data da coleta (formato string)
            laboratorio: Nome do laboratório

        Returns:
            Exame atualizado ou None se não encontrado
        """
        coerced_id = self._coerce_exame_id(exame_id) or exame_id
        exame = db.query(Exame).filter(Exame.id == coerced_id).first()
        if exame:
            if data_coleta:
                parsed = self._parse_data_coleta(data_coleta)
                if parsed:
                    exame.data_coleta = parsed
                else:
                    logger.warning(
                        f"Data de coleta inválida para exame {exame_id}: {data_coleta}"
                    )
            if laboratorio:
                exame.laboratorio = laboratorio
            db.commit()
            db.refresh(exame)
        return exame

    def add_resultado(
        self, db: Session, exame_id: uuid.UUID, resultado: dict
    ) -> ResultadoBiomarcador:
        """
        Adiciona resultado de biomarcador (método legado).

        Args:
            db: Sessão do banco
            exame_id: UUID do exame
            resultado: Dict com nome, valor, unidade, referencia, status_alerta

        Returns:
            ResultadoBiomarcador criado
        """
        db_resultado = ResultadoBiomarcador(
            exame_id=exame_id,
            nome_marcador=resultado.get("nome"),
            valor_extraido=resultado.get("valor"),
            unidade_medida=resultado.get("unidade"),
            referencia_lab=resultado.get("referencia"),
            status_alerta=resultado.get("status_alerta"),
        )
        db.add(db_resultado)
        db.commit()
        return db_resultado

    def add_resultado_normalizado(
        self, db: Session, exame_id: str, resultado: dict
    ) -> ResultadoBiomarcador:
        """
        Adiciona resultado de biomarcador normalizado.

        Args:
            db: Sessão do banco
            exame_id: UUID do exame (como string)
            resultado: Dict com campos normalizados da camada de normalização

        Returns:
            ResultadoBiomarcador criado
        """
        # Monta string de referência
        ref_min = resultado.get("referencia_min")
        ref_max = resultado.get("referencia_max")
        referencia_lab = ""
        if ref_min is not None and ref_max is not None:
            referencia_lab = f"{ref_min} - {ref_max}"
        elif ref_min is not None:
            referencia_lab = f"> {ref_min}"
        elif ref_max is not None:
            referencia_lab = f"< {ref_max}"

        db_resultado = ResultadoBiomarcador(
            exame_id=exame_id,
            nome_marcador=resultado.get("nome_marcador_normalizado"),
            valor_raw=resultado.get("valor_raw"),
            valor_numerico=resultado.get("valor_numerico"),
            valor_extraido=resultado.get("valor_extraido"),
            tipo_valor=resultado.get("tipo_valor"),
            unidade_medida=resultado.get("unidade_medida_normalizada"),
            referencia_lab=referencia_lab,
            referencia_min=ref_min,
            referencia_max=ref_max,
            status_alerta=resultado.get("status_alerta"),
            needs_review=resultado.get("needs_review", False),
            correcao_aplicada=resultado.get("correcao_aplicada"),
            confianca=resultado.get("confianca", 1.0),
        )
        db.add(db_resultado)
        db.commit()
        return db_resultado
