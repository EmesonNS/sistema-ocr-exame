import json
import runpy
import subprocess
from pathlib import Path


def test_build_golden_quality_baseline_creates_green_contract(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "golden_quality_baseline.json"

    result = subprocess.run(
        [
            "python3",
            "evaluation/scripts/build_golden_quality_baseline.py",
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["quality_gate"]["status"] == "green"
    assert payload["quality_gate"]["unsafe_normal_rate"] == 0
    assert payload["report"]["summary"]["documents_total"] == 2
    assert payload["baseline_contract"]["kind"] == "ideal_golden_perfect_match"
    assert '"status": "green"' in result.stdout


def test_score_eval_report_green_on_perfect_golden_match(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = runpy.run_path(str(repo_root / "evaluation/scripts/score_eval_report.py"))
    golden = json.loads(
        (repo_root / "evaluation/datasets/golden/golden_exams.json").read_text(encoding="utf-8")
    )
    alias_map = module["build_alias_map"]({})
    golden_docs = module["index_expected_biomarkers"](golden["documents"], alias_map)
    perfect_report_docs = []
    for doc in golden["documents"]:
        perfect_report_docs.append(
            {
                "document_id": doc["document_id"],
                "corpus_class": "golden_candidate_raw_lab",
                "result": "passed",
                "resultados": [
                    {
                        "nome_marcador": biomarker["name"],
                        "status_alerta": biomarker["expected_status"],
                    }
                    for biomarker in doc["expected_biomarkers"]
                ],
            }
        )

    scored = module["compare_documents"](perfect_report_docs, golden_docs, alias_map)
    assert scored["summary"]["biomarker_precision"] == 1.0
    assert scored["summary"]["biomarker_recall"] == 1.0
    assert scored["summary"]["unsafe_normal_rate"] == 0.0


def test_score_eval_report_blocks_below_precision_recall_threshold(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = runpy.run_path(str(repo_root / "evaluation/scripts/score_eval_report.py"))
    golden = json.loads(
        (repo_root / "evaluation/datasets/golden/golden_exams.json").read_text(encoding="utf-8")
    )
    alias_map = module["build_alias_map"]({})
    golden_docs = module["index_expected_biomarkers"](golden["documents"], alias_map)

    low_quality_report_docs = []
    for doc in golden["documents"]:
        low_quality_report_docs.append(
            {
                "document_id": doc["document_id"],
                "corpus_class": "golden_candidate_raw_lab",
                "result": "passed",
                "resultados": [
                    {
                        "nome_marcador": doc["expected_biomarkers"][0]["name"],
                        "status_alerta": doc["expected_biomarkers"][0]["expected_status"],
                    },
                    {
                        "nome_marcador": "MARCADOR_EXTRA",
                        "status_alerta": "normal",
                    },
                ],
            }
        )

    scored = module["compare_documents"](low_quality_report_docs, golden_docs, alias_map)
    assert scored["summary"]["biomarker_precision"] == 0.5
    assert scored["summary"]["biomarker_recall"] < 0.8

    out_dir = tmp_path / "score"
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "run_id": "low-quality",
                "created_at": "2026-07-08T00:00:00+00:00",
                "git_sha": "abc123",
                "pipeline_mode": "api",
                "app_base_url": "http://127.0.0.1:18080/api",
                "knowledge_version": "0.1.0",
                "dataset_version": "1.0.0",
                "corpus_source": "amostras_exames",
                "summary": {
                    "documents_total": len(low_quality_report_docs),
                    "documents_passed": len(low_quality_report_docs),
                    "documents_blocked": 0,
                },
                "documents": low_quality_report_docs,
                "steps": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "python3",
            "evaluation/scripts/score_eval_report.py",
            "--report",
            str(report_path),
            "--golden",
            str(repo_root / "evaluation/datasets/golden/golden_exams.json"),
            "--output-dir",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    scored_report = json.loads((out_dir / "report.score.json").read_text(encoding="utf-8"))
    assert scored_report["quality_gate"]["status"] == "red"
    assert "threshold" in scored_report["quality_gate"]["reason"]
    assert scored_report["quality_gate"]["biomarker_precision"] == 0.5
