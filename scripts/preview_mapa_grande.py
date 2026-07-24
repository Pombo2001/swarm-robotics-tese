"""
preview_mapa_grande.py — Planta do MAPA GRANDE proposto, para aprovação visual
==============================================================================
RASCUNHO. Este ficheiro NÃO toca no simulador: a geometria vive aqui até o mapa
ser aprovado. Só depois é que passa a um `_spawn_obstacles_*` em
`src/environment/swarm_env_3d.py` e a uma entrada em `src/scenarios.py`.

O objetivo é decidir TAMANHO e ASPETO antes de escrever código a sério:
    - planta de topo à escala, com o mapa atual (r=15) sobreposto em fantasma
    - ninho parado + 20 robôs no spawn, para se ver a escala
    - caminho mais curto REAL (BFS geodésico, igual ao do ambiente) e o seu
      comprimento em metros -> é isto que dimensiona o `max_steps`

Formato das paredes IDÊNTICO ao do ambiente ({'pos': [x,y,z], 'size': [sx,sy,sz]},
caixas alinhadas aos eixos), de propósito: na integração é copiar e colar.

Uso:
    .venv/Scripts/python.exe scripts/preview_mapa_grande.py                 # r=30
    .venv/Scripts/python.exe scripts/preview_mapa_grande.py --radius 45
    .venv/Scripts/python.exe scripts/preview_mapa_grande.py --radius 30 45  # comparar
"""
import argparse
import os
import sys
from collections import deque

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(PROJECT_ROOT, "results", "maps_3d")

# --- Constantes REAIS do projeto (configs/foraging.yaml) ---------------------
ARENA_ATUAL = 15.0     # arena_radius em uso nos 7 cenários
ROBOT_RADIUS = 0.15    # physics.agent_radius
LIDAR_RANGE = 8.0      # environment.lidar_range
GEO_RES = 0.4          # environment.geodesic_cell_size
NUM_AGENTS = 20        # environment.num_agents
ESPESSURA = 1.5        # espessura de parede usada no four_rooms
ABERTURA = 2.5         # largura das passagens (alargada de 1.5 em 22 jun)
ALTURA_Z = 30.0        # altura das paredes (igual aos outros cenários)

C_PAREDE = "#3B4252"
C_CHAO = "#EAEDF2"
C_NINHO = "#22C55E"
C_ROBO = "#3D9EFF"
C_PORTA = "#F59E0B"
C_FANTASMA = "#EF4444"
C_CAMINHO = "#7C3AED"


def _parede(cx, cy, sx, sy):
    """Caixa alinhada aos eixos, no formato EXATO do ambiente."""
    return {"pos": np.array([cx, cy, 0.0]), "size": np.array([sx, sy, ALTURA_Z])}


