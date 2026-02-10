import matplotlib.pyplot as plt
import pandas as pd
import os
import glob
import numpy as np


def plot_comparison():
    print("🔄 A iniciar geração do gráfico...")

    # 1. Carregar dados do GNN (Algoritmo Genético)
    gnn_path = os.path.join('results', 'logs', 'training_history.csv')
    if os.path.exists(gnn_path):
        df_gnn = pd.read_csv(gnn_path)
        print(f"✅ Dados GNN carregados: {len(df_gnn)} gerações.")
    else:
        print(f"❌ Erro: CSV do GNN não encontrado em {gnn_path}")
        return

    # 2. Carregar dados do PPO (Reinforcement Learning)
    # Procura a pasta mais recente em results/logs_ppo/
    ppo_base_dir = os.path.join('results', 'logs_ppo')
    if not os.path.exists(ppo_base_dir):
        print(f"❌ Erro: Pasta {ppo_base_dir} não existe.")
        return

    ppo_dirs = glob.glob(os.path.join(ppo_base_dir, 'PPO_*'))
    if not ppo_dirs:
        print("❌ Erro: Nenhuma pasta PPO encontrada.")
        return

    latest_ppo_dir = max(ppo_dirs, key=os.path.getctime)
    print(f"📂 Pasta PPO mais recente: {latest_ppo_dir}")

    # Tenta encontrar progress.csv (Padrão do SB3)
    progress_file = os.path.join(latest_ppo_dir, 'progress.csv')

    if os.path.exists(progress_file):
        print("✅ Ficheiro progress.csv encontrado!")
        df_ppo = pd.read_csv(progress_file)
        # O SB3 guarda a recompensa média na coluna 'rollout/ep_rew_mean'
        if 'rollout/ep_rew_mean' in df_ppo.columns:
            ppo_rewards = df_ppo['rollout/ep_rew_mean']
            # O eixo X do PPO são os timesteps ou iterações
            ppo_steps = df_ppo['time/total_timesteps']
        else:
            print("⚠️ Aviso: Coluna 'rollout/ep_rew_mean' não encontrada no CSV do PPO.")
            return
    else:
        # Fallback para monitor.csv (caso tenhas usado Wrapper)
        monitor_files = glob.glob(os.path.join(latest_ppo_dir, '*.monitor.csv'))
        if monitor_files:
            print("✅ Ficheiro monitor.csv encontrado!")
            df_ppo = pd.read_csv(monitor_files[0], skiprows=1)
            ppo_rewards = df_ppo['r'].rolling(window=10).mean()  # Suavizar
            ppo_steps = np.cumsum(df_ppo['l'])
        else:
            print(f"❌ Erro: Nenhum ficheiro CSV (progress.csv ou monitor.csv) encontrado em {latest_ppo_dir}")
            print(f"Conteúdo da pasta: {os.listdir(latest_ppo_dir)}")
            return

    # 3. Gerar o Gráfico
    plt.figure(figsize=(10, 6))

    # --- GNN ---
    # Normalizar eixo X do GNN para ser comparável (se quisermos) ou usar Gerações
    plt.plot(df_gnn['generation'], df_gnn['best_score'],
             label='GNN (Melhor Agente)', color='blue', linewidth=2)
    plt.plot(df_gnn['generation'], df_gnn['avg_score'],
             label='GNN (Média População)', color='lightblue', linestyle='--')

    # --- PPO ---
    # O PPO tem muitas iterações (steps). Vamos criar um eixo secundário ou apenas plotar
    # Para simplificar a visualização lado a lado, vamos usar um eixo X partilhado artificial
    # ou plotar o PPO no eixo secundário Y se as escalas forem muito diferentes.
    # Mas aqui vamos tentar plotar direto.

    # Como o PPO tem muitos pontos (steps), vamos escalar o eixo X do PPO para caber no gráfico
    # Ou simplesmente plotar o PPO usando o index como "Tempo Relativo"

    # Opção: Criar Eixo Secundário para o PPO (Melhor Visualização)
    ax1 = plt.gca()
    ax1.set_xlabel('Gerações (GNN)', fontsize=12)
    ax1.set_ylabel('Score GNN', fontsize=12, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twiny()  # Segundo eixo X em cima
    ax2.set_xlabel('Steps de Treino (PPO)', fontsize=12, color='orange')
    ax2.plot(ppo_steps, ppo_rewards, label='PPO (Reward Médio)', color='orange', linewidth=2)
    ax2.tick_params(axis='x', labelcolor='orange')

    # Legendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.title('Comparação Final: GNN vs PPO (Obstáculos Móveis)', fontsize=14, y=1.05)
    plt.grid(True, alpha=0.3)

    output_file = 'comparacao_final_obstaculos.png'
    plt.savefig(output_file, bbox_inches='tight')
    print(f"✅ Gráfico guardado com sucesso: {output_file}")
    plt.show()


if __name__ == "__main__":
    plot_comparison()