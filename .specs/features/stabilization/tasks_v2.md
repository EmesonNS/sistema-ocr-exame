# Tasks: Advanced Optimizations

## T5: Async LLM Refactoring [P]
- [x] Refactor `app/services/ai_service.py` to use `AsyncOpenAI` and async Gemini calls.
- [x] Refactor `app/services/clinical_summary_service.py` to use async Gemini calls.
- [x] Update `app/api/endpoints/exames.py` to correctly await these services.
- **Done when:** API remains responsive during LLM calls.

## T6: Webhook System
- [x] Add `webhook_url` field to `Exame` model.
- [x] Create migration for the new field.
- [x] Implement `WebhookService` to send POST notifications.
- [x] Trigger webhook in `app/tasks/worker.py` upon completion/failure.
- [x] Add `webhook_url` parameter to upload endpoint.
- **Done when:** POST request is sent to a test endpoint after exam processing.

## T7: Final Validation
- [x] Run full test suite (77 tests).
- [x] Fix async test cases in `test_ai_service.py`.
- [x] Manual verification of database migrations.
- **Done when:** 100% tests pass with 0 critical warnings.
