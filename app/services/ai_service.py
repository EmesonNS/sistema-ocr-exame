import google.generativeai as genai
import os
import json
import time

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extrair_dados_exame(file_path: str):
  
  model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
  )
  
  try:
    exame_file = genai.upload_file(path=file_path, display_name="Exame Laboratorial")

    # Verificação de processamento
    while exame_file.state.name == "PROCESSING":
        time.sleep(1)
        exame_file = genai.get_file(exame_file.name)

    if exame_file.state.name == "FAILED":
        raise Exception("O processamento do arquivo no Google falhou.")

    prompt = """
    Analise este exame laboratorial e extraia os resultados em formato JSON estritamente seguindo esta estrutura:
    {
      "exame": {
        "laboratorio": "string",
        "data": "YYYY-MM-DD",
        "biomarcadores": [
          {"nome": "Glicose", "valor": 90.5, "unidade": "mg/dL", "referencia": "70 a 99"},
          ...
        ]
      }
    }
    Ignore textos informativos e foque apenas nos nomes dos marcadores, valores numéricos e unidades.
    """
    # Gera a resposta
    response = model.generate_content([prompt, exame_file])
  
    json_data = json.loads(response.text)
  
    genai.delete_file(exame_file.name)
  
    return json_data
  
  except Exception as e:
    try:
       genai.delete_file(exame_file.name)
    except:
       pass
    raise Exception(f"Erro no processamento da IA: {str(e)}")