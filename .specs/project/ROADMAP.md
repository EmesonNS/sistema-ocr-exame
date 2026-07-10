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
- [x] Static UI prototype documented in `docs/auditoria-dashboard-prototipo.html`

## Phase 9: Production Maturity & Clinical Standardization
- [x] FHIR DiagnosticReport Grouping
- [x] Dynamic LOINC Mapping Strategy
- [x] Agentic Token & Cost Tracking
- [x] Data Retention Policy & Compliance Worker

## OCR Quality Eval

- [x] Materializar `evaluation/` com estrutura base, schemas placeholders e corpus manifest
- [x] Classificar o corpus real atual em candidatos, derivados, negativos e shadow set
- [x] Seed inicial da knowledge layer versionada
- [x] Contratos de corpus/report validados por JSON Schema
- [x] Runner API-mode com evidência bloqueada real para um derivado
- [x] Cobertura automatizada mínima do benchmark (manifest + report helper)
- [x] Export consolidado de report e CSVs de release
- [x] Scorer mínimo com findings tipados e gate `unsafe_normal_rate` quando houver golden
- [x] Anotar manualmente o primeiro `golden_exams`
- [x] Implementar runner, scorer e reports de release
- [x] Validar o negative set com run rastreavel e report verificavel
- [x] Cobrir o runner em `in-process` e o scorer com testes unitarios

## Production Readiness Gaps

- [ ] Integrar o OCR ao produto com proxy autenticado no backend e contrato estável de upload/status/evidence
- [ ] Implementar o frontend real do dashboard de auditoria no repo do produto
- [ ] Validar o stack de produção com segredos reais, deploy controlado e smoke pós-deploy
- [ ] Adicionar monitoramento contínuo de qualidade, custo e segurança em ambiente real
