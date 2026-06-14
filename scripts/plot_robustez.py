# -*- coding: utf-8 -*-
"""Rrobust — gráfico de robustez a falhas de agentes.

Compara as recolhas por episódio da avaliação base (eval_summary.csv) com a
avaliação com 10% de falhas a meio do episódio (eval_{algo}_{cen}_fail10.csv).
As duas avaliações usam as mesmas seeds (emparelhadas), pelo que a diferença
mede só o efeito das falhas. Gera results/evaluation/robustez_falhas.png.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")

ALL_SCENARIOS = ["none", "u_wall", "bottleneck", "four_rooms",
                 "cooperative_door", "cooperative_perception"]
SCENARIO_LABELS = {
    "none": "Sandbox", "u_wall": "Beco Sem Saída (U)", "bottleneck": "Gargalo",
    "four_rooms": "Quatro Salas", "cooperative_door": "Porta Cooperativa",
    "cooperative_perception": "Perceção Cooperativa",
}
ALGOS = ["GNN", "PPO", "SAC"]
ALGO_COLORS = {"GNN": "#2E7D32", "PPO": "#E65100", "SAC": "#0277BD"}


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns

    base = pd.read_csv(os.path.join(EVAL_DIR, "eval_summary.csv"))

    rows = []
    for sc in ALL_SCENARIOS:
        for algo in ALGOS:
            b = base[(base.Scenario == sc) & (base.Algorithm == algo)]
            fp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{sc}_fail10.csv")
            if b.empty or not os.path.exists(fp):
                continue
            f = pd.read_csv(fp)
            rows.append({
                "Scenario": SCENARIO_LABELS[sc], "Algorithm": algo,
                "base_m": b.food_collected.mean(), "base_sd": b.food_collected.std(),
                "fail_m": f.food_collected.mean(), "fail_sd": f.food_collected.std(),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        print("[ROBUSTEZ] Sem dados — corre a avaliação base e a fail10 primeiro.")
        return

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=False)
    scen_order = [SCENARIO_LABELS[s] for s in ALL_SCENARIOS]
    x = np.arange(len(scen_order))
    w = 0.38
    for ax, algo in zip(axes, ALGOS):
        d = df[df.Algorithm == algo].set_index("Scenario").reindex(scen_order)
        c = ALGO_COLORS[algo]
        ax.bar(x - w / 2, d.base_m, w, yerr=d.base_sd, capsize=3,
               color=c, label="Sem falhas")
        ax.bar(x + w / 2, d.fail_m, w, yerr=d.fail_sd, capsize=3,
               color=c, alpha=0.45, hatch="//", label="10% falhas")
        # retenção (%) por cima das barras com falhas
        for xi, (bm, fm) in enumerate(zip(d.base_m, d.fail_m)):
            if bm and bm > 0.5:
                ax.text(xi + w / 2, fm, f"{fm / bm * 100:.0f}%",
                        ha="center", va="bottom", fontsize=8)
        ax.set_title(algo, fontweight="bold", color=c)
        ax.set_xticks(x)
        ax.set_xticklabels(scen_order, rotation=30, ha="right", fontsize=8)
        ax.legend(fontsize=8)
        ax.set_ylabel("Recolhas por episódio" if algo == "GNN" else "")
    fig.suptitle("Robustez a Falhas de Agentes (Rrobust) — 10% dos agentes falham a meio do episódio",
                 fontweight="bold")
    fig.text(0.5, 0.005,
             "Avaliação determinística emparelhada (30 episódios, mesmas seeds); "
             "rótulo = % de recolhas retidas face à avaliação sem falhas.",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    out = os.path.join(EVAL_DIR, "robustez_falhas.png")
    fig.savefig(out, dpi=300)
    print(f"[OK] {out}")

    res = df.copy()
    res["retencao_%"] = (res.fail_m / res.base_m.replace(0, np.nan) * 100).round(1)
    print(res[["Scenario", "Algorithm", "base_m", "fail_m", "retencao_%"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
