"""
render_maps.py — Renders 3D de qualidade dos mapas/cenários (PyVista)
=====================================================================
Substitui as caixas básicas do Ursina por figuras 3D limpas e de alta resolução
dos seis cenários, prontas para a tese. Lê a geometria real do ambiente
(env.walls, env.nest_pos), pelo que os mapas estão sempre sincronizados com o código.

Uso:
    python scripts/render_maps.py                 # gera os 6 mapas
    python scripts/render_maps.py --scenario u_wall
    python scripts/render_maps.py --scenarios u_wall four_rooms --camera top

Saída: results/maps_3d/mapa_3d_{cenario}.png
"""
import argparse
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pyvista as pv
from src.environment.swarm_env_3d import SwarmForagingEnv3D, DOOR_SCENARIOS
from src.scenarios import SCENARIOS, SCENARIO_LABELS

ALL_SCENARIOS = list(SCENARIOS)
OUT_DIR = os.path.join(PROJECT_ROOT, "results", "maps_3d")

# Paleta (coerente com o resto dos gráficos)
C_FLOOR = "#EAEDF2"
C_WALL  = "#3B4252"
C_DOOR  = "#F59E0B"
C_NEST  = "#10B981"
C_OBST  = "#9CA3AF"
C_RING  = "#6B7280"
C_DOMIN = "#94A3B8"
# ⚠️ `WALL_H` é a altura a que a parede é desenhada CHEIA, e mais nada. Dizia-se
# aqui que "o mundo é planar" e que o z do ambiente era só para colisão — não é
# verdade, e a figura da tese herdava a afirmação. Os agentes têm componente
# vertical (`move_local[2]`) e o domínio é uma ESFERA de raio `arena_radius`:
# medido em 400 passos de PPO, |z| médio 2,35 m no Sandbox e máximo 11,8 m. Foi
# exatamente por o z ser livre que, a 29 jul, se descobriu que os agentes
# passavam POR CIMA de paredes de 30 m (ver `_altura_paredes`). Por isso a
# parede sólida fica baixa (para a planta se ler) mas leva por cima o volume
# real, translúcido, e a esfera do domínio aparece em arame.
WALL_H  = 2.0


def _globo(R, meridianos=3, paralelos=3, lados=120):
    """Círculos que dão a forma da esfera do domínio, como linhas soltas."""
    curvas = []
    ang = np.linspace(0, 2 * np.pi, lados)
    for k in range(1, paralelos + 1):                    # paralelos (z constante)
        z = R * (2.0 * k / (paralelos + 1) - 1.0)
        r = float(np.sqrt(max(0.0, R * R - z * z)))
        pts = np.c_[r * np.cos(ang), r * np.sin(ang), np.full(lados, z)]
        curvas.append(pv.lines_from_points(pts, close=True))
    for m in range(meridianos):                          # meridianos (verticais)
        th = np.pi * m / meridianos
        pts = np.c_[np.cos(th) * R * np.cos(ang),
                    np.sin(th) * R * np.cos(ang),
                    R * np.sin(ang)]
        curvas.append(pv.lines_from_points(pts, close=True))
    return curvas


def _add_map(plotter, env, volume=True):
    """`volume=False` na planta: vista de topo é um desenho técnico, e a esfera
    em arame vista de cima é só uma cebola de círculos."""
    R = float(env.arena_radius)

    # Plano de referência z=0 (não é um chão físico: o domínio é esférico)
    floor = pv.Disc(center=(0, 0, 0), inner=0.0, outer=R, normal=(0, 0, 1), c_res=72)
    # Ligeiramente translúcido quando se mostra o volume: o ninho está centrado
    # no seu z real e metade dele fica ABAIXO deste plano — como deve ser, já que
    # o plano é uma referência e não um chão.
    plotter.add_mesh(floor, color=C_FLOOR, smooth_shading=True, specular=0.1,
                     opacity=0.88 if volume else 1.0)
    ring = pv.Disc(center=(0, 0, 0.01), inner=R - 0.25, outer=R, normal=(0, 0, 1), c_res=72)
    plotter.add_mesh(ring, color=C_RING)

    if volume:
        # A esfera do domínio, como um globo esquemático: três meridianos e três
        # paralelos. `pv.Sphere` em `style="wireframe"` mostrava a triangulação
        # toda — diagonais a mais, e a figura ficava suja.
        for c in _globo(R):
            plotter.add_mesh(c, color=C_DOMIN, line_width=1.2, opacity=0.5)

    door_idx = getattr(env, "door_wall_index", -1)
    for w_i, wall in enumerate(env.walls):
        pos, size = wall["pos"], wall["size"]
        if np.any(np.abs(pos) > R + 5):
            continue  # parede removida (porta aberta)
        is_door = (env.classic_scenario in DOOR_SCENARIOS and w_i == door_idx)
        cor = C_DOOR if is_door else C_WALL
        cube = pv.Cube(center=(float(pos[0]), float(pos[1]), WALL_H / 2.0),
                       x_length=float(size[0]), y_length=float(size[1]), z_length=WALL_H)
        plotter.add_mesh(cube, color=cor,
                         smooth_shading=False, specular=0.2, ambient=0.25)
        if volume:
            # A parede a sério: vai de -R a +R, e é isso que a torna estanque.
            alto = pv.Cube(center=(float(pos[0]), float(pos[1]), 0.0),
                           x_length=float(size[0]), y_length=float(size[1]),
                           z_length=float(size[2]))
            plotter.add_mesh(alto, color=cor, opacity=0.07, style="surface")

    # Obstáculos esféricos (existem no Sandbox; vazios nos labirintos).
    # Na posição REAL, incluindo z: eles ocupam o volume da esfera, e desenhá-los
    # todos assentes no plano era a mesma mentira da parede baixa.
    for obs in getattr(env, "obstacles", []):
        z = float(obs[2]) if volume else float(env.obstacle_radius)
        s = pv.Sphere(radius=float(env.obstacle_radius),
                      center=(float(obs[0]), float(obs[1]), z))
        plotter.add_mesh(s, color=C_OBST, smooth_shading=True)

    # Ninho / alvo — também com o seu z (no Sandbox nasce dentro do volume)
    z_nest = float(env.nest_pos[2]) if volume else float(env.nest_radius)
    nest = pv.Sphere(radius=float(env.nest_radius),
                     center=(float(env.nest_pos[0]), float(env.nest_pos[1]), z_nest))
    plotter.add_mesh(nest, color=C_NEST, smooth_shading=True, specular=0.4)


