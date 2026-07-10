from decimal import Decimal
from types import SimpleNamespace

from app.services.interoperability_service import InteroperabilityService


def test_fhir_bundle_contains_diagnostic_report_and_references():
    service = InteroperabilityService()
    exame = SimpleNamespace(
        id="exam-1",
        patient_id=42,
        data_coleta=None,
        laboratorio="Lab Teste",
        status_processamento="concluido",
        original_filename="hemograma.pdf",
        storage_content_type="application/pdf",
        resultados=[
            SimpleNamespace(
                id="result-1",
                nome_marcador="GLICOSE",
                valor_numerico=Decimal("95.0"),
                unidade_medida="mg/dL",
                loinc_code="2345-7",
                referencia_min=Decimal("70"),
                referencia_max=Decimal("99"),
                exame=SimpleNamespace(data_coleta=None),
            )
        ],
    )

    bundle = service.build_fhir_bundle(exame)

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert len(bundle["entry"]) == 2

    diagnostic_report = bundle["entry"][0]["resource"]
    observation = bundle["entry"][1]["resource"]

    assert diagnostic_report["resourceType"] == "DiagnosticReport"
    assert diagnostic_report["status"] == "final"
    assert diagnostic_report["subject"]["reference"] == "Patient/42"
    assert diagnostic_report["result"] == [{"reference": "urn:uuid:Observation/result-1"}]
    assert observation["resourceType"] == "Observation"
    assert observation["code"]["coding"][0]["code"] == "2345-7"
