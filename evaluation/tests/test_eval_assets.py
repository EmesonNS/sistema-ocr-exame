import json
from pathlib import Path
import runpy
import subprocess

from jsonschema import validate


def test_corpus_manifest_has_nine_documents():
    manifest = json.loads(
        Path("evaluation/datasets/manifests/corpus_manifest.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        Path("evaluation/schemas/corpus_manifest.schema.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == "1.0.0"
    assert len(manifest["documents"]) == 9
    assert any(doc["corpus_class"] == "golden_candidate_raw_lab" for doc in manifest["documents"])
    assert any(doc["corpus_class"] == "negative_document" for doc in manifest["documents"])
    validate(manifest, schema)


def test_schema_accepts_negative_document_with_empty_expected_biomarkers():
    schema = json.loads(
        Path("evaluation/schemas/golden_exam.schema.json").read_text(encoding="utf-8")
    )
    negative_document = {
        "document_id": "negative_case",
        "file_path": "evaluation/datasets/negative_documents/example.pdf",
        "document_type": "non_lab_document",
        "source_status": "real",
        "expected_behavior": "reject_or_zero_biomarkers",
        "expected_biomarkers": [],
    }

    validate(negative_document, schema)


def test_initial_golden_baseline_is_schema_valid_and_shadow_decision_is_recorded():
    golden = json.loads(
        Path("evaluation/datasets/golden/golden_exams.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        Path("evaluation/schemas/golden_exam.schema.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        Path("evaluation/datasets/manifests/corpus_manifest.json").read_text(encoding="utf-8")
    )

    assert golden["version"] == "1.0.0"
    assert len(golden["documents"]) == 2
    assert {doc["document_id"] for doc in golden["documents"]} == {
        "laudo_completo_2026_02_04",
        "laudosabin_ana_rodrigues_2025_05_13",
    }
    for doc in golden["documents"]:
        validate(doc, schema)

    emissao = next(
        doc for doc in manifest["documents"] if doc["document_id"] == "emissao_de_laudo"
    )
    assert emissao["curation_status"] == "shadow_document_confirmed"


def test_runner_build_report_includes_git_sha_and_mode():
    module = runpy.run_path("evaluation/scripts/run_ocr_eval.py")
    manifest = json.loads(
        Path("evaluation/datasets/manifests/corpus_manifest.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        Path("evaluation/schemas/run_report.schema.json").read_text(encoding="utf-8")
    )

    report = module["build_report"](
        "run-id",
        manifest,
        "http://127.0.0.1:18080/api",
        {"email": "eval@example.com", "cnpj": "123"},
        [],
        "api",
    )

    assert report["git_sha"] != "unknown"
    assert report["pipeline_mode"] == "api"
    assert report["summary"]["documents_total"] == 0
    validate(report, schema)


def test_runner_in_process_mode_uses_local_ai_service_without_http():
    module = runpy.run_path("evaluation/scripts/run_ocr_eval.py")

    class FakeAIService:
        async def extrair_biomarcadores(self, file_path):
            assert file_path.endswith("Laudo Completo 04_02_2026 (1).pdf")
            return (
                [
                    {
                        "nome_marcador": "HEMOGLOBINA",
                        "valor_raw": "13,0",
                        "unidade_medida": "g/dL",
                        "referencia_lab": "14.0 - 17.0",
                        "referencia_min": 14.0,
                        "referencia_max": 17.0,
                        "status_alerta": "alto",
                        "needs_review": False,
                    }
                ],
                "15/02/2026",
                "Lab Teste",
            )

    manifest = json.loads(
        Path("evaluation/datasets/manifests/corpus_manifest.json").read_text(encoding="utf-8")
    )
    doc = next(doc for doc in manifest["documents"] if doc["document_id"] == "laudo_completo_2026_02_04")
    doc_run = module["run_document_in_process"](doc, FakeAIService())

    assert doc_run.final_status == "concluido"
    assert doc_run.processing_stage == "completed"
    assert doc_run.result == "passed"
    assert doc_run.resultados and doc_run.resultados[0]["nome_marcador"] == "HEMOGLOBINA"


def test_export_eval_report_builds_release_artifacts(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    runner_report = {
        "run_id": "run-id",
        "created_at": "2026-07-08T00:00:00+00:00",
        "git_sha": "abc123",
        "pipeline_mode": "api",
        "app_base_url": "http://127.0.0.1:18080/api",
        "knowledge_version": "0.1.0",
        "dataset_version": "1.0.0",
        "corpus_source": "amostras_exames",
        "summary": {"documents_total": 1, "documents_passed": 0, "documents_blocked": 1},
        "documents": [
            {
                "document_id": "ana_caroline",
                "corpus_class": "derived_output_do_not_use_as_source",
                "result": "blocked",
                "upload_status": 201,
                "exam_id": "exam-1",
                "final_status": "erro",
                "processing_stage": "failed",
                "processing_percent": 0,
                "processing_message": "Nenhum dado extraído do documento",
                "download_status": None,
                "pdf_bytes": None,
                "error": "terminal=erro: Nenhum dado extraído do documento",
            }
        ],
        "steps": [{"name": "auth", "role": "CLINIC", "jwt_role": "CLINIC"}],
    }
    input_path = tmp_path / "runner.json"
    input_path.write_text(json.dumps(runner_report, ensure_ascii=False), encoding="utf-8")

    export_path = tmp_path / "out"
    result = subprocess.run(
        [
            "python3",
            "evaluation/scripts/export_eval_report.py",
            "--input",
            str(input_path),
            "--output-dir",
            str(export_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    exported = json.loads((export_path / "runner.export.json").read_text(encoding="utf-8"))
    assert exported["quality_gate"]["status"] == "not_ready"
    assert exported["quality_gate"]["candidate_documents"] == 0
    assert "\"status\": \"not_ready\"" in result.stdout
    assert (export_path / "runner.documents.csv").exists()
    assert (export_path / "runner.steps.csv").exists()

    strict = subprocess.run(
        [
            "python3",
            "evaluation/scripts/export_eval_report.py",
            "--input",
            str(input_path),
            "--output-dir",
            str(export_path),
            "--strict-release",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1


def test_score_eval_report_detects_unsafe_normal(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    report = {
        "run_id": "run-id",
        "created_at": "2026-07-08T00:00:00+00:00",
        "git_sha": "abc123",
        "pipeline_mode": "api",
        "app_base_url": "http://127.0.0.1:18080/api",
        "knowledge_version": "0.1.0",
        "dataset_version": "1.0.0",
        "corpus_source": "amostras_exames",
        "summary": {"documents_total": 1, "documents_passed": 1, "documents_blocked": 0},
        "documents": [
            {
                "document_id": "laudo_completo_2026_02_04",
                "corpus_class": "golden_candidate_raw_lab",
                "result": "passed",
                "upload_status": 201,
                "exam_id": "exam-1",
                "final_status": "concluido",
                "processing_stage": "completed",
                "processing_percent": 100,
                "processing_message": "ok",
                "download_status": 200,
                "pdf_bytes": 1024,
                "error": None,
                "resultados": [
                    {
                        "nome_marcador": "HEMOGLOBINA",
                        "valor_extraido": "13.0",
                        "unidade_medida": "g/dL",
                        "referencia_lab": "14.0 - 17.0",
                        "referencia_min": 14.0,
                        "referencia_max": 17.0,
                        "status_alerta": "normal",
                        "needs_review": False,
                    }
                ],
            }
        ],
        "steps": [],
    }
    report_path = tmp_path / "runner.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    golden = {
        "documents": [
            {
                "document_id": "laudo_completo_2026_02_04",
                "file_path": "evaluation/datasets/raw_labs/Laudo Completo 04_02_2026 (1).pdf",
                "document_type": "lab_report",
                "source_status": "real",
                "expected_behavior": "extract_biomarkers",
                "expected_biomarkers": [
                    {
                        "name": "HEMOGLOBINA",
                        "value_raw": "13,0",
                        "value_numeric": 13.0,
                        "unit": "g/dL",
                        "reference_min": 14.0,
                        "reference_max": 17.0,
                        "expected_status": "alto",
                    }
                ],
            }
        ]
    }
    golden_path = tmp_path / "golden.json"
    golden_path.write_text(json.dumps(golden, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "score"
    result = subprocess.run(
        [
            "python3",
            "evaluation/scripts/score_eval_report.py",
            "--report",
            str(report_path),
            "--golden",
            str(golden_path),
            "--knowledge",
            "evaluation/knowledge",
            "--output-dir",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    scored = json.loads((out_dir / "runner.score.json").read_text(encoding="utf-8"))
    assert scored["quality_gate"]["status"] == "red"
    assert scored["score"]["summary"]["unsafe_normal_rate"] == 1.0
    assert scored["score"]["summary"]["biomarker_recall"] == 1.0
    assert scored["score"]["summary"]["biomarker_precision"] == 1.0
    assert any(finding["type"] == "unsafe_normal" for finding in scored["score"]["findings"])

    strict = subprocess.run(
        [
            "python3",
            "evaluation/scripts/score_eval_report.py",
            "--report",
            str(report_path),
            "--golden",
            str(golden_path),
            "--knowledge",
            "evaluation/knowledge/canonical_biomarkers.json",
            "--output-dir",
            str(out_dir),
            "--strict-release",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1


def test_compare_documents_handles_aliases_and_unsafe_normal():
    module = runpy.run_path("evaluation/scripts/score_eval_report.py")
    knowledge = {
        "canonical_biomarkers": [
            {
                "name": "HEMOGLOBINA",
                "aliases": ["HB", "Hemoglobina"],
            }
        ]
    }
    alias_map = module["build_alias_map"](knowledge)
    golden_docs = module["index_expected_biomarkers"](
        [
            {
                "document_id": "doc-1",
                "document_type": "lab_report",
                "expected_behavior": "extract_biomarkers",
                "expected_biomarkers": [
                    {
                        "name": "HB",
                        "expected_status": "alto",
                    }
                ],
            }
        ],
        alias_map,
    )
    scored = module["compare_documents"](
        [
            {
                "document_id": "doc-1",
                "corpus_class": "golden_candidate_raw_lab",
                "result": "passed",
                "resultados": [
                    {
                        "nome_marcador": "Hemoglobina",
                        "status_alerta": "normal",
                    }
                ],
            }
        ],
        golden_docs,
        alias_map,
    )

    assert scored["summary"]["documents_scored"] == 1
    assert scored["summary"]["biomarker_precision"] == 1.0
    assert scored["summary"]["biomarker_recall"] == 1.0
    assert scored["summary"]["unsafe_normal_rate"] == 1.0
    assert any(finding["type"] == "unsafe_normal" for finding in scored["findings"])


def test_load_knowledge_layer_reads_versioned_directory():
    module = runpy.run_path("evaluation/scripts/score_eval_report.py")
    knowledge = module["load_knowledge_layer"](Path("evaluation/knowledge"))

    assert knowledge["knowledge_version"] == "0.1.0"
    assert "canonical_biomarkers" in knowledge
    assert "unit_aliases" in knowledge
    assert "clinical_rules" in knowledge
    assert any(item["name"] == "HEMOGLOBINA" for item in knowledge["canonical_biomarkers"])


def test_compare_eval_runs_detects_regression(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    base_score = {
        "report": {"run_id": "base-run", "created_at": "2026-07-08T00:00:00+00:00"},
        "quality_gate": {"status": "green", "reason": None},
        "score": {
            "summary": {
                "documents_passed": 1,
                "documents_blocked": 0,
                "biomarker_precision": 1.0,
                "biomarker_recall": 1.0,
                "unsafe_normal_rate": 0.0,
            },
            "findings": [],
        },
    }
    head_score = {
        "report": {"run_id": "head-run", "created_at": "2026-07-08T00:05:00+00:00"},
        "quality_gate": {"status": "red", "reason": "regressao"},
        "score": {
            "summary": {
                "documents_passed": 1,
                "documents_blocked": 1,
                "biomarker_precision": 0.5,
                "biomarker_recall": 0.75,
                "unsafe_normal_rate": 1.0,
            },
            "findings": [{"type": "unsafe_normal"}],
        },
    }
    base_path = tmp_path / "base.score.json"
    head_path = tmp_path / "head.score.json"
    base_path.write_text(json.dumps(base_score, ensure_ascii=False), encoding="utf-8")
    head_path.write_text(json.dumps(head_score, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "compare"
    result = subprocess.run(
        [
            "python3",
            "evaluation/scripts/compare_eval_runs.py",
            "--base",
            str(base_path),
            "--head",
            str(head_path),
            "--output-dir",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    comparison = json.loads((out_dir / "head.score.vs.base.score.compare.json").read_text(encoding="utf-8"))
    assert comparison["comparison_gate"]["status"] == "red"
    assert comparison["metrics"]["biomarker_precision"]["delta"] == -0.5
    assert comparison["metrics"]["unsafe_normal_rate"]["delta"] == 1.0
    assert comparison["regressions"]
    assert "\"comparison_gate\": {" in result.stdout

    strict = subprocess.run(
        [
            "python3",
            "evaluation/scripts/compare_eval_runs.py",
            "--base",
            str(base_path),
            "--head",
            str(head_path),
            "--output-dir",
            str(out_dir),
            "--strict-release",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