def build_walls(R):
    """Geometria do mapa grande, parametrizada pelo raio da arena.

    Retângulo de proporção 2:1 inscrito no círculo de raio R (W=2H e W²+H²=(2R)²
    dão H=2R/√5). Cinco zonas da esquerda para a direita, cada uma a citar uma
    dificuldade já validada nos 7 cenários; o ninho fica no extremo oposto ao
    spawn para maximizar a distância geodésica.
    """
    H = 2 * R / np.sqrt(5)          # altura do retângulo útil
    W = 2 * H                       # largura
    t = ESPESSURA
    ab = ABERTURA

    x0, x1 = -W / 2, W / 2
    y0, y1 = -H / 2, H / 2
    walls = []

    # --- Fronteira retangular (a arena continua circular; isto é o labirinto) --
    walls += [
        _parede(0, y1, W, t),        # norte
        _parede(0, y0, W, t),        # sul
        _parede(x0, 0, t, H),        # oeste
        _parede(x1, 0, t, H),        # este
    ]

    # === ZONA A (oeste): GARGALO + BECO EM U ================================
    # Parede vertical que separa A de B, com UMA passagem estreita (gargalo).
    # A abertura fica DESLOCADA para sul (y=-H/4) e não a meio: a meio colidiria
    # com o braço horizontal da cruz das Quatro Salas, que arranca neste mesmo x
    # — as duas aberturas anular-se-iam e o mapa ficaria intransponível.
    xa = x0 + 0.30 * W
    y_gargalo = -H / 4
    b_baixo = (y_gargalo - ab / 2) - y0
    b_cima = y1 - (y_gargalo + ab / 2)
    walls += [
        _parede(xa, y0 + b_baixo / 2, t, b_baixo),
        _parede(xa, y1 - b_cima / 2, t, b_cima),
    ]
    # Beco em U aberto para ESTE: o gradiente euclidiano aponta para lá (o ninho
    # está a este) mas é um saco — só se sai voltando para trás. Igual ao u_wall.
    ux, uy = x0 + 0.15 * W, 0.0
    uw, uh = 0.13 * W, 0.34 * H
    walls += [
        _parede(ux - uw / 2, uy, t, uh),            # fundo do U (oeste)
        _parede(ux, uy + uh / 2, uw, t),            # topo
        _parede(ux, uy - uh / 2, uw, t),            # base
    ]

    # === ZONA B: QUATRO SALAS (cruz com aberturas) ==========================
    xb = x0 + 0.55 * W
    yb = 0.0
    # Vertical da cruz: abertura deslocada para NORTE (mesma razão da zona A —
    # a meio colidiria com o braço horizontal). Ficando a norte, obriga o enxame
    # a atravessar as salas na diagonal: entra a sul pelo gargalo, sai a norte.
    y_passagem_b = H / 4
    c_baixo = (y_passagem_b - ab / 2) - y0
    c_cima = y1 - (y_passagem_b + ab / 2)
    walls += [
        _parede(xb, y0 + c_baixo / 2, t, c_baixo),
        _parede(xb, y1 - c_cima / 2, t, c_cima),
    ]
    # Horizontal da cruz, de xa a xb, com abertura a meio do vão
    largura_b = xb - xa
    segh = (largura_b - ab) / 2
    walls += [
        _parede(xa + segh / 2, yb, segh, t),
        _parede(xb - segh / 2, yb, segh, t),
    ]

    # === ZONA C: PORTA COOPERATIVA + ALTERNATIVA LONGA ======================
    # Parede vertical com uma "porta" central (a laranja no desenho) e uma
    # abertura permanente encostada a NORTE — o desvio mais longo, como o bypass.
    xc = x0 + 0.78 * W
    porta_h = 3.0                       # porta cooperativa (3 m, como no cenário)
    alt_h = 4.0                         # passagem alternativa livre (4 m)
    # de y0 até ao BORDO INFERIOR da porta (-porta_h/2). Usar +porta_h/2 aqui
    # tapava a porta toda e o caminho mais curto fugia pela alternativa.
    b1 = (-porta_h / 2) - y0
    walls.append(_parede(xc, y0 + b1 / 2, t, b1))
    # da porta até ao início da alternativa (que fica encostada a norte)
    y_alt0 = y1 - alt_h
    b2 = y_alt0 - (porta_h / 2)
    walls.append(_parede(xc, porta_h / 2 + b2 / 2, t, b2))
    # Parede defletora: obriga quem usa a alternativa a afastar-se do ninho
    walls.append(_parede(xc + 0.09 * W, y1 - alt_h - t, 0.18 * W, t))

    porta = {"pos": np.array([xc, 0.0, 0.0]),
             "size": np.array([t, porta_h, ALTURA_Z])}

    return walls, porta, (W, H)


