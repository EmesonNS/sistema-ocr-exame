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
- **DEC-011:** Visual Traceability coordinates normalized to 0-1000 scale [ymin, xmin, ymax, xmax].
- **DEC-012:** Support for multi-page visual citations in `ResultadoBiomarcador`.
- **DEC-013:** Re-normalization triggered after Agentic Loop to ensure numeric integrity.
- **DEC-014:** Expansion of `PHYSIOLOGICAL_RANGES` to include endocrine and vitamin panels.
- **DEC-015:** Visual Evidence Crop API with Redis caching (exp: 1h) to support human audit.
- **DEC-016:** Human verification tracking in `ResultadoBiomarcador`.

## Blockers
- None.

## Todos
- [ ] Monitor performance and safety in real-world scenarios.
- [ ] Build Frontend for Audit Dashboard.
- [ ] Execute Phase 9 (Production Maturity & Clinical Standardization).
