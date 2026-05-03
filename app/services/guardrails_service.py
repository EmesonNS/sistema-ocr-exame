"""
Serviço de Guardrails para segurança e plausibilidade de dados de saúde.

Implementa verificações determinísticas e heurísticas para garantir que 
os dados extraídos pela IA sejam seguros e clinicamente plausíveis.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

# Faixas de plausibilidade fisiológica (Sanity Ranges)
# Se o valor estiver FORA desta faixa, é provável que seja um erro de OCR/IA.
PHYSIOLOGICAL_RANGES = {
    "GLICOSE": (20, 1000),      # mg/dL
    "HEMOGLOBINA": (3, 25),     # g/dL
    "HEMATÓCRITO": (10, 75),    # %
    "LEUCÓCITOS": (200, 300000), # /mm³
    "PLAQUETAS": (5000, 1500000), # /mm³
    "COLESTEROL TOTAL": (50, 600), # mg/dL
    "TRIGLICERÍDEOS": (20, 3000),  # mg/dL
    "UREIA": (5, 400),           # mg/dL
    "CREATININA": (0.1, 25),     # mg/dL
    "SÓDIO": (100, 180),         # mEq/L
    "POTÁSSIO": (1.5, 10),       # mEq/L
}

# Palavras-chave que indicam possível injeção de prompt ou instrução maliciosa
INJECTION_KEYWORDS = [
    "ignore todas", "ignorar instruções", "instruções anteriores", 
    "system note", "set value", "mude o valor", "developer mode",
    "prompt injection", "overwrite", "dan mode"
]

class GuardrailsService:
    """Serviço para validar segurança e coerência dos dados extraídos."""

    def validate_plausibility(self, nome: str, valor: float) -> Tuple[bool, Optional[str]]:
        """
        Verifica se um valor numérico é plausível para o biomarcador informado.
        
        Returns:
            Tuple (is_plausible, warning_message)
        """
        nome_upper = nome.upper()
        
        # Procurar correspondência no dicionário de faixas
        for marcador, (min_val, max_val) in PHYSIOLOGICAL_RANGES.items():
            if marcador in nome_upper:
                if valor < min_val or valor > max_val:
                    msg = (
                        f"Valor {valor} para {nome} está fora da faixa fisiológica "
                        f"plausível ({min_val}-{max_val}). Possível erro de OCR."
                    )
                    logger.warning(msg)
                    return False, msg
                return True, None
                
        # Se não temos regra, assumimos plausível mas logamos
        return True, None

    def detect_prompt_injection(self, text: str) -> bool:
        """
        Detecta tentativas de manipular a IA através de texto malicioso no documento.
        """
        text_lower = text.lower()
        for keyword in INJECTION_KEYWORDS:
            if keyword in text_lower:
                logger.error(f"Possível injeção de prompt detectada: '{keyword}'")
                return True
        return False

    def sanitize_results(self, resultados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aplica os guardrails a uma lista de resultados normalizados.
        """
        for res in resultados:
            valor_num = res.get("valor_numerico")
            nome = res.get("nome_marcador_normalizado", res.get("nome_marcador", ""))
            
            if valor_num is not None:
                # Converter para float para comparação se necessário
                val = float(valor_num)
                is_ok, warning = self.validate_plausibility(nome, val)
                
                if not is_ok:
                    res["needs_review"] = True
                    res["status_alerta"] = "incoerente"
                    current_correcao = res.get("correcao_aplicada")
                    res["correcao_aplicada"] = (
                        f"{current_correcao + ' | ' if current_correcao else ''}"
                        f"ALERTA SEGURANÇA: {warning}"
                    )
        
        return resultados
