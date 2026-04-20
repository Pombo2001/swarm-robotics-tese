import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


def get_x_col(df):
    """Vamos forçar o Eixo X a ser o Tempo em Minutos para veres que eles correram as 8h!"""
    if 'time' in df.columns:
        df['time_minutes'] = df['time'] / 60
        return 'time_minutes'
    return df.columns[0]


def plot_normalized_safe(ax, csv_path, label, color, y_col_name):
    """Lê, suaviza e normaliza uma linha de forma blindada contra erros matemáticos"""
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        if len(df) > 1 and y_col_name in df.columns:
            x_col = get_x_col(df)

            # 1. Suavizar os dados primeiro (rolling mean)
            smoothed_series = df[y_col_name].rolling(10, min_periods=1).mean()

            # 2. Encontrar o mínimo e o máximo
            min_val = smoothed_series.min()
            max_val = smoothed_series.max()

            # 3. Normalizar de 0 a 100% de forma segura (evitando divisão por zero)
            if max_val > min_val:
                norm_series = ((smoothed_series - min_val) / (max_val - min_val)) * 100
            else:
                # Se o algoritmo for uma linha reta (ainda não aprendeu nada), fica no 0%
                norm_series = pd.Series([0.0] * len(smoothed_series))

            ax.plot(df[x_col], norm_series, color=color, linewidth=2.5, label=label)
            print(f"✅ {label} processado e normalizado com sucesso.")
        else:
            print(f"⚠️ {label}: Ficheiro tem poucos dados ou coluna não encontrada.")


def create_thesis_plots_3d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gnn_csv = os.path.join(base_dir, 'results', 'logs', 'gnn_3d_training.csv')
    ppo_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_ppo_3d.csv')
    sac_csv = os.path.join(base_dir, 'results', 'logs_ppo', 'training_history_sac_3d.csv')

    output_dir = os.path.join(base_dir, 'results', 'graficos_tese')
    os.makedirs(output_dir, exist_ok=True)

    # --- 1, 2, 3. GRÁFICOS INDIVIDUAIS (Mantidos para teres na tese) ---
    def plot_individual(csv_file, y_col, title, color_light, color_dark, out_name):
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            df.columns = df.columns.str.strip()
            if len(df) > 0 and y_col in df.columns:
                x_col = get_x_col(df)
                plt.figure(figsize=(8, 5))
                plt.plot(df[x_col], df[y_col], color=color_light, alpha=0.3, label='Bruto')
                plt.plot(df[x_col], df[y_col].rolling(10, min_periods=1).mean(), color=color_dark, linewidth=2,
                         label='Suavizado')
                plt.title(title, fontsize=14, fontweight='bold')
                plt.xlabel('Tempo Real de Treino (Minutos)', fontsize=12)
                plt.ylabel('Score Absoluto', fontsize=12)
                plt.grid(True, linestyle='--', alpha=0.6)
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, out_name), dpi=300)
                plt.close()

    plot_individual(gnn_csv, 'best_fitness', 'Evolução do GNN 3D', '#4CAF50', '#2E7D32', '1_gnn_3d_plot.png')
    plot_individual(ppo_csv, 'ep_rew_mean', 'Aprendizagem do PPO 3D', '#FFA726', '#E65100', '2_ppo_3d_plot.png')
    plot_individual(sac_csv, 'ep_rew_mean', 'Aprendizagem do SAC 3D', '#29B6F6', '#0277BD', '3_sac_3d_plot.png')

    # --- 4. O GRÁFICO DE MESTRADO: COMPARAÇÃO NORMALIZADA ---
    print("\n📊 A gerar o Gráfico de Comparação Normalizada...")
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # ATENÇÃO: Aqui está a prova dos 9! O eixo X agora mostra os minutos.
    ax1.set_xlabel('Tempo Real de Treino (Minutos)', fontsize=12)
    ax1.set_ylabel('Evolução do Desempenho (0% a 100%)', fontsize=12, fontweight='bold')

    # Chamar a nossa função blindada para os 3 algoritmos
    plot_normalized_safe(ax1, gnn_csv, 'GNN 3D (Evolutivo)', '#2E7D32', 'best_fitness')
    plot_normalized_safe(ax1, ppo_csv, 'PPO 3D (Actor-Critic)', '#E65100', 'ep_rew_mean')
    plot_normalized_safe(ax1, sac_csv, 'SAC 3D (Soft Actor-Critic)', '#0277BD', 'ep_rew_mean')

    plt.title('Batalha de Eficiência: GNN vs PPO vs SAC', fontsize=16, fontweight='bold')

    # Forçar o eixo Y a ir de 0 a 105 para o gráfico respirar
    ax1.set_ylim([-5, 105])

    ax1.legend(loc='lower right', fontsize=11)
    ax1.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()

    path_comp = os.path.join(output_dir, '4_comparacao_justa_tempo.png')
    plt.savefig(path_comp, dpi=300)
    print(f"\n✅ Gráficos guardados na pasta: {output_dir}")
    plt.show()


if __name__ == "__main__":
    import traceback

    try:
        create_thesis_plots_3d()
    except Exception as e:
        print("\n💥 CRASH FATAL! Erro ao gerar os gráficos:")
        traceback.print_exc()
    finally:
        input("\n🛑 Pressiona ENTER para fechar a janela...")