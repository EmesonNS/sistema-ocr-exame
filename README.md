# Sistema OCR para Exames Médicos

Microserviço responsável por processar exames laboratoriais via OCR (Inteligência Artificial) e extrair biomarcadores automaticamente. Desenvolvido como parte da plataforma [Storge Care](https://app.storge.care).

## Funcionalidades

- **Upload de PDFs**: Recebe arquivos PDF de exames laboratoriais
- **Processamento via IA**: Extrai biomarcadores usando Google Gemini (primário) e OpenRouter como fallback
- **Processamento Assíncrono**: Usa Celery + Redis para processamento em background
- **API REST**: Interface RESTful com autenticação via API Keys
- **Polling de Status**: Acompanhamento do status de processamento em tempo real
- **Gerenciamento de API Keys**: Sistema completo de criação e revogação de chaves de acesso

## Arquitetura

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Cliente   │─────▶│  FastAPI     │─────▶│ PostgreSQL  │
│             │◀─────│   (API)      │◀─────│   (Dados)   │
└─────────────┘      └──────────────┘      └─────────────┘
                           │
                           ▼
                    ┌──────────────┐      ┌─────────────┐
                    │    Celery    │─────▶│    Redis    │
                    │   (Worker)   │◀─────│   (Broker)  │
                    └──────────────┘      └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Gemini AI  │
                    │  /OpenRouter │
                    └──────────────┘
```

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
- **Docker & Docker Compose**: Orquestração de containers

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- API Keys do Google Gemini ([obter aqui](https://aistudio.google.com/app/apikey))
- (Opcional) API Key do OpenRouter ([obter aqui](https://openrouter.ai/))

## Instalação e Configuração

### 1. Clone o repositório

```bash
git clone <repositorio>
cd sistema-ocr-exame
```

### 2. Configure as variáveis de ambiente

Copie o arquivo de exemplo e edite com suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

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

### 3. Inicie os containers

```bash
docker-compose up -d
```

Os seguintes serviços serão iniciados:
- **API**: `http://localhost:8001`
- **PostgreSQL**: `localhost:5433`
- **Redis**: Container interno (sem porta exposta)
- **Worker Celery**: Container interno

### 4. Execute as migrations do banco

```bash
docker-compose exec api alembic upgrade head
```

### 5. Verifique o status

```bash
curl http://localhost:8001/health
```

Deve retornar: `{"status":"ok","version":"1.0.0"}`

## Documentação da API

A documentação interativa (Swagger) está disponível em:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Autenticação

Todos os endpoints (exceto `/health`) exigem uma **API Key** no header:

```
X-API-Key: sua-chave-aqui
```

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/patients/{patient_id}/exames/upload` | Upload de PDF de exame |
| GET | `/api/v1/patients/{patient_id}/exames` | Listar exames do paciente |
| GET | `/api/v1/exames/{exame_id}` | Detalhes do exame com biomarcadores |
| GET | `/api/v1/exames/{exame_id}/status` | Status do processamento |

### Gerenciamento de API Keys

> **IMPORTANTE**: Todos os endpoints de API Keys requerem autenticação administrativa via header `X-Master-Key`. Configure `MASTER_API_KEY` no arquivo `.env`.

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/v1/api-keys` | Criar nova API Key | X-Master-Key |
| GET | `/api/v1/api-keys` | Listar todas as API Keys | X-Master-Key |
| DELETE | `/api/v1/api-keys/{id}` | Revogar uma API Key | X-Master-Key |
| POST | `/api/v1/api-keys/{id}/activate` | Reativar uma API Key | X-Master-Key |

**Exemplo de criação de API Key:**

```bash
curl -X POST http://localhost:8001/api/v1/api-keys \
  -H "X-Master-Key: sua-chave-mestra" \
  -H "Content-Type: application/json" \
  -d '{"name": "Minha Chave", "rate_limit": 60}'
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
- Aplica correções quando há alta confiança (>90%)
- Marca como `needs_review: true` quando a correção é incerta
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
├── tests/                     # Testes
├── docker-compose.yml         # Orquestração Docker
├── docker-compose.prod.yml    # Configuração produção
├── Dockerfile                 # Imagem da aplicação
├── requirements.txt           # Dependências Python
└── alembic.ini                # Configuração Alembic
```

## Criação de Migrations

Para criar uma nova migration após alterar os modelos:

```bash
docker-compose exec api alembic revision --autogenerate -m "descrição da alteração"
```

Para aplicar as migrations:

```bash
docker-compose exec api alembic upgrade head
```

## Executar Testes

```bash
docker-compose exec api pytest -v
```

## Produção

Para ambiente de produção, use o arquivo `docker-compose.prod.yml`:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Ver logs dos containers

```bash
# Logs da API
docker-compose logs -f api

# Logs do worker
docker-compose logs -f worker

# Logs do banco
docker-compose logs -f db
```

### Reiniciar serviços

```bash
docker-compose restart api worker
```

### Recriar containers (após alterações no Dockerfile)

```bash
docker-compose up -d --build
```

### Limpar tudo (cuidado: remove volumes)

```bash
docker-compose down -v
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
