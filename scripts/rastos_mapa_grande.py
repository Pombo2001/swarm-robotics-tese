#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onde é que cada controlador passa o episódio, no mapa grande — em planta.

    python scripts/rastos_mapa_grande.py

Porque existe
-------------
Os três episódios 3D do mapa grande (`results/episodios_3d/*_mapa_grande.json`)
respondem à pergunta certa — «o que é que o PPO e o SAC fazem, se não recolhem?»
—, mas só a quem os vir a correr no browser durante um minuto. Numa apresentação,
numa revisão por e-mail, ou na dissertação, não há animação nenhuma: há uma
figura.

Esta é essa figura. Desenha o **rasto de cada agente ao longo do episódio
inteiro** sobre a planta real do mapa, um painel por controlador, com a mesma
escala e as mesmas paredes. O que se vê de imediato é o que a medição do
`onde_param_mapa_grande.py` diz em números: os rastos do PPO e do SAC ficam a
oeste, e só os do GNN atravessam para a câmara do ninho.

Lê os MESMOS JSON que a vista «Episódio 3D» desenha — não corre modelos nem
inventa episódios. Se um episódio for regenerado, a figura muda com ele.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODIOS = os.path.join(RAIZ, "results", "episodios_3d")
SAIDA = os.path.join(RAIZ, "results", "mapa_grande", "rastos_mapa_grande.png")

# A ordem é a da narrativa: quem resolve primeiro, quem não resolve depois.
ALGOS = [("gnn", "GNN (Evolutivo)", "#2E7D32"),
         ("ppo", "PPO", "#E65100"),
         ("sac", "SAC", "#0277BD")]


def _carregar(algo):
    caminho = os.path.join(EPISODIOS, "%s_mapa_grande.json" % algo)
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    dados = [(a, rot, cor, _carregar(a)) for a, rot, cor in ALGOS]
    em_falta = [a for a, _, _, d in dados if d is None]
    if em_falta:
        raise SystemExit(
            "[!] faltam episódios: %s\n    Gera com: python "
            "scripts/exportar_episodio_3d.py --algo <a> --cenario mapa_grande"
            % ", ".join(em_falta))

    fig, eixos = plt.subplots(len(dados), 1, figsize=(11, 12.5), dpi=150)
    for ax, (algo, rotulo, cor, d) in zip(eixos, dados):
        geo, quadros = d["geometria"], d["quadros"]
        for w in geo["paredes"]:
            (cx, cy, _), (sx, sy, _) = w["p"], w["s"]
            ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy,
                                   facecolor="#2b3440", edgecolor="none",
                                   zorder=2))
        # Os obstáculos são só posições `[x, y, z]` (as paredes é que trazem
        # dicionário com `p` e `s`).
        for o in geo["obstaculos"]:
            ax.plot(o[0], o[1], ".", color="#8d6e63", ms=2, zorder=3)

        # Um rasto por agente. A linha fina e transparente é deliberada: com 20
        # agentes × 400 quadros, o que interessa é ONDE a tinta se acumula.
        n = d["meta"]["agentes"]
        for i in range(n):
            xs = [q[i][0] for q in quadros]
            ys = [q[i][1] for q in quadros]
            ax.plot(xs, ys, "-", color=cor, lw=0.6, alpha=0.45, zorder=4)
        # Onde acabaram, e onde começaram.
        ax.plot([q[0] for q in quadros[0]], [q[1] for q in quadros[0]], "o",
                color="#ffffff", ms=3, mec="#333", mew=0.4, zorder=6)
        ax.plot([q[0] for q in quadros[-1]], [q[1] for q in quadros[-1]], "o",
                color=cor, ms=4.5, mec="#111", mew=0.5, zorder=6)

        nx, ny, _ = d["ninho"][-1]
        ax.plot(nx, ny, "*", color="#22c55e", ms=22, mec="#0b3d16", mew=0.8,
                zorder=7)
        ax.annotate("ninho", (nx, ny), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=9,
                    color="#166534", weight="bold", zorder=7)

        rec = d["meta"]["recolhas"]
        ax.set_title("%s  —  %d recolhas no episódio" % (rotulo, rec),
                     fontsize=12, weight="bold", color=cor, loc="left")
        r = d["meta"]["raio_arena"]
        ax.set_xlim(-r * 0.92, r * 0.92)
        ax.set_ylim(-r * 0.56, r * 0.56)
        ax.set_aspect("equal")
        ax.set_facecolor("#f7f9fb")
        for lado in ("top", "right", "bottom", "left"):
            ax.spines[lado].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle("Mapa grande: por onde andam os 20 agentes num episódio "
                 "(2000 passos)", fontsize=13, weight="bold", y=0.995)
    fig.text(0.5, 0.005,
             "Rasto de cada agente ao longo do episódio inteiro. Pontos brancos: "
             "onde nasceram. Pontos cheios: onde acabaram.\n"
             "Mesma planta, mesma escala, mesmas sementes. Os episódios são os "
             "mesmos que a vista «Episódio 3D» do dashboard desenha.",
             ha="center", fontsize=8.5, color="#555")
    fig.tight_layout(rect=[0, 0.03, 1, 0.98])
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    fig.savefig(SAIDA, bbox_inches="tight", facecolor="white")
    print("[v] %s" % os.path.relpath(SAIDA, RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
