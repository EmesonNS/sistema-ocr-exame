"""
Camada determinística de parsing/normalização de biomarcadores.

Todas as funções são PURAS (sem side effects).
Seguem a filosofia: Early Exit, Parse Don't Validate, Atomic Predictability, Fail Fast, Intentional Naming.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import re
from typing import Optional


class TipoValor(str, Enum):
    """Classificação do tipo de valor extraído."""

    ABSOLUTO = "absoluto"
    PERCENTUAL = "percentual"
    TEXTUAL = "textual"


class NivelAlerta(str, Enum):
    """Nível de alerta baseado na comparação com referência."""

    BAIXO = "baixo"
    NORMAL = "normal"
    ALTO = "alto"
    INDEFINIDO = "indefinido"


class FonteValor(str, Enum):
    """Fonte do valor normalizado."""

    OCR = "ocr"
    CALCULADO = "calculado"
    CORRIGIDO = "corrigido"


# Padrões regex compilados (constantes para reuso)
_PATTERN_PERCENTUAL = re.compile(r"%|percentual|por cento", re.IGNORECASE)
_PATTERN_ABSOLUTO = re.compile(r"/mm[³3]|/ml|/l\b|mm[³3]\b|celulas", re.IGNORECASE)
_PATTERN_NUMERO = re.compile(r"[-+]?\d(?:[\d.,\s]*\d)?")
_PATTERN_NUMERO_REFERENCIA = r"[-+]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d+)?"
_PATTERN_REFERENCIA = re.compile(
    rf"(?P<min>{_PATTERN_NUMERO_REFERENCIA})\s*(?:a|até|-|–|—)\s*(?P<max>{_PATTERN_NUMERO_REFERENCIA})",
    re.IGNORECASE,
)
_PATTERN_TEXTO_POSITIVO = re.compile(
    r"^(positivo|presente|detectado|reagente|sim|yes|positive|detected|reactive)$",
    re.IGNORECASE,
)
_PATTERN_TEXTO_NEGATIVO = re.compile(
    r"^(negativo|ausente|não detectado|não reagente|nao detectado|nao reagente|não|nao|no|negative|absent|non.?reactive)$",
    re.IGNORECASE,
)

# Marcadores que são tipicamente percentuais
_MARCADORES_PERCENTUAIS = frozenset(
    [
        "segmentados",
        "bastonetes",
        "linfocitos",
        "linfócitos",
        "monocitos",
        "monócitos",
        "eosinofilos",
        "eosinófilos",
        "basofilos",
        "basófilos",
        "neutrofilos",
        "neutrófilos",
        "vcm",
        "hcm",
        "chcm",
        "rdw",
        "volume corpuscular",
    ]
)


def _normalizar_string(valor: Optional[str]) -> str:
    """Remove espaços extras e normaliza string."""
    if not valor:
        return ""
    return " ".join(valor.strip().split())


def _detectar_locale_por_separador(valor: Optional[str]) -> str:
    """
    Detecta locale baseado no padrão de separadores.

    Heurísticas:
    - "1.234,56" -> pt_BR (ponto = milhar, vírgula = decimal)
    - "1,234.56" -> en_US (vírgula = milhar, ponto = decimal)
    - "1234,56" ou "1234.56" -> ambíguo, usa locale_hint
    """
    if not valor:
        return "pt_BR"

    valor = _normalizar_string(valor)

    # Padrão pt_BR: ponto como milhar, vírgula como decimal
    if re.match(r"^\d{1,3}(\.\d{3})+,\d+$", valor):
        return "pt_BR"

    # Padrão en_US: vírgula como milhar, ponto como decimal
    if re.match(r"^\d{1,3}(,\d{3})+\.\d+$", valor):
        return "en_US"

    # Ponto simples com casas decimais é comum em laudos e respostas de IA.
    # Ex.: "13.8" e "0.86" devem preservar o ponto decimal, não removê-lo
    # como separador de milhar pt_BR.
    if "." in valor and "," not in valor:
        if re.match(r"^\d{1,3}(\.\d{3})+$", valor):
            return "pt_BR"
        return "en_US"

    # Vírgula simples sem ponto é decimal no padrão pt_BR.
    if "," in valor and "." not in valor:
        return "pt_BR"

    # Padrão com espaço como milhar (comum em alguns labs)
    if re.match(r"^\d{1,3}(\s\d{3})+[,.]\d+$", valor):
        return "pt_BR"  # Assume pt_BR para espaços

    return "pt_BR"  # Default


def extrair_tipo_valor(valor_raw: Optional[str], unidade: Optional[str]) -> TipoValor:
    """
    Detecta se valor é percentual, absoluto ou textual baseado em padrões.

    Prioridade de detecção:
    1. Unidade explícita (%, /mm³)
    2. Padrão no valor (49,0 %)
    3. Tipo textual (Negativo, Positivo)

    Args:
        valor_raw: Valor original extraído pelo OCR
        unidade: Unidade de medida extraída

    Returns:
        TipoValor classificado
    """
    if not valor_raw:
        return TipoValor.TEXTUAL

    valor_normalizado = _normalizar_string(valor_raw)
    unidade_normalizada = _normalizar_string(unidade) if unidade else ""

    # Early exit: unidade explícita percentual
    if _PATTERN_PERCENTUAL.search(unidade_normalizada) or _PATTERN_PERCENTUAL.search(
        valor_normalizado
    ):
        return TipoValor.PERCENTUAL

    # Early exit: unidade explícita absoluta
    if _PATTERN_ABSOLUTO.search(unidade_normalizada):
        return TipoValor.ABSOLUTO

    # Early exit: valor textual
    if _PATTERN_TEXTO_POSITIVO.match(valor_normalizado):
        return TipoValor.TEXTUAL

    if _PATTERN_TEXTO_NEGATIVO.match(valor_normalizado):
        return TipoValor.TEXTUAL

    # Verifica se parece ser um número
    if not _PATTERN_NUMERO.search(valor_normalizado):
        return TipoValor.TEXTUAL

    # Default: assume absoluto para números sem indicação
    return TipoValor.ABSOLUTO


def parse_valor_numerico(
    valor_raw: Optional[str], locale_hint: str = "pt_BR"
) -> Optional[Decimal]:
    """
    Converte string para Decimal, lidando com diferentes formatos de locale.

    Trata:
    - "1.234,56" (pt_BR)
    - "1,234.56" (en_US)
    - "12,3" vs "12.3"
    - "1 234,56" (espaço como separador de milhar)
    - "49,0 %" (com unidade no valor)

    Args:
        valor_raw: String do valor numérico
        locale_hint: Locale sugerido ("pt_BR" ou "en_US")

    Returns:
        Decimal do valor ou None se não for possível converter
    """
    if not valor_raw:
        return None

    valor = _normalizar_string(valor_raw)

    # Early exit: valor textual
    if _PATTERN_TEXTO_POSITIVO.match(valor) or _PATTERN_TEXTO_NEGATIVO.match(valor):
        return None

    # Extrai apenas a parte numérica do valor
    # Isso remove unidades como %, /mm³ que possam estar junto
    match = _PATTERN_NUMERO.search(valor)
    if not match:
        return None
    valor = match.group(0)

    # Detecta locale automaticamente
    locale = (
        _detectar_locale_por_separador(valor) if locale_hint == "pt_BR" else locale_hint
    )

    # Remove espaços (separador de milhar em alguns formatos)
    valor = valor.replace(" ", "")

    # Normaliza baseado no locale
    if locale == "pt_BR":
        # pt_BR: remove pontos (milhar), troca vírgula por ponto
        valor = valor.replace(".", "").replace(",", ".")
    else:
        # en_US: remove vírgulas (milhar)
        valor = valor.replace(",", "")

    # Tenta converter para Decimal
    try:
        return Decimal(valor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def parse_referencia(
    referencia_raw: Optional[str],
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Extrai valores mínimo e máximo de string de referência.

    Exemplos:
    - "1.440 a 9.000/mm³" -> (1440, 9000)
    - "0,0 a 5,0%" -> (0, 5)
    - "40,0 a 75,0 %" -> (40, 75)
    - "< 190 mg/dL" -> (None, 190)
    - "> 13 g/dL" -> (13, None)

    Args:
        referencia_raw: String de referência do laboratório

    Returns:
        Tupla (min, max) com valores Decimal ou None
    """
    if not referencia_raw:
        return None, None

    referencia = _normalizar_string(referencia_raw)

    # Early exit: padrão intervalo "min a max" ou "min - max"
    match = _PATTERN_REFERENCIA.search(referencia)
    if match:
        min_str = match.group("min")
        max_str = match.group("max")
        return parse_valor_numerico(min_str), parse_valor_numerico(max_str)

    # Padrão "< valor" (apenas máximo)
    match_menor = re.search(rf"[<≤]\s*({_PATTERN_NUMERO_REFERENCIA})", referencia)
    if match_menor:
        return None, parse_valor_numerico(match_menor.group(1))

    # Padrão "> valor" (apenas mínimo)
    match_maior = re.search(rf"[>≥]\s*({_PATTERN_NUMERO_REFERENCIA})", referencia)
    if match_maior:
        return parse_valor_numerico(match_maior.group(1)), None

    return None, None


