import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np


def plot_comparison():
    print("📊 A gerar Gráfico Final da Tese...")

    # --- 1. CARREGAR GNN (Do CSV que já tens) ---
    gnn_path = os.path.join('results', 'logs', 'training_history.csv')
    if os.path.exists(gnn_path):
        df_gnn = pd.read_csv(gnn_path)
        print(f"✅ GNN carregado: {len(df_gnn)} gerações (Max Score: {df_gnn['best_score'].max():.1f})")
    else:
        print(f"❌ Erro: {gnn_path} não encontrado.")
        return

    # --- 2. DADOS DO PPO (Extraídos manualmente dos teus logs) ---
    # Isto evita ter de instalar bibliotecas complexas como o TensorBoard.
    # Dados baseados no teu treino "PPO_18" (Iteração 1 a 25)
    print("✅ A usar dados do PPO extraídos dos logs...")

    # Valores de 'ep_rew_mean' que enviaste
    ppo_rewards = [
        39, 54.4, 80.4, 126, 156, 193, 219, 254, 271, 296,
        319, 330, 348, 378, 401, 402, 405, 421, 433, 439,
        438, 446, 443, 450, 462
    ]

    # O PPO treinou durante 512,000 steps (25 iterações * 20480 steps)
    ppo_steps = np.linspace(0, 512000, len(ppo_rewards))

    # --- 3. GERAR O GRÁFICO (EIXO DUPLO) ---
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Eixo 1: GNN (Gerações)
    ax1.set_xlabel('Gerações (GNN - Evolutivo)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Score (Recompensa)', fontsize=12, fontweight='bold', color='black')

    # Linhas do GNN
    lns1 = ax1.plot(df_gnn['generation'], df_gnn['best_score'],
                    label='GNN - Melhor Agente (Max: ~3000)', color='blue', linewidth=2)
    lns2 = ax1.plot(df_gnn['generation'], df_gnn['avg_score'],
                    label='GNN - Média População', color='lightblue', linestyle='--')

    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)

    # Eixo 2: PPO (Steps) - Criamos um segundo eixo X em cima
    ax2 = ax1.twiny()
    color_ppo = 'tab:orange'
    ax2.set_xlabel('Steps de Treino (PPO - Reinforcement Learning)', fontsize=12, fontweight='bold', color=color_ppo)

    # Linha do PPO
    lns3 = ax2.plot(ppo_steps, ppo_rewards, label='PPO - Reward Médio (Max: ~460)', color='orange', linewidth=2.5,
                    marker='o', markersize=4)
    ax2.tick_params(axis='x', labelcolor=color_ppo)

    # Título e Legendas
    plt.title('Comparação Final: Evolução (GNN) vs RL (PPO)\nCenário: Obstáculos Móveis', fontsize=14, pad=20)

    # Juntar legendas
    lns = lns1 + lns2 + lns3
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc='upper left', frameon=True, shadow=True)

    plt.tight_layout()
    output_file = 'grafico_tese_final.png'
    plt.savefig(output_file, dpi=300)
    print(f"✅ Gráfico guardado com sucesso: {output_file}")
    plt.show()


if __name__ == "__main__":
    plot_comparison()