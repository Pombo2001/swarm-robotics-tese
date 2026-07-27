"""Análise pré-registada do MAPA GRANDE (docs/PRE_REGISTO_MAPA_GRANDE.md).

Escrito a 27 jul 2026, com o F1 a correr e o F2 por lançar. Pelas mesmas razões
do `analise_megatreino.py`: quando os dados existirem, a análise corre em minutos
e nenhum teste é escolhido depois de ver o número.

Cobre as duas fases:

  F1 — zero-shot de topologia (`zeroshot_mapa_grande.csv`)
       grelha 7 cenários de origem × 3 algoritmos, nas QUATRO condições
       pré-registadas (natural, escala, sem obstáculos, sem features da porta).
       A leitura está pré-comprometida: se uma condição de controlo der O MESMO
       que a natural, essa causa está excluída e reporta-se só a natural; se
       DIVERGIR, o zero-shot está confundido com essa causa e é isso que se
       reporta — sem escolher a condição que dá o número melhor.

  F2 — treino nativo (`eval_by_run.csv`), M1-M3:
       M1  GNN vs PPO e GNN vs SAC, bilateral, médias por run (n=7)
       M2  convergência: runs com ≥1 recolha e runs a 100% (DESCRITIVO — com
           n=7 não se faz inferência sobre proporções)
       M3  uso da porta cooperativa, por algoritmo (descritivo + δ)

Regra de decisão da QI7 (pré-comprometida, §4 do pré-registo): sobe a resultado
se F2 der ≥5/7 runs convergentes em pelo menos um algoritmo E M1 for
interpretável. Caso contrário, resultado negativo honesto — que é reportado na
mesma e NÃO se repete com parâmetros diferentes à procura de número melhor.

Uso:
    python scripts/analise_mapa_grande.py --verificar
    python scripts/analise_mapa_grande.py
"""
import argparse
import os
import sys
from itertools import combinations

import pandas as pd

try:
    from scipy.stats import mannwhitneyu
except ImportError:  # pragma: no cover
    print("!! scipy em falta: pip install scipy")
    raise

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F1_CSV = os.path.join(BASE, "results", "evaluation", "zeroshot_mapa_grande.csv")
F2_CSV = os.path.join(BASE, "results", "mapa_grande", "evaluation", "eval_by_run.csv")

ALGOS = ["GNN", "PPO", "SAC"]
CONDICOES = {
    ("mapa", "base"): "natural (principal)",
    ("treino", "base"): "escala da observação",
    ("mapa", "sem_obstaculos"): "sem obstáculos",
    ("mapa", "sem_porta_obs"): "sem features da porta",
}


def cliffs_delta(a, b):
    n = 0
    for x in a:
        for y in b:
            n += (x > y) - (x < y)
    return n / (len(a) * len(b))


def _col(df, *nomes):
    for n in nomes:
        if n in df.columns:
            return n
    return None


# ── F1 ───────────────────────────────────────────────────────────────────────

def analisar_f1():
    print("=" * 78)
    print("F1 — ZERO-SHOT DE TOPOLOGIA")
    print("=" * 78)
    if not os.path.exists(F1_CSV):
        print("  SEM DADOS: %s" % os.path.relpath(F1_CSV, BASE))
        return
    df = pd.read_csv(F1_CSV)
    c_alg = _col(df, "Algoritmo", "Algorithm", "Algo")
    c_org = _col(df, "Origem", "TreinadoEm", "Scenario")
    c_food = _col(df, "food_collected", "Recolhas", "FoodMean")
    c_norm = _col(df, "NormObs", "norm_obs")
    c_ctrl = _col(df, "Controlo", "controlo")
    if not all([c_alg, c_org, c_food]):
        print("  !! colunas inesperadas: %s" % list(df.columns))
        return

    for (norm, ctrl), rotulo in CONDICOES.items():
        sub = df
        if c_norm:
            sub = sub[sub[c_norm] == norm]
        if c_ctrl:
            sub = sub[sub[c_ctrl] == ctrl]
        if sub.empty:
            print("\n  [%s] SEM DADOS" % rotulo)
            continue
        print("\n  ── %s ──" % rotulo)
        tab = sub.pivot_table(index=c_org, columns=c_alg, values=c_food,
                              aggfunc="mean")
        print(tab.round(1).to_string())
        print("    média por algoritmo: %s"
              % ", ".join("%s %.2f" % (a, tab[a].mean())
                          for a in tab.columns))
        zeros = int((tab.fillna(0) == 0).sum().sum())
        print("    células a zero absoluto: %d de %d" % (zeros, tab.size))

    print()
    print("  LEITURA PRÉ-COMPROMETIDA: uma condição de controlo que dê O MESMO")
    print("  que a natural exclui essa causa (vai para apêndice); uma que DIVIRJA")
    print("  mostra que o zero-shot está confundido com ela — e é isso que se")
    print("  reporta. Um controlo que ressuscite os campeões NÃO salva a leitura")
    print("  'a topologia é dura': desmente-a.")


