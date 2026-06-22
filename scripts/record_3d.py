"""
record_3d.py — Grava episodios em VIDEO 3D (PyVista, offscreen)
==============================================================
Corre um modelo treinado e grava um episodio como video 3D, reutilizando o
mesmo motor de render da tese (scripts/render_maps.py): cena offscreen, sem abrir
janelas, com a geometria REAL do ambiente. Ao contrario da vista de cima (2D) e do
visualizador Ursina (que achata o z), AQUI os robos aparecem no seu z REAL — o
treino e mesmo 3D (o z dos agentes varia varios metros).

Saida: <pasta_do_treino>/videos/<algo>_<cenario>.mp4  (ou .gif se ffmpeg faltar).
Por omissao guarda na subpasta videos/ da sessao de treino mais recente
(results/graficos_tese/<data>/), deixando tudo auto-contido.

Exemplos:
  python scripts/record_3d.py --algo sac --scenario u_wall
  python scripts/record_3d.py --algo gnn --scenario four_rooms --spin 0.3
  python scripts/record_3d.py --all                  # todos algos x cenarios
"""
import argparse
import glob as _glob
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pyvista as pv
from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.scenarios import SCENARIOS, SCENARIO_LABELS, ALGO_LABELS
from scripts.render_maps import C_FLOOR, C_WALL, C_DOOR, C_NEST, C_OBST, C_RING
from scripts.heatmaps import _load_model, _policy_actions

# Cores dos robos por estado (mesma convencao da vista 2D)
RGB_ROBOT = (59, 130, 246)    # azul: agente normal
RGB_NEST = (16, 185, 129)     # verde: agente no ninho (signaling)
RGB_FAILED = (107, 114, 128)  # cinza: agente falhado (Rrobust)

# As paredes sao visualmente curtas em render_maps (WALL_H=2). Aqui, como os robos
# usam o z real (tipicamente ~[-8, +1] m), desenhamos as paredes a cobrir essa faixa
# para continuarem a ler-se como barreiras a toda a altura por onde os robos passam.
Z_LO, Z_HI = -9.0, 2.0


def _build_scene(plotter, env):
    """Constroi a cena estatica (chao, anel, paredes altas, ninho, obstaculos).
    Espelha scripts/render_maps._add_map mas com paredes que cobrem o z dos robos."""
    R = float(env.arena_radius)
    floor = pv.Disc(center=(0, 0, 0), inner=0.0, outer=R, normal=(0, 0, 1), c_res=72)
    plotter.add_mesh(floor, color=C_FLOOR, opacity=0.55, smooth_shading=True, specular=0.1)
    ring = pv.Disc(center=(0, 0, 0.01), inner=R - 0.25, outer=R, normal=(0, 0, 1), c_res=72)
    plotter.add_mesh(ring, color=C_RING)

    door_idx = getattr(env, "door_wall_index", -1)
    z_center = (Z_LO + Z_HI) / 2.0
    z_len = (Z_HI - Z_LO)
    for w_i, wall in enumerate(env.walls):
        pos, size = wall["pos"], wall["size"]
        if np.any(np.abs(pos) > R + 5):
            continue  # parede removida (porta aberta)
        is_door = (env.classic_scenario in ("cooperative_door", "cooperative_door_bypass")
                   and w_i == door_idx)
        cube = pv.Cube(center=(float(pos[0]), float(pos[1]), z_center),
                       x_length=float(size[0]), y_length=float(size[1]), z_length=z_len)
        plotter.add_mesh(cube, color=C_DOOR if is_door else C_WALL,
                         opacity=0.85, smooth_shading=False, specular=0.2, ambient=0.25)

    for obs in getattr(env, "obstacles", []):
        s = pv.Sphere(radius=float(env.obstacle_radius),
                      center=(float(obs[0]), float(obs[1]), 0.0))
        plotter.add_mesh(s, color=C_OBST, smooth_shading=True)


