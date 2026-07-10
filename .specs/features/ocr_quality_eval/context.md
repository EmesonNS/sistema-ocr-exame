# Contexto Consolidado: OCR Quality Eval and Knowledge Layer

## Status da Fase

- `spec.md` foi criada e ja fecha o problema, escopo, requisitos e criterios de aceite da feature.
- `design.md` ainda nao existe.
- `tasks.md` ainda nao existe.
- Esta feature deve ser retomada pela fase de design, nao pela fase de descoberta.

## Problema Ja Confirmado

O repositorio `sistema-ocr-exame` possui:

- testes unitarios e de integracao;
- testes de normalizacao de biomarcadores;
- testes de API, guardrails e agentic loop;

mas nao possui:

- eval ponta a ponta com `ground truth` real;
- dataset golden estruturado;
- metricas automatizadas de qualidade por documento/biomarcador;
- relatorio de regressao entre versoes do pipeline.

Consequencia:

- nao existe forma objetiva de medir se uma mudanca melhorou ou piorou a qualidade da extracao;
- nao existe score confiavel por biomarcador, laboratorio ou tipo de erro;
- nao existe gate quantitativo para release com foco em risco clinico.

## Estado do Codigo Relacionado

Ja existe base util no codigo para um eval:

- camada de normalizacao em `app/services/biomarker_normalization.py`
- testes unitarios de normalizacao em `app/tests/test_biomarker_normalization.py`
- guardrails clinicos e de seguranca
- suporte a `needs_review`
- suporte a `status_alerta`
- suporte a coordenadas visuais (`bounding_box`, `page_number`)
- suporte a `LOINC` e serializacao `FHIR`

Isso significa que o eval deve medir a saida final estruturada do sistema, nao apenas OCR bruto.

## Decisoes Ja Fechadas na Spec

### Unidade principal de avaliacao

O eval sera centrado em biomarcador estruturado, nao apenas em documento.

Campos minimos por item:

- `nome_canonico`
- `valor_raw`
- `valor_numerico`
- `unidade`
- `referencia_min`
- `referencia_max`
- `status_esperado`
- metadados documentais relevantes

### Camadas do eval

O eval foi dividido conceitualmente em 4 camadas:

1. `corpus`
2. `ground truth`
3. `knowledge layer`
4. `runner + scorer`

### Knowledge layer

A feature ja assume uma camada versionada de conhecimento tecnico/clinico separada do golden.

Estrutura minima prevista:

```text
evaluation/knowledge/
  canonical_biomarkers.json
  unit_aliases.json
  reference_parsing_rules.json
  clinical_rules.json
  lab_patterns.json
```

### Metricas obrigatorias

Ja fechadas como obrigatorias:

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

### Taxonomia minima de erros

Ja fechada:

- `missing_biomarker`
- `unexpected_biomarker`
- `wrong_raw_value`
- `wrong_numeric_value`
- `wrong_unit`
- `wrong_reference`
- `wrong_status`
- `unsafe_normal`
- `document_type_misclassified`

### Regra clinica critica

`unsafe_normal_rate` foi promovida a metrica critica de release.

Tambem ficou fechado que:

- `indefinido` nao pode virar `normal` por default no eval;
- `incoerente` nao pode ser tratado como normal;
- documentos sem referencia explicita nao devem gerar classificacao segura sem regra clara.

## Corpus Real Ja Inspecionado

Foi inspecionada a pasta:

- `/mnt/storage/repos/storge/sistema-ocr-exame/amostras_exames`

Contagem observada no momento da analise:

- `9` arquivos

Classificacao observada:

### Candidatos a laudo laboratorial fonte

- `Laudo Completo 04_02_2026 (1).pdf`
- `LaudoSabin-AnaRodrigues-13-05-25.pdf`
- `EmissaoDeLaudo.pdf` sob validacao de integridade

### Documentos derivados que nao servem como fonte de golden de extracao

- `Ana Caroline.pdf`
- `Ana Perla.pdf`
- `Alexsandra.pdf`

Motivo:

- sao resumos/pareceres prontos;
- nao representam o laudo laboratorial bruto;
- contaminariam o benchmark se usados como truth da extracao.

### Documentos reais para `negative set`

- `Receita Alexsandra Ribeiro.pdf`
- `Adicionar plano - Support Clinic.pdf`
- `Protocolo - Ana Perlla.pdf`

Motivo:

- sao documentos reais, mas nao sao laudos laboratoriais;
- servem para avaliar classificacao/rejeicao de documentos nao alvo.

## Evidencias Ja Observadas no Corpus

### `Laudo Completo 04_02_2026 (1).pdf`

- PDF real com texto extraivel.
- `pdfinfo` reportou `Pages: 21`.
- Contem dados laboratoriais estruturados e varios biomarcadores.
- Ja foi usado em validacao local da extracao.

### `LaudoSabin-AnaRodrigues-13-05-25.pdf`

- PDF real multipagina.
- `pdfinfo` reportou `Pages: 29`.
- Contem hemograma e varios exames laboratoriais.

### `EmissaoDeLaudo.pdf`

- Conteudo aparente de laudo laboratorial.
- `file` reportou `data`, portanto a integridade/legibilidade precisa ser confirmada antes de promover a golden candidate.

## Decisao Ja Fechada sobre `amostras_exames`

A pasta `amostras_exames/`:

- serve como corpus inicial real;
- nao serve como `golden_exams` pronto;
- exige curadoria manual e anotacao campo a campo antes de promocao ao benchmark.

## Formato Basico de Golden Ja Fechado

Schema base ja aprovado na spec:

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

## Regras de Curadoria Ja Fechadas

- nenhum PDF entra automaticamente no golden;
- promocao para golden exige anotacao manual;
- documentos derivados nao entram no golden de extracao;
- documentos administrativos ou terapeuticos entram, no maximo, como `negative set`;
- documentos ambiguos devem permanecer em `shadow set` ate revisao.

## O que Falta na Proxima Sessao

### Design

O `design.md` deve fechar:

- estrutura fisica de `evaluation/`
- formato final dos arquivos de knowledge layer
- formato do relatorio JSON/CSV
- estrategia de matching entre extraido e esperado
- regras de tolerancia numerica e equivalencia de unidade
- contrato do `negative set`
- estrategia de versionamento do benchmark

### Tasks

O `tasks.md` deve quebrar pelo menos:

- estrutura de pastas de `evaluation/`
- schema e seed de `golden_exams`
- knowledge layer inicial
- runner
- scorer
- relatorio
- curadoria/anotacao dos 3 primeiros documentos candidatos
- teste de `negative set`

## Riscos e Cuidados Ja Conhecidos

- usar PDFs derivados como truth invalida o benchmark;
- medir apenas texto cru mascara erro clinico;
- tolerancia frouxa demais pode esconder regressao perigosa;
- benchmark muito pequeno nao sustenta decisao de release;
- benchmark muito heterogeneo sem estratificacao gera score pouco acionavel.

## Ponto de Retomada Recomendado

Na proxima sessao:

1. abrir `spec.md`
2. abrir este `context.md`
3. produzir `design.md`
4. depois quebrar em `tasks.md`
