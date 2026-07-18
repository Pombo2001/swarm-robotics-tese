"""
eval_scalability.py — Sscale: transferência Zero-Shot para N variável
======================================================================
Treina-se com N=20 agentes e avalia-se, SEM retreino, com N in {10,20,50,100}.
Mede a capacidade de generalização do controlador a enxames de outra dimensão.

Nota arquitetural (resultado relevante para a tese):
  - GNN: a política agrega os vizinhos por atenção, logo é INVARIANTE ao número
    de agentes — aceita qualquer N nativamente.
  - PPO/SAC: usam uma MLP com entrada de dimensão FIXA (16 + (N_treino-1)*5).
    Para N != N_treino a observação muda de tamanho e o modelo é incompatível.
    O script deteta isto e marca "N/A" — evidência empírica de que o MLP não
    escala e a GNN sim.

Pré-requisito: modelos treinados (idealmente no cenário a testar).

Uso:
    python scripts/eval_scalability.py --scenario none --episodes 20
    python scripts/eval_scalability.py --scenario none --sizes 10,20,50,100
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.dirname(__file__))  # para importar run_eval

import yaml
from src.environment.swarm_env_3d import SwarmForagingEnv3D
from run_eval import load_model, run_episode, SCENARIO_LABELS

ALGOS = ["gnn", "ppo", "sac"]
PALETTE = {"GNN": "#2E7D32", "PPO": "#E65100", "SAC": "#0277BD"}
OUT_STATS = os.path.join(PROJECT_ROOT, "results", "estatisticas")


def eval_at_size(algo, model, base_config, scenario, num_agents, n_episodes):
    """Corre n_episodes com num_agents agentes. Devolve dict de métricas
    ou None se o modelo for incompatível com este N (caso do MLP do PPO/SAC)."""
    cfg = yaml.safe_load(yaml.dump(base_config))  # cópia profunda
    cfg["environment"]["num_agents"] = num_agents
    cfg["environment"]["classic_scenario"] = scenario
    env = SwarmForagingEnv3D(config=cfg)

    foods, succ, per_agent = [], [], []
    for _ in range(n_episodes):
        try:
            r = run_episode(env, algo, model)
        except Exception as e:
            # Shape mismatch típico do MLP (PPO/SAC) quando N != N_treino.
            print(f"    [{algo.upper()}] N={num_agents}: incompativel ({type(e).__name__}) — N/A")
            return None
        foods.append(r["food_collected"])
        succ.append(1.0 if r["success"] else 0.0)
        per_agent.append(r["food_collected"] / num_agents)

    return {
        "mean_food": float(np.mean(foods)),
        "std_food": float(np.std(foods)),
        "success_rate": float(np.mean(succ)),
        "food_per_agent": float(np.mean(per_agent)),
    }


def plot_scalability(df, scenario, label, sizes):
    """Gera o PNG a partir do DataFrame (mesmo formato do CSV escalabilidade_*.csv)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for algo in df["Algorithm"].unique():
        d = df[(df["Algorithm"] == algo) & (df["compatible"])].sort_values("N")
        if d.empty:
            continue
        ax.plot(d["N"], d["food_per_agent"], "o-", linewidth=2.5, markersize=8,
                color=PALETTE.get(algo, "#888"), label=algo)
    ax.set_title(f"Escalabilidade Zero-Shot — {label}\n(treino com N=20, sem retreino)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Número de agentes (N)", fontsize=11)
    ax.set_ylabel("Recolhas por agente (eficiência normalizada)", fontsize=11)
    ax.set_xticks(sizes)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(title="Algoritmo", fontsize=11)
    incompat = df[~df["compatible"]]["Algorithm"].unique()
    if len(incompat):
        fig.text(0.5, 0.01,
                 f"{', '.join(incompat)}: MLP de entrada fixa — incompatível com N≠20 "
                 "(só a GNN faz transferência Zero-Shot).",
                 ha="center", va="bottom", fontsize=8.5, color="#AA5500", style="italic")
        fig.subplots_adjust(bottom=0.13)
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    png_path = os.path.join(OUT_STATS, f"escalabilidade_zeroshot_{scenario}.png")
    plt.savefig(png_path, dpi=300)
    plt.close()
    return png_path


def main():
    parser = argparse.ArgumentParser(description="Sscale — Zero-Shot Transfer (N variavel)")
    parser.add_argument("--scenario", type=str, default="none")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--sizes", type=str, default="10,20,50,100",
                        help="Tamanhos de enxame separados por virgula")
    parser.add_argument("--replot", action="store_true",
                        help="Nao reavalia: regenera o PNG a partir do CSV existente "
                             "(usar quando os modelos no disco ja nao sao os da campanha)")
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    with open(config_path) as f:
        base_config = yaml.safe_load(f)
    label = SCENARIO_LABELS.get(args.scenario, args.scenario)

    if args.replot:
        csv_path = os.path.join(OUT_STATS, f"escalabilidade_{args.scenario}.csv")
        if not os.path.exists(csv_path):
            print(f"[!] {csv_path} nao existe — corre primeiro sem --replot.")
            sys.exit(1)
        df = pd.read_csv(csv_path)
        png_path = plot_scalability(df, args.scenario, label, sizes)
        print(f"  [OK] Grafico regenerado do CSV: {png_path}")
        return

    print(f"\n{'='*68}")
    print(f"  SSCALE — Zero-Shot Transfer  |  {label}")
    print(f"  Tamanhos: {sizes}  |  {args.episodes} episodios cada")
    print(f"{'='*68}")

    rows = []
    for algo in ALGOS:
        try:
            model = load_model(algo, args.scenario, config_path)
        except FileNotFoundError as e:
            print(f"\n[{algo.upper()}] modelo nao encontrado — saltado ({e})")
            continue
        print(f"\n--- {algo.upper()} ---")
        for n in sizes:
            res = eval_at_size(algo, model, base_config, args.scenario, n, args.episodes)
            if res is None:
                rows.append({"Algorithm": algo.upper(), "N": n, "mean_food": np.nan,
                             "success_rate": np.nan, "food_per_agent": np.nan,
                             "compatible": False})
                continue
            print(f"    N={n:3d}: recolhas={res['mean_food']:.2f}  "
                  f"sucesso={res['success_rate']*100:.0f}%  "
                  f"por_agente={res['food_per_agent']:.3f}")
            rows.append({"Algorithm": algo.upper(), "N": n,
                         "mean_food": round(res["mean_food"], 3),
                         "success_rate": round(res["success_rate"], 3),
                         "food_per_agent": round(res["food_per_agent"], 4),
                         "compatible": True})

    if not rows:
        print("\n[!] Nenhum modelo avaliado. Treina primeiro.")
        sys.exit(1)

    os.makedirs(OUT_STATS, exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_STATS, f"escalabilidade_{args.scenario}.csv")
    df.to_csv(csv_path, index=False)

    # Gráfico: recolhas por agente vs N (mede manutenção de eficiência ao escalar).
    png_path = plot_scalability(df, args.scenario, label, sizes)

    print(f"\n{'='*68}")
    print(f"  [OK] CSV     : {csv_path}")
    print(f"  [OK] Grafico : {png_path}")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    main()
