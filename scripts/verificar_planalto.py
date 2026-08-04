# -*- coding: utf-8 -*-
"""As curvas estabilizaram dentro do orçamento? — verificação da nota de leitura.

A dissertação compara três algoritmos com orçamentos de treino diferentes (195
minutos por execução do evolutivo, 48 do PPO/SAC). A validade dessa comparação
assenta numa afirmação: a de que cada paradigma atinge o seu planalto dentro do
orçamento concedido. Enquanto foi afirmada sem teste, foi o ponto mais frágil do
capítulo — e o mais fácil de atacar, porque os dados para a verificar estão
publicados no repositório.

O teste: para cada célula (cenário × algoritmo), compara-se, **por execução**, a
média do último quinto do orçamento (80--100%) com a do quinto anterior
(60--80%), e testa-se com um Wilcoxon emparelhado entre as 7 execuções. Uma
célula que ainda suba significativamente no fim não atingiu o planalto, e o seu
valor deve ler-se como limite inferior.

Nota de interpretação: a curva mede a **recompensa episódica**, que inclui o
shaping. Os históricos da campanha final não guardaram a métrica de tarefa
(`ep_task_mean`) — existe no código do treino, mas não nos CSV consolidados —,
pelo que um crescimento aqui não distingue "recolhe mais" de "farma mais
shaping". Isso está declarado na nota de leitura da dissertação.

Uso:  .venv/Scripts/python.exe scripts/verificar_planalto.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

from src.scenarios import SCENARIOS, SCENARIO_LABELS_SHORT  # noqa: E402

CURVAS = os.path.join(RAIZ, "results", "graficos_tese", "final_7d",
                      "all_curves_data_7d.csv")
ALGOS = ["GNN", "PPO", "SAC"]
# Uma célula conta como "ainda a subir" se o crescimento for significativo E
# materialmente relevante: subidas de 1-2% são significativas com 7 execuções
# emparelhadas e não põem em causa leitura nenhuma.
P_MAX, GANHO_MIN = 0.05, 5.0


def progresso(d):
    ss = d.groupby(["Scenario", "Algorithm", "Run"])["Step"].agg(["min", "max"])
    ss.columns = ["lo", "hi"]
    d = d.join(ss, on=["Scenario", "Algorithm", "Run"])
    d["tp"] = (d["Step"] - d["lo"]) / (d["hi"] - d["lo"]).clip(lower=1) * 100
    return d


def main():
    if not os.path.exists(CURVAS):
        print(f"[!] falta {os.path.relpath(CURVAS, RAIZ)}")
        return 1
    d = progresso(pd.read_csv(CURVAS))

    print("=" * 78)
    print("PLANALTO — o último quinto do orçamento contra o anterior, por execução")
    print("=" * 78)
    print(f"{'cenário':<26} {'algo':<5} {'60-80%':>10} {'80-100%':>10} "
          f"{'ganho':>8} {'p':>8}")
    subir = []
    for cen in SCENARIOS:
        for algo in ALGOS:
            sub = d[(d.Scenario == cen) & (d.Algorithm == algo)]
            antes, depois = [], []
            for _, g in sub.groupby("Run"):
                a = g[(g.tp >= 60) & (g.tp < 80)]["Score"].mean()
                b = g[g.tp >= 80]["Score"].mean()
                if np.isfinite(a) and np.isfinite(b):
                    antes.append(a)
                    depois.append(b)
            if len(antes) < 5:
                continue
            try:
                _, p = wilcoxon(depois, antes, alternative="greater")
            except ValueError:            # todos os pares iguais
                p = 1.0
            base = max(abs(np.mean(antes)), 1e-9)
            ganho = (np.mean(depois) - np.mean(antes)) / base * 100
            alerta = p < P_MAX and ganho > GANHO_MIN
            if alerta:
                subir.append((cen, algo, ganho, p))
            print(f"{SCENARIO_LABELS_SHORT.get(cen, cen):<26} {algo:<5} "
                  f"{np.mean(antes):10.0f} {np.mean(depois):10.0f} "
                  f"{ganho:7.1f}% {p:8.4f}" + ("   ← ainda a subir" if alerta else ""))

    print("-" * 78)
    print(f"{len(subir)} de 21 combinações ainda subiam no fim do orçamento.")
    if subir:
        print("Nestas, o valor do algoritmo é um LIMITE INFERIOR — está declarado")
        print("na nota de leitura da Secção 'Metodologia de Avaliação'.")
        for cen, algo, g, p in sorted(subir, key=lambda x: -x[2]):
            print(f"   {algo:<4} {SCENARIO_LABELS_SHORT.get(cen, cen):<26} "
                  f"{g:+6.0f}%  (p={p:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
