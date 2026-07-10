from types import SimpleNamespace

from app.services.interoperability_service import InteroperabilityService


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def query(self, model):
        return _FakeQuery(self.rows)


def test_map_to_loinc_prefers_database_rows(monkeypatch):
    service = InteroperabilityService()
    fake_rows = [
        SimpleNamespace(keyword="GLICOSE", loinc_code="9999-9"),
        SimpleNamespace(keyword="HEMOGLOBINA", loinc_code="718-7"),
    ]

    monkeypatch.setattr(service, "_get_loinc_model", lambda: object())

    assert service.map_to_loinc("Glicose", db=_FakeDB(fake_rows)) == "9999-9"
    assert service.map_to_loinc("Hemoglobina", db=_FakeDB(fake_rows)) == "718-7"


def test_map_to_loinc_falls_back_to_static_when_db_unavailable(monkeypatch):
    service = InteroperabilityService()

    monkeypatch.setattr(service, "_load_loinc_mapping", lambda db=None: {"GLICOSE": "2345-7"})

    assert service.map_to_loinc("Glicose") == "2345-7"
