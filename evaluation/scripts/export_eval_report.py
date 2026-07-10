#!/usr/bin/env python3
"""
Exporta o report consolidado do eval OCR.

Este script consome a saida do runner e gera:
- report JSON consolidado;
- CSV por documento;
- CSV de eventos;
- gate minimo de release.

O objetivo nesta fase e dar forma operavel ao eval sem fingir que o scorer
clínico completo já existe.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_export(report: dict[str, Any]) -> dict[str, Any]:
    documents = report.get("documents", [])
    blocked_docs = [doc for doc in documents if doc.get("result") != "passed"]
    passed_docs = [doc for doc in documents if doc.get("result") == "passed"]

    candidate_docs = [
        doc
        for doc in documents
        if doc.get("corpus_class") in {"golden_candidate_raw_lab", "shadow_document"}
    ]
    negative_docs = [doc for doc in documents if doc.get("corpus_class") == "negative_document"]

    release_gate = {
        "status": "not_ready" if blocked_docs else "green",
        "blocked_documents": len(blocked_docs),
        "passed_documents": len(passed_docs),
        "candidate_documents": len(candidate_docs),
        "negative_documents": len(negative_docs),
        "unsafe_normal_rate": None,
        "reason": None,
    }

    if candidate_docs and blocked_docs:
        release_gate["reason"] = "candidatos do benchmark ainda terminam com erro/blocked"
    elif negative_docs and any(doc.get("result") == "passed" for doc in negative_docs):
        release_gate["status"] = "red"
        release_gate["reason"] = "negative_document nao pode passar como laudo valido"

    return {
        "run_id": report.get("run_id"),
        "created_at": report.get("created_at"),
        "source_report": report,
        "summary": report.get("summary", {}),
        "quality_gate": release_gate,
    }


def write_document_csv(path: Path, documents: list[dict[str, Any]]) -> None:
    fieldnames = [
        "document_id",
        "corpus_class",
        "result",
        "upload_status",
        "exam_id",
        "final_status",
        "processing_stage",
        "processing_percent",
        "processing_message",
        "download_status",
        "pdf_bytes",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for doc in documents:
            writer.writerow({key: doc.get(key) for key in fieldnames})


def write_steps_csv(path: Path, steps: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for step in steps for key in step.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for step in steps:
            writer.writerow(step)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export consolidated OCR eval report.")
    parser.add_argument("--input", required=True, help="Runner report JSON")
    parser.add_argument("--output-dir", required=True, help="Diretorio de saida")
    parser.add_argument("--strict-release", action="store_true", help="Falha com status nao verde quando houver candidatos bloqueados ou negativos aprovados")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = load_json(input_path)
    export = build_export(report)
    export_path = output_dir / f"{input_path.stem}.export.json"
    export_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

    write_document_csv(output_dir / f"{input_path.stem}.documents.csv", report.get("documents", []))
    write_steps_csv(output_dir / f"{input_path.stem}.steps.csv", report.get("steps", []))

    print(json.dumps(export, ensure_ascii=False, indent=2))

    gate_status = export["quality_gate"]["status"]
    if args.strict_release and gate_status != "green":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
