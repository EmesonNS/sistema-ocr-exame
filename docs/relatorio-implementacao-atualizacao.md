# Relatorio de implementacao - Atualizacao do sistema OCR de exames

Data: 2026-02-21

Este documento descreve a atualizacao mais recente do microservico `sistema-ocr-exame`, com foco em: acompanhamento de progresso do processamento, normalizacao deterministica, e resumo clinico gerado por IA.

## Contexto e objetivo da atualizacao

O processamento de exames e assincrono (API recebe upload, worker processa). Antes desta atualizacao, o consumidor tinha pouco feedback sobre o andamento e nao havia um resumo clinico estruturado persistido no banco.

Objetivos desta atualizacao:

- Expor progresso detalhado (stage, percentual, mensagem) para suportar polling simples no frontend.
- Padronizar parsing e normalizacao de biomarcadores com regras deterministicas e auditaveis.
- Persistir e reutilizar (cache) um resumo clinico estruturado para o exame, com opcao de regeneracao.
- Fortalecer o modelo de seguranca com:
  - `X-API-Key` para consumo dos endpoints de exames.
  - `MASTER_API_KEY` (via `X-Master-Key`) para endpoints administrativos de emissao e gestao de API Keys.

## O que foi implementado (checklist do que foi concluido)

- [x] Campos de progresso no modelo `Exame`: `processing_stage`, `processing_percent`, `processing_message`.
- [x] Endpoint leve de status para polling: `GET /exames/{exame_id}/status` retornando progresso detalhado.
- [x] Estagios de progresso padronizados no processamento assincorno via worker.
- [x] Persistencia de resumo clinico (`clinical_summary`) e timestamp (`summary_generated_at`) no `Exame`.
- [x] Endpoints para ler e regenerar resumo clinico.
- [x] Normalizacao deterministica com:
  - deteccao de tipo (percentual vs absoluto vs textual)
  - parse de numero e referencia
  - heuristica de decimal deslocado (com auditoria)
  - campos de qualidade e rastreabilidade no banco
- [x] Autenticacao por API Key (`X-API-Key`) aplicada aos endpoints de exames.
- [x] Autenticacao administrativa via `MASTER_API_KEY` (`X-Master-Key`) para endpoints de API Keys.
- [x] Suite de testes cobrindo upload, listagem, detalhes, status e endpoints de resumo clinico.

## Funcionamento atual (fluxo ponta-a-ponta)

Fluxo principal:

1. Cliente chama `POST /patients/{patient_id}/exames/upload` com `file` (PDF) e `user_id`.
2. A API salva o arquivo em disco (`uploads/`) e cria um registro em `exames` com `status_processamento = "pendente"`.
3. A API dispara uma task Celery (`processar_exame_task`) com `exame_id` e `file_path`.
4. O worker atualiza progresso em etapas (queued, downloading, ocr_extracting, ai_analyzing, normalizing) e executa:
   - extracao via IA (`AIService`)
   - normalizacao deterministica (`biomarker_normalization`)
   - persistencia em `resultados_biomarcadores`
5. O worker tenta gerar resumo clinico (best-effort). Se falhar, o exame ainda pode finalizar como `completed`.
6. Ao final:
   - `processing_stage` muda para `completed` e `processing_percent` para 100, ou `failed` em caso de erro.
   - `status_processamento` e mapeado para: `pendente`, `processando`, `concluido`, `erro`.
   - o arquivo temporario e removido pelo worker.
7. O cliente usa polling em `GET /exames/{exame_id}/status` para acompanhar e, quando `status == "concluido"`, pode consumir:
   - `GET /exames/{exame_id}` (detalhes + biomarcadores)
   - `GET /exames/{exame_id}/resumo` (resumo clinico, se disponivel)

## API: autenticacao + endpoints + exemplos (request/response)

### Autenticacao

Consumo (endpoints de exames):

- Header obrigatorio: `X-API-Key: <api_key_do_cliente>`
- Validacao: o valor do header e hasheado (SHA-256) e comparado com `api_keys.key_hash` (somente chaves ativas).

