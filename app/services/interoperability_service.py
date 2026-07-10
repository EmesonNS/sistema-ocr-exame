"""
Serviço de Interoperabilidade para mapeamento LOINC e exportação FHIR.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

logger = logging.getLogger(__name__)

# Dicionário simplificado de mapeamento para LOINC
# Em produção, isso seria uma tabela no banco ou consulta a uma API externa.
LOINC_MAPPING = {
    "GLICOSE": "2345-7",
    "HEMOGLOBINA": "718-7",
    "HEMATOCRITO": "4544-3",
    "LEUCOCITOS": "6690-2",
    "ERITROCITOS": "789-8",
    "PLAQUETAS": "777-3",
    "COLESTEROL TOTAL": "2093-3",
    "TRIGLICERIDEOS": "2571-8",
    "HDL": "2085-9",
    "LDL": "13457-7",
    "VLDL": "46986-6",
    "UREIA": "22664-4",
    "CREATININA": "2160-0",
    "TGO": "1920-8",
    "TGP": "1742-6",
    "TSH": "11579-0",
    "T4 LIVRE": "3024-7",
}

class InteroperabilityService:
    """Gerencia padrões de interoperabilidade clínica (LOINC, FHIR)."""

    def map_to_loinc(self, nome_marcador: str, db: Any | None = None) -> Optional[str]:
        """Mapeia um nome de marcador para o código LOINC correspondente."""
        if not nome_marcador:
            return None

        normalized_name = nome_marcador.upper().replace("Ó", "O").replace("Í", "I").replace("Ê", "E").replace("Á", "A")

        loinc_map = self._load_loinc_mapping(db)

        if normalized_name in loinc_map:
            return loinc_map[normalized_name]

        for key, code in loinc_map.items():
            if key in normalized_name:
                return code

        return None

    def _load_loinc_mapping(self, db: Any | None = None) -> Dict[str, str]:
        if db is None:
            return dict(LOINC_MAPPING)

        cache_key = "loinc_mapping:v1"
        try:
            from app.core.cache import get_redis_client_sync

            redis_client = get_redis_client_sync()
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    try:
                        return json.loads(cached)
                    except json.JSONDecodeError as exc:
                        logger.warning("Cache LOINC corrompido, ignorando entrada: %s", exc)
            finally:
                redis_client.close()
        except Exception as exc:
            logger.warning("Cache LOINC indisponivel, usando fallback: %s", exc)

        try:
            model = self._get_loinc_model()
            rows = db.query(model).all()
            mapping = {str(row.keyword).upper(): row.loinc_code for row in rows if row.keyword and row.loinc_code}
            if mapping:
                try:
                    redis_client = get_redis_client_sync()
                    try:
                        redis_client.set(cache_key, json.dumps(mapping), ex=86400)
                    finally:
                        redis_client.close()
                except Exception as exc:
                    logger.warning("Falha ao atualizar cache LOINC: %s", exc)
                return mapping
        except Exception:
            logger.warning("Falha ao carregar LOINC do banco, usando fallback estático")

        return dict(LOINC_MAPPING)

    def _get_loinc_model(self):
        from app.models.loinc_mapping import LoincMapping

        return LoincMapping

    def convert_to_fhir_observation(self, resultado: Any, patient_id: int) -> Dict:
        """Converte um resultado de biomarcador para o recurso FHIR Observation."""
        observation = {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": []
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": (
                resultado.exame.data_coleta.isoformat()
                if getattr(resultado, "exame", None) and getattr(resultado.exame, "data_coleta", None)
                else None
            ),
            "valueQuantity": {
                "value": float(resultado.valor_numerico) if getattr(resultado, "valor_numerico", None) is not None else None,
                "unit": getattr(resultado, "unidade_medida", None),
                "system": "http://unitsofmeasure.org",
                "code": getattr(resultado, "unidade_medida", None)
            }
        }

        # Adiciona LOINC se disponível
        if getattr(resultado, "loinc_code", None):
            observation["code"]["coding"].append({
                "system": "http://loinc.org",
                "code": resultado.loinc_code,
                "display": resultado.nome_marcador
            })
        else:
            observation["code"]["text"] = getattr(resultado, "nome_marcador", None)

        # Adiciona referência se disponível
        if getattr(resultado, "referencia_min", None) is not None or getattr(resultado, "referencia_max", None) is not None:
            observation["referenceRange"] = [{
                "low": {"value": float(resultado.referencia_min)} if resultado.referencia_min is not None else None,
                "high": {"value": float(resultado.referencia_max)} if resultado.referencia_max is not None else None,
                "type": {"text": "Normal Range"}
            }]

        return observation

    def build_fhir_diagnostic_report(self, exame: Any, observation_refs: List[Dict[str, str]]) -> Dict:
        """Monta um DiagnosticReport FHIR R4 para um exame e seus resultados."""
        diagnostic_report = {
            "resourceType": "DiagnosticReport",
            "status": "final" if getattr(exame, "status_processamento", None) == "concluido" else "partial",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "LAB",
                            "display": "Laboratory",
                        }
                    ]
                }
            ],
            "code": {
                "text": "Exame Laboratorial"
            },
            "subject": {
                "reference": f"Patient/{exame.patient_id}"
            },
            "effectiveDateTime": (
                exame.data_coleta.isoformat()
                if getattr(exame, "data_coleta", None)
                else None
            ),
            "issued": datetime.now(timezone.utc).isoformat(),
            "result": observation_refs,
        }

        if getattr(exame, "laboratorio", None):
            diagnostic_report["performer"] = [
                {
                    "display": exame.laboratorio,
                }
            ]

        if getattr(exame, "original_filename", None):
            diagnostic_report["presentedForm"] = [
                {
                    "contentType": getattr(exame, "storage_content_type", None) or "application/pdf",
                    "title": exame.original_filename,
                }
            ]

        return diagnostic_report

    def build_fhir_bundle(self, exame: Any) -> Dict:
        """Agrupa DiagnosticReport e Observations em um Bundle FHIR."""
        resultados = list(getattr(exame, "resultados", []) or [])
        if not resultados:
            raise ValueError("Exame não possui resultados para exportar")

        entries: List[Dict[str, Any]] = []
        observation_refs: List[Dict[str, str]] = []
        for resultado in resultados:
            observation = self.convert_to_fhir_observation(resultado, exame.patient_id)
            observation_full_url = f"urn:uuid:Observation/{resultado.id}"
            entries.append(
                {
                    "fullUrl": observation_full_url,
                    "resource": observation,
                }
            )
            observation_refs.append({"reference": observation_full_url})

        diagnostic_report = self.build_fhir_diagnostic_report(exame, observation_refs)
        entries.insert(
            0,
            {
                "fullUrl": f"urn:uuid:DiagnosticReport/{exame.id}",
                "resource": diagnostic_report,
            },
        )

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": entries,
        }
