# Codebase Concerns & Tech Debt

## Bottlenecks

### 1. OOM Risk with Large PDFs (Critical)
- **Location:** `app/services/ai_service.py:186`
- **Impact:** High. Converting entire large PDFs to images in memory will cause worker crashes.
- **Fix:** Limit page count or use temporary file storage for images instead of keeping all in RAM.

### 2. Suboptimal Task Distribution (Medium)
- **Location:** `app/core/celery_app.py`
- **Impact:** Medium. Default prefetch multiplier causes task imbalance.
- **Fix:** Set `worker_prefetch_multiplier = 1` and `task_acks_late = True`.

### 3. API Timeout Risk - Clinical Summary (Medium)
- **Location:** `app/api/endpoints/exames.py`
- **Impact:** Medium. Sync-style AI calls on a potentially slow LLM can cause client timeouts.
- **Fix:** Ensure summary generation is fully backgrounded or has appropriate timeouts and retry logic.

## Tech Debt / Deprecations

### 1. SQLAlchemy 2.0 Deprecations
- **Location:** `app/core/database.py:12`
- **Issue:** `declarative_base()` usage.
- **Fix:** Migrate to `sqlalchemy.orm.declarative_base()`.

### 2. FastAPI OpenAPI Deprecations
- **Location:** `app/api/endpoints/exames.py:48, 77`
- **Issue:** `example` parameter in `Path`.
- **Fix:** Use `examples=[...]`.

### 3. Pydantic 2.0 Config Deprecations
- **Location:** Multiple models/schemas.
- **Issue:** Class-based `Config`.
- **Fix:** Use `ConfigDict`.
