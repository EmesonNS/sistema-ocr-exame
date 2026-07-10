# Feature: OCR Quality Eval and Knowledge Layer

## Objetivo

Criar um benchmark reproduzivel para medir a qualidade real da extracao OCR do `sistema-ocr-exame`, separando erro de leitura, erro de normalizacao e erro de classificacao clinica.

O benchmark deve permitir:

- medir regressao entre versoes do pipeline;
- localizar tipos de erro por documento, biomarcador e etapa;
- incorporar uma camada versionada de conhecimento tecnico/clinico ao scorer;
- usar um subconjunto curado de documentos reais como base de `golden_exams`.

## Contexto

Hoje o repositorio possui testes unitarios e de integracao, mas nao possui um eval ponta a ponta com `ground truth` real. Isso impede responder com rigor:

- se uma mudanca melhorou ou piorou a qualidade da extracao;
- quais biomarcadores/labs falham mais;
- se o sistema esta convertendo casos `indefinido` em `normal`;
- qual parte do pipeline falhou: OCR, extracao, normalizacao ou regra clinica.

Tambem ja foi identificado que `amostras_exames/` contem documentos reais, mas heterogeneos:

- laudos laboratoriais fonte;
- resumos/pareceres derivados;
- receitas;
- protocolos/planos.

Portanto a pasta atual nao pode ser usada integralmente como `golden_exams` sem curadoria.

## Escopo

Esta feature cobre:

- definicao do benchmark de qualidade OCR;
- definicao do schema de `golden_exams`;
- definicao da camada de conhecimento tecnico/clinico;
- definicao das metricas e regras de scoring;
- curadoria inicial do corpus real em `amostras_exames`;
- criterios para separar `golden set`, `negative set` e documentos fora de benchmark.

Esta feature nao cobre, por si so:

- implementacao completa do runner/scorer;
- anotacao manual de todos os documentos;
- dashboard visual de resultados;
- avaliacao de UX do frontend;
- validacao clinica formal por medico responsavel.

## Arquitetura Conceitual

O eval deve operar em 4 camadas:

1. `corpus`
   PDFs reais e representativos do trafego esperado.

2. `ground truth`
   Verdade anotada manualmente por documento e por biomarcador.

3. `knowledge layer`
   Dicionarios, regras e taxonomias versionadas usadas pelo scorer e pela normalizacao.

4. `runner + scorer`
   Execucao do pipeline real e comparacao automatica com o golden.

## Unidade de Avaliacao

A unidade principal do benchmark deve ser o biomarcador estruturado, nao apenas o documento inteiro.

Cada item avaliado deve conter, no minimo:

- `nome_canonico`
- `valor_raw`
- `valor_numerico`
- `unidade`
- `referencia_min`
- `referencia_max`
- `status_esperado`
- `metadados_documento` relevantes (`laboratorio`, `data_coleta`, tipo de documento)

## Camada de Conhecimento

O eval deve incluir uma camada versionada de conhecimento tecnico/clinico. Essa camada nao serve para "inventar" verdade; ela serve para:

- padronizar comparacoes;
- resolver aliases e nomes canonicos;
- normalizar unidades equivalentes;
- aplicar regras de classificacao clinica seguras;
- explicitar o que e erro grave versus diferenca irrelevante.

### Estrutura minima da camada de conhecimento

O projeto do eval SHOULD prever uma estrutura como:

```text
evaluation/knowledge/
  canonical_biomarkers.json
  unit_aliases.json
  reference_parsing_rules.json
  clinical_rules.json
  lab_patterns.json
```

### Funcoes da camada de conhecimento

- `canonical_biomarkers.json`
  mapa de aliases para nome canonico (`HB`, `Hemoglobina`, `HEMOGLOBINA` -> `HEMOGLOBINA`)

- `unit_aliases.json`
  equivalencias seguras de unidade (`/mm3`, `/mm^3`, `/uL`, `/uL` normalizado conforme regra local)

