"""
Repository para operações de banco de dados relacionadas a exames.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.exame import Exame, ResultadoBiomarcador, ProcessingStage, ExameBatch
from typing import List, Tuple, Optional
import uuid
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class ExameRepository:
    """Repository para gerenciar exames e resultados de biomarcadores."""

    def _coerce_uuid(self, obj_id) -> uuid.UUID | None:
        if isinstance(obj_id, uuid.UUID):
            return obj_id

        if isinstance(obj_id, str):
            try:
                return uuid.UUID(obj_id)
            except ValueError:
                return None

        return None

    def _coerce_exame_id(self, exame_id) -> uuid.UUID | None:
        return self._coerce_uuid(exame_id)

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
        self, db: Session, patient_id: int, user_id: int, file_path: str, webhook_url: Optional[str] = None, is_digitally_signed: bool = False, batch_id: Optional[uuid.UUID] = None
    ) -> Exame:
        """Cria um novo exame."""
        db_exame = Exame(
            patient_id=patient_id,
            uploaded_by_user_id=user_id,
            url_documento=file_path,
            status_processamento="pendente",
            webhook_url=webhook_url,
            is_digitally_signed=is_digitally_signed,
            batch_id=batch_id,
        )
        db.add(db_exame)
        db.commit()
        db.refresh(db_exame)
        return db_exame

    def create_batch(self, db: Session, patient_id: int, total_files: int, webhook_url: Optional[str] = None) -> ExameBatch:
        """Cria um novo lote de exames."""
        batch = ExameBatch(
            patient_id=patient_id,
            total_files=total_files,
            webhook_url=webhook_url,
            status="processando"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    def get_batch(self, db: Session, batch_id: uuid.UUID) -> Optional[ExameBatch]:
        """Busca lote por ID."""
        return db.query(ExameBatch).filter(ExameBatch.id == batch_id).first()

    def update_batch_progress(self, db: Session, batch_id: uuid.UUID, success: bool = True) -> Tuple[Optional[ExameBatch], bool]:
        """
        Atualiza o progresso do lote de forma atômica.
        Retorna (batch, just_completed_flag).
        """
        from sqlalchemy import update
        
        # 1. Incremento Atômico
        field = ExameBatch.completed_files if success else ExameBatch.failed_files
        stmt = (
            update(ExameBatch)
            .where(ExameBatch.id == batch_id)
            .values({field: field + 1})
        )
        db.execute(stmt)
        db.commit()

        # 2. Verificar se este worker finalizou o lote
        # Usamos uma transação para mudar o status de 'processando' para 'concluido'
        # apenas UMA VEZ. O worker que conseguir fazer o update do status para 'concluido'
        # será o responsável por disparar o webhook.
        batch = self.get_batch(db, batch_id)
        if not batch:
            return None, False
        
        just_completed = False
        if (batch.completed_files + batch.failed_files >= batch.total_files) and batch.status == "processando":
            # Tentar marcar como concluído de forma atômica
            stmt_status = (
                update(ExameBatch)
                .where(ExameBatch.id == batch_id)
                .where(ExameBatch.status == "processando") # Garantia de concorrência
                .values(status="concluido")
            )
            result = db.execute(stmt_status)
            db.commit()
            
            # Se rowcount > 0, este worker foi o vencedor
            if result.rowcount > 0:
                just_completed = True
                db.refresh(batch)
            
        return batch, just_completed

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
            page_number=resultado.get("page_number"),
            bounding_box=resultado.get("bounding_box"),
            loinc_code=resultado.get("loinc_code"),
        )
        db.add(db_resultado)
        db.commit()
        return db_resultado

    def update_resultado_reinspecionado(self, db: Session, exame_id: str, resultado_dict: dict):
        """Atualiza a nota de re-inspeção em um resultado existente."""
        coerced_id = self._coerce_exame_id(exame_id) or exame_id
        db_res = db.query(ResultadoBiomarcador).filter(
            ResultadoBiomarcador.exame_id == coerced_id,
            ResultadoBiomarcador.nome_marcador == resultado_dict.get("nome_marcador_normalizado")
        ).first()
        
        if db_res:
            db_res.correcao_aplicada = resultado_dict.get("correcao_aplicada")
            db_res.valor_raw = resultado_dict.get("valor_raw")
            db_res.valor_numerico = resultado_dict.get("valor_numerico")
            db_res.valor_extraido = resultado_dict.get("valor_extraido")
            db_res.status_alerta = resultado_dict.get("status_alerta")
            db_res.confianca = resultado_dict.get("confianca", 1.0)
            db.commit()
            db.refresh(db_res)
        return db_res

    def get_resultado(self, db: Session, resultado_id: uuid.UUID) -> Optional[ResultadoBiomarcador]:
        """Busca um resultado de biomarcador por ID."""
        return db.query(ResultadoBiomarcador).filter(ResultadoBiomarcador.id == resultado_id).first()

    def verify_resultado(self, db: Session, resultado_id: uuid.UUID) -> Optional[ResultadoBiomarcador]:
        """Marca um resultado como verificado por um humano."""
        db_res = self.get_resultado(db, resultado_id)
        if db_res:
            db_res.is_human_verified = True
            db_res.verified_at = datetime.utcnow()
            db.commit()
            db.refresh(db_res)
        return db_res
