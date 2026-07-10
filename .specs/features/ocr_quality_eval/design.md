# Design: OCR Quality Eval and Knowledge Layer

## Objetivo

Materializar um benchmark reproducivel para o `sistema-ocr-exame` que meca a qualidade da saida estruturada final do pipeline e separe:

- erro de ingestao/classificacao documental;
- erro de extracao;
- erro de normalizacao;
- erro de classificacao clinica.

Este design fecha a implementacao de:

- estrutura fisica de `evaluation/`;
- contratos de dataset, knowledge layer e reports;
- estrategia de matching e scoring;
- gates minimos para release;
- fluxo de curadoria do corpus real.

## Fora de Escopo

Este design nao cobre:

- dashboard visual;
- revisao clinica formal por medico;
- anotacao completa de todo o corpus real;
- alteracoes de UX no produto Storge.

## Contexto Tecnico Relevante

O benchmark precisa refletir o comportamento real do pipeline atual:

1. upload de PDF real;
2. extracao multimodal em `app/services/ai_service.py`;
3. normalizacao deterministica em `app/services/biomarker_normalization.py`;
4. guardrails e `needs_review`;
5. persistencia do resultado estruturado.

O eval deve medir a saida final equivalente ao contrato de `ResultadoBiomarcador`, e nao OCR cru ou mocks isolados.

## Arquitetura Proposta

### Estrutura fisica

```text
evaluation/
  README.md
  datasets/
    manifests/
      corpus_manifest.json
    raw_labs/
    derived_outputs_do_not_use_as_source/
    negative_documents/
    excluded_documents/
    shadow_set/
    golden/
      golden_exams.json
  knowledge/
    VERSION.json
    canonical_biomarkers.json
    unit_aliases.json
    reference_parsing_rules.json
    clinical_rules.json
    lab_patterns.json
  reports/
    .gitkeep
  schemas/
    golden_exam.schema.json
    run_report.schema.json
  scripts/
    run_ocr_eval.py
    curate_corpus.py
    export_eval_report.py
```

### Componentes

1. `datasets/manifests/corpus_manifest.json`
   Catalogo canonico dos arquivos do benchmark e de seus estados de curadoria.

2. `datasets/golden/golden_exams.json`
   Fonte de verdade manual, versionada, para o scorer.

3. `knowledge/`
   Camada versionada separada do golden, usada para canonizacao, equivalencias e regras seguras de comparacao.

4. `scripts/run_ocr_eval.py`
   Runner ponta a ponta. Executa o pipeline real sobre o corpus-alvo e coleta a saida estruturada final.

5. `scripts/export_eval_report.py`
   Gera artefatos em JSON e CSV para consumo humano e gates de release.

6. `reports/`
   Pasta de saida versionavel por convencao, mas sem commitar resultados efemeros por default.

## Contratos de Dados

### Manifesto do corpus

Cada documento catalogado no corpus deve conter no minimo:

```json
{
  "document_id": "laudo_dasa_2026_02_04",
  "file_path": "evaluation/datasets/raw_labs/Laudo Completo 04_02_2026 (1).pdf",
  "corpus_class": "golden_candidate_raw_lab",
  "document_type_expected": "lab_report",
  "source_status": "real",
  "curation_status": "pending_annotation",
  "notes": "PDF multipagina com texto extraivel"
}
```

`corpus_class` aceita:

- `golden_candidate_raw_lab`
- `derived_output_do_not_use_as_source`
- `negative_document`
- `excluded_document`
- `shadow_document`

### Golden exam

O arquivo `golden_exams.json` deve seguir um schema unico por documento:

```json
{
  "document_id": "laudo_dasa_2026_02_04",
  "file_path": "evaluation/datasets/raw_labs/Laudo Completo 04_02_2026 (1).pdf",
  "document_type": "lab_report",
  "source_status": "real",
  "laboratorio_esperado": "DASA",
  "data_coleta_esperada": "2026-02-04",
  "expected_behavior": "extract_biomarkers",
  "expected_biomarkers": [
    {
      "name": "HEMOGLOBINA",
      "value_raw": "16,0",
      "value_numeric": 16.0,
      "unit": "g/dL",
      "reference_min": 13.0,
      "reference_max": 17.0,
      "expected_status": "normal",
      "allows_tolerance": false
    }
  ]
}
```

Para `negative_documents`, o schema deve permitir:

```json
{
  "document_id": "receita_alexsandra",
  "file_path": "evaluation/datasets/negative_documents/Receita Alexsandra Ribeiro.pdf",
  "document_type": "non_lab_document",
  "source_status": "real",
  "expected_behavior": "reject_or_zero_biomarkers",
  "expected_biomarkers": []
}
```

### Knowledge layer

Cada arquivo em `knowledge/` deve ser auditavel por diff e carregado explicitamente pelo scorer.

`VERSION.json` deve registrar:

```json
{
  "knowledge_version": "1.0.0",
  "updated_at": "2026-07-04T00:00:00Z",
  "notes": "Baseline inicial do OCR eval"
}
```

## Estrategia de Matching

### Matching de documento

O runner identifica o documento pelo `document_id` do manifest e associa a execucao ao item correspondente do golden.

### Matching de biomarcadores

O scorer deve aplicar a sequencia:

1. canonizar `nome_marcador` pela knowledge layer;
2. separar entradas por nome canonico;
3. para nomes repetidos, tentar pareamento por:
   - unidade normalizada;
   - proximidade de referencia;
   - proximidade numerica;
   - ordem estavel de aparicao como desempate final.

### Regras de comparacao

- `raw_value_accuracy`
  comparacao estrita apos limpeza minima de espacos.
