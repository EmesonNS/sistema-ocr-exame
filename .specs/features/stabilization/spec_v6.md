# Feature: AI Guardrails and Semantic Safety

Ensure the trustworthiness and security of AI-extracted medical data through biological plausibility checks and adversarial content detection.

## Requirements

### R16: Biological Plausibility Checks (Deterministic Rails)
- The system MUST maintain a dictionary of "sanity ranges" for critical biomarkers.
- If an extracted value is outside the physiological possibility (e.g., Glucose > 1000 mg/dL or < 10 mg/dL), the result MUST be flagged with `needs_review=True`.
- A descriptive warning MUST be added to `correcao_aplicada`.
- Traceability: `GUARD-001`

### R17: Prompt Injection Detection (Input Rails)
- The system SHOULD use a lightweight check to detect if the PDF contains hidden instructions intended to manipulate the OCR (Adversarial attacks).
- If injection is detected, the exam status MUST be set to `failed` with a security warning.
- Traceability: `GUARD-002`

### R18: Self-Criticism Pass (Output Rails)
- After extraction, the AI SHOULD perform a "self-critic" pass to identify any hallucinated values or formatting errors.
- Traceability: `GUARD-003`
