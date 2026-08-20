#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""As figuras do PDF são as que os dados produzem hoje?

    python scripts/verificar_figuras_tese.py
    python scripts/verificar_figuras_tese.py --listar   # a tabela figura → fonte

Porque existe
-------------
As figuras da dissertação são **cópias**: nascem em `results/`, são copiadas
para `Tese/images/` e a partir daí vivem sozinhas. Nada liga as duas cópias, e
por isso elas derivam sem ninguém dar por nada. Este projeto já o fez duas
vezes:

* **21 jul** — oito figuras do artigo estavam desatualizadas face à tese, com
  barras de erro negativas que já tinham sido corrigidas;
* **4 ago** — as capturas 3D no PDF eram de 6 de junho, anteriores à correção
  das paredes: mostravam robôs a atravessar o labirinto por cima.

Uma figura errada não é apanhada por nenhum verificador de números: os números
do texto continuam a bater, e é a imagem que mente. Daí este.

O que faz: para cada figura referenciada no `.tex` (ignorando linhas
comentadas), procura o ficheiro com o **mesmo nome** debaixo de `results/` e
compara-o **pixel a pixel** com o que está em `Tese/images/`. O md5 não serve —
o matplotlib grava metadados que mudam a cada corrida, e duas imagens idênticas
dariam md5 diferentes.

⚠️ Uma figura da tese sem ficheiro homónimo em `results/` é, por si, um
achado: quer dizer que ninguém consegue saber o que a produziu. Gerar com um
nome e copiar com outro quebra a única ligação automática que existe.

As divergências **declaradas** abaixo são as que têm explicação e ficam
registadas com ela. Uma divergência nova aparece como falha.
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image, ImageChops

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESE = os.path.join(RAIZ, "Tese")
FONTES = ("results",)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# Divergências conhecidas, com a razão. Cada entrada é uma dívida declarada:
# se a razão deixar de valer, tira-se daqui e a figura passa a ter de bater.
DECLARADAS = {
    "heatmap_ocupacao_gnn_u_wall.png":
        "a tese usa a versão de 6 episódios (pipeline canónico, "
        "plot_results.py) e a legenda diz «6 episódios por painel»; a cópia em "
        "final_7d foi regenerada a 31 jul pelo figuras_campanha.py, que corre "
        "4. A da tese é a coerente com o que a tese afirma.",
    "heatmap_ocupacao_ppo_u_wall.png": "idem — ver o painel do GNN.",
    "heatmap_ocupacao_sac_u_wall.png": "idem — ver o painel do GNN.",
}

# Quem gera o quê, por prefixo do nome. Serve o `--listar`: sem isto, «de onde
# vem esta figura?» responde-se a grep, e a resposta envelhece.
GERADORES = [
    ("mapa_3d_", "scripts/render_maps.py --camera iso"),
    ("mapa_topo_", "scripts/render_maps.py --camera top"),
    ("mapa_grande_planta", "scripts/gerar_figuras_mapa_grande.py"),
    ("mapa_grande_rastos", "scripts/rastos_mapa_grande.py"),
    ("comparacao_mapa_", "scripts/gerar_figuras_7d.py"),
    ("desempenho_global", "scripts/gerar_figuras_7d.py"),
    ("dotplot_eval", "scripts/gerar_figuras_7d.py"),
    ("boxplot", "scripts/gerar_figuras_7d.py"),
    ("escalabilidade_zeroshot", "scripts/eval_scalability.py --replot"),
    ("heatmap_ocupacao", "scripts/heatmaps.py (corre os modelos)"),
    ("heatmap_geodesico", "scripts/heatmaps.py"),
    ("viz_", "scripts/captura_episodio.py"),
    ("prisma", "scripts/slr_pipeline.py"),
    ("robustez", "scripts/plot_robustez.py"),
    ("megatreino", "scripts/analise_megatreino.py"),
]


def figuras_referenciadas():
    """Os caminhos de imagem citados no `.tex`, fora de linhas comentadas."""
    figs = set()
    for nome in ("main.tex", "seccao_mapa_grande.tex"):
        caminho = os.path.join(TESE, nome)
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            for linha in fh:
                if linha.lstrip().startswith("%"):
                    continue
                for m in re.finditer(r"\{(images/[^}]+\.(?:png|pdf|jpg))\}",
                                     linha):
                    figs.add(m.group(1))
    return sorted(figs)


