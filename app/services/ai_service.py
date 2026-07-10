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
from pypdf import PdfReader
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
import re
import unicodedata

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

TEXTUAL_BIOMARKER_RULES = {
    "ERITROCITOS": {"aliases": ["ERITROCITOS", "ERITROCITO", "ERITROCIT"]},
    "HEMOGLOBINA": {"aliases": ["HEMOGLOBINA"]},
    "HEMATOCRITO": {"aliases": ["HEMATOCRITO"]},
    "VCM": {"aliases": ["VCM"]},
    "HCM": {"aliases": ["HCM"]},
    "CHCM": {"aliases": ["CHCM"]},
    "RDW": {"aliases": ["RDW"]},
    "LEUCOCITOS": {"aliases": ["LEUCOCITOS"]},
    "NEUTROFILOS": {"aliases": ["NEUTROFILOS"]},
    "EOSINOFILOS": {"aliases": ["EOSINOFILOS"]},
    "BASOFILOS": {"aliases": ["BASOFILOS"]},
    "LINFOCITOS": {"aliases": ["LINFOCITOS"]},
    "MONOCITOS": {"aliases": ["MONOCITOS"]},
    "PLAQUETAS": {"aliases": ["PLAQUETAS"]},
    "VPM": {"aliases": ["VPM"]},
    "FERRO": {"aliases": ["FERRO"]},
}


