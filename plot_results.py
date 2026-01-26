import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import argparse


def plot_graph(mode):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Configurações baseadas no modo
    if mode == "gnn":
        file_path = os.path.join(base_dir, 'results/logs/training_history.csv')
        title = "Evolução da Aprendizagem (GNN)"
        xlabel = "Gerações"
        x_col = "generation"
        y_col_best = "best_score"
        y_col_avg = "avg_score"
    elif mode == "ppo":
        file_path = os.path.join(base_dir, 'results/logs_ppo/training_history_ppo.csv')
        title = "Aprendizagem por Reforço (PPO)"
        xlabel = "Timesteps"
        x_col = "timesteps"
        y_col_best = None  # PPO não tem 'best' da população, só média
        y_col_avg = "ep_rew_mean"
    else:
        print("Modo desconhecido.")
        return

    if not os.path.exists(file_path):
        print(f"❌ Ficheiro não encontrado: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)
    except:
        return

    plt.figure(figsize=(10, 6))
    plt.style.use('ggplot')

    if mode == "gnn":
        plt.plot(df[x_col], df[y_col_best], label='Melhor Agente', color='green', linewidth=2)
        plt.plot(df[x_col], df[y_col_avg], label='Média', color='blue', linestyle='--', alpha=0.7)
    else:
        # PPO
        plt.plot(df[x_col], df[y_col_avg], label='Recompensa Média', color='orange', linewidth=2)

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel('Score (Recompensa)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()  # Abre a janela pop-up


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="gnn", help="gnn ou ppo")
    args = parser.parse_args()
    plot_graph(args.mode)