# Tasks: Private Storge OCR Integration

## Execucao para Antigravity CLI

Sequencia recomendada:

1. `T-PRI-001` para fechar a fotografia real da VPS.
2. `T-PRI-003` e `T-PRI-004` no backend, porque a chamada ao OCR depende do usuario real e do contrato correto.
3. `T-PRI-002` no frontend, para alinhar a rota publica do produto Storge.
4. `T-PRI-005` na configuracao de producao/Nginx.
5. `T-PRI-006` para validar o fluxo fim-a-fim.

Regras para a delegacao:

- Uma tarefa por vez, salvo `T-PRI-003` + `T-PRI-004`, que podem ser tratadas em sequencia no mesmo lote.
- Nao alterar a VPS fora de `T-PRI-001`, `T-PRI-005` e `T-PRI-006`.
- Manter o OCR privado; qualquer exposicao publica do OCR e regressao.

## T-PRI-001: Inspecionar VPS via `ssh storge`

**Objetivo:** levantar o estado real da VPS antes de qualquer mudanca.

- [x] Executar inspeção read-only da VPS.
- [x] Identificar configuracao Nginx ativa.
- [x] Identificar como `storge-service`, `storge-system` e OCR rodam em producao.
- [x] Identificar rede Docker, compose files, env files e portas expostas.
- [x] Registrar qualquer diferenca entre a VPS e os repositorios locais.
- **Done when:** Existe um resumo com paths reais da VPS, containers ativos, Nginx ativo e URL interna possivel para OCR.
- **Gate:** Nenhuma alteracao feita na VPS nesta tarefa.
- **Onde:** VPS Hostinger via `ssh storge`.
- **Reusa:** `STATE.md` DEC-019 a DEC-021.
- **Testes/Comandos:** `ssh storge`, `docker ps`, `docker compose ls`, `systemctl status nginx`, `nginx -T`, `ss -ltnp`.

## T-PRI-002: Restaurar contrato publico frontend -> backend

**Objetivo:** fazer o frontend chamar apenas a API publica do `storge-service`.

- [x] Ajustar frontend para chamar `POST /api/exams/patient/{patientId}/upload`.
- [x] Garantir que o frontend nao chame OCR direto.
- [x] Garantir que a API key do OCR nao aparece em bundle/env frontend.
- **Done when:** Upload/listagem/status usam apenas API publica do backend Storge.
- **Gate:** Build do frontend passa.
- **Onde:** `storge-system/src/services/exams.ts`, `storge-system/src/services/ocrApi.ts`, `storge-system/src/services/api.ts`, `storge-system/nginx.conf`.
- **Depende de:** contrato publico definido em `spec.md`.
- **Reusa:** branch `origin/main` do `storge-system` e a rota publica decidida em `STATE.md`.
- **Testes/Comandos:** build do frontend, busca por `ocrApi`/`/api/v1` no bundle, verificacao de que o upload usa `/api/exams/patient/{patientId}/upload`.

## T-PRI-003: Restaurar usuario real no backend

**Objetivo:** parar de usar `userId = 1L` e extrair o usuario autenticado.

- [x] Ajustar `ExamController` para usar `@AuthenticationPrincipal UserPrincipal`.
- [x] Remover `userId = 1L`.
- [x] Usar `userPrincipal.getId()` para montar a chamada ao OCR.
- **Done when:** Backend envia o ID real do usuario autenticado para OCR.
- **Gate:** Teste unitario/integracao cobre usuario autenticado ou valida logs/request mock.
- **Onde:** `storge-service/src/main/java/com/storge/storge_service/controller/ExamController.java`, `storge-service/src/main/java/com/storge/storge_service/config/UserPrincipal.java`, testes relacionados a auth/exames.
- **Depende de:** autenticacao JWT existente no backend.
- **Reusa:** branch `origin/exam-ai` do `storge-service`.
- **Testes/Comandos:** teste de controller/service com principal mockado, verificacao de log/argumento do service.

## T-PRI-004: Corrigir contrato backend -> OCR

**Objetivo:** restaurar a chamada historicamente correta ao OCR.

- [x] Remover `user_id` do multipart body.
- [x] Adicionar `user_id` como query param na URL do OCR.
- [x] Manter `file` como multipart.
- [x] Manter header `X-API-Key`.
- **Done when:** Chamada backend -> OCR corresponde a `POST /api/v1/patients/{patientId}/exames/upload?user_id={userId}`.
- **Gate:** Teste integrado ou mock HTTP confirma URL, query param e multipart.
- **Onde:** `storge-service/src/main/java/com/storge/storge_service/service/OcrService.java`, `storge-service/src/main/java/com/storge/storge_service/config/OcrApiConfig.java`, DTOs de exame/status se necessario.
- **Depende de:** `T-PRI-003`.
- **Reusa:** branch `origin/exam-ai` do `storge-service` e o contrato OCR documentado em `spec.md`.
- **Testes/Comandos:** teste com HTTP mock ou inspeção de request, validação contra OCR local, cobertura da rota de upload.

## T-PRI-005: Configurar prod sem expor OCR

**Objetivo:** fechar a fronteira de producao com Nginx/Hostinger e rede interna.

- [x] Ajustar config de producao para `OCR_API_BASE_URL` interno.
- [x] Remover dependencia de `host.docker.internal` em producao.
- [x] Confirmar que OCR nao publica porta externa desnecessaria.
- [x] Confirmar Nginx com `/api/*` somente para `storge-service`.
- [x] Ajustar `client_max_body_size` e timeouts no Nginx se necessario.
- **Done when:** Producao usa rede interna para OCR e Nginx nao expoe OCR.
- **Gate:** `curl` externo nao acessa OCR diretamente; upload via frontend/backend funciona.
- **Onde:** compose/prod env do `storge-app`, config de deploy da VPS, `storge-system/nginx.conf` ou config equivalente na VPS.
- **Depende de:** resultado de `T-PRI-001`.
- **Reusa:** DEC-019, DEC-020, DEC-021.
- **Testes/Comandos:** `curl` externo para OCR deve falhar, `curl` para `/api/*` deve ir ao backend, verificacao de `proxy_pass` e `client_max_body_size`.

## T-PRI-006: Validacao fim-a-fim

**Objetivo:** comprovar o fluxo publico completo em ambiente alvo.

- [x] Criar ou reutilizar API key OCR valida em ambiente alvo.
- [x] Executar upload de PDF pelo caminho publico.
- [x] Verificar resposta de exame criado.
- [x] Verificar polling de status.
- [x] Verificar logs do backend e OCR.
- **Done when:** O fluxo Browser/Nginx/backend/OCR funciona na VPS com OCR privado.
- **Gate:** Evidencia de comando/log registrada no handoff.
- **Onde:** VPS Hostinger e repositores de app.
- **Depende de:** `T-PRI-002`, `T-PRI-003`, `T-PRI-004`, `T-PRI-005`.
- **Reusa:** `spec.md` e `STATE.md`.
- **Testes/Comandos:** upload real, polling de status, logs de backend/OCR, `curl` externo ao OCR, verificacao de roteamento no Nginx.