class AIService:
    """Serviço de extração de biomarcadores usando IA com fallback."""

    def __init__(self):
        self.google_client = None
        try:
            self.google_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as exc:
            logger.warning("Falha ao inicializar cliente Gemini: %s", exc)
            self.google_client = None
        self.google_model = "gemini-2.0-flash"
        self.openrouter_model = "google/gemini-2.5-flash"
        self.openrouter_client = None
        self.async_openrouter_client = None
        self.guardrails = GuardrailsService()
        self._usage_events: list[dict[str, int | str]] = []

        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
            self.async_openrouter_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

    def begin_usage_tracking(self) -> None:
        """Inicia um novo ciclo de rastreamento de uso."""
        self._usage_events = []

    def consume_usage_summary(self) -> dict[str, int]:
        """Retorna e limpa o uso acumulado no ciclo atual."""
        summary = {
            "total_tokens": sum(
                int(event.get("total_tokens", 0))
                for event in self._usage_events
                if event.get("kind") == "main"
            ),
            "agentic_zoom_tokens": sum(
                int(event.get("total_tokens", 0))
                for event in self._usage_events
                if event.get("kind") == "agentic_zoom"
            ),
        }
        self._usage_events = []
        return summary

    def _get_value(self, source: object, *names: str) -> object | None:
        for name in names:
            if isinstance(source, dict) and name in source:
                return source.get(name)
            if hasattr(source, name):
                return getattr(source, name)
        return None

    def _extract_total_tokens(self, response: object) -> int | None:
        usage = self._get_value(response, "usage", "usage_metadata", "usageMetadata")
        if usage is None:
            return None

        total = self._get_value(usage, "total_tokens", "total_token_count")
        if total is not None:
            try:
                return int(total)
            except (TypeError, ValueError):
                return None

        prompt = self._get_value(usage, "prompt_tokens", "prompt_token_count")
        completion = self._get_value(usage, "completion_tokens", "candidates_token_count")
        try:
            if prompt is not None and completion is not None:
                return int(prompt) + int(completion)
        except (TypeError, ValueError):
            return None

        return None

    def _record_usage(self, response: object, kind: str) -> None:
        total_tokens = self._extract_total_tokens(response)
        if total_tokens is None:
            return
        self._usage_events.append({"kind": kind, "total_tokens": total_tokens})

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
        self.begin_usage_tracking()
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
            dados = await self._extrair_via_openrouter_texto_async(file_path)
            if dados and dados.get("biomarcadores"):
                resultados, dt, lab = self._processar_biomarcadores(dados, leucocitos_total)
                resultados = self.guardrails.sanitize_results(resultados)
                return resultados, dt, lab

            dados = await self._extrair_via_openrouter_async(file_path)
            if dados and dados.get("biomarcadores"):
                resultados, dt, lab = self._processar_biomarcadores(dados, leucocitos_total)
                # Aplicar Guardrails Fisiológicos
                resultados = self.guardrails.sanitize_results(resultados)
                return resultados, dt, lab

        dados = await self._extrair_via_texto_deterministico(file_path)
        if dados and dados.get("biomarcadores"):
            logger.warning(
                "Fallback deterministico de texto usado para extracao de biomarcadores"
            )
            resultados, dt, lab = self._processar_biomarcadores(dados, leucocitos_total)
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
        # Note: this wrapper is only safe when called from a truly sync context.
        # If a running event loop exists, callers must use the async API directly.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            resultados, _, _ = asyncio.run(self.extrair_biomarcadores(file_path))
            return {"resultados": resultados}

        raise RuntimeError(
            "extrair_dados_exame() não deve ser chamado dentro de um event loop; "
            "use extrair_biomarcadores() diretamente"
        )

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
            self._record_usage(response, "main")

            text = response.text
            if not text:
                return None

            logger.info("Resposta recebida do Google Gemini (Async)")
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Erro no Google Gemini (Async): {e}")
            return None

    async def _extrair_via_openrouter_texto_async(self, file_path: str) -> dict | None:
        if not self.async_openrouter_client:
            return None

        try:
            loop = asyncio.get_event_loop()

            def extract_text_sync() -> str:
                reader = PdfReader(file_path)
                pages = []
                for page in reader.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
                return "\n\n".join(pages)

            text = await loop.run_in_executor(None, extract_text_sync)
            if len(text.strip()) < 200:
                return None

            prompt = f"""
            Analise o texto extraído deste laudo laboratorial e extraia todos os biomarcadores.

            Para cada biomarcador encontrado, retorne:
            - nome
            - valor_raw exatamente como aparece
            - unidade
            - referencia, quando houver intervalo de referência próximo ao resultado
            - tipo: percentual, absoluto ou textual
            - page: null
            - bounding_box: null

            Não invente valores ausentes. Preserve vírgula, ponto, símbolos <, > e unidades.
            Retorne somente JSON no formato:
            {{
              "biomarcadores": [
                {{
                  "nome": "string",
                  "valor_raw": "string",
                  "unidade": "string",
                  "referencia": "string|null",
                  "tipo": "percentual|absoluto|textual",
                  "page": null,
                  "bounding_box": null
                }}
              ],
              "data_coleta": "string|null",
              "laboratorio": "string|null"
            }}

            TEXTO DO LAUDO:
            {text[:80000]}
            """

            response = await asyncio.wait_for(
                self.async_openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS,
            )
            self._record_usage(response, "main")

            content = response.choices[0].message.content
            if not content:
                return None
            logger.info("Resposta recebida do OpenRouter por texto extraído")
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Erro no OpenRouter por texto extraído: {e}")
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

            response = await asyncio.wait_for(
                self.async_openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=[
                        {
                            "role": "user",
                            "content": final_content_parts,
                        }
                    ],
                ),
                timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS,
            )
            self._record_usage(response, "main")

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

    async def _extrair_via_texto_deterministico(self, file_path: str) -> dict | None:
        """Fallback local para PDFs textuais com estrutura de laudo tabular."""
        try:
            loop = asyncio.get_event_loop()

            def read_pages() -> tuple[list[str], str]:
                reader = PdfReader(file_path)
                pages_text: list[str] = []
                for page in reader.pages:
                    pages_text.append(page.extract_text() or "")
                return pages_text, "\n".join(pages_text)

            pages_text, full_text = await loop.run_in_executor(None, read_pages)
            biomarcadores: list[dict[str, object]] = []
            seen: set[str] = set()

            for page_index, page_text in enumerate(pages_text, start=1):
                for raw_line in page_text.splitlines():
                    line = (raw_line or "").strip()
                    if not line or not re.search(r"\d", line):
                        continue

                    name = self._infer_textual_marker_name(line)
                    if not name or name in seen:
                        continue

                    parsed = self._parse_textual_marker_line(name, line, page_index)
                    if not parsed:
                        continue

                    biomarcadores.append(parsed)
                    seen.add(name)

            if not biomarcadores:
                return None

            data_coleta = self._extract_date_from_text(full_text)
            laboratorio = self._extract_laboratory_from_text(full_text)
            return {
                "biomarcadores": biomarcadores,
                "data_coleta": data_coleta,
                "laboratorio": laboratorio,
            }
        except Exception as exc:
            logger.error("Fallback deterministico de texto falhou: %s", exc)
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
                logger.debug(
                    "Google client disponível, mas o zoom de recorte usa OpenRouter por suporte nativo a imagem base64"
                )

            if self.async_openrouter_client:
                response = await asyncio.wait_for(
                    self.async_openrouter_client.chat.completions.create(
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
                    ),
                    timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS,
                )
                self._record_usage(response, "agentic_zoom")
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

    def _normalize_marker_name(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return re.sub(r"[^A-Z]", "", normalized.upper())

    def _infer_textual_marker_name(self, line: str) -> str | None:
        if not line:
            return None

        first_digit = re.search(r"\d", line)
        if not first_digit:
            return None

        raw_name = line[: first_digit.start()]
        normalized = self._normalize_marker_name(raw_name)
        if not normalized:
            return None

        for canonical, payload in TEXTUAL_BIOMARKER_RULES.items():
            if any(normalized == alias for alias in payload["aliases"]):
                return canonical
        return None

    def _extract_value_pairs(self, line: str) -> list[tuple[str, str]]:
        matches = re.findall(r"([<>]?\s*\d[\d.,]*)\s*([A-Za-zµμ/%^°0-9./-]+)?", line)
        cleaned: list[tuple[str, str]] = []
        for value, unit in matches:
            value = value.strip()
            unit = (unit or "").strip()
            if not value:
                continue
            if unit.lower() == "a":
                continue
            cleaned.append((value, unit))
        return cleaned

    def _select_textual_value(self, marker_name: str, pairs: list[tuple[str, str]]) -> tuple[str, str] | None:
        if not pairs:
            return None

        def has_unit(pair: tuple[str, str], needle: str) -> bool:
            return needle.lower() in (pair[1] or "").lower()

        if marker_name == "LEUCOCITOS":
            for pair in pairs:
                if any(token in pair[1].upper() for token in ["/µL", "/ΜL", "/UL", "/MM3", "/MM³"]):
                    return pair
        elif marker_name in {"NEUTROFILOS", "EOSINOFILOS", "BASOFILOS", "LINFOCITOS", "MONOCITOS", "HEMATOCRITO", "RDW"}:
            for pair in pairs:
                if has_unit(pair, "%"):
                    return pair
        elif marker_name == "PLAQUETAS":
            for pair in pairs:
                if any(token in pair[1].upper() for token in ["/µL", "/ΜL", "/UL", "/MM3", "/MM³"]):
                    return pair

        return pairs[0]

    def _extract_reference_from_line(self, line: str, start_index: int) -> str | None:
        tail = line[start_index:]
        match = re.search(r"(\d[\d.,]*)\s*a\s*(\d[\d.,]*)\s*([A-Za-zµμ/%^°0-9./-]+)", tail)
        if not match:
            return None
        return f"{match.group(1)} a {match.group(2)} {match.group(3)}"

    def _parse_textual_marker_line(self, marker_name: str, line: str, page_number: int) -> dict | None:
        pairs = self._extract_value_pairs(line)
        selected = self._select_textual_value(marker_name, pairs)
        if not selected:
            return None

        value_raw, unit = selected
        value_index = line.find(value_raw)
        if value_index < 0:
            return None

        referencia = self._extract_reference_from_line(line, value_index + len(value_raw))
        payload: dict[str, object] = {
            "nome": marker_name,
            "valor_raw": value_raw,
            "unidade": unit or None,
            "tipo": "textual" if marker_name not in {"LEUCOCITOS", "PLAQUETAS", "ERITROCITOS"} and "%" not in (unit or "") and "/" not in (unit or "") and "g/dL" not in (unit or "") else "absoluto",
            "page": page_number,
            "bounding_box": None,
        }
        if referencia:
            payload["referencia"] = referencia
        return payload

    def _extract_date_from_text(self, text: str) -> str | None:
        for raw_line in (text or "").replace("\u00a0", " ").splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue
            upper = line.upper()
            if "COLETA/RECEBIMENTO" in upper:
                match = re.search(
                    r"DATA\s+COLETA/RECEBIMENTO\s*:\s*(\d{2}/\d{2}/\d{4})",
                    line,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1)
            if "DATA DA COLETA" in upper:
                match = re.search(
                    r"DATA\s+DA\s+COLETA\s*:\s*(\d{2}/\d{2}/\d{4})",
                    line,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1)
        return None

    def _extract_laboratory_from_text(self, text: str) -> str | None:
        match = re.search(r"Laboratório\s*[:\-]\s*([^\n|]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
