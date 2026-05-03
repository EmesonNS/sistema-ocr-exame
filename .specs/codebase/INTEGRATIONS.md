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
- **Uso:** Armazenamento de imagens convertidas de PDF (Base64) para evitar re-conversão em falhas.
- **TTL:** 24 horas.
