# Tasks: OCR Quality Eval and Knowledge Layer

## Sequencia Recomendada

1. `T-EVAL-001` para materializar a estrutura fisica do benchmark.
2. `T-EVAL-002` e `T-EVAL-003` para fechar contratos de dados e knowledge layer.
3. `T-EVAL-004` para curar o corpus real atual.
4. `T-EVAL-005` e `T-EVAL-006` para implementar runner e scorer.
5. `T-EVAL-007` para relatorios e gates.
6. `T-EVAL-008` para cobertura automatizada.
7. `T-EVAL-009` e `T-EVAL-010` para anotacao inicial do golden e validacao do negative set.

Regras de execucao:

- Nao promover documento para `golden` sem anotacao manual.
- Nao usar documentos derivados como fonte de truth.
- O primeiro gate clinico obrigatorio e `unsafe_normal_rate`.

## T-EVAL-001: Criar estrutura `evaluation/`

**Objetivo:** materializar a arvore base do benchmark no repositorio.

- [x] Criar `evaluation/datasets/`, `evaluation/knowledge/`, `evaluation/reports/`, `evaluation/schemas/` e `evaluation/scripts/`.
- [x] Adicionar `README.md` explicando o proposito da pasta e a regra de que `golden` so aceita anotacao manual.
- [x] Adicionar placeholders minimos versionaveis para manifests, schemas e reports.
- **Done when:** A pasta `evaluation/` existe e bate com o design da feature.
- **Gate:** Nenhum arquivo de resultado efemero e commitado como baseline de report.
- **Onde:** `evaluation/`
- **Reusa:** `design.md`, `STATE.md` DEC-022 e DEC-023.
- **Testes/Comandos:** `find evaluation -maxdepth 3 -type d`, revisao manual da arvore.

## T-EVAL-002: Definir schemas e contratos do dataset

**Objetivo:** fechar os contratos de `corpus_manifest`, `golden_exams` e `run_report`.

- [x] Criar `golden_exam.schema.json`.
- [x] Criar `run_report.schema.json`.
- [x] Criar seed inicial de `corpus_manifest.json`.
- [x] Garantir suporte a `expected_biomarkers: []` para `negative_documents`.
- **Done when:** Os contratos de dados do eval existem e conseguem validar manifests e reports.
- **Gate:** Schemas cobrem `lab_report` e `non_lab_document`.
- **Onde:** `evaluation/schemas/`, `evaluation/datasets/manifests/`
- **Depende de:** `T-EVAL-001`.
- **Reusa:** `spec.md` EVAL-002, EVAL-007, EVAL-010.
- **Testes/Comandos:** validacao local com JSON Schema em fixture positiva e negativa.

## T-EVAL-003: Seed inicial da knowledge layer

**Objetivo:** criar a camada versionada minima para canonizacao e comparacao segura.

**Status:** concluido para o escopo minimo. A seed inicial foi criada, o loader do scorer carrega a pasta versionada e a validacao automatizada existe.

- [x] Criar `VERSION.json`.
- [x] Criar `canonical_biomarkers.json`.
- [x] Criar `unit_aliases.json`.
- [x] Criar `reference_parsing_rules.json`.
- [x] Criar `clinical_rules.json`.
- [x] Criar `lab_patterns.json`.
- **Done when:** O scorer consegue carregar a knowledge layer sem depender de constantes hardcoded dispersas.
- **Gate:** Cada arquivo tem estrutura minima documentada e diff auditavel.
- **Onde:** `evaluation/knowledge/`
- **Depende de:** `T-EVAL-001`.
- **Reusa:** `app/services/biomarker_normalization.py`, `design.md`, EVAL-003.
- **Testes/Comandos:** loader do scorer ou fixture dedicada carregando todos os arquivos sem erro.

## T-EVAL-004: Curadoria inicial de `amostras_exames`

**Objetivo:** classificar o corpus real atual nas categorias corretas do benchmark.

