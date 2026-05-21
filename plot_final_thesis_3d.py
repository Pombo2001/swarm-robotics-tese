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
    # Formato: 07-05-2026_09h55m_...
    try:
        date_str = folder_name[:17]
        return datetime.strptime(date_str, "%d-%m-%Y_%Hh%Mm")
    except:
        # Se falhar o parse, devolve uma data muito antiga para não ser escolhida
        return datetime.min

def update_latest_thesis_plots():
    print("A procurar o último treino completo realizado...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stats_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas')
    
    if not os.path.exists(stats_dir):
        print(f"Erro: A pasta de estatísticas ({stats_dir}) não existe.")
        input("\nPressione ENTER para sair...")
        return
        
    # Encontrar todas as subpastas em estatisticas
    dirs = [d for d in os.listdir(stats_dir) if os.path.isdir(os.path.join(stats_dir, d))]
    
    if not dirs:
        print("Erro: Ainda não existem treinos gerados.")
        input("\nPressione ENTER para sair...")
        return
        
    # Lógica CORRIGIDA: Usa a data escrita no nome da pasta para encontrar a mais recente
    # Isto garante que abre SEMPRE a última, independentemente de quando o Windows modificou os ficheiros
    latest_folder_name = max(dirs, key=parse_folder_date)
    latest_dir = os.path.join(stats_dir, latest_folder_name)
    
    print(f"Pasta de treino mais recente encontrada: {latest_folder_name}")
    
    csv_scores = os.path.join(latest_dir, 'all_best_scores.csv')
    csv_curves = os.path.join(latest_dir, 'all_curves_data.csv')
    
    # --- DESTINO CORRETO (finais_pdf) ---
    final_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'finais_pdf', latest_folder_name)
    os.makedirs(final_dir, exist_ok=True)
    
    if not os.path.exists(csv_scores) or not os.path.exists(csv_curves):
        print("Os ficheiros CSV não foram encontrados nesta pasta. A abrir a pasta de qualquer forma...")
        if os.name == 'nt':
            os.startfile(final_dir)
        return

    print("A re-gerar os gráficos limpos com base nos dados deste treino...")
    df_best = pd.read_csv(csv_scores)
    df_curves = pd.read_csv(csv_curves)

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    cores = {'GNN': '#2ca02c', 'PPO': '#ff7f0e', 'SAC': '#1f77b4'} # Verde, Laranja, Azul Clássico

    scenarios = df_best['Scenario'].unique()
    algorithms = df_best['Algorithm'].unique()

    print(" -> Gráfico Global...")
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
        plt.title(f'Distribuição de Melhores Scores\n(Cenário: {scenario.upper()})', fontweight='bold', fontsize=14)
        plt.ylabel('Score Máximo', fontsize=12)
        plt.xlabel('Algoritmo', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'boxplot_{scenario}.png'), dpi=300)
        plt.close()

    print(" -> Curvas de Aprendizagem Globais...")
    for scenario in scenarios:
        plt.figure(figsize=(10, 6))
        data_scen = df_curves[df_curves['Scenario'] == scenario].copy()
        
        # Suavizar as curvas
        data_scen['Score_Suavizado'] = data_scen.groupby(['Algorithm', 'Run'])['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
        
        sns.lineplot(data=data_scen, x='Step', y='Score_Suavizado', hue='Algorithm', palette=cores, errorbar='ci', n_boot=1000)
        
        plt.title(f'Curvas de Aprendizagem Média Suavizada\n(Cenário: {scenario.upper()})', fontweight='bold', fontsize=14)
        plt.ylabel('Score Absoluto', fontsize=12)
        plt.xlabel('Timesteps Simulação', fontsize=12)
        plt.legend(title='Algoritmo')
        plt.tight_layout()
        plt.savefig(os.path.join(final_dir, f'curva_aprendizagem_suavizada_{scenario}.png'), dpi=300)
        plt.close()

    print(" -> Gráficos INDIVIDUAIS por Algoritmo (Bruto vs Média)...")
    indiv_dir = os.path.join(final_dir, 'individuais')
    os.makedirs(indiv_dir, exist_ok=True)
    
    for scenario in scenarios:
        for algo in algorithms:
            plt.figure(figsize=(8, 5))
            data_scen_algo = df_curves[(df_curves['Scenario'] == scenario) & (df_curves['Algorithm'] == algo)].copy()
            
            if data_scen_algo.empty:
                continue
                
            # Desenha as runs brutas em pano de fundo (cinzento/claro)
            sns.lineplot(data=data_scen_algo, x='Step', y='Score', hue='Run', palette='Greys', alpha=0.3, legend=False)
            
            # Calcula a média suavizada
            data_scen_algo['Score_Suavizado'] = data_scen_algo.groupby('Run')['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
            mean_data = data_scen_algo.groupby('Step')['Score_Suavizado'].mean().reset_index()
            
            # Desenha a linha média destacada
            sns.lineplot(data=mean_data, x='Step', y='Score_Suavizado', color=cores.get(algo, 'black'), linewidth=2.5, label=f'Média de {len(data_scen_algo["Run"].unique())} Runs')
            
            plt.title(f'Desempenho {algo} - Cenário: {scenario.upper()}', fontweight='bold')
            plt.ylabel('Score')
            plt.xlabel('Timesteps')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(indiv_dir, f'desempenho_{algo}_{scenario}.png'), dpi=300)
            plt.close()

    print(f"\n✅ Concluído! A abrir a pasta com os novos gráficos:\n{final_dir}")
    
    if os.name == 'nt':
        os.startfile(final_dir)

if __name__ == '__main__':
    try:
        update_latest_thesis_plots()
    except Exception as e:
        print(f"\n[!] Ocorreu um erro fatal ao gerar os gráficos: {e}")
        
    input("\nPressione ENTER para fechar esta janela...")