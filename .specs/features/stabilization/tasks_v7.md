# Tasks: Phase 7 (The Next Level)

## T22: Visual Traceability [P]
- [x] **T22.1: Model Update**
  - Add `bounding_box` (JSONB) field to `ResultadoBiomarcador` model in `app/models/exame.py`.
  - Add `page_number` (Integer) field to `ResultadoBiomarcador`.
- [x] **T22.2: Database Migration**
  - Generate and run Alembic migration `006_add_visual_traceability`.
- [x] **T22.3: AIService Enhancement**
  - Update `PROMPT_EXAME` in `app/services/ai_service.py` to request `bounding_box` (normalized 0-1000) and `page`.
  - Update `_processar_biomarcadores` to handle the new fields.
- [x] **T22.4: Repository Update**
  - Update `add_resultado_normalizado` in `app/repositories/exame_repo.py` to save `bounding_box` and `page_number`.
- [x] **T22.5: Schema and API Update**
  - Update `app/schemas/exame.py` to include visual traceability in the response.
- [x] **T22.6: Verification**
  - Create `app/tests/test_visual_traceability.py` to verify end-to-end extraction with coordinates.
- **Done when:** API returns biomarker values with their associated coordinates and page numbers.

## T23: Interoperability Layer
- [x] Create `app/services/interoperability_service.py`.
- [x] Implement a lookup dictionary/service for common LOINC codes.
- [x] Add `loinc_code` field to `ResultadoBiomarcador` model.
- [x] Implement `FHIR` export utility.
- **Done when:** Results can be downloaded as JSON FHIR R4.

## T24: Agentic Loop Implementation
- [x] Update `worker.py` to support "Re-extraction" pass.
- [x] Create specialized prompt for zoomed-in image extraction.
- **Done when:** Guardrail failures trigger an automatic re-inspection pass.

## T25: Infrastructure & Documentation
- [x] Update `SOTA_RESEARCH.md` with implementation results.
