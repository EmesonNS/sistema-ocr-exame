import google.generativeai as genai
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extrair_dados_exame(self, file_path: str) -> dict:
        prompt = """
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
        
        try:
            sample_file = genai.upload_file(path=file_path, display_name="Exame")
            response = self.model.generate_content([sample_file, prompt])
            
            # Clean logging of raw response to avoid massive logs, just log success/fail
            logger.info("Resposta recebida do Gemini")
            
            # Remove markdown formatting if present
            cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
            
            dados = json.loads(cleaned_text)
            
            # Process alerts logic here to keep it centralized or keep it simple
            for item in dados.get("resultados", []):
                item["status_alerta"] = self._classificar_alerta(item["valor"], item["referencia"])
                
            return dados
            
        except Exception as e:
            logger.error(f"Erro na extração de dados com IA: {e}")
            return {"resultados": []}

    def _classificar_alerta(self, valor, referencia):
        # Implementação simplificada de classificação
        # Pode ser expandida com regex para parsear a string de referência
        return "normal"