- `reference_parsing_rules.json`
  regras para comparar referencias em formato texto com min/max normalizados

- `clinical_rules.json`
  regras para status esperado (`normal`, `alto`, `baixo`, `indefinido`, `incoerente`) e para casos de `needs_review`

- `lab_patterns.json`
  heuristicas por laboratorio/layout para suportar analise de erro por origem documental

### Restricoes da camada de conhecimento

- A camada de conhecimento MUST ser versionada.
- A camada de conhecimento MUST ser auditavel por diff.
- A camada de conhecimento MUST NOT sobrescrever o ground truth manual.
- A camada de conhecimento SHOULD ser separada do codigo de inferencia para permitir benchmark estavel entre versoes.

## Requisitos

### EVAL-001: Benchmark ponta a ponta

- O sistema MUST definir um eval ponta a ponta que exercite o pipeline real de extracao e normalizacao.
- O eval MUST medir a saida final que chega ao contrato estruturado do sistema, e nao apenas OCR cru ou mocks.
- Traceability: `EVAL-001`

### EVAL-002: Ground truth estruturado

- O benchmark MUST definir um schema estruturado para `golden_exams`.
- Cada documento do golden MUST conter metadados do arquivo, tipo documental e lista de biomarcadores esperados.
- O golden MUST suportar documentos com zero biomarcadores quando o documento nao for um laudo laboratorial valido.
- Traceability: `EVAL-002`

### EVAL-003: Camada de conhecimento versionada

- O projeto MUST definir uma camada de conhecimento tecnico/clinico separada do golden.
- O scorer MUST usar essa camada para comparacoes canonicas, unidades equivalentes e regras de status.
- A camada MUST ser passivel de evolucao sem invalidar silenciosamente benchmarks anteriores.
- Traceability: `EVAL-003`

### EVAL-004: Metricas por etapa

- O eval MUST medir separadamente:
  - sucesso do documento;
  - recall de biomarcadores;
  - precision de biomarcadores;
  - acerto do valor raw;
  - acerto do valor numerico;
  - acerto de unidade;
  - acerto de referencia;
  - acerto de status clinico;
  - taxa de `needs_review`;
  - taxa de `unsafe_normal`.
- O relatorio MUST permitir agregacao por documento, por biomarcador e por laboratorio.
- Traceability: `EVAL-004`

### EVAL-005: Taxonomia de erro

- O eval MUST classificar erros por tipo.
- A taxonomia minima SHOULD incluir:
  - `missing_biomarker`
  - `unexpected_biomarker`
  - `wrong_raw_value`
  - `wrong_numeric_value`
  - `wrong_unit`
  - `wrong_reference`
  - `wrong_status`
  - `unsafe_normal`
  - `document_type_misclassified`
- Traceability: `EVAL-005`

### EVAL-006: Curadoria do corpus real

- O benchmark MUST separar claramente:
  - `golden_candidates_raw_labs`
  - `derived_outputs_do_not_use_as_source`
  - `negative_documents`
  - `excluded_documents`
- A entrada em `golden` MUST exigir revisao manual.
- A existencia de um PDF em `amostras_exames` MUST NOT implicar entrada automatica no benchmark.
- Traceability: `EVAL-006`

### EVAL-007: Regras para documentos nao laboratoriais

- O benchmark MUST incluir um `negative set` com documentos reais que nao sao laudos laboratoriais.
- O scorer MUST considerar correto quando o sistema rejeita, marca ou retorna zero biomarcadores para esses documentos, conforme contrato definido.
- Receitas, protocolos e planos MUST NOT ser usados como fonte de verdade para extracao laboratorial.
- Traceability: `EVAL-007`

### EVAL-008: Benchmark congelado e shadow set

- O projeto SHOULD manter:
  - um `frozen benchmark` estavel para comparacao entre versoes;
  - um `shadow set` para novos documentos ainda nao promovidos ao benchmark principal.
