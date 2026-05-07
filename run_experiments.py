import os
import sys
import yaml
import subprocess
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES BASE DO SCRIPT
# ==============================================================================
SCENARIOS = ['none', 'u_wall', 'bottleneck', 'four_rooms', 'cooperative_door', 'cooperative_perception']

ALGORITHMS = {
    'GNN': 'src/training/evo_trainer_3d.py',
    'PPO': 'src/training/train_ppo_3d.py',
    'SAC': 'src/training/train_sac_3d.py'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'configs', 'foraging.yaml')

LOG_PATHS = {
    'GNN': os.path.join(BASE_DIR, 'results', 'logs', 'gnn_3d_training.csv'),
    'PPO': os.path.join(BASE_DIR, 'results', 'logs_ppo', 'training_history_ppo_3d.csv'),
    'SAC': os.path.join(BASE_DIR, 'results', 'logs_ppo', 'training_history_sac_3d.csv')
}

SCORE_COLS = {
    'GNN': 'best_fitness',
    'PPO': 'ep_rew_mean',
    'SAC': 'ep_rew_mean'
}

STEP_COLS = {
    'GNN': 'timestep',
    'PPO': 'timesteps',
    'SAC': 'timesteps'
}

def set_scenario(scenario_name):
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        config['environment']['classic_scenario'] = scenario_name
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f)
        print(f"[*] Cenário configurado para: {scenario_name}")
    except Exception as e:
        print(f"[!] Erro ao configurar cenário: {e}")

def run_experiments(num_runs, time_limit):
    curves_data = []
    best_scores_data = []

    print(f"Iniciando Automacao de Experiencias:")
    print(f"Runs: {num_runs} | Tempo Limite: {time_limit}m | Cenários: {len(SCENARIOS)}")

    for scenario in SCENARIOS:
        set_scenario(scenario)
        
        for algo_name, algo_script in ALGORITHMS.items():
            script_path = os.path.join(BASE_DIR, algo_script)
            log_path = LOG_PATHS[algo_name]
            score_col = SCORE_COLS[algo_name]
            step_col = STEP_COLS[algo_name]
            
            for run in range(1, num_runs + 1):
                print(f"\n--- A EXECUTAR | Cenário: {scenario} | Algoritmo: {algo_name} | Run: {run}/{num_runs} ---")
                
                if os.path.exists(log_path):
                    try:
                        os.remove(log_path)
                    except Exception as e:
                        print(f"[!] Aviso: Nao foi possivel apagar o log antigo ({e})")
                
                cmd = [sys.executable, script_path, '--time_limit', str(time_limit)]
                
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"[!] Run {run} do {algo_name} falhou: {e}")
                
                # Extracao de Dados
                if os.path.exists(log_path):
                    try:
                        df = pd.read_csv(log_path)
                        df.columns = df.columns.str.strip()
                        
                        if not df.empty and score_col in df.columns and step_col in df.columns:
                            max_score = df[score_col].max()
                            
                            best_scores_data.append({
                                'Scenario': scenario,
                                'Algorithm': algo_name,
                                'Run': run,
                                'BestScore': max_score
                            })
                            
                            for _, row in df.iterrows():
                                curves_data.append({
                                    'Scenario': scenario,
                                    'Algorithm': algo_name,
                                    'Run': run,
                                    'Step': row[step_col],
                                    'Score': row[score_col]
                                })
                        else:
                            print(f"[!] Log vazio ou colunas nao encontradas para {algo_name} Run {run}.")
                    except Exception as e:
                        print(f"[!] Erro ao ler CSV do {algo_name} Run {run}: {e}")
                else:
                    print(f"[!] Ficheiro de log {log_path} nao encontrado apos a execucao.")

    df_curves = pd.DataFrame(curves_data)
    df_best = pd.DataFrame(best_scores_data)
    
    generate_plots(df_curves, df_best, num_runs, time_limit)

