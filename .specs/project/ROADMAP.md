# Roadmap

## Phase 1: Stabilization & Performance (Completed)
- [x] Fix OOM risk with large PDFs in AI fallback
- [x] Optimize Celery task distribution (Prefetch)
- [x] Improve Clinical Summary responsiveness (Async LLM)
- [x] Resolve framework deprecation warnings

## Phase 2: Advanced Integration (Completed)
- [x] Webhook support for completion notifications
- [x] Async LLM interactions across all services
- [x] Modernized Pydantic/SQLAlchemy patterns

## Phase 3: Future Enhancements (Completed)
- [x] Digital signature verification for PDFs
- [x] Image cache for OCR fallback

## Phase 4: Multi-document Batch Processing (Completed)
- [x] Batch tracking model (`ExameBatch`)
- [x] Batch upload endpoint (`POST /batch`)
- [x] Batch progress tracking and polling
- [x] Batch-level webhooks

## Phase 5: Critical Bug Fixes (Completed)
- [x] Fix Batch Race Condition (Atomic Increments)
- [x] Webhook Retry Mechanism with exponential backoff

## Phase 6: AI Guardrails & Security (Completed)
- [x] Physiological plausibility checks (Medical Sanity Ranges)
- [x] Prompt Injection Detection (Output Self-Check)
- [x] Automated sanitization of extracted results

## Phase 7: Interoperability & Traceability (Completed)
- [x] Visual Citations (Bounding Boxes for human audit)
- [x] Automated LOINC mapping for biomarkers
- [x] FHIR R4 Compatibility for hospital EHR integration
- [x] Agentic Self-Correction Loop for high-risk values

## Phase 8: Human-in-the-Loop & Audit (Completed)
- [x] Evidence Crop API (Visual Proof)
- [x] Human verification workflow
- [ ] Auditor Dashboard

## Phase 9: Production Maturity & Clinical Standardization
- [ ] FHIR DiagnosticReport Grouping
- [ ] Dynamic LOINC Mapping Strategy
- [ ] Agentic Token & Cost Tracking
- [ ] Data Retention Policy & Compliance Worker
