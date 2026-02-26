import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_fair_comparison():
    # Caminhos
    gnn_file = os.path.join(os.path.dirname(__file__), 'results', 'logs', 'continuous_training.csv')
    ppo_file = r"C:\Users\goncalo.santos\swarm-robotics-tese\results\logs_ppo\training_history_ppo.csv"

    print("📊 A carregar dados de treino...")

    try:
        df_gnn = pd.read_csv(gnn_file)
        has_gnn = True
        print("✅ GNN carregado!")
    except FileNotFoundError:
        has_gnn = False

    try:
        df_ppo = pd.read_csv(ppo_file)
        has_ppo = True
        print("✅ PPO carregado!")
    except FileNotFoundError:
        has_ppo = False

    if not has_gnn and not has_ppo:
        print("❌ Nenhum dado encontrado. Abortando.")
        return

    # --- A CORREÇÃO DE ESCALA (Magia Matemática) ---
    # Multiplicamos a média móvel do GNN pelo tamanho do episódio do PPO (500)
    # Assim estão a competir na mesma métrica de "Pontos por 500 steps"
    EPISODE_LENGTH = 500
    if has_gnn:
        df_gnn['avg_fitness_ep'] = df_gnn['avg_fitness'] * EPISODE_LENGTH
        df_gnn['best_fitness_ep'] = df_gnn['best_fitness'] * EPISODE_LENGTH

    # Estilo
    sns.set_theme(style="whitegrid")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Comparação Justa: GNN Steady-State vs PPO (Escala Normalizada)', fontsize=16, fontweight='bold')

    # --- GRÁFICO 1: Amostras vs Recompensa ---
    if has_gnn:
        ax1.plot(df_gnn['timestep'], df_gnn['avg_fitness_ep'], label='GNN - Média', color='blue', linewidth=2)
        ax1.plot(df_gnn['timestep'], df_gnn['best_fitness_ep'], label='GNN - Melhor', color='cyan', linestyle='--',
                 alpha=0.7)

    if has_ppo:
        ax1.plot(df_ppo['timesteps'], df_ppo['ep_rew_mean'], label='PPO', color='darkorange', linewidth=2.5)

    ax1.set_title('Eficiência (Timesteps)', fontsize=14)
    ax1.set_xlabel('Total de Interações (Timesteps)')
    ax1.set_ylabel('Recompensa Equivalente (500 steps)')
    ax1.legend()

    # --- GRÁFICO 2: Tempo Real vs Recompensa ---
    if has_gnn and 'time' in df_gnn.columns:
        ax2.plot(df_gnn['time'], df_gnn['avg_fitness_ep'], label='GNN - Média', color='blue', linewidth=2)

    if has_ppo and 'time' in df_ppo.columns:
        ax2.plot(df_ppo['time'], df_ppo['ep_rew_mean'], label='PPO', color='darkorange', linewidth=2)
    else:
        ax2.text(0.5, 0.5, 'Tempo indisponível no CSV do PPO',
                 horizontalalignment='center', verticalalignment='center',
                 transform=ax2.transAxes, color='gray', fontsize=12)

    ax2.set_title('Tempo de Execução', fontsize=14)
    ax2.set_xlabel('Tempo (Segundos)')
    ax2.set_ylabel('Recompensa Equivalente (500 steps)')
    ax2.legend()

    plt.tight_layout()
    plt.savefig('graficos_comparacao_justa.png', dpi=300)
    print("✅ Gráfico guardado com sucesso!")
    plt.show()


if __name__ == "__main__":
    plot_fair_comparison()