def generate_plots(df_curves, df_best, num_runs, time_limit):
    print("\n--- A GERAR GRÁFICOS AVANÇADOS ---")
    
    # 1. Cálculos de Tempo para a Pasta e o TXT
    total_runs = len(SCENARIOS) * len(ALGORITHMS) * num_runs
    minutos_totais = total_runs * time_limit
    horas_totais = round(minutos_totais / 60, 2)
    
    now = datetime.now()
    date_time_str = now.strftime("%d-%m-%Y_%Hh%Mm")
    
    # Formato que pediste: DATA_ATUAL_HORAS_MINUTOS_XhT
    folder_name = f"{date_time_str}_{horas_totais}hT"
    out_dir = os.path.join(BASE_DIR, 'results', 'graficos_tese', 'estatisticas', folder_name)
    os.makedirs(out_dir, exist_ok=True)

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)
    cores = {'GNN': '#2ca02c', 'PPO': '#ff7f0e', 'SAC': '#1f77b4'}

    # 2. Curvas de Aprendizagem (Agrupadas e Suavizadas)
    if not df_curves.empty:
        # Média Móvel para não parecerem rabiscos difíceis de ler
        df_curves['Score_Suavizado'] = df_curves.groupby(['Scenario', 'Algorithm', 'Run'])['Score'].transform(lambda x: x.rolling(window=15, min_periods=1).mean())
        
        for scenario in df_curves['Scenario'].unique():
            plt.figure(figsize=(10, 6))
            data_scen = df_curves[df_curves['Scenario'] == scenario]
            sns.lineplot(data=data_scen, x='Step', y='Score_Suavizado', hue='Algorithm', palette=cores, errorbar='sd')
            plt.title(f'Curva de Aprendizagem Suavizada - Cenário: {scenario.upper()}', fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f'curva_aprendizagem_{scenario}.png'), dpi=300)
            plt.close()

    # 3. Boxplots (Normais e Limpos)
    if not df_best.empty:
        for scenario in df_best['Scenario'].unique():
            plt.figure(figsize=(8, 6))
            data_scen = df_best[df_best['Scenario'] == scenario]
            sns.boxplot(data=data_scen, x='Algorithm', y='BestScore', hue='Algorithm', palette=cores, width=0.5, fliersize=5)
            plt.title(f'Distribuição de Melhores Scores das {num_runs} Runs - Cenário: {scenario.upper()}', fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f'boxplot_{scenario}.png'), dpi=300)
            plt.close()

        # 4. Gráfico Geral de Barras (Escala Logarítmica para se ler tudo)
        plt.figure(figsize=(14, 7))
        df_best_log = df_best.copy()
        df_best_log['BestScore_Log'] = np.maximum(df_best_log['BestScore'], 1)  # Impede valores <= 0 de quebrar o log
        
        ax = sns.barplot(data=df_best_log, x='Scenario', y='BestScore_Log', hue='Algorithm', errorbar='sd', palette=cores)
        ax.set_yscale("log")
        plt.title('Comparação Geral de Desempenho (Escala Logarítmica)', fontweight='bold', fontsize=16)
        plt.ylabel('Score Máximo (Escala Log)')
        plt.xlabel('Cenários')
        plt.legend(title='Algoritmo')
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, 'comparacao_barras_geral_log.png'), dpi=300)
        plt.close()

    # Guarda raw data
    if not df_curves.empty:
        df_curves.to_csv(os.path.join(out_dir, 'all_curves_data.csv'), index=False)
        df_curves.to_csv(os.path.join(BASE_DIR, 'results', 'graficos_tese', 'estatisticas', 'all_curves_data.csv'), index=False)
        
    if not df_best.empty:
        df_best.to_csv(os.path.join(out_dir, 'all_best_scores.csv'), index=False)
        df_best.to_csv(os.path.join(BASE_DIR, 'results', 'graficos_tese', 'estatisticas', 'all_best_scores.csv'), index=False)
        
    # 5. GERAR O FICHEIRO TXT COM AS INFORMAÇÕES DO TREINO
    info_txt_path = os.path.join(out_dir, "info_treino.txt")
    with open(info_txt_path, 'w', encoding='utf-8') as f:
        f.write("=========================================\n")
        f.write("      RELATÓRIO DE TREINO AUTOMÁTICO     \n")
        f.write("=========================================\n")
        f.write(f"Data de Geração      : {now.strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Tempo Total de Treino: {horas_totais} horas\n")
        f.write(f"Tempo por Run        : {time_limit} minutos\n")
        f.write(f"Nº de Runs           : {num_runs} por cenário e algoritmo\n")
        f.write(f"Total de Execuções   : {total_runs}\n\n")
        
        f.write(f"--- CENÁRIOS AVALIADOS ({len(SCENARIOS)}) ---\n")
        for s in SCENARIOS:
            f.write(f" - {s}\n")
            
        f.write(f"\n--- ALGORITMOS TESTADOS ({len(ALGORITHMS)}) ---\n")
        for a in ALGORITHMS.keys():
            f.write(f" - {a}\n")
            
    print(f"[*] Gráficos legíveis, CSVs e Relatório TXT guardados com sucesso em:\n    {out_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automação de Experiências para a Tese")
    parser.add_argument("--runs", type=int, default=5, help="Nº de Runs por Cenário")
    parser.add_argument("--time", type=int, default=60, help="Minutos por Run")
    args = parser.parse_args()
    
    run_experiments(num_runs=args.runs, time_limit=args.time)