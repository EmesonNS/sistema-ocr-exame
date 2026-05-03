# Feature: Multi-document Batch Processing

Enable clients to upload multiple medical exams in a single request and track their collective progress.

## Requirements

### R10: Batch Tracking Model
- A new `ExameBatch` model MUST be created to group multiple `Exame` records.
- Fields: `id` (UUID), `patient_id` (int), `status` (pending|processing|completed|error), `created_at`, `total_files`, `completed_files`.
- Traceability: `PH4-001`

### R11: Batch Upload Endpoint
- A new endpoint `POST /patients/{patient_id}/exames/batch` MUST be implemented.
- It MUST accept multiple `UploadFile` objects.
- It MUST return a `batch_id` immediately.
- Traceability: `PH4-002`

### R12: Batch Webhook Notification
- If a `webhook_url` is provided during batch upload, the system MUST notify the client when the ENTIRE batch is finished.
- Traceability: `PH4-003`

### R13: Batch Status Polling
- An endpoint `GET /exames/batch/{batch_id}` MUST return the overall progress of the batch and a list of included exam IDs with their individual statuses.
- Traceability: `PH4-004`