def _capture_episode(algo, scenario, config_path, seed, n_frames):
    """Corre 1 episodio determinista e devolve snapshots (pos 3D, estados, ninho)."""
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = scenario

    model = None
    try:
        model = _load_model(algo, scenario, config_path)
    except Exception as e:
        print(f"[aviso] sem modelo para {algo}/{scenario} ({e}); uso acoes aleatorias.")

    obs, _ = env.reset(seed=seed)
    n_steps = env.max_steps
    stride = max(1, n_steps // n_frames)

    frames = []
    for t in range(n_steps):
        if model is not None:
            actions = _policy_actions(env, algo, model, obs)
        else:
            actions = {a: env.action_space(a).sample() for a in env.agents}
        obs, _, terms, truncs, _ = env.step(actions)
        if t % stride == 0:
            frames.append({
                "pos": env.agent_positions.copy(),          # (N, 3) z REAL
                "signaling": env.signaling.copy(),
                "failed": env.failed.copy(),
                "nest": env.nest_pos.copy(),
                "food": int(env.total_food_collected),
                "step": t,
            })
        if all(terms.values()) or all(truncs.values()):
            break
    return env, frames, n_steps


def _robot_color(sig_i, failed_i):
    """Cor (0..1) de um robo conforme o estado: falhado > sinalizar > normal."""
    if failed_i:
        rgb = RGB_FAILED
    elif sig_i > 0.5:
        rgb = RGB_NEST
    else:
        rgb = RGB_ROBOT
    return tuple(c / 255.0 for c in rgb)


def _encode(frame_glob, out, fps):
    """Monta os PNGs num video. Usa ffmpeg (MP4) se existir; senao GIF via Pillow."""
    ffmpeg = shutil.which("ffmpeg")
    if out.lower().endswith(".mp4") and ffmpeg:
        cmd = [ffmpeg, "-y", "-framerate", str(fps), "-pattern_type", "sequence",
               "-i", frame_glob.replace("*", "%05d"),
               "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", out]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out
    # Fallback: GIF com Pillow
    from PIL import Image
    out = os.path.splitext(out)[0] + ".gif"
    files = sorted(_glob.glob(frame_glob))
    imgs = [Image.open(f).convert("P", palette=Image.ADAPTIVE) for f in files]
    if imgs:
        imgs[0].save(out, save_all=True, append_images=imgs[1:],
                     duration=int(1000 / fps), loop=0, optimize=True)
    return out


def record(algo, scenario, config_path, seed=2024, seconds=15, fps=20,
           spin=0.0, out=None, out_dir=None, window_size=(1280, 960)):
    n_frames = max(10, seconds * fps)
    env, frames, n_steps = _capture_episode(algo, scenario, config_path, seed, n_frames)
    print(f"[ok] {len(frames)} frames capturados ({n_steps} passos do episodio).")

    R = float(env.arena_radius)
    plotter = pv.Plotter(off_screen=True, window_size=window_size)
    plotter.set_background("white")
    _build_scene(plotter, env)
    plotter.add_light(pv.Light(position=(R, -R, 2 * R), light_type="scene light", intensity=0.7))

    # Geometrias unitarias centradas na origem; a posicao real e dada por SetPosition
    # a cada frame (evita o deslocamento a dobrar e permite mover ninho/robos).
    nest_geom = pv.Sphere(radius=float(env.nest_radius), center=(0, 0, 0))
    nest_actor = plotter.add_mesh(nest_geom, color=C_NEST, smooth_shading=True, specular=0.4)

    r_rob = float(env.robot_radius) * 1.4   # ligeiramente maior p/ leitura no video
    n_ag = frames[0]["pos"].shape[0]
    robot_actors = []
    for _ in range(n_ag):
        geom = pv.Sphere(radius=r_rob, center=(0, 0, 0))
        robot_actors.append(plotter.add_mesh(geom, color=RGB_ROBOT, smooth_shading=True,
                                             specular=0.3))

    plotter.view_isometric()
    plotter.camera.zoom(1.25)

    tmp = tempfile.mkdtemp(prefix=f"rec3d_{algo}_{scenario}_")
    for i, f in enumerate(frames):
        pos, sig, failed = f["pos"], f["signaling"], f["failed"]
        for k, act in enumerate(robot_actors):
            act.SetPosition(float(pos[k, 0]), float(pos[k, 1]), float(pos[k, 2]))
            act.prop.color = _robot_color(sig[k], failed[k])
        nest_actor.SetPosition(float(f["nest"][0]), float(f["nest"][1]), 0.0)
        plotter.add_text(
            f"{ALGO_LABELS.get(algo, algo)}  |  {SCENARIO_LABELS.get(scenario, scenario)}\n"
            f"passo {f['step']}   recolhas: {f['food']}",
            position="upper_left", font_size=11, color="#111827", name="hud")
        if spin:
            plotter.camera.azimuth += spin
        plotter.screenshot(os.path.join(tmp, f"{i:05d}.png"))
    plotter.close()

    if out is None:
        out_dir = out_dir or _default_videos_dir()
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{algo}_{scenario}.mp4")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    final = _encode(os.path.join(tmp, "*.png"), out, fps)
    shutil.rmtree(tmp, ignore_errors=True)
    size_mb = os.path.getsize(final) / 1e6
    print(f"[ok] video guardado: {final}  ({size_mb:.1f} MB, {fps} fps, ~{seconds}s)")
    return final


def _latest_training_dir():
    base = os.path.join(PROJECT_ROOT, "results", "graficos_tese")
    if not os.path.isdir(base):
        return None
    subs = [os.path.join(base, d) for d in os.listdir(base)
            if d[:1].isdigit() and os.path.isdir(os.path.join(base, d))]
    if not subs:
        return None
    subs.sort(key=os.path.getmtime)
    return subs[-1]


def _default_videos_dir():
    train = _latest_training_dir()
    if train is not None:
        return os.path.join(train, "videos")
    return os.path.join(PROJECT_ROOT, "results", "videos")


def generate_all(out_dir, algos=("sac", "ppo", "gnn"), scenarios=None,
                 config_path=None, seconds=12, fps=20, spin=0.0,
                 progress_base=0.0, progress_span=1.0):
    """Grava um video por algoritmo x cenario para out_dir/videos/.
    Robusto: falhas individuais (sem modelo, etc.) nao abortam o conjunto."""
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    if scenarios is None:
        scenarios = list(SCENARIOS)
    try:
        from scripts.progress import set_progress
    except Exception:
        def set_progress(frac, msg): pass

    videos_dir = os.path.join(out_dir, "videos")
    os.makedirs(videos_dir, exist_ok=True)
    total = len(scenarios) * len(algos)
    done = n_ok = 0
    print("\n[VIDEOS 3D] A gravar episodios...")
    for sc in scenarios:
        for algo in algos:
            set_progress(progress_base + progress_span * (done / max(1, total)),
                         f"Video 3D — {algo.upper()}/{sc}")
            try:
                record(algo, sc, config_path, seconds=seconds, fps=fps, spin=spin,
                       out_dir=videos_dir)
                n_ok += 1
            except Exception as e:
                print(f"[!] Falha no video {algo}/{sc}: {e}")
            done += 1
    print(f"[VIDEOS 3D] {n_ok} video(s) gravado(s) em: {videos_dir}")
    return n_ok


def main():
    p = argparse.ArgumentParser(description="Grava episodios em video 3D (PyVista).")
    p.add_argument("--algo", choices=["gnn", "ppo", "sac"], default="sac")
    p.add_argument("--scenario", default="u_wall")
    p.add_argument("--seconds", type=int, default=15)
    p.add_argument("--fps", type=int, default=20)
    p.add_argument("--seed", type=int, default=2024)
    p.add_argument("--spin", type=float, default=0.0,
                   help="graus de rotacao da camara por frame (orbita lenta; 0 = fixa)")
    p.add_argument("--out", default=None, help="caminho do ficheiro de saida (.mp4/.gif)")
    p.add_argument("--out-dir", default=None,
                   help="pasta de saida (default: videos/ da pasta do treino mais recente)")
    p.add_argument("--all", action="store_true",
                   help="grava TODOS os algoritmos x cenarios para a pasta do treino")
    p.add_argument("--config", default=os.path.join(PROJECT_ROOT, "configs", "foraging.yaml"))
    a = p.parse_args()

    if a.all:
        out_dir = a.out_dir or _latest_training_dir() or os.path.join(PROJECT_ROOT, "results")
        generate_all(out_dir, config_path=a.config, seconds=a.seconds, fps=a.fps, spin=a.spin)
        return
    record(a.algo, a.scenario, a.config, seed=a.seed, seconds=a.seconds,
           fps=a.fps, spin=a.spin, out=a.out, out_dir=a.out_dir)


if __name__ == "__main__":
    main()
