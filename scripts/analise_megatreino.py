"""Análise pré-registada do MEGA-TREINO de 1 mês (docs/PRE_REGISTO_MEGATREINO.md).

Escrito a 27 jul 2026, com as campanhas ainda a correr no servidor e **zero dados
no disco**. A razão de existir é essa: quando megaA e megaB fecharem (~1-3 ago),
a análise corre em minutos e não há espaço para decidir o teste depois de ver o
número. Segue o mesmo padrão do `analise_adaptativo.py`, que cumpriu o pré-registo
anterior sem desvios a 19 jul.

Regras herdadas do pré-registo (não são opção deste script):
  · unidade estatística = MÉDIA POR RUN, nunca o episódio (armadilha nº3);
  · Mann-Whitney U exato + delta de Cliff;
  · convergência = DESCRITIVO, exceto o Fisher de M1, que a n=28 é reportável;
  · todos os runs, todas as configs, todas as fases — sem subconjuntos.

Testes confirmatórios:
  M1  u_wall n=28: adaptativo vs objetivo (unilateral) + Fisher sobre convergência
  M2  u_wall n=28, 4 braços, 6 pares bilaterais (multiplicidade assinalada)
  M3  bypass: adaptativo vs fixo w=0,5 (bilateral)
Exploratórios (rotulados, sem regra binária):
  E1  ablação do anneal: sustain 5/20 e decay 0,95/0,995 vs default
  E2  Sandbox adaptativo
  E3  Perceção adaptativa

Uso:
    python scripts/analise_megatreino.py --verificar     # que dados existem?
    python scripts/analise_megatreino.py                 # corre o que houver
"""
import argparse
import os
import sys
from itertools import combinations

import pandas as pd

try:
    from scipy.stats import mannwhitneyu, fisher_exact
except ImportError:  # pragma: no cover
    print("!! scipy em falta: pip install scipy")
    raise

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEGA = os.path.join(BASE, "results", "mega_1mes")

# Mapa fase -> (rótulo, cenário). Os nomes das pastas seguem o padrão das
# campanhas anteriores (`~/mega_{A,B}_fase{N}` arquivadas no servidor).
FASES = {
    "mega_A_fase1": ("GNN adaptativo",      "u_wall"),
    "mega_A_fase2": ("GNN objetivo",        "u_wall"),
    "mega_A_fase3": ("PPO",                 "u_wall"),
    "mega_A_fase4": ("SAC",                 "u_wall"),
    "mega_A_fase5": ("GNN adaptativo",      "none"),
    "mega_B_fase1": ("anneal sustain=5",    "u_wall+bypass"),
    "mega_B_fase2": ("anneal sustain=20",   "u_wall+bypass"),
    "mega_B_fase3": ("anneal decay=0,95",   "u_wall+bypass"),
    "mega_B_fase4": ("anneal decay=0,995",  "u_wall+bypass"),
    "mega_B_fase5": ("GNN adaptativo",      "cooperative_door_bypass"),
    "mega_B_fase6": ("SAC",                 "bottleneck"),
    "mega_B_fase7": ("GNN adaptativo",      "cooperative_perception"),
}

# Referências de campanhas ANTERIORES (n=7). Só entram em M3 e nos exploratórios,
# e sempre DECLARADAS: o pré-registo proíbe somá-las às células n=28 do u_wall.
FIXO_BYPASS = os.path.join(BASE, "results", "novelty_final", "bypass",
                           "results", "evaluation", "eval_by_run.csv")


def caminho(fase):
    return os.path.join(MEGA, fase, "evaluation", "eval_by_run.csv")


def carregar(fase, cenario=None):
    """Médias por run de uma fase. Devolve None se os dados ainda não existirem."""
    fp = caminho(fase)
    if not os.path.exists(fp):
        return None
    df = pd.read_csv(fp)
    if cenario and "Scenario" in df.columns:
        df = df[df["Scenario"] == cenario]
    if df.empty:
        return None
    col_run = "Run" if "Run" in df.columns else df.columns[0]
    g = df.groupby(col_run).agg(food=("food_collected", "mean"),
                                suc=("success", "mean"))
    return g.sort_index()


def cliffs_delta(a, b):
    n = 0
    for x in a:
        for y in b:
            n += (x > y) - (x < y)
    return n / (len(a) * len(b))


def compara(nome, a, b, alternative="two-sided", rotulo_a="A", rotulo_b="B"):
    if a is None or b is None:
        print("  %-46s SEM DADOS" % nome)
        return None
    U, p = mannwhitneyu(a["food"], b["food"], alternative=alternative,
                        method="exact" if len(a) + len(b) < 40 else "asymptotic")
    d = cliffs_delta(list(a["food"]), list(b["food"]))
    print("  %s" % nome)
    print("    %-18s n=%-3d %6.1f ± %5.1f   convergentes: %d/%d"
          % (rotulo_a, len(a), a["food"].mean(), a["food"].std(),
             int((a["suc"] >= 1.0).sum()), len(a)))
    print("    %-18s n=%-3d %6.1f ± %5.1f   convergentes: %d/%d"
          % (rotulo_b, len(b), b["food"].mean(), b["food"].std(),
             int((b["suc"] >= 1.0).sum()), len(b)))
    print("    Mann-Whitney (%s): p = %.4f   |   delta de Cliff = %+.2f"
          % (alternative, p, d))
    return p, d


