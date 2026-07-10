#!/usr/bin/env python3
"""
Scorer mínimo do benchmark OCR.

Com golden manual disponível, calcula:
- precision/recall de biomarcadores;
- acerto por documento;
- unsafe_normal_rate;
- gate de release.

Sem golden manual, o scorer devolve status `not_ready` de forma honesta.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_knowledge_layer(path: Path) -> dict[str, Any]:
    if path.is_file():
        return load_json(path)

    payload: dict[str, Any] = {}
    version_path = path / "VERSION.json"
    if version_path.exists():
        payload.update(load_json(version_path))

    for filename in [
        "canonical_biomarkers.json",
        "unit_aliases.json",
        "reference_parsing_rules.json",
        "clinical_rules.json",
        "lab_patterns.json",
    ]:
        file_path = path / filename
        if file_path.exists():
            file_payload = load_json(file_path)
            key = filename.removesuffix(".json")
            if key in file_payload:
                payload[key] = file_payload[key]
            else:
                payload[key] = file_payload

    return payload


def normalize_name(name: str | None) -> str:
    return " ".join((name or "").strip().upper().split())


def build_alias_map(knowledge: dict[str, Any] | None) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    if not knowledge:
        return alias_map
    for item in knowledge.get("canonical_biomarkers", []):
        canonical = normalize_name(item.get("name"))
        for alias in item.get("aliases", []):
            alias_map[normalize_name(alias)] = canonical
        alias_map[canonical] = canonical
    return alias_map


def canonicalize_name(name: str | None, alias_map: dict[str, str]) -> str:
    normalized = normalize_name(name)
    return alias_map.get(normalized, normalized)


def index_expected_biomarkers(golden_docs: list[dict[str, Any]], alias_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for doc in golden_docs:
        expected = {}
        for biomarker in doc.get("expected_biomarkers", []):
            canonical = canonicalize_name(biomarker.get("name"), alias_map)
            expected[canonical] = biomarker
        indexed[doc["document_id"]] = {
            "document_type": doc.get("document_type"),
            "expected_biomarkers": expected,
            "expected_behavior": doc.get("expected_behavior"),
        }
    return indexed


def index_actual_biomarkers(doc: dict[str, Any], alias_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for biomarker in doc.get("resultados", []) or []:
        canonical = canonicalize_name(biomarker.get("nome_marcador"), alias_map)
        indexed[canonical] = biomarker
    return indexed


def compare_documents(
    report_docs: list[dict[str, Any]],
    golden_docs: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> dict[str, Any]:
    document_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    totals = {
        "documents_total": 0,
        "documents_scored": 0,
        "documents_passed": 0,
        "documents_blocked": 0,
        "biomarkers_expected": 0,
        "biomarkers_observed": 0,
        "biomarkers_matched": 0,
        "unsafe_normal": 0,
        "unsafe_normal_denominator": 0,
    }

    for doc in report_docs:
        document_id = doc.get("document_id")
        golden = golden_docs.get(document_id)
        actual = index_actual_biomarkers(doc, alias_map)

        totals["documents_total"] += 1
        totals["documents_passed"] += 1 if doc.get("result") == "passed" else 0
        totals["documents_blocked"] += 1 if doc.get("result") != "passed" else 0

        row = {
            "document_id": document_id,
            "corpus_class": doc.get("corpus_class"),
            "result": doc.get("result"),
            "expected_behavior": golden.get("expected_behavior") if golden else None,
            "document_type_misclassified": False,
            "expected_biomarkers": 0,
            "observed_biomarkers": len(actual),
            "matched_biomarkers": 0,
            "missing_biomarkers": 0,
            "unexpected_biomarkers": 0,
            "unsafe_normal": 0,
        }

        if golden:
            totals["documents_scored"] += 1
            expected_biomarkers = golden["expected_biomarkers"]
            row["expected_biomarkers"] = len(expected_biomarkers)
            totals["biomarkers_expected"] += len(expected_biomarkers)
            totals["biomarkers_observed"] += len(actual)
            if golden.get("document_type") == "non_lab_document" and doc.get("result") == "passed":
                row["document_type_misclassified"] = True
            if golden.get("document_type") == "lab_report" and doc.get("result") != "passed":
                row["document_type_misclassified"] = True

            matched_names = set(expected_biomarkers).intersection(actual)
            row["matched_biomarkers"] = len(matched_names)
            row["missing_biomarkers"] = len(set(expected_biomarkers) - set(actual))
            row["unexpected_biomarkers"] = len(set(actual) - set(expected_biomarkers))
            totals["biomarkers_matched"] += len(matched_names)

            if row["missing_biomarkers"] > 0:
                findings.append(
                    {
                        "document_id": document_id,
                        "type": "missing_biomarker",
                        "count": row["missing_biomarkers"],
                    }
                )
            if row["unexpected_biomarkers"] > 0:
                findings.append(
                    {
                        "document_id": document_id,
                        "type": "unexpected_biomarker",
                        "count": row["unexpected_biomarkers"],
                    }
                )

            for canonical_name, expected in expected_biomarkers.items():
                if str(expected.get("expected_status", "")).lower() != "normal":
                    totals["unsafe_normal_denominator"] += 1
                actual_bm = actual.get(canonical_name)
                if not actual_bm:
                    continue
                expected_status = str(expected.get("expected_status", "")).lower()
                actual_status = str(actual_bm.get("status_alerta", "")).lower()
                if expected_status != "normal" and actual_status == "normal":
                    row["unsafe_normal"] += 1
                    totals["unsafe_normal"] += 1
                    findings.append(
                        {
                            "document_id": document_id,
                            "biomarker": canonical_name,
                            "type": "unsafe_normal",
                        }
                    )

            if row["document_type_misclassified"]:
                findings.append(
                    {
                        "document_id": document_id,
                        "type": "document_type_misclassified",
                    }
                )

        document_rows.append(row)

    biomarker_precision = (
        totals["biomarkers_matched"] / totals["biomarkers_observed"]
        if totals["biomarkers_observed"]
        else None
    )
    biomarker_recall = (
        totals["biomarkers_matched"] / totals["biomarkers_expected"]
        if totals["biomarkers_expected"]
        else None
    )
    unsafe_normal_rate = (
        totals["unsafe_normal"] / totals["unsafe_normal_denominator"]
        if totals["unsafe_normal_denominator"]
        else None
    )

    return {
        "summary": {
            "documents_total": totals["documents_total"],
            "documents_scored": totals["documents_scored"],
            "documents_passed": totals["documents_passed"],
            "documents_blocked": totals["documents_blocked"],
            "biomarkers_expected": totals["biomarkers_expected"],
            "biomarkers_observed": totals["biomarkers_observed"],
            "biomarkers_matched": totals["biomarkers_matched"],
            "biomarker_precision": biomarker_precision,
            "biomarker_recall": biomarker_recall,
            "unsafe_normal_rate": unsafe_normal_rate,
        },
        "documents": document_rows,
        "findings": findings,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score OCR eval reports against optional golden.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--golden", help="golden_exams.json manual")
    parser.add_argument("--knowledge", help="knowledge/versioned canonical layer")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--min-biomarker-precision",
        type=float,
        default=0.8,
        help="Minimum biomarker precision required for release",
    )
    parser.add_argument(
        "--min-biomarker-recall",
        type=float,
        default=0.8,
        help="Minimum biomarker recall required for release",
    )
    parser.add_argument(
        "--max-unsafe-normal-rate",
        type=float,
        default=0.0,
        help="Maximum allowed unsafe normal rate for release",
    )
    parser.add_argument("--strict-release", action="store_true")
    args = parser.parse_args()

    report = load_json(Path(args.report))
    golden_docs = []
    alias_map: dict[str, str] = {}

    if args.knowledge:
        knowledge = load_knowledge_layer(Path(args.knowledge))
        alias_map = build_alias_map(knowledge)

    if args.golden:
        golden_payload = load_json(Path(args.golden))
        golden_docs = golden_payload.get("documents", golden_payload if isinstance(golden_payload, list) else [])
    else:
        golden_docs = []

    report_docs = report.get("documents", [])
    scored = compare_documents(report_docs, index_expected_biomarkers(golden_docs, alias_map), alias_map)
    quality_gate = {
        "status": "not_ready" if not golden_docs else "green",
        "reason": None,
        "unsafe_normal_rate": scored["summary"]["unsafe_normal_rate"],
        "biomarker_precision": scored["summary"]["biomarker_precision"],
        "biomarker_recall": scored["summary"]["biomarker_recall"],
        "min_biomarker_precision": args.min_biomarker_precision,
        "min_biomarker_recall": args.min_biomarker_recall,
        "max_unsafe_normal_rate": args.max_unsafe_normal_rate,
    }

    golden_ids = {doc.get("document_id") for doc in golden_docs}

    if golden_docs and any(doc.get("document_id") in golden_ids and doc.get("result") != "passed" for doc in report_docs):
        quality_gate["status"] = "red"
        quality_gate["reason"] = "documento do golden terminou bloqueado"
    elif golden_docs and scored["summary"]["unsafe_normal_rate"] is not None and scored["summary"]["unsafe_normal_rate"] > args.max_unsafe_normal_rate:
        quality_gate["status"] = "red"
        quality_gate["reason"] = (
            "unsafe_normal_rate acima do threshold "
            f"({scored['summary']['unsafe_normal_rate']} > {args.max_unsafe_normal_rate})"
        )
    elif golden_docs and (
        scored["summary"]["biomarker_precision"] is None
        or scored["summary"]["biomarker_precision"] < args.min_biomarker_precision
    ):
        quality_gate["status"] = "red"
        quality_gate["reason"] = (
            "biomarker_precision abaixo do threshold "
            f"({scored['summary']['biomarker_precision']} < {args.min_biomarker_precision})"
        )
    elif golden_docs and (
        scored["summary"]["biomarker_recall"] is None
        or scored["summary"]["biomarker_recall"] < args.min_biomarker_recall
    ):
        quality_gate["status"] = "red"
        quality_gate["reason"] = (
            "biomarker_recall abaixo do threshold "
            f"({scored['summary']['biomarker_recall']} < {args.min_biomarker_recall})"
        )
    elif golden_docs and any(doc.get("result") == "blocked" and doc.get("corpus_class") == "negative_document" for doc in report_docs):
        quality_gate["status"] = "red"
        quality_gate["reason"] = "negative_document nao pode ficar bloqueado/passar sem comportamento esperado"
    elif not golden_docs:
        quality_gate["reason"] = "golden manual ausente"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    export = {
        "report": report,
        "score": scored,
        "quality_gate": quality_gate,
    }
    (output_dir / f"{Path(args.report).stem}.score.json").write_text(
        json.dumps(export, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(output_dir / f"{Path(args.report).stem}.score.documents.csv", scored["documents"])
    print(json.dumps(export, ensure_ascii=False, indent=2))
    if args.strict_release and quality_gate["status"] != "green":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