- [x] Catalogar os 9 PDFs atuais em `corpus_manifest.json`.
- [x] Marcar `Laudo Completo 04_02_2026 (1).pdf`, `LaudoSabin-AnaRodrigues-13-05-25.pdf` e `EmissaoDeLaudo.pdf` como `golden_candidate_raw_lab` ou `shadow_document` conforme integridade.
- [x] Marcar `Ana Caroline.pdf`, `Ana Perla.pdf` e `Alexsandra.pdf` como `derived_output_do_not_use_as_source`.
- [x] Marcar `Receita Alexsandra Ribeiro.pdf`, `Adicionar plano - Support Clinic.pdf` e `Protocolo - Ana Perlla.pdf` como `negative_document`.
- **Done when:** Todo PDF em `amostras_exames/` tem classificacao explicita no manifest.
- **Gate:** Nenhum documento ambiguo entra no `golden` automaticamente.
- **Onde:** `evaluation/datasets/manifests/corpus_manifest.json`
- **Depende de:** `T-EVAL-002`.
- **Reusa:** `context.md`, `STATE.md` DEC-022.
- **Testes/Comandos:** `find amostras_exames -type f | wc -l`, checagem de cobertura 1:1 no manifest.

## T-EVAL-005: Implementar runner ponta a ponta

**Objetivo:** executar o pipeline real do OCR sobre um conjunto de documentos do corpus.

**Status:** concluido para o escopo minimo. O runner existe, gera reporte e registra terminais bloqueados; o modo `in-process` agora tambem esta suportado sem depender de HTTP.

- [x] Criar `run_ocr_eval.py`.
- [x] Suportar modo de execucao local/in-process.
- [x] Registrar `run_id`, `git sha`, `knowledge_version`, dataset e timestamp.
- [x] Persistir artefato bruto da run para o scorer.
- **Done when:** Uma execucao do runner produz saida estruturada rastreavel por documento.
- **Gate:** Runner usa o pipeline real, nao mocks, para a extracao avaliada.
- **Onde:** `evaluation/scripts/run_ocr_eval.py`
- **Depende de:** `T-EVAL-002`, `T-EVAL-003`, `T-EVAL-004`.
- **Reusa:** `app/services/ai_service.py`, `app/services/biomarker_normalization.py`, endpoints de exames, EVAL-001 e EVAL-010.
- **Testes/Comandos:** execucao controlada sobre 1 documento real e 1 `negative_document`.

## T-EVAL-006: Implementar scorer e matching canonico

**Objetivo:** comparar o resultado extraido com o golden e classificar erros.

**Status:** concluido para o escopo minimo. O scorer agora produz summary, detalhes por documento e findings tipados; o refinamento do golden continua como proximo passo.

- [x] Implementar matching de biomarcadores por nome canonico.
- [x] Implementar regras de comparacao para raw, numerico, unidade, referencia e status.
- [x] Implementar taxonomia de erro minima.
- [x] Implementar metricas agregadas e por documento.
- **Done when:** O scorer produz summary, detalhes por documento e lista de erros tipados.
- **Gate:** `unsafe_normal` e `document_type_misclassified` aparecem explicitamente no report.
- **Onde:** `evaluation/scripts/run_ocr_eval.py` ou modulo dedicado em `evaluation/scripts/`
- **Depende de:** `T-EVAL-003`, `T-EVAL-005`.
- **Reusa:** `design.md`, EVAL-004, EVAL-005, EVAL-009.
- **Testes/Comandos:** fixtures com casos de `missing_biomarker`, `wrong_status`, `unsafe_normal`.

## T-EVAL-007: Exportar reports e gates de release

**Objetivo:** transformar a saida do scorer em artefatos consumiveis por humano e CI.

**Status:** concluido para o escopo minimo. O export consolidado, o gate minimo e a comparacao entre runs existem; ainda falta ligar isso a um baseline manual real.

