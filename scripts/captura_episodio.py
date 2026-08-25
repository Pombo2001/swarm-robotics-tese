# -*- coding: utf-8 -*-
"""Capturas qualitativas de um episódio, a partir dos JSON de results/episodios_3d/.

Porque é que estas figuras existem
----------------------------------
As capturas qualitativas que estavam na tese (`viz_*.png`) eram fotografias do
visualizador tiradas a **6 de junho de 2026** — anteriores à correção das
paredes de 29 jul (numa arena esférica de raio 60, paredes de 30 m deixavam 45 m
de céu aberto e os agentes passavam por cima) e anteriores a todas as campanhas
que a dissertação reporta. O texto usava-as para afirmar comportamentos das
políticas finais, que não são as que ali estão.

Estes JSON são as trajetórias que o painel "Ao vivo (3D)" reproduz, gravadas a
31 jul com os modelos campeões da campanha final — os mesmos que produzem os
números das tabelas.

Porquê rasto e não uma pose
---------------------------
O que o texto afirma é *comportamento*: contornar o obstáculo, sincronizar na
porta, cercar o alvo móvel. Uma pose instantânea não mostra nada disso — mostra
onde 20 agentes calharam estar num quadro. O rasto ao longo do episódio mostra
o caminho, e a cor (progresso do episódio) mostra o sentido.

Uso:
    .venv/Scripts/python.exe scripts/captura_episodio.py
    .venv/Scripts/python.exe scripts/captura_episodio.py --cenarios u_wall four_rooms
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

from src.scenarios import SCENARIO_LABELS  # noqa: E402  (precisa do sys.path acima)

ORIGEM = os.path.join(RAIZ, "results", "episodios_3d")
# FORA de results/graficos_tese/: tudo o que é pasta ali dentro entra na galeria
# do dashboard como se fosse uma campanha de treino, e estas capturas não são
# campanha nenhuma — são um recorte de episódios já gravados.
DESTINO = os.path.join(RAIZ, "results", "capturas_episodios")

COR_PAREDE = "#2b3038"
COR_NINHO = "#12a35f"
COR_FUNDO = "#ffffff"


def carregar(algo: str, cenario: str) -> dict:
    caminho = os.path.join(ORIGEM, f"{algo.lower()}_{cenario}.json")
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def desenhar(ep: dict, destino: str, *, titulo_extra: str = "") -> str:
    meta = ep["meta"]
    raio = float(meta["raio_arena"])
    quadros = np.asarray(ep["quadros"], dtype=float)      # (T, N, 3)
    ninho = np.asarray(ep["ninho"], dtype=float)          # (T, 3)
    n_quadros, n_agentes, _ = quadros.shape

    fig, ax = plt.subplots(figsize=(7.2, 7.2))
    ax.set_facecolor(COR_FUNDO)

    # Arena e geometria, por baixo dos rastos.
    ax.add_patch(Circle((0, 0), raio, fill=False, linestyle="--",
                        edgecolor="#9aa2ad", linewidth=1.2, zorder=1))
    for parede in ep["geometria"].get("paredes", []):
        cx, cy, _ = parede["p"]
        sx, sy, _ = parede["s"]
        ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy,
                               facecolor=COR_PAREDE, edgecolor="none", zorder=2))
    for obst in ep["geometria"].get("obstaculos", []):
        ox, oy = obst["p"][0], obst["p"][1]
        ax.add_patch(Circle((ox, oy), float(meta.get("raio_obstaculo", 0.2)),
                            facecolor=COR_PAREDE, edgecolor="none", zorder=2))

    # Rasto de cada agente, colorido pelo progresso do episódio. Um LineCollection
    # por agente (e não uma linha por segmento) mantém isto em segundos mesmo com
    # 20 agentes x 334 quadros.
    #
    # SALTO_MAX: ao entregar comida no ninho, o agente reaparece noutro ponto da
    # arena. Ligados, esses dois pontos dão um segmento reto de até 24 m que
    # ATRAVESSA as paredes — precisamente a leitura que a figura serve para
    # desmentir. O deslocamento real entre quadros tem mediana 0,5-0,9 m e p99
    # abaixo de 1 m fora dos respawns, pelo que 2 m separa os dois casos com
    # folga larga. Os segmentos de respawn são cortados, não redesenhados.
    SALTO_MAX = 2.0
    t = np.linspace(0.0, 1.0, n_quadros)
    cortados = 0
    for i in range(n_agentes):
        xy = quadros[:, i, :2]
        segmentos = np.stack([xy[:-1], xy[1:]], axis=1)
        continuo = np.linalg.norm(np.diff(xy, axis=0), axis=1) <= SALTO_MAX
        cortados += int((~continuo).sum())
        lc = LineCollection(segmentos[continuo], cmap="viridis",
                            norm=plt.Normalize(0, 1), linewidths=1.1,
                            alpha=0.75, zorder=3)
        lc.set_array(t[:-1][continuo])
        ax.add_collection(lc)

    # Posições finais e ninho por cima de tudo.
    ax.scatter(quadros[-1, :, 0], quadros[-1, :, 1], s=26, c="#fde725",
               edgecolors="#3b3b3b", linewidths=0.5, zorder=5,
               label=f"posição final ({n_agentes} agentes)")
    # O ninho move-se na Perceção Cooperativa: desenha-se o rasto dele também.
    # O deslocamento mede-se POR EIXO — um np.ptp sobre o array inteiro compara a
    # coluna x com a coluna y e dá 10 m num ninho parado em (0, 10).
    if float(np.linalg.norm(ninho[:, :2] - ninho[0, :2], axis=1).max()) > 0.5:
        ax.plot(ninho[:, 0], ninho[:, 1], color=COR_NINHO, linewidth=2.0,
                linestyle=":", zorder=4, label="trajetória do alvo móvel")
    ax.add_patch(Circle((ninho[-1, 0], ninho[-1, 1]),
                        float(meta.get("raio_ninho", 1.5)),
                        facecolor=COR_NINHO, alpha=0.85, edgecolor="white",
                        linewidth=1.5, zorder=6))

    ax.set_xlim(-raio * 1.05, raio * 1.05)
    ax.set_ylim(-raio * 1.05, raio * 1.05)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)", fontsize=10)
    ax.set_ylabel("y (m)", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.35)
    # O nome do cenário lê-se da CHAVE (`meta['cenario']`) e não do `rotulo`
    # gravado dentro do JSON: esse é o nome que vigorava no dia em que o
    # episódio foi exportado, e ficou congelado lá. É o mesmo defeito que o
    # seletor da vista «Episódio 3D» teve — oferecia três nomes que a
    # dissertação abandonou. Um ficheiro gravado em junho não se reescreve para
    # mudar um nome; lê-se-lhe a chave e dá-se-lhe o nome de hoje.
    rotulo = SCENARIO_LABELS.get(meta.get("cenario"), meta.get("rotulo", "?"))
    ax.set_title(f"{rotulo} — {meta['algo']}\n"
                 f"{n_agentes} agentes, {meta['passos']} passos, "
                 f"{meta['recolhas']} recolhas{titulo_extra}",
                 fontsize=12, fontweight="bold", pad=12)

    barra = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 100),
                                               cmap="viridis"),
                         ax=ax, fraction=0.046, pad=0.03)
    barra.set_label("progresso do episódio (%)", fontsize=9)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    # A nota vai em duas linhas: numa só, saía pelos dois lados da figura (a
    # figura é quadrada e estreita para o comprimento do texto).
    fig.text(0.5, 0.012,
             f"Rasto dos {n_agentes} agentes ao longo do episódio; a cor indica o instante.\n"
             "Os saltos de reaparecimento após entrega no ninho não são desenhados.",
             ha="center", va="bottom", fontsize=8, color="#555555", style="italic",
             linespacing=1.4)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    fig.savefig(destino, dpi=200)
    plt.close(fig)
    return destino, cortados


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--algo", default="gnn")
    p.add_argument("--cenarios", nargs="*", default=[
        "u_wall", "four_rooms", "cooperative_door", "cooperative_perception"])
    p.add_argument("--destino", default=DESTINO)
    args = p.parse_args()

    for cen in args.cenarios:
        ep = carregar(args.algo, cen)
        saida = os.path.join(args.destino, f"viz_{cen}.png")
        _, cortados = desenhar(ep, saida)
        print(f"[OK] {saida}  ({ep['meta']['recolhas']} recolhas, "
              f"{ep['meta']['quadros']} quadros, {cortados} saltos de "
              f"reaparecimento cortados)")


if __name__ == "__main__":
    main()
