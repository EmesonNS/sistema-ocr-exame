# Feature: Docker Environments Separation

Separar o sistema OCR em tres ambientes Docker isolados: `dev`, `test` e `prod`.

## Contexto Atual

O repositorio possui:

- `docker-compose.yml`: usado como ambiente de desenvolvimento, com bind mount do codigo, `uvicorn --reload`, PostgreSQL, Redis, API e worker.
- `docker-compose.prod.yml`: tentativa de ambiente produtivo, com `restart: always`, sem bind mount do codigo e porta parametrizada.
- `Dockerfile`: imagem unica para API e worker, com `poppler-utils`, dependencias Python, Alembic e entrypoint.
- `entrypoint.sh`: executa `alembic upgrade head` antes de iniciar o comando do container.
- `app/tests/conftest.py`: testes usam SQLite local (`sqlite:///./test.db`) quando executados via pytest.

## Problemas Observados

- Os composes usam `container_name` fixo (`ocr_db`, `ocr_api`, `ocr_worker`, `ocr_redis`), o que impede rodar ambientes em paralelo.
- O compose de producao injeta `JWT_SECRET`, mas a aplicacao usa `MASTER_API_KEY`; tambem nao injeta `OPENROUTER_API_KEY`.
- O Redis healthcheck de producao usa `redis-cli incr ping` sem autenticacao, incompatível com `--requirepass`.
- `app/core/cache.py` monta Redis diretamente como `redis://:${settings.REDIS_PASS}@redis:6379/1`, sem respeitar uma URL de cache dedicada.
- O entrypoint roda migrations em todo container que usar a imagem, inclusive worker/test se nao houver override.
- `dev` e `prod` usam o mesmo nome logico de banco (`ocr_exames`) e mesmo volume base (`postgres_data`) dentro de cada compose, exigindo project names ou nomes de volume distintos para isolamento.
- O ambiente de teste nao esta containerizado como ambiente proprio; hoje depende do pytest e suas dependencias no ambiente local ou dentro da imagem.

## Requisitos

### R1: Isolamento de ambientes

- Cada ambiente MUST ter seu proprio project name Docker Compose.
- Cada ambiente MUST ter volumes proprios para PostgreSQL, Redis/cache quando aplicavel e uploads.
- Ambientes MUST poder rodar sem conflito de portas, nomes de containers ou redes.
- `container_name` fixo SHOULD ser removido para permitir isolamento por project name.

### R2: Ambiente dev

- MUST rodar 100% em containers.
- MUST usar bind mount do codigo para desenvolvimento rapido.
- MUST usar `uvicorn --reload`.
- MUST expor API apenas em localhost.
- MUST ter PostgreSQL e Redis containerizados.
- SHOULD expor PostgreSQL localmente para debug com cliente externo.
- SHOULD manter uploads em pasta local bind-mounted para inspecao manual.
- SHOULD permitir rodar migrations automaticamente no start da API.

### R3: Ambiente test

- MUST rodar 100% em containers.
- MUST executar `pytest` dentro da imagem/container.
- MUST ser efemero por padrao.
- MUST nao compartilhar banco, Redis ou uploads com dev/prod.
- MUST poder usar SQLite para suite atual, desde que dentro do container, ou PostgreSQL isolado quando testes de integracao real forem adicionados.
- SHOULD ter perfil para testes com PostgreSQL real.
- MUST desabilitar chamadas reais para Gemini/OpenRouter por padrao.
- MUST usar secrets falsas e deterministicamente seguras para testes.
- MUST evitar que o entrypoint rode API/migrations quando o objetivo for apenas pytest, salvo quando o teste exigir banco PostgreSQL migrado.

### R4: Ambiente prod

- MUST rodar 100% em containers.
- MUST nao usar bind mount do codigo fonte.
- MUST usar imagem buildada e versionavel.
- MUST usar volumes persistentes para PostgreSQL e uploads.
- MUST configurar `restart` para API, worker, PostgreSQL e Redis.
- MUST expor apenas a API publicamente; PostgreSQL e Redis nao devem publicar portas no host.
- MUST exigir `DB_PASS`, `REDIS_PASS`, `MASTER_API_KEY`, `GEMINI_API_KEY` e `CORS_ORIGINS` explicitos.
- SHOULD configurar `OPENROUTER_API_KEY` quando fallback for desejado.
- MUST ter healthchecks validos para PostgreSQL, Redis e API.
- MUST rodar migrations de forma controlada, preferencialmente por servico `migrate` unico antes de API/worker.
- SHOULD suportar escala independente do worker.

### R5: Variaveis de ambiente

- Cada ambiente MUST ter arquivo dedicado:
  - `.env.dev`
  - `.env.test`
  - `.env.prod`
- Arquivos com segredos reais MUST nao ser commitados.
- Exemplos seguros SHOULD ser commitados:
  - `.env.dev.example`
  - `.env.test.example`
  - `.env.prod.example`
- Configuracoes comuns SHOULD ter nomes iguais entre ambientes para reduzir drift.

### R6: Observabilidade operacional

- Cada ambiente SHOULD ter logs consultaveis via `docker compose logs`.
- Prod SHOULD ter healthcheck HTTP em `/health`.
- Prod SHOULD ter limites ou politicas operacionais para logs, restart e recursos.
- Futuro: adicionar metricas/alertas quando a Phase 9 de maturidade produtiva evoluir.

## Matriz de Ambientes

| Item | dev | test | prod |
| --- | --- | --- | --- |
| Codigo | bind mount | imagem/container | imagem versionada |
| API command | `uvicorn --reload` | nao sobe por padrao ou sobe para teste | `uvicorn` sem reload |
| Worker | sim | opcional/mockado | sim |
| DB | PostgreSQL container | SQLite container-local ou PostgreSQL isolado | PostgreSQL persistente |
| Redis | container | container opcional ou mock | container persistente |
| Uploads | bind mount local | volume/pasta efemera | volume persistente |
| Portas | localhost API e DB opcional | sem portas por padrao | API publica/configurada |
| IA externa | real opcional | desabilitada/mockada | real obrigatoria para OCR |
| Migrations | automaticas aceitaveis | controladas pelo job/test | job `migrate` controlado |

## Fora de Escopo Nesta Etapa

- Kubernetes.
- CI/CD remoto.
- Observabilidade externa como Prometheus/Grafana.
- Alterar a arquitetura da aplicacao.
- Implementar dashboard de auditoria.

