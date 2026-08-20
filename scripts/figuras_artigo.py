# -*- coding: utf-8 -*-
"""Versões das figuras desenhadas para a COLUNA do artigo (8,9 cm).

O artigo sai em duas colunas (`elsarticle`, `columnwidth` = 252 pt = 3,49 in).
As figuras da dissertação são desenhadas para 16 cm de largura de texto: postas
numa coluna do artigo, ficam reduzidas a 0,37-0,44 e o texto delas chega ao
papel com 4 a 6 pt. Passá-las a `figure*` resolve a legibilidade e custa duas
páginas — o artigo tem limite.

A saída fica em `Artigo/images/*_col.png`: são as MESMAS figuras, dos mesmos
dados, redesenhadas mais estreitas e com as fontes proporcionalmente maiores.
O sufixo evita que se confundam com as cópias sincronizadas da tese, que o
`verificar_figuras_artigo.py` exige idênticas.

Uso:
    python scripts/figuras_artigo.py
"""
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
import matplotlib.pyplot as plt          # noqa: E402
import pandas as pd                      # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

DESTINO = os.path.join(RAIZ, "Artigo", "images")
LARGURA_COLUNA_IN = 252.0 / 72.27


def escalabilidade():
    """A eficiência per capita com o aumento do enxame (QI2)."""
    from eval_scalability import plot_scalability
    csv = os.path.join(RAIZ, "results", "estatisticas", "escalabilidade_none.csv")
    if not os.path.exists(csv):
        print("[!] sem %s" % os.path.relpath(csv, RAIZ))
        return None
    df = pd.read_csv(csv)
    caminho = plot_scalability(df, "none", "Sandbox", sorted(df["N"].unique()),
                               figsize=(4.6, 2.9), escala_fontes=0.72,
                               sufixo="_col")
    destino = os.path.join(DESTINO, os.path.basename(caminho))
    shutil.copy2(caminho, destino)
    return destino


def geodesico():
    """Potencial euclidiano vs geodésico no Muro em U."""
    from heatmaps import run_geodesic
    cfg = os.path.join(RAIZ, "configs", "foraging.yaml")
    return run_geodesic("u_wall", cfg, out_dir=DESTINO, figsize=(4.6, 2.3),
                        escala_fontes=0.8, sufixo="_col")


def megatreino():
    """Os quatro braços do mega-treino no Muro em U, a n=28."""
    import figuras_megatreino as fm
    from gerar_figuras_7d import dotplot_por_run
    fases = list(zip(("mega_A_fase1", "mega_A_fase2", "mega_A_fase3",
                      "mega_A_fase4"), fm.BRACOS_UWALL))
    partes = [fm.moldar(fm.carregar(f, "u_wall"), rot) for f, rot in fases]
    partes = [p for p in partes if p is not None]
    if not partes:
        print("[!] sem dados do mega-treino")
        return None
    d = pd.concat(partes, ignore_index=True)
    n = int(d.groupby("Algorithm").size().max())
    caminho = os.path.join(DESTINO, "megatreino_u_wall_4bracos_col.png")
    dotplot_por_run(
        d, "Muro em U — os quatro braços (n=%d)" % n, caminho,
        ordem=fm.BRACOS_UWALL, cores=fm.CORES_UWALL, n_por_algo=n,
        largura=4.6, altura_rel=0.95,
        nota_extra=(" O braço objetivo é bimodal: as execuções que resolvem "
                    "fazem-no bem, e as que não resolvem ficam a zero."),
    )
    return caminho


def main():
    os.makedirs(DESTINO, exist_ok=True)
    print("Figuras para a coluna do artigo (%.2f in) -> %s"
          % (LARGURA_COLUNA_IN, os.path.relpath(DESTINO, RAIZ)))
    for f in (escalabilidade, geodesico, megatreino):
        try:
            caminho = f()
        except Exception as e:                               # noqa: BLE001
            print("  [X] %-16s %s" % (f.__name__, e))
            continue
        if caminho:
            print("  [v] %s" % os.path.relpath(caminho, RAIZ))


if __name__ == "__main__":
    main()
