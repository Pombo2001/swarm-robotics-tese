"""Grava um episodio dos robos em video (GIF top-down 2D), AUTOMATICO e offline
(sem janela interativa). Reutiliza o carregador de modelos e o desenho da cena.

Vista de cima (xy): mais limpa para ler a navegacao nos labirintos. (O treino e 3D,
mas esta vista projeta no plano — preferida para os videos.)

Exemplos:
  python scripts/record_episode.py --algo sac --scenario u_wall
  python scripts/record_episode.py --algo gnn --scenario four_rooms --seconds 20 --trails
  python scripts/record_episode.py --all                  # todos algos x cenarios

Saida: <pasta_do_treino>/videos/<algo>_<cenario>.gif (por omissao, na sessao de
treino mais recente; senao results/videos/).
"""
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")  # offline, sem janela
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.animation import FuncAnimation, PillowWriter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D, DOOR_SCENARIOS
from src.scenarios import SCENARIOS, SCENARIO_LABELS, ALGO_LABELS
from scripts.heatmaps import _load_model, _policy_actions

CONFIG_DEFAULT = os.path.join("configs", "foraging.yaml")
ROBOT_COLOR = "#3B82F6"       # azul: agente normal
NEST_ROBOT_COLOR = "#10B981"  # verde: agente no ninho (signaling)
FAILED_COLOR = "#6B7280"      # cinza: agente falhado (Rrobust)


def _latest_training_dir():
    """Pasta da sessao de treino mais recente (results/graficos_tese/<data>) ou None."""
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


def _capture_episode(algo, scenario, config_path, seed, n_frames, models_root=None):
    """Corre 1 episodio determinista e devolve snapshots da cena por frame.

    `models_root` permite gravar a partir dos modelos de OUTRA campanha sem tocar
    nos ativos (ver run_eval.load_model).
    """
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = scenario

    # Sem modelo NAO se grava. Antes caia-se em acoes aleatorias com um aviso na
    # consola — e o que ficava no disco era um GIF chamado `gnn_u_wall.gif`, com
    # o rotulo do algoritmo por cima, de robos a andar ao calhas. Ninguem que o
    # visse no dashboard tinha como saber; o aviso morre no terminal e o
    # ficheiro fica la para sempre a parecer um resultado.
    model = _load_model(algo, scenario, config_path, models_root=models_root)

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
                "pos": env.agent_positions[:, :2].copy(),
                "signaling": env.signaling.copy(),
                "failed": env.failed.copy(),
                "nest": env.nest_pos[:2].copy(),
                "walls": [(w["pos"][:2].copy(), w["size"][:2].copy()) for w in env.walls],
                "door_idx": getattr(env, "door_wall_index", -1),
                "food": int(env.total_food_collected),
                "step": t,
            })
        if all(terms.values()) or all(truncs.values()):
            break

    return frames, env.arena_radius, n_steps


def record(algo, scenario, config_path, seed=2024, seconds=15, fps=20,
           trails=False, out=None, out_dir=None, models_root=None):
    n_frames = max(10, seconds * fps)
    frames, R, n_steps = _capture_episode(algo, scenario, config_path, seed, n_frames,
                                          models_root=models_root)
    print(f"[ok] {len(frames)} frames capturados ({n_steps} passos do episodio).")

    fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
    trail_hist = []  # historico de posicoes para os rastos

    def draw(i):
        ax.clear()
        f = frames[i]
        ax.add_patch(Circle((0, 0), R, fill=False, ec="#6B7280", lw=1.2, ls="--"))
        # paredes (a porta cooperativa nao e solida; paredes removidas vao p/ 999)
        for w_i, (wpos, wsize) in enumerate(f["walls"]):
            if w_i == f["door_idx"] and scenario in DOOR_SCENARIOS:
                continue
            if np.any(np.abs(wpos) > R + 5):
                continue
            ax.add_patch(Rectangle((wpos[0] - wsize[0] / 2, wpos[1] - wsize[1] / 2),
                                   wsize[0], wsize[1], facecolor="#111827",
                                   edgecolor="none", alpha=0.9, zorder=5))
        # rastos (opcional)
        if trails:
            trail_hist.append(f["pos"])
            if len(trail_hist) > 25:
                trail_hist.pop(0)
            for past in trail_hist[:-1]:
                ax.scatter(past[:, 0], past[:, 1], s=4, c=ROBOT_COLOR,
                           alpha=0.08, zorder=4, edgecolors="none")
        # robos, coloridos por estado
        pos, sig, failed = f["pos"], f["signaling"], f["failed"]
        colors = np.where(failed, FAILED_COLOR,
                          np.where(sig > 0.5, NEST_ROBOT_COLOR, ROBOT_COLOR))
        ax.scatter(pos[:, 0], pos[:, 1], s=70, c=colors, zorder=7,
                   edgecolors="white", linewidths=0.6)
        # ninho/alvo
        ax.plot(f["nest"][0], f["nest"][1], marker="*", markersize=24,
                color="#10B981", markeredgecolor="white", markeredgewidth=1.4, zorder=8)
        ax.set_xlim(-R, R); ax.set_ylim(-R, R); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{ALGO_LABELS.get(algo, algo.upper())} — "
                     f"{SCENARIO_LABELS.get(scenario, scenario)}\n"
                     f"passo {f['step']}   |   recolhas: {f['food']}", fontsize=11)
        return []

    anim = FuncAnimation(fig, draw, frames=len(frames), interval=1000 / fps, blit=False)

    if out is None:
        out_dir = out_dir or _default_videos_dir()
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{algo}_{scenario}.gif")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    size_mb = os.path.getsize(out) / 1e6
    print(f"[ok] video guardado: {out}  ({size_mb:.1f} MB, {fps} fps, ~{seconds}s)")
    return out


