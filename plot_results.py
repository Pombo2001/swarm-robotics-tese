import pandas as pd
import matplotlib

# --- CORREÇÃO DE CONGELAMENTO ---
# Força o uso do backend TkAgg, que é o mais estável para janelas soltas no Windows
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import os
import sys
import argparse
from tkinter import messagebox
import tkinter as tk


def plot_graph(mode):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Configurações
    if mode == "gnn":
        file_path = os.path.join(base_dir, 'results/logs/training_history.csv')
        title = "Evolução da Aprendizagem (GNN)"
        xlabel = "Gerações"
        x_col = "generation"
        y_col_main = "best_score"
        label_main = "Melhor Agente"
    elif mode == "ppo":
        file_path = os.path.join(base_dir, 'results/logs_ppo/training_history_ppo.csv')
        title = "Aprendizagem por Reforço (PPO)"
        xlabel = "Timesteps"
        x_col = "timesteps"
        y_col_main = "ep_rew_mean"
        label_main = "Recompensa Média"
    else:
        return

    # Verificações de segurança
    if not os.path.exists(file_path):
        root = tk.Tk();
        root.withdraw()
        messagebox.showerror("Erro", f"Ficheiro não encontrado:\n{file_path}")
        return

    try:
        df = pd.read_csv(file_path)
        if df.empty or len(df) < 2:
            root = tk.Tk();
            root.withdraw()
            messagebox.showwarning("Aviso", "Dados insuficientes para gerar gráfico.")
            return
    except Exception as e:
        print(f"Erro: {e}")
        return

    # Desenhar
    plt.figure(figsize=(10, 6))
    plt.style.use('ggplot')

    if mode == "gnn":
        plt.plot(df[x_col], df['best_score'], label='Melhor Agente', color='green', linewidth=2)
        plt.plot(df[x_col], df['avg_score'], label='Média', color='blue', linestyle='--', alpha=0.7)
    else:
        plt.plot(df[x_col], df[y_col_main], label=label_main, color='orange', linewidth=2)

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel('Score')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Esta linha agora é segura graças ao 'TkAgg'
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="gnn")
    args = parser.parse_args()
    plot_graph(args.mode)