def normalizar_unidade(unidade: Optional[str]) -> str:
    """
    Normaliza unidades de medida para formato padrão.

    Transformações:
    - "/mm³", "/mm3", "mm³", "mm3" -> "/mm³"
    - "%", " %", "%" -> "%"
    - "mg/dL", "mg/dl" -> "mg/dL"

    Args:
        unidade: Unidade original

    Returns:
        Unidade normalizada
    """
    if not unidade:
        return ""

    unidade = _normalizar_string(unidade)

    # Normaliza variações de mm³
    if re.match(r"^/?mm[³3]$", unidade, re.IGNORECASE):
        return "/mm³"

    # Normaliza porcentagem
    if unidade.strip() == "%":
        return "%"

    if unidade.isupper():
        return unidade

    # Normaliza variações de mL, L
    unidade = re.sub(r"\bml\b", "mL", unidade, flags=re.IGNORECASE)
    unidade = re.sub(r"\bdl\b", "dL", unidade, flags=re.IGNORECASE)
    unidade = re.sub(r"\bl\b", "L", unidade, flags=re.IGNORECASE)

    return unidade


def classificar_alerta(
    valor: Decimal,
    ref_min: Optional[Decimal],
    ref_max: Optional[Decimal],
    tipo_valor: TipoValor,
) -> NivelAlerta:
    """
    Classifica se valor está baixo/normal/alto baseado na referência.

    Args:
        valor: Valor numérico do biomarcador
        ref_min: Valor mínimo de referência (ou None)
        ref_max: Valor máximo de referência (ou None)
        tipo_valor: Tipo do valor (afeta lógica de classificação)

    Returns:
        NivelAlerta classificado
    """
    # Early exit: valor textual não tem alerta numérico
    if tipo_valor == TipoValor.TEXTUAL:
        return NivelAlerta.INDEFINIDO

    # Early exit: sem referência definida
    if ref_min is None and ref_max is None:
        return NivelAlerta.INDEFINIDO

    # Classifica baseado nos limites
    if ref_min is not None and valor < ref_min:
        return NivelAlerta.BAIXO

    if ref_max is not None and valor > ref_max:
        return NivelAlerta.ALTO

    return NivelAlerta.NORMAL


