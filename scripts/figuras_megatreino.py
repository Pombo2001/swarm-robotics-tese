#!/usr/bin/env python3
"""Figuras do mega-treino (M1/M2/M3 do pré-registo v2) para a tese.

Porquê um script à parte do `figuras_campanha.py`
-------------------------------------------------
O `figuras_campanha.py` faz as figuras DE UMA campanha — uma pasta, os seus
cenários, os seus algoritmos. As figuras que a tese precisa aqui são de outra
natureza: comparam **braços** que vivem em pastas diferentes (`mega_A_fase1..4`
são quatro condições do MESMO cenário) e, em M3, atravessam campanhas. Nenhuma
delas cabe no contrato "uma pasta = um conjunto de figuras".

Os números vêm por importação de `analise_megatreino.py` — o mesmo `carregar()`,
os mesmos ficheiros, o mesmo `FASES`. Se a análise e a figura lessem os dados
cada uma à sua maneira, a tese poderia citar um número que a figura ao lado
desmente, e foi exatamente isso que aconteceu com as figuras do artigo em julho.

O desenho é o `dotplot_por_run` do `gerar_figuras_7d.py`, sem alterações: um
ponto por run, a média em barra, a contagem de convergentes à direita. Com n=28
essa escolha vale ainda mais do que a n=7 — o resultado do Muro em U É a
bimodalidade do braço objetivo (15 runs a resolver, 13 a ficar pelo caminho), e
uma caixa pintaria de cheio o intervalo onde não está run nenhum.

Uso:
    python scripts/figuras_megatreino.py
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analise_megatreino import BASE, FIXO_BYPASS, carregar  # noqa: E402
from gerar_figuras_7d import dotplot_por_run  # noqa: E402

# `mega_treino` e não `megatreino`: o empacotador do Pi só leva as campanhas cujo
# nome começa por um dos prefixos canónicos, e um deles é "mega_". Sem o
# underscore, estas figuras ficavam na torre e a vista do Pi mostrava molduras
# vazias — o mesmo gap que deixou a campanha da QI6 sem imagens.
SAIDA = os.path.join(BASE, "results", "graficos_tese", "mega_treino")

# Os quatro braços do u_wall. A família GNN mantém-se verde (a convenção do
# projeto, `src/scenarios.py`), com o adaptativo em tom cheio e o objetivo em tom
# claro — a identidade não depende da cor, que o nome está no eixo.
BRACOS_UWALL = ["GNN adaptativo", "GNN objetivo", "PPO", "SAC"]
CORES_UWALL = {
    "GNN adaptativo": "#2E7D32",
    "GNN objetivo":   "#81C784",
    "PPO":            "#E65100",
    "SAC":            "#0277BD",
}


def moldar(g, rotulo):
    """`carregar()` devolve food/suc por run; o dotplot quer recolhas/sucesso."""
    if g is None:
        return None
    return pd.DataFrame({
        "Algorithm": rotulo,
        "recolhas": g["food"].to_numpy(dtype=float),
        "sucesso": g["suc"].to_numpy(dtype=float),
    })


def figura_uwall():
    partes = [
        moldar(carregar("mega_A_fase1", "u_wall"), "GNN adaptativo"),
        moldar(carregar("mega_A_fase2", "u_wall"), "GNN objetivo"),
        moldar(carregar("mega_A_fase3", "u_wall"), "PPO"),
        moldar(carregar("mega_A_fase4", "u_wall"), "SAC"),
    ]
    partes = [p for p in partes if p is not None]
    if len(partes) < 4:
        print("  [!] u_wall: só %d dos 4 braços têm dados — não desenho." % len(partes))
        return None
    d = pd.concat(partes, ignore_index=True)
    n = int(d.groupby("Algorithm").size().max())
    caminho = os.path.join(SAIDA, "megatreino_u_wall_4bracos.png")
    dotplot_por_run(
        d,
        "Muro em U — os quatro braços do mega-treino (n=%d por braço)" % n,
        caminho,
        ordem=BRACOS_UWALL, cores=CORES_UWALL, n_por_algo=n,
        nota_extra=(" O braço objetivo é bimodal: as execuções que resolvem "
                    "fazem-no bem, e as que não resolvem ficam a zero — a média "
                    "sozinha não descreve execução nenhuma."),
    )
    print("  [v] %s" % os.path.relpath(caminho, BASE))
    return d


def figura_bypass():
    """M3: adaptativo desta campanha vs peso fixo de 12 jul. Campanhas DIFERENTES."""
    ad = moldar(carregar("mega_B_fase5", "cooperative_door_bypass"), "Adaptativo (n=21)")
    if ad is None:
        print("  [!] bypass: sem dados do braço adaptativo.")
        return None
    if not os.path.exists(FIXO_BYPASS):
        print("  [!] bypass: falta a referência de peso fixo (%s)." % FIXO_BYPASS)
        return None
    df = pd.read_csv(FIXO_BYPASS)
    col_run = "Run" if "Run" in df.columns else df.columns[0]
    g = df.groupby(col_run).agg(food=("food_collected", "mean"), suc=("success", "mean"))
    fx = moldar(g, "Peso fixo w=0,5 (n=%d)" % len(g))

    d = pd.concat([ad, fx], ignore_index=True)
    ordem = ["Adaptativo (n=21)", "Peso fixo w=0,5 (n=%d)" % len(g)]
    cores = {ordem[0]: "#2E7D32", ordem[1]: "#9E9E9E"}
    caminho = os.path.join(SAIDA, "megatreino_bypass_adaptativo_vs_fixo.png")
    dotplot_por_run(
        d, "Porta com Alternativa — dosagem adaptativa vs peso fixo", caminho,
        ordem=ordem, cores=cores,
        nota_extra=(" Atenção: campanhas DIFERENTES (o peso fixo é de 12 jul), "
                    "como o pré-registo obriga a declarar."),
    )
    print("  [v] %s" % os.path.relpath(caminho, BASE))
    return d


def figura_ablacao():
    """E1 (exploratório): sensibilidade ao schedule do anilamento."""
    variantes = [
        ("mega_B_fase1", "sustain=5"),
        ("mega_B_fase2", "sustain=20"),
        ("mega_B_fase3", "decay=0,95"),
        ("mega_B_fase4", "decay=0,995"),
    ]
    for cen, titulo, slug in (
        ("u_wall", "Muro em U", "u_wall"),
        ("cooperative_door_bypass", "Porta com Alternativa", "bypass"),
    ):
        partes = [moldar(carregar(f, cen), rot) for f, rot in variantes]
        partes = [p for p in partes if p is not None]
        if not partes:
            continue
        d = pd.concat(partes, ignore_index=True)
        ordem = [rot for _, rot in variantes if rot in set(d["Algorithm"])]
        cores = {rot: "#2E7D32" for rot in ordem}
        caminho = os.path.join(SAIDA, "megatreino_ablacao_anneal_%s.png" % slug)
        dotplot_por_run(
            d, "%s — ablação do anilamento (exploratório)" % titulo, caminho,
            ordem=ordem, cores=cores,
            nota_extra=(" Exploratório: a pergunta é a SENSIBILIDADE ao schedule, "
                        "não qual das variantes vence."),
        )
        print("  [v] %s" % os.path.relpath(caminho, BASE))


def main():
    os.makedirs(SAIDA, exist_ok=True)
    print("Figuras do mega-treino -> %s" % os.path.relpath(SAIDA, BASE))
    print("\nM1/M2 — os quatro braços no Muro em U")
    figura_uwall()
    print("\nM3 — Porta com Alternativa")
    figura_bypass()
    print("\nE1 — ablação do anilamento")
    figura_ablacao()


if __name__ == "__main__":
    main()
