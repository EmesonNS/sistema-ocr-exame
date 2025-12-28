import google.generativeai as genai
import os
import json
import time
import re

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def classificar_status_alerta(valor: float, referencia_lab: str) -> str:
    """
    Classifica o status do biomarcador baseado no valor e referência.
    
    Args:
        valor: Valor extraído do biomarcador
        referencia_lab: String com a referência (ex: "70 a 99", "4.5-5.5")
    
    Returns:
        "normal", "alerta" ou "critico"
    """
    if not referencia_lab or valor is None:
        return "normal"
    
    try:
        # Remove espaços e converte para minúsculas
        ref = referencia_lab.strip().lower()
        
        # Tenta extrair limites numéricos (aceita formatos: "70-99", "70 a 99", "70-99 mg/dL")
        # Remove unidades de medida
        ref_clean = re.sub(r'[a-z°%/].*$', '', ref).strip()
        
        # Padrões: "70-99", "70 a 99", "70 até 99"
        if '-' in ref_clean:
            partes = ref_clean.split('-')
        elif ' a ' in ref_clean:
            partes = ref_clean.split(' a ')
        elif ' até ' in ref_clean:
            partes = ref_clean.split(' até ')
        else:
            return "normal"
        
        if len(partes) == 2:
            try:
                minimo = float(partes[0].strip())
                maximo = float(partes[1].strip())
                
                # Lógica de classificação
                if minimo <= valor <= maximo:
                    return "normal"
                elif valor < minimo:
                    # Abaixo do mínimo - verifica se é crítico (muito abaixo)
                    diferenca_percentual = ((minimo - valor) / minimo) * 100
                    if diferenca_percentual > 20:
                        return "critico"
                    return "alerta"
                else:  # valor > maximo
                    # Acima do máximo - verifica se é crítico (muito acima)
                    diferenca_percentual = ((valor - maximo) / maximo) * 100
                    if diferenca_percentual > 20:
                        return "critico"
                    return "alerta"
            except ValueError:
                return "normal"
    except Exception:
        pass
    
    return "normal"


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