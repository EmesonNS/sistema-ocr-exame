# Feature: Image Caching and Digital Signatures

Enhance system efficiency and security by caching CPU-heavy operations and verifying document authenticity.

## Requirements

### R8: PDF Image Caching (Redis)
- The system MUST cache the base64 representations of PDF pages when using the OpenRouter fallback.
- The cache MUST use the file's MD5 or SHA256 hash as the key.
- The cache MUST have an expiration time (e.g., 24 hours) to prevent Redis memory bloat.
- Traceability: `PH3-001`

### R9: Digital Signature Detection
- The system SHOULD detect if the uploaded PDF contains a digital signature.
- A new boolean field `is_digitally_signed` MUST be added to the `Exame` model.
- The upload endpoint MUST parse the PDF and set this flag before saving.
- Traceability: `PH3-002`
