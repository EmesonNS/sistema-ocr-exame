"""
Testes unitários para a camada de normalização de biomarcadores.

Cobertura:
- Percentual vs absoluto (caso SEGMENTADOS)
- Parsing de decimais pt_BR vs en_US
- Correção de decimal deslocado
- Classificação de alerta
"""

import pytest
from decimal import Decimal

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


class TestExtrairTipoValor:
    """Testes para detecção de tipo de valor."""

    def test_percentual_com_simbolo_porcento(self):
        """Detecta percentual com símbolo %."""
        assert extrair_tipo_valor("49,0 %", "") == TipoValor.PERCENTUAL
        assert extrair_tipo_valor("49%", "") == TipoValor.PERCENTUAL
        assert extrair_tipo_valor("49 %", "") == TipoValor.PERCENTUAL

    def test_percentual_na_unidade(self):
        """Detecta percentual quando % está na unidade."""
        assert extrair_tipo_valor("49,0", "%") == TipoValor.PERCENTUAL
        assert extrair_tipo_valor("49", " % ") == TipoValor.PERCENTUAL

    def test_absoluto_com_unidade_mm3(self):
        """Detecta absoluto com unidade /mm³."""
        assert extrair_tipo_valor("5500", "/mm³") == TipoValor.ABSOLUTO
        assert extrair_tipo_valor("5500", "/mm3") == TipoValor.ABSOLUTO
        assert extrair_tipo_valor("5500", "mm³") == TipoValor.ABSOLUTO

    def test_textual_negativo(self):
        """Detecta valor textual 'Negativo'."""
        assert extrair_tipo_valor("Negativo", "") == TipoValor.TEXTUAL
        assert extrair_tipo_valor("negativo", "") == TipoValor.TEXTUAL
        assert extrair_tipo_valor("NÃO REAGENTE", "") == TipoValor.TEXTUAL
        assert extrair_tipo_valor("nao detectado", "") == TipoValor.TEXTUAL

    def test_textual_positivo(self):
        """Detecta valor textual 'Positivo'."""
        assert extrair_tipo_valor("Positivo", "") == TipoValor.TEXTUAL
        assert extrair_tipo_valor("POSITIVO", "") == TipoValor.TEXTUAL
        assert extrair_tipo_valor("Reagente", "") == TipoValor.TEXTUAL

    def test_numero_sem_unidade_eh_absoluto(self):
        """Número sem indicação assume absoluto."""
        assert extrair_tipo_valor("150", "") == TipoValor.ABSOLUTO
        assert extrair_tipo_valor("1.234", "") == TipoValor.ABSOLUTO


class TestParseValorNumerico:
    """Testes para parsing de valores numéricos."""

    def test_formato_pt_br_com_virgula_decimal(self):
        """Parse de formato brasileiro: 1.234,56."""
        assert parse_valor_numerico("1.234,56") == Decimal("1234.56")
        assert parse_valor_numerico("12,3") == Decimal("12.3")
        assert parse_valor_numerico("0,5") == Decimal("0.5")

    def test_formato_en_us_com_ponto_decimal(self):
        """Parse de formato americano: 1,234.56."""
        assert parse_valor_numerico("1,234.56", "en_US") == Decimal("1234.56")
        assert parse_valor_numerico("12.3", "en_US") == Decimal("12.3")

    def test_espaco_como_separador_milhar(self):
        """Parse com espaço como separador de milhar."""
        assert parse_valor_numerico("1 234,56") == Decimal("1234.56")
        assert parse_valor_numerico("10 000") == Decimal("10000")

    def test_numero_simples(self):
        """Parse de número simples."""
        assert parse_valor_numerico("5500") == Decimal("5500")
        assert parse_valor_numerico("42") == Decimal("42")

    def test_valor_negativo(self):
        """Parse de valor negativo."""
        assert parse_valor_numerico("-5,5") == Decimal("-5.5")
        assert parse_valor_numerico("-100") == Decimal("-100")

    def test_valor_com_unidade_junta(self):
        """Parse de valor com unidade junto (ex: 49,0 %)."""
        assert parse_valor_numerico("49,0 %") == Decimal("49.0")
        assert parse_valor_numerico("100mg") == Decimal("100")

    def test_valor_textual_retorna_none(self):
        """Valor textual retorna None."""
        assert parse_valor_numerico("Negativo") is None
        assert parse_valor_numerico("Positivo") is None

    def test_valor_vazio_retorna_none(self):
        """Valor vazio retorna None."""
        assert parse_valor_numerico("") is None
        assert parse_valor_numerico(None) is None

    def test_valor_invalido_retorna_none(self):
        """Valor inválido retorna None."""
        assert parse_valor_numerico("abc") is None
        assert parse_valor_numerico("--") is None