def verificar():
    print("=" * 78)
    print("DADOS ESPERADOS DO MEGA-TREINO")
    print("=" * 78)
    print("raiz: %s\n" % os.path.relpath(MEGA, BASE))
    faltam = 0
    for fase, (rot, cen) in FASES.items():
        fp = caminho(fase)
        existe = os.path.exists(fp)
        n = ""
        if existe:
            try:
                df = pd.read_csv(fp)
                col = "Run" if "Run" in df.columns else df.columns[0]
                n = "  (%d runs, %d linhas)" % (df[col].nunique(), len(df))
            except Exception as e:
                n = "  (ilegível: %s)" % e
        else:
            faltam += 1
        print("  [%s] %-14s %-18s %-24s%s"
              % ("x" if existe else " ", fase, rot, cen, n))
    print("\n  em falta: %d de %d" % (faltam, len(FASES)))
    if faltam:
        print("\n  Enquanto faltarem, a análise corre só o que existir. Ao trazer a")
        print("  campanha: pos_campanha.py -> instalar em results/mega_1mes/ ->")
        print("  confirmar _run{n} -> só depois correr isto (pré-registo, §Mecânica).")
    return faltam


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verificar", action="store_true",
                    help="lista que dados existem e sai (não analisa)")
    a = ap.parse_args()

    if a.verificar:
        sys.exit(0 if verificar() == 0 else 1)

    verificar()
    print()
    print("=" * 78)
    print("M1 (PRINCIPAL) — u_wall n=28: adaptativo vs objetivo")
    print("=" * 78)
    adapt = carregar("mega_A_fase1", "u_wall")
    obj = carregar("mega_A_fase2", "u_wall")
    r = compara("magnitude (unilateral: adaptativo > objetivo)", adapt, obj,
                "greater", "adaptativo", "objetivo")
    if adapt is not None and obj is not None:
        ca, cb = int((adapt["suc"] >= 1.0).sum()), int((obj["suc"] >= 1.0).sum())
        odds, pf = fisher_exact([[ca, len(adapt) - ca], [cb, len(obj) - cb]])
        print("    Fisher exato sobre convergência: %d/%d vs %d/%d   p = %.4f"
              % (ca, len(adapt), cb, len(obj), pf))
        print("    (a n=28 este teste é reportável; a n=7 não era — ver pré-registo)")

    print()
    print("=" * 78)
    print("M2 — u_wall n=28, 4 braços, 6 pares BILATERAIS")
    print("=" * 78)
    bracos = {}
    for fase, rot in (("mega_A_fase1", "GNN adaptativo"),
                      ("mega_A_fase2", "GNN objetivo"),
                      ("mega_A_fase3", "PPO"),
                      ("mega_A_fase4", "SAC")):
        d = carregar(fase, "u_wall")
        if d is not None:
            bracos[rot] = d
    for x, y in combinations(sorted(bracos), 2):
        compara("%s vs %s" % (x, y), bracos[x], bracos[y], "two-sided", x, y)
    if len(bracos) > 1:
        print("  ⚠ multiplicidade: 6 pares, p BRUTOS (o pré-registo manda assinalar,")
        print("    não corrigir — a leitura assenta no delta).")

    print()
    print("=" * 78)
    print("M3 — bypass: adaptativo vs fixo w=0,5")
    print("=" * 78)
    byp = carregar("mega_B_fase5", "cooperative_door_bypass")
    fixo = None
    if os.path.exists(FIXO_BYPASS):
        df = pd.read_csv(FIXO_BYPASS)
        col = "Run" if "Run" in df.columns else df.columns[0]
        fixo = df.groupby(col).agg(food=("food_collected", "mean"),
                                   suc=("success", "mean"))
    if byp is not None and fixo is not None:
        print("  ⚠ campanhas DIFERENTES (adaptativo desta; fixo de 12 jul) — declarado.")
    compara("bypass adaptativo vs fixo", byp, fixo, "two-sided",
            "adaptativo", "fixo w=0,5")

    print()
    print("=" * 78)
    print("EXPLORATÓRIO (rotulado — sem regra de decisão binária)")
    print("=" * 78)
    print("E1 — ablação do anneal (a pergunta é a SENSIBILIDADE, não um vencedor)")
    for fase in ("mega_B_fase1", "mega_B_fase2", "mega_B_fase3", "mega_B_fase4"):
        rot = FASES[fase][0]
        for cen in ("u_wall", "cooperative_door_bypass"):
            d = carregar(fase, cen)
            if d is None:
                continue
            print("    %-22s %-26s n=%-3d %6.1f ± %5.1f   %d/%d convergentes"
                  % (rot, cen, len(d), d["food"].mean(), d["food"].std(),
                     int((d["suc"] >= 1.0).sum()), len(d)))
    print("E2/E3 — Sandbox e Perceção adaptativos")
    for fase, cen in (("mega_A_fase5", "none"),
                      ("mega_B_fase7", "cooperative_perception")):
        d = carregar(fase, cen)
        if d is None:
            print("    %-14s SEM DADOS" % fase)
            continue
        print("    %-14s %-24s n=%-3d %6.1f ± %5.1f   %d/%d convergentes"
              % (fase, cen, len(d), d["food"].mean(), d["food"].std(),
                 int((d["suc"] >= 1.0).sum()), len(d)))

    print()
    print("Compromissos do pré-registo: todos os runs e configs reportados; nada")
    print("fechado depois de 22 ago entra na tese (vai para a defesa).")


if __name__ == "__main__":
    main()
