import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys
import yaml

# Adicionar a raiz do projeto ao path para encontrar os módulos
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def plot_metrics(algo_short, scenario):
    """
    Lê o ficheiro de dados centralizado ('all_curves_data.csv'), filtra pelo
    algoritmo e cenário, e plota a curva de aprendizagem da ÚLTIMA run.
    """
    base_dir = PROJECT_ROOT
    # O ficheiro central que contém todos os dados
    log_file = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas', 'all_curves_data.csv')

    # Mapear o nome curto do algo (gnn, ppo, sac) para o nome completo usado no CSV (GNN, PPO, SAC)
    algo_map = {'gnn': 'GNN', 'ppo': 'PPO', 'sac': 'SAC'}
    algo_full = algo_map.get(algo_short.lower())

    if not algo_full:
        print(f"ERRO: Algoritmo '{algo_short}' não reconhecido.")
        return

    plot_title = f'Curva de Aprendizagem (Última Run) - {algo_full} - Cenário: {scenario.upper()}'

    try:
        if not os.path.exists(log_file):
            raise FileNotFoundError(f"Ficheiro de dados central não encontrado: {log_file}")

        # Ler o ficheiro de dados completo
        df_all = pd.read_csv(log_file)

        # Filtrar para o algoritmo e cenário específicos
        df_filtered = df_all[(df_all['Algorithm'] == algo_full) & (df_all['Scenario'] == scenario)]

        if df_filtered.empty:
            raise ValueError(f"Não foram encontrados dados para o algoritmo '{algo_full}' no cenário '{scenario}'.")

        # Isolar a última run
        last_run_num = df_filtered['Run'].max()
        df_last_run = df_filtered[df_filtered['Run'] == last_run_num].copy()
        
        if df_last_run.empty:
            raise ValueError(f"Não foram encontrados dados para a última run ({last_run_num}).")

        # Suavização com média móvel para um gráfico mais limpo
        df_last_run['Score_Suavizado'] = df_last_run['Score'].rolling(window=15, min_periods=1).mean()

        # Plotar os dados da última run
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.figure(figsize=(12, 7))
        
        plt.plot(df_last_run['Step'], df_last_run['Score_Suavizado'], marker='o', linestyle='-', markersize=3, label=f'Run {last_run_num} (Suavizado)')
        plt.plot(df_last_run['Step'], df_last_run['Score'], color='gray', alpha=0.4, linestyle='--', label=f'Run {last_run_num} (Raw)')

        plt.title(plot_title, fontsize=16)
        plt.xlabel("Timestep", fontsize=12)
        plt.ylabel("Score", fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.show()

    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"ERRO ao ler ou plotar os dados: {e}")
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, f'Erro ao processar dados:\n{e}', 
                 ha='center', va='center', fontsize=12, color='red')
        plt.title(plot_title)
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Plota a métrica da última run de um algoritmo.")
    parser.add_argument("--algo", type=str, required=True, help="O algoritmo a plotar (gnn, ppo, sac).")
    
    # O cenário é lido do config.yaml para garantir que corresponde ao da simulação
    base_dir = PROJECT_ROOT
    config_path = os.path.join(base_dir, 'configs', 'foraging.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        current_scenario = config['environment'].get('classic_scenario', 'none')
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Aviso: Não foi possível ler o cenário do config.yaml: {e}. Usando 'none'.")
        current_scenario = 'none'

    args = parser.parse_args()
    
    plot_metrics(args.algo, current_scenario)
