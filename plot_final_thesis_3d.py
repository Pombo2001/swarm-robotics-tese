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

def parse_folder_date(folder_name):
    try:
        date_str = folder_name.split('_')[0] + '_' + folder_name.split('_')[1]
        return datetime.strptime(date_str, "%d-%m-%Y_%Hh%Mm")
    except:
        return datetime.min

def update_latest_thesis_plots():
    print("A procurar o último treino realizado...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stats_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas')
    
    if not os.path.exists(stats_dir):
        print(f"Erro: A pasta {stats_dir} não existe.")
        input("\nPressione ENTER para sair...")
        return
        
    dirs = [d for d in os.listdir(stats_dir) if os.path.isdir(os.path.join(stats_dir, d))]
    if not dirs:
        print("Erro: Ainda não existem treinos gerados.")
        input("\nPressione ENTER para sair...")
        return
        
    latest_folder_name = max(dirs, key=parse_folder_date)
    latest_dir = os.path.join(stats_dir, latest_folder_name)
    
    print(f"Último treino encontrado: {latest_folder_name}")
    
    csv_scores = os.path.join(latest_dir, 'all_best_scores.csv')
    csv_curves = os.path.join(latest_dir, 'all_curves_data.csv')
    
    final_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'finais_pdf', latest_folder_name)
    os.makedirs(final_dir, exist_ok=True)
    
    if not os.path.exists(csv_scores) or not os.path.exists(csv_curves):
        print("Os ficheiros CSV não foram encontrados. A abrir a pasta...")
        if os.name == 'nt': os.startfile(final_dir)
        return

    print("A re-gerar os gráficos limpos...")
    df_best = pd.read_csv(csv_scores)
    df_curves = pd.read_csv(csv_curves)

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    cores = {'GNN': '#2ca02c', 'PPO': '#ff7f0e', 'SAC': '#1f77b4'}

    scenarios = df_best['Scenario'].unique()
    algorithms = df_best['Algorithm'].unique()

    # --- GRÁFICOS NOVOS E MELHORADOS ---

    # 1. Curvas de Aprendizagem com Escala Logarítmica
    print(" -> Curvas de Aprendizagem (Escala Logarítmica)...")
    for scenario in scenarios:
        plt.figure(figsize=(10, 6))
        data_scen = df_curves[df_curves['Scenario'] == scenario].copy()
        data_scen['Score_Suavizado'] = data_scen.groupby(['Algorithm', 'Run'])['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
        
        # Usar symlog para lidar com valores negativos ou zero de forma graciosa
        ax = sns.lineplot(data=data_scen, x='Step', y='Score_Suavizado', hue='Algorithm', palette=cores, errorbar='ci', n_boot=1000)
        ax.set_yscale('symlog', linthresh=1) # 'symlog' é melhor que 'log' para dados com zeros ou negativos
        
        plt.title(f'Curvas de Aprendizagem (Escala Log) - Cenário: {scenario.upper()}', fontweight='bold', fontsize=14)
        plt.ylabel('Score (Escala Symlog)', fontsize=12)
        plt.xlabel('Timesteps', fontsize=12)
        plt.legend(title='Algoritmo')
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'curva_log_{scenario}.png'), dpi=300)
        plt.close()

    # 2. Gráficos Lado a Lado (Subplots) para Comparação Direta
    print(" -> Gráficos Comparativos (Lado a Lado)...")
    for scenario in scenarios:
        # Criar uma figura com 3 subplots
        fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharex=True)
        fig.suptitle(f'Comparação de Desempenho Normalizado - Cenário: {scenario.upper()}', fontsize=16, fontweight='bold')

        for i, algo in enumerate(algorithms):
            ax = axes[i]
            data_scen_algo = df_curves[(df_curves['Scenario'] == scenario) & (df_curves['Algorithm'] == algo)].copy()
            
            if data_scen_algo.empty:
                ax.text(0.5, 0.5, 'Sem dados', horizontalalignment='center', verticalalignment='center')
                ax.set_title(algo)
                continue

            # Desenha as runs individuais de fundo
            sns.lineplot(data=data_scen_algo, x='Step', y='Score', hue='Run', palette='Greys', alpha=0.3, legend=False, ax=ax)
            
            # Calcula e desenha a média suavizada
            data_scen_algo['Score_Suavizado'] = data_scen_algo.groupby('Run')['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
            mean_data = data_scen_algo.groupby('Step')['Score_Suavizado'].mean().reset_index()
            sns.lineplot(data=mean_data, x='Step', y='Score_Suavizado', color=cores.get(algo, 'black'), linewidth=2.5, label=f'Média ({algo})', ax=ax)
            
            ax.set_title(f'Algoritmo: {algo}', fontsize=14)
            ax.set_ylabel('Score')
            ax.legend()

        axes[0].set_xlabel('Timesteps')
        axes[1].set_xlabel('Timesteps')
        axes[2].set_xlabel('Timesteps')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajustar para o supertítulo
        plt.savefig(os.path.join(final_dir, f'comparativo_subplots_{scenario}.png'), dpi=300)
        plt.close()

    # --- GRÁFICOS ANTIGOS (Mantidos para referência) ---

    print(" -> Gráfico Global (Barras)...")
    plt.figure(figsize=(14, 7))
    df_best_log = df_best.copy()
    df_best_log['BestScore_Log'] = np.maximum(df_best_log['BestScore'], 1)
    ax = sns.barplot(data=df_best_log, x='Scenario', y='BestScore_Log', hue='Algorithm', errorbar='sd', palette=cores, capsize=.1)
    ax.set_yscale("log")
    plt.title('Comparação Global de Desempenho (Escala Logarítmica)', fontweight='bold', fontsize=16)
    plt.ylabel('Score Máximo Atingido (Escala Log)', fontsize=14)
    plt.xlabel('Cenários', fontsize=14)
    plt.xticks(rotation=15)
    plt.legend(title='Algoritmo', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(final_dir, 'comparacao_barras_geral_log.png'), dpi=300)
    plt.close()

    print(" -> Boxplots por cenário...")
    for scenario in scenarios:
        plt.figure(figsize=(8, 6))
        data_scen = df_best[df_best['Scenario'] == scenario]
        sns.boxplot(data=data_scen, x='Algorithm', y='BestScore', hue='Algorithm', palette=cores, width=0.5, fliersize=5)
        plt.title(f'Distribuição de Melhores Scores\nCenário: {scenario.upper()}', fontweight='bold', fontsize=14)
        plt.ylabel('Score Máximo', fontsize=12)
        plt.xlabel('Algoritmo', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'boxplot_{scenario}.png'), dpi=300)
        plt.close()

    print(" -> Curvas de Aprendizagem (Escala Linear)...")
    for scenario in scenarios:
        plt.figure(figsize=(10, 6))
        data_scen = df_curves[df_curves['Scenario'] == scenario].copy()
        data_scen['Score_Suavizado'] = data_scen.groupby(['Algorithm', 'Run'])['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
        sns.lineplot(data=data_scen, x='Step', y='Score_Suavizado', hue='Algorithm', palette=cores, errorbar='ci', n_boot=1000)
        plt.title(f'Curvas de Aprendizagem (Escala Linear) - Cenário: {scenario.upper()}', fontweight='bold', fontsize=14)
        plt.ylabel('Score', fontsize=12)
        plt.xlabel('Timesteps', fontsize=12)
        plt.legend(title='Algoritmo')
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'curva_linear_{scenario}.png'), dpi=300)
        plt.close()

    print(f"\n✅ Concluído! A abrir a pasta com os novos gráficos:\n{final_dir}")
    
    if os.name == 'nt':
        os.startfile(final_dir)

if __name__ == '__main__':
    try:
        update_latest_thesis_plots()
    except Exception as e:
        print(f"\n[!] Ocorreu um erro ao gerar os gráficos: {e}")
        
    input("\nPressione ENTER para fechar esta janela...")