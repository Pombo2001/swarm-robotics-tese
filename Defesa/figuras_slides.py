# -*- coding: utf-8 -*-
"""Figuras desenhadas para PROJEÇÃO, para os slides da QI1, da bimodalidade e da QI3.

Porquê não as figuras da tese
As da tese são desenhadas para uma página A4 lida de perto: letra de 8–10 pt,
sete rótulos de cenário rodados, e a robustez em três painéis empilhados.
Encolhidas para metade de um slide e atiradas para uma parede, os eixos e as
legendas ficam ilegíveis — a sala vê barras coloridas e mais nada. Estas são as
MESMAS contas, sobre os MESMOS CSV, com outra forma: barras horizontais (o nome
do cenário lê-se sem rodar a cabeça), letra de 15–17 pt e uma só mensagem por
figura.

Os números não são escritos aqui: saem dos CSV de onde saem os quadros da tese
(`final_7d/eval_by_run_7d.csv` e as avaliações emparelhadas de robustez em
`results/evaluation/`), e o script confere no fim os valores que os slides citam.

Uso: .venv/Scripts/python.exe Defesa/figuras_slides.py   (antes do gerar_slides.py)
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
from src.scenarios import THESIS_SCENARIOS, SCENARIO_LABELS_SHORT, ALGO_COLORS  # noqa: E402

SAIDA = os.path.join(RAIZ, "Defesa", ".assets")
EVAL = os.path.join(RAIZ, "results", "graficos_tese", "final_7d", "eval_by_run_7d.csv")
ROB = os.path.join(RAIZ, "results", "evaluation")
ALGOS = ["GNN", "PPO", "SAC"]
ROT = {"GNN": "GNN evolutivo", "PPO": "PPO", "SAC": "SAC"}

plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 17, "axes.labelsize": 15,
    "xtick.labelsize": 14, "ytick.labelsize": 15, "legend.fontsize": 14,
    "axes.spines.top": False, "axes.spines.right": False,
})


def _por_execucao():
    ev = pd.read_csv(EVAL)
    return (ev.groupby(["Scenario", "Algorithm", "Run"])
              .agg(cheg=("food_collected", "mean"), suc=("success", "mean"))
              .reset_index())


def _guardar(fig, nome):
    os.makedirs(SAIDA, exist_ok=True)
    p = os.path.join(SAIDA, nome)
    fig.savefig(p, dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("[v] Defesa/.assets/%s" % nome)
    return p


def qi1_chegadas(r):
    """Chegadas por episódio, média ± dp das 7 execuções, cenário a cenário."""
    cen = list(reversed(THESIS_SCENARIOS))  # de cima para baixo, pela ordem da tese
    y = np.arange(len(cen))
    h = 0.26
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    for k, a in enumerate(ALGOS):
        g = r[r.Algorithm == a].groupby("Scenario").cheg
        m, s = g.mean().reindex(cen), g.std().reindex(cen)
        ax.barh(y + (1 - k) * h, m, h, xerr=s, color=ALGO_COLORS[a], label=ROT[a],
                error_kw={"elinewidth": 1.2, "capsize": 2.5, "ecolor": "#333"})
    ax.set_yticks(y, [SCENARIO_LABELS_SHORT[c] for c in cen])
    ax.set_xlabel("Chegadas por episódio (média ± dp de 7 execuções)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False)
    return _guardar(fig, "slide_qi1_chegadas.png")


def bimodal(r):
    """Uma linha por algoritmo, um ponto por execução: Muro em U e Sandbox."""
    fig, eixos = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=False)
    rng = np.random.default_rng(7)
    for ax, c in zip(eixos, ["u_wall", "none"]):
        for k, a in enumerate(ALGOS):
            d = r[(r.Scenario == c) & (r.Algorithm == a)]
            yk = 2 - k
            ax.scatter(d.cheg, yk + rng.uniform(-0.28, 0.28, len(d)), s=70,
                       color=ALGO_COLORS[a], edgecolor="white", linewidth=1, zorder=3)
            ax.plot([d.cheg.mean()] * 2, [yk - 0.32, yk + 0.32], color="#222", lw=2.5, zorder=2)
            ax.text(1.01, yk, "%d/7" % int((d.suc >= 1).sum()), transform=ax.get_yaxis_transform(),
                    va="center", fontsize=14, color="#444")
        ax.set_yticks([2, 1, 0], ALGOS)
        ax.set_ylim(-0.6, 2.6)
        ax.set_title(SCENARIO_LABELS_SHORT[c], loc="left", fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        ax.set_xlim(left=-3)
    eixos[-1].set_xlabel("Chegadas por episódio (1 ponto = 1 execução; barra = média)")
    fig.text(0.985, 0.985, "a 100 %", ha="right", va="top", fontsize=13, color="#444")
    fig.tight_layout(h_pad=1.2)
    return _guardar(fig, "slide_bimodal.png")


def robustez():
    """Retenção de chegadas com 10 % de falhas, emparelhada com a avaliação base."""
    linhas = []
    for c in THESIS_SCENARIOS:
        for a in ALGOS:
            b = os.path.join(ROB, "eval_%s_%s.csv" % (a.lower(), c))
            f = os.path.join(ROB, "eval_%s_%s_fail10.csv" % (a.lower(), c))
            if os.path.exists(b) and os.path.exists(f):
                base = pd.read_csv(b).food_collected.mean()
                falha = pd.read_csv(f).food_collected.mean()
                linhas.append((c, a, 100.0 * falha / base))
    df = pd.DataFrame(linhas, columns=["Scenario", "Algorithm", "ret"])
    cen = list(reversed(THESIS_SCENARIOS))
    y = np.arange(len(cen))
    h = 0.26
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    for k, a in enumerate(ALGOS):
        v = df[df.Algorithm == a].set_index("Scenario").ret.reindex(cen)
        ax.barh(y + (1 - k) * h, v, h, color=ALGO_COLORS[a], label=ROT[a])
    ax.axvline(100, color="#222", lw=1.5, ls="--")
    ax.text(100.4, -0.55, "100 % = imune", fontsize=13, va="center", color="#222")
    ax.set_xlim(80, 110)
    ax.set_yticks(y, [SCENARIO_LABELS_SHORT[c] for c in cen])
    ax.set_xlabel("Chegadas retidas com 10 % de falhas (%)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False)
    _guardar(fig, "slide_robustez.png")
    return df


def main():
    r = _por_execucao()
    qi1_chegadas(r)
    bimodal(r)
    df = robustez()
    # Os valores que os slides citam em texto, conferidos contra o que se desenhou.
    lo, hi = df.ret.min(), df.ret.max()
    assert round(lo) == 92 and round(hi) == 106, (lo, hi)
    m = r.groupby(["Scenario", "Algorithm"]).cheg.mean()
    assert round(m["four_rooms", "GNN"], 1) == 59.8 and round(m["none", "PPO"], 1) == 71.5
    uw = r[(r.Scenario == "u_wall") & (r.Algorithm == "GNN")]
    assert int((uw.suc >= 1).sum()) == 3 and int((uw.cheg == 0).sum()) == 4
    print("[v] retenção %.0f–%.0f %%, médias e contagens batem com os slides" % (lo, hi))


if __name__ == "__main__":
    main()
