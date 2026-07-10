# Tasks: Phase 9 (Production Maturity)

## T29: FHIR DiagnosticReport [P]
- [x] Atualizar `InteroperabilityService` para gerar a estrutura base do `DiagnosticReport`.
- [x] Modificar o endpoint `/fhir` para retornar um Bundle que contém o `DiagnosticReport` e as `Observations` como "`hasMember`".
- [x] Adicionar testes de validação do schema FHIR.
- **Done when:** O endpoint FHIR retorna um Bundle semanticamente correto agrupado por relatório.

## T30: LOINC Dictionary Migration
- [x] Criar modelo `LoincMapping` (id, keyword, loinc_code, description).
- [x] Migrar o dicionário estático atual para registros "seed" no banco de dados.
- [x] Atualizar `InteroperabilityService` para fazer queries no banco (com cache no Redis).
- **Done when:** O mapeamento LOINC é recuperado dinamicamente.

## T31: Cost Observability
- [x] Criar decorator ou interceptor em `AIService` para capturar `usage_metadata` das respostas do OpenRouter/Gemini.
- [x] Adicionar campos `total_tokens` e `agentic_zoom_tokens` ao modelo `Exame`.
- [x] Atualizar o worker do Celery para salvar essas métricas ao finalizar.
- **Done when:** Cada exame rastreia quanto custou sua extração.

## T32: Retention Policy Worker
- [x] Criar task periódica no Celery (Beat) `cleanup_old_exams_task`.
- [x] Implementar deleção física de arquivos em `uploads/` baseada no `created_at` (> 30 dias).
- **Done when:** Arquivos antigos são removidos sem intervenção manual.