class TestParseReferencia:
    """Testes para parsing de referência."""

    def test_referencia_intervalo_padrao(self):
        """Parse de referência no formato 'min a max'."""
        ref_min, ref_max = parse_referencia("1.440 a 9.000/mm³")
        assert ref_min == Decimal("1440")
        assert ref_max == Decimal("9000")

    def test_referencia_com_virgula_decimal(self):
        """Parse de referência com vírgula decimal."""
        ref_min, ref_max = parse_referencia("0,0 a 5,0%")
        assert ref_min == Decimal("0")
        assert ref_max == Decimal("5")

    def test_referencia_com_espaco_e_porcentagem(self):
        """Parse de referência com %."""
        ref_min, ref_max = parse_referencia("40,0 a 75,0 %")
        assert ref_min == Decimal("40")
        assert ref_max == Decimal("75")

    def test_referencia_menor_que(self):
        """Parse de referência '< valor'."""
        ref_min, ref_max = parse_referencia("< 190 mg/dL")
        assert ref_min is None
        assert ref_max == Decimal("190")

    def test_referencia_maior_que(self):
        """Parse de referência '> valor'."""
        ref_min, ref_max = parse_referencia("> 13 g/dL")
        assert ref_min == Decimal("13")
        assert ref_max is None

    def test_referencia_com_travessao(self):
        """Parse de referência com travessão."""
        ref_min, ref_max = parse_referencia("10 – 50")
        assert ref_min == Decimal("10")
        assert ref_max == Decimal("50")

    def test_referencia_vazia(self):
        """Referência vazia retorna (None, None)."""
        assert parse_referencia("") == (None, None)
        assert parse_referencia(None) == (None, None)


class TestNormalizarUnidade:
    """Testes para normalização de unidades."""

    def test_normaliza_mm3(self):
        """Normaliza variações de mm³."""
        assert normalizar_unidade("/mm³") == "/mm³"
        assert normalizar_unidade("/mm3") == "/mm³"
        assert normalizar_unidade("mm³") == "/mm³"
        assert normalizar_unidade("mm3") == "/mm³"

    def test_normaliza_porcentagem(self):
        """Normaliza porcentagem."""
        assert normalizar_unidade("%") == "%"
        assert normalizar_unidade(" % ") == "%"

    def test_normaliza_mg_dl(self):
        """Normaliza mg/dL."""
        assert normalizar_unidade("mg/dl") == "mg/dL"
        assert normalizar_unidade("MG/DL") == "MG/DL"

    def test_unidade_vazia(self):
        """Unidade vazia retorna string vazia."""
        assert normalizar_unidade("") == ""
        assert normalizar_unidade(None) == ""


class TestClassificarAlerta:
    """Testes para classificação de alerta."""

    def test_valor_normal(self):
        """Valor dentro do range é normal."""
        assert (
            classificar_alerta(
                Decimal("50"), Decimal("10"), Decimal("100"), TipoValor.ABSOLUTO
            )
            == NivelAlerta.NORMAL
        )

    def test_valor_baixo(self):
        """Valor abaixo do mínimo é baixo."""
        assert (
            classificar_alerta(
                Decimal("5"), Decimal("10"), Decimal("100"), TipoValor.ABSOLUTO
            )
            == NivelAlerta.BAIXO
        )

    def test_valor_alto(self):
        """Valor acima do máximo é alto."""
        assert (
            classificar_alerta(
                Decimal("150"), Decimal("10"), Decimal("100"), TipoValor.ABSOLUTO
            )
            == NivelAlerta.ALTO
        )

    def test_sem_referencia(self):
        """Sem referência retorna indefinido."""
        assert (
            classificar_alerta(Decimal("50"), None, None, TipoValor.ABSOLUTO)
            == NivelAlerta.INDEFINIDO
        )

    def test_textual_eh_indefinido(self):
        """Valor textual sempre é indefinido."""
        assert (
            classificar_alerta(Decimal("0"), None, None, TipoValor.TEXTUAL)
            == NivelAlerta.INDEFINIDO
        )

    def test_valor_no_limite_minimo(self):
        """Valor no limite mínimo é normal."""
        assert (
            classificar_alerta(
                Decimal("10"), Decimal("10"), Decimal("100"), TipoValor.ABSOLUTO
            )
            == NivelAlerta.NORMAL
        )

    def test_valor_no_limite_maximo(self):
        """Valor no limite máximo é normal."""
        assert (
            classificar_alerta(
                Decimal("100"), Decimal("10"), Decimal("100"), TipoValor.ABSOLUTO
            )
            == NivelAlerta.NORMAL
        )


