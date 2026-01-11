from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import database
from app import models
from app.api.endpoints import pacientes, exames

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Sistema OCR Exames - Arquitetura Limpa")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Pacientes"])
app.include_router(exames.router, prefix="/api/v1", tags=["Exames"])

@app.get("/health")
def health_check():
    return {"status": "api running", "version": "1.0.0"}