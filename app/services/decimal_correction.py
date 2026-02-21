"""
Heurísticas específicas para correção de decimais deslocados.

Este módulo contém lógica especializada para detectar e sugerir correções
quando valores de biomarcadores parecem ter decimais deslocados.

TODOS os valores de referência aqui são para VALIDAÇÃO de coerência,
NÃO para diagnóstico médico.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


# Ranges esperados por marcador para VALIDAÇÃO (não diagnóstico)
# Estes valores servem para detectar anomalias óbvias de OCR/digitacao
EXPECTED_RANGES = {
    # Hemograma
    "HEMOGLOBINA": (Decimal("7.0"), Decimal("20.0"), "g/dL"),
    "HEMATOCRITO": (Decimal("21.0"), Decimal("60.0"), "%"),
    "HEMÁCIAS": (Decimal("3.0"), Decimal("6.5"), "milhões/mm³"),
    "HEMACIAS": (Decimal("3.0"), Decimal("6.5"), "milhões/mm³"),
    "LEUCÓCITOS": (Decimal("2500"), Decimal("15000"), "/mm³"),
    "LEUCOCITOS": (Decimal("2500"), Decimal("15000"), "/mm³"),
    "PLAQUETAS": (Decimal("100000"), Decimal("500000"), "/mm³"),
    "VCM": (Decimal("60"), Decimal("110"), "fL"),
    "HCM": (Decimal("20"), Decimal("40"), "pg"),
    "CHCM": (Decimal("28"), Decimal("38"), "g/dL"),
    "RDW": (Decimal("10"), Decimal("20"), "%"),
    # Diferencial de leucócitos (valores absolutos típicos)
    "NEUTRÓFILOS": (Decimal("1500"), Decimal("8000"), "/mm³"),
    "NEUTROFILOS": (Decimal("1500"), Decimal("8000"), "/mm³"),
    "SEGMENTADOS": (Decimal("1500"), Decimal("8000"), "/mm³"),
    "BASTONETES": (Decimal("0"), Decimal("500"), "/mm³"),
    "LINFÓCITOS": (Decimal("1000"), Decimal("4000"), "/mm³"),
    "LINFOCITOS": (Decimal("1000"), Decimal("4000"), "/mm³"),
    "MONÓCITOS": (Decimal("100"), Decimal("1000"), "/mm³"),
    "MONOCITOS": (Decimal("100"), Decimal("1000"), "/mm³"),
    "EOSINÓFILOS": (Decimal("0"), Decimal("700"), "/mm³"),
    "EOSINOFILOS": (Decimal("0"), Decimal("700"), "/mm³"),
    "BASÓFILOS": (Decimal("0"), Decimal("200"), "/mm³"),
    "BASOFILOS": (Decimal("0"), Decimal("200"), "/mm³"),
    # Bioquímica
    "GLICOSE": (Decimal("50"), Decimal("300"), "mg/dL"),
    "GLICEMIA": (Decimal("50"), Decimal("300"), "mg/dL"),
    "CREATININA": (Decimal("0.3"), Decimal("15.0"), "mg/dL"),
    "UREIA": (Decimal("10"), Decimal("200"), "mg/dL"),
    "UREIA PRE": (Decimal("10"), Decimal("200"), "mg/dL"),
    "ÁCIDO ÚRICO": (Decimal("2.0"), Decimal("12.0"), "mg/dL"),
    "ACIDO URICO": (Decimal("2.0"), Decimal("12.0"), "mg/dL"),
    # Função hepática
    "TGO": (Decimal("5"), Decimal("200"), "U/L"),
    "AST": (Decimal("5"), Decimal("200"), "U/L"),
    "TGP": (Decimal("5"), Decimal("200"), "U/L"),
    "ALT": (Decimal("5"), Decimal("200"), "U/L"),
    "GAMA GT": (Decimal("5"), Decimal("300"), "U/L"),
    "GAMAGT": (Decimal("5"), Decimal("300"), "U/L"),
    "GGT": (Decimal("5"), Decimal("300"), "U/L"),
    "FA": (Decimal("30"), Decimal("300"), "U/L"),
    "FOSFATASE ALCALINA": (Decimal("30"), Decimal("300"), "U/L"),
    "BILIRRUBINA TOTAL": (Decimal("0.1"), Decimal("20.0"), "mg/dL"),
    "BILIRRUBINA DIRETA": (Decimal("0.0"), Decimal("10.0"), "mg/dL"),
    "BILIRRUBINA INDIRETA": (Decimal("0.1"), Decimal("15.0"), "mg/dL"),
    # Lipídios
    "COLESTEROL TOTAL": (Decimal("80"), Decimal("350"), "mg/dL"),
    "HDL": (Decimal("20"), Decimal("100"), "mg/dL"),
    "LDL": (Decimal("30"), Decimal("250"), "mg/dL"),
    "VLDL": (Decimal("5"), Decimal("100"), "mg/dL"),
    "TRIGLICERÍDEOS": (Decimal("30"), Decimal("500"), "mg/dL"),
    "TRIGLICERIDEOS": (Decimal("30"), Decimal("500"), "mg/dL"),
    # Tireoide
    "TSH": (Decimal("0.1"), Decimal("20.0"), "mUI/L"),
    "T4 LIVRE": (Decimal("0.4"), Decimal("5.0"), "ng/dL"),
    "T4 TOTAL": (Decimal("3.0"), Decimal("20.0"), "mcg/dL"),
    "T3 LIVRE": (Decimal("1.5"), Decimal("6.0"), "pg/mL"),
    "T3 TOTAL": (Decimal("60"), Decimal("200"), "ng/dL"),
    # Vitaminas e minerais
    "VITAMINA D": (Decimal("5"), Decimal("150"), "ng/mL"),
    "VITAMINA B12": (Decimal("100"), Decimal("2000"), "pg/mL"),
    "FERRO": (Decimal("20"), Decimal("200"), "mcg/dL"),
    "FERRITINA": (Decimal("5"), Decimal("500"), "ng/mL"),
    # Coagulação
    "TP": (Decimal("8"), Decimal("20"), "segundos"),
    "INR": (Decimal("0.8"), Decimal("5.0"), ""),
    "TTPA": (Decimal("20"), Decimal("50"), "segundos"),
    "APTT": (Decimal("20"), Decimal("50"), "segundos"),
}


def obter_range_esperado(marcador: str) -> Optional[tuple[Decimal, Decimal, str]]:
    """
    Obtém o range esperado para um marcador.

    Args:
        marcador: Nome do marcador (case insensitive)

    Returns:
        Tupla (min, max, unidade) ou None se marcador não conhecido
    """
    marcador_upper = marcador.upper().strip()

    # Busca direta
    if marcador_upper in EXPECTED_RANGES:
        return EXPECTED_RANGES[marcador_upper]

    # Busca parcial
    for key, valor in EXPECTED_RANGES.items():
        if marcador_upper in key or key in marcador_upper:
            return valor

    return None


def _calcular_distancia_relativa(
    valor: Decimal, ref_min: Optional[Decimal], ref_max: Optional[Decimal]
) -> Optional[Decimal]:
    """
    Calcula o quão distante o valor está do range.

    Returns:
        Fator de distância (positivo = acima, negativo = abaixo)
        None se não for possível calcular
    """
    if ref_min is None or ref_max is None:
        return None

    if ref_min <= valor <= ref_max:
        return Decimal("0")  # Dentro do range

    if valor < ref_min:
        # Abaixo do mínimo
        if ref_min == 0:
            return None
        return (valor - ref_min) / ref_min

    # Acima do máximo
    if ref_max == 0:
        return None
    return (valor - ref_max) / ref_max


def sugerir_correcao_decimal(
    valor: Decimal,
    ref_min: Optional[Decimal],
    ref_max: Optional[Decimal],
    marcador: str,
) -> list[dict]:
    """
    Sugere candidatos de correção para decimal deslocado.

    Analisa o valor e gera sugestões de correção baseadas em
    multiplicação/divisão por potências de 10.

    Args:
        valor: Valor extraído pelo OCR
        ref_min: Valor mínimo de referência
        ref_max: Valor máximo de referência
        marcador: Nome do marcador

    Returns:
        Lista de candidatos de correção, cada um com:
        - "valor": Decimal corrigido
        - "fator": float (0.01, 0.1, 1, 10, 100)
        - "score": float (0-1, quão boa é a correção)
        - "razao": str explicando a correção
    """
    candidatos = []

    # Early exit: sem referência
    if ref_min is None and ref_max is None:
        # Tenta usar range esperado do marcador
        range_esperado = obter_range_esperado(marcador)
        if range_esperado is None:
            return []
        ref_min, ref_max, _ = range_esperado

    # Fatores de correção a tentar
    fatores = [
        (Decimal("100"), 100, "multiplicado por 100"),
        (Decimal("10"), 10, "multiplicado por 10"),
        (Decimal("1"), 1, "sem alteração"),
        (Decimal("0.1"), 0.1, "dividido por 10"),
        (Decimal("0.01"), 0.01, "dividido por 100"),
    ]

    for fator_decimal, fator_float, descricao in fatores:
        valor_ajustado = valor * fator_decimal

        # Verifica se está no range
        esta_no_range = False
        if ref_min is not None and ref_max is not None:
            esta_no_range = ref_min <= valor_ajustado <= ref_max

        if not esta_no_range:
            continue

        # Calcula score baseado na posição no range
        if ref_min is not None and ref_max is not None:
            range_total = ref_max - ref_min
            if range_total > 0:
                # Valor central = score 1.0, bordas = score 0.7
                centro = (ref_min + ref_max) / 2
                distancia_centro = abs(valor_ajustado - centro)
                score = max(
                    Decimal("0.7"), Decimal("1.0") - (distancia_centro / range_total)
                )
            else:
                score = Decimal("0.8")
        else:
            score = Decimal("0.5")

        # Penaliza correções mais extremas
        if fator_float == 100 or fator_float == 0.01:
            score = score * Decimal("0.7")
        elif fator_float == 10 or fator_float == 0.1:
            score = score * Decimal("0.9")

        candidatos.append(
            {
                "valor": valor_ajustado,
                "fator": fator_float,
                "score": float(score),
                "razao": f"Valor {valor} {descricao} = {valor_ajustado} (dentro do range {ref_min}-{ref_max})",
            }
        )

    # Ordena por score decrescente
    candidatos.sort(key=lambda x: x["score"], reverse=True)

    return candidatos


def escolher_melhor_correcao(candidatos: list[dict]) -> Optional[dict]:
    """
    Seleciona o melhor candidato de correção.

    Critérios:
    1. Score mais alto
    2. Preferência por correções menos extremas (fator mais próximo de 1)

    Args:
        candidatos: Lista de candidatos de sugerir_correcao_decimal

    Returns:
        Melhor candidato ou None se lista vazia
    """
    if not candidatos:
        return None

    # Já está ordenado por score, pega o primeiro
    melhor = candidatos[0]

    # Se há empate de score, prefere fator mais próximo de 1
    candidatos_com_mesmo_score = [
        c for c in candidatos if abs(c["score"] - melhor["score"]) < 0.05
    ]

    if len(candidatos_com_mesmo_score) > 1:
        # Ordena por proximidade do fator a 1
        candidatos_com_mesmo_score.sort(key=lambda x: abs(x["fator"] - 1))
        melhor = candidatos_com_mesmo_score[0]

    return melhor


def validar_coerencia_valor(
    valor: Decimal, marcador: str, unidade: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida se um valor parece coerente para o marcador.

    Esta função é útil para detectar problemas óbvios de OCR
    mesmo quando não há referência do laboratório.

    Args:
        valor: Valor numérico
        marcador: Nome do marcador
        unidade: Unidade de medida (opcional)

    Returns:
        Tupla (eh_coerente, mensagem)
    """
    range_esperado = obter_range_esperado(marcador)

    if range_esperado is None:
        return True, None  # Marcador desconhecido, não podemos validar

    min_esperado, max_esperado, unidade_esperada = range_esperado

    # Verifica se está muito fora do range
    if valor < min_esperado / 10:
        return False, (
            f"Valor {valor} muito baixo para {marcador}. "
            f"Esperado: {min_esperado} - {max_esperado} {unidade_esperada}"
        )

    if valor > max_esperado * 10:
        return False, (
            f"Valor {valor} muito alto para {marcador}. "
            f"Esperado: {min_esperado} - {max_esperado} {unidade_esperada}"
        )

    return True, None
