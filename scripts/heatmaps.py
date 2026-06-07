"""
heatmaps.py — Mapas de calor para diagnóstico e tese
=====================================================
Dois modos:

1. OCUPAÇÃO (--mode occupancy): corre um modelo treinado e acumula as posições
   de todos os robôs ao longo de N episódios → mapa de calor de "onde passam".
   Serve para CONFIRMAR que os robôs já não ficam presos nas paredes/cantos.

   python scripts/heatmaps.py --mode occupancy --algo sac --scenario u_wall --episodes 10

2. GEODÉSICO (--mode geodesic): visualiza o campo de distância geodésica vs
   euclidiana ao ninho. Justifica na tese a correção do progress reward
   (o euclidiano prende atrás das paredes; o geodésico contorna-as).

   python scripts/heatmaps.py --mode geodesic --scenario u_wall

Saída: results/heatmaps/*.png
"""
import argparse
import os
import sys
import numpy as np

# Windows: evita UnicodeEncodeError (cp1252) ao imprimir caracteres de caixa.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

SCENARIO_LABELS = {
    "none":                   "Sandbox (Arena Aberta)",
    "u_wall":                 "Beco Sem Saída (Muro U)",
    "bottleneck":             "Gargalo (Porta Estreita)",
    "four_rooms":             "Quatro Salas (Labirinto)",
    "cooperative_door":       "Porta Cooperativa (3 Robôs)",
    "cooperative_perception": "Perceção Cooperativa (Alvo Móvel)",
}
ALGO_LABELS = {"gnn": "GNN (Evolutivo)", "ppo": "PPO", "sac": "SAC"}

OUT_DIR = os.path.join(PROJECT_ROOT, "results", "heatmaps")


def _draw_walls_and_nest(ax, env, nest_marker=True):
    """Desenha as paredes (retângulos), o contorno da arena e o ninho por cima."""
    R = env.arena_radius
    ax.add_patch(Circle((0, 0), R, fill=False, ec="#6B7280", lw=1.2, ls="--"))
    for w_i, wall in enumerate(env.walls):
        if (env.classic_scenario == "cooperative_door"
                and w_i == getattr(env, "door_wall_index", -1)):
            continue  # a porta não é parede sólida (zona de passagem)
        if np.any(np.abs(wall["pos"]) > R + 5):
            continue  # parede removida (porta aberta)
        sx, sy = wall["size"][0], wall["size"][1]
        llx = wall["pos"][0] - sx / 2.0
        lly = wall["pos"][1] - sy / 2.0
        ax.add_patch(Rectangle((llx, lly), sx, sy,
                               facecolor="#111827", edgecolor="none", alpha=0.9, zorder=5))
    if nest_marker:
        ax.plot(env.nest_pos[0], env.nest_pos[1], marker="*", markersize=22,
                color="#10B981", markeredgecolor="white", markeredgewidth=1.2,
                zorder=6, label="Ninho/Alvo")
    ax.set_xlim(-R, R)
    ax.set_ylim(-R, R)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")


def _load_model(algo, scenario, config_path):
    """Reutiliza o carregador do run_eval (mesma convenção de sufixos)."""
    from scripts.run_eval import load_model
    return load_model(algo, scenario, config_path)


def _policy_actions(env, algo, model, obs_dict):
    import torch
    if algo == "gnn":
        obs_list = [obs_dict[a] for a in env.agents]
        obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)
        with torch.no_grad():
            acts = model(obs_tensor).cpu().numpy()
        return {a: acts[i] for i, a in enumerate(env.agents)}
    actions = {}
    for a in env.agents:
        action, _ = model.predict(np.array(obs_dict[a], dtype=np.float32), deterministic=True)
        actions[a] = action
    return actions


def run_occupancy(algo, scenario, episodes, bins, config_path, out_dir=None):
    try:
        model = _load_model(algo, scenario, config_path)
    except FileNotFoundError:
        print(f"[--] Sem modelo {algo.upper()} para '{scenario}' — heatmap de ocupação saltado.")
        return None
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = scenario

    R = env.arena_radius
    xs, ys = [], []
    food_total = 0
    for ep in range(episodes):
        obs_dict, _ = env.reset(seed=2000 + ep)
        done = False
        while not done:
            actions = _policy_actions(env, algo, model, obs_dict)
            obs_dict, _, terms, truncs, _ = env.step(actions)
            for p in env.agent_positions:
                xs.append(p[0])
                ys.append(p[1])
            done = any(terms.values()) or any(truncs.values())
        food_total += int(env.total_food_collected)

    H, _, _ = np.histogram2d(xs, ys, bins=bins, range=[[-R, R], [-R, R]])
    H = np.log1p(H)  # comprime a dinâmica (zonas muito visitadas não saturam tudo)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(H.T, origin="lower", extent=[-R, R, -R, R],
                   cmap="inferno", interpolation="bilinear", zorder=0)
    _draw_walls_and_nest(ax, env)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Densidade de ocupação  (log)")
    ax.set_title(f"Ocupação dos robôs — {ALGO_LABELS.get(algo, algo)}\n"
                 f"{SCENARIO_LABELS.get(scenario, scenario)}  "
                 f"({episodes} ep, {food_total} recolhas totais)")
    ax.legend(loc="upper right", framealpha=0.9)

    out_dir = out_dir or OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"heatmap_ocupacao_{algo}_{scenario}.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[OK] Heatmap de ocupação ({algo.upper()}/{scenario}): {food_total} recolhas em {episodes} ep")
    return out


