import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_final_comparison():
    log_dir = os.path.join(os.path.dirname(__file__), 'results', 'logs')
    # O novo ficheiro do GNN Geracional
    gnn_file = os.path.join(log_dir, 'gnn_fair_training.csv')
    # O ficheiro do PPO que já tinhas
    ppo_file = r"C:\Users\goncalo.santos\swarm-robotics-tese\results\logs_ppo\training_history_ppo.csv"

    print("📊 A preparar comparação final para a tese...")

    try:
        df_gnn = pd.read_csv(gnn_file)
        # Normalizar: Score Total / 30 agentes = Média por agente por episódio
        df_gnn['avg_normalized'] = df_gnn['avg_fitness'] / 30
        df_gnn['best_normalized'] = df_gnn['best_fitness'] / 30
        has_gnn = True
    except FileNotFoundError:
        print("⚠️ Ficheiro GNN não encontrado.")
        has_gnn = False

    try:
        df_ppo = pd.read_csv(ppo_file)
        has_ppo = True
    except FileNotFoundError:
        print("⚠️ Ficheiro PPO não encontrado.")
        has_ppo = False

    sns.set_theme(style="whitegrid")
    fig, ax1 = plt.subplots(figsize=(12, 7))

    if has_gnn:
        ax1.plot(df_gnn['timestep'], df_gnn['avg_normalized'], label='GNN (Elite GA) - Média', color='blue',
                 linewidth=2)
        ax1.fill_between(df_gnn['timestep'], df_gnn['avg_normalized'], df_gnn['best_normalized'], color='blue',
                         alpha=0.1, label='GNN (Intervalo Média-Melhor)')

    if has_ppo:
        ax1.plot(df_ppo['timesteps'], df_ppo['ep_rew_mean'], label='PPO (Baseline)', color='darkorange', linewidth=2,
                 linestyle='--')

    ax1.set_title('Comparação de Performance: GNN vs PPO (Normalizado)', fontsize=15, fontweight='bold')
    ax1.set_xlabel('Total de Timesteps (Amostras do Ambiente)', fontsize=12)
    ax1.set_ylabel('Recompensa Média por Agente', fontsize=12)
    ax1.legend(loc='lower right')

    plt.tight_layout()
    output_plot = 'comparacao_final_tese.png'
    plt.savefig(output_plot, dpi=300)
    print(f"✅ Gráfico guardado: {output_plot}")
    plt.show()


if __name__ == "__main__":
    plot_final_comparison()