- `numeric_value_accuracy`
  comparacao por igualdade numerica normalizada.
- `unit_accuracy`
  comparacao por unidade canonica usando `unit_aliases.json`.
- `reference_accuracy`
  comparacao por `referencia_min` e `referencia_max` normalizados.
- `status_accuracy`
  comparacao por status final seguro: `normal|alto|baixo|indefinido|incoerente`.

Nao deve haver tolerancia numerica frouxa por default. Qualquer tolerancia futura deve ser explicita por biomarcador/regra no knowledge layer, nunca implicita no scorer.

## Metricas e Reports

### Metricas obrigatorias

O runner deve produzir pelo menos:

- `document_success_rate`
- `biomarker_recall`
- `biomarker_precision`
- `raw_value_accuracy`
- `numeric_value_accuracy`
- `unit_accuracy`
- `reference_accuracy`
- `status_accuracy`
- `needs_review_rate`
- `unsafe_normal_rate`

### Agregacoes obrigatorias

O report deve agregar por:

- execucao total;
- documento;
- laboratorio;
- nome canonico de biomarcador;
- tipo de erro.

### Taxonomia minima de erro

O scorer deve emitir:

- `missing_biomarker`
- `unexpected_biomarker`
- `wrong_raw_value`
- `wrong_numeric_value`
- `wrong_unit`
- `wrong_reference`
- `wrong_status`
- `unsafe_normal`
- `document_type_misclassified`

### Formato de saida

O report principal em JSON deve conter:

```json
{
  "run_id": "2026-07-04T12-00-00Z",
  "code_version": "git-sha",
  "knowledge_version": "1.0.0",
  "dataset_version": "corpus-v1",
  "executed_at": "2026-07-04T12:00:00Z",
  "summary": {
    "document_success_rate": 0.0,
    "biomarker_recall": 0.0,
    "biomarker_precision": 0.0,
    "raw_value_accuracy": 0.0,
    "numeric_value_accuracy": 0.0,
    "unit_accuracy": 0.0,
    "reference_accuracy": 0.0,
    "status_accuracy": 0.0,
    "needs_review_rate": 0.0,
    "unsafe_normal_rate": 0.0
  },
  "documents": [],
  "errors": []
}
```

CSV complementar:

- `document_summary.csv`
- `biomarker_summary.csv`
- `error_taxonomy.csv`

## Regras para Negative Set

Documentos em `negative_documents/` nao devem ser avaliados como laudo laboratorial com matching de biomarcadores.

O comportamento correto aceitavel sera:

- rejeicao explicita por tipo documental; ou
- execucao concluida com zero biomarcadores.

Qualquer extracao de biomarcadores nesses casos deve gerar:

- `unexpected_biomarker`
- possivelmente `document_type_misclassified`

## Reprodutibilidade e Versionamento

### Versoes obrigatorias por run

Cada execucao deve registrar:

- `git sha` do codigo;
- `knowledge_version`;
- identificador do dataset/manifest;
- timestamp da execucao;
- modo de execucao (`local`, `docker`, `api-live`).

### Frozen benchmark e shadow set

- `golden/` representa o benchmark congelado.
- `shadow_set/` recebe documentos reais ainda nao promovidos.
- promocao de `shadow_set` para `golden` exige anotacao manual e diff rastreavel no manifest e no golden.

## Integracao com o Codigo Atual

O runner deve preferir reuso do pipeline real, nao duplicacao de logica:

- chamar `AIService` e `biomarker_normalization` via codigo quando rodando in-process; ou
- chamar o endpoint real da API OCR quando rodando contra stack Docker/local.

O scorer deve tratar a saida no formato proximo ao contrato de `ResultadoBiomarcador`.

Isso evita um eval "paralelo" que diverge do comportamento entregue ao produto.

## Estrategia de Implementacao

### Fase 1

- criar estrutura `evaluation/`;
- criar schemas;
- criar manifest do corpus;
- classificar os 9 documentos atuais;
- seed inicial da knowledge layer.

### Fase 2

- implementar runner base;
- implementar scorer com matching canonico;
- emitir report JSON e CSV;
- adicionar testes unitarios do scorer.

### Fase 3

- anotar manualmente os 3 primeiros `golden_candidates_raw_labs`;
- validar `negative_documents`;
- definir gate inicial de release com foco em `unsafe_normal_rate`.

## Gates Iniciais

Antes de usar o eval como gate de release, o sistema deve cumprir:

- `unsafe_normal_rate == 0` no frozen benchmark inicial;
- nenhum `negative_document` pode retornar biomarcadores sem ser contabilizado como erro;
- report reproduzivel com mesmo dataset e mesma knowledge layer;
- erro por documento e por biomarcador visivel no report.

## Riscos Conhecidos

- usar PDF derivado como truth invalida o benchmark;
- executar o runner por API live sem controle de versao do modelo pode introduzir variacao entre runs;
- tolerancia numerica implicita mascara regressao;
- frozen benchmark pequeno demais gera falsa confianca.

## Traceability

- `EVAL-001`: runner ponta a ponta
- `EVAL-002`: schema de golden e suporte a zero biomarcadores
- `EVAL-003`: knowledge layer separada e versionada
- `EVAL-004`: metricas por etapa e agregacoes
- `EVAL-005`: taxonomia de erro
- `EVAL-006`: separacao fisica e logica do corpus real
- `EVAL-007`: contrato do negative set
- `EVAL-008`: frozen benchmark e shadow set
- `EVAL-009`: gate clinico com `unsafe_normal_rate`
- `EVAL-010`: versoes e reproducao por run
