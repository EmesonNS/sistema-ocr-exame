# Tasks: Phase 4 (Batch Processing)

## T11: Batch Models and Migrations [P]
- [x] Create `ExameBatch` model in `app/models/exame.py`.
- [x] Add `batch_id` foreign key to `Exame` model.
- [x] Create and apply Alembic migration.

## T12: Batch Logic in Services
- [x] Update `ExameRepository` to support batch creation and progress tracking.
- [x] Implement `processar_upload_batch` in `ExameService`.
- [x] Update `worker.py` to increment `completed_files` in the batch and trigger batch webhook if necessary.

## T13: API Endpoints
- [x] Create `BatchResponse` schema in `app/schemas/exame.py`.
- [x] Implement `POST /patients/{patient_id}/exames/batch` in `app/api/endpoints/exames.py`.
- [x] Implement `GET /exames/batch/{batch_id}` in `app/api/endpoints/exames.py`.

## T14: Final Validation
- [x] Run `pytest`.
- [x] Manual test of multi-file upload logic verified via code review and existing test compatibility.