def walls_four_rooms():
    """Geometria REAL do cenário Quatro Salas, copiada de _spawn_obstacles_maze()
    (src/environment/swarm_env_3d.py). Serve de termo de comparação honesto: sem
    isto, dizer que o mapa novo é "N vezes maior" seria um número inventado."""
    return [
        _parede(-12.8375, 0.0, 4.325, 1.5),
        _parede(0.0, 0.0, 16.35, 1.5),
        _parede(12.8375, 0.0, 4.325, 1.5),
        _parede(0.0, -12.8375, 1.5, 4.325),
        _parede(0.0, -4.4625, 1.5, 7.425),
        _parede(0.0, 4.4625, 1.5, 7.425),
        _parede(0.0, 12.8375, 1.5, 4.325),
    ]


def pior_percurso(walls, R, ninho):
    """Maior distância geodésica ao ninho sobre todas as células livres — o
    percurso mais difícil que o mapa impõe. Métrica bem definida e comparável
    entre mapas de tamanhos diferentes."""
    res, n = GEO_RES, int(2 * R / GEO_RES) + 1
    bloq = np.zeros((n, n), dtype=bool)
    for w in walls:
        half = w["size"] / 2.0
        i0 = max(0, int((w["pos"][0] - half[0] - ROBOT_RADIUS + R) / res))
        i1 = min(n - 1, int((w["pos"][0] + half[0] + ROBOT_RADIUS + R) / res))
        j0 = max(0, int((w["pos"][1] - half[1] - ROBOT_RADIUS + R) / res))
        j1 = min(n - 1, int((w["pos"][1] + half[1] + ROBOT_RADIUS + R) / res))
        bloq[i0:i1 + 1, j0:j1 + 1] = True
    # fora do círculo da arena não é chão
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    fora = ((ii * res - R) ** 2 + (jj * res - R) ** 2) > R ** 2
    bloq |= fora

    dist = np.full((n, n), np.inf)
    si, sj = int((ninho[0] + R) / res), int((ninho[1] + R) / res)
    dist[si, sj] = 0.0
    fila = deque([(si, sj)])
    viz = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
           (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
    while fila:
        i, j = fila.popleft()
        for di_, dj_, c in viz:
            a, b = i + di_, j + dj_
            if 0 <= a < n and 0 <= b < n and not bloq[a, b]:
                nd = dist[i, j] + c * res
                if nd < dist[a, b] - 1e-9:
                    dist[a, b] = nd
                    fila.append((a, b))
    finitos = dist[np.isfinite(dist)]
    return float(finitos.max()) if finitos.size else float("nan")


def spawn_e_ninho(R):
    """Spawn a OESTE (dentro da zona A), ninho a ESTE (zona D)."""
    H = 2 * R / np.sqrt(5)
    W = 2 * H
    ninho = np.array([W / 2 - 0.06 * W, 0.0])
    centro_spawn = np.array([-W / 2 + 0.055 * W, -H / 2 + 0.12 * H])
    return centro_spawn, ninho


def bfs_geodesico(walls, R, origem, destino):
    """Caminho mais curto contornando paredes — mesma ideia do _build_geodesic_field
    do ambiente (grelha, paredes infladas pelo raio do robô, 8-conexo)."""
    res = GEO_RES
    n = int(2 * R / res) + 1
    bloq = np.zeros((n, n), dtype=bool)
    for w in walls:
        half = w["size"] / 2.0
        i0 = max(0, int((w["pos"][0] - half[0] - ROBOT_RADIUS + R) / res))
        i1 = min(n - 1, int((w["pos"][0] + half[0] + ROBOT_RADIUS + R) / res))
        j0 = max(0, int((w["pos"][1] - half[1] - ROBOT_RADIUS + R) / res))
        j1 = min(n - 1, int((w["pos"][1] + half[1] + ROBOT_RADIUS + R) / res))
        bloq[i0:i1 + 1, j0:j1 + 1] = True

    def to_ij(p):
        return (int((p[0] + R) / res), int((p[1] + R) / res))

    si, sj = to_ij(origem)
    di, dj = to_ij(destino)
    dist = np.full((n, n), np.inf)
    prev = {}
    dist[si, sj] = 0.0
    fila = deque([(si, sj)])
    viz = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
           (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
    while fila:
        i, j = fila.popleft()
        for di_, dj_, c in viz:
            a, b = i + di_, j + dj_
            if 0 <= a < n and 0 <= b < n and not bloq[a, b]:
                nd = dist[i, j] + c * res
                if nd < dist[a, b] - 1e-9:
                    dist[a, b] = nd
                    prev[(a, b)] = (i, j)
                    fila.append((a, b))
    if not np.isfinite(dist[di, dj]):
        # Diagnóstico: aberturas de zonas diferentes podem anular-se (ver zonas A/B).
        livres = int((~bloq).sum())
        alcancaveis = int(np.isfinite(dist).sum())
        print(f"  !! SEM CAMINHO spawn->ninho. Alcançável a partir do spawn: "
              f"{alcancaveis}/{livres} células livres ({100 * alcancaveis / max(livres, 1):.0f}%)"
              f" — procurar aberturas que se anulam.")
        return None, np.inf
    caminho, no = [], (di, dj)
    while no in prev:
        caminho.append((no[0] * res - R, no[1] * res - R))
        no = prev[no]
    caminho.append((si * res - R, sj * res - R))
    return caminho[::-1], dist[di, dj]


def desenhar(R, out_path):
    walls, porta, (W, H) = build_walls(R)
    centro_spawn, ninho = spawn_e_ninho(R)
    caminho, comprimento = bfs_geodesico(walls, R, centro_spawn, ninho)

    fig, ax = plt.subplots(figsize=(15, 15 * (2 * R) / (2 * R)))
    ax.set_facecolor("white")

    # Arena circular (a fronteira REAL do ambiente)
    ax.add_patch(Circle((0, 0), R, facecolor=C_CHAO, edgecolor="#94A3B8",
                        lw=2, ls="--", zorder=0))
    # Fantasma do mapa atual, para comparação de tamanho
    ax.add_patch(Circle((0, 0), ARENA_ATUAL, facecolor="none",
                        edgecolor=C_FANTASMA, lw=2.5, ls=":", zorder=1))
    ax.text(0, ARENA_ATUAL + 0.9, f"arena ATUAL (r={ARENA_ATUAL:.0f} m)",
            color=C_FANTASMA, ha="center", fontsize=11, fontweight="bold", zorder=6)

    for w in walls:
        cx, cy, _ = w["pos"]
        sx, sy, _ = w["size"]
        ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy,
                               facecolor=C_PAREDE, edgecolor="none", zorder=3))
    # Porta cooperativa (a laranja): passável só com 3 agentes na zona de pressão
    cx, cy, _ = porta["pos"]
    sx, sy, _ = porta["size"]
    ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy,
                           facecolor=C_PORTA, edgecolor="none", zorder=4))

    if caminho:
        xs = [p[0] for p in caminho]
        ys = [p[1] for p in caminho]
        ax.plot(xs, ys, color=C_CAMINHO, lw=2.6, ls="--", zorder=5,
                label=f"caminho mais curto: {comprimento:.0f} m")

    # Ninho + robôs (raio real 0,15 m — ampliados para serem visíveis)
    ax.add_patch(Circle(ninho, 1.1, facecolor=C_NINHO, edgecolor="white",
                        lw=2, zorder=6))
    ax.text(ninho[0], ninho[1] + 2.2, "NINHO", color="#166534", ha="center",
            fontsize=12, fontweight="bold", zorder=6)

    rng = np.random.default_rng(7)
    for _ in range(NUM_AGENTS):
        p = centro_spawn + rng.uniform(-0.035 * W, 0.035 * W, 2)
        ax.add_patch(Circle(p, 0.45, facecolor=C_ROBO, edgecolor="white",
                            lw=0.8, zorder=6))
    ax.text(centro_spawn[0], centro_spawn[1] - 2.6,
            f"{NUM_AGENTS} robôs\n(raio real 0,15 m — ampliados)",
            color="#1D4ED8", ha="center", fontsize=9, zorder=6)

    # Alcance do LiDAR, à escala, a partir de um robô
    ax.add_patch(Circle(centro_spawn, LIDAR_RANGE, facecolor="none",
                        edgecolor="#1D4ED8", lw=1.4, ls="-.", alpha=0.75, zorder=5))
    ax.text(centro_spawn[0] + LIDAR_RANGE * 0.72, centro_spawn[1] + LIDAR_RANGE * 0.72,
            f"LiDAR {LIDAR_RANGE:.0f} m", color="#1D4ED8", fontsize=10, zorder=6)

    # Rótulos das zonas
    zonas = [
        (-W / 2 + 0.15 * W, H / 2 - 0.06 * H, "A · Gargalo + Beco em U"),
        (-W / 2 + 0.42 * W, H / 2 - 0.06 * H, "B · Quatro Salas"),
        (-W / 2 + 0.70 * W, H / 2 - 0.06 * H, "C · Porta coop. + alternativa"),
        (-W / 2 + 0.92 * W, H / 2 - 0.06 * H, "D · Ninho"),
    ]
    for zx, zy, txt in zonas:
        ax.text(zx, zy, txt, ha="center", fontsize=11, color="#0F172A",
                fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#CBD5E1", alpha=0.9))

    # Barra de escala (10 m)
    bx, by = -R * 0.95, -R * 0.93
    ax.plot([bx, bx + 10], [by, by], color="#0F172A", lw=4, zorder=6)
    ax.text(bx + 5, by + 1.0, "10 m", ha="center", fontsize=11,
            fontweight="bold", color="#0F172A", zorder=6)

    # Referência REAL: pior percurso do Quatro Salas (geometria copiada do env)
    pior_atual = pior_percurso(walls_four_rooms(), ARENA_ATUAL, np.array([10.0, 10.0]))
    pior_novo = pior_percurso(walls, R, ninho)
    passos = int(np.ceil(comprimento / 10.0) * 100) if np.isfinite(comprimento) else 0
    ax.set_title(
        f"MAPA GRANDE (rascunho) — arena r={R:.0f} m  ·  labirinto {W:.0f}×{H:.0f} m\n"
        f"spawn→ninho {comprimento:.0f} m  ·  pior percurso {pior_novo:.0f} m "
        f"({pior_novo / pior_atual:.1f}× o do Quatro Salas: {pior_atual:.0f} m)  ·  "
        f"max_steps sugerido ≈ {passos}",
        fontsize=15, fontweight="bold", pad=16)
    ax.set_xlim(-R * 1.02, R * 1.02)
    ax.set_ylim(-R * 1.02, R * 1.02)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=11)
    ax.grid(alpha=0.12)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    n_geo = int(2 * R / GEO_RES) + 1
    print(f"  r={R:>4.0f} m | labirinto {W:>5.1f}x{H:<5.1f} m | paredes {len(walls):>2} | "
          f"spawn->ninho {comprimento:>6.1f} m | pior percurso {pior_novo:>6.1f} m "
          f"({pior_novo / pior_atual:.1f}x o Quatro Salas) | max_steps~{passos:>5} | "
          f"grelha {n_geo}^2 | LiDAR ve {LIDAR_RANGE / (2 * R) * 100:.0f}% da largura")
    return comprimento


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, nargs="+", default=[30.0])
    args = ap.parse_args()
    print("Planta(s) do mapa grande (RASCUNHO — nada integrado no simulador):")
    for R in args.radius:
        out = os.path.join(OUT_DIR, f"preview_mapa_grande_r{int(R)}.png")
        desenhar(R, out)
        print(f"         -> {os.path.relpath(out, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
