# Feature: System Stabilization and Performance

Improve system resilience and performance by addressing identified bottlenecks and technical debt.

## Requirements

### R1: Memory Safety in PDF Processing
- The system MUST NOT crash when processing PDFs with many pages.
- The `convert_from_path` call MUST be limited to the first 5 pages by default to prevent OOM.
- Traceability: `STAB-001`

### R2: Optimized Task Distribution
- Celery workers MUST process one task at a time to ensure fair load balancing.
- Workers MUST only acknowledge tasks after successful completion or fatal failure (acks_late).
- Traceability: `STAB-002`

### R3: Resilient Clinical Summary
- The `regenerate` endpoint MUST handle slow LLM responses without blocking the event loop or timing out prematurely.
- Traceability: `STAB-003`

### R4: Modernize API and Database Code
- SQLAlchemy usage MUST follow 2.0 standards.
- FastAPI OpenAPI documentation MUST use non-deprecated `examples`.
- Pydantic models MUST use `ConfigDict`.
- Traceability: `STAB-004`
