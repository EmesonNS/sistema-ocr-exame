# System Architecture

## Visão Geral
O sistema utiliza uma arquitetura orientada a serviços com processamento assíncrono para operações de IA de longa duração, seguindo padrões modernos de segurança e interoperabilidade.

## Componentes
1. **API Layer (FastAPI):** Gerencia autenticação (API Keys), ingestão de arquivos, exportação FHIR R4, evidências visuais e polling de status.
2. **Service Layer:** 
   - `AIService`: Orquestração de extração multimodal, fallback e Agentic Zoom.
   - `NormalizationService`: Regras determinísticas de correção médica.
   - `GuardrailsService`: Segurança semântica e faixas de plausibilidade (Sanity Ranges).
   - `InteroperabilityService`: Mapeamento LOINC e serialização FHIR R4.
   - `EvidenceService`: Recorte dinâmico de evidências visuais (crops) de PDFs.
   - `WebhookService`: Notificações ativas com retry.
3. **Task Layer (Celery):** Workers isolados que executam o pipeline pesado e o Ciclo Agêntico de re-inspeção.
4. **Data Layer:** PostgreSQL (com suporte a JSONB para Rastreabilidade Visual) e Redis para cache de imagens.

## Fluxos Avançados (SOTA)

### Ciclo Agêntico (Agentic Loop)
Para garantir alta fidelidade, o sistema implementa um ciclo de auto-correção:
1. **Extração Inicial**: IA lê o documento completo.
2. **Validação**: `GuardrailsService` identifica valores fisicamente impossíveis ou suspeitos.
3. **Re-inspeção (Zoom)**: O worker realiza um recorte (crop) de alta resolução na área do biomarcador suspeito.
4. **Re-Normalização**: O novo valor é re-processado deterministicamente, garantindo integridade numérica e atualização de alertas.

### Auditoria Human-in-the-Loop
Para cenários clínicos, a transparência é fundamental:
1. **Recuperação de Evidência**: Endpoint `/evidence` retorna apenas o trecho da imagem de onde o dado saiu.
2. **Mecanismo de Cache**: Crops são salvos no Redis (TTL 1h) para performance.
3. **Verificação**: Profissionais podem marcar resultados como "Auditados" via API.

## Fluxo de Dados (Upload)
1. Cliente envia PDF via `POST /upload`.
2. API salva arquivo, detecta assinatura digital e cria registro `Pendente`.
3. Task é enviada ao Celery.
4. Worker converte PDF -> Imagem (com cache Redis) -> Extração IA -> Normalização -> Guardrails.
5. Se disparado, o **Agentic Loop** realiza o zoom e correção.
6. Mapeamento LOINC é aplicado.
7. Resultado é salvo e Webhook é disparado.

## Fronteira de Produção com Storge

Em produção, o OCR não é uma API pública. O desenho alvo é:

1. Browser acessa o Nginx público da VPS Hostinger.
2. Nginx serve o frontend e encaminha `/api/*` para `storge-service`.
3. `storge-service` autentica o usuário, extrai `userId` real e chama o OCR pela rede interna.
4. OCR recebe `user_id` como query param e a API key no header `X-API-Key`.

Fluxo decidido:

```text
Browser -> Nginx -> storge-service -> sistema-ocr-exame
```

O Nginx não deve publicar uma rota direta para `sistema-ocr-exame`.
