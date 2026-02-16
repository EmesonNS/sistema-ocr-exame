from google import genai
from openai import OpenAI
from app.core.config import settings
import base64
import json
import logging

logger = logging.getLogger(__name__)

PROMPT_EXAME = """
Analise este exame médico e extraia os resultados dos biomarcadores.
Retorne APENAS um JSON válido com a seguinte estrutura, sem markdown:
{
    "resultados": [
        {
            "nome": "nome do biomarcador",
            "valor": 0.0,
            "unidade": "unidade de medida",
            "referencia": "valores de referência"
        }
    ]
}
Se o valor não for numérico, tente converter ou extraia como está.
"""


class AIService:
    def __init__(self):
        self.google_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.0-flash"
        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

    def extrair_dados_exame(self, file_path: str) -> dict:
        # Tenta Google Gemini primeiro
        dados = self._extrair_via_google(file_path)
        if dados and dados.get("resultados"):
            return dados

        # Fallback para OpenRouter
        if self.openrouter_client:
            logger.warning("Google Gemini falhou ou retornou vazio, tentando OpenRouter")
            dados = self._extrair_via_openrouter(file_path)
            if dados:
                return dados

        logger.error("Ambos os provedores falharam na extração")
        return {"resultados": []}

    def _extrair_via_google(self, file_path: str) -> dict | None:
        try:
            uploaded_file = self.google_client.files.upload(file=file_path)

            response = self.google_client.models.generate_content(
                model=self.model,
                contents=[uploaded_file, PROMPT_EXAME],
            )

            logger.info("Resposta recebida do Google Gemini")
            return self._parse_response(response.text)

        except Exception as e:
            logger.error(f"Erro no Google Gemini: {e}")
            return None

    def _extrair_via_openrouter(self, file_path: str) -> dict | None:
        try:
            with open(file_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

            response = self.openrouter_client.chat.completions.create(
                model=f"google/{self.model}",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "file",
                                "file": {
                                    "filename": "exame.pdf",
                                    "data": f"data:application/pdf;base64,{pdf_b64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": PROMPT_EXAME,
                            },
                        ],
                    }
                ],
            )

            text = response.choices[0].message.content
            logger.info("Resposta recebida do OpenRouter (fallback)")
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Erro no OpenRouter (fallback): {e}")
            return None

    def _parse_response(self, text: str) -> dict | None:
        try:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(cleaned)

            for item in dados.get("resultados", []):
                item["status_alerta"] = self._classificar_alerta(
                    item.get("valor"), item.get("referencia")
                )

            return dados
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Erro ao parsear resposta da IA: {e}")
            return None

    def _classificar_alerta(self, valor, referencia):
        return "normal"
