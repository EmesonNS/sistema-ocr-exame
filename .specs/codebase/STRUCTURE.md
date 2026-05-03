# Project Structure

```
/
├── .specs/             # Documentação técnica e planejamento (Spec-Driven)
├── alembic/            # Migrações de banco de dados
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── core/           # Configurações globais, DB, Cache e Auth
│   ├── models/         # Modelos SQLAlchemy (Entidades)
│   ├── repositories/   # Camada de persistência (Abstração DB)
│   ├── schemas/        # Schemas Pydantic (DTOs)
│   ├── services/       # Lógica de negócio e integrações de IA
│   ├── tasks/          # Workers do Celery
│   └── tests/          # Suíte de testes Pytest
├── docs/               # Documentação adicional de suporte
├── scripts/            # Utilitários de CLI
└── uploads/            # Armazenamento temporário de PDFs
```
