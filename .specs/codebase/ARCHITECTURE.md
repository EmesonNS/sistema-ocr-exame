# System Architecture

## Visão Geral
O sistema utiliza uma arquitetura orientada a serviços com processamento assíncrono para operações de IA de longa duração.

## Componentes
1. **API Layer (FastAPI):** Gerencia autenticação (API Keys), ingestão de arquivos e polling de status.
2. **Service Layer:** 
   - `AIService`: Orquestração de extração multimodal e fallback.
   - `NormalizationService`: Regras determinísticas de correção médica.
   - `GuardrailsService`: Segurança semântica e plausibilidade.
   - `WebhookService`: Notificações ativas com retry.
3. **Task Layer (Celery):** Workers isolados que executam o pipeline pesado de OCR.
4. **Data Layer:** PostgreSQL para persistência de longo prazo e Redis para cache volátil.

## Fluxo de Dados (Upload)
1. Cliente envia PDF via `POST /upload`.
2. API salva arquivo, detecta assinatura digital e cria registro `Pendente`.
3. Task é enviada ao Celery.
4. Worker converte PDF -> Imagem (com cache Redis) -> Extração IA -> Normalização -> Guardrails.
5. Resultado é salvo e Webhook é disparado.