def run_geodesic(scenario, config_path, out_dir=None):
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = scenario
    env.reset(seed=0)
    R = env.arena_radius

    if not env.use_geodesic:
        print(f"[--] '{scenario}' não usa campo geodésico (sem paredes) — saltado.")
        return None

    n = env.geo_n
    geo = np.array(env.geo_field, dtype=float)        # (i=x, j=y)
    geo_masked = np.ma.masked_invalid(geo)            # inf (bloqueado) → branco

    # Campo euclidiano na mesma grelha, para comparação lado a lado.
    res = env.geo_res
    eucl = np.zeros((n, n))
    for i in range(n):
        x = -R + (i + 0.5) * res
        for j in range(n):
            y = -R + (j + 0.5) * res
            eucl[i, j] = np.hypot(x - env.nest_pos[0], y - env.nest_pos[1])

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for ax, field, title in (
            (axes[0], eucl, "Euclidiano (ANTES) — atravessa as paredes"),
            (axes[1], geo_masked, "Geodésico (DEPOIS) — contorna as paredes")):
        im = ax.imshow(field.T, origin="lower", extent=[-R, R, -R, R],
                       cmap="viridis", zorder=0)
        cs = ax.contour(np.linspace(-R, R, n), np.linspace(-R, R, n), field.T,
                        levels=12, colors="white", linewidths=0.5, alpha=0.6)
        _draw_walls_and_nest(ax, env)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("distância ao ninho (m)")
        ax.set_title(title)

    fig.suptitle(f"Potencial de navegação — {SCENARIO_LABELS.get(scenario, scenario)}\n"
                 "As linhas de nível mostram para onde o progress reward 'puxa' o robô",
                 fontsize=12)
    out_dir = out_dir or OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"heatmap_geodesico_{scenario}.png")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[OK] Heatmap geodésico ({scenario})")
    return out


def generate_all(out_dir=None, episodes=6, algos=("sac", "ppo", "gnn"),
                 scenarios=None, config_path=None):
    """Gera TODOS os heatmaps (ocupação por algo×cenário + geodésico por labirinto).
    Robusto: falhas individuais (modelo em falta, etc.) não abortam o conjunto.
    Pensado para ser chamado pelo plot_results.py após a rotina noturna."""
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    if scenarios is None:
        scenarios = list(SCENARIO_LABELS.keys())
    maze_scenarios = ["u_wall", "bottleneck", "four_rooms", "cooperative_door"]

    print("\n[HEATMAPS] A gerar mapas de calor...")
    n_ok = 0

    # 1) Campo geodésico (não precisa de modelos) — figuras de justificação da tese.
    for sc in maze_scenarios:
        if sc not in scenarios:
            continue
        try:
            if run_geodesic(sc, config_path, out_dir=out_dir):
                n_ok += 1
        except Exception as e:
            print(f"[!] Falha no heatmap geodésico '{sc}': {e}")

    # 2) Ocupação por algoritmo × cenário (salta os que não têm modelo treinado).
    for sc in scenarios:
        for algo in algos:
            try:
                if run_occupancy(algo, sc, episodes, 120, config_path, out_dir=out_dir):
                    n_ok += 1
            except Exception as e:
                print(f"[!] Falha no heatmap de ocupação {algo}/{sc}: {e}")

    dest = out_dir or OUT_DIR
    print(f"[HEATMAPS] {n_ok} mapa(s) gerado(s) em: {dest}")
    return n_ok


def main():
    parser = argparse.ArgumentParser(description="Mapas de calor (ocupação / geodésico)")
    parser.add_argument("--mode", required=True, choices=["occupancy", "geodesic"])
    parser.add_argument("--algo", choices=["gnn", "ppo", "sac"],
                        help="(occupancy) algoritmo a carregar")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--episodes", type=int, default=10,
                        help="(occupancy) nº de episódios a acumular")
    parser.add_argument("--bins", type=int, default=120,
                        help="(occupancy) resolução do histograma 2D")
    args = parser.parse_args()

    config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")

    if args.mode == "occupancy":
        if not args.algo:
            parser.error("--algo é obrigatório no modo occupancy")
        run_occupancy(args.algo, args.scenario, args.episodes, args.bins, config_path)
    else:
        run_geodesic(args.scenario, config_path)


if __name__ == "__main__":
    main()