def render_scenario(scenario, config_path, camera="iso", out_dir=None):
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = scenario
    env.reset(seed=7)

    pv.global_theme.font.family = "arial"
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 1200))
    plotter.set_background("white")
    plotter.enable_parallel_projection()   # ortográfico = aspeto técnico/limpo
    _add_map(plotter, env, volume=(camera != "top"))

    plotter.add_text(SCENARIO_LABELS.get(scenario, scenario),
                     position="upper_edge", font_size=18, color="#111827")

    R = float(env.arena_radius)
    # Enquadramento automático (view_* faz reset_camera e ajusta a escala
    # ortográfica para caber toda a cena — essencial com projeção paralela).
    if camera == "top":
        # Planta técnica: luz frontal uniforme (evita o efeito de "domo") e sem sombras.
        plotter.add_light(pv.Light(light_type="headlight", intensity=0.9))
        plotter.view_xy()
    else:
        plotter.add_light(pv.Light(position=(R, -R, 2 * R), light_type="scene light", intensity=0.6))
        try:
            plotter.enable_shadows()
        except Exception:
            pass
        plotter.view_isometric()
    plotter.camera.zoom(1.25)

    out_dir = out_dir or OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    tag = "topo" if camera == "top" else "3d"
    out = os.path.join(out_dir, f"mapa_{tag}_{scenario}.png")
    plotter.screenshot(out, transparent_background=False)
    plotter.close()
    _autocrop(out)
    print(f"[OK] Mapa 3D ({scenario}) -> {out}")
    return out


def _autocrop(path, margin=35):
    """Recorta a margem branca à volta da cena (melhor aspeto em painéis na tese)."""
    try:
        from PIL import Image, ImageChops
    except Exception:
        return
    img = Image.open(path).convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bbox = ImageChops.difference(img, bg).getbbox()
    if not bbox:
        return
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - margin), max(0, y0 - margin)
    x1, y1 = min(img.width, x1 + margin), min(img.height, y1 + margin)
    img.crop((x0, y0, x1, y1)).save(path)


def main():
    parser = argparse.ArgumentParser(description="Renders 3D dos mapas (PyVista)")
    parser.add_argument("--scenario", default=None, help="um cenário específico")
    parser.add_argument("--scenarios", nargs="*", default=None, help="subconjunto de cenários")
    parser.add_argument("--camera", choices=["iso", "top", "both"], default="iso",
                        help="both = gera as duas vistas (isométrica + topo)")
    parser.add_argument("--open", action="store_true",
                        help="abrir a pasta de saída no fim (para o botão do dashboard)")
    args = parser.parse_args()

    config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    if args.scenario:
        scenarios = [args.scenario]
    elif args.scenarios:
        scenarios = args.scenarios
    else:
        scenarios = ALL_SCENARIOS

    cams = ["iso", "top"] if args.camera == "both" else [args.camera]
    for cam in cams:
        for sc in scenarios:
            try:
                render_scenario(sc, config_path, camera=cam)
            except Exception as e:
                print(f"[!] Falha a renderizar '{sc}' ({cam}): {e}")

    if args.open and os.name == "nt":
        try:
            os.startfile(OUT_DIR)
        except Exception:
            pass


if __name__ == "__main__":
    main()
