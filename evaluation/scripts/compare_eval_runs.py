#!/usr/bin/env python3
"""
Compara duas execucoes do eval OCR.

O objetivo e tornar regressao entre runs rastreavel sem depender de analise
manual do JSON bruto. O comparador trabalha sobre saidas ja scored.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_delta(base: Any, head: Any) -> dict[str, Any]:
    if isinstance(base, (int, float)) and isinstance(head, (int, float)):
        return {
            "base": base,
            "head": head,
            "delta": head - base,
        }
    return {"base": base, "head": head, "delta": None}


def summarize_findings(score_payload: dict[str, Any]) -> dict[str, int]:
    return dict(Counter(finding.get("type", "unknown") for finding in score_payload.get("score", {}).get("findings", [])))


def build_comparison(base: dict[str, Any], head: dict[str, Any]) -> dict[str, Any]:
    base_summary = base.get("score", {}).get("summary", {})
    head_summary = head.get("score", {}).get("summary", {})
    base_gate = base.get("quality_gate", {})
    head_gate = head.get("quality_gate", {})

    metrics = {
        "documents_passed": metric_delta(base_summary.get("documents_passed"), head_summary.get("documents_passed")),
        "documents_blocked": metric_delta(base_summary.get("documents_blocked"), head_summary.get("documents_blocked")),
        "biomarker_precision": metric_delta(base_summary.get("biomarker_precision"), head_summary.get("biomarker_precision")),
        "biomarker_recall": metric_delta(base_summary.get("biomarker_recall"), head_summary.get("biomarker_recall")),
        "unsafe_normal_rate": metric_delta(base_summary.get("unsafe_normal_rate"), head_summary.get("unsafe_normal_rate")),
    }

    regressions: list[dict[str, Any]] = []
    if metrics["documents_blocked"]["delta"] is not None and metrics["documents_blocked"]["delta"] > 0:
        regressions.append(
            {
                "metric": "documents_blocked",
                "reason": "mais documentos bloqueados na run mais nova",
            }
        )
    if metrics["biomarker_precision"]["delta"] is not None and metrics["biomarker_precision"]["delta"] < 0:
        regressions.append(
            {
                "metric": "biomarker_precision",
                "reason": "precision de biomarcadores caiu",
            }
        )
    if metrics["biomarker_recall"]["delta"] is not None and metrics["biomarker_recall"]["delta"] < 0:
        regressions.append(
            {
                "metric": "biomarker_recall",
                "reason": "recall de biomarcadores caiu",
            }
        )
    if metrics["unsafe_normal_rate"]["delta"] is not None and metrics["unsafe_normal_rate"]["delta"] > 0:
        regressions.append(
            {
                "metric": "unsafe_normal_rate",
                "reason": "taxa unsafe_normal subiu",
            }
        )
    if base_gate.get("status") == "green" and head_gate.get("status") != "green":
        regressions.append(
            {
                "metric": "quality_gate",
                "reason": "gate piorou de green para nao-green",
            }
        )

    return {
        "base": {
            "run_id": base.get("report", {}).get("run_id") or base.get("run_id"),
            "created_at": base.get("report", {}).get("created_at") or base.get("created_at"),
            "quality_gate": base_gate,
            "findings": summarize_findings(base),
        },
        "head": {
            "run_id": head.get("report", {}).get("run_id") or head.get("run_id"),
            "created_at": head.get("report", {}).get("created_at") or head.get("created_at"),
            "quality_gate": head_gate,
            "findings": summarize_findings(head),
        },
        "metrics": metrics,
        "regressions": regressions,
        "comparison_gate": {
            "status": "red" if regressions else "green",
            "reason": "regressao detectada" if regressions else "sem regressao detectada",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two OCR eval score reports.")
    parser.add_argument("--base", required=True, help="Score report base")
    parser.add_argument("--head", required=True, help="Score report head")
    parser.add_argument("--output-dir", required=True, help="Diretorio de saida")
    parser.add_argument("--strict-release", action="store_true", help="Falha quando houver regressao")
    args = parser.parse_args()

    base = load_json(Path(args.base))
    head = load_json(Path(args.head))
    comparison = build_comparison(base, head)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(args.head).stem}.vs.{Path(args.base).stem}.compare.json"
    output_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(comparison, ensure_ascii=False, indent=2))

    if args.strict_release and comparison["comparison_gate"]["status"] != "green":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
