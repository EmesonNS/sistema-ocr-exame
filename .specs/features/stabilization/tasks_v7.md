# Tasks: Phase 7 (The Next Level)

## T22: Visual Traceability [P]
- [ ] Add `bounding_box` (JSON) field to `ResultadoBiomarcador` model.
- [ ] Update `AIService` prompt to include spatial reasoning instructions (requesting 2D coordinates).
- [ ] Implement coordinates normalization (scaling JSON coords to original image pixels).
- **Done when:** API returns biomarker values with their associated coordinates.

## T23: Interoperability Layer
- [ ] Create `app/services/interoperability_service.py`.
- [ ] Implement a lookup dictionary/service for common LOINC codes.
- [ ] Add `loinc_code` field to `ResultadoBiomarcador` model.
- [ ] Implement `FHIR` export utility.
- **Done when:** Results can be downloaded as JSON FHIR R4.

## T24: Agentic Loop Implementation
- [ ] Update `worker.py` to support "Re-extraction" pass.
- [ ] Create specialized prompt for zoomed-in image extraction.
- **Done when:** Guardrail failures trigger an automatic re-inspection pass.

## T25: Infrastructure & Documentation
- [ ] Run migrations for new database fields.
- [ ] Update `SOTA_RESEARCH.md` with implementation results.