class TestDetectarDecimalDeslocado:
    """Testes para detecção de decimal deslocado."""

    def test_valor_ja_no_range(self):
        """Valor já no range não é corrigido."""
        valor, corrigido, regra, confianca = detectar_decimal_deslocado(
            Decimal("50"), Decimal("10"), Decimal("100"), "TESTE"
        )
        assert corrigido is False
        assert valor == Decimal("50")

    def test_valor_100x_acima_divide(self):
        """Valor 100x acima do max é dividido por 100."""
        valor, corrigido, regra, confianca = detectar_decimal_deslocado(
            Decimal("12345"), Decimal("100"), Decimal("1000"), "TESTE"
        )
        assert corrigido is True
        assert valor == Decimal("123.45")

    def test_valor_10x_abaixo_multiplica(self):
        """Valor 10x abaixo do min é multiplicado por 10."""
        valor, corrigido, regra, confianca = detectar_decimal_deslocado(
            Decimal("5"), Decimal("10"), Decimal("100"), "TESTE"
        )
        assert corrigido is True
        assert valor == Decimal("50")

    def test_sem_referencia_sem_correcao(self):
        """Sem referência não há correção."""
        valor, corrigido, regra, confianca = detectar_decimal_deslocado(
            Decimal("5000"), None, None, "TESTE"
        )
        assert corrigido is False


class TestConverterPercentualParaAbsoluto:
    """Testes para conversão percentual -> absoluto."""

    def test_conversao_simples(self):
        """Conversão básica de percentual."""
        resultado = converter_percentual_para_absoluto(Decimal("50"), Decimal("10000"))
        assert resultado == Decimal("5000")

    def test_conversao_segmentados(self):
        """Caso real: SEGMENTADOS 49% de 5500 leucócitos."""
        resultado = converter_percentual_para_absoluto(Decimal("49.0"), Decimal("5500"))
        assert resultado == Decimal("2695.0")

    def test_valor_zero_porcento(self):
        """0% de qualquer base = 0."""
        resultado = converter_percentual_para_absoluto(Decimal("0"), Decimal("10000"))
        assert resultado == Decimal("0")

    def test_valor_cem_porcento(self):
        """100% da base = base."""
        resultado = converter_percentual_para_absoluto(Decimal("100"), Decimal("5500"))
        assert resultado == Decimal("5500")

    def test_base_zero_erro(self):
        """Base zero lança erro."""
        with pytest.raises(ValueError):
            converter_percentual_para_absoluto(Decimal("50"), Decimal("0"))

    def test_base_negativa_erro(self):
        """Base negativa lança erro."""
        with pytest.raises(ValueError):
            converter_percentual_para_absoluto(Decimal("50"), Decimal("-100"))


class TestNormalizarResultadoBiomarcador:
    """Testes para normalização completa de biomarcador."""

    def test_caso_segmentados_percentual(self):
        """Caso real: SEGMENTADOS 49,0 % deve ser detectado como percentual."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="SEGMENTADOS",
            valor_raw="49,0 %",
            unidade_raw="%",
            referencia_raw="40,0 a 75,0 %",
            contexto=None,
        )

        assert resultado["tipo_valor"] == "percentual"
        assert resultado["valor_numerico"] == Decimal("49.0")
        assert resultado["status_alerta"] == "normal"
        assert resultado["fonte_valor"] == "ocr"

    def test_caso_segmentados_com_conversao(self):
        """SEGMENTADOS convertido para absoluto com contexto de leucócitos."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="SEGMENTADOS",
            valor_raw="49,0 %",
            unidade_raw="%",
            referencia_raw="1.440 a 9.000/mm³",
            contexto={"leucocitos_total": 5500},
        )

        assert resultado["tipo_valor"] == "percentual"
        # O valor foi convertido para absoluto
        assert resultado["valor_numerico"] == Decimal("2695.0")
        assert resultado["fonte_valor"] == "calculado"
        assert "Convertido de 49" in resultado["correcao_aplicada"]

    def test_valor_textual_negativo(self):
        """Valor textual é preservado."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="EXAME URINA",
            valor_raw="Negativo",
            unidade_raw="",
            referencia_raw="",
            contexto=None,
        )

        assert resultado["tipo_valor"] == "textual"
        assert resultado["valor_numerico"] is None
        assert resultado["status_alerta"] == "indefinido"

    def test_valor_alto(self):
        """Valor acima da referência."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="GLICOSE",
            valor_raw="250",
            unidade_raw="mg/dL",
            referencia_raw="70 a 99 mg/dL",
            contexto=None,
        )

        assert resultado["status_alerta"] == "alto"
        assert resultado["valor_numerico"] == Decimal("250")

    def test_valor_baixo(self):
        """Valor abaixo da referência."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="HEMOGLOBINA",
            valor_raw="10.5",
            unidade_raw="g/dL",
            referencia_raw="12.0 a 16.0 g/dL",
            contexto=None,
        )

        assert resultado["status_alerta"] == "baixo"

    def test_nome_marcador_normalizado(self):
        """Nome do marcador é normalizado para uppercase."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="  colesterol  total  ",
            valor_raw="195",
            unidade_raw="mg/dL",
            referencia_raw="",
            contexto=None,
        )

        assert resultado["nome_marcador_normalizado"] == "COLESTEROL TOTAL"


