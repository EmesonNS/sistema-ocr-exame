# Sistema OCR para Exames Médicos

Microserviço responsável por processar exames laboratoriais via OCR (Inteligência Artificial) e extrair biomarcadores automaticamente. Desenvolvido como parte da plataforma [Storge Care](https://app.storge.care).

## Funcionalidades

- **Upload de PDFs**: Recebe arquivos PDF de exames laboratoriais
- **Processamento via IA**: Extrai biomarcadores usando Google Gemini (primário) e OpenRouter como fallback
- **Processamento Assíncrono**: Usa Celery + Redis para processamento em background
- **API REST**: Interface RESTful com autenticação via API Keys
- **Polling de Status**: Acompanhamento do status de processamento em tempo real
- **Gerenciamento de API Keys**: Criação, listagem, rotação, revogação e reativação de chaves de acesso
- **Storage agnóstico**: Suporte a backend local ou S3-compatible/MinIO para arquivos de exame

## Estado Atual

O estado atual detalhado do OCR no contexto do produto Storge esta documentado em `.specs/project/OCR_CURRENT_STATE.md`. Esse retrato cobre a API OCR, worker, storage, eval, integracao com `storge-service`, fluxo de frontend, evidencias de validacao e leitura quantitativa de qualidade.

Resumo operacional atual:

- OCR privado com FastAPI, Celery, Redis, PostgreSQL, API keys e readiness real.
- Upload de PDF, polling de status, resultados estruturados, resumo clinico, evidencia visual, FHIR e verificacao humana no contrato interno do OCR.
- Storage local ou S3-compatible/MinIO para o arquivo original do exame.
- Integracao pelo backend Spring Boot do produto, mantendo o OCR fora da superficie publica.
- Frontend React com upload PDF, polling real, historico e resultado resumido; auditoria visual, LOINC, FHIR e verificacao humana existem no OCR/backend, mas nao estao todos expostos na UI atual.
- Harness integrado em `storge-app/scripts/integrated-gate.sh` e eval quantitativo em `evaluation/`.
- Qualidade clinica de release nao deve ser inferida pelo sucesso de runtime; leia os relatórios versionados em `evaluation/reports/`.

## Arquitetura

```
┌─────────────┐      ┌────────────────┐      ┌──────────────┐
│ Cliente/UI  │─────▶│ storge-service │─────▶│ FastAPI OCR  │
└─────────────┘      │  Backend API   │      └──────────────┘
                     └────────────────┘              │
                                                     ▼
                    ┌──────────────┐      ┌──────────────────┐
                    │    Celery    │◀────▶│ Redis/PostgreSQL │
                    │   Worker     │      │ Storage local/S3 │
                    └──────────────┘      └──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Gemini AI  │
                    │  /OpenRouter │
                    └──────────────┘
```

Em desenvolvimento isolado, um cliente pode chamar a FastAPI diretamente para testar o microservico. No produto Storge, a superficie publica deve passar pelo backend `storge-service`.

## Tecnologias Utilizadas

- **Python 3.10+**: Linguagem principal
- **FastAPI**: Framework web para criação da API REST
- **SQLAlchemy 2.0**: ORM para acesso ao banco de dados
- **PostgreSQL 15**: Banco de dados relacional
- **Celery 5.3**: Processamento de tarefas assíncronas
- **Redis 7**: Message broker e cache
- **Alembic**: Gerenciamento de migrations do banco
- **Google Gemini**: API primária para OCR
- **OpenRouter**: API de fallback para OCR
- **MinIO/S3-compatible**: backend opcional para storage de exames
- **Docker & Docker Compose**: Orquestração de containers

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- API Keys do Google Gemini ([obter aqui](https://aistudio.google.com/app/apikey))
- (Opcional) API Key do OpenRouter ([obter aqui](https://openrouter.ai/))

Antes de subir o ambiente, confirme que o cliente consegue falar com o daemon Docker:

```bash
docker info
docker compose version
```

Se `docker info` falhar com `Cannot connect to the Docker daemon` ou erro em
`/var/run/docker.sock`, o problema ainda e de ambiente local: inicie o Docker
Engine/Docker Desktop antes de rodar os comandos do projeto.

## Instalação e Configuração

### 1. Clone o repositório

```bash
git clone <repositorio>
cd sistema-ocr-exame
```

### 2. Configure as variáveis de ambiente

Escolha o ambiente e copie o arquivo de exemplo correspondente:

```bash
cp .env.dev.example .env.dev
cp .env.test.example .env.test
cp .env.prod.example .env.prod
```

Edite o arquivo escolhido com suas configurações. Nunca versione arquivos `.env.*` reais.

```bash
# Banco de dados
DB_USER=ocr_user
DB_PASS=senha_segura_aqui  # OBRIGATÓRIO - não usar default

# Redis
REDIS_PASS=senha_segura_aqui  # OBRIGATÓRIO - não usar default

# APIs de IA
GEMINI_API_KEY=sua_chave_gemini_aqui
OPENROUTER_API_KEY=sua_chave_openrouter_aqui  # Opcional, usado como fallback

# Chave mestra para operações administrativas
MASTER_API_KEY=sua_chave_mestra_segura_aqui  # OBRIGATÓRIO em produção

# CORS (origens permitidas)
CORS_ORIGINS=["http://localhost:5173", "https://app.storge.care"]
```

### 3. Ambiente dev integrado com `storge-app`

```bash
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Use o nome padrao do projeto (`sistema-ocr-exame`) no ambiente dev integrado. A
app principal espera a rede Docker criada como `sistema-ocr-exame_ocr_network`.
Evite `-p ocr-dev` quando for rodar OCR junto com `storge-app`, porque isso muda
o nome da rede para `ocr-dev_ocr_network`.

Para desenvolvimento isolado do OCR, um nome de projeto customizado e aceitavel
desde que nenhum `storge-app` precise consumir a rede desse compose. O smoke
isolado `F-001`, por exemplo, usa projeto proprio (`ocr-f001`) de forma
intencional.

Serviços:
- **API**: `http://localhost:8001`
- **PostgreSQL**: `127.0.0.1:15433`
- **Redis**: interno na rede Docker
- **Worker Celery**: interno na rede Docker
- **Uploads**: bind mount em `./uploads`

O serviço `migrate` aplica `alembic upgrade head` antes da API e do worker iniciarem.

### 4. Ambiente test

```bash
docker compose --env-file .env.test -p ocr-test \
  -f docker-compose.test.yml run --rm test
```

O ambiente de teste roda em container e usa credenciais falsas. A suíte atual usa SQLite dentro do container.

### 5. Ambiente prod

```bash
docker compose --env-file .env.prod -p ocr-prod \
  -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Em produção:
- API é o único serviço exposto no host.
- PostgreSQL e Redis não publicam portas.
- `MASTER_API_KEY`, `GEMINI_API_KEY`, `DB_PASS`, `REDIS_PASS` e `CORS_ORIGINS` devem estar definidos.
- Migrations rodam pelo serviço `migrate`, não implicitamente em API/worker.
- A API OCR so deve ficar acessivel por rede privada, firewall ou reverse proxy restrito ao backend do produto. O compose publica `API_PORT`; essa publicacao nao e, sozinha, garantia de privacidade.

### 6. Verifique o status

```bash
curl http://localhost:8001/health
```

Deve retornar: `{"status":"ok","version":"1.0.0"}`

Para o readiness operacional real do pipeline:

```bash
curl http://localhost:8001/ready
```

Esse endpoint retorna `503` quando banco, Redis, worker ou segredos obrigatórios nao estao prontos.

### Smoke baseline F-001

O caminho reproduzível de smoke do OCR isolado fica em:

```bash
./scripts/smoke_runtime_ocr.sh
```

O script:
- sobe `db`, `redis`, `migrate`, `api` e `worker` com o compose base;
- copia a fixture controlada `fixtures/f-001-baseline-runtime-ocr.pdf` para o container `api`;
- cria uma API key via `X-Master-Key` se `OCR_SMOKE_API_KEY` não for informada;
- faz upload, polling de status e valida que o exame concluiu com resultados persistidos;
- aceita `OCR_SMOKE_STOP_ON_EXIT=1` para derrubar o stack ao final;
- usa `/ready` como preflight real do runtime antes de executar o fluxo;
- usa `docker compose -p ocr-f001 -f docker-compose.yml down --remove-orphans` como teardown manual.

## Documentação da API

A documentação interativa (Swagger) está disponível em:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Autenticação

Endpoints de negócio exigem uma **API Key** no header:

```
X-API-Key: sua-chave-aqui
```

Endpoints operacionais:
- `/health`: publico no código atual; confirma apenas que a API HTTP responde.
- `/ready`: publico no código atual; valida segredos obrigatorios, banco, Redis e worker, mas nao valida qualidade OCR nem chamada real aos provedores de IA.

Endpoints administrativos de API keys usam `X-Master-Key`.

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/patients/{patient_id}/exames/upload` | Upload de PDF de exame |
| POST | `/api/v1/patients/{patient_id}/exames/batch` | Upload em lote de PDFs |
| GET | `/api/v1/patients/{patient_id}/exames` | Listar exames do paciente |
| GET | `/api/v1/exames/{exame_id}` | Detalhes do exame com biomarcadores |
| GET | `/api/v1/exames/{exame_id}/file` | Download do arquivo original |
| GET | `/api/v1/exames/{exame_id}/status` | Status do processamento |
| GET | `/api/v1/exames/{exame_id}/resumo` | Resumo clinico cached/best-effort |
| POST | `/api/v1/exames/{exame_id}/resumo/regenerate` | Regenerar resumo clinico |
| GET | `/api/v1/exames/{exame_id}/fhir` | Exportar Bundle FHIR |
| GET | `/api/v1/exames/{exame_id}/resultados/{resultado_id}/evidence` | Recuperar evidencia visual |
| POST | `/api/v1/exames/{exame_id}/resultados/{resultado_id}/verify` | Marcar resultado como verificado |

### Gerenciamento de API Keys

> **IMPORTANTE**: Todos os endpoints de API Keys requerem autenticação administrativa via header `X-Master-Key`. Configure `MASTER_API_KEY` no arquivo `.env`.

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/v1/api-keys` | Criar nova API Key | X-Master-Key |
| GET | `/api/v1/api-keys` | Listar todas as API Keys | X-Master-Key |
| POST | `/api/v1/api-keys/{id}/rotate` | Rotacionar uma API Key | X-Master-Key |
| DELETE | `/api/v1/api-keys/{id}` | Revogar uma API Key | X-Master-Key |
| POST | `/api/v1/api-keys/{id}/activate` | Reativar uma API Key | X-Master-Key |

`rate_limit_per_minute` e persistido no cadastro da chave. Nao trate esse campo
como enforcement runtime local a menos que exista uma camada externa ou middleware
explicitamente configurado para aplica-lo.

**Exemplo de criação de API Key:**

```bash
curl -X POST http://localhost:8001/api/v1/api-keys \
  -H "X-Master-Key: sua-chave-mestra" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "storge-dev", "rate_limit_per_minute": 60}'
```

> **Segurança**: Os endpoints de API Keys são protegidos por `X-Master-Key`. Configure uma chave segura em `MASTER_API_KEY` e mantenha-a segura. Em produção, considere também restringir via firewall.

## Fluxo de Processamento

1. **Upload**: Cliente envia PDF → status `pendente`
2. **Worker**: Celery processa com IA → status `processando`
3. **Conclusão**: Resultados extraídos → status `concluido` ou `erro`

## Tipos de Valores de Biomarcadores

O sistema distingue automaticamente entre:

- **Valores Absolutos**: Números com unidades como `/mm³`, `g/dL`, `mg/dL`
- **Valores Percentuais**: Números com `%`
- **Valores Textuais**: Como "Negativo", "Positivo", "Traços"

### Exemplo de Extração Correta

Para um hemograma com `SEGMENTADOS 49,0 %`:

```json
{
  "nome_marcador": "SEGMENTADOS",
  "valor_raw": "49,0",
  "valor_numerico": 49.0,
  "tipo_valor": "percentual",
  "unidade_medida": "%",
  "referencia_min": 40.0,
  "referencia_max": 75.0,
  "status_alerta": "normal"
}
```

O sistema **NÃO** converte automaticamente percentuais para absolutos para evitar erros de interpretação.

### Auditoria e Correção de Valores

O sistema detecta automaticamente valores potencialmente incorretos (ex: decimal deslocado) e:
- Aplica heuristicas deterministicas de correção quando encontra um padrão compatível
- Marca como `needs_review: true` quando a correção ou a confiança exige revisão humana
- Registra auditoria completa: valor original, valor corrigido, regra aplicada, confiança

Campos de auditoria em cada resultado:
- `valor_raw`: Valor original extraído do PDF
- `valor_numerico`: Valor numérico normalizado
- `correcao_aplicada`: Descrição da correção (se houver)
- `confianca`: Nível de confiança na extração (0.0 a 1.0)
- `needs_review`: Se precisa revisão manual

### Exemplo de Uso

```python
import requests
import time

API_KEY = "sua-chave-aqui"
BASE_URL = "http://localhost:8001/api/v1"
headers = {"X-API-Key": API_KEY}

# 1. Fazer upload
with open("exame.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/patients/42/exames/upload",
        headers=headers,
        files={"file": f},
        params={"user_id": 1}
    )
exame_id = response.json()["id"]

# 2. Polling do status
while True:
    status = requests.get(
        f"{BASE_URL}/exames/{exame_id}/status",
        headers=headers
    ).json()["status"]

    if status == "concluido":
        break
    elif status == "erro":
        raise Exception("Erro no processamento")

    time.sleep(3)

# 3. Obter resultados
detalhes = requests.get(
    f"{BASE_URL}/exames/{exame_id}",
    headers=headers
).json()

for biomarcador in detalhes["resultados"]:
    print(f"{biomarcador['nome']}: {biomarcador['valor']} {biomarcador['unidade']}")
```

## Estrutura do Projeto

```
sistema-ocr-exame/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── exames.py      # Endpoints de exames
│   │       └── api_keys.py    # Endpoints de API Keys
│   ├── core/
│   │   ├── auth.py            # Autenticação via API Key
│   │   ├── config.py          # Configurações
│   │   ├── database.py        # Conexão com banco
│   │   └── celery_app.py      # Configuração do Celery
│   ├── models/
│   │   ├── exame.py           # Modelo Exame
│   │   └── api_key.py         # Modelo ApiKey
│   ├── services/
│   │   ├── exame_service.py   # Lógica de negócio
│   │   └── ai_service.py      # Integração com APIs de IA
│   ├── schemas/
│   │   └── exame.py           # Schemas Pydantic
│   ├── tasks/
│   │   └── worker.py          # Tasks Celery
│   └── main.py                # Aplicação FastAPI
├── alembic/                   # Migrations
├── uploads/                   # Arquivos PDFs enviados
├── app/tests/                 # Testes
├── docker-compose.yml         # Base Docker compartilhada
├── docker-compose.dev.yml     # Override desenvolvimento
├── docker-compose.test.yml    # Runner de testes
├── docker-compose.prod.yml    # Override produção
├── Dockerfile                 # Imagem da aplicação
├── requirements.txt           # Dependências Python
├── requirements-test.txt      # Dependências adicionais para testes
└── alembic.ini                # Configuração Alembic
```

## Criação de Migrations

Para criar uma nova migration após alterar os modelos:

```bash
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.dev.yml exec api \
  alembic revision --autogenerate -m "descrição da alteração"
```

Para aplicar as migrations:

```bash
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.dev.yml run --rm migrate
```

## Executar Testes

```bash
docker compose --env-file .env.test -p ocr-test \
  -f docker-compose.test.yml run --rm test
```

## Produção

Para ambiente de produção, use o arquivo `docker-compose.prod.yml`:

```bash
docker compose --env-file .env.prod -p ocr-prod \
  -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

### Ver logs dos containers

```bash
# Logs da API
docker compose logs -f api

# Logs do worker
docker compose logs -f worker

# Logs do banco
docker compose logs -f db
```

### Reiniciar serviços

```bash
docker compose restart api worker
```

### Recriar containers (após alterações no Dockerfile)

```bash
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Limpar tudo (cuidado: remove volumes)

```bash
docker compose down -v
```

## Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto é propriedade da Storge Care.

## Suporte

Para questões e suporte, entre em contato através do [site da Storge Care](https://app.storge.care).
