"""
Serviços de negócio do sistema OCR de exames.
"""

from app.services.biomarker_normalization import (
    TipoValor,
    NivelAlerta,
    FonteValor,
    extrair_tipo_valor,
    parse_valor_numerico,
    parse_referencia,
    normalizar_unidade,
    classificar_alerta,
    detectar_decimal_deslocado,
    converter_percentual_para_absoluto,
    normalizar_nome_marcador,
    normalizar_resultado_biomarcador,
)
from app.services.decimal_correction import (
    obter_range_esperado,
    sugerir_correcao_decimal,
    escolher_melhor_correcao,
    validar_coerencia_valor,
)

__all__ = [
    # biomarker_normalization
    "TipoValor",
    "NivelAlerta",
    "FonteValor",
    "extrair_tipo_valor",
    "parse_valor_numerico",
    "parse_referencia",
    "normalizar_unidade",
    "classificar_alerta",
    "detectar_decimal_deslocado",
    "converter_percentual_para_absoluto",
    "normalizar_nome_marcador",
    "normalizar_resultado_biomarcador",
    # decimal_correction
    "obter_range_esperado",
    "sugerir_correcao_decimal",
    "escolher_melhor_correcao",
    "validar_coerencia_valor",
]
