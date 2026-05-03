# Project State

## Current Context
- System hardened, optimized and secured.
- Phase 6 (AI Guardrails) implemented and verified.
- 100% Test pass rate with specific guardrail coverage.

## Decisions
- **DEC-001:** Limit PDF conversion to 5 pages in fallback mode.
- **DEC-002:** Celery `prefetch=1` and `acks_late=True`.
- **DEC-003:** Migrated to Pydantic 2.0 and SQLAlchemy 2.0.
- **DEC-004:** Fully asynchronous LLM interaction.
- **DEC-005:** Webhook system (Individual & Batch) with exponential backoff.
- **DEC-006:** Redis image caching for OCR fallback.
- **DEC-007:** Digital signature detection on upload.
- **DEC-008:** Atomic increments for Batch progress.
- **DEC-009:** Implemented `GuardrailsService` for medical data integrity.
- **DEC-010:** Keyword-based Prompt Injection detection in LLM output.

## Blockers
- None.

## Todos
- [ ] Monitor performance and safety in real-world scenarios.
- [ ] Expand `PHYSIOLOGICAL_RANGES` with more biomarkers.
