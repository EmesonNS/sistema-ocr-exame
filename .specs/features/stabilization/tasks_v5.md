# Tasks: Bug Fixes (Phase 5)

## T15: Fix Batch Race Condition [TDD]
- [ ] **RED:** Create a test `app/tests/test_concurrency.py` that simulates multiple workers updating the same batch simultaneously.
- [ ] **GREEN:** Modify `app/repositories/exame_repo.py` to use SQLAlchemy `F()` expressions or equivalent for atomic increments.
- [ ] **REFACTOR:** Ensure all batch status logic is robust.
- **Done when:** Concurrency test passes 100% of the time.

## T16: Enhance Webhook Reliability
- [ ] Update `app/services/webhook_service.py` to use a retry strategy with `httpx`.
- [ ] Update unit tests to verify retry behavior.
- **Done when:** Webhooks successfully retry on 503 errors in tests.

## T17: Validation
- [ ] Run full test suite.
- **Done when:** 0 regressions and new bugs fixed.
