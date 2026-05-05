import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from datetime import datetime
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def create_thesis_plots_3d(total_hours=None):
    print("A analisar e gerar gráficos finais de alta qualidade para a tese...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stats_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas')
    
    # Criar string com data/hora e horas de treino
    now = datetime.now()
    date_time_str = now.strftime("%d-%m-%Y_%Hh%Mm")
    
    # Se total_hours for garantidamente passado como um valor válido
    if total_hours and str(total_hours).strip() != "N":
        folder_name = f"{date_time_str}_{total_hours}hT"
    else:
        folder_name = f"{date_time_str}_Treino"
        
    # Pasta final com carimbo de tempo
    final_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'finais_pdf', folder_name)
    os.makedirs(final_dir, exist_ok=True)
    
    csv_scores = os.path.join(stats_dir, 'all_best_scores.csv')
    csv_curves = os.path.join(stats_dir, 'all_curves_data.csv')
    
    if not os.path.exists(csv_scores) or not os.path.exists(csv_curves):
        print(f"Erro: Não foram encontrados os ficheiros CSV agregados na pasta {stats_dir}")
        print("Tem a certeza que correu o run_experiments.py primeiro?")
        input("\nPressione ENTER para sair...")
        return

    df_best = pd.read_csv(csv_scores)
    df_curves = pd.read_csv(csv_curves)

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    cores = {'GNN': '#2ca02c', 'PPO': '#ff7f0e', 'SAC': '#1f77b4'} # Verde, Laranja, Azul Clássico

    scenarios = df_best['Scenario'].unique()

    print("A gerar Gráfico Global...")
    # 1. GRÁFICO GLOBAL (Com escala logarítmica para se conseguir ver PPO e SAC)
    plt.figure(figsize=(14, 7))
    
    # Adicionamos uma pequena constante para não quebrar a escala logarítmica com valores muito baixos
    df_best['BestScore_Log'] = np.maximum(df_best['BestScore'], 1)
    
    ax = sns.barplot(data=df_best, x='Scenario', y='BestScore', hue='Algorithm', errorbar='sd', palette=cores, capsize=.1)
    
    # Aplicar Escala Logarítmica ao eixo Y (Isto resolve a ilegibilidade!)
    ax.set_yscale("log")
    
    plt.title('Comparação Global de Desempenho (Média das 30 Runs) - Escala Logarítmica', fontweight='bold', fontsize=16)
    plt.ylabel('Score Máximo Atingido (Escala Log)', fontsize=14)
    plt.xlabel('Cenários', fontsize=14)
    plt.xticks(rotation=15)
    plt.legend(title='Algoritmo', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(final_dir, '1_Comparacao_Global_Barras_LOG.png'), dpi=300)
    plt.close()

    print("A gerar Boxplots por cenário...")
    for scenario in scenarios:
        plt.figure(figsize=(8, 6))
        data_scen = df_best[df_best['Scenario'] == scenario]
        
        # Boxplot NORMAL (sem stripplot, para ser mais legível e profissional)
        sns.boxplot(data=data_scen, x='Algorithm', y='BestScore', hue='Algorithm', palette=cores, width=0.5, fliersize=5)
        
        plt.title(f'Distribuição de Scores das 30 Runs\nCenário: {scenario.upper()}', fontweight='bold', fontsize=14)
        plt.ylabel('Score Máximo', fontsize=12)
        plt.xlabel('Algoritmo', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'2_Boxplot_{scenario}.png'), dpi=300)
        plt.close()

    print("A gerar Curvas de Aprendizagem...")
    for scenario in scenarios:
        plt.figure(figsize=(10, 6))
        data_scen = df_curves[df_curves['Scenario'] == scenario]
        
        # Suavizar as curvas com Média Móvel (Rolling Mean) para não ficarem ilegíveis ("rabiscos")
        data_scen['Score_Suavizado'] = data_scen.groupby(['Algorithm', 'Run'])['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
        
        # O lineplot do Seaborn desenha a banda de erro suave
        sns.lineplot(data=data_scen, x='Step', y='Score_Suavizado', hue='Algorithm', palette=cores, errorbar='ci', n_boot=1000)
        
        plt.title(f'Curvas de Aprendizagem Média Suavizada (Cenário: {scenario.upper()})', fontweight='bold', fontsize=14)
        plt.ylabel('Score Absoluto', fontsize=12)
        plt.xlabel('Timesteps Simulação', fontsize=12)
        plt.legend(title='Algoritmo')
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'3_Curva_Suavizada_{scenario}.png'), dpi=300)
        plt.close()

    print(f"\n✅ Concluído! Todos os gráficos foram guardados na nova pasta datada:\n{final_dir}")
    
    if os.name == 'nt':
        os.startfile(final_dir)

if __name__ == '__main__':
    total_hours = None
    if len(sys.argv) > 1:
        total_hours = sys.argv[1]
    create_thesis_plots_3d(total_hours)
    input("\nPressione ENTER para fechar esta janela...")