def detectar_decimal_deslocado(
    valor: Decimal,
    ref_min: Optional[Decimal],
    ref_max: Optional[Decimal],
    marcador: str,
) -> tuple[Decimal, bool, str, float]:
    """
    Detecta e corrige decimal deslocado usando heurísticas.

    Heurísticas aplicadas:
    - Se valor >> 10x acima do max e valor/10 está no range -> dividir por 10
    - Se valor << 10x abaixo do min e valor*10 está no range -> multiplicar por 10

    Args:
        valor: Valor numérico extraído
        ref_min: Valor mínimo de referência
        ref_max: Valor máximo de referência
        marcador: Nome do biomarcador (para contexto)

    Returns:
        Tupla (valor_corrigido, correcao_aplicada, regra, confianca)
    """
    # Early exit: sem referência para validar
    if ref_min is None and ref_max is None:
        return valor, False, "", 0.0

    # Early exit: valor já está no range
    if ref_min is not None and ref_max is not None:
        if ref_min <= valor <= ref_max:
            return valor, False, "", 0.0

    # Tenta correção por fator 10 (para cima)
    valor_x10 = valor * 10
    if ref_min is not None and ref_max is not None:
        if ref_min <= valor_x10 <= ref_max:
            regra = f"Valor {valor} muito baixo para referência {ref_min}-{ref_max}. Multiplicado por 10."
            return valor_x10, True, regra, 0.8

    # Tenta correção por fator 10 (para baixo)
    valor_div10 = valor / 10
    if ref_min is not None and ref_max is not None:
        if ref_min <= valor_div10 <= ref_max:
            regra = f"Valor {valor} muito alto para referência {ref_min}-{ref_max}. Dividido por 10."
            return valor_div10, True, regra, 0.8

    # Tenta correção por fator 100 (casos extremos)
    valor_x100 = valor * 100
    if ref_min is not None and ref_max is not None:
        if ref_min <= valor_x100 <= ref_max:
            regra = f"Valor {valor} extremamente baixo. Multiplicado por 100."
            return valor_x100, True, regra, 0.6

    valor_div100 = valor / 100
    if ref_min is not None and ref_max is not None:
        if ref_min <= valor_div100 <= ref_max:
            regra = f"Valor {valor} extremamente alto. Dividido por 100."
            return valor_div100, True, regra, 0.6

    # Sem correção aplicável
    return valor, False, "", 0.0