def procurar_fonte(base):
    """O ficheiro homónimo mais recente debaixo de `results/`, ou None."""
    achados = []
    for raiz_rel in FONTES:
        for pasta, _, ficheiros in os.walk(os.path.join(RAIZ, raiz_rel)):
            if base in ficheiros:
                achados.append(os.path.join(pasta, base))
    if not achados:
        return None
    # A fonte canónica é a da campanha da tese quando existe; senão, a mais
    # recente. `final_7d` é a pasta que o Cap. 6 usa.
    for a in achados:
        if "final_7d" in a:
            return a
    return max(achados, key=os.path.getmtime)


# Quantos pixels têm de diferir para isto ser uma diferença, e não ruído.
# O limiar é ABSOLUTO, e é assim que ficou depois de um ensaio o desmentir.
# Estava em «0,05% dos pixels», que numa figura de 3000×2000 dá 3000 pixels de
# tolerância: pintei um quadrado de 40×40 no meio de uma figura da tese e o
# verificador deu-a por boa. Uma barra de erro com a altura errada, um ponto que
# desapareceu ou uma legenda trocada mexem em muito menos do que isso — que é
# exatamente o tipo de defeito que este guião existe para apanhar.
PIXEIS_MINIMOS = 50


def compara(a, b):
    """None se as imagens forem iguais; senão, a descrição da diferença."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return "tamanhos diferentes: %s vs %s" % (ia.size, ib.size)
    d = np.asarray(ImageChops.difference(ia, ib))
    # 8 níveis de tolerância por canal absorvem recompressão e antialiasing de
    # uma versão diferente do matplotlib; não absorvem conteúdo que mudou.
    difs = d.max(axis=2) > 8
    n = int(difs.sum())
    if n <= PIXEIS_MINIMOS:
        return None
    return "%d pixels diferem (%.3f%% da imagem)" % (n, 100.0 * n / difs.size)


def gerador(base):
    for pref, cmd in GERADORES:
        if base.startswith(pref) or pref in base:
            return cmd
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listar", action="store_true",
                    help="imprime a tabela figura → fonte → gerador")
    a = ap.parse_args()

    figs = figuras_referenciadas()
    print("=" * 78)
    print("FIGURAS DA DISSERTAÇÃO  vs  o que os dados produzem")
    print("=" * 78)
    print("  %d figuras referenciadas (linhas comentadas ignoradas)" % len(figs))

    iguais, divergentes, sem_fonte, sem_ficheiro = [], [], [], []
    for f in figs:
        base = os.path.basename(f)
        na_tese = os.path.join(TESE, f)
        if not os.path.exists(na_tese):
            sem_ficheiro.append(f)
            continue
        fonte = procurar_fonte(base)
        if fonte is None:
            sem_fonte.append(f)
            continue
        r = compara(na_tese, fonte)
        if a.listar:
            print("  %-46s %-46s %s"
                  % (base[:46], os.path.relpath(fonte, RAIZ)[:46], gerador(base)))
        (iguais if r is None else divergentes).append((base, fonte, r))

    problemas = []
    print()
    print("  idênticas à fonte ......... %d" % len(iguais))
    print("  divergentes ............... %d" % len(divergentes))
    print("  sem fonte em results/ ..... %d" % len(sem_fonte))
    if sem_ficheiro:
        print("  ⚠️ REFERENCIADAS MAS INEXISTENTES: %d" % len(sem_ficheiro))

    for f in sem_ficheiro:
        problemas.append("a tese referencia %s, que não existe" % f)

    if divergentes:
        print()
        for base, fonte, r in divergentes:
            razao = DECLARADAS.get(base)
            marca = "[i]" if razao else "[X]"
            print("  %s %-44s %s" % (marca, base[:44], r))
            print("      fonte: %s" % os.path.relpath(fonte, RAIZ))
            if razao:
                print("      declarada: %s" % razao)
            else:
                problemas.append(
                    "%s difere da fonte (%s) e a divergência não está "
                    "declarada" % (base, r))

    if sem_fonte:
        print()
        for f in sem_fonte:
            print("  [X] %s: nenhum ficheiro com este nome em results/" % f)
            problemas.append(
                "%s não tem fonte homónima em results/ — ninguém consegue "
                "saber o que a produziu" % os.path.basename(f))

    # Uma exceção declarada que já não diverge é lixo: enganou-se quem a leu.
    nomes_div = {b for b, _, _ in divergentes}
    for base in DECLARADAS:
        if base not in nomes_div:
            problemas.append(
                "%s está declarada como divergência conhecida mas já bate com "
                "a fonte — tirar de DECLARADAS" % base)

    print()
    print("=" * 78)
    if problemas:
        print("%d PROBLEMA(S):" % len(problemas))
        for p in problemas:
            print("   · %s" % p)
        print("=" * 78)
        return 1
    print("As %d figuras batem com as fontes (%d divergências declaradas)."
          % (len(figs), len(DECLARADAS)))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
