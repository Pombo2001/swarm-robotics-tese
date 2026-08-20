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
       M1  GNN vs PPO e GNN vs SAC, bilateral, médias por run (n=21 pela
           emenda 19; era 7 quando isto foi escrito)
       M2  convergência: runs com ≥1 recolha e runs a 100% (DESCRITIVO — com
           o n desta campanha não se faz inferência sobre proporções)
       M3  uso da porta cooperativa, por algoritmo (descritivo + δ)

Regra de decisão da QI7 (pré-comprometida, §4 do pré-registo): sobe a resultado
se F2 der ≥71,4% de runs convergentes (a proporção que «5/7» fixou) em
pelo menos um algoritmo E M1 for
interpretável. Caso contrário, resultado negativo honesto — que é reportado na
mesma e NÃO se repete com parâmetros diferentes à procura de número melhor.

Uso:
    python scripts/analise_mapa_grande.py --verificar
    python scripts/analise_mapa_grande.py
"""
import argparse
import glob
import math
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

# O F1 estava a ser lido de `results/evaluation/zeroshot_mapa_grande.csv` — a
# corrida ANULADA a 29 jul (paredes de 30 m numa arena de raio 60: os agentes
# voavam por cima do labirinto). Este script imprimia-a como se fosse o
# resultado, 420 linhas e tudo. O F1 que vale são os quatro CSV da repetição, em
# `f1_zeroshot_v2/`, e leem-se TODOS: a análise é por condição.
F1_DIR = os.path.join(BASE, "results", "mapa_grande", "f1_zeroshot_v2")

# O F2 ainda não existe. Quando chegar do servidor fica numa pasta por braço
# (`f2_gnn`, `f2_grad`, `f2_longo`) — procura-se, em vez de fixar um caminho que
# depois não é o que o transporte usou.
F2_GLOB = os.path.join(BASE, "results", "mapa_grande", "f2*", "**",
                       "eval_by_run.csv")

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
            # `int(...)`: com escalares NumPy, `np.bool_ - np.bool_` e um
            # TypeError desde o NumPy 2. So nao rebenta aqui porque cada
            # chamador embrulha os dados em `list()` — e isso e uma
            # convencao, nao uma garantia. O valor devolvido e o mesmo.
            n += int(x > y) - int(x < y)
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
    csvs = sorted(glob.glob(os.path.join(F1_DIR, "zeroshot_*.csv")))
    if not csvs:
        print("  SEM DADOS em %s" % os.path.relpath(F1_DIR, BASE))
        return
    df = pd.concat([pd.read_csv(c) for c in csvs], ignore_index=True)
    print("  fonte: %s (%d ficheiros, %d episódios)"
          % (os.path.relpath(F1_DIR, BASE), len(csvs), len(df)))
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

def _avisar_falhas(csvs):
    """Se o `eval_by_run.py` deixou um sidecar de falhas, dizê-lo AQUI.

    O sidecar existe porque um run que falhe ao avaliar não entra no CSV, e o n
    do CSV é o que fixa o limiar da QI7 (⌈5/7 × n⌉ — 21 execuções pedem 15,
    19 pedem 14). Escrever o aviso ao lado dos dados não chega se o sítio onde
    o limiar é calculado não olhar para ele: um aviso que ninguém lê é a mesma
    coisa que não existir.
    """
    for c in csvs:
        sidecar = c.replace(".csv", "_FALHAS.txt")
        if not os.path.exists(sidecar):
            continue
        print()
        print("  " + "!" * 70)
        print("  AVISO: %s" % os.path.relpath(sidecar, BASE))
        with open(sidecar, encoding="utf-8") as fh:
            for linha in fh.read().splitlines():
                print("  " + linha)
        print("  " + "!" * 70)


def medir_f2(glob_csv=None):
    """As métricas do F2 em números, sem imprimir nada.

    Existe separada do `analisar_f2()` porque o `fechar_qi7.py` precisa
    exatamente destes valores para os escrever na secção. Copiá-los para lá
    criaria a mesma conta em dois sítios — o defeito que este projeto apanhou a
    5 ago com o custo do percurso (13,4% num sítio, 17,0% no outro). A conta
    vive aqui; quem a escreve, importa-a.

    Devolve `None` se ainda não houver CSV nenhum.
    """
    hits = sorted(glob.glob(glob_csv or F2_GLOB, recursive=True))
    if not hits:
        return None
    df = pd.concat([pd.read_csv(h) for h in hits], ignore_index=True)
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
        g = sub.groupby(c_run).agg(
            food=(c_food, "mean"),
            suc=(c_suc, "mean") if c_suc else (c_food, "mean")).sort_index()
        por_algo[algo] = {
            "n": len(g),
            "media": float(g["food"].mean()),
            "dp": float(g["food"].std()),
            "sucesso": float(g["suc"].mean()) if c_suc else None,
            "convergentes": int((g["food"] > 0).sum()),
            "cem_por_cento": int((g["suc"] >= 1.0).sum()) if c_suc else 0,
            "medias_por_run": [float(v) for v in g["food"]],
            "porta": (float(sub[c_porta].mean()) if c_porta else None),
            "min": float(g["food"].min()), "max": float(g["food"].max()),
        }
    if not por_algo:
        return None

    m1 = []
    for x, y in combinations([a for a in ALGOS if a in por_algo], 2):
        a = por_algo[x]["medias_por_run"]
        b = por_algo[y]["medias_por_run"]
        _U, p = mannwhitneyu(a, b, alternative="two-sided", method="exact")
        m1.append({"a": x, "b": y, "p": float(p),
                   "delta": cliffs_delta(list(a), list(b))})

    # A regra do pré-registo é "≥5/7 runs convergentes". Com a emenda 19 o n
    # passou de 7 para 21, e 5/7 tem de ser lido como a PROPORÇÃO que era —
    # 71,4% — e não como o número 5. Ler o «5» à letra com n=21 baixava a
    # fasquia de 71% para 24% por acidente de aritmética, o que é enfraquecer a
    # regra de decisão depois de escrita. Declarado na emenda 21, antes dos dados.
    n_runs = max(v["n"] for v in por_algo.values())
    limiar = int(math.ceil(5.0 / 7.0 * n_runs))
    campeao = max(por_algo, key=lambda a: por_algo[a]["convergentes"])
    max_conv = por_algo[campeao]["convergentes"]

    return {
        "fontes": [os.path.relpath(h, BASE) for h in hits],
        "n_runs": n_runs, "limiar": limiar,
        "por_algo": por_algo, "m1": m1,
        "algo_campeao": campeao, "max_convergentes": max_conv,
        "tem_porta": c_porta is not None,
        # A leitura da secção, pela regra pré-comprometida (ver o bloco de
        # comentário na Discussão de `seccao_mapa_grande.tex`).
        "leitura": ("A" if max_conv >= limiar else "B" if max_conv == 0 else "C"),
    }


def analisar_f2():
    print()
    print("=" * 78)
    print("F2 — TREINO NATIVO")
    print("=" * 78)
    m = medir_f2()
    if m is None:
        print("  SEM DADOS: nada em results/mapa_grande/f2*/")
        print("  (a campanha arranca a 3 ago, quando o megaB largar a máquina)")
        return
    print("  fonte: %s" % ", ".join(m["fontes"]))
    _avisar_falhas(sorted(glob.glob(F2_GLOB, recursive=True)))

    print("\n  M2 — convergência (DESCRITIVO; não se infere sobre proporções "
          "— ver emenda 19)")
    for algo, v in m["por_algo"].items():
        print("    %-4s n=%-2d  %6.1f ± %5.1f   ≥1 recolha: %d/%d   100%%: %d/%d"
              % (algo, v["n"], v["media"], v["dp"],
                 v["convergentes"], v["n"], v["cem_por_cento"], v["n"]))

    print("\n  M1 — magnitude (Mann-Whitney bilateral sobre médias por run)")
    for t in m["m1"]:
        print("    %-4s vs %-4s   p = %.4f   δ = %+.2f"
              % (t["a"], t["b"], t["p"], t["delta"]))
    print("    (expectativa pré-registada: a GNN NÃO é inferior a nenhum dos dois;")
    print("     não foi pré-registada superioridade)")

    if m["tem_porta"]:
        print("\n  M3 — uso da porta cooperativa")
        for algo, v in m["por_algo"].items():
            print("    %-4s fração de episódios com porta aberta: %.2f"
                  % (algo, v["porta"]))
    else:
        print("\n  M3 — coluna da porta ausente do CSV; registar porquê.")

    print()
    print("  REGRA DE DECISÃO DA QI7 (pré-comprometida):")
    print("    limiar: %d de %d runs (5/7 = 71,4%%, a proporção pré-registada)"
          % (m["limiar"], m["n_runs"]))
    if m["leitura"] == "A":
        print("    %d/%d runs convergentes em pelo menos um algoritmo →"
              % (m["max_convergentes"], m["n_runs"]))
        print("    a QI7 SOBE A RESULTADO: secção nova no Cap. de Resultados + QI7 nas")
        print("    Conclusões, desde que M1 seja interpretável.")
    else:
        print("    máximo de %d/%d runs convergentes (< %d) → resultado NEGATIVO "
              "honesto." % (m["max_convergentes"], m["n_runs"], m["limiar"]))
        print("    Reporta-se na mesma: evidencia o limite dos três métodos sob")
        print("    composição+escala. NÃO se repete a campanha com outros parâmetros.")
        print("    Leitura da secção: (%s)." % m["leitura"])


def verificar():
    print("=" * 78)
    print("DADOS ESPERADOS DO MAPA GRANDE")
    print("=" * 78)
    alvos = [("F1 zero-shot", c) for c in
             sorted(glob.glob(os.path.join(F1_DIR, "zeroshot_*.csv")))] or             [("F1 zero-shot", os.path.join(F1_DIR, "zeroshot_natural.csv"))]
    alvos += [("F2 treino nativo", h) for h in sorted(glob.glob(F2_GLOB, recursive=True))] or              [("F2 treino nativo", os.path.join(BASE, "results", "mapa_grande",
                                                "f2_*", "evaluation", "eval_by_run.csv"))]
    for nome, fp in alvos:
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
