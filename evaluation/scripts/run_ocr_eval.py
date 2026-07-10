#!/usr/bin/env python3
"""
Runner do benchmark OCR.

Foco atual:
- carregar o corpus curado;
- executar o fluxo real via backend Storge;
- registrar evidencias objetivas por documento;
- separar sucesso de processamento, erro de extração e erro de orquestração.

O scorer completo ainda será separado nesta trilha.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

try:
    from app.services.ai_service import AIService
except Exception:  # noqa: BLE001
    AIService = None  # type: ignore[assignment]


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT_DIR / "evaluation/datasets/manifests/corpus_manifest.json"
DEFAULT_REPORT_DIR = ROOT_DIR / "evaluation/reports"
DEFAULT_APP_BASE_URL = os.environ.get("OCR_EVAL_APP_BASE_URL", "http://127.0.0.1:18080/api")


@dataclass
class DocumentRun:
    document_id: str
    file_path: str
    corpus_class: str
    upload_status: int | None = None
    exam_id: str | None = None
    final_status: str | None = None
    processing_stage: str | None = None
    processing_percent: int | None = None
    processing_message: str | None = None
    download_status: int | None = None
    pdf_bytes: int | None = None
    resultados: list[dict[str, Any]] | None = None
    result: str = "blocked"
    error: str | None = None


def decode_jwt_claim(token: str, claim: str) -> Any:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    return data.get(claim)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True)
            .strip()
        )
    except Exception:
        return "unknown"


def select_documents(manifest: dict[str, Any], document_ids: set[str] | None) -> list[dict[str, Any]]:
    docs = manifest.get("documents", [])
    if not document_ids:
        return docs
    return [doc for doc in docs if doc.get("document_id") in document_ids]


def step_event(run: dict[str, Any], name: str, **data: Any) -> None:
    run["steps"].append({"name": name, **data})


def register_clinic(session: requests.Session, base_url: str) -> dict[str, Any]:
    stamp = time.time_ns()
    email = f"ocr-eval.{stamp}@storge.local"
    password = "S3nh@Eval2026!"
    phone = f"11{str(stamp)[-8:]}"
    cnpj = f"123456780001{str(stamp)[-2:]}"
    response = session.post(
        f"{base_url}/auth/register/clinic",
        json={
            "name": "OCR Eval Clinic",
            "email": email,
            "password": password,
            "cnpj": cnpj,
            "phoneNumber": phone,
        },
        timeout=60,
    )
    response.raise_for_status()
    return {"email": email, "password": password, "phone": phone, "cnpj": cnpj, "payload": response.json()}


def login(session: requests.Session, base_url: str, email: str, password: str) -> dict[str, Any]:
    response = session.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload["accessToken"]
    return {
        "token": token,
        "role": payload.get("userProfile", {}).get("role"),
        "jwt_role": decode_jwt_claim(token, "role"),
        "payload": payload,
    }


def create_patient(session: requests.Session, base_url: str, name: str, phone: str, token: str) -> dict[str, Any]:
    response = session.post(
        f"{base_url}/patients",
        json={"name": name, "phoneNumber": phone, "dateOfBirth": "1990-01-01", "source": "BY_CLINIC"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return {"patient_id": payload.get("patientId") or payload.get("id"), "payload": payload}


def wait_for_terminal(session: requests.Session, base_url: str, token: str, patient_id: int, exam_id: str, timeout: int, poll_interval: int) -> dict[str, Any]:
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    last = None
    while time.time() < deadline:
        response = session.get(f"{base_url}/exams/patient/{patient_id}/{exam_id}", headers=headers, timeout=60)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status_processamento")
        if status != last:
            last = status
        if str(status).lower() in {"concluido", "erro"}:
            return payload
        time.sleep(poll_interval)
    raise TimeoutError(f"timeout aguardando exame {exam_id}")


def upload_document(
    session: requests.Session,
    base_url: str,
    token: str,
    patient_id: int,
    file_path: Path,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    with file_path.open("rb") as handle:
        response = session.post(
            f"{base_url}/exams/patient/{patient_id}/upload",
            headers=headers,
            files={"file": (file_path.name, handle, "application/pdf")},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def download_document(session: requests.Session, base_url: str, token: str, patient_id: int, exam_id: str) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"}
    response = session.get(f"{base_url}/exams/patient/{patient_id}/{exam_id}/file", headers=headers, timeout=120)
    response.raise_for_status()
    return response


def build_report(
    run_id: str,
    manifest: dict[str, Any],
    app_base_url: str,
    clinic: dict[str, Any],
    documents: Iterable[DocumentRun],
    pipeline_mode: str,
) -> dict[str, Any]:
    documents_list = list(documents)
    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": get_git_sha(),
        "pipeline_mode": pipeline_mode,
        "app_base_url": app_base_url,
        "knowledge_version": json.loads((ROOT_DIR / "evaluation/knowledge/VERSION.json").read_text(encoding="utf-8"))["knowledge_version"],
        "dataset_version": manifest.get("version"),
        "corpus_source": manifest.get("source"),
        "clinic": {"email": clinic["email"], "cnpj": clinic["cnpj"]},
        "summary": {
            "documents_total": len(documents_list),
            "documents_passed": sum(1 for doc in documents_list if doc.result == "passed"),
            "documents_blocked": sum(1 for doc in documents_list if doc.result != "passed"),
        },
        "documents": [doc.__dict__ for doc in documents_list],
    }


def run_document_in_process(
    doc: dict[str, Any],
    ai_service: AIService,
) -> DocumentRun:
    file_path = ROOT_DIR / doc["file_path"]
    doc_run = DocumentRun(
        document_id=doc["document_id"],
        file_path=str(file_path),
        corpus_class=doc["corpus_class"],
    )

    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    resultados, data_coleta, laboratorio = asyncio.run(ai_service.extrair_biomarcadores(str(file_path)))
    doc_run.final_status = "concluido" if resultados else "erro"
    doc_run.processing_stage = "completed" if resultados else "failed"
    doc_run.processing_percent = 100 if resultados else 0
    doc_run.processing_message = (
        f"Processamento concluído - {len(resultados)} biomarcadores extraídos"
        if resultados
        else "Nenhum dado extraído do documento"
    )
    doc_run.resultados = resultados or []
    doc_run.download_status = None
    doc_run.pdf_bytes = None

    if doc_run.corpus_class == "negative_document":
        if resultados:
            doc_run.result = "blocked"
            doc_run.error = f"negative_document retornou {len(resultados)} biomarcadores inesperados"
        else:
            doc_run.result = "blocked"
            doc_run.error = "terminal=erro: Nenhum dado extraído do documento"
    elif resultados:
        doc_run.result = "passed"
        doc_run.error = None
    else:
        doc_run.result = "blocked"
        doc_run.error = "terminal=erro: Nenhum dado extraído do documento"

    return doc_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR quality eval against the real backend flow.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--document-id", action="append", help="Only run selected document ids. Can be repeated.")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument(
        "--pipeline-mode",
        choices=["api", "in-process"],
        default=os.environ.get("OCR_EVAL_PIPELINE_MODE", "api"),
        help="Modo de execução do benchmark",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    document_ids = set(args.document_id) if args.document_id else None
    selected = select_documents(manifest, document_ids)
    if not selected:
        raise SystemExit("nenhum documento selecionado para o eval")

    session = requests.Session()
    run_id = str(uuid.uuid4())
    run = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    documents: list[DocumentRun] = []
    if args.pipeline_mode == "api":
        clinic = register_clinic(session, args.app_base_url)
        token_info = login(session, args.app_base_url, clinic["email"], clinic["password"])
        if token_info["role"] != "CLINIC":
            raise SystemExit(f"role inesperada no login: {token_info['role']}")
        if token_info["jwt_role"] != "CLINIC":
            raise SystemExit(f"claim JWT divergente: {token_info['jwt_role']}")

        step_event(run, "auth", role=token_info["role"], jwt_role=token_info["jwt_role"])
        patient = create_patient(session, args.app_base_url, "OCR Eval Patient", clinic["phone"], token_info["token"])
        patient_id = int(patient["patient_id"])
        step_event(run, "patient", patient_id=patient_id)

        for doc in selected:
            file_path = ROOT_DIR / doc["file_path"]
            doc_run = DocumentRun(
                document_id=doc["document_id"],
                file_path=str(file_path),
                corpus_class=doc["corpus_class"],
            )
            try:
                if not file_path.exists():
                    raise FileNotFoundError(str(file_path))

                upload = upload_document(session, args.app_base_url, token_info["token"], patient_id, file_path)
                doc_run.upload_status = 201
                doc_run.exam_id = upload.get("id")
                step_event(run, "upload", document_id=doc_run.document_id, exam_id=doc_run.exam_id, corpus_class=doc_run.corpus_class)

                terminal = wait_for_terminal(session, args.app_base_url, token_info["token"], patient_id, doc_run.exam_id, args.timeout, args.poll_interval)
                doc_run.final_status = terminal.get("status_processamento")
                doc_run.processing_stage = terminal.get("processing_stage")
                doc_run.processing_percent = terminal.get("processing_percent")
                doc_run.processing_message = terminal.get("processing_message")
                step_event(run, "terminal", document_id=doc_run.document_id, status=doc_run.final_status, stage=doc_run.processing_stage, message=doc_run.processing_message)

                if str(doc_run.final_status).lower() == "concluido":
                    download = download_document(session, args.app_base_url, token_info["token"], patient_id, doc_run.exam_id)
                    doc_run.download_status = download.status_code
                    doc_run.pdf_bytes = len(download.content)
                    detail_response = session.get(
                        f"{args.app_base_url}/exams/patient/{patient_id}/{doc_run.exam_id}",
                        headers={"Authorization": f"Bearer {token_info['token']}"},
                        timeout=60,
                    )
                    detail_response.raise_for_status()
                    detail_payload = detail_response.json()
                    doc_run.resultados = detail_payload.get("resultados") or []
                    doc_run.result = "passed"
                else:
                    doc_run.result = "blocked"
                    doc_run.error = f"terminal={doc_run.final_status}: {doc_run.processing_message}"
            except Exception as exc:  # noqa: BLE001
                doc_run.result = "blocked"
                doc_run.error = str(exc)
                step_event(run, "error", document_id=doc_run.document_id, error=str(exc))
            documents.append(doc_run)

        clinic_info = clinic
        app_base_url = args.app_base_url
    else:
        clinic_info = {"email": "in-process@storge.local", "cnpj": "00000000000000"}
        app_base_url = "in-process"
        if AIService is None:
            raise SystemExit("AIService indisponível no ambiente atual para pipeline in-process")
        ai_service = AIService()
        step_event(run, "mode", pipeline_mode="in-process")
        for doc in selected:
            try:
                doc_run = run_document_in_process(doc, ai_service)
                if doc_run.result == "passed":
                    step_event(run, "terminal", document_id=doc_run.document_id, status=doc_run.final_status, stage=doc_run.processing_stage, message=doc_run.processing_message)
                else:
                    step_event(run, "terminal", document_id=doc_run.document_id, status=doc_run.final_status, stage=doc_run.processing_stage, message=doc_run.processing_message)
            except Exception as exc:  # noqa: BLE001
                doc_run = DocumentRun(
                    document_id=doc["document_id"],
                    file_path=str(ROOT_DIR / doc["file_path"]),
                    corpus_class=doc["corpus_class"],
                    result="blocked",
                    error=str(exc),
                    final_status="erro",
                    processing_stage="failed",
                    processing_percent=0,
                    processing_message=str(exc),
                )
                step_event(run, "error", document_id=doc_run.document_id, error=str(exc))
            documents.append(doc_run)

    report = build_report(run_id, manifest, app_base_url, clinic_info, documents, args.pipeline_mode)
    report["steps"] = run["steps"]
    report_path = report_dir / f"ocr-eval-{run_id}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(doc.result == "passed" for doc in documents) else 1


if __name__ == "__main__":
    raise SystemExit(main())
