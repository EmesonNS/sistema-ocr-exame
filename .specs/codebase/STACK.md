# Tech Stack

## Backend
- **Framework:** FastAPI (Python 3.10)
- **Asincronia:** Asyncio/Await em todas as rotas e serviços core.
- **Servidor ASGI:** Uvicorn.

## Data & Persistence
- **Banco de Dados:** PostgreSQL 15.
- **ORM:** SQLAlchemy 2.0 (estilo declarativo moderno).
- **Migrações:** Alembic.
- **Cache:** Redis (usado para filas e cache de imagens de PDF).

## AI & Processing
- **LLM Primário:** Google Gemini 2.0 Flash (via `google-genai` SDK).
- **LLM Fallback:** OpenRouter (modelos variados, ex: Gemini 1.5/2.5).
- **Processamento PDF:** `pdf2image` (Poppler) + `pypdf` (para assinaturas).
- **Task Queue:** Celery 5.3 + Redis Broker.

## Testing & Quality
- **Framework:** Pytest.
- **Plugins:** `pytest-asyncio`, `httpx`.
- **Análise Estática:** Pydantic 2.0 (validação de tipos e schemas).
