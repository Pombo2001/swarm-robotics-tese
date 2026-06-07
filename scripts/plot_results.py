import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import os
import sys
from datetime import datetime
import shutil

# Windows: evita UnicodeEncodeError (cp1252) ao imprimir caracteres de caixa.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Force a Unicode-capable font on Windows to avoid encoding errors with
# accented characters (ó, é, etc.) and math symbols (±, ×, →).
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
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
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
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
        # 1. Gráficos "1 MAPA, 3 MODELOS" — eixo X normalizado [0→100%]
        #    Cada algoritmo tem unidades diferentes (GNN: passos evolutivos;
        #    PPO/SAC: timesteps de política). Normalizar para progresso relativo
        #    permite comparação justa na mesma figura.
        # ==============================================================
        palette_models = {'GNN': '#2E7D32', 'PPO': '#E65100', 'SAC': '#0277BD'}
        scenarios = df_curves['Scenario'].unique()
        print(f"[*] Encontrados dados de {len(scenarios)} cenários no Treino Noturno.")

        # Normalizar Step → TrainingProgress [0, 100] por (Scenario, Algorithm, Run)
        df_curves = df_curves.copy()
        step_stats = df_curves.groupby(['Scenario', 'Algorithm', 'Run'])['Step'].agg(['min', 'max'])
        step_stats.columns = ['step_min', 'step_max']
        df_curves = df_curves.join(step_stats, on=['Scenario', 'Algorithm', 'Run'])
        rng = df_curves['step_max'] - df_curves['step_min']
        df_curves['TrainingProgress'] = (df_curves['Step'] - df_curves['step_min']) / rng.clip(lower=1) * 100
        df_curves = df_curves.drop(columns=['step_min', 'step_max'])

        for scenario in scenarios:
            df_scen = df_curves[df_curves['Scenario'] == scenario].copy()
            label_pt = SCENARIO_LABELS_PT.get(scenario, scenario.upper())
            desc     = MAP_DESCRIPTIONS.get(scenario, "")

            fig, ax = plt.subplots(figsize=(11, 7))
            sns.lineplot(data=df_scen, x='TrainingProgress', y='Score', hue='Algorithm',
                         palette=palette_models, linewidth=2.5, errorbar='sd', ax=ax)

            ax.set_title(f'Comparação de Desempenho — {label_pt}',
                         fontsize=15, fontweight='bold', pad=14)
            ax.set_xlabel('Progresso do Treino (%)', fontsize=11)
            ax.set_ylabel('Recompensa Média por Episódio', fontsize=11)
            ax.set_xlim(0, 100)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))
            ax.legend(title="Algoritmo", loc='lower right', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.5)

            caption = ("Eixo X normalizado (0%→100% do treino de cada algoritmo) para comparação justa. "
                       "GNN: fitness evolutiva; PPO/SAC: recompensa episódica.")
            if desc:
                caption = desc.replace('\n', ' ') + "  |  " + caption
            fig.text(0.5, 0.01, caption, ha='center', va='bottom',
                     fontsize=8.5, color='#555555', style='italic')
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
                   "A fitness é a média de 3 episódios; cada geração avalia 30 genomas em paralelo.",
            "PPO": "Proximal Policy Optimization — método on-policy Actor-Critic com parameter sharing.\n"
                   "Todos os 20 agentes partilham a mesma rede, atualizada com PPO clipped objective.",
            "SAC": "Soft Actor-Critic — método off-policy com entropia regularizada.\n"
                   "Mantém um replay buffer e aprende de experiências passadas de forma mais eficiente.",
        }

        for algo in algorithms:
            df_algo = df_curves[df_curves['Algorithm'] == algo].copy()
            df_algo['Scenario'] = df_algo['Scenario'].map(
                lambda s: SCENARIO_LABELS_PT.get(s, s))

            fig, ax = plt.subplots(figsize=(12, 7))
            # Para gráficos intra-algoritmo usar TrainingProgress (já calculado acima)
            sns.lineplot(data=df_algo, x='TrainingProgress', y='Score', hue='Scenario',
                         palette=palette_scenarios, linewidth=2.5, errorbar='sd', ax=ax)

            ax.set_title(f'Desempenho Global — {algo.upper()}',
                         fontsize=15, fontweight='bold', pad=14)
            ax.set_xlabel('Progresso do Treino (%)', fontsize=11)
            ax.set_ylabel('Recompensa Média por Episódio', fontsize=11)
            ax.set_xlim(0, 100)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))
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
        print("[!] Para gerar graficos completos usa a Rotina Noturna (run_experiments.py).")
        print("[i] A tentar fallback com logs individuais...")

    # ==============================================================
    # 3. BOXPLOTS e 4. BARRAS AGREGADORAS (Melhores Scores)
    # ==============================================================
    if os.path.exists(best_csv):
        df_best = pd.read_csv(best_csv)
        sns.set_theme(style="whitegrid")
        palette_models = {'GNN': '#2E7D32', 'PPO': '#E65100', 'SAC': '#0277BD'}
        
        # 3a. Boxplots por Mapa (um por cenário, algoritmos lado a lado)
        # NOTA: GNN usa fitness evolutiva; PPO/SAC usam recompensa episódica.
        # São métricas diferentes — as escalas não são directamente comparáveis.
        for scenario in df_best['Scenario'].unique():
            df_scen = df_best[df_best['Scenario'] == scenario].copy()
            label_pt = SCENARIO_LABELS_PT.get(scenario, scenario.upper())
            desc     = MAP_DESCRIPTIONS.get(scenario, "")

            fig, ax = plt.subplots(figsize=(8, 6))
            sns.boxplot(data=df_scen, x='Algorithm', y='BestScore',
                        palette=palette_models, ax=ax)
            ax.set_title(f'Fiabilidade — {label_pt}',
                         fontsize=14, fontweight='bold', pad=12)
            ax.set_ylabel('Melhor Score por Run (escala varia por algoritmo)', fontsize=10)
            ax.set_xlabel('Algoritmo', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.4, axis='y')

            caption = ("ATENCAO: GNN usa fitness evolutiva; PPO/SAC usam recompensa episodica "
                       "(escalas diferentes). Cada caixa = 5 runs independentes, mediana + IQR 25-75%.")
            if desc:
                caption = desc.replace('\n', ' ') + "  |  " + caption
            fig.text(0.5, 0.01, caption, ha='center', va='bottom',
                     fontsize=8, color='#AA5500', style='italic')
            fig.subplots_adjust(bottom=0.13)
            plt.tight_layout(rect=[0, 0.09, 1, 1])
            plt.savefig(os.path.join(output_dir, f'boxplot_{scenario}.png'), dpi=300)
            plt.close()
            print(f"[*] Boxplot por mapa: {scenario}")

        # 3b. Boxplots por Algoritmo (um por algo, cenários lado a lado)
        # Comparação intra-algoritmo: qual cenário é mais difícil para cada modelo?
        scenario_order = [s for s in
            ['none','u_wall','bottleneck','four_rooms','cooperative_door','cooperative_perception']
            if s in df_best['Scenario'].unique()]
        scenario_labels_short = {
            'none': 'Sandbox', 'u_wall': 'U-Wall', 'bottleneck': 'Gargalo',
            'four_rooms': '4 Salas', 'cooperative_door': 'Porta Coop.',
            'cooperative_perception': 'Percepcao',
        }
        algo_ylabels = {
            'GNN': 'Fitness Evolutiva (melhor genoma)',
            'PPO': 'Recompensa Episodica (melhor run)',
            'SAC': 'Recompensa Episodica (melhor run)',
        }
        for algo in ['GNN', 'PPO', 'SAC']:
            df_algo = df_best[df_best['Algorithm'] == algo].copy()
            if df_algo.empty:
                continue
            df_algo['ScenLabel'] = df_algo['Scenario'].map(
                lambda s: scenario_labels_short.get(s, s))
            ordered = [scenario_labels_short.get(s, s) for s in scenario_order
                       if s in df_algo['Scenario'].values]

            fig, ax = plt.subplots(figsize=(11, 6))
            sns.boxplot(data=df_algo, x='ScenLabel', y='BestScore',
                        order=ordered,
                        color=palette_models.get(algo, '#888888'), ax=ax)
            ax.set_title(f'{algo} — Desempenho por Cenario (5 runs cada)',
                         fontsize=14, fontweight='bold', pad=12)
            ax.set_ylabel(algo_ylabels.get(algo, 'Score'), fontsize=11)
            ax.set_xlabel('Cenario', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.4, axis='y')
            plt.xticks(rotation=15, ha='right')
            fig.text(0.5, 0.01,
                     "Comparacao intra-algoritmo: mostra qual cenario e mais dificil para "
                     f"o {algo}. Escala consistente dentro do algoritmo.",
                     ha='center', va='bottom', fontsize=8.5, color='#555555', style='italic')
            fig.subplots_adjust(bottom=0.14)
            plt.tight_layout(rect=[0, 0.09, 1, 1])
            plt.savefig(os.path.join(output_dir, f'boxplot_por_algo_{algo.lower()}.png'), dpi=300)
            plt.close()
            print(f"[*] Boxplot por algoritmo: {algo}")

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
        # Fallback: plot individual training logs if available
        gnn_csv = os.path.join(base_dir, 'results', 'logs', 'gnn_3d_training.csv')
        ppo_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_ppo_3d.csv')
        sac_csv = os.path.join(base_dir, 'results', 'logs_sac', 'training_history_sac_3d.csv')

        # (path, label, cor, coluna_y, coluna_task)
        ALGO_LOGS = [
            (gnn_csv, 'GNN', '#2E7D32', 'best_fitness',  None),
            (ppo_csv, 'PPO', '#E65100', 'ep_rew_mean',   'ep_task_mean'),
            (sac_csv, 'SAC', '#0277BD', 'ep_rew_mean',   'ep_task_mean'),
        ]

        # ── Gráfico 1: por TIMESTEPS (eixo X = amostras) ─────────────────────
        fig, ax = plt.subplots(figsize=(11, 6))
        plotted = 0
        for path_log, label, col, y_col, _ in ALGO_LOGS:
            if not os.path.exists(path_log):
                continue
            try:
                df = pd.read_csv(path_log)
                df.columns = df.columns.str.strip()
                x_col = df.columns[0]   # primeira coluna = timesteps/timestep
                if y_col not in df.columns or len(df) < 2:
                    continue
                smoothed = df[y_col].rolling(10, min_periods=1).mean()
                ax.plot(df[x_col], smoothed, color=col, linewidth=2.5, label=label)
                plotted += 1
            except Exception as e:
                print(f"[!] Erro ao ler {path_log}: {e}")

        if plotted == 0:
            ax.text(0.5, 0.5, "Sem dados de treino.\nCorre pelo menos um algoritmo primeiro.",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='#6B7280')
        else:
            ax.legend(loc='lower right', fontsize=11)

        ax.set_title('Comparacao de Algoritmos — Recompensa por Timestep', fontsize=14, fontweight='bold')
        ax.set_xlabel('Timesteps / Geracoes x Passos (GNN)', fontsize=11)
        ax.set_ylabel('Recompensa total (suavizada 10pt)', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.5)
        fig.text(0.5, 0.01,
                 "NOTA: eixos X nao sao directamente comparaveis entre GNN (passos de simulacao) "
                 "e PPO/SAC (passos de politica).",
                 ha='center', va='bottom', fontsize=8.5, color='#6B7280', style='italic')
        fig.subplots_adjust(bottom=0.10)
        plt.tight_layout(rect=[0, 0.07, 1, 1])
        plt.savefig(os.path.join(output_dir, 'fallback_comparacao_timesteps.png'), dpi=300)
        plt.close()
        print(f"[i] Grafico por timesteps guardado ({plotted} algo(s))")

        # ── Gráfico 2: por TEMPO REAL (eixo X = minutos) ─────────────────────
        # Comparacao justa: todos correm no mesmo hardware e o eixo e tempo de parede.
        fig, ax = plt.subplots(figsize=(11, 6))
        plotted_time = 0
        for path_log, label, col, y_col, _ in ALGO_LOGS:
            if not os.path.exists(path_log):
                continue
            try:
                df = pd.read_csv(path_log)
                df.columns = df.columns.str.strip()
                if 'time' not in df.columns or y_col not in df.columns or len(df) < 2:
                    continue
                minutes  = df['time'] / 60.0
                smoothed = df[y_col].rolling(10, min_periods=1).mean()
                ax.plot(minutes, smoothed, color=col, linewidth=2.5, label=label)
                plotted_time += 1
            except Exception as e:
                print(f"[!] Erro ao ler (time) {path_log}: {e}")

        if plotted_time > 0:
            ax.legend(loc='lower right', fontsize=11)
            ax.set_title('Comparacao de Algoritmos — Recompensa por Tempo Real',
                         fontsize=14, fontweight='bold')
            ax.set_xlabel('Tempo de treino (minutos)', fontsize=11)
            ax.set_ylabel('Recompensa total (suavizada 10pt)', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.5)
            fig.text(0.5, 0.01,
                     "Comparacao por tempo de parede (wall-clock): eixo X identico para todos os algoritmos. "
                     "Mais justo para a tese do que comparar por timesteps.",
                     ha='center', va='bottom', fontsize=8.5, color='#6B7280', style='italic')
            fig.subplots_adjust(bottom=0.10)
            plt.tight_layout(rect=[0, 0.07, 1, 1])
            plt.savefig(os.path.join(output_dir, 'fallback_comparacao_tempo.png'), dpi=300)
            print(f"[i] Grafico por tempo real guardado ({plotted_time} algo(s))")
        plt.close()

        # ── Gráfico 3: TASK REWARD (recolhas puras, sem shaping) ─────────────
        fig, ax = plt.subplots(figsize=(11, 6))
        plotted_task = 0
        for path_log, label, col, _, task_col in ALGO_LOGS:
            if task_col is None or not os.path.exists(path_log):
                continue
            try:
                df = pd.read_csv(path_log)
                df.columns = df.columns.str.strip()
                if task_col not in df.columns or 'time' not in df.columns or len(df) < 2:
                    continue
                minutes  = df['time'] / 60.0
                smoothed = df[task_col].rolling(10, min_periods=1).mean()
                ax.plot(minutes, smoothed, color=col, linewidth=2.5, label=label)
                plotted_task += 1
            except Exception as e:
                print(f"[!] Erro ao ler (task) {path_log}: {e}")

        if plotted_task > 0:
            ax.legend(loc='lower right', fontsize=11)
            ax.set_title('Task Reward — Recompensa de Tarefa Pura (sem shaping)',
                         fontsize=14, fontweight='bold')
            ax.set_xlabel('Tempo de treino (minutos)', fontsize=11)
            ax.set_ylabel('Recompensa de tarefa (food x 100)', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.5)
            fig.text(0.5, 0.01,
                     "Apenas a recompensa de recolha (food_collected x 100), sem bónus de progresso. "
                     "Pedido pelo orientador para comparar com avaliacao de teste.",
                     ha='center', va='bottom', fontsize=8.5, color='#6B7280', style='italic')
            fig.subplots_adjust(bottom=0.10)
            plt.tight_layout(rect=[0, 0.07, 1, 1])
            plt.savefig(os.path.join(output_dir, 'fallback_task_reward.png'), dpi=300)
            print(f"[i] Grafico task reward guardado ({plotted_task} algo(s))")
        plt.close()
        print(f"[i] Total: {max(plotted, plotted_time, plotted_task)} algoritmo(s) com dados")
        
    # ==============================================================
    # 5. GRÁFICOS DE AVALIAÇÃO (métricas de TAREFA por cenário)
    #    Taxa de sucesso (Ptask) + recolhas/ep — honestos e comparáveis entre
    #    algoritmos, ao contrário do reward de treino (shaping + escalas mistas).
    #    Lê results/evaluation/eval_summary.csv (gerado pela rotina/eval_suite).
    # ==============================================================
    try:
        from scripts.eval_suite import plot_evaluation
        if not plot_evaluation(out_dir=output_dir):
            print("[i] Sem dados de avaliacao (eval_summary.csv) — corre a rotina "
                  "noturna ou 'python scripts/eval_suite.py' para gerar os graficos de tarefa.")
    except Exception as e:
        print(f"[!] Graficos de avaliacao nao gerados (nao critico): {e}")

    # ==============================================================
    # 6. HEATMAPS (ocupação por algo×cenário + geodésico por labirinto)
    #    Import lazy: evita mexer no backend do matplotlib já carregado.
    #    Robusto: uma falha aqui não deve perder os gráficos já gerados.
    # ==============================================================
    try:
        from scripts.heatmaps import generate_all as _gen_heatmaps
        _gen_heatmaps(out_dir=output_dir, episodes=6)
    except Exception as e:
        print(f"[!] Heatmaps nao gerados (nao critico): {e}")

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