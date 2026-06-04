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

SCENARIO_LABELS_PT = {
    "none":                    "Sandbox (Arena Aberta)",
    "u_wall":                  "Beco Sem Saída (Muro U)",
    "bottleneck":              "Gargalo (Porta Estreita)",
    "four_rooms":              "Quatro Salas (Labirinto)",
    "cooperative_door":        "Porta Cooperativa (3 Robôs)",
    "cooperative_perception":  "Perceção Cooperativa (Alvo Móvel)",
}

MAP_DESCRIPTIONS = {
    "none":
        "Arena aberta sem obstáculos fixos. O ninho é móvel e há obstáculos dinâmicos.\n"
        "Avalia a capacidade base de forrageamento e orientação.",
    "u_wall":
        "Um muro em U bloqueia o caminho direto ao ninho (topo da arena).\n"
        "Exige que os agentes aprendam a explorar lateralmente.",
    "bottleneck":
        "Duas paredes criam uma passagem estreita de 1,5m no centro.\n"
        "Testa gestão de congestionamento e fluxo cooperativo.",
    "four_rooms":
        "Labirinto de quatro salas com passagens específicas.\n"
        "Avalia navegação estruturada e memória espacial.",
    "cooperative_door":
        "Uma porta bloqueada que só abre quando 3 robôs a empurram em simultâneo.\n"
        "Testa coordenação emergente sem comunicação explícita.",
    "cooperative_perception":
        "Um alvo móvel que só é capturado quando rodeado por 3+ robôs a 360°.\n"
        "Avalia perseguição e encirclement cooperativo.",
}

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
            label_pt = SCENARIO_LABELS_PT.get(scenario, scenario.upper())
            desc     = MAP_DESCRIPTIONS.get(scenario, "")

            fig, ax = plt.subplots(figsize=(11, 7))
            sns.lineplot(data=df_scen, x='Step', y='Score', hue='Algorithm',
                         palette=palette_models, linewidth=2.5, errorbar='sd', ax=ax)

            ax.set_title(f'Comparação de Desempenho — {label_pt}',
                         fontsize=15, fontweight='bold', pad=14)
            ax.set_xlabel('Timesteps (PPO/SAC)  /  Gerações × Passos (GNN)', fontsize=11)
            ax.set_ylabel('Recompensa Média por Episódio', fontsize=11)
            ax.legend(title="Algoritmo", loc='lower right', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.5)

            if desc:
                fig.text(0.5, 0.01, desc, ha='center', va='bottom',
                         fontsize=9, color='#555555',
                         style='italic', wrap=True)
                fig.subplots_adjust(bottom=0.14)

            plt.tight_layout(rect=[0, 0.10, 1, 1])
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
        
        algo_descs = {
            "GNN": "Algoritmo Evolutivo com Rede Neuronal de Grafos e atenção sobre vizinhos.\n"
                   "A fitness é a média de 2 episódios; cada geração avalia 30 genomas em paralelo.",
            "PPO": "Proximal Policy Optimization — método on-policy Actor-Critic com parameter sharing.\n"
                   "Todos os 20 agentes partilham a mesma rede, atualizada com PPO clipped objective.",
            "SAC": "Soft Actor-Critic — método off-policy com entropia regularizada.\n"
                   "Mantém um replay buffer e aprende de experiências passadas de forma mais eficiente.",
        }

        for algo in algorithms:
            df_algo = df_curves[df_curves['Algorithm'] == algo].copy()
            # Rename scenarios for readability in legend
            df_algo = df_algo.copy()
            df_algo['Scenario'] = df_algo['Scenario'].map(
                lambda s: SCENARIO_LABELS_PT.get(s, s))

            fig, ax = plt.subplots(figsize=(12, 7))
            sns.lineplot(data=df_algo, x='Step', y='Score', hue='Scenario',
                         palette=palette_scenarios, linewidth=2.5, errorbar='sd', ax=ax)

            ax.set_title(f'Desempenho Global — {algo.upper()}',
                         fontsize=15, fontweight='bold', pad=14)
            ax.set_xlabel('Timesteps (PPO/SAC)  /  Gerações × Passos (GNN)', fontsize=11)
            ax.set_ylabel('Recompensa Média por Episódio', fontsize=11)
            ax.legend(title="Cenário", loc='lower right', fontsize=10,
                      bbox_to_anchor=(1.02, 0.0), borderaxespad=0)
            ax.grid(True, linestyle='--', alpha=0.5)

            desc = algo_descs.get(algo, "")
            if desc:
                fig.text(0.5, 0.01, desc, ha='center', va='bottom',
                         fontsize=9, color='#555555', style='italic')
                fig.subplots_adjust(bottom=0.14)

            plt.tight_layout(rect=[0, 0.10, 1, 1])
            out_path = os.path.join(output_dir, f'desempenho_global_{algo.lower()}.png')
            plt.savefig(out_path, dpi=300, bbox_inches='tight')
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
            label_pt = SCENARIO_LABELS_PT.get(scenario, scenario.upper())
            desc     = MAP_DESCRIPTIONS.get(scenario, "")

            fig, ax = plt.subplots(figsize=(8, 6))
            sns.boxplot(data=df_scen, x='Algorithm', y='BestScore',
                        palette=palette_models, ax=ax)
            ax.set_title(f'Fiabilidade — {label_pt}',
                         fontsize=14, fontweight='bold', pad=12)
            ax.set_ylabel('Melhor Recompensa Obtida (por run)', fontsize=11)
            ax.set_xlabel('Algoritmo', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.4, axis='y')

            caption = ("Cada caixa representa 5 runs independentes. "
                       "A linha central é a mediana; a caixa cobre IQR 25–75%.")
            if desc:
                caption = desc.replace('\n', ' ') + "  |  " + caption
            fig.text(0.5, 0.01, caption, ha='center', va='bottom',
                     fontsize=8.5, color='#555555', style='italic')
            fig.subplots_adjust(bottom=0.12)

            plt.tight_layout(rect=[0, 0.08, 1, 1])
            plt.savefig(os.path.join(output_dir, f'boxplot_{scenario}.png'), dpi=300)
            plt.close()
            print(f"[*] Gerado Boxplot para o mapa: {scenario}")

        # 4. Gráfico de Barras Agregador
        df_best_labeled = df_best.copy()
        df_best_labeled['Scenario'] = df_best_labeled['Scenario'].map(
            lambda s: SCENARIO_LABELS_PT.get(s, s))

        fig, ax = plt.subplots(figsize=(14, 7))
        sns.barplot(data=df_best_labeled, x='Scenario', y='BestScore',
                    hue='Algorithm', errorbar='sd',
                    palette=palette_models, ax=ax)
        ax.set_title('Resumo Geral — Melhor Recompensa por Algoritmo e Cenário',
                     fontsize=15, fontweight='bold', pad=14)
        ax.set_ylabel('Recompensa Máxima Média (± Desvio Padrão entre runs)', fontsize=11)
        ax.set_xlabel('Cenário', fontsize=11)
        ax.legend(title="Algoritmo", loc='upper right', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.4, axis='y')
        plt.xticks(rotation=18, ha='right', fontsize=10)

        fig.text(0.5, 0.01,
                 "Cada barra é a média do melhor score por run (N=5). "
                 "Barras de erro representam o desvio padrão entre runs independentes. "
                 "GNN usa fitness evolutiva; PPO e SAC usam recompensa episódica.",
                 ha='center', va='bottom', fontsize=9, color='#555555', style='italic')
        fig.subplots_adjust(bottom=0.14)

        plt.tight_layout(rect=[0, 0.09, 1, 1])
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