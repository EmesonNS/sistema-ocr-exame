# Feature: Advanced Optimizations & Webhooks

Enhance system responsiveness and integration capabilities through async LLM handling and a notification system.

## Requirements

### R5: Async LLM Interaction
- API endpoints that call LLMs MUST NOT block the FastAPI event loop.
- Use `client.aio` (async) for Google Gemini calls.
- Use `AsyncOpenAI` for OpenRouter calls.
- Traceability: `OPT-001`

### R6: Webhook Notifications
- The system SHOULD allow clients to register a callback URL.
- When an exam processing is completed (success or error), the system MUST send a POST request to the registered URL.
- Traceability: `OPT-002`

### R7: Image Cache for Fallback
- Converted images from PDF fallback MUST be cached to avoid redundant CPU-heavy conversions during retries.
- Traceability: `OPT-003`
