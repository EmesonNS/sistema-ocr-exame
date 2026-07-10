# Estado Atual do OCR Storge

Atualizado em: 2026-07-10

Este documento descreve o que o OCR da Storge ja entrega hoje, como ele esta integrado ao produto e quais evidencias locais sustentam esse estado. Ele nao e um roadmap.

## Leitura Executiva

O OCR esta implementado como um microservico privado do ecossistema Storge. Ele recebe PDFs de exames laboratoriais, processa a extracao em segundo plano com worker Celery, persiste resultados estruturados, mantem o arquivo original em storage configuravel e expoe APIs internas para consulta, auditoria, evidencia visual, exportacao FHIR e verificacao humana.

A integracao com o app principal ja existe pelo backend Spring Boot (`storge-service`). O frontend React usa o backend do produto para upload, polling de status, historico e visualizacao de resultados. O OCR nao deve ser consumido diretamente pela interface publica; a fronteira operacional atual e: frontend -> backend Storge -> OCR privado.

## Componentes Atuais

| Componente | Estado atual |
|---|---|
| API OCR | FastAPI com endpoints de upload, listagem, detalhe, status, resumo, evidencia, FHIR, lote, API keys e readiness. |
| Worker | Celery processa exames de forma assincrona via Redis, atualiza estagios de progresso e persiste resultados. |
| Banco | PostgreSQL com migrations Alembic executadas pelo servico dedicado `migrate`. |
| Fila/cache | Redis usado como broker/result backend do Celery e como cache operacional em partes do pipeline. |
| Storage | Adapter local e S3-compatible/MinIO para arquivos originais de exame; producao fica explicitamente em storage local no compose atual. |
| IA | Gemini como provedor principal e OpenRouter como fallback configuravel. |
| App backend | Spring Boot faz proxy do contrato do OCR e mantem a API publica do produto desacoplada da API interna do OCR. |
| App frontend | React/Vite com fluxo desktop de upload PDF, polling real, historico e resultado resumido. Campos de auditoria clinica, LOINC, evidencia visual e verificacao humana existem no OCR/backend, mas nao estao todos expostos na UI atual. |
| Observabilidade de integracao | Backend possui health operacional da integracao OCR e resumo administrativo agregado protegido por papel ADMIN. |

## Fluxo Operacional Implementado

1. O usuario envia um PDF pelo produto Storge.
2. O frontend chama o backend Spring Boot, nao o OCR diretamente.
3. O backend encaminha o arquivo para o OCR privado usando `OCR_API_BASE_URL` e `OCR_API_KEY`.
4. A API OCR grava o exame, armazena o arquivo e agenda a tarefa assincrona.
5. O worker processa o documento, extrai biomarcadores, normaliza valores e atualiza progresso.
6. O frontend acompanha o status por polling atraves do backend do produto.
7. Ao concluir, o produto consulta detalhe, resultados e metadados estruturados.
8. O arquivo original pode ser recuperado por proxy autenticado do backend, sem bucket publico.

## Contrato Funcional Ja Exposto

### Upload e acompanhamento

- Upload de PDF por paciente.
- Status `pendente`, `processando`, `concluido` e `erro`.
- Campos de progresso como `processing_stage`, `processing_percent` e `processing_message`.
- Polling real no frontend, sem simulacao de temporizador como fonte de verdade.

### Resultado estruturado

- Biomarcadores com nome, valor bruto, valor numerico, unidade, referencia, status de alerta e confianca.
- Separacao de valores absolutos, percentuais e textuais.
- Marcacao de `needs_review` quando ha baixa confianca ou correcao incerta.
- Correcao/auditoria de valores quando regras deterministicas identificam deslocamento decimal ou inconsistencia provavel.

### Recursos clinicos e interoperabilidade

- No OCR interno: resumo clinico gerado de forma best-effort quando provedor de IA esta disponivel.
- No OCR interno: exportacao FHIR em formato `DiagnosticReport` com referencias para `Observation`.
- No OCR interno: mapeamento LOINC consultavel por tabela dedicada e fallback controlado.
- No OCR interno: evidencia visual por biomarcador, com coordenadas normalizadas e crop/cache para auditoria.
- No OCR interno: verificacao humana registrada por biomarcador.
- No produto atual: o frontend usa upload, polling, historico e resultado resumido; a experiencia completa de auditoria clinica nao deve ser inferida pela existencia dos endpoints internos.

### Seguranca e acesso

- Endpoints principais de negocio protegidos por `X-API-Key`.
- Endpoints administrativos de API key protegidos por `X-Master-Key`.
- OCR operado como servico privado; o produto consome por rede Docker/VPS interna.
- `/health` e `/ready` sao publicos no codigo atual; `/ready` valida segredos obrigatorios, banco, Redis e worker, mas nao valida qualidade OCR nem chamada real aos provedores de IA.
- Resumo operacional do backend do produto restrito a ADMIN.

## Docker e Ambientes

