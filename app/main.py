from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core import database
from app import models
from app.api.endpoints import exames, api_keys
from app.core.config import settings

DESCRIPTION = """
## API de OCR para Exames Médicos

Microserviço responsável por processar exames laboratoriais via OCR (IA)
e extrair biomarcadores automaticamente.

### Autenticação
Todos os endpoints (exceto `/health`) exigem uma **API Key** válida.

Envie a API Key no header:
```
X-API-Key: sua-chave-aqui
```

### Gerenciamento de API Keys
Os endpoints de gerenciamento de API Keys (`/api/v1/api-keys/*`) permitem:
- Criar novas chaves para clientes
- Listar chaves existentes
- Revogar/reativar chaves

**Nota**: Esses endpoints devem ser protegidos por firewall ou rede privada,
já que permitem criar novas chaves de acesso.

### Fluxo de Processamento
1. Upload do PDF → status `pendente`
2. Worker Celery processa com IA → status `processando`
3. Resultados extraídos → status `concluido` (ou `erro`)

Use o endpoint de **polling** (`GET /exames/{id}/status`) para acompanhar.
"""


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Storge OCR Exames API",
        version="1.0.0",
        description=DESCRIPTION,
        routes=app.routes,
        contact={
            "name": "Storge Care",
            "url": "https://app.storge.care",
        },
    )

    # Adiciona security scheme para API Key no Swagger
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key para autenticação"
        }
    }

    # Aplica security a todos os endpoints exceto health
    for path, path_item in openapi_schema["paths"].items():
        for method in path_item.values():
            if "security" not in method:
                method["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


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
        {
            "name": "API Keys",
            "description": "Gerenciamento de API Keys (restrito)",
        },
    ],
)
app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exames.router, prefix="/api/v1", tags=["Exames"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])


@app.get("/health", tags=["Health"], summary="Health Check")
def health_check():
    """Verifica se a API está online. Não requer autenticação."""
    return {"status": "ok", "version": "1.0.0"}