Administrativo (endpoints de API Keys):

- Header obrigatorio: `X-Master-Key: <master_key>`
- A chave mestra vem de `MASTER_API_KEY` no ambiente. Se estiver vazia, o acesso admin fica desabilitado (retorna 503).

### Endpoints de exames (definidos em `app/api/endpoints/exames.py`)

- `POST /patients/{patient_id}/exames/upload`
- `GET /patients/{patient_id}/exames`
- `GET /exames/{exame_id}`
- `GET /exames/{exame_id}/status`
- `GET /exames/{exame_id}/resumo`
- `POST /exames/{exame_id}/resumo/regenerate`

Observacao: na aplicacao, o router e montado com prefixo `/api/v1`, entao os exemplos abaixo usam `/api/v1/...`.

### Valores padronizados

Progress stage values:

- `queued`, `downloading`, `ocr_extracting`, `ai_analyzing`, `normalizing`, `completed`, `failed`.

Status values referenced:

- `pendente`, `processando`, `concluido`, `erro`.

### Exemplos

#### 1) Upload de exame (PDF)

Request:

```bash
curl -X POST \
  "http://localhost:8000/api/v1/patients/42/exames/upload?user_id=123" \
  -H "X-API-Key: <sua-api-key>" \
  -F "file=@/caminho/para/exame.pdf"
```

Response (exemplo, campos principais):

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": 42,
  "data_coleta": null,
  "laboratorio": null,
  "status_processamento": "pendente",
  "url_documento": "uploads/abc123.pdf",
  "processing_stage": null,
  "processing_percent": null,
  "processing_message": null,
  "has_summary": false
}
```

Notas:

- A API valida extensao do arquivo. Se nao for `.pdf`, retorna 400.
- A task Celery e enfileirada, e o progresso passa a ser refletido no endpoint de status.

#### 2) Listar exames do paciente

Request:

```bash
curl -X GET \
  "http://localhost:8000/api/v1/patients/42/exames?page=1&limit=10" \
  -H "X-API-Key: <sua-api-key>"
