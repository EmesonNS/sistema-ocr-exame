# Project State

## Current Context
- System hardened, optimized and secured.
- Phase 6 (AI Guardrails) implemented and verified.
- 100% Test pass rate with specific guardrail coverage.
- Side chat on 2026-06-18 settled the production integration boundary: OCR stays private and is accessed only by `storge-service`; Nginx on the Hostinger VPS exposes frontend and `/api/*` to the backend only.

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
- **DEC-017:** Docker environments separated by Compose project names (`ocr-dev`, `ocr-test`, `ocr-prod`) with dedicated env files, no fixed `container_name`, and isolated volumes/networks.
- **DEC-018:** Database migrations are controlled by a dedicated `migrate` service; API and worker skip migrations on startup by default.
- **DEC-019:** Production must not expose `sistema-ocr-exame` directly. Public traffic flows Browser -> Nginx -> `storge-service`; the backend calls OCR through an internal Docker/VPS network.
- **DEC-020:** Public exam upload route should use the Storge product contract `POST /api/exams/patient/{patientId}/upload`; the internal OCR contract remains `POST /api/v1/patients/{patientId}/exames/upload?user_id={userId}`.
- **DEC-021:** Implementation on the VPS must begin with read-only inspection using `ssh storge` before changing Nginx, Docker Compose, env files, or services.

## Blockers
- None.

## Todos
- [ ] Monitor performance and safety in real-world scenarios.
- [ ] Build Frontend for Audit Dashboard.
- [ ] Execute Phase 9 (Production Maturity & Clinical Standardization).
- [ ] Validate prod stack with real secrets before production rollout.
- [ ] Implement `.specs/features/private_storge_ocr_integration/` using `ssh storge` for VPS inspection and rollout.
- [x] Delegate `.specs/features/private_storge_ocr_integration/tasks.md` to Antigravity CLI in order: `T-PRI-001` -> `T-PRI-003`/`T-PRI-004` -> `T-PRI-002` -> `T-PRI-005`.
- [x] Local integration verified successfully (`storge-app` backend connected to `sistema-ocr-exame` via `ocr_network` with valid API Key).
- [ ] Push changes, deploy backend to VPS, and execute `T-PRI-006` (Validation in Production).
