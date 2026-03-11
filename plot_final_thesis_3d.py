import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


def create_thesis_plots_3d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gnn_csv = os.path.join(base_dir, 'results', 'logs', 'gnn_3d_training.csv')
    ppo_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_ppo_3d.csv')

    output_dir = os.path.join(base_dir, 'results', 'graficos_tese')
    os.makedirs(output_dir, exist_ok=True)

    # --- 1. GRÁFICO INDIVIDUAL: GNN 3D ---
    if os.path.exists(gnn_csv):
        df_gnn = pd.read_csv(gnn_csv)
        df_gnn.columns = df_gnn.columns.str.strip()

        plt.figure(figsize=(8, 5))
        plt.plot(df_gnn['time'] / 60, df_gnn['best_fitness'], color='#4CAF50', alpha=0.3, label='GNN Bruto')
        plt.plot(df_gnn['time'] / 60, df_gnn['best_fitness'].rolling(5, min_periods=1).mean(), color='#2E7D32',
                 linewidth=2, label='GNN Suavizado')

        plt.title('Evolução do GNN 3D', fontsize=14, fontweight='bold')
        plt.xlabel('Tempo de Treino (Minutos)', fontsize=12)
        plt.ylabel('Fitness Score', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '1_gnn_3d_plot_tempo.png'), dpi=300)
        plt.close()

    # --- 2. GRÁFICO INDIVIDUAL: PPO 3D ---
    if os.path.exists(ppo_csv):
        df_ppo = pd.read_csv(ppo_csv)
        df_ppo.columns = df_ppo.columns.str.strip()

        plt.figure(figsize=(8, 5))
        plt.plot(df_ppo['time'] / 60, df_ppo['ep_rew_mean'], color='#FFA726', alpha=0.3, label='PPO Bruto')
        plt.plot(df_ppo['time'] / 60, df_ppo['ep_rew_mean'].rolling(10, min_periods=1).mean(), color='#E65100',
                 linewidth=2, label='PPO Suavizado')

        plt.title('Aprendizagem do PPO 3D', fontsize=14, fontweight='bold')
        plt.xlabel('Tempo de Treino (Minutos)', fontsize=12)
        plt.ylabel('Recompensa Média', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '2_ppo_3d_plot_tempo.png'), dpi=300)
        plt.close()

    # --- 3. GRÁFICO DE COMPARAÇÃO JUSTA ---
    if os.path.exists(gnn_csv) and os.path.exists(ppo_csv):
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Eixo X é o TEMPO (Minutos)
        ax1.set_xlabel('Tempo de Treino Simultâneo (Minutos)', fontsize=12)

        color1 = '#2E7D32'
        ax1.set_ylabel('Pontuação GNN (Fitness Bruto)', color=color1, fontsize=12, fontweight='bold')
        line1 = ax1.plot(df_gnn['time'] / 60, df_gnn['best_fitness'].rolling(5, min_periods=1).mean(), color=color1,
                         linewidth=2.5, label='GNN 3D')
        ax1.tick_params(axis='y', labelcolor=color1)

        ax2 = ax1.twinx()
        color2 = '#E65100'
        ax2.set_ylabel('Pontuação PPO (Recompensa Média)', color=color2, fontsize=12, fontweight='bold')
        line2 = ax2.plot(df_ppo['time'] / 60, df_ppo['ep_rew_mean'].rolling(10, min_periods=1).mean(), color=color2,
                         linewidth=2.5, label='PPO 3D')
        ax2.tick_params(axis='y', labelcolor=color2)

        plt.title('Comparação Justa por Tempo: GNN vs PPO (3D)', fontsize=16, fontweight='bold')

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='lower right', fontsize=11)
        ax1.grid(True, linestyle='--', alpha=0.5)

        fig.tight_layout()
        plt.savefig(os.path.join(output_dir, '3_comparacao_justa_tempo_3d.png'), dpi=300)
        plt.show()


if __name__ == "__main__":
    create_thesis_plots_3d()