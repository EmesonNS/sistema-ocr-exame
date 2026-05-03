# Tasks: Phase 3

## T8: Image Caching Implementation [P]
- [x] Add `redis` client setup in `app/core/database.py` or a new `app/core/cache.py`.
- [x] Refactor `app/services/ai_service.py` to calculate file hash.
- [x] Check Redis for cached base64 images before running `convert_from_path`.
- [x] Save base64 images to Redis after conversion.

## T9: Digital Signature Detection
- [x] Add `pypdf` to `requirements.txt` and install it.
- [x] Add `is_digitally_signed` to `Exame` model and create an Alembic migration.
- [x] Create a utility function in `app/services/exame_service.py` to check for signatures.
- [x] Update `processar_upload` to set the flag based on the check.

## T10: Validation
- [x] Run `pytest` to ensure nothing is broken.
- [x] Verify Alembic migration is applied.