- [x] Exportar report principal em JSON.
- [x] Exportar CSVs de sumario por documento, biomarcador e taxonomia.
- [x] Implementar gate inicial para `unsafe_normal_rate`.
- [x] Documentar como comparar duas runs.
- **Done when:** O eval gera artefatos em `evaluation/reports/` e falha quando gate critico e violado.
- **Gate:** `unsafe_normal_rate > 0` quebra a run com status nao verde.
- **Onde:** `evaluation/scripts/export_eval_report.py`, `evaluation/reports/`, `evaluation/README.md`
- **Depende de:** `T-EVAL-006`.
- **Reusa:** EVAL-004, EVAL-009, EVAL-010.
- **Testes/Comandos:** run de fixture com falha forcada em `unsafe_normal_rate`.

## T-EVAL-008: Cobertura automatizada do benchmark

**Objetivo:** proteger runner, scorer e knowledge layer com testes automatizados.

**Status:** concluido para o escopo minimo. Existe cobertura para manifest, metadata do runner, runner `in-process`, scorer e export consolidado.

- [x] Criar testes unitarios do scorer.
- [x] Criar testes de schema/manifest.
- [x] Criar testes de `negative_document`.
- [x] Mockar provedores externos quando o teste nao precisar de execucao real.
- **Done when:** O benchmark tem cobertura automatizada suficiente para evolucao segura.
- **Gate:** Suite de testes do eval roda em Pytest sem depender de chamadas externas reais.
- **Onde:** `app/tests/` ou `evaluation/tests/` conforme padrao definido na implementacao.
- **Depende de:** `T-EVAL-002`, `T-EVAL-003`, `T-EVAL-006`, `T-EVAL-007`.
- **Reusa:** `.specs/codebase/TESTING.md`
- **Testes/Comandos:** `pytest` focado no eval.

## T-EVAL-009: Anotar baseline inicial do golden

**Objetivo:** promover os primeiros laudos reais para `golden_exams` com anotacao manual.

- [x] Anotar manualmente `Laudo Completo 04_02_2026 (1).pdf`.
- [x] Anotar manualmente `LaudoSabin-AnaRodrigues-13-05-25.pdf`.
- [x] Validar `EmissaoDeLaudo.pdf` e decidir por mantê-lo em `shadow_document`.
- [x] Registrar metadados documentais e biomarcadores esperados.
- **Done when:** Existe um baseline inicial de `golden_exams` com pelo menos 2 documentos reais completos e 1 decisao documentada sobre `EmissaoDeLaudo.pdf`.
- **Gate:** Toda promocao para golden possui revisao manual campo a campo.
- **Onde:** `evaluation/datasets/golden/golden_exams.json`, `evaluation/datasets/manifests/corpus_manifest.json`
- **Depende de:** `T-EVAL-004`.
- **Reusa:** `context.md`, `design.md`, EVAL-002, EVAL-006, EVAL-008.
- **Testes/Comandos:** validacao do arquivo contra schema e revisao manual cruzada com o PDF.

## T-EVAL-010: Validar negative set e contrato documental

**Objetivo:** garantir que documentos nao laboratoriais sejam tratados corretamente pelo benchmark.

- [x] Rodar o runner sobre os 3 `negative_documents`.
- [x] Confirmar comportamento `reject_or_zero_biomarkers`.
- [x] Garantir contabilizacao correta de `unexpected_biomarker` e `document_type_misclassified` quando houver erro.
- **Done when:** O negative set participa da run e possui resultado verificavel no report.
- **Gate:** Nenhum `negative_document` passa como laudo valido sem erro explicito no report.
- **Onde:** `evaluation/scripts/run_ocr_eval.py`, `evaluation/datasets/negative_documents/`, `evaluation/reports/`
- **Depende de:** `T-EVAL-005`, `T-EVAL-006`, `T-EVAL-007`.
- **Reusa:** EVAL-007, EVAL-009.
- **Testes/Comandos:** execucao do eval sobre `negative_documents` e inspecao do report.

## Criterios de Fechamento da Feature

- `design.md` e `tasks.md` refletem integralmente `spec.md`.
- A estrutura de `evaluation/` esta implementada.
- O corpus inicial esta classificado.
- O runner e o scorer existem.
- O benchmark mede `unsafe_normal_rate`.
- Existe baseline inicial de golden com documentos reais anotados manualmente.
