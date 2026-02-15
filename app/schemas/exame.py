from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from uuid import UUID

class ExameResponse(BaseModel):
    """Resumo de um exame processado."""
    id: UUID = Field(description="UUID do exame")
    patient_id: int = Field(description="ID do paciente no Storge")
    data_coleta: Optional[date] = Field(None, description="Data da coleta do exame")
    laboratorio: Optional[str] = Field(None, description="Nome do laboratório")
    status_processamento: str = Field(description="Status: pendente | processando | concluido | erro")
    url_documento: str = Field(description="Caminho do arquivo PDF")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "patient_id": 42,
                "data_coleta": "2026-02-10",
                "laboratorio": "Laboratório São Paulo",
                "status_processamento": "concluido",
                "url_documento": "uploads/abc123.pdf"
            }
        }

class ResultadoBiomarcadorResponse(BaseModel):
    """Resultado de um biomarcador individual extraído pelo OCR."""
    id: UUID = Field(description="UUID do resultado")
    nome_marcador: str = Field(description="Nome do biomarcador (ex: Colesterol Total)")
    valor_extraido: float = Field(description="Valor numérico extraído")
    unidade_medida: Optional[str] = Field(None, description="Unidade de medida (ex: mg/dL)")
    referencia_lab: Optional[str] = Field(None, description="Faixa de referência do laboratório")
    status_alerta: Optional[str] = Field(None, description="Classificação: normal | alto | baixo")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "f1e2d3c4-b5a6-7890-fedc-ba0987654321",
                "nome_marcador": "Colesterol Total",
                "valor_extraido": 195.0,
                "unidade_medida": "mg/dL",
                "referencia_lab": "< 190 mg/dL",
                "status_alerta": "alto"
            }
        }

class DetalheExameResponse(BaseModel):
    """Detalhes completos de um exame com seus biomarcadores extraídos."""
    id: UUID = Field(description="UUID do exame")
    patient_id: int = Field(description="ID do paciente no Storge")
    data_coleta: Optional[date] = Field(None, description="Data da coleta")
    laboratorio: Optional[str] = Field(None, description="Laboratório")
    status_processamento: str = Field(description="Status do processamento OCR")
    resultados: List[ResultadoBiomarcadorResponse] = Field(description="Biomarcadores extraídos")

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
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "pages": 0
            }
        }

class ExameStatusResponse(BaseModel):
    """Status de processamento de um exame (para polling)."""
    status: str = Field(description="Status atual: pendente | processando | concluido | erro")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processando"
            }
        }