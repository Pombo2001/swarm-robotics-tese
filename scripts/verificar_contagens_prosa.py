# -*- coding: utf-8 -*-
"""As contagens em PROSA da tese (X/Y execuções) batem com os dados?

Porque existe
-------------
O `verificar_numeros_tese.py` compara as TABELAS com os CSV — 346 valores. As
afirmações em prosa não tinham verificador nenhum, e é aí que os erros têm
aparecido: a 4 ago o «planalto» que sete células não atingiam, a 5 ago a linha do
tempo do dashboard e um custo de percurso medido com a régua errada.

Este script cobre as contagens da campanha final (7 execuções por célula), que
são as que sustentam a resposta à QI1 e a discussão da variância:

  · «15 das 21 combinações atingem 100% de sucesso em todos os runs»
  · «Sandbox: 5/7 runs funcionais; Perceção Cooperativa: 6/7»
  · «Muro em U: GNN 3/7, PPO 4/7, SAC 2/7»
  · «Gargalo: SAC apenas 5/7»

Lê os números DO `.tex` (por regex, com o contexto à volta) e recalcula-os do
`eval_by_run_7d.csv`. Fixá-los no script seria verificar o script contra si
próprio — o defeito que a primeira versão do verificador principal tinha.

Uso:
    .venv/Scripts/python.exe scripts/verificar_contagens_prosa.py
"""
import os
import re
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(RAIZ, "Tese", "main.tex")
CSV = os.path.join(RAIZ, "results", "graficos_tese", "final_7d", "eval_by_run_7d.csv")

falhas = []


def _corpo():
    t = open(TEX, encoding="utf-8").read()
    i0, i1 = t.find(r"\begin{document}"), t.find(r"\appendix")
    return re.sub(r"(?<!\\)%.*", "", t[i0:i1 if i1 > 0 else len(t)])


def _runs_a_100(d, cenario, algo):
    """Execuções em que TODOS os episódios tiveram pelo menos uma recolha."""
    sub = d[(d["Scenario"] == cenario) & (d["Algorithm"] == algo)]
    if sub.empty:
        return None, 0
    por_run = sub.groupby("Run")["success"].mean()
    return int((por_run >= 1.0).sum()), len(por_run)


def compara(rotulo, obtido, na_tese):
    ok = obtido == na_tese
    print(f"  {'[v]' if ok else '[X]'} {rotulo:<52} dados {obtido}   tese {na_tese}")
    if not ok:
        falhas.append(f"{rotulo}: dados dizem {obtido}, a tese diz {na_tese}")


def main():
    if not os.path.exists(CSV):
        print(f"[!] sem {CSV}")
        return 1
    d = pd.read_csv(CSV)
    corpo = _corpo()

    print("=" * 78)
    print("CONTAGENS EM PROSA  vs  eval_by_run_7d.csv")
    print("=" * 78)

    # ── «15 das 21 combinações a 100% em todos os runs e episódios» ─────────
    m = re.search(r"\\textbf\{(\d+) das (\d+) combinações algoritmo--cenário "
                  r"atingem 100\\% de sucesso", corpo)
    if not m:
        falhas.append("não encontrei a frase das «N das M combinações» na tese")
    else:
        na_tese, total_tese = int(m.group(1)), int(m.group(2))
        celulas = d.groupby(["Scenario", "Algorithm"])
        perfeitas = sum(1 for _, sub in celulas
                        if (sub.groupby("Run")["success"].mean() >= 1.0).all())
        compara("combinações com 100% em todos os runs", perfeitas, na_tese)
        compara("total de combinações", len(celulas), total_tese)

    # ── As frações por célula que a prosa cita ──────────────────────────────
    # (rótulo na tese, cenário, algoritmo) — o padrão procura a fração junto ao
    # rótulo, para não apanhar um «5/7» de outro sítio.
    CASOS = [
        (r"Sandbox: (\d)/(\d) \\textit\{runs\} funcionais", "none", "GNN",
         "Sandbox GNN"),
        (r"Perceção Cooperativa: (\d)/(\d)\)", "cooperative_perception", "GNN",
         "Perceção Cooperativa GNN"),
        (r"GNN (\d)/(\d) \\textit\{runs\}, PPO", "u_wall", "GNN", "Muro em U GNN"),
        (r"\\textit\{runs\}, PPO (\d)/(\d), SAC", "u_wall", "PPO", "Muro em U PPO"),
        (r"PPO \d/\d, SAC (\d)/(\d)\)", "u_wall", "SAC", "Muro em U SAC"),
        (r"no Gargalo apenas (\d)/(\d) \\textit\{runs\} convergem", "bottleneck",
         "SAC", "Gargalo SAC"),
        (r"e no Muro (?:em )?U apenas (\d)/(\d)", "u_wall", "SAC", "Muro em U SAC (2.ª menção)"),
    ]
    for padrao, cenario, algo, rotulo in CASOS:
        m = re.search(padrao, corpo)
        if not m:
            falhas.append(f"não encontrei na tese a frase de «{rotulo}»")
            print(f"  [X] {rotulo:<52} (frase não encontrada no .tex)")
            continue
        na_tese, total_tese = int(m.group(1)), int(m.group(2))
        obtido, total = _runs_a_100(d, cenario, algo)
        compara(f"{rotulo} — runs a 100%", obtido, na_tese)
        compara(f"{rotulo} — nº de execuções", total, total_tese)

    print()
    print("=" * 78)
    if falhas:
        for f in falhas:
            print(f"  DIVERGE  {f}")
        print(f"\n{len(falhas)} divergência(s)")
        return 1
    print("  As contagens em prosa batem com o CSV da campanha final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
