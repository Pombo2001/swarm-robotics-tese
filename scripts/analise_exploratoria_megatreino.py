# -*- coding: utf-8 -*-
"""As análises EXPLORATÓRIAS do mega-treino — as que o pré-registo prometeu.

O `analise_megatreino.py` produz os testes confirmatórios M1-M3 (Muro em U e
bypass), que são os que entraram na dissertação. Mas o pré-registo
(`docs/PRE_REGISTO_MEGATREINO.md`) tem mais duas coisas:

  «Todos os runs, todas as configs, todas as fases — sem exceção nem
   subconjuntos.»  (Compromissos de reporte, ponto 1)

e uma secção *Exploratório (rotulado; sem regra de decisão binária)* com três
perguntas por responder: a ablação do anneal (B1-B4), o Sandbox adaptativo (A5)
e a Perceção adaptativa (B7). A fase B6 (SAC no Gargalo) é a quarta célula que
ficou fora dos confirmatórios.

Sem este relatório, a dissertação reporta o subconjunto favorável de uma
campanha pré-registada — exatamente o que o pré-registo existe para impedir.
Estas células não têm regra de decisão binária: descrevem-se, com o δ de Cliff
como âncora, e sem transformar um p em veredicto.

Uso:  .venv/Scripts/python.exe scripts/analise_exploratoria_megatreino.py
      .venv/Scripts/python.exe scripts/analise_exploratoria_megatreino.py --json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEGA = os.path.join(RAIZ, "results", "mega_1mes")
ADAPT = os.path.join(RAIZ, "results", "novelty_adaptativo")
FINAL7D = os.path.join(RAIZ, "results", "graficos_tese", "final_7d",
                       "eval_medias_por_run_7d.csv")

# Cada fase da stream B com a sua configuração de anneal (do pré-registo).
ABLACAO = {
    "mega_B_fase1": "sustain=5",
    "mega_B_fase2": "sustain=20",
    "mega_B_fase3": "decay=0,95",
    "mega_B_fase4": "decay=0,995",
}
DEFAULT_ANNEAL = "sustain=10, decay=0,98"


def cliffs_delta(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b):
        return float("nan")
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return float(gt - lt) / (len(a) * len(b))


def _por_run(caminho, cenario=None, algoritmo=None):
    """Médias por execução (a unidade estatística) de um eval_by_run.csv."""
    d = pd.read_csv(caminho)
    if cenario:
        d = d[d.Scenario == cenario]
    if algoritmo:
        d = d[d.Algorithm == algoritmo]
    if d.empty:
        return None
    g = d.groupby("Run")
    return pd.DataFrame({
        "recolhas": g["food_collected"].mean(),
        "sucesso": g["success"].mean(),
    })


def _fase(nome, cenario=None, algoritmo=None):
    padrao = os.path.join(MEGA, nome, "**", "eval_by_run.csv")
    fs = glob.glob(padrao, recursive=True)
    return _por_run(fs[0], cenario, algoritmo) if fs else None


def _semana(nome, cenario, algoritmo="GNN"):
    padrao = os.path.join(ADAPT, nome, "**", "eval_by_run.csv")
    fs = glob.glob(padrao, recursive=True)
    return _por_run(fs[0], cenario, algoritmo) if fs else None


def _sete_dias(cenario, algoritmo):
    d = pd.read_csv(FINAL7D)
    d = d[(d.Scenario == cenario) & (d.Algorithm == algoritmo)]
    return d.rename(columns={"recolhas": "recolhas"})[["recolhas", "sucesso"]]


def _linha(rot, df):
    if df is None or df.empty:
        return f"  {rot:<34} —"
    conv = int((df["sucesso"] == 1).sum())
    return (f"  {rot:<34} n={len(df):>2}  {df['recolhas'].mean():6.1f} ± "
            f"{df['recolhas'].std(ddof=1):5.1f}   {conv}/{len(df)} a 100%")


def _comparar(a, b, rot_a, rot_b):
    if a is None or b is None or a.empty or b.empty:
        return None
    u, p = mannwhitneyu(a["recolhas"], b["recolhas"], alternative="two-sided")
    return {"p": float(p), "delta": cliffs_delta(a["recolhas"], b["recolhas"]),
            "a": rot_a, "b": rot_b}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true",
                    help="escreve o resumo em results/mega_1mes/resumo_exploratorio.json")
    args = ap.parse_args()

    saida = {}
    linhas = []

    def p(s=""):
        linhas.append(s)
        print(s)

    p("=" * 76)
    p("MEGA-TREINO — CÉLULAS EXPLORATÓRIAS (pré-registo, secção 'Exploratório')")
    p("=" * 76)
    p("Sem regra de decisão binária: descreve-se, com o δ de Cliff como âncora.")
    p("")

    # ── E1. Ablação do anneal ───────────────────────────────────────────────
    p("E1. ABLAÇÃO DO ANNEAL — a dosagem adaptativa é sensível ao seu ajuste?")
    p("-" * 76)
    saida["ablacao"] = {}
    for cen, rot_cen in (("u_wall", "Muro em U"),
                         ("cooperative_door_bypass", "Porta c/ Alternativa")):
        p(f"  · {rot_cen}")
        base = _semana("week_A_fase1" if cen == "u_wall" else "week_B_fase1", cen)
        p(_linha(f"default ({DEFAULT_ANNEAL})", base))
        for fase, cfg in ABLACAO.items():
            df = _fase(fase, cen, "GNN")
            p(_linha(cfg, df))
            if df is not None and base is not None:
                c = _comparar(df, base, cfg, "default")
                saida["ablacao"].setdefault(cen, {})[cfg] = {
                    "n": len(df), "media": float(df["recolhas"].mean()),
                    "dp": float(df["recolhas"].std(ddof=1)),
                    "convergentes": int((df["sucesso"] == 1).sum()),
                    "vs_default": c,
                }
        p("")

    # ── E2. Sandbox adaptativo (A5) ─────────────────────────────────────────
    p("E2. SANDBOX ADAPTATIVO (A5) — a novidade reduz os runs degenerados em aberto?")
    p("-" * 76)
    a5 = _fase("mega_A_fase5", "none", "GNN")
    obj7 = _sete_dias("none", "GNN")
    p(_linha("adaptativo (mega-treino)", a5))
    p(_linha("objetivo (campanha de 7 dias)", obj7))
    c = _comparar(a5, obj7, "adaptativo n=21", "objetivo n=7")
    if c:
        p(f"  Mann-Whitney p={c['p']:.4f}   δ={c['delta']:+.2f}")
        saida["sandbox_A5"] = {"n": len(a5), "media": float(a5["recolhas"].mean()),
                               "dp": float(a5["recolhas"].std(ddof=1)),
                               "convergentes": int((a5["sucesso"] == 1).sum()),
                               "vs_objetivo_7d": c}
    p("")

    # ── E3. Perceção Cooperativa (B7) ───────────────────────────────────────
    p("E3. PERCEÇÃO COOPERATIVA (B7) — o 5/7 de 19 jul era acaso ou custo real?")
    p("-" * 76)
    b7 = _fase("mega_B_fase7", "cooperative_perception", "GNN")
    jul = _semana("week_B_fase1", "cooperative_perception")
    obj = _sete_dias("cooperative_perception", "GNN")
    p(_linha("adaptativo (mega-treino)", b7))
    p(_linha("adaptativo (19 jul, n=7)", jul))
    p(_linha("objetivo (campanha de 7 dias)", obj))
    c = _comparar(b7, obj, "adaptativo n=21", "objetivo n=7")
    if c:
        p(f"  Mann-Whitney p={c['p']:.4f}   δ={c['delta']:+.2f}")
        saida["percecao_B7"] = {"n": len(b7), "media": float(b7["recolhas"].mean()),
                                "dp": float(b7["recolhas"].std(ddof=1)),
                                "convergentes": int((b7["sucesso"] == 1).sum()),
                                "vs_objetivo_7d": c}
    p("")

    # ── E4. SAC no Gargalo (B6) ─────────────────────────────────────────────
    p("E4. SAC NO GARGALO (B6) — a célula 5/7 da campanha final, com n=21")
    p("-" * 76)
    b6 = _fase("mega_B_fase6", "bottleneck", "SAC")
    sac7 = _sete_dias("bottleneck", "SAC")
    p(_linha("SAC (mega-treino, orçamento 48 min)", b6))
    p(_linha("SAC (campanha de 7 dias, 195 min)", sac7))
    if b6 is not None:
        saida["sac_gargalo_B6"] = {
            "n": len(b6), "media": float(b6["recolhas"].mean()),
            "dp": float(b6["recolhas"].std(ddof=1)),
            "convergentes": int((b6["sucesso"] == 1).sum()),
            "nota": "orçamento por execução de 48 min (não 195) — ver pré-registo B6",
        }
    p("")
    p("=" * 76)

    if args.json:
        destino = os.path.join(MEGA, "resumo_exploratorio.json")
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(saida, f, ensure_ascii=False, indent=1)
        print(f"[OK] {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