def converter_percentual_para_absoluto(
    valor_percentual: Decimal, valor_base: Decimal
) -> Decimal:
    """
    Converte valor percentual para absoluto.

    Args:
        valor_percentual: Valor em porcentagem (ex: 49.0 para 49%)
        valor_base: Valor base para cálculo (ex: total de leucócitos)

    Returns:
        Valor absoluto calculado
    """
    if valor_base <= 0:
        raise ValueError(f"Valor base deve ser positivo, recebido: {valor_base}")

    return (valor_percentual / 100) * valor_base


def normalizar_nome_marcador(nome: Optional[str]) -> str:
    """
    Normaliza nome do marcador para formato padrão.

    Args:
        nome: Nome original do marcador

    Returns:
        Nome normalizado (uppercase, sem espaços extras)
    """
    if not nome:
        return ""

    return _normalizar_string(nome).upper()


def _detectar_se_marcador_eh_percentual_por_nome(nome: Optional[str]) -> bool:
    """
    Detecta se um marcador é tipicamente percentual baseado no nome.

    Args:
        nome: Nome do marcador

    Returns:
        True se o marcador é tipicamente reportado como percentual
    """
    if not nome:
        return False

    nome_normalizado = normalizar_nome_marcador(nome)

    for marcador in _MARCADORES_PERCENTUAIS:
        if marcador.upper() in nome_normalizado:
            return True

    return False


