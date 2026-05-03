# Feature: Bug Fixes - Race Condition & Webhook Reliability

Address critical operational bugs identified during the deep architectural review.

## Requirements

### R14: Atomic Batch Updates
- The `ExameBatch` file counts MUST be updated atomically using database-level increments.
- Manual increments in Python (read-modify-write) MUST be removed to prevent race conditions.
- Traceability: `BUG-001`

### R15: Webhook Retry Mechanism
- The `WebhookService` SHOULD implement a basic retry logic (e.g., exponential backoff) for transient failures (HTTP 5xx, timeouts).
- Traceability: `BUG-002`
