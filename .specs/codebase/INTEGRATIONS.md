# External Integrations

## 1. Google Gemini API
- **Uso:** Extração primária de biomarcadores e geração de resumo clínico.
- **Conexão:** SDK oficial `google-genai` via modo assíncrono (`aio`).

## 2. OpenRouter API
- **Uso:** Fallback automático quando o Gemini falha ou atinge cota.
- **Conexão:** `AsyncOpenAI` client.

## 3. Webhook Integration
- **Uso:** Notificação proativa de conclusão de exames e lotes.
- **Padrão:** POST JSON com retentativas exponenciais.

## 4. Redis Cache
- **Uso:** 
  - Armazenamento de imagens convertidas de PDF (Base64) para evitar re-conversão em falhas (TTL 24h).
  - Cache de *crops* de evidência visual (TTL 1h).

## 5. Clinical Terminologies (LOINC)
- **Uso:** Mapeamento de termos locais para o vocabulário padrão universal de resultados laboratoriais (LOINC).
- **Implementação:** Local via `InteroperabilityService` (Expansível para API externa na Fase 9).

## 6. FHIR R4 Export
- **Uso:** Exportação de dados no padrão internacional de saúde.
- **Padrão:** Endpoint `/exames/{id}/fhir` gera um Bundle contendo recursos do tipo `Observation` vinculados aos códigos LOINC.

## 7. Storge Backend Integration
- **Uso:** O `storge-service` é o único consumidor externo autorizado do OCR em produção.
- **Fronteira pública:** O frontend/Nginx deve falar com o `storge-service`, não com o OCR.
- **Contrato público recomendado:** `POST /api/exams/patient/{patientId}/upload`.
- **Contrato interno OCR:** `POST /api/v1/patients/{patientId}/exames/upload?user_id={userId}` com `X-API-Key` e `multipart/form-data`.
- **Produção:** Na VPS Hostinger, o Nginx deve expor apenas frontend e `/api/*` para o backend. O OCR deve ficar privado em rede Docker/VPS interna.