- Mudancas no frozen benchmark MUST ser versionadas e justificadas.
- Traceability: `EVAL-008`

### EVAL-009: Seguranca clinica

- O eval MUST ter metricas orientadas a risco clinico.
- `unsafe_normal_rate` MUST ser tratada como metrica critica de release.
- Casos `indefinido`, `incoerente` ou sem referencia explicita MUST NOT ser contabilizados como `normal` por default.
- Traceability: `EVAL-009`

### EVAL-010: Reprodutibilidade

- O runner MUST registrar versao do codigo, versao da knowledge layer, dataset usado e data/hora da execucao.
- O relatorio MUST ser reproduzivel sobre o mesmo conjunto de arquivos e configuracao.
- Traceability: `EVAL-010`

## Schema Proposto para Golden

O benchmark SHOULD adotar um schema semelhante a:

```json
{
  "document_id": "laudo_001",
  "file_path": "evaluation/datasets/raw_labs/laudo_001.pdf",
  "document_type": "lab_report",
  "source_status": "real",
  "laboratorio_esperado": "DASA",
  "data_coleta_esperada": "2026-02-04",
  "expected_biomarkers": [
    {
      "name": "HEMOGLOBINA",
      "value_raw": "16,0",
      "value_numeric": 16.0,
      "unit": "g/dL",
      "reference_min": 13.0,
      "reference_max": 17.0,
      "expected_status": "normal"
    }
  ]
}
```

## Curadoria Inicial de `amostras_exames`

### Documentos que ja servem como candidatos reais para `golden`

Os seguintes arquivos SHOULD entrar na fila de anotacao manual como candidatos a `golden_candidates_raw_labs`:

- `Laudo Completo 04_02_2026 (1).pdf`
- `LaudoSabin-AnaRodrigues-13-05-25.pdf`
- `EmissaoDeLaudo.pdf` (se a integridade do PDF for validada no processo de anotacao)

### Documentos reais que nao devem ser fonte de golden laboratorial

Os seguintes arquivos parecem documentos derivados, e MUST NOT ser usados como fonte primaria do golden de extracao:

- `Ana Caroline.pdf`
- `Ana Perla.pdf`
- `Alexsandra.pdf`

Motivo:

- sao resumos/pareceres prontos, nao o laudo laboratorial bruto;
- usar saida derivada como truth contaminaria o benchmark.

### Documentos reais que devem compor o `negative set`

Os seguintes arquivos SHOULD ser usados para validar rejeicao/classificacao de documento nao laboratorial:

- `Receita Alexsandra Ribeiro.pdf`
- `Adicionar plano - Support Clinic.pdf`
- `Protocolo - Ana Perlla.pdf`

### Regra de promocao para `golden`

- Um documento so entra em `golden_exams` apos anotacao manual campo a campo.
- Um documento derivado ou administrativo MUST NOT entrar no `golden` de extracao laboratorial.
- Um documento ambiguo SHOULD permanecer em `shadow set` ate revisao humana.

## Fora de Escopo

- Criar benchmark com centenas de arquivos nesta primeira iteracao.
- Inferir verdades clinicas nao explicitadas no laudo.
- Medir qualidade apenas por semelhanca textual.
- Misturar laudos laboratoriais com resumos medicos como se fossem a mesma classe documental.
- Tratar PDF resumido do proprio sistema como `ground truth` de extracao.

## Criterios de Aceite

- Existe uma spec clara para benchmark OCR com requisitos rastreaveis.
- A camada de conhecimento esta definida como artefato separado e versionado.
- O schema de `golden_exams` esta fechado em nivel suficiente para implementacao.
- As metricas obrigatorias e a taxonomia de erros estao definidas.
- `amostras_exames` esta classificada em candidatos a golden, derivados e negative set.
- A spec deixa explicito que a pasta atual nao e benchmark pronto e exige curadoria manual.
