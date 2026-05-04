"""
AI Service para extração de biomarcadores de exames laboratoriais.

Integra provedores de IA (Google Gemini, OpenRouter) com a camada
determinística de normalização de biomarcadores.
"""

from google import genai
from openai import OpenAI, AsyncOpenAI
from pdf2image import convert_from_path
from decimal import Decimal
from typing import Optional
from app.core.config import settings
from app.core.cache import get_redis_client
from app.services.biomarker_normalization import normalizar_resultado_biomarcador
from app.services.guardrails_service import GuardrailsService
import base64
import io
import json
import logging
import hashlib
import asyncio

logger = logging.getLogger(__name__)

PROMPT_EXAME = """
Analise este exame laboratorial e extraia os biomarcadores com alta precisão espacial.

Para cada biomarcador encontrado:
- nome: nome do marcador (ex: "HEMOGLOBINA", "LEUCÓCITOS", "SEGMENTADOS")
- valor_raw: valor EXATAMENTE como aparece no documento (ex: "49,0", "5500", "< 10")
- unidade: unidade como aparece (ex: "%", "/mm³", "g/dL")
- tipo: "percentual" se tiver %, "absoluto" se for número puro, "textual" se for texto
- page: número da página (começando em 1) onde o biomarcador foi encontrado
- bounding_box: coordenadas [ymin, xmin, ymax, xmax] normalizadas de 0 a 1000 que englobam o NOME e o VALOR do biomarcador na página.

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
      "tipo": "percentual|absoluto|textual",
      "page": number,
      "bounding_box": [ymin, xmin, ymax, xmax]
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
        self.async_openrouter_client = None
        self.guardrails = GuardrailsService()

        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
            self.async_openrouter_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

    async def extrair_biomarcadores(
        self, file_path: str, leucocitos_total: Optional[Decimal] = None
    ) -> tuple[list[dict], Optional[str], Optional[str]]:
        """
        Extrai biomarcadores do exame e normaliza resultados de forma assíncrona.

        Args:
            file_path: Caminho do arquivo PDF/imagem
            leucocitos_total: Valor total de leucócitos (para conversão percentual->absoluto)

        Returns:
            Tupla (resultados_normalizados, data_coleta, laboratorio)
        """
        if self.google_client:
            dados = await self._extrair_via_google_async(file_path)
            if dados and dados.get("biomarcadores"):
                resultados, dt, lab = self._processar_biomarcadores(dados, leucocitos_total)
                # Aplicar Guardrails Fisiológicos
                resultados = self.guardrails.sanitize_results(resultados)
                return resultados, dt, lab

        # Fallback para OpenRouter
        if self.async_openrouter_client:
            logger.warning(
                "Google Gemini falhou ou retornou vazio, tentando OpenRouter (Async)"
            )
            dados = await self._extrair_via_openrouter_async(file_path)
            if dados and dados.get("biomarcadores"):
                resultados, dt, lab = self._processar_biomarcadores(dados, leucocitos_total)
                # Aplicar Guardrails Fisiológicos
                resultados = self.guardrails.sanitize_results(resultados)
                return resultados, dt, lab

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
            
            # Adiciona metadados de rastreabilidade visual (Fase 7)
            normalizado["page_number"] = item.get("page")
            normalizado["bounding_box"] = item.get("bounding_box")
            
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
        # Note: This remains synchronous for backward compatibility if needed, 
        # but internal calls in this project should use the async version.
        import asyncio
        resultados, _, _ = asyncio.run(self.extrair_biomarcadores(file_path))
        return {"resultados": resultados}

    async def _extrair_via_google_async(self, file_path: str) -> dict | None:
        # Early exit: cliente não configurado
        if not self.google_client:
            return None

        try:
            # Upload de arquivo (atualmente síncrono na SDK)
            uploaded_file = self.google_client.files.upload(file=file_path)

            response = await self.google_client.aio.models.generate_content(
                model=self.google_model,
                contents=[uploaded_file, PROMPT_EXAME],
            )

            text = response.text
            if not text:
                return None

            logger.info("Resposta recebida do Google Gemini (Async)")
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Erro no Google Gemini (Async): {e}")
            return None

    async def _extrair_via_openrouter_async(self, file_path: str) -> dict | None:
        # Early exit: cliente não configurado
        if not self.async_openrouter_client:
            return None

        try:
            # Verifica cache no Redis
            redis_client = get_redis_client()
            
            # Leitura de arquivo é bloqueante, rodar em thread
            loop = asyncio.get_event_loop()
            def read_file_sync():
                with open(file_path, "rb") as f:
                    return f.read()
            
            file_bytes = await loop.run_in_executor(None, read_file_sync)
            file_hash = hashlib.md5(file_bytes).hexdigest()
            cache_key = f"pdf_images:{file_hash}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Imagens do PDF ({file_hash}) carregadas do cache")
                content_parts = json.loads(cached_data)
            else:
                # Converte PDF em imagens (CPU bound e bloqueante)
                def convert_sync():
                    return convert_from_path(
                        file_path,
                        dpi=200,
                        first_page=1,
                        last_page=settings.MAX_PDF_PAGES_FALLBACK,
                    )
                
                images = await loop.run_in_executor(None, convert_sync)
                logger.info(
                    f"PDF convertido em {len(images)} página(s) "
                    f"(limite: {settings.MAX_PDF_PAGES_FALLBACK})"
                )

                # Monta content parts (Conversão para Base64 também pode ser pesada)
                def encode_images_sync():
                    parts = []
                    for img in images:
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                        })
                    return parts

                content_parts = await loop.run_in_executor(None, encode_images_sync)
                
                # Salva no cache por 24h (86400 segundos)
                await redis_client.set(cache_key, json.dumps(content_parts), ex=86400)

            # Adiciona o texto do prompt por último
            # Copiamos a lista para não alterar o cache armazenado
            final_content_parts = list(content_parts)
            final_content_parts.append(
                {
                    "type": "text",
                    "text": PROMPT_EXAME,
                }
            )

            response = await self.async_openrouter_client.chat.completions.create(
                model=self.openrouter_model,
                messages=[
                    {
                        "role": "user",
                        "content": final_content_parts,
                    }
                ],
            )

            text = response.choices[0].message.content
            if not text:
                return None
            logger.info("Resposta recebida do OpenRouter (fallback async)")
            return self._parse_response(text)

        except Exception as e:
            error_str = str(e)
            if (
                "429" in error_str
                or "rate" in error_str.lower()
                or "insufficient" in error_str.lower()
            ):
                logger.error(
                    f"OpenRouter Async: Erro 429/Rate Limit/Crédito insuficiente: {e}"
                )
            else:
                logger.error(f"Erro no OpenRouter (fallback async): {e}")
            return None

    async def focar_extracao(
        self, file_path: str, page_number: int, bounding_box: list[int], nome_marcador: str
    ) -> dict | None:
        """
        Realiza uma extração focada em uma região específica (zoom) para confirmar um valor suspeito.
        """
        logger.info(f"Iniciando extração focada para {nome_marcador} na página {page_number}")

        try:
            # 1. Converter página específica do PDF
            loop = asyncio.get_event_loop()
            def get_page_image():
                return convert_from_path(
                    file_path,
                    dpi=300, # Maior DPI para zoom
                    first_page=page_number,
                    last_page=page_number,
                )[0]
            
            image = await loop.run_in_executor(None, get_page_image)
            width, height = image.size

            # 2. Calcular coordenadas de recorte com margem (padding)
            # bounding_box: [ymin, xmin, ymax, xmax] em escala 0-1000
            ymin, xmin, ymax, xmax = bounding_box
            
            # Adicionar 10% de margem
            pad_h = (ymax - ymin) * 0.1
            pad_w = (xmax - xmin) * 0.1
            
            left = max(0, (xmin - pad_w) * width / 1000)
            top = max(0, (ymin - pad_h) * height / 1000)
            right = min(width, (xmax + pad_w) * width / 1000)
            bottom = min(height, (ymax + pad_h) * height / 1000)

            # 3. Recortar imagem
            cropped_image = image.crop((left, top, right, bottom))
            
            # 4. Enviar para IA com prompt especializado
            buf = io.BytesIO()
            cropped_image.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            prompt = f"""
            Analise este recorte ampliado de um exame laboratorial.
            Foco no biomarcador: {nome_marcador}
            
            Extraia EXATAMENTE o valor numérico que aparece nesta imagem.
            Ignore qualquer outro texto.
            
            Retorne APENAS um JSON:
            {{
                "valor_raw": "string",
                "confianca_reinspecao": float (0.0-1.0)
            }}
            """

            if self.google_client:
                # O Google Client SDK atual pode não suportar bytes diretamente no generate_content de forma async fácil 
                # sem upload. Para simplicidade, usamos OpenRouter aqui ou implementamos via bytes se suportado.
                # Como já temos o base64, OpenRouter é mais direto agora.
                pass

            if self.async_openrouter_client:
                response = await self.async_openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                            ],
                        }
                    ],
                )
                text = response.choices[0].message.content
                return self._parse_response(text)

            return None

        except Exception as e:
            logger.error(f"Erro na extração focada: {e}")
            return None

    def _parse_response(self, text: str) -> dict | None:
        """
        Parse da resposta da IA para JSON com detecção de injeção.
        """
        # Detecção de Prompt Injection no output (Self-Check)
        if self.guardrails.detect_prompt_injection(text):
            logger.critical("BLOQUEIO DE SEGURANÇA: Tentativa de Prompt Injection detectada no output da IA.")
            return None

        try:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(cleaned)
            return dados
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Erro ao parsear resposta da IA: {e}")
            return None