class TestDecimalCorrection:
    """Testes para módulo de correção de decimais."""

    def test_obter_range_esperado_existente(self):
        """Obtém range de marcador conhecido."""
        range_result = obter_range_esperado("HEMOGLOBINA")
        assert range_result is not None
        assert range_result[0] == Decimal("7.0")
        assert range_result[1] == Decimal("20.0")

    def test_obter_range_esperado_inexistente(self):
        """Marcador desconhecido retorna None."""
        assert obter_range_esperado("MARCADOR_DESCONHECIDO") is None

    def test_obter_range_case_insensitive(self):
        """Busca é case insensitive."""
        range1 = obter_range_esperado("hemoglobina")
        range2 = obter_range_esperado("HEMOGLOBINA")
        assert range1 == range2

    def test_sugerir_correcao_no_range(self):
        """Valor no range não gera sugestões de correção."""
        candidatos = sugerir_correcao_decimal(
            Decimal("15"), Decimal("12"), Decimal("18"), "HEMOGLOBINA"
        )
        # Sem correção necessária
        assert len(candidatos) == 0 or candidatos[0]["fator"] == 1

    def test_validar_coerencia_valor_ok(self):
        """Valor coerente não gera alerta."""
        eh_coerente, msg = validar_coerencia_valor(Decimal("15"), "HEMOGLOBINA")
        assert eh_coerente is True
        assert msg is None

    def test_validar_coerencia_valor_muito_alto(self):
        """Valor muito alto gera alerta."""
        eh_coerente, msg = validar_coerencia_valor(Decimal("500"), "HEMOGLOBINA")
        assert eh_coerente is False
        assert "muito alto" in msg.lower()


class TestCasosReaisOCR:
    """Testes com casos reais de extração OCR."""

    def test_leucocitos_formato_br(self):
        """Caso real: LEUCÓCITOS com formato brasileiro."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="LEUCÓCITOS",
            valor_raw="5.500",
            unidade_raw="/mm³",
            referencia_raw="3.600 a 12.000/mm³",
            contexto=None,
        )

        assert resultado["valor_numerico"] == Decimal("5500")
        assert resultado["tipo_valor"] == "absoluto"
        assert resultado["status_alerta"] == "normal"

    def test_plaquetas_valor_grande(self):
        """Caso real: PLAQUETAS com valor grande."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="PLAQUETAS",
            valor_raw="250.000",
            unidade_raw="/mm³",
            referencia_raw="150.000 a 450.000/mm³",
            contexto=None,
        )

        assert resultado["valor_numerico"] == Decimal("250000")
        assert resultado["status_alerta"] == "normal"

    def test_hemoglobina_formato_lab(self):
        """Caso real: HEMOGLOBINA com formato de laboratório."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="HEMOGLOBINA",
            valor_raw="13,5",
            unidade_raw="g/dL",
            referencia_raw="12,0 a 16,0 g/dL",
            contexto=None,
        )

        assert resultado["valor_numerico"] == Decimal("13.5")
        assert resultado["status_alerta"] == "normal"


class TestEdgeCases:
    """Testes para casos de borda."""

    def test_valor_raw_none(self):
        """Valor None é tratado como textual."""
        resultado = normalizar_resultado_biomarcador(
            nome_marcador="TESTE",
            valor_raw=None,
            unidade_raw="",
            referencia_raw="",
            contexto=None,
        )
        assert resultado["tipo_valor"] == "textual"

    def test_referencia_com_espacos_extras(self):
        """Referência com espaços extras é normalizada."""
        ref_min, ref_max = parse_referencia("  10  a   50  ")
        assert ref_min == Decimal("10")
        assert ref_max == Decimal("50")

    def test_valor_com_espacos_extras(self):
        """Valor com espaços extras é normalizado."""
        assert parse_valor_numerico("  123,45  ") == Decimal("123.45")
