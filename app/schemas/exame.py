from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID


class ExameResponse(BaseModel):
    """Resumo de um exame processado."""

    id: UUID = Field(description="UUID do exame")
    patient_id: int = Field(description="ID do paciente no Storge")
    data_coleta: Optional[date] = Field(None, description="Data da coleta do exame")
    laboratorio: Optional[str] = Field(None, description="Nome do laboratório")
    status_processamento: str = Field(
        description="Status: pendente | processando | concluido | erro"
    )
    url_documento: str = Field(description="Caminho do arquivo PDF")

    # Progress tracking fields
    processing_stage: Optional[str] = Field(
        None,
        description="Estágio atual do processamento",
    )
    processing_percent: Optional[int] = Field(
        None,
        description="Percentual de progresso (0-100)",
        ge=0,
        le=100,
    )
    processing_message: Optional[str] = Field(
        None,
        description="Mensagem descritiva do progresso",
    )

    has_summary: bool = Field(
        False,
        description="Indica se o exame possui resumo clínico gerado",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "patient_id": 42,
                "data_coleta": "2026-02-10",
                "laboratorio": "Laboratório São Paulo",
                "status_processamento": "concluido",
                "url_documento": "uploads/abc123.pdf",
                "processing_stage": "completed",
                "processing_percent": 100,
                "processing_message": "Processamento concluído - 15 biomarcadores extraídos",
            }
        }


class ResultadoBiomarcadorResponse(BaseModel):
    """Resultado de um biomarcador individual extraído pelo OCR.

    Inclui campos normalizados para parsing determinístico e
    metadados de confiança/correção.
    """

    id: UUID = Field(description="UUID do resultado")

    # Identificação
    nome_marcador: str = Field(description="Nome do biomarcador (normalizado)")

    # Valores (para exibição)
    valor_extraido: Optional[str] = Field(
        None, description="Valor formatado para exibição"
    )
    unidade_medida: Optional[str] = Field(
        None, description="Unidade normalizada (ex: /mm³, %)"
    )

    # Referência
    referencia_lab: Optional[str] = Field(
        None, description="Referência original do laboratório"
    )
    referencia_min: Optional[float] = Field(
        None, description="Valor mínimo da referência parseada"
    )
    referencia_max: Optional[float] = Field(
        None, description="Valor máximo da referência parseada"
    )

    # Classificação
    status_alerta: Optional[str] = Field(
        None, description="Classificação: normal | alto | baixo | indefinido"
    )

    # Metadados de normalização
    tipo_valor: Optional[str] = Field(
        None, description="Tipo: absoluto | percentual | textual"
    )
    valor_raw: Optional[str] = Field(
        None, description="Valor original extraído pelo OCR"
    )
    valor_numerico: Optional[float] = Field(
        None, description="Valor numérico para cálculos"
    )
    fonte_valor: Optional[str] = Field(
        None, description="Fonte: ocr | calculado | corrigido"
    )

    # Qualidade
    needs_review: bool = Field(False, description="Requer revisão manual")
    correcao_aplicada: Optional[str] = Field(
        None, description="Descrição da correção aplicada"
    )
    confianca: float = Field(1.0, description="Nível de confiança (0.0 a 1.0)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "f1e2d3c4-b5a6-7890-fedc-ba0987654321",
                "nome_marcador": "SEGMENTADOS",
                "valor_extraido": "49.0",
                "unidade_medida": "%",
                "referencia_lab": "40,0 a 75,0 %",
                "referencia_min": 40.0,
                "referencia_max": 75.0,
                "status_alerta": "normal",
                "tipo_valor": "percentual",
                "valor_raw": "49,0 %",
                "valor_numerico": 49.0,
                "fonte_valor": "ocr",
                "needs_review": False,
                "correcao_aplicada": None,
                "confianca": 1.0,
            }
        }


class DetalheExameResponse(BaseModel):
    """Detalhes completos de um exame com seus biomarcadores extraídos."""

    id: UUID = Field(description="UUID do exame")
    patient_id: int = Field(description="ID do paciente no Storge")
    data_coleta: Optional[date] = Field(None, description="Data da coleta")
    laboratorio: Optional[str] = Field(None, description="Laboratório")
    status_processamento: str = Field(description="Status do processamento OCR")
    resultados: List[ResultadoBiomarcadorResponse] = Field(
        description="Biomarcadores extraídos"
    )

    # Progress tracking fields
    processing_stage: Optional[str] = Field(
        None,
        description="Estágio atual do processamento",
    )
    processing_percent: Optional[int] = Field(
        None,
        description="Percentual de progresso (0-100)",
        ge=0,
        le=100,
    )
    processing_message: Optional[str] = Field(
        None,
        description="Mensagem descritiva do progresso",
    )

    has_summary: bool = Field(
        False,
        description="Indica se o exame possui resumo clínico gerado",
    )

    class Config:
        from_attributes = True


