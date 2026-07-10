# Knowledge Layer

Camada versionada de conhecimento tecnico/clinico usada pelo OCR eval para canonizacao, aliases, equivalencias de unidade, regras de referencia, regras clinicas e padroes de laboratorio.

## Estado Atual

- seed inicial criada;
- arquivos auditaveis por diff;
- loader usado pelo scorer em `evaluation/scripts/score_eval_report.py`;
- contratos principais cobertos por testes em `evaluation/tests/`;
- knowledge versionada por `VERSION.json`.

## Regras

- a knowledge layer nao substitui o ground truth manual;
- aliases e regras de unidade devem ser conservadores;
- qualquer evolucao precisa manter versionamento explicito;
- mudancas nesta camada devem ser avaliadas contra reports versionados antes de virar claim de melhoria clinica;
- o scorer atual e minimo/conservador: mede matching estrutural e metricas criticas como `unsafe_normal_rate`, mas nao deve ser descrito como validação clinica completa de valor, unidade, referencia e status.
