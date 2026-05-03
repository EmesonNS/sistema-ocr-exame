# Tasks: Phase 6 (AI Guardrails)

## T18: Physiological Guardrails [P]
- [ ] Create `app/services/guardrails_service.py` with a library of medical sanity ranges.
- [ ] Implement `validate_plausibility` function.
- [ ] Integrate this service into `biomarker_normalization.py` or directly in the repo layer.
- **Done when:** Biomarkers with impossible values are flagged for review.

## T19: Security Guardrails (Injection Detection)
- [ ] Implement an input-check pass in `AIService` to look for malicious tokens.
- [ ] Update `worker.py` to handle security exceptions.
- **Done when:** Exams with "ignore instructions" text are rejected.

## T20: AI Self-Critic Pass
- [ ] Modify `AIService` to optionally run a validation prompt after the main extraction.
- **Done when:** Hallucination rates decrease in validation tests.

## T21: Final Validation [TDD]
- [ ] **RED:** Write tests in `app/tests/test_guardrails.py` for extreme values and malicious inputs.
- [ ] **GREEN:** Verify all guardrails catch the intended scenarios.
