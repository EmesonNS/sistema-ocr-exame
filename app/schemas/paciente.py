from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from uuid import UUID

class PacienteCreate(BaseModel):
    nome: str
    cpf: str
    data_nascimento: Optional[date] = None
    sexo_biologico: Optional[str] = Field(None, pattern="^[MF]$")

    class Config:
        from_attributes = True

class PacienteResponse(BaseModel):
    id: UUID
    nome: str
    cpf: str
    data_nascimento: Optional[date] = None
    sexo_biologico: Optional[str] = None

    class Config:
        from_attributes = True