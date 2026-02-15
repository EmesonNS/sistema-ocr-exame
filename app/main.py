from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import database
from app import models
from app.api.endpoints import exames
from app.core.config import settings

DESCRIPTION = """
## API de OCR para Exames Médicos

Microserviço responsável por processar exames laboratoriais via OCR (Gemini AI)
e extrair biomarcadores automaticamente.

### Autenticação
Todos os endpoints (exceto `/health`) exigem um **JWT válido** emitido pelo `storge-service`.

O token pode ser enviado de duas formas:
- **Header**: `Authorization: Bearer <token>`
- **Cookie**: `auth_token=<token>` (enviado automaticamente pelo frontend com `withCredentials: true`)

### Fluxo de Processamento
1. Upload do PDF → status `pendente`
2. Worker Celery processa com Gemini AI → status `processando`
3. Resultados extraídos → status `concluido` (ou `erro`)

Use o endpoint de **polling** (`GET /exames/{id}/status`) para acompanhar.
"""

app = FastAPI(
    title="Storge OCR Exames API",
    description=DESCRIPTION,
    version="1.0.0",
    contact={
        "name": "Storge Care",
        "url": "https://app.storge.care",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Status da API",
        },
        {
            "name": "Exames",
            "description": "Upload, listagem e detalhes de exames processados por OCR",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exames.router, prefix="/api/v1", tags=["Exames"])

@app.get("/health", tags=["Health"], summary="Health Check")
def health_check():
    """Verifica se a API está online. Não requer autenticação."""
    return {"status": "ok", "version": "1.0.0"}