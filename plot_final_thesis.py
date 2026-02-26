import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_final_comparison():
    log_dir = os.path.join(os.path.dirname(__file__), 'results', 'logs')
    gnn_file = os.path.join(log_dir, 'gnn_fair_training.csv')
    ppo_file = r"C:\Users\goncalo.santos\swarm-robotics-tese\results\logs_ppo\training_history_ppo.csv"

    print("📊 A preparar comparação final para a tese...")

    try:
        df_gnn = pd.read_csv(gnn_file)
        df_gnn = df_gnn.apply(pd.to_numeric, errors='coerce').dropna()

        # CORREÇÃO: Remover a divisão errada por 30.
        # Vamos usar o Score Total do Episódio (Soma do Enxame)
        df_gnn['avg_score'] = df_gnn['avg_fitness']
        df_gnn['best_score'] = df_gnn['best_fitness']
        has_gnn = True
    except FileNotFoundError:
        print("⚠️ Ficheiro GNN não encontrado.")
        has_gnn = False

    try:
        df_ppo = pd.read_csv(ppo_file)
        df_ppo = df_ppo.apply(pd.to_numeric, errors='coerce').dropna()
        has_ppo = True
    except FileNotFoundError:
        print("⚠️ Ficheiro PPO não encontrado.")
        has_ppo = False

    sns.set_theme(style="whitegrid")
    fig, ax1 = plt.subplots(figsize=(12, 7))

    if has_gnn:
        ax1.plot(df_gnn['timestep'], df_gnn['avg_score'], label='GNN (Elite GA) - Média do Enxame', color='blue',
                 linewidth=2)
        ax1.fill_between(df_gnn['timestep'], df_gnn['avg_score'], df_gnn['best_score'], color='blue', alpha=0.1,
                         label='GNN (Elite GA) - Melhor Cérebro')

    if has_ppo:
        ax1.plot(df_ppo['timesteps'], df_ppo['ep_rew_mean'], label='PPO (Baseline)', color='darkorange', linewidth=2,
                 linestyle='--')

    ax1.set_title('Comparação de Performance: GNN vs PPO (Nova Arena)', fontsize=15, fontweight='bold')
    ax1.set_xlabel('Total de Timesteps (Amostras do Ambiente)', fontsize=12)
    ax1.set_ylabel('Recompensa Total do Enxame por Episódio', fontsize=12)
    ax1.legend(loc='upper left')

    plt.tight_layout()
    output_plot = 'comparacao_final_tese.png'
    plt.savefig(output_plot, dpi=300)

    # Acesso read/write padrão garantido [cite: 2026-02-23]
    os.chmod(output_plot, 0o666)

    print(f"✅ Gráfico guardado: {output_plot}")
    plt.show()


if __name__ == "__main__":
    plot_final_comparison()