def _build_panels(videos_dir, panels_dir, scenarios, algos, frac=0.85):
    """Painel comparativo por cenario: junta um frame tardio (~frac do episodio) dos
    GIFs dos 3 algos lado a lado -> panels_dir/painel_videos_<cenario>.png.
    Ordem de exibicao fixa (GNN | PPO | SAC) independentemente da ordem de gravacao."""
    try:
        from PIL import Image
    except Exception:
        print("[paineis] Pillow indisponivel; paineis saltados.")
        return 0
    order = [a for a in ("gnn", "ppo", "sac") if a in algos]
    n_ok = 0
    for sc in scenarios:
        frames = []
        for a in order:
            p = os.path.join(videos_dir, f"{a}_{sc}.gif")
            if not os.path.exists(p):
                continue
            im = Image.open(p)
            nfr = getattr(im, "n_frames", 1)
            im.seek(min(nfr - 1, int(nfr * frac)))
            frames.append(im.convert("RGB"))
        if not frames:
            continue
        w = sum(f.width for f in frames)
        h = max(f.height for f in frames)
        montage = Image.new("RGB", (w, h), "white")
        x = 0
        for f in frames:
            montage.paste(f, (x, 0))
            x += f.width
        montage.save(os.path.join(panels_dir, f"painel_videos_{sc}.png"))
        n_ok += 1
    print(f"[paineis] {n_ok} painel(eis) comparativo(s) em: {panels_dir}")
    return n_ok


def generate_all(out_dir, algos=("sac", "ppo", "gnn"), scenarios=None,
                 config_path=None, seconds=12, fps=15, trails=False,
                 progress_base=0.0, progress_span=1.0, models_root=None):
    """Grava um GIF 2D por algoritmo x cenario para out_dir/videos/.
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
    print("\n[VIDEOS 2D] A gravar episodios...")
    for sc in scenarios:
        for algo in algos:
            set_progress(progress_base + progress_span * (done / max(1, total)),
                         f"Video 2D — {algo.upper()}/{sc}")
            try:
                record(algo, sc, config_path, seconds=seconds, fps=fps,
                       trails=trails, out_dir=videos_dir, models_root=models_root)
                n_ok += 1
            except Exception as e:
                print(f"[!] Falha no video {algo}/{sc}: {e}")
            done += 1
    print(f"[VIDEOS 2D] {n_ok} video(s) gravado(s) em: {videos_dir}")
    # Paineis comparativos (GNN|PPO|SAC) na pasta do treino, ao lado dos outros graficos.
    _build_panels(videos_dir, out_dir, scenarios, list(algos))
    return n_ok


def main():
    p = argparse.ArgumentParser(description="Grava episodios dos robos em GIF 2D (top-down).")
    p.add_argument("--algo", choices=["gnn", "ppo", "sac"], default="sac")
    p.add_argument("--scenario", default="u_wall")
    p.add_argument("--seconds", type=int, default=15)
    p.add_argument("--fps", type=int, default=20)
    p.add_argument("--seed", type=int, default=2024)
    p.add_argument("--trails", action="store_true", help="desenha rastos dos robos")
    p.add_argument("--out", default=None, help="caminho do ficheiro GIF de saida")
    p.add_argument("--out-dir", default=None,
                   help="pasta de saida (default: videos/ da pasta do treino mais recente)")
    p.add_argument("--all", action="store_true",
                   help="grava TODOS os algoritmos x cenarios para a pasta do treino")
    p.add_argument("--config", default=CONFIG_DEFAULT)
    a = p.parse_args()

    if a.all:
        out_dir = a.out_dir or _latest_training_dir() or os.path.join(PROJECT_ROOT, "results")
        generate_all(out_dir, config_path=a.config, seconds=a.seconds,
                     fps=a.fps, trails=a.trails)
        return
    record(a.algo, a.scenario, a.config, seed=a.seed, seconds=a.seconds,
           fps=a.fps, trails=a.trails, out=a.out, out_dir=a.out_dir)


if __name__ == "__main__":
    main()
