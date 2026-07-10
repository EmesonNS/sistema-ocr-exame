#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT_DIR"
PROJECT_NAME="${OCR_SMOKE_PROJECT:-ocr-f001}"
COMPOSE_BASE=(docker compose --env-file "$COMPOSE_DIR/.env" -p "$PROJECT_NAME" -f "$COMPOSE_DIR/docker-compose.yml")
SMOKE_NAME="${OCR_SMOKE_CLIENT_NAME:-f001-smoke-$(date +%Y%m%d-%H%M%S)-$$}"
FIXTURE_PATH="${OCR_SMOKE_FIXTURE:-$ROOT_DIR/fixtures/f-001-baseline-runtime-ocr.pdf}"
TIMEOUT_SECONDS="${OCR_SMOKE_TIMEOUT_SECONDS:-420}"
POLL_INTERVAL_SECONDS="${OCR_SMOKE_POLL_INTERVAL_SECONDS:-5}"
PATIENT_ID="${OCR_SMOKE_PATIENT_ID:-42}"
USER_ID="${OCR_SMOKE_USER_ID:-7}"
RATE_LIMIT="${OCR_SMOKE_RATE_LIMIT:-60}"
CREATE_KEY="${OCR_SMOKE_CREATE_KEY:-1}"
API_KEY="${OCR_SMOKE_API_KEY:-}"
STOP_ON_EXIT="${OCR_SMOKE_STOP_ON_EXIT:-0}"
FIXTURE_IN_CONTAINER="/tmp/f-001-baseline-runtime-ocr.pdf"

log() {
  printf '[f-001] %s\n' "$*"
}

die() {
  printf '[f-001][erro] %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ "$STOP_ON_EXIT" == "1" ]]; then
    "${COMPOSE_BASE[@]}" down --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

ensure_fixture() {
  [[ -f "$FIXTURE_PATH" ]] || die "Fixture PDF ausente: $FIXTURE_PATH"
}

main() {
  cd "$COMPOSE_DIR"

  log "Subindo db, redis, migrate, api e worker."
  "${COMPOSE_BASE[@]}" up -d --build db redis migrate api worker

  ensure_fixture
  log "Copiando fixture controlada para o container da API."
  "${COMPOSE_BASE[@]}" cp "$FIXTURE_PATH" "api:$FIXTURE_IN_CONTAINER"

  if [[ -n "$API_KEY" ]]; then
    log "Usando API key fornecida via ambiente."
  else
    [[ "$CREATE_KEY" == "1" ]] || die "Nenhuma API key fornecida e criacao desabilitada."
    log "API key sera criada pelo proprio smoke usando MASTER_API_KEY do container."
  fi

  log "Executando fluxo de smoke dentro do container da API."
  "${COMPOSE_BASE[@]}" exec -T api python - \
    "$FIXTURE_IN_CONTAINER" \
    "$SMOKE_NAME" \
    "$PATIENT_ID" \
    "$USER_ID" \
    "$RATE_LIMIT" \
    "$CREATE_KEY" \
    "$API_KEY" \
    "$TIMEOUT_SECONDS" \
    "$POLL_INTERVAL_SECONDS" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

import httpx

fixture_path = Path(sys.argv[1])
client_name = sys.argv[2]
patient_id = int(sys.argv[3])
user_id = int(sys.argv[4])
rate_limit = int(sys.argv[5])
create_key = sys.argv[6] == "1"
api_key = sys.argv[7] or None
timeout_seconds = int(sys.argv[8])
poll_interval_seconds = int(sys.argv[9])
master_key = os.environ.get("MASTER_API_KEY", "")

base_url = "http://127.0.0.1:8000"
deadline = time.time() + timeout_seconds

def log(message: str) -> None:
    print(f"[f-001] {message}", flush=True)

def die(message: str) -> None:
    raise SystemExit(f"[f-001][erro] {message}")

def request_json(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        die(f"{method} {path} falhou com {response.status_code}: {response.text}")
    return response.json()

def wait_for_health(client: httpx.Client) -> None:
    while time.time() < deadline:
        try:
            response = client.get("/ready")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(3)
    die("API nao respondeu ao readiness dentro do timeout.")

with httpx.Client(base_url=base_url, timeout=60.0) as client:
    wait_for_health(client)

    if api_key:
        log("Usando API key fornecida via ambiente.")
    else:
        if not create_key:
            die("Nenhuma API key fornecida e criacao desabilitada.")
        if not master_key:
            die("MASTER_API_KEY nao configurada no container.")
        log(f"Criando API key para o cliente {client_name}.")
        created = request_json(
            client,
            "POST",
            "/api/v1/api-keys",
            headers={"X-Master-Key": master_key},
            json={"client_name": client_name, "rate_limit_per_minute": rate_limit},
        )
        api_key = created["api_key"]
        log("API key criada com sucesso.")

    headers = {"X-API-Key": api_key}
    log(f"Enviando upload controlado: {fixture_path.name}.")
    with fixture_path.open("rb") as handle:
        upload = request_json(
            client,
            "POST",
            f"/api/v1/patients/{patient_id}/exames/upload",
            params={"user_id": user_id},
            headers=headers,
            files={"file": (fixture_path.name, handle, "application/pdf")},
        )

    exame_id = upload.get("id")
    if not exame_id:
        die("Upload nao retornou exame_id.")
    log(f"Upload aceito para exame {exame_id}.")

    last_status = ""
    while time.time() < deadline:
        status_payload = request_json(client, "GET", f"/api/v1/exames/{exame_id}/status", headers=headers)
        detail_payload = request_json(client, "GET", f"/api/v1/exames/{exame_id}", headers=headers)
        status = status_payload.get("status", "")
        resultados = detail_payload.get("resultados") or []
        if status != last_status:
            log(f"Status atual: {status} (resultados={len(resultados)})")
            last_status = status
        if status == "concluido":
            if not resultados:
                die("Exame concluiu sem resultados persistidos.")
            log(f"Exame concluido com {len(resultados)} resultado(s).")
            log("Smoke finalizado com sucesso.")
            break
        if status == "erro":
            die(f"Pipeline retornou erro: {json.dumps(status_payload, ensure_ascii=False)}")
        time.sleep(poll_interval_seconds)
    else:
        die(f"Timeout aguardando conclusao do exame {exame_id}.")
PY
}

main "$@"
