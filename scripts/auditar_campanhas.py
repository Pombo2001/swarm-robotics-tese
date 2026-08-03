#!/usr/bin/env python3
"""Cada campanha tem tudo? — dados, gráficos, vídeo, heatmaps, modelos.

O buraco que isto tapa
----------------------
As campanhas chegam do servidor por caminhos diferentes (fases arquivadas,
`pos_campanha.py`, cópias à mão) e cada uma perde uma coisa diferente pelo
caminho. Já aconteceu, tudo em julho e agosto de 2026:

  · a campanha da QI6 — a que está NA TESE — tinha 268 CSV e **zero** imagens;
  · o mega-treino veio sem uma única figura, e os modelos das 12 fases ficaram
    no servidor até 3 ago;
  · três fases arquivaram os modelos do algoritmo ERRADO (uma cópia do GNN em
    vez do PPO/SAC que treinaram);
  · o delta para o Pi levava o código e esquecia as figuras que a vista lia.

Nenhum destes casos dá erro. A campanha fica lá, com menos coisas, e só se
descobre quando alguém abre o dashboard à procura de um vídeo que não existe.

Este script não repara nada — diz o que falta, por campanha, e porquê é que
falta importa. `--tese` restringe às campanhas que sustentam a dissertação, que
são as únicas onde a ausência é um problema a sério.

Uso:
    python scripts/auditar_campanhas.py
    python scripts/auditar_campanhas.py --tese
"""
from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRAFICOS = os.path.join(RAIZ, "results", "graficos_tese")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# As campanhas que a tese cita. As outras são histórico: podem estar
# incompletas sem que isso seja um defeito.
DA_TESE = ("final_7d", "adaptativo_", "mega_")

# Pastas que vivem aqui mas NÃO são campanhas: não têm treino, não têm runs, e
# exigir-lhes vídeo ou CSV é inventar um defeito. `mega_treino` são as figuras
# que COMPARAM os braços do mega-treino entre si (a da tese, dos 4 braços) —
# derivam dos CSV das campanhas mega_A*/mega_B*, que essas sim são auditadas.
NAO_SAO_CAMPANHAS = {"mega_treino", "estatisticas", "eval_7d"}

# (chave, rótulo, como se reconhece, porque é que importa)
REQUISITOS = [
    ("dados",    "dados",     lambda fs: [f for f in fs if f.endswith(".csv")],
     "sem CSV não há números para verificar nem para o dashboard ler"),
    ("graficos", "gráficos",  lambda fs: [f for f in fs if f.endswith(".png")],
     "a campanha fica invisível na Galeria e nas figuras da tese"),
    ("dotplot",  "dot plot",  lambda fs: [f for f in fs if f.startswith("dotplot")],
     "é a figura que mostra a bimodalidade — a média sozinha engana"),
    ("curvas",   "curvas",    lambda fs: [f for f in fs if f.startswith("comparacao_mapa")],
     "sem curva de treino não se vê se o run convergiu ou estagnou"),
    ("heatmap",  "heatmaps",  lambda fs: [f for f in fs if "heatmap" in f],
     "mostram POR ONDE o enxame andou; é o que explica o número"),
    ("video",    "vídeo",     lambda fs: [f for f in fs if f.endswith(".gif")],
     "é o que se mostra na defesa — um número não se vê a mexer"),
]


def ficheiros(pasta):
    """Todos os nomes de ficheiro sob a pasta (recursivo, sem caminhos)."""
    out = []
    for raiz_dir, _, fs in os.walk(pasta):
        out += fs
    return out


def campanhas(so_tese):
    if not os.path.isdir(GRAFICOS):
        return []
    ds = sorted(d for d in os.listdir(GRAFICOS)
                if os.path.isdir(os.path.join(GRAFICOS, d)) and not d.startswith("_")
                and d not in NAO_SAO_CAMPANHAS)
    return [d for d in ds if d.startswith(DA_TESE)] if so_tese else ds


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tese", action="store_true",
                    help="só as campanhas que a dissertação cita")
    a = ap.parse_args()

    ds = campanhas(a.tese)
    if not ds:
        print("Sem campanhas em results/graficos_tese/.")
        return 0

    print("=" * 78)
    print("UNIFORMIDADE DAS CAMPANHAS%s" % ("  (só as da tese)" if a.tese else ""))
    print("=" * 78)
    cab = "%-22s" % "campanha" + "".join("%-11s" % r[1] for r in REQUISITOS)
    print(cab)
    print("-" * len(cab))

    faltas = {}
    for d in ds:
        fs = ficheiros(os.path.join(GRAFICOS, d))
        linha, em_falta = "%-22s" % d[:21], []
        for chave, rot, regra, _ in REQUISITOS:
            n = len(regra(fs))
            linha += "%-11s" % (str(n) if n else "—")
            if not n:
                em_falta.append(chave)
        print(linha)
        if em_falta:
            faltas[d] = em_falta

    print()
    if not faltas:
        print("Todas as campanhas têm tudo.")
        return 0

    print("=" * 78)
    print("O QUE FALTA, E PORQUÊ IMPORTA")
    print("=" * 78)
    porque = {c: p for c, _, _, p in REQUISITOS}
    rotulo = {c: r for c, r, _, _ in REQUISITOS}
    for d, em_falta in faltas.items():
        print("\n%s" % d)
        for c in em_falta:
            print("   sem %-10s %s" % (rotulo[c] + ":", porque[c]))

    print()
    print("-" * 78)
    print("%d de %d campanhas incompletas." % (len(faltas), len(ds)))
    print("Gráficos e vídeos regeneram-se com:")
    print("    python scripts/figuras_campanha.py --campanha <nome>")
    print("    python scripts/figuras_campanha.py --campanha <nome> --heatmaps  (lento)")
    print("Os heatmaps e os vídeos precisam dos MODELOS da campanha — se a fase")
    print("os não trouxe do servidor, não há como os gerar (ver LEIA-ME_modelos.md).")
    return 1 if a.tese else 0


if __name__ == "__main__":
    sys.exit(main())
