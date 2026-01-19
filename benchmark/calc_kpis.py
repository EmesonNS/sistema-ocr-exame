import json
import pandas as pd
from Levenshtein import ratio
import numpy as np

# --- CONFIGURAÇÕES ---
CUSTO_API_GEMINI = 0.002
CUSTO_HUMANO_MINUTO = 0.50 
TEMPO_ABRIR_DOC = 0.3
TEMPO_CORRIGIR_CAMPO = 0.5

def carregar_dados():
    try:
        with open("benchmark_resultados_full.json", "r", encoding="utf-8") as f:
            resultados = json.load(f)
        with open("benchmark/ground_truth.json", "r", encoding="utf-8") as f:
            gabarito = json.load(f)
        return resultados, gabarito
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
        exit()

def normalizar(texto):
    if not texto: return ""
    return str(texto).lower().strip().replace(',', '.')

def safe_float(valor):
    try:
        if isinstance(valor, str):
            # Limpa tudo que não for número ou ponto/vírgula
            import re
            valor = re.sub(r'[^\d.,-]', '', valor)
            valor = valor.replace(',', '.')
        return float(valor)
    except (ValueError, TypeError):
        return None

def calcular_metricas(predicao, verdade, texto_raw, nome_arquivo, modelo):
    # 1. CER (Erro de Texto)
    verdade_str = json.dumps(verdade, ensure_ascii=False)
    cer = 1.0 - ratio(str(texto_raw), verdade_str)

    # 2. Extração de Campos
    # Normaliza a estrutura (lidando com "exame" ou raiz)
    pred_bios = {}
    lista_pred = predicao.get('exame', {}).get('biomarcadores', [])
    if not lista_pred and 'biomarcadores' in predicao: lista_pred = predicao['biomarcadores']
    
    for b in lista_pred:
        nome = normalizar(b.get('nome'))
        val = safe_float(b.get('valor'))
        if nome and val is not None: pred_bios[nome] = val

    true_bios = {}
    lista_real = verdade.get('biomarcadores', [])
    if not lista_real and 'exame' in verdade: lista_real = verdade['exame'].get('biomarcadores', [])
    
    for b in lista_real:
        nome = normalizar(b.get('nome'))
        val = safe_float(b.get('valor'))
        if nome and val is not None: true_bios[nome] = val

    # 3. Comparação Detalhada
    acertos = 0
    erros = 0
    total_esperado = len(true_bios)
    erros_detalhes = []

    if total_esperado == 0: return 0, 0, 0, 0, 0, 0 # Evita div zero

    for nome_real, valor_real in true_bios.items():
        encontrou = False
        for nome_pred, valor_pred in pred_bios.items():
            # Match de Nome (Fuzzy 80%)
            if ratio(nome_real, nome_pred) > 0.80:
                # Match de Valor (Margem 0.1)
                if abs(valor_pred - valor_real) < 0.1:
                    acertos += 1
                    encontrou = True
                    break
                else:
                    # Achou o nome, mas valor está errado
                    erros_detalhes.append(f"Valor incorreto em '{nome_real}': Real={valor_real} vs Pred={valor_pred}")
                    break # Para de procurar este campo
        
        if not encontrou and not any(msg.startswith(f"Valor incorreto em '{nome_real}'") for msg in erros_detalhes):
            erros += 1
            erros_detalhes.append(f"Não encontrou o campo '{nome_real}'")

    # Se houver erros, imprime para você saber ONDE errou
    if erros_detalhes and "Gemini" in modelo:
        print(f"\n--- DEBUG EMR ({modelo}) em {nome_arquivo} ---")
        for e in erros_detalhes:
            print(f"  ❌ {e}")

    # 4. Métricas Finais
    accuracy = acertos / total_esperado # Acurácia (O que você queria)
    emr = 1.0 if acertos == total_esperado else 0.0 # EMR (Rigoroso)
    
    # Cálculo F1 Simplificado
    precision = acertos / len(pred_bios) if len(pred_bios) > 0 else 0
    f1 = 2 * (precision * accuracy) / (precision + accuracy) if (precision + accuracy) > 0 else 0

    return cer, f1, emr, accuracy, len(erros_detalhes)

def main():
    resultados, gabarito = carregar_dados()
    metricas = []

    print(f"Calculando...")

    for item in resultados:
        f = item['arquivo']
        if f not in gabarito: continue

        cer, f1, emr, acc, qtd_erros = calcular_metricas(
            item.get('json_output', {}), 
            gabarito[f], 
            item.get('raw_text', ''),
            f,
            item['modelo']
        )

        # TCO Proporcional
        custo_humano = TEMPO_ABRIR_DOC
        if emr < 1.0:
            custo_humano += (qtd_erros * TEMPO_CORRIGIR_CAMPO)
        
        tco = (CUSTO_API_GEMINI if "Gemini" in item['modelo'] else 0.0) + (custo_humano * CUSTO_HUMANO_MINUTO)

        metricas.append({
            "Modelo": item['modelo'],
            "Acuracia (%)": round(acc * 100, 1), # Nova Coluna
            "EMR (0/1)": round(emr, 2),
            "F1-Score": round(f1, 2),
            "TCO ($)": round(tco, 2),
            "Latencia (s)": round(item['latencia'], 1)
        })

    df = pd.DataFrame(metricas)
    resumo = df.groupby("Modelo")[["Acuracia (%)", "EMR (0/1)", "F1-Score", "TCO ($)", "Latencia (s)"]].mean().reset_index()

    print("\n=== RELATÓRIO DETALHADO ===")
    try: print(resumo.to_markdown(index=False))
    except: print(resumo)
    
    resumo.to_csv("benchmark_final_acuracia.csv", index=False)

if __name__ == "__main__":
    main()