class ExameListResponse(BaseModel):
    """Lista paginada de exames de um paciente."""

    items: List[ExameResponse] = Field(description="Exames da página atual")
    total: int = Field(description="Total de exames do paciente")
    page: int = Field(description="Página atual")
    pages: int = Field(description="Total de páginas")

    class Config:
        json_schema_extra = {
            "example": {"items": [], "total": 0, "page": 1, "pages": 0}
        }


class ExameStatusResponse(BaseModel):
    """Status de processamento de um exame (para polling)."""

    status: str = Field(
        description="Status atual: pendente | processando | concluido | erro"
    )
    processing_stage: Optional[str] = Field(
        None,
        description="Estágio atual: queued | downloading | ocr_extracting | ai_analyzing | normalizing | completed | failed",
    )
    processing_percent: Optional[int] = Field(
        None,
        description="Progresso de 0-100%",
        ge=0,
        le=100,
    )
    processing_message: Optional[str] = Field(
        None,
        description="Mensagem descritiva do progresso atual",
    )
    has_summary: bool = Field(
        False,
        description="Indica se o exame possui resumo clínico gerado",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processando",
                "processing_stage": "ai_analyzing",
                "processing_percent": 50,
                "processing_message": "Analisando biomarcadores com IA",
                "has_summary": False,
            }
        }


# Schema para input de normalização (uso interno)
class BiomarcadorNormalizadoInput(BaseModel):
    """Input para normalização de biomarcador."""

    nome_marcador: str
    valor_raw: str
    unidade_raw: Optional[str] = None
    referencia_raw: Optional[str] = None
    contexto: Optional[dict] = None


class BiomarcadorNormalizadoOutput(BaseModel):
    """Output da normalização de biomarcador."""

    nome_marcador_normalizado: str
    valor_raw: Optional[str] = None
    valor_numerico: Optional[float] = None
    valor_extraido: Optional[str] = None
    tipo_valor: str
    unidade_medida_normalizada: Optional[str] = None
    referencia_min: Optional[float] = None
    referencia_max: Optional[float] = None
    status_alerta: str
    needs_review: bool
    correcao_aplicada: Optional[str] = None
    confianca: float
    fonte_valor: str


# ========================================
# Clinical Summary Schemas
# ========================================


class AlertaClinico(BaseModel):
    """Alerta individual de um biomarcador."""

    biomarcador: str = Field(description="Nome do biomarcador")
    valor: str = Field(description="Valor encontrado")
    referencia: str = Field(description="Intervalo de referência")
    severidade: str = Field(
        description="Severidade: critico | atencao | normal",
    )
    descricao: str = Field(description="Explicação do significado clínico")


class ClinicalSummaryResponse(BaseModel):
    """Resumo clínico gerado pela IA."""

    resumo_geral: str = Field(description="Visão geral dos resultados em 2-3 frases")
    alertas: List[AlertaClinico] = Field(
        default_factory=list,
        description="Lista de alertas por biomarcador",
    )
    recomendacoes: List[str] = Field(
        default_factory=list,
        description="Ações práticas baseadas nos resultados",
    )
    destilacoes: List[str] = Field(
        default_factory=list,
        description="Insights importantes que o paciente deve saber",
    )
    proximos_passos: List[str] = Field(
        default_factory=list,
        description="Sugestões de acompanhamento médico",
    )
    generated_at: Optional[datetime] = Field(
        None, description="Data e hora da geração do resumo"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "resumo_geral": "O hemograma apresenta alterações nos leucócitos...",
                "alertas": [
                    {
                        "biomarcador": "LEUCÓCITOS",
                        "valor": "12000",
                        "referencia": "4000-10000",
                        "severidade": "atencao",
                        "descricao": "Leve leucocitose pode indicar processo inflamatório",
                    }
                ],
                "recomendacoes": ["Acompanhamento com médico clínico geral"],
                "destilacoes": ["Os valores alterados podem ser temporários"],
                "proximos_passos": ["Repetir exame em 15 dias se sintomas persistirem"],
                "generated_at": "2026-02-21T10:30:00Z",
            }
        }
