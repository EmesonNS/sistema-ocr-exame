"""
AI Service para extração de biomarcadores de exames laboratoriais.

Integra provedores de IA (Google Gemini, OpenRouter) com a camada
determinística de normalização de biomarcadores.
"""

from google import genai
from openai import OpenAI
from pdf2image import convert_from_path
from decimal import Decimal
from typing import Optional
from app.core.config import settings
from app.services.biomarker_normalization import normalizar_resultado_biomarcador
import base64
import io
import json
import logging

logger = logging.getLogger(__name__)

PROMPT_EXAME = """
Analise este exame laboratorial e extraia:

Para cada biomarcador encontrado:
- nome: nome do marcador (ex: "HEMOGLOBINA", "LEUCÓCITOS", "SEGMENTADOS")
- valor_raw: valor EXATAMENTE como aparece no documento (ex: "49,0", "5500", "< 10")
- unidade: unidade como aparece (ex: "%", "/mm³", "g/dL")
- tipo: "percentual" se tiver %, "absoluto" se for número puro, "textual" se for texto

IMPORTANTE:
- NÃO CONVERTA valores percentuais para absolutos
- NÃO CALCULE nada - apenas extraia o que está escrito
- Se o valor tem "%" junto, extraia como percentual
- Preserve casas decimais exatamente como aparecem

Metadados do exame:
- data_coleta: data da coleta se disponível (formato DD/MM/AAAA ou null)
- laboratorio: nome do laboratório se disponível (ou null)

Retorne em JSON:
{
  "biomarcadores": [
    {
      "nome": "string",
      "valor_raw": "string",
      "unidade": "string", 
      "tipo": "percentual|absoluto|textual"
    }
  ],
  "data_coleta": "string|null",
  "laboratorio": "string|null"
}
"""


class AIService:
    """Serviço de extração de biomarcadores usando IA com fallback."""

    def __init__(self):
        self.google_client = None
        try:
            self.google_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception:
            self.google_client = None
        self.google_model = "gemini-2.0-flash"
        self.openrouter_model = "google/gemini-2.5-flash"
        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

    def extrair_biomarcadores(
        self, file_path: str, leucocitos_total: Optional[Decimal] = None
    ) -> tuple[list[dict], Optional[str], Optional[str]]:
        """
        Extrai biomarcadores do exame e normaliza resultados.

        Args:
            file_path: Caminho do arquivo PDF/imagem
            leucocitos_total: Valor total de leucócitos (para conversão percentual->absoluto)

        Returns:
            Tupla (resultados_normalizados, data_coleta, laboratorio)
        """
        if self.google_client:
            dados = self._extrair_via_google(file_path)
            if dados and dados.get("biomarcadores"):
                return self._processar_biomarcadores(dados, leucocitos_total)

        # Fallback para OpenRouter
        if self.openrouter_client:
            logger.warning(
                "Google Gemini falhou ou retornou vazio, tentando OpenRouter"
            )
            dados = self._extrair_via_openrouter(file_path)
            if dados and dados.get("biomarcadores"):
                return self._processar_biomarcadores(dados, leucocitos_total)

        logger.error(
            "Ambos os provedores falharam na extração - retornando lista vazia"
        )
        return [], None, None

    def _processar_biomarcadores(
        self, dados: dict, leucocitos_total: Optional[Decimal] = None
    ) -> tuple[list[dict], Optional[str], Optional[str]]:
        """
        Processa dados extraídos usando a camada de normalização.

        Args:
            dados: Dict com biomarcadores, data_coleta, laboratorio
            leucocitos_total: Valor total para conversões

        Returns:
            Tupla (resultados_normalizados, data_coleta, laboratorio)
        """
        data_coleta = dados.get("data_coleta")
        laboratorio = dados.get("laboratorio")

        resultados = []
        for item in dados.get("biomarcadores", []):
            # Monta contexto para normalização
            contexto = {}
            if leucocitos_total and "LEUCÓCITO" in item.get("nome", "").upper():
                contexto["leucocitos_total"] = leucocitos_total

            # Normaliza usando camada determinística
            normalizado = normalizar_resultado_biomarcador(
                nome_marcador=item.get("nome"),
                valor_raw=item.get("valor_raw"),
                unidade_raw=item.get("unidade"),
                referencia_raw=item.get("referencia", ""),
                contexto=contexto,
            )
            resultados.append(normalizado)

        return resultados, data_coleta, laboratorio

    def extrair_dados_exame(self, file_path: str) -> dict:
        """
        Método legado para compatibilidade.

        Args:
            file_path: Caminho do arquivo

        Returns:
            Dict com 'resultados' (lista de biomarcadores normalizados)
        """
        resultados, _, _ = self.extrair_biomarcadores(file_path)
        return {"resultados": resultados}

    def _extrair_via_google(self, file_path: str) -> dict | None:
        # Early exit: cliente não configurado
        if not self.google_client:
            return None

        try:
            uploaded_file = self.google_client.files.upload(file=file_path)

            response = self.google_client.models.generate_content(
                model=self.google_model,
                contents=[uploaded_file, PROMPT_EXAME],
            )

            text = response.text
            if not text:
                return None

            logger.info("Resposta recebida do Google Gemini")
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Erro no Google Gemini: {e}")
            return None

    def _extrair_via_openrouter(self, file_path: str) -> dict | None:
        # Early exit: cliente não configurado
        if not self.openrouter_client:
            return None

        try:
            # Converte PDF em imagens (uma por página)
            images = convert_from_path(file_path, dpi=200)
            logger.info(f"PDF convertido em {len(images)} página(s)")

            # Monta content parts: todas as páginas como imagens
            content_parts = []
            for i, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                        },
                    }
                )

            content_parts.append(
                {
                    "type": "text",
                    "text": PROMPT_EXAME,
                }
            )

            response = self.openrouter_client.chat.completions.create(
                model=self.openrouter_model,
                messages=[
                    {
                        "role": "user",
                        "content": content_parts,
                    }
                ],
            )

            text = response.choices[0].message.content
            if not text:
                return None
            logger.info("Resposta recebida do OpenRouter (fallback)")
            return self._parse_response(text)

        except Exception as e:
            error_str = str(e)
            # Verifica se é erro de rate limit (429) ou crédito insuficiente
            if (
                "429" in error_str
                or "rate" in error_str.lower()
                or "insufficient" in error_str.lower()
            ):
                logger.error(
                    f"OpenRouter: Erro 429/Rate Limit/Crédito insuficiente: {e}"
                )
            else:
                logger.error(f"Erro no OpenRouter (fallback): {e}")
            return None

    def _parse_response(self, text: str) -> dict | None:
        """
        Parse da resposta da IA para JSON.

        Nota: A classificação de alerta agora é feita pela camada
        determinística de normalização, não mais aqui.
        """
        try:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(cleaned)
            return dados
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Erro ao parsear resposta da IA: {e}")
            return None
