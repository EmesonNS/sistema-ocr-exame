# Project Structure

```
/
├── .specs/             # Documentação técnica e planejamento (Spec-Driven)
├── alembic/            # Migrações de banco de dados
├── app/
│   ├── api/            # Endpoints FastAPI
│   │   └── endpoints/
│   │       ├── api_keys.py
│   │       └── exames.py
│   ├── core/           # Configurações globais, DB, Cache e Auth
│   ├── models/         # Modelos SQLAlchemy (Entidades)
│   ├── repositories/   # Camada de persistência (Abstração DB)
│   ├── schemas/        # Schemas Pydantic (DTOs)
│   ├── services/       # Lógica de negócio e integrações de IA
│   │   ├── ai_service.py               # Extração multimodal + Zoom
│   │   ├── clinical_summary_service.py # Geração de insights
│   │   ├── evidence_service.py         # Crops de evidência visual
│   │   ├── interoperability_service.py # FHIR & LOINC mapping
│   │   ├── guardrails_service.py       # Segurança e faixas médicas
│   │   └── biomarker_normalization.py  # Camada determinística
│   ├── tasks/          # Workers do Celery (Pipelines pesados)
│   └── tests/          # Suíte de testes Pytest
├── docs/               # Documentação adicional de suporte
├── scripts/            # Utilitários de CLI
└── uploads/            # Armazenamento temporário de PDFs
```
