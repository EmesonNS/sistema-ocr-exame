import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configuração de Estilo Científico
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 12})

def gerar_graficos():
    file_path = "benchmark_final_acuracia.csv"
    
    if not os.path.exists(file_path):
        print(f"Erro: Rode o 'calc_kpis.py' primeiro para gerar o arquivo {file_path}")
        return

    df = pd.read_csv(file_path)

    # Cria pasta para salvar imagens
    os.makedirs("benchmark/graficos", exist_ok=True)

    # --- GRÁFICO 1: Eficácia Técnica (Acurácia vs F1) ---
    plt.figure(figsize=(10, 6))
    
    # Derrete o dataframe para formato longo (seaborn gosta assim)
    df_melt = df.melt(id_vars=["Modelo"], value_vars=["Acuracia (%)", "F1-Score"], var_name="Métrica", value_name="Valor")
    
    # Ajusta escala do F1 para ficar comparável (0-100)
    df_melt.loc[df_melt["Métrica"] == "F1-Score", "Valor"] *= 100
    
    sns.barplot(data=df_melt, x="Modelo", y="Valor", hue="Métrica", palette="viridis")
    plt.title("Comparativo de Eficácia: LLM vs OCR Tradicional", fontsize=14, pad=20)
    plt.ylabel("Performance (Escala 0-100)")
    plt.ylim(0, 105)
    plt.legend(loc='upper right')
    
    plt.savefig("benchmark/graficos/1_eficacia.png", dpi=300, bbox_inches='tight')
    print("Gráfico 1 salvo: Eficácia")

    # --- GRÁFICO 2: Custo Total (TCO) ---
    plt.figure(figsize=(8, 6))
    colors = ['#2ecc71' if 'Gemini' in x else '#e74c3c' for x in df['Modelo']]
    
    bar = sns.barplot(data=df, x="Modelo", y="TCO ($)", palette=colors)
    plt.title("Custo Total de Propriedade (TCO) por Documento", fontsize=14, pad=20)
    plt.ylabel("Custo Estimado (USD)")
    
    # Adiciona valores nas barras
    for p in bar.patches:
        bar.annotate(f'${p.get_height():.2f}', 
                     (p.get_x() + p.get_width() / 2., p.get_height()), 
                     ha = 'center', va = 'center', xytext = (0, 10), textcoords = 'offset points')

    plt.savefig("benchmark/graficos/2_tco_custo.png", dpi=300, bbox_inches='tight')
    print("Gráfico 2 salvo: TCO")

    # --- GRÁFICO 3: Trade-off (Latência vs Acurácia) ---
    plt.figure(figsize=(10, 6))
    
    # Scatter Plot
    sns.scatterplot(data=df, x="Latencia (s)", y="Acuracia (%)", hue="Modelo", style="Modelo", s=200, palette="deep")
    
    plt.title("Trade-off: Tempo de Processamento vs. Qualidade", fontsize=14, pad=20)
    plt.xlabel("Latência Média (segundos)")
    plt.ylabel("Acurácia (%)")
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Anotações para explicar o gráfico
    plt.text(df['Latencia (s)'].max(), df['Acuracia (%)'].max() - 5, 
             "Alta Qualidade,\nProcessamento Lento\n(Ideal p/ Background)", 
             horizontalalignment='right', fontsize=10, color='green')

    plt.savefig("benchmark/graficos/3_tradeoff.png", dpi=300, bbox_inches='tight')
    print("Gráfico 3 salvo: Trade-off")

if __name__ == "__main__":
    gerar_graficos()