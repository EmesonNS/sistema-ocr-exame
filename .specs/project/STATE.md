# Project State

Atualizado em: 2026-07-10

## Current Context

O `sistema-ocr-exame` esta implementado como microservico privado para processamento de exames laboratoriais por OCR/IA. O servico opera com FastAPI, Celery, Redis, PostgreSQL, Alembic, API keys, readiness operacional, storage configuravel, auditoria visual, verificacao humana, exportacao FHIR, LOINC dinamico, retencao e avaliacao quantitativa em `evaluation/`.

A fronteira de produto atual esta definida: o OCR permanece privado e e consumido pelo `storge-service`. O trafego publico passa pelo frontend e pelo backend do produto; a API OCR interna nao e a superficie publica de upload.

## Capacidades Implementadas

| Area | Estado atual |
|---|---|
| API | Upload, listagem, detalhe, status, lote, resumo clinico, evidencia, FHIR, verificacao humana e administracao de API keys. |
| Processamento | Worker Celery com Redis, progresso por etapa e persistencia de resultados estruturados. |
| Guardrails | Normalizacao, rechecagens deterministicas, deteccao de prompt injection em saida de LLM e marcacao de revisao humana. |
| Storage | Camada agnostica entre local e S3-compatible; compose de producao fixa storage local explicitamente. |
| Readiness | `/ready` valida segredos obrigatorios, banco, Redis e worker. |
| Interoperabilidade | Bundle FHIR `DiagnosticReport` referenciando `Observation`; LOINC consultavel em tabela dedicada com fallback controlado. |
| Avaliacao | Corpus classificado, golden manual inicial, negative set, knowledge layer versionada, runner API/in-process, scorer e exportacao de relatorios/CSVs. |
| Integracao produto | Backend Storge consome OCR por rede privada e chave interna; frontend usa o backend para upload, polling e resultados. |
| Observabilidade app | Health operacional da integracao e resumo administrativo agregado restrito a ADMIN no backend Storge. |

## Evidencias de Validacao Registradas

- Suite containerizada do OCR registrada como verde em execucao anterior (`94 passed`).
- Prod compose validado anteriormente com env seguro: `/health` respondeu `ok` e worker conectou ao Redis.
- Negative set validado por execucao API-mode com documentos nao laboratoriais retornando bloqueio sem extracao indevida.
- Runner in-process coberto por teste com fake AI service.
- Dataset contract validado por JSON Schema para manifest, negative documents e metadados de relatorio.
- Exportacao consolidada de relatorio e CSVs implementada em `evaluation/scripts/export_eval_report.py`.
- Scoring e comparacao de runs implementados em `evaluation/scripts/score_eval_report.py` e `evaluation/scripts/compare_eval_runs.py`.
- Storage local/S3 coberto por testes de servico e contrato de compose de producao.
- LOINC cache, falhas de storage cleanup, inicializacao Gemini e readiness de segredos possuem cobertura observavel em logs/testes.

Essas evidencias descrevem registros existentes. Use `validado agora` apenas quando o comando, smoke ou teste tiver sido reexecutado na sessao corrente.

## Qualidade Quantitativa Atual

O pipeline de avaliacao existe e mede a saida estruturada contra golden/knowledge layer. O report versionado encontrado em `evaluation/reports/benchmarks/ocr-eval-05e07734-f1eb-4296-8bf1-83f0dd344195.score.json` registra `quality_gate.status=red`, `biomarker_precision=null`, `biomarker_recall=0.0` e motivo de documento golden bloqueado. Numeros de precision/recall sem referencia a report versionado especifico nao devem ser tratados como estado atual. A interpretacao correta e: runtime e integracao estao materializados; qualidade de extracao deve ser lida pelos relatorios do eval, nao apenas pelo sucesso do upload ou pela tela de resultado.

## Decisions

- **DEC-001:** Limitar conversao de PDF a 5 paginas no fallback.
- **DEC-002:** Celery usa `prefetch=1` e `acks_late=True`.
- **DEC-003:** Projeto migrado para Pydantic 2.0 e SQLAlchemy 2.0.
- **DEC-004:** Interacao com LLM e assíncrona.
- **DEC-005:** Webhook individual e batch com backoff exponencial.
- **DEC-006:** Cache Redis para imagens no fallback OCR.
- **DEC-007:** Deteccao de assinatura digital no upload.
- **DEC-008:** Incrementos atomicos para progresso de lote.
- **DEC-009:** `GuardrailsService` protege integridade de dados medicos.
- **DEC-010:** Deteccao por palavras-chave para prompt injection em saida de LLM.
- **DEC-011:** Coordenadas de rastreabilidade visual normalizadas em escala 0-1000 `[ymin, xmin, ymax, xmax]`.
- **DEC-012:** Suporte a citacoes visuais multipagina em `ResultadoBiomarcador`.
- **DEC-013:** Re-normalizacao apos agentic loop para integridade numerica.
- **DEC-014:** `PHYSIOLOGICAL_RANGES` expandido para paineis endocrinos e vitaminas.
- **DEC-015:** API de crop de evidencia visual com cache Redis para auditoria humana.
- **DEC-016:** Verificacao humana registrada em `ResultadoBiomarcador`.
- **DEC-017:** Ambientes Docker separados por Compose e arquivos `.env` dedicados, sem `container_name` fixo.
- **DEC-018:** Migrations controladas por servico dedicado `migrate`; API e worker nao rodam migrations implicitamente por default.
- **DEC-019:** OCR nao e exposto diretamente em producao; trafego publico passa por Nginx/backend do produto.
- **DEC-020:** Contrato publico de upload do produto usa `POST /api/exams/patient/{patientId}/upload`; contrato interno OCR permanece em `/api/v1/patients/{patientId}/exames/upload?user_id={userId}`.
- **DEC-021:** Mudancas em VPS comecam por inspecao read-only via `ssh storge`.
- **DEC-022:** Benchmark usa corpus real curado com classes separadas para raw labs, outputs derivados e documentos negativos.
- **DEC-023:** Eval possui knowledge layer versionada separada de `golden_exams`; `unsafe_normal_rate` e metrica critica de release.

## Referencias Locais

- Estado atual do OCR no produto: `.specs/project/OCR_CURRENT_STATE.md`
- README operacional: `sistema-ocr-exame/README.md`
- API principal: `sistema-ocr-exame/app/api/endpoints/exames.py`
- Worker: `sistema-ocr-exame/app/tasks/worker.py`
- Readiness: `sistema-ocr-exame/app/core/runtime_readiness.py`
- Storage: `sistema-ocr-exame/app/services/storage_service.py`
- Eval: `sistema-ocr-exame/evaluation/`
- Integração backend: `storge-app/storge-service/src/main/java/com/storge/storge_service/service/OcrService.java`
- Gate integrado: `storge-app/scripts/integrated-gate.sh`
