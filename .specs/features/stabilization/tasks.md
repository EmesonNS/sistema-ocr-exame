# Tasks: System Stabilization

## T1: Memory Safety (OOM Prevention)
- [x] **T1.1:** Add `MAX_PDF_PAGES_FALLBACK` to `Settings` in `app/core/config.py`.
- [x] **T1.2:** Update `convert_from_path` in `app/services/ai_service.py` to use `first_page` and `last_page` parameters.
- **Done when:** Large PDFs process only the configured number of pages in fallback mode.

## T2: Celery Optimization
- [x] **T2.1:** Set `worker_prefetch_multiplier = 1` in `app/core/celery_app.py`.
- [x] **T2.2:** Set `task_acks_late = True` in `app/core/celery_app.py`.
- **Done when:** Workers process tasks one at a time and acknowledge them after completion.

## T3: Fix Deprecations (Modernization)
- [x] **T3.1:** Update `app/core/database.py` to use `sqlalchemy.orm.declarative_base`.
- [x] **T3.2:** Update `app/api/endpoints/exames.py` to use `examples=[...]` instead of `example=...`.
- [x] **T3.3:** Migrate `ExameResponse` and other schemas in `app/schemas/exame.py` to use `ConfigDict`.
- **Done when:** `pytest` runs with 0 warnings related to these frameworks.

## T4: Final Verification
- [x] **T4.1:** Run `PYTHONPATH=. pytest -v` inside the container.
- [x] **T4.2:** Verify Celery logs for correct configuration loading.
- **Done when:** 100% tests pass with 0 critical warnings.
