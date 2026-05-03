# Project: Sistema OCR Exame

Microservice for medical exam OCR and biomarker extraction using Google Gemini and OpenRouter.

## Goals
- Stable and accurate biomarker extraction from laboratory PDFs.
- Resilient processing using asynchronous tasks.
- Secure API access via API Keys.
- Modern and maintainable technical stack.

## Architecture Overview
- **Backend:** FastAPI (Python 3.10)
- **Database:** PostgreSQL (SQLAlchemy 2.0)
- **Task Queue:** Celery + Redis
- **AI Engine:** Google GenAI (Gemini 2.0 Flash) + OpenAI (OpenRouter fallback)
- **Deployment:** Docker & Docker Compose