# ── F2 ───────────────────────────────────────────────────────────────────────

def analisar_f2():
    print()
    print("=" * 78)
    print("F2 — TREINO NATIVO")
    print("=" * 78)
    if not os.path.exists(F2_CSV):
        print("  SEM DADOS: %s" % os.path.relpath(F2_CSV, BASE))
        print("  (a campanha só arranca depois do mega-treino, ~3 ago)")
        return
    df = pd.read_csv(F2_CSV)
    c_alg = _col(df, "Algorithm", "Algoritmo", "Algo")
    c_run = _col(df, "Run", "run")
    c_food = _col(df, "food_collected", "Recolhas")
    c_suc = _col(df, "success", "Sucesso")
    c_porta = _col(df, "door_opened", "PortaAberta", "door")

    por_algo = {}
    for algo in ALGOS:
        sub = df[df[c_alg].str.upper() == algo] if c_alg else df
        if sub.empty:
            continue
        g = sub.groupby(c_run).agg(food=(c_food, "mean"),
                                   suc=(c_suc, "mean") if c_suc else (c_food, "mean"))
        por_algo[algo] = g.sort_index()

    if not por_algo:
        print("  !! nenhum algoritmo encontrado no CSV")
        return

    print("\n  M2 — convergência (DESCRITIVO; com n=7 não se infere sobre proporções)")
    for algo, g in por_algo.items():
        com_recolha = int((g["food"] > 0).sum())
        a_100 = int((g["suc"] >= 1.0).sum()) if c_suc else 0
        print("    %-4s n=%-2d  %6.1f ± %5.1f   ≥1 recolha: %d/%d   100%%: %d/%d"
              % (algo, len(g), g["food"].mean(), g["food"].std(),
                 com_recolha, len(g), a_100, len(g)))

    print("\n  M1 — magnitude (Mann-Whitney bilateral sobre médias por run)")
    for x, y in combinations([a for a in ALGOS if a in por_algo], 2):
        a, b = por_algo[x]["food"], por_algo[y]["food"]
        U, p = mannwhitneyu(a, b, alternative="two-sided", method="exact")
        d = cliffs_delta(list(a), list(b))
        print("    %-4s vs %-4s   p = %.4f   δ = %+.2f" % (x, y, p, d))
    print("    (expectativa pré-registada: a GNN NÃO é inferior a nenhum dos dois;")
    print("     não foi pré-registada superioridade)")

    if c_porta:
        print("\n  M3 — uso da porta cooperativa")
        for algo in por_algo:
            sub = df[df[c_alg].str.upper() == algo]
            print("    %-4s fração de episódios com porta aberta: %.2f"
                  % (algo, sub[c_porta].mean()))
    else:
        print("\n  M3 — coluna da porta ausente do CSV (%s); registar porquê." % c_porta)

    print()
    print("  REGRA DE DECISÃO DA QI7 (pré-comprometida):")
    max_conv = max(int((g["food"] > 0).sum()) for g in por_algo.values())
    if max_conv >= 5:
        print("    ≥5/7 runs convergentes em pelo menos um algoritmo (%d) →" % max_conv)
        print("    a QI7 SOBE A RESULTADO: secção nova no Cap. de Resultados + QI7 nas")
        print("    Conclusões, desde que M1 seja interpretável.")
    else:
        print("    máximo de %d/7 runs convergentes → resultado NEGATIVO honesto." % max_conv)
        print("    Reporta-se na mesma: evidencia o limite dos três métodos sob")
        print("    composição+escala. NÃO se repete a campanha com outros parâmetros.")


def verificar():
    print("=" * 78)
    print("DADOS ESPERADOS DO MAPA GRANDE")
    print("=" * 78)
    for nome, fp in (("F1 zero-shot", F1_CSV), ("F2 treino nativo", F2_CSV)):
        existe = os.path.exists(fp)
        extra = ""
        if existe:
            try:
                d = pd.read_csv(fp)
                extra = "  (%d linhas, %d colunas)" % (len(d), len(d.columns))
            except Exception as e:
                extra = "  (ilegível: %s)" % e
        print("  [%s] %-18s %s%s" % ("x" if existe else " ", nome,
                                     os.path.relpath(fp, BASE), extra))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verificar", action="store_true")
    a = ap.parse_args()
    verificar()
    if a.verificar:
        return
    print()
    analisar_f1()
    analisar_f2()


if __name__ == "__main__":
    main()