def normalizar_resultado_biomarcador(
    nome_marcador: Optional[str],
    valor_raw: Optional[str],
    unidade_raw: Optional[str],
    referencia_raw: Optional[str],
    contexto: Optional[dict] = None,
) -> dict:
    """
    Normaliza um resultado de biomarcador de forma determinística.

    Esta é a função de entrada principal que orquestra todas as
    normalizações individuais.

    Args:
        nome_marcador: Nome do biomarcador extraído
        valor_raw: Valor original do OCR
        unidade_raw: Unidade original do OCR
        referencia_raw: Referência do laboratório
        contexto: Contexto adicional (ex: {"leucocitos_total": 5500})

    Returns:
        Dict com todos os campos normalizados:
        - nome_marcador_normalizado
        - valor_raw (original)
        - valor_numerico (Decimal)
        - valor_extraido (string formatada)
        - tipo_valor
        - unidade_medida_normalizada
        - referencia_min, referencia_max
        - status_alerta
        - needs_review
        - correcao_aplicada
        - confianca
        - fonte_valor
    """
    contexto = contexto or {}

    # Normaliza nome
    nome_normalizado = normalizar_nome_marcador(nome_marcador)

    # Detecta tipo do valor
    tipo_valor = extrair_tipo_valor(valor_raw, unidade_raw)

    # Normaliza unidade
    unidade_normalizada = normalizar_unidade(unidade_raw)

    # Parse referência
    ref_min, ref_max = parse_referencia(referencia_raw)

    # Inicializa resultado base
    resultado = {
        "nome_marcador_normalizado": nome_normalizado,
        "valor_raw": valor_raw,
        "valor_numerico": None,
        "valor_extraido": valor_raw,
        "tipo_valor": tipo_valor.value,
        "unidade_medida_normalizada": unidade_normalizada,
        "referencia_min": ref_min,
        "referencia_max": ref_max,
        "status_alerta": NivelAlerta.INDEFINIDO.value,
        "needs_review": False,
        "correcao_aplicada": None,
        "confianca": 1.0,
        "fonte_valor": FonteValor.OCR.value,
    }

    # Early exit: valor textual
    if tipo_valor == TipoValor.TEXTUAL:
        resultado["status_alerta"] = NivelAlerta.INDEFINIDO.value
        return resultado

    # Parse valor numérico
    valor_numerico = parse_valor_numerico(valor_raw)

    if valor_numerico is None:
        resultado["needs_review"] = True
        resultado["confianca"] = 0.0
        return resultado

    # Detecta decimal deslocado e aplica correção se necessário
    # IMPORTANTE: Não aplica correção de decimal para valores percentuais
    # pois a lógica de detecção assume referências absolutas
    if tipo_valor == TipoValor.ABSOLUTO:
        valor_corrigido, correcao_aplicada, regra, confianca = (
            detectar_decimal_deslocado(
                valor_numerico, ref_min, ref_max, nome_normalizado
            )
        )

        if correcao_aplicada:
            valor_numerico = valor_corrigido
            resultado["correcao_aplicada"] = regra
            resultado["confianca"] = confianca
            resultado["fonte_valor"] = FonteValor.CORRIGIDO.value
            resultado["needs_review"] = True

    # Verifica se precisa converter percentual para absoluto
    # (quando temos o valor base no contexto, como total de leucócitos)
    if tipo_valor == TipoValor.PERCENTUAL and "leucocitos_total" in contexto:
        try:
            base = Decimal(str(contexto["leucocitos_total"]))
            valor_absoluto = converter_percentual_para_absoluto(valor_numerico, base)

            # Atualiza resultado com valor convertido
            resultado["valor_numerico"] = valor_absoluto
            resultado["valor_extraido"] = f"{valor_absoluto:.1f}"
            resultado["unidade_medida_normalizada"] = "/mm³"
            resultado["fonte_valor"] = FonteValor.CALCULADO.value
            resultado["correcao_aplicada"] = (
                f"Convertido de {valor_numerico}% para absoluto "
                f"(base: {base} leucócitos)"
            )
            resultado["confianca"] = 0.9
        except (ValueError, InvalidOperation):
            resultado["valor_numerico"] = valor_numerico
            resultado["valor_extraido"] = str(valor_numerico)
    else:
        resultado["valor_numerico"] = valor_numerico
        resultado["valor_extraido"] = str(valor_numerico)

    # Classifica alerta
    resultado["status_alerta"] = classificar_alerta(
        resultado["valor_numerico"], ref_min, ref_max, tipo_valor
    ).value

    # Marca para revisão se confiança baixa
    if resultado["confianca"] < 0.8:
        resultado["needs_review"] = True

    return resultado
