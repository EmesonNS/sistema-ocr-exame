"""
Serviço de Interoperabilidade para mapeamento LOINC e exportação FHIR.
"""

import logging
from typing import Optional, List, Dict
from app.models.exame import ResultadoBiomarcador

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

    def map_to_loinc(self, nome_marcador: str) -> Optional[str]:
        """Mapeia um nome de marcador para o código LOINC correspondente."""
        if not nome_marcador:
            return None
        
        normalized_name = nome_marcador.upper().replace("Ó", "O").replace("Í", "I").replace("Ê", "E").replace("Á", "A")
        
        # Busca direta
        if normalized_name in LOINC_MAPPING:
            return LOINC_MAPPING[normalized_name]
        
        # Busca por substring parcial (ex: "GLICOSE, JEJUM")
        for key, code in LOINC_MAPPING.items():
            if key in normalized_name:
                return code
                
        return None

    def convert_to_fhir_observation(self, resultado: ResultadoBiomarcador, patient_id: int) -> Dict:
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
            "effectiveDateTime": resultado.exame.data_coleta.isoformat() if resultado.exame and resultado.exame.data_coleta else None,
            "valueQuantity": {
                "value": float(resultado.valor_numerico) if resultado.valor_numerico else None,
                "unit": resultado.unidade_medida,
                "system": "http://unitsofmeasure.org",
                "code": resultado.unidade_medida
            }
        }

        # Adiciona LOINC se disponível
        if resultado.loinc_code:
            observation["code"]["coding"].append({
                "system": "http://loinc.org",
                "code": resultado.loinc_code,
                "display": resultado.nome_marcador
            })
        else:
            observation["code"]["text"] = resultado.nome_marcador

        # Adiciona referência se disponível
        if resultado.referencia_min is not None or resultado.referencia_max is not None:
            observation["referenceRange"] = [{
                "low": {"value": float(resultado.referencia_min)} if resultado.referencia_min is not None else None,
                "high": {"value": float(resultado.referencia_max)} if resultado.referencia_max is not None else None,
                "type": {"text": "Normal Range"}
            }]

        return observation
