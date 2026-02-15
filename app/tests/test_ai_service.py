from app.services.ai_service import AIService
from unittest.mock import MagicMock, patch

def test_ai_service_extraction_success():
    service = AIService()
    
    # Mock Google Generative AI response
    with patch("google.generativeai.GenerativeModel.generate_content") as mock_generate:
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "resultados": [
                {
                    "nome": "Colesterol Total",
                    "valor": 180,
                    "unidade": "mg/dL",
                    "referencia": "< 190"
                }
            ]
        }
        '''
        mock_generate.return_value = mock_response
        
        with patch("google.generativeai.upload_file"):
            result = service.extrair_dados_exame("fake_path.pdf")
            
            assert "resultados" in result
            assert len(result["resultados"]) == 1
            assert result["resultados"][0]["nome"] == "Colesterol Total"
            # Since logic is mocked/simplified, alert might be normal
            assert result["resultados"][0]["status_alerta"] == "normal"

def test_ai_service_handling_error():
    service = AIService()
    
    with patch("google.generativeai.GenerativeModel.generate_content", side_effect=Exception("API Error")):
         with patch("google.generativeai.upload_file"):
            result = service.extrair_dados_exame("fake_path.pdf")
            assert result == {"resultados": []}
