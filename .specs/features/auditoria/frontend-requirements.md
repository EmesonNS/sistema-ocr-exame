# Frontend Requirements: Dashboard de Auditoria

## Objetivo

Permitir conferência humana rápida e confiável dos biomarcadores extraídos, usando as superfícies de backend já existentes para evidência visual e validação.

## Escopo

O dashboard deve consumir apenas a API pública do backend `storge-service`.

Superfícies já disponíveis:

- `GET /api/v1/patients/{patientId}/exames`
- `GET /api/v1/exames/{exameId}`
- `GET /api/v1/exames/{exameId}/status`
- `GET /api/v1/exames/{exameId}/arquivo`
- `GET /api/v1/exames/{exameId}/resumo`
- `GET /api/v1/exames/{exameId}/fhir`
- `GET /api/v1/exames/{exameId}/resultados/{resultadoId}/evidence`
- `POST /api/v1/exames/{exameId}/resultados/{resultadoId}/verify`

## Requisitos Funcionais

### A1: Lista operacional de exames

- O dashboard MUST exibir uma tabela/lista paginada de exames.
- A lista SHOULD mostrar `status_processamento`, `processing_stage`, data, laboratório, nome do arquivo e estado de revisão.
- A lista SHOULD permitir filtro por `patientId`, status e pendência de revisão humana.
- A paginação MUST respeitar o contrato de backend existente.

### A2: Visão detalhada por exame

- O dashboard MUST abrir uma visão detalhada para um exame selecionado.
- A visão MUST mostrar biomarcadores, referência, unidade, confiança, status clínico e marcação de revisão humana.
- A visão SHOULD exibir o resumo clínico quando disponível.
- A visão SHOULD expor o arquivo original persistido para inspeção.

### A3: Evidência visual por biomarcador

- O dashboard MUST mostrar o recorte visual associado a cada biomarcador.
- A visualização MUST usar o endpoint de `evidence` como fonte primária.
- A interface SHOULD destacar `page_number` e `bounding_box` para orientar a auditoria.
- Quando a evidência não estiver disponível, o dashboard MUST informar isso de forma explícita.

### A4: Fluxo de verificação humana

- O dashboard MUST permitir marcar um biomarcador como verificado.
- O estado de verificação MUST refletir o campo `is_human_verified`.
- O fluxo SHOULD mostrar feedback de sucesso, erro e estado já verificado.
- A ação de verificação SHOULD ser restrita a usuários com permissão de auditoria.

### A5: Acesso ao relatório FHIR

- O dashboard SHOULD oferecer uma ação para inspecionar o Bundle FHIR do exame.
- O foco da UI MUST ser conferência humana, não edição clínica do Bundle.

## Requisitos Não Funcionais

- A UI MUST ser responsiva para desktop e tablet.
- A UI SHOULD priorizar leitura rápida, com hierarquia visual clara para status, risco e revisão.
- A UI MUST evitar chamar OCR diretamente; tudo deve passar pelo backend Storge.
- A UI SHOULD tratar carregamento lento de crops como estado explícito, sem travar a tela inteira.
- A UI SHOULD registrar estados de erro por exame e por biomarcador.

## Estados de Interface

- `loading`: busca inicial de exames e detalhes.
- `empty`: nenhum exame encontrado.
- `review_pending`: biomarcador sem validação humana.
- `reviewed`: biomarcador validado.
- `evidence_missing`: não foi possível gerar o crop.
- `processing`: exame ainda em processamento.
- `failed`: exame terminou em erro.

## Critérios de Aceitação

- Um auditor consegue localizar um exame, abrir seus biomarcadores, visualizar o crop e marcar verificação sem sair do dashboard.
- O dashboard usa exclusivamente as APIs públicas do backend.
- O estado de revisão humana fica consistente com o backend após refresh.
- O dashboard deixa claro quando a evidência visual está ausente ou ainda em geração.
