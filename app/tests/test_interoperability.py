import pytest
from app.services.interoperability_service import InteroperabilityService
from app.models.exame import ResultadoBiomarcador, Exame
from unittest.mock import MagicMock
from decimal import Decimal

def test_loinc_mapping():
    service = InteroperabilityService()
    assert service.map_to_loinc("GLICOSE") == "2345-7"
    assert service.map_to_loinc("Hemoglobina") == "718-7"
    assert service.map_to_loinc("GLICOSE, JEJUM") == "2345-7"
    assert service.map_to_loinc("DESCONHECIDO") is None

def test_fhir_conversion():
    service = InteroperabilityService()
    
    # Mock do Resultado
    resultado = ResultadoBiomarcador(
        nome_marcador="GLICOSE",
        valor_numerico=Decimal("95.0"),
        unidade_medida="mg/dL",
        loinc_code="2345-7",
        referencia_min=Decimal("70"),
        referencia_max=Decimal("99")
    )
    
    # Mock do Exame associado
    exame = Exame(patient_id=42)
    resultado.exame = exame
    
    fhir_obs = service.convert_to_fhir_observation(resultado, patient_id=42)
    
    assert fhir_obs["resourceType"] == "Observation"
    assert fhir_obs["subject"]["reference"] == "Patient/42"
    assert fhir_obs["code"]["coding"][0]["code"] == "2345-7"
    assert fhir_obs["valueQuantity"]["value"] == 95.0
    assert fhir_obs["referenceRange"][0]["low"]["value"] == 70.0
    assert fhir_obs["referenceRange"][0]["high"]["value"] == 99.0


def test_loinc_mapping_logs_when_cache_is_unavailable(monkeypatch, caplog):
    service = InteroperabilityService()

    def fake_get_redis_client_sync():
        raise RuntimeError("redis fora")

    monkeypatch.setattr("app.core.cache.get_redis_client_sync", fake_get_redis_client_sync)

    fake_db = MagicMock()
    fake_model_row = MagicMock(keyword="GLICOSE", loinc_code="2345-7")
    fake_db.query.return_value.all.return_value = [fake_model_row]

    with caplog.at_level("WARNING"):
        assert service.map_to_loinc("GLICOSE", db=fake_db) == "2345-7"

    assert "Cache LOINC indisponivel" in caplog.text


def test_loinc_mapping_logs_when_cache_payload_is_corrupted(monkeypatch, caplog):
    service = InteroperabilityService()

    class FakeRedis:
        def get(self, key):
            return "{invalid-json"

        def close(self):
            return None

    def fake_get_redis_client_sync():
        return FakeRedis()

    monkeypatch.setattr("app.core.cache.get_redis_client_sync", fake_get_redis_client_sync)

    fake_db = MagicMock()
    fake_model_row = MagicMock(keyword="GLICOSE", loinc_code="2345-7")
    fake_db.query.return_value.all.return_value = [fake_model_row]

    with caplog.at_level("WARNING"):
        assert service.map_to_loinc("GLICOSE", db=fake_db) == "2345-7"

    assert "Cache LOINC corrompido" in caplog.text
