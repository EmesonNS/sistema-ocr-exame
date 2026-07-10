# Tasks: Docker Environments Separation

## T1: Padronizar estrutura de Compose

- [x] Criar compose base com servicos comuns: `db`, `redis`, `api`, `worker`.
- [x] Criar override de dev com bind mount, reload, portas locais e comandos ergonomicos.
- [x] Criar compose de test com runner `pytest` e isolamento de artefatos.
- [x] Criar compose de prod sem bind mount do codigo, com restart policy e portas restritas.
- [x] Remover `container_name` fixo dos composes.
- **Done when:** `dev`, `test` e `prod` podem ser executados com project names diferentes sem colisao.

## T2: Normalizar variaveis de ambiente

- [x] Criar `.env.dev.example`.
- [x] Criar `.env.test.example`.
- [x] Criar `.env.prod.example`.
- [x] Corrigir producao para usar `MASTER_API_KEY` e `OPENROUTER_API_KEY` quando aplicavel.
- [x] Documentar quais variaveis sao obrigatorias por ambiente.
- **Done when:** cada ambiente tem arquivo de exemplo completo e sem segredo real.

## T3: Controlar migrations por ambiente

- [x] Avaliar se `entrypoint.sh` deve continuar rodando migration automaticamente.
- [x] Criar servico `migrate` para producao.
- [x] Garantir que worker nao rode migrations implicitamente.
- [x] Garantir que test consiga rodar sem iniciar API desnecessariamente.
- **Done when:** migrations rodam uma vez por deploy/provisionamento e nao em todo processo.

## T4: Corrigir healthchecks

- [x] Adicionar healthcheck HTTP para API em `/health`.
- [x] Corrigir Redis healthcheck com autenticacao.
- [x] Garantir `depends_on: condition: service_healthy` onde fizer sentido.
- **Done when:** `docker compose ps` mostra servicos saudaveis em dev/prod.

## T5: Testar ambiente dev

- [x] Subir stack dev.
- [x] Validar `GET /health`.
- [x] Validar migrations.
- [x] Validar logs da API e worker.
- [x] Validar persistencia de uploads.
- **Done when:** dev roda localmente em containers e aceita ciclo de desenvolvimento com reload.

## T6: Testar ambiente test

- [x] Rodar `pytest` dentro de container.
- [x] Garantir que nao ha chamadas reais para provedores externos.
- [x] Garantir limpeza de artefatos (`test.db`, uploads temporarios, cache).
- **Done when:** suite executa por Docker com resultado reprodutivel.

## T7: Testar ambiente prod

- [x] Subir stack prod com env de exemplo local seguro.
- [x] Validar que DB/Redis nao expoem portas no host.
- [x] Validar `GET /health`.
- [x] Validar worker conectado ao broker.
- [x] Validar restart policy e logs.
- **Done when:** prod roda com containers isolados, configuracao explicita e sem bind mount do codigo.

## T8: Atualizar documentacao operacional

- [x] Atualizar README com comandos de dev/test/prod.
- [x] Documentar matriz de variaveis.
- [x] Documentar comandos de logs, migrations, testes e reset de ambiente.
- **Done when:** qualquer operador consegue subir, testar e diagnosticar os tres ambientes pelos comandos documentados.
