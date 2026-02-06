import pandas as pd
import matplotlib

matplotlib.use('TkAgg')  # Para não bloquear
import matplotlib.pyplot as plt
import os


def plot_comparison():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Caminhos dos Logs
    gnn_path = os.path.join(base_dir, 'results/logs/training_history.csv')
    ppo_path = os.path.join(base_dir, 'results/logs_ppo/training_history_ppo.csv')

    plt.figure(figsize=(12, 7))
    plt.style.use('ggplot')  # Estilo bonito

    # 1. Plot GNN (Eixo X = Gerações)
    if os.path.exists(gnn_path):
        df_gnn = pd.read_csv(gnn_path)
        # Normalizar para % de treino para podermos comparar visualmente
        # (Ou podemos usar apenas o Score no Eixo Y e ignorar o tempo X)
        plt.plot(df_gnn['generation'], df_gnn['best_score'],
                 label='GNN (Melhor Agente)', color='green', linewidth=3)
        plt.plot(df_gnn['generation'], df_gnn['avg_score'],
                 label='GNN (Média População)', color='lightgreen', linestyle='--')

        max_gnn = df_gnn['best_score'].max()
        plt.axhline(y=max_gnn, color='green', linestyle=':', alpha=0.5)
        plt.text(0, max_gnn, f' Peak: {max_gnn:.0f}', color='green', va='bottom')

    # 2. Plot PPO (Temos de "aldrabar" o Eixo X para caber no gráfico ou usar 2 eixos)
    # Vamos usar um eixo secundário para o PPO se quisermos comparar evolução,
    # MAS como queremos comparar SCORES, usamos o mesmo eixo Y.
    # O PPO tem muito mais pontos de dados (steps), vamos desenhar uma linha horizontal
    # representando o Score Final do PPO para servir de referência.

    if os.path.exists(ppo_path):
        df_ppo = pd.read_csv(ppo_path)
        final_ppo_score = df_ppo['ep_rew_mean'].iloc[-1]

        plt.axhline(y=final_ppo_score, color='orange', linewidth=3, label=f'PPO Final Score ({final_ppo_score:.0f})')
        plt.text(0, final_ppo_score, f' PPO: {final_ppo_score:.0f}', color='orange', va='bottom', fontweight='bold')

    plt.title("Batalha Final: Algoritmo Genético vs PPO", fontsize=16)
    plt.xlabel("Gerações (Apenas GNN)", fontsize=12)
    plt.ylabel("Score (Comida Recolhida)", fontsize=12)
    plt.legend(loc='upper left', fontsize=12)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_comparison()