O OCR usa Compose com servicos separados para:

- `db` PostgreSQL;
- `redis`;
- `migrate`;
- `api`;
- `worker`;
- `minio` no ambiente de desenvolvimento quando storage S3-compatible e usado.

O ambiente de desenvolvimento integrado usa o nome padrao do projeto `sistema-ocr-exame`, criando a rede `sistema-ocr-exame_ocr_network`. O backend Storge usa essa rede externa por `OCR_NETWORK_NAME`.

Comandos principais documentados no README do OCR:

```bash
cd sistema-ocr-exame
cp .env.dev.example .env.dev
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Preflight do Docker antes de qualquer subida:

```bash
docker info
docker compose version
```

## Health e Readiness

O OCR expoe dois niveis de checagem:

| Endpoint | Uso |
|---|---|
| `/health` | Confirma que a API HTTP responde. |
| `/ready` | Confirma prontidao operacional com segredos, banco, Redis e worker. |

`/ready` e o endpoint usado como referencia para evitar falso positivo de API viva com pipeline indisponivel. Ele nao substitui smoke de upload/processamento nem avaliacao quantitativa de qualidade.

## Validacao Local Registrada

As evidencias ja registradas no repositorio indicam:

- Smoke isolado do OCR com upload real, polling e resultados persistidos.
- Smoke integrado com backend Storge, MinIO e download autenticado de PDF persistido.
- Suite OCR executada em container como caminho canonico de validacao.
- Testes focados do backend Spring Boot para contrato com OCR, incluindo upload/listagem/detalhe/status e erros 400/401/404/5xx.
- Build e testes do frontend para o fluxo de exames, incluindo upload real, polling, retry e erro.
- Harness canonico em `storge-app/scripts/integrated-gate.sh` para gate integrado HTTP backend/OCR com evidencias JSON. Esse harness nao equivale a walkthrough automatizado de navegador.

Quando citar validacao, diferencie:

- `implementado`: existe no codigo/configuracao;
- `configurado`: existe em compose/env/estrutura operacional;
- `executado anteriormente`: existe registro ou artefato historico;
- `validado agora`: foi reexecutado na sessao corrente.

## Qualidade OCR Medida

O projeto possui uma estrutura de avaliacao em `sistema-ocr-exame/evaluation/` com:

- corpus classificado;
- `golden_exams` manual inicial;
- negative set;
- knowledge layer versionada;
- runner API e in-process;
- scorer conservador;
- exportacao de relatorio consolidado e CSVs.

A leitura atual da qualidade e objetiva: a infraestrutura de eval existe, mas qualidade clinica de release nao esta aprovada. O report versionado encontrado em `evaluation/reports/benchmarks/ocr-eval-05e07734-f1eb-4296-8bf1-83f0dd344195.score.json` registra `quality_gate.status=red`, `biomarker_precision=null`, `biomarker_recall=0.0` e motivo de documento golden bloqueado. Numeros de precision/recall sem referencia a report versionado especifico nao devem ser tratados como estado atual.

## Arquivos de Referencia

| Area | Arquivo |
|---|---|
| README operacional OCR | `sistema-ocr-exame/README.md` |
| Compose base OCR | `sistema-ocr-exame/docker-compose.yml` |
| Override dev OCR | `sistema-ocr-exame/docker-compose.dev.yml` |
| Estado interno OCR | `sistema-ocr-exame/.specs/project/STATE.md` |
| Gate integrado | `storge-app/scripts/integrated-gate.sh` |
| Compose app Storge | `storge-app/docker-compose.yml` |
| Servico OCR no backend | `storge-app/storge-service/src/main/java/com/storge/storge_service/service/OcrService.java` |
| Controller de exames do app | `storge-app/storge-service/src/main/java/com/storge/storge_service/controller/ExamController.java` |
| Health da integracao | `storge-app/storge-service/src/main/java/com/storge/storge_service/controller/OcrIntegrationHealthController.java` |
| Observabilidade administrativa | `storge-app/storge-service/src/main/java/com/storge/storge_service/controller/ObservabilityController.java` |
| Frontend de exames | `storge-app/storge-system/src/components/examAnalysis/ExamAnalysis.tsx` |
| Eval OCR | `sistema-ocr-exame/evaluation/` |

## Como Avaliar o Estado Atual

Para uma avaliacao tecnica local, a sequencia pratica e:

1. Confirmar Docker ativo com `docker info`.
2. Subir o OCR pelo README do microservico.
3. Checar `/health` e `/ready`.
4. Criar ou configurar uma `OCR_API_KEY` valida.
5. Subir o backend Storge com `OCR_NETWORK_NAME=sistema-ocr-exame_ocr_network`.
6. Executar o harness integrado em `storge-app/scripts/integrated-gate.sh` quando o ambiente estiver preparado.
7. Consultar os relatorios em `sistema-ocr-exame/evaluation/` para leitura quantitativa de qualidade.
