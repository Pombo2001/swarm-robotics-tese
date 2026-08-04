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
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")

from src.scenarios import (SCENARIOS as ALL_SCENARIOS,
                           SCENARIO_LABELS_SHORT as SCENARIO_LABELS, ALGO_COLORS)
ALGOS = ["GNN", "PPO", "SAC"]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns

    rows = []
    for sc in ALL_SCENARIOS:
        for algo in ALGOS:
            # Base = avaliação do MESMO modelo campeão sem falhas (mesmas seeds da
            # fail10) — não o eval_summary.csv, que entretanto passou a agregar as
            # 7 runs da campanha e deixaria de estar emparelhado com a fail10.
            bp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{sc}.csv")
            fp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{sc}_fail10.csv")
            if not (os.path.exists(bp) and os.path.exists(fp)):
                continue
            b = pd.read_csv(bp)
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

    # Só entram os cenários com dados nos TRÊS algoritmos. O src/scenarios.py
    # passou a incluir o mapa grande (8.º cenário), que só tem avaliação do GNN:
    # desenhá-lo daria uma coluna cheia e duas vazias, e punha na figura da tese
    # um cenário que a campanha dos sete não reporta — o pré-registo do mapa
    # grande manda-o para uma secção própria, com dados próprios.
    completos = {s for s, g in df.groupby("Scenario") if len(set(g.Algorithm)) == len(ALGOS)}
    omitidos = sorted(set(df.Scenario) - completos)
    if omitidos:
        print(f"[ROBUSTEZ] omitidos (sem os três algoritmos): {', '.join(omitidos)}")
    df = df[df.Scenario.isin(completos)]

    sns.set_theme(style="whitegrid")
    # sharey=True porque os três painéis medem a MESMA coisa na MESMA unidade
    # (recolhas por episódio). Com eixos independentes, o Gargalo do PPO (123
    # recolhas) desenhava-se com a mesma altura que o do GNN (88) e a figura
    # convidava a uma comparação entre painéis que as escalas desmentiam.
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
    scen_order = [SCENARIO_LABELS[s] for s in ALL_SCENARIOS
                  if SCENARIO_LABELS[s] in completos]
    x = np.arange(len(scen_order))
    w = 0.38
    # Folga do rótulo, em unidades do eixo: 1,5% do maior valor desenhado (com o
    # eixo partilhado, o mesmo valor serve os três painéis).
    folga = 0.015 * float((df.fail_m + df.fail_sd.fillna(0)).max())
    for ax, algo in zip(axes, ALGOS):
        d = df[df.Algorithm == algo].set_index("Scenario").reindex(scen_order)
        c = ALGO_COLORS[algo]
        ax.bar(x - w / 2, d.base_m, w, yerr=d.base_sd, capsize=3,
               color=c, label="Sem falhas")
        ax.bar(x + w / 2, d.fail_m, w, yerr=d.fail_sd, capsize=3,
               color=c, alpha=0.45, hatch="//", label="10% falhas")
        # Retenção (%) por cima das barras com falhas — acima do TOPO DA BARRA DE
        # ERRO, não do topo da barra: colado à barra, o rótulo caía em cima do
        # bigode do desvio padrão e ficava ilegível em metade dos cenários.
        for xi, (bm, fm, fsd) in enumerate(zip(d.base_m, d.fail_m, d.fail_sd)):
            if bm and bm > 0.5:
                topo = fm + (fsd if np.isfinite(fsd) else 0.0)
                ax.text(xi + w / 2, topo + folga, f"{fm / bm * 100:.0f}%",
                        ha="center", va="bottom", fontsize=8)
        ax.set_title(algo, fontweight="bold", color=c)
        ax.set_xticks(x)
        ax.set_xticklabels(scen_order, rotation=30, ha="right", fontsize=8)
        ax.legend(fontsize=8)
        ax.set_ylabel("Recolhas por episódio" if algo == "GNN" else "")
    fig.suptitle("Robustez a Falhas de Agentes (Rrobust) — 10% dos agentes falham a meio do episódio",
                 fontweight="bold")
    fig.text(0.5, 0.005,
             "Avaliação determinística emparelhada (20 episódios, mesmas seeds); "
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