```

Response (estrutura):

```json
{
  "items": [
    {
      "id": "...",
      "patient_id": 42,
      "status_processamento": "concluido",
      "processing_stage": "completed",
      "processing_percent": 100,
      "processing_message": "Processamento concluido - 15 biomarcadores extraidos",
      "has_summary": true
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

#### 3) Detalhes do exame (com biomarcadores)

Request:

```bash
curl -X GET \
  "http://localhost:8000/api/v1/exames/<exame_id>" \
  -H "X-API-Key: <sua-api-key>"
```

Response (estrutura, campos principais):

```json
{
  "id": "...",
  "patient_id": 42,
  "data_coleta": "2026-02-10",
  "laboratorio": "Laboratorio Sao Paulo",
  "status_processamento": "concluido",
  "processing_stage": "completed",
  "processing_percent": 100,
  "processing_message": "Processamento concluido - 15 biomarcadores extraidos",
  "has_summary": true,
  "resultados": [
    {
      "id": "...",
      "nome_marcador": "SEGMENTADOS",
      "valor_extraido": "49.0",
      "unidade_medida": "%",
      "referencia_lab": "40,0 a 75,0 %",
      "referencia_min": 40.0,
      "referencia_max": 75.0,
      "status_alerta": "normal",
      "tipo_valor": "percentual",
      "valor_raw": "49,0 %",
      "valor_numerico": 49.0,
      "fonte_valor": "ocr",
      "needs_review": false,
      "correcao_aplicada": null,
      "confianca": 1.0
    }
  ]
}
```

#### 4) Status de processamento (polling)

Request:

```bash
curl -X GET \
  "http://localhost:8000/api/v1/exames/<exame_id>/status" \
  -H "X-API-Key: <sua-api-key>"
```

Response (estrutura):

```json
{
  "status": "processando",
  "processing_stage": "ai_analyzing",
  "processing_percent": 50,
  "processing_message": "Analisando biomarcadores com IA",
  "has_summary": false
}
```

#### 5) Resumo clinico

Request:

```bash
curl -X GET \
  "http://localhost:8000/api/v1/exames/<exame_id>/resumo" \
  -H "X-API-Key: <sua-api-key>"
```

Response (estrutura):

```json
{
  "resumo_geral": "...",
  "alertas": [
    {
      "biomarcador": "LEUCOCITOS",
      "valor": "12000",
      "referencia": "4000-10000",
      "severidade": "atencao",
      "descricao": "..."
    }
  ],
  "recomendacoes": ["..."],
  "destilacoes": ["..."],
  "proximos_passos": ["..."],
  "generated_at": "2026-02-21T10:30:00Z"
}
```

Regras importantes deste endpoint:

- Se `status_processamento != "concluido"`, retorna 400 (exame ainda processando).
- Se nao houver biomarcadores persistidos, retorna 404.
- Se `GEMINI_API_KEY` estiver ausente, o servico de resumo retorna `None` e o endpoint retorna 500.

#### 6) Regenerar resumo clinico

Request:

```bash
curl -X POST \
  "http://localhost:8000/api/v1/exames/<exame_id>/resumo/regenerate" \
  -H "X-API-Key: <sua-api-key>"
```

Response: mesma estrutura de `GET /exames/{exame_id}/resumo`, com `generated_at` atualizado.

## Arquitetura: diagrama Mermaid (fluxo + componentes)

```mermaid
flowchart LR
  Client[Cliente / Frontend] -->|X-API-Key + PDF| API[FastAPI - /api/v1]
  API -->|salva arquivo| FS[(Disco local: uploads/)]
  API -->|cria Exame (pendente)| DB[(PostgreSQL)]
  API -->|send_task processar_exame_task| Broker[(Redis Broker)]
  Broker --> Worker[Celery Worker]

  Worker -->|update_processing_progress| DB
  Worker --> AI[AIService]
  AI -->|Gemini| Gemini[Google Gemini]
  AI -->|fallback| OR[OpenRouter (opcional)]
  AI --> Norm[Normalizacao deterministica]
  Norm -->|Result. normalizados + auditoria| DB

  Worker -->|best-effort| CS[ClinicalSummaryService]
  CS -->|GEMINI_API_KEY| Gemini
  CS -->|clinical_summary + summary_generated_at| DB

  Client -->|polling| Status[GET /exames/{id}/status]
  Status --> DB
  Client -->|detalhes| Details[GET /exames/{id}]
  Details --> DB
  Client -->|resumo| Summary[GET /exames/{id}/resumo]
  Summary --> DB
```

## Modelo de dados e migrations (o que mudou e por que)

### Tabela `exames`

Campos relevantes do modelo atual (`app/models/exame.py`):

- Identificacao: `id` (UUID), `patient_id`, `uploaded_by_user_id`
- Metadados: `data_coleta`, `laboratorio`, `url_documento`
- Status: `status_processamento` (default `pendente`)
- Progresso:
  - `processing_stage` (string)
  - `processing_percent` (int)
  - `processing_message` (string)
- Resumo clinico:
  - `clinical_summary` (JSONB no Postgres)
  - `summary_generated_at` (DateTime timezone)

### Migration 004: `004_add_processing_progress`

O que mudou:

- Adicionou `processing_stage`, `processing_percent`, `processing_message` em `exames`.
- Backfill de registros existentes com mapeamento baseado em `status_processamento`:
  - `concluido` -> stage `completed`, percent 100
  - `erro` -> stage `failed`, percent 0
  - `processando` -> stage `ai_analyzing`, percent 50
  - default -> stage `queued`, percent 0

Por que:

- Permitir que o consumidor acompanhe o processamento em tempo real via polling, sem depender de logs.

### Migration 005: `005_add_clinical_summary`

O que mudou:

- Adicionou `clinical_summary` (JSONB) e `summary_generated_at` em `exames`.

Por que:

- Persistir o resumo clinico para reuso (cache) e permitir auditoria (timestamp de geracao).

### Tabela `resultados_biomarcadores`

O modelo `ResultadoBiomarcador` armazena tanto informacao para exibicao quanto campos normalizados e de auditoria:

- Exibicao e referencia:
  - `nome_marcador`, `valor_extraido`, `unidade_medida`, `referencia_lab`
- Normalizacao:
  - `valor_raw` (texto do OCR)
  - `valor_numerico` (Numeric(10,4))
  - `tipo_valor` (`absoluto|percentual|textual`)
  - `referencia_min`, `referencia_max` (Numeric(10,4))
- Classificacao:
  - `status_alerta` (`baixo|normal|alto|indefinido`)
- Auditoria e qualidade:
  - `needs_review` (bool)
  - `correcao_aplicada` (texto explicando a regra aplicada)
  - `confianca` (0.0 a 1.0)
  - `fonte_valor` (`ocr|calculado|corrigido`)

## Normalizacao deterministica

Esta camada esta concentrada em `app/services/biomarker_normalization.py` e segue regras puras (sem side effects), para garantir previsibilidade.

### Percentual vs absoluto

Regras implementadas:

- Classificacao do tipo do valor (`extrair_tipo_valor`):
  - `percentual` quando detecta `%` no valor ou na unidade.
  - `absoluto` quando a unidade indica contagem/volume (ex: `/mm3`, `/mm³`) ou quando e numerico sem indicacao.
  - `textual` para respostas como "positivo", "negativo" e similares.
- Conversao percentual para absoluto e condicional (`converter_percentual_para_absoluto`):
  - so ocorre quando `tipo_valor == percentual` e existe `leucocitos_total` no `contexto`.
  - o resultado calculado registra auditoria em `correcao_aplicada` e marca `fonte_valor = calculado`.

Observacao importante do fluxo atual:

- No worker, `AIService.extrair_biomarcadores(file_path)` e chamado sem `leucocitos_total`, entao essa conversao nao ocorre automaticamente neste caminho.

### Auditoria de decimal (correcao de decimal deslocado)

Regras implementadas:

- `detectar_decimal_deslocado` aplica heuristicas por fator 10 e 100:
  - se `valor / 10` cai no range, sugere "dividido por 10"
  - se `valor * 10` cai no range, sugere "multiplicado por 10"
  - idem para fator 100 em casos extremos
- A correcao so e aplicada para `TipoValor.ABSOLUTO`.
- Ao aplicar correcao:
  - `correcao_aplicada` recebe uma descricao legivel
  - `fonte_valor` muda para `corrigido`
  - `confianca` e ajustada (ex: 0.8, 0.6)
  - `needs_review` vira `true` para facilitar revisao manual

Complemento para analise (nao acoplado ao fluxo do worker):

- `app/services/decimal_correction.py` fornece:
  - ranges esperados por marcador (para validacao de coerencia)
  - geracao de candidatos de correcao com score (`sugerir_correcao_decimal`)
  - selecao do melhor candidato (`escolher_melhor_correcao`)

### Campos de auditoria

Campos persistidos para rastreabilidade:

- `valor_raw`: texto original do OCR
- `valor_numerico`: representacao numerica para comparacoes
- `tipo_valor`: absoluto, percentual, textual
- `needs_review`: sinalizacao de caso com baixa confianca ou correcao aplicada
- `correcao_aplicada`: justificativa deterministica (regra)
- `confianca`: escala 0.0 a 1.0
- `fonte_valor`: ocr, calculado, corrigido

## Resumo clinico

### Cache

- `ClinicalSummaryService.generate_clinical_summary` retorna o resumo cached quando `exame.clinical_summary` ja existe.
- O endpoint `GET /exames/{exame_id}/resumo` descreve esse comportamento como cache apos a primeira geracao.

### Regenerate

- `ClinicalSummaryService.regenerate_summary` limpa `clinical_summary` e `summary_generated_at`, comita, e chama `generate_clinical_summary` para gerar novamente.
- O endpoint `POST /exames/{exame_id}/resumo/regenerate` expoe esse fluxo.

### Comportamento quando `GEMINI_API_KEY` esta ausente

- `ClinicalSummaryService` inicializa `self.client` somente se `settings.GEMINI_API_KEY` estiver configurada.
- Se nao houver key, `generate_clinical_summary` retorna `None` e registra erro: "GEMINI_API_KEY nao configurada".
- No worker, a geracao do resumo e best-effort: excecoes sao capturadas e o processamento pode finalizar como `completed` mesmo sem resumo.
- Nos endpoints de resumo, se a geracao retornar `None`, a API responde com erro 500 (falha ao gerar ou regenerar resumo clinico).

## Seguranca

### MASTER_API_KEY para API Keys (admin)

- Config: `MASTER_API_KEY` em `app/core/config.py`.
- Enforcement: dependency `require_master_key` em `app/core/admin_auth.py`.
- Header: `X-Master-Key`.
- Comportamento:
  - se `MASTER_API_KEY` estiver vazia, retorna 503 (admin desabilitado)
  - se `X-Master-Key` divergir, retorna 401

### X-API-Key para consumo (exames)

- Header: `X-API-Key`.
- Persistencia segura: a chave nao e salva em texto puro, apenas `SHA-256` em `api_keys.key_hash`.
- Validacao:
  - ausencia do header retorna 401
  - chave invalida ou inativa retorna 401

## Testes e verificacao (com evidencia)

Hard fact (executado):

- Verification executed: `.venv/bin/python -m pytest -q` => `77 passed, 22 warnings`.

Evidencias no codigo de testes:

- `app/tests/conftest.py`:
  - cria banco SQLite por teste (`Base.metadata.create_all` e `drop_all`)
  - sobrescreve `get_db` para usar a sessao de teste
  - stub de `celery_app.send_task` para nao disparar worker durante testes
  - cria uma API key valida e retorna `auth_headers = {"X-API-Key": ...}`
  - fornece `master_headers = {"X-Master-Key": ...}` para operacoes admin
- `app/tests/test_exames.py`:
  - valida upload de PDF (200) e rejeicao de nao-PDF (400)
  - lista exames (200)
  - busca exame inexistente (404)
  - garante que o status endpoint retorna `processing_stage`, `processing_percent`, `processing_message` e `status == "pendente"` apos upload
  - cobre endpoints de resumo clinico e regenerate com mocks assincornos (patch em `clinical_summary_service`)

## Itens em aberto / limitacoes / follow-ups

- Resumo clinico depende de `GEMINI_API_KEY`. Quando ausente, os endpoints de resumo retornam 500. Follow-up: padronizar resposta (ex: 503) e adicionar mensagem de indisponibilidade mais clara.
- `AIService` e `ClinicalSummaryService` nao derrubam o processo quando `GEMINI_API_KEY` esta vazia: eles desabilitam a geracao via Gemini e seguem apenas com fallback (quando configurado) ou retornam erro/None conforme o endpoint.
- `rate_limit_per_minute` e retornado por `get_api_client`, mas nao ha enforcement no request path observado. Follow-up: implementar rate limiting ou remover o campo se nao for usado.
- Conversao de percentual para absoluto existe na camada deterministica, mas nao e acionada no fluxo do worker (nao ha `leucocitos_total`). Follow-up: derivar `leucocitos_total` do proprio exame e habilitar conversao quando fizer sentido.
- `decimal_correction.py` oferece sugestoes com score e ranges esperados, mas nao esta acoplado ao fluxo principal do worker mostrado. Follow-up: decidir integracao (ou manter apenas para auditoria e ferramentas internas).
- Upload e armazenamento em disco local (`uploads/`). Follow-up: avaliar persistencia em storage externo e politicas de retencao, principalmente para ambientes com multiplas replicas.
