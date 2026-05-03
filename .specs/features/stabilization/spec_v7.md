# Feature: Interoperability and Traceability (Phase 7)

Elevate the system to international clinical standards (SOTA 2026) by providing visual evidence and standardized coding.

## Requirements

### R19: Visual Citations (Bounding Boxes)
- The extraction process MUST return the spatial coordinates (x, y, w, h) for each identified biomarker.
- These coordinates MUST be stored in the `ResultadoBiomarcador` model.
- Traceability: `NEXT-001`

### R20: LOINC Mapping
- The system SHOULD attempt to map extracted biomarkers to their corresponding **LOINC** codes.
- A local cache or external API (e.g., Regenstrief) may be used for validation.
- Traceability: `NEXT-002`

### R21: FHIR R4 Compatibility
- The system MUST provide an endpoint to export the exam results as a **FHIR Observation** resource.
- Traceability: `NEXT-003`

### R22: Agentic Self-Correction Loop
- If a `needs_review` flag is triggered by Guardrails, the system MUST perform a secondary "Focused Extraction" pass (using image cropping) to confirm the value.
- Traceability: `NEXT-004`
