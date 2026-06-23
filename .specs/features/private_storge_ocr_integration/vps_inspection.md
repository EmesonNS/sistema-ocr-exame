# VPS Inspection Summary (T-PRI-001)

## Paths Reais na VPS
- **Backend/Frontend (Storge App):** `/root/storge_app`
- **OCR System:** `/root/sistema-ocr-exame`
- **Nginx Configs:** `/etc/nginx/sites-enabled/`

## Containers Ativos
**`storge_app` (docker-compose running):**
- `storge-backend` (binds `127.0.0.1:8081`)
- `storge-frontend` (binds `127.0.0.1:5175`)
- `storge-db` (binds `127.0.0.1:3307`)
- `n8n-api` (binds `127.0.0.1:8002`)

**`sistema-ocr-exame` (docker-compose exited):**
- `ocr_api` (binds `127.0.0.1:8001`) - Currently stopped (Exited 6 weeks ago)
- `ocr_worker` - Stopped
- `ocr_db` (binds `5433:5432`) - Stopped
- `ocr_redis` - Stopped

## Configuração Nginx Ativa
O Nginx está ativo e possui as seguintes configurações relevantes em `/etc/nginx/sites-enabled/`:
- **`storge` (`storge.local`):** 
  - `/` -> `http://127.0.0.1:5173`
  - `/api` -> `http://127.0.0.1:8081` (Backend)
  - `/ocr-api/` -> `http://127.0.0.1:8001/` (OCR)
- **`medocr-api` (`api.medocr.ecossystem.solutions`):** -> `http://127.0.0.1:8001`
- **`medocr-front` (`medocr.ecossystem.solutions`):** -> `http://127.0.0.1:3001`
- **`prontuario.storgecare.com.br`**: -> `http://127.0.0.1:5173`
- Existem também arquivos default apontando subdomínios antigos ou pegando o tráfego 443 via certbot.

## URL Interna OCR (Diferenças vs Local)
- O OCR mapeia a porta para `127.0.0.1:8001`.
- O Storge Backend em produção se comunica com banco e frontend mapeando para o host-gateway (ou chamando direto 127.0.0.1 via proxy Nginx).
- Como ambos (Storge Backend e OCR API) expõem portas em `127.0.0.1` (`8081` e `8001` respectivamente), o backend do storge pode alcançar o OCR chamando `http://127.0.0.1:8001` ou via Nginx `http://storge.local/ocr-api/` se houvesse DNS, ou através da porta `8001` no host, visto que `storge-backend` define `extra_hosts: ["host.docker.internal:host-gateway"]`. Assim o backend pode chamar `http://host.docker.internal:8001`.
- A porta `8001` NÃO está exposta na rede externa (apenas 127.0.0.1), mantendo-se privada. Entretanto, a rota `/ocr-api/` no Nginx do `storge.local` expõe o OCR para o mundo (ou exporia, caso storge.local ou um DNS mapeado para ele batesse nesse server block publicamente). E `api.medocr.ecossystem.solutions` expõe abertamente. Isso precisa ser fechado (T-PRI-005).
