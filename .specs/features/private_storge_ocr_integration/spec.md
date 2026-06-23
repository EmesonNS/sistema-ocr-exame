# Feature: Private Storge OCR Integration

## Objetivo

Restaurar a integracao correta entre `storge-system`, `storge-service` e `sistema-ocr-exame` sem expor o servico OCR publicamente.

O OCR deve continuar sendo um microservico interno, acessado apenas pelo backend Storge. O Nginx de producao na VPS Hostinger deve expor somente o frontend e a API publica do `storge-service`.

## Contexto

Durante a auditoria de producao foi identificado que a integracao local atual quebrou em relacao ao desenho antigo:

- O branch remoto `storge-service:exam-ai` tinha `ExamService` chamando o OCR com `user_id` como query param.
- O OCR atual ainda espera `user_id` via query em `POST /api/v1/patients/{patient_id}/exames/upload`.
- O backend local atual envia `user_id` como campo multipart, o que causa `422 Unprocessable Entity`.
- O backend local atual tambem usa `userId = 1L`, enquanto o branch antigo usava `UserPrincipal.getId()`.
- O frontend deve falar com o backend Storge, nao com o OCR.

Decisao do side chat em 2026-06-18:

- Nao expor o OCR para fora.
- Manter o OCR acessivel apenas pelo backend, como estava antes.
- Preferir uma rota publica do dominio Storge, nao uma rota publica espelhada do OCR.

## Arquitetura Alvo

```text
Browser
  -> Nginx publico na VPS Hostinger
    -> Frontend static assets
    -> /api/* para storge-service
      -> rede interna Docker/VPS
        -> sistema-ocr-exame
```

## Rota Publica Decidida

O frontend deve chamar o backend Storge:

```text
POST /api/exams/patient/{patientId}/upload
```

Essa rota representa o contrato publico do produto Storge. Ela nao deve revelar a topologia interna do OCR.

## Contrato Interno Backend -> OCR

O backend Storge deve chamar o OCR pela rede interna:

```text
POST {OCR_API_BASE_URL}/patients/{patientId}/exames/upload?user_id={userId}
Header: X-API-Key: {OCR_API_KEY}
Body: multipart/form-data
  file=<PDF>
```

Onde `OCR_API_BASE_URL` deve apontar para o OCR interno com prefixo `/api/v1`, por exemplo:

```text
http://ocr-api:8000/api/v1
```

Em producao, `host.docker.internal` nao deve ser a estrategia primaria.

## Requisitos

### PRI-001: OCR privado

- O servico OCR MUST NOT ser exposto como rota publica no Nginx.
- O servico OCR MUST ser acessivel apenas pelo backend Storge na rede interna da VPS/Docker.
- A API key do OCR MUST permanecer somente no backend/configuracao de servidor.

### PRI-002: Rota publica do produto Storge

- O frontend MUST chamar uma rota publica do `storge-service`.
- A rota publica escolhida SHOULD ser `POST /api/exams/patient/{patientId}/upload`, alinhada ao desenho antigo do branch `exam-ai`.
- O frontend MUST NOT chamar diretamente `/api/v1/patients/{patientId}/exames/upload`.

### PRI-003: Usuario real no upload

- O backend MUST extrair o usuario autenticado real via `UserPrincipal.getId()`.
- O backend MUST NOT usar `userId = 1L` em producao.

### PRI-004: Contrato interno correto com OCR

- O backend MUST enviar `user_id` como query param para o OCR.
- O backend MUST enviar apenas o PDF no multipart body.
- O backend MUST enviar `X-API-Key` no header.

### PRI-005: Nginx na VPS Hostinger

- O Nginx publico MUST rotear `/api/*` para o `storge-service`.
- O Nginx SHOULD configurar `client_max_body_size` suficiente para PDFs.
- O Nginx SHOULD configurar timeouts adequados para upload e respostas do backend.
- O Nginx MUST NOT publicar uma rota direta para o OCR, salvo excecao temporaria documentada e removida antes de producao.

### PRI-006: Execucao via `ssh storge`

- Antes de qualquer alteracao na VPS, a implementacao MUST fazer inspeção read-only via `ssh storge`.
- A inspeção MUST levantar Nginx ativo, compose/systemd ativo, redes Docker, containers, variaveis de ambiente e paths de deploy.
- Alteracoes na VPS MUST ser pequenas, reversiveis e registradas.

## Fora de Escopo

- Reescrever o OCR.
- Expor o OCR publicamente.
- Criar API gateway separado.
- Migrar para Kubernetes.
- Refazer todo o modulo de exames do frontend.

## Evidencias Historicas

- `storge-service:exam-ai` tinha `ExamService.uploadFile()` usando `queryParam("user_id", userId)`.
- `storge-service:exam-ai` tinha `ExamController` usando `@AuthenticationPrincipal UserPrincipal` e `userPrincipal.getId()`.
- OCR atual em `app/api/endpoints/exames.py` declara `user_id: int = Query(...)`.
- Backend local atual em `OcrService.uploadExam()` adiciona `user_id` no multipart body.

## Criterios de Aceite

- Upload de PDF pelo frontend passa por Nginx -> backend -> OCR sem expor OCR.
- Backend envia `user_id` correto no query param.
- OCR retorna `201/200` ou resposta de exame criado, nao `422` por `query.user_id`.
- Status/listagem/detalhe de exame seguem funcionando pela API publica do backend.
- Nginx da VPS nao possui rota publica direta para o OCR.
- Configuracao de producao usa URL interna para OCR.
