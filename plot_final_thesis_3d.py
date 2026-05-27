import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from datetime import datetime
import shutil

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def create_thesis_plots_3d():
    print("\n A gerar os Graficos de Tese Avancados...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stats_dir = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas')
    
    now = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
    output_dir = os.path.join(base_dir, 'results', 'graficos_tese', now)
    os.makedirs(output_dir, exist_ok=True)
    
    curves_csv = os.path.join(stats_dir, 'all_curves_data.csv')
    best_csv = os.path.join(stats_dir, 'all_best_scores.csv')
    
    if os.path.exists(curves_csv):
        df_curves = pd.read_csv(curves_csv)
        sns.set_theme(style="whitegrid")
        
        # ==============================================================
        # 1. Gráficos "1 MAPA, 3 MODELOS" (Curvas de Aprendizagem)
        # ==============================================================
        palette_models = {'GNN': '#2E7D32', 'PPO': '#E65100', 'SAC': '#0277BD'}
        scenarios = df_curves['Scenario'].unique()
        print(f"[*] Encontrados dados de {len(scenarios)} cenários no Treino Noturno.")
        
        for scenario in scenarios:
            df_scen = df_curves[df_curves['Scenario'] == scenario].copy()
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=df_scen, x='Step', y='Score', hue='Algorithm', 
                         palette=palette_models, linewidth=2.5, errorbar='sd')
            
            plt.title(f'Comparacao de Desempenho - {scenario.upper()}', fontsize=16, fontweight='bold')
            plt.xlabel('Timesteps / Geracao', fontsize=12)
            plt.ylabel('Recompensa (Score)', fontsize=12)
            plt.legend(title="Modelo", loc='lower right', fontsize=11)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            out_path = os.path.join(output_dir, f'comparacao_mapa_{scenario}.png')
            plt.savefig(out_path, dpi=300)
            plt.close()
            print(f"[*] Gerado grafico: 3 Modelos no mapa {scenario}")
            
        # ==============================================================
        # 2. Gráficos "1 MODELO, TODOS OS MAPAS" (Curvas de Aprendizagem)
        # ==============================================================
        algorithms = df_curves['Algorithm'].unique()
        # Paleta para diferenciar os mapas (ate 10 mapas suportados)
        palette_scenarios = sns.color_palette("husl", len(scenarios))
        
        for algo in algorithms:
            df_algo = df_curves[df_curves['Algorithm'] == algo].copy()
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=df_algo, x='Step', y='Score', hue='Scenario', 
                         palette=palette_scenarios, linewidth=2.5, errorbar='sd')
            
            plt.title(f'Desempenho Global do Algoritmo: {algo.upper()}', fontsize=16, fontweight='bold')
            plt.xlabel('Timesteps / Geracao', fontsize=12)
            plt.ylabel('Recompensa (Score)', fontsize=12)
            plt.legend(title="Cenario", loc='lower right', fontsize=11, bbox_to_anchor=(1.0, 0.0))
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            out_path = os.path.join(output_dir, f'desempenho_global_{algo.lower()}.png')
            plt.savefig(out_path, dpi=300)
            plt.close()
            print(f"[*] Gerado grafico: {algo} em todos os mapas")

        # Copy info files
        config_src = os.path.join(base_dir, 'configs', 'foraging.yaml')
        if os.path.exists(config_src):
            shutil.copy(config_src, os.path.join(output_dir, 'info_treino.yaml'))
        shutil.copy(curves_csv, os.path.join(output_dir, 'dados_historicos.csv'))
    else:
        print("[!] Ficheiro 'all_curves_data.csv' nao encontrado!")

    # ==============================================================
    # 3. BOXPLOTS e 4. BARRAS AGREGADORAS (Melhores Scores)
    # ==============================================================
    if os.path.exists(best_csv):
        df_best = pd.read_csv(best_csv)
        sns.set_theme(style="whitegrid")
        palette_models = {'GNN': '#2E7D32', 'PPO': '#E65100', 'SAC': '#0277BD'}
        
        # 3. Boxplots por Mapa
        for scenario in df_best['Scenario'].unique():
            df_scen = df_best[df_best['Scenario'] == scenario].copy()
            plt.figure(figsize=(8, 6))
            sns.boxplot(data=df_scen, x='Algorithm', y='BestScore', palette=palette_models)
            plt.title(f'Fiabilidade (Distribuição de Max Scores) - {scenario.upper()}', fontsize=14, fontweight='bold')
            plt.ylabel('Melhor Recompensa Final')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'boxplot_{scenario}.png'), dpi=300)
            plt.close()
            print(f"[*] Gerado Boxplot para o mapa: {scenario}")
            
        # 4. Gráfico de Barras Agregador
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df_best, x='Scenario', y='BestScore', hue='Algorithm', errorbar='sd', palette=palette_models)
        plt.title('A Batalha Final: Resumo de Recompensa Máxima por Mapa', fontsize=16, fontweight='bold')
        plt.ylabel('Recompensa Maxima Media (com Desvio Padrao)')
        plt.xlabel('Cenario (Mapa)')
        plt.legend(title="Modelo", loc='upper right')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'comparacao_barras_geral.png'), dpi=300)
        plt.close()
        print("[*] Gerado Grafico de Barras Agregador")
        
        shutil.copy(best_csv, os.path.join(output_dir, 'dados_melhores_scores.csv'))
    else:
        print("[!] Ficheiro 'all_best_scores.csv' nao encontrado para fazer Boxplots!")
        # Fallback original
        gnn_csv = os.path.join(base_dir, 'results', 'logs', 'gnn_3d_training.csv')
        ppo_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_ppo_3d.csv')
        sac_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_sac_3d.csv')
        
        plt.figure(figsize=(10, 6))
        for p, label, col in [(gnn_csv, 'GNN', '#2E7D32'), (ppo_csv, 'PPO', '#E65100'), (sac_csv, 'SAC', '#0277BD')]:
            if os.path.exists(p):
                df = pd.read_csv(p)
                df.columns = df.columns.str.strip()
                y_col = 'best_fitness' if 'best' in df.columns[1] else df.columns[1]
                if len(df) > 1 and y_col in df.columns:
                    x_col = df.columns[0]
                    plt.plot(df[x_col], df[y_col].rolling(10, min_periods=1).mean(), color=col, linewidth=2.5, label=label)
        
        plt.title('Batalha de Algoritmos (Fallback Ultima Run)', fontsize=16, fontweight='bold')
        plt.xlabel('Timesteps', fontsize=12)
        plt.ylabel('Score (Suavizado)', fontsize=12)
        plt.legend(loc='lower right')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'fallback_comparacao.png'), dpi=300)
        plt.close()
        
    print(f"\n[*] Concluido! Graficos guardados em: {output_dir}")
    
    if os.name == 'nt':
        os.startfile(output_dir)

if __name__ == "__main__":
    import traceback

    try:
        create_thesis_plots_3d()
    except Exception as e:
        print("\n[!] CRASH FATAL! Erro ao gerar os graficos:")
        traceback.print_exc()
    finally:
        input("\n[*] Pressiona ENTER para fechar a janela...")