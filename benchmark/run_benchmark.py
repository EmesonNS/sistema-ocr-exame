import os
import time
import json
import re
import pandas as pd
import pytesseract
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
import google.generativeai as genai
import logging
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configuração Paddle (Sem MKLDNN para evitar crash)
logging.getLogger("ppocr").setLevel(logging.ERROR)
try:
    paddle_engine = PaddleOCR(use_angle_cls=True, lang='pt', show_log=False, enable_mkldnn=False)
except:
    paddle_engine = PaddleOCR(use_angle_cls=True, lang='pt', enable_mkldnn=False)

DATASET_DIR = "dataset_teste"
# Salvamos em JSON agora para manter a estrutura completa, CSV quebra formatação
RESULTADOS_JSON = "benchmark_resultados_full.json" 

PROMPT_PADRAO = """
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

# --- PARSER HEURÍSTICO (A "CHANCE" DO TESSERACT) ---
def parse_raw_text_to_json(text):
    """
    Parser avançado com correção de erros comuns de OCR (Heurística).
    Tenta recuperar dados mesmo quando o OCR troca caracteres.
    """
    extracted = {
        "exame": {
            "laboratorio": None,
            "data": None,
            "biomarcadores": []
        }
    }
    
    # --- 1. Pré-processamento e Limpeza (O Pulo do Gato) ---
    # Corrige erros comuns de leitura de unidades e símbolos
    correcoes = {
        "$": "%",       # OCR confunde % com $
        "&": "%",       # OCR confunde % com &
        "f1": "fL",     # OCR confunde fL com f1
        "fI": "fL",     # OCR confunde fL com fI
        "mcr": "mm3",   # OCR destrói o mm3 às vezes
        "mm?": "mm3",
        "g/dl": "g/dL", # Padronização
    }
    
    # Aplica as correções no texto bruto
    text_clean = text
    for erro, corr in correcoes.items():
        text_clean = text_clean.replace(erro, corr)

    # --- 2. Extração de Data ---
    # Aceita dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa
    date_match = re.search(r'(\d{2})[\/\.\-](\d{2})[\/\.\-](\d{4})', text_clean)
    if date_match:
        extracted["exame"]["data"] = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"

    # --- 3. Extração de Biomarcadores (Regex Mais Flexível) ---
    lines = text_clean.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) < 5: continue

        # Regex Explicado:
        # 1. (Nome): Letras, espaços, parênteses, hifens (ex: "V.C.M.", "Hemoglobina-Glicada")
        # 2. (Valor): Números com vírgula ou ponto (ex: 13,5 ou 4.58)
        # 3. (Unidade): Qualquer palavra colada no número (ex: g/dL, %, mm3)
        
        # Padrão: Nome... espaço... Valor... espaço... Unidade
        match = re.search(r'^([A-Za-zÀ-ÿ0-9\.\-\s\(\)]+?)\s+(\d+[,.]\d+)\s+([A-Za-z%°\/3]+)', line)
        
        if match:
            try:
                nome = match.group(1).strip()
                valor_str = match.group(2).replace(',', '.')
                unidade = match.group(3).strip()
                
                # Validações de sanidade para evitar lixo
                # a) Nome deve ter pelo menos 2 letras
                # b) Unidade não deve ser muito longa (senão pegou texto de referência)
                # c) Ignora linhas que parecem datas ou telefones
                if len(nome) > 2 and len(unidade) < 12 and not re.search(r'\d{2}/\d{2}', nome):
                    extracted["exame"]["biomarcadores"].append({
                        "nome": nome,
                        "valor": float(valor_str),
                        "unidade": unidade
                    })
            except:
                continue

    # --- 4. Extração de Laboratório (Heurística Simples) ---
    # Pega a primeira linha que parece um nome de empresa (sem números)
    for line in lines[:6]:
        clean_line = line.strip()
        if len(clean_line) > 3 and not re.search(r'\d', clean_line) and "exame" not in clean_line.lower():
            extracted["exame"]["laboratorio"] = clean_line
            break
            
    return extracted

# --- FUNÇÕES AUXILIARES ---
def pdf_to_image(pdf_path):
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
        return images[0] if images else None
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None

# --- MODELOS ---
def run_gemini(file_path):
    start = time.time()
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        myfile = genai.upload_file(file_path)
        while myfile.state.name == "PROCESSING": time.sleep(0.5); myfile = genai.get_file(myfile.name)
        
        response = model.generate_content([PROMPT_PADRAO, myfile])
        output_struct = json.loads(response.text) # Já sai estruturado
        output_text = response.text # Texto puro para CER
        genai.delete_file(myfile.name)
        
    except Exception as e:
        output_struct = {"error": str(e)}
        output_text = ""
    
    return output_struct, output_text, time.time() - start

def run_local_ocr(file_path, engine="paddle"):
    start = time.time()
    try:
        img = pdf_to_image(file_path)
        if not img: raise Exception("Falha img")
        
        raw_text = ""
        if engine == "paddle":
            import numpy as np
            result = paddle_engine.ocr(np.array(img))
            if result and result[0]:
                raw_text = "\n".join([line[1][0] for line in result[0]])
        else: # tesseract
            raw_text = pytesseract.image_to_string(img, lang='por')
            
        # AQUI ESTÁ A DIFERENÇA: Tentamos parsear o texto
        output_struct = parse_raw_text_to_json(raw_text)
        
    except Exception as e:
        raw_text = str(e)
        output_struct = {"error": str(e)}
        
    return output_struct, raw_text, time.time() - start

# --- MAIN ---
def main():
    if not os.path.exists(DATASET_DIR): os.makedirs(DATASET_DIR); return

    files = [f for f in os.listdir(DATASET_DIR) if f.lower().endswith('.pdf')]
    results = []

    print(f"--- Iniciando Benchmark Real (Parser Ativo) ---")
    
    for file in files:
        fpath = os.path.join(DATASET_DIR, file)
        print(f"Processando: {file}")
        
        # 1. Gemini
        s_gem, t_gem, time_gem = run_gemini(fpath)
        results.append({
            "arquivo": file, "modelo": "Gemini 2.5", 
            "json_output": s_gem, "raw_text": t_gem, "latencia": time_gem
        })
        
        # 2. Paddle
        s_pad, t_pad, time_pad = run_local_ocr(fpath, "paddle")
        results.append({
            "arquivo": file, "modelo": "PaddleOCR", 
            "json_output": s_pad, "raw_text": t_pad, "latencia": time_pad
        })

        # 3. Tesseract
        s_tes, t_tes, time_tes = run_local_ocr(fpath, "tesseract")
        results.append({
            "arquivo": file, "modelo": "Tesseract", 
            "json_output": s_tes, "raw_text": t_tes, "latencia": time_tes
        })

    with open(RESULTADOS_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Resultados salvos em {RESULTADOS_JSON}")

if __name__ == "__main__":
    main()