from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from uuid import UUID

class ExameResponse(BaseModel):
    id: UUID
    paciente_id: UUID
    data_coleta: Optional[date]
    laboratorio: Optional[str]
    status_processamento: str
    url_documento: str

    class Config:
        from_attributes = True

class ResultadoBiomarcadorResponse(BaseModel):
    id: UUID
    nome_marcador: str
    valor_extraido: float
    unidade_medida: Optional[str]
    referencia_lab: Optional[str]
    status_alerta: Optional[str]

    class Config:
        from_attributes = True

class DetalheExameResponse(BaseModel):
    id: UUID
    data_coleta: Optional[date]
    laboratorio: Optional[str]
    status_processamento: str
    resultados: List[ResultadoBiomarcadorResponse]

    class Config:
        from_attributes = True