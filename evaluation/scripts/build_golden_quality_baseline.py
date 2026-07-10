#!/usr/bin/env python3
"""
Gera uma baseline ideal para o golden set manual.

O objetivo nao e afirmar qualidade atual do OCR, e sim manter um artefato
reprodutivel para validar o scorer, o formato do baseline e o criterio de gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(name: str | None) -> str:
    return " ".join((name or "").strip().upper().split())


def build_perfect_document(doc: dict[str, Any]) -> dict[str, Any]:
    expected_biomarkers = []
    for biomarker in doc.get("expected_biomarkers", []):
        expected_biomarkers.append(
            {
                "nome_marcador": normalize_name(biomarker.get("name")),
                "valor_raw": biomarker.get("value_raw"),
                "unidade_medida": biomarker.get("unit"),
                "referencia_lab": f"{biomarker.get('reference_min')} - {biomarker.get('reference_max')}",
                "status_alerta": biomarker.get("expected_status", "normal"),
                "needs_review": False,
            }
        )

    return {
        "document_id": doc["document_id"],
        "corpus_class": "golden_candidate_raw_lab",
        "result": "passed",
        "final_status": "concluido",
        "processing_stage": "completed",
        "processing_percent": 100,
        "processing_message": f"Processamento concluído - {len(expected_biomarkers)} biomarcadores extraídos",
        "resultados": expected_biomarkers,
    }


def build_baseline(golden_payload: dict[str, Any]) -> dict[str, Any]:
    documents = [build_perfect_document(doc) for doc in golden_payload.get("documents", [])]
    return {
        "report": {
            "run_id": "golden-baseline-ideal",
            "created_at": golden_payload.get("updated_at"),
            "dataset_version": golden_payload.get("version"),
            "corpus_source": golden_payload.get("source"),
            "summary": {
                "documents_total": len(documents),
                "documents_passed": len(documents),
                "documents_blocked": 0,
            },
            "documents": documents,
        },
        "quality_gate": {
            "status": "green",
            "reason": "baseline ideal do golden set manual",
            "unsafe_normal_rate": 0,
            "candidate_documents": len(documents),
        },
        "baseline_contract": {
            "kind": "ideal_golden_perfect_match",
            "note": "Artefato de contrato, nao prova qualidade real do OCR.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an ideal OCR quality baseline from the golden set.")
    parser.add_argument(
        "--golden",
        default=str(ROOT_DIR / "evaluation/datasets/golden/golden_exams.json"),
        help="Caminho para o golden_exams.json",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "evaluation/reports/baseline/golden_quality_baseline.json"),
        help="Arquivo de saida",
    )
    args = parser.parse_args()

    golden_payload = load_json(Path(args.golden))
    baseline = build_baseline(golden_payload)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(baseline, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
