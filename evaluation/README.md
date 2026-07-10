# Evaluation

Benchmark e knowledge layer do OCR.

Este diretorio existe para separar:

- corpus real curado;
- golden anotado manualmente;
- knowledge layer versionada;
- reports reproduciveis;
- scripts de runner/scorer;
- comparacao objetiva entre duas runs scored.

Estado atual:

- a estrutura base foi materializada;
- o corpus real foi classificado em candidatos, derivados e negativos;
- existe um baseline inicial de `golden_exams` anotado manualmente com 2 laudos reais;
- `EmissaoDeLaudo.pdf` permaneceu em shadow set por decisão de curadoria;
- o `negative set` ja foi validado em run real, com os 3 documentos bloqueados por `Nenhum dado extraído do documento`;
- o runner agora suporta `api` e `in-process`, e o caminho local foi coberto com um fake AI service nos testes;
- resultados efemeros nao devem ser versionados como baseline;
- existe comparador de runs scored para registrar regressao ou ganho entre duas execucoes.

Regra canonica:

- `golden` so entra com anotacao manual campo a campo;
- documentos derivados nao podem ser usados como truth para benchmark laboratorial;
- documentos nao laboratoriais ficam no `negative_documents`.
