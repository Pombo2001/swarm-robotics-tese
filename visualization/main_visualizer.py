import torch
from ursina import *
import numpy as np
import sys
import os
import yaml
import argparse
from stable_baselines3 import PPO, SAC

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D

SCENARIO_LABELS = {
    "none":                   "Sandbox (Arena Aberta)",
    "u_wall":                 "Beco Sem Saida (Muro U)",
    "bottleneck":             "Gargalo (Corredor Estreito)",
    "four_rooms":             "Quatro Salas (Labirinto)",
    "cooperative_door":       "Porta Cooperativa (3 Robos)",
    "cooperative_perception": "Percepcao Cooperativa (Alvo Movel)",
}


def heading_rotation_z(hx, hy):
    """rotation_z para o eixo Y local apontar no sentido do heading (XY plane)."""
    return float(np.degrees(np.arctan2(hx, hy)))


def main(args):
    app = Ursina()

    # ── WALL_COLORS definido DEPOIS do Ursina() para evitar crash de init ──
    WALL_COLORS = {
        "none":                   color.hsv(215, 0.4, 0.65),
        "u_wall":                 color.hsv(200, 0.5, 0.70),
        "bottleneck":             color.hsv(25,  0.6, 0.75),
        "four_rooms":             color.hsv(270, 0.4, 0.70),
        "cooperative_door":       color.hsv(10,  0.7, 0.80),
        "cooperative_perception": color.hsv(150, 0.4, 0.70),
    }

    config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    scenario       = config['environment'].get('classic_scenario', 'none')
    scenario_label = SCENARIO_LABELS.get(scenario, scenario.upper())
    scenario_suffix = f"_{scenario}" if scenario and scenario != 'none' else ""

    window.title = f'Swarm 3D  {args.algo.upper()} | {scenario_label}'
    window.color = color.rgb(10, 12, 18)
    EditorCamera()

    env = SwarmForagingEnv3D(config_path=config_path)
    obs_dict, _ = env.reset()

    # ── Carregar modelo (com fallback para modelo generico) ──────────────────
    model = None
    if args.algo == 'gnn':
        paths = [
            os.path.join(PROJECT_ROOT, 'results', 'models', f'gnn_3d_best{scenario_suffix}.pth'),
            os.path.join(PROJECT_ROOT, 'results', 'models', 'gnn_3d_best.pth'),
        ]
        gnn_agent = GNNAgent3D("visualizer", env.action_space("robot_0"), config_path=config_path)
        for p in paths:
            if os.path.exists(p):
                gnn_agent.load_state_dict(torch.load(p, weights_only=True))
                gnn_agent.eval()
                model = gnn_agent
                print(f"[OK] GNN: {p}")
                break
        if model is None:
            print("[AVISO] Nenhum modelo GNN encontrado — robos com acoes aleatorias")

    elif args.algo == 'ppo':
        paths = [
            os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'ppo_3d_final{scenario_suffix}.zip'),
            os.path.join(PROJECT_ROOT, 'results', 'models_ppo', 'ppo_3d_final.zip'),
        ]
        for p in paths:
            if os.path.exists(p):
                model = PPO.load(p)
                print(f"[OK] PPO: {p}")
                break
        if model is None:
            print("[AVISO] Nenhum modelo PPO encontrado — robos com acoes aleatorias")

    elif args.algo == 'sac':
        paths = [
            os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'sac_3d_final{scenario_suffix}.zip'),
            os.path.join(PROJECT_ROOT, 'results', 'models_ppo', 'sac_3d_final.zip'),
        ]
        for p in paths:
            if os.path.exists(p):
                model = SAC.load(p)
                print(f"[OK] SAC: {p}")
                break
        if model is None:
            print("[AVISO] Nenhum modelo SAC encontrado — robos com acoes aleatorias")

    # ── Iluminação ───────────────────────────────────────────────────────────
    DirectionalLight(y=5, z=-4, shadows=True, rotation=(50, -30, 0))
    AmbientLight(color=color.rgba(80, 90, 110, 100))

    # ── Chão e arena ─────────────────────────────────────────────────────────
    Entity(model='quad',   scale=env.arena_radius * 2.6,
           color=color.rgb(16, 20, 28), z=0.2)
    Entity(model='circle', scale=env.arena_radius * 2,
           color=color.rgb(20, 26, 40), z=0.15)
    Entity(model='circle', scale=env.arena_radius * 2,
           color=color.rgb(50, 110, 200), mode='line', z=0.1)

    # ── Ninho ────────────────────────────────────────────────────────────────
    nest_view = Entity(
        model='circle',
        color=color.rgb(20, 220, 80),
        scale=env.nest_radius * 2,
        position=(env.nest_pos[0], env.nest_pos[1], 0.05),
        unlit=True,
    )
    nest_glow = Entity(
        model='circle',
        color=color.rgba(20, 255, 80, 60),
        scale=env.nest_radius * 5,
        position=(env.nest_pos[0], env.nest_pos[1], 0.04),
        unlit=True,
    )

    # ── Obstáculos ───────────────────────────────────────────────────────────
    obs_views = []
    for obs_pos in env.obstacles:
        obs_views.append(Entity(
            model='sphere',
            color=color.rgb(190, 70, 30),
            scale=env.obstacle_radius * 2,
            position=(obs_pos[0], obs_pos[1], 0.0),
        ))

    # ── Paredes ──────────────────────────────────────────────────────────────
    wall_col        = WALL_COLORS.get(scenario, color.hsv(215, 0.3, 0.6))
    door_wall_index = getattr(env, 'door_wall_index', -1)
    wall_views      = []

    for i, wall in enumerate(env.walls):
        w_color = color.rgb(220, 55, 35) if i == door_wall_index else wall_col
        e = Entity(
            model='cube',
            color=w_color,
            scale=(wall['size'][0], wall['size'][1], 2.0),   # Z=2 para visibilidade 3D
            position=(wall['pos'][0], wall['pos'][1], 0.8),
            texture='white_cube',
        )
        wall_views.append(e)

    # ── Robôs ─────────────────────────────────────────────────────────────────
    # Cada robot = cubo laranja + visor preto na frente (como visualize_3d.py).
    # look_at() orienta o cubo para o heading; o visor preto indica a frente.
    robot_views = {}
    r = env.robot_radius

    for agent_id, pos, heading in zip(env.agents, env.agent_positions, env.agent_headings):
        body = Entity(
            model='cube',
            color=color.rgb(255, 130, 30),
            scale=r * 2,
            position=(pos[0], pos[1], 0.0),
        )
        Entity(parent=body, model='cube', color=color.black,
               scale=(0.8, 0.3, 0.4), position=(0, 0, 0.5))
        robot_views[agent_id] = body

    # ── HUD ──────────────────────────────────────────────────────────────────
    Text(text=f'{args.algo.upper()}  |  {scenario_label}',
         parent=camera.ui, x=-0.75, y=0.45,
         color=color.rgb(180, 210, 255), scale=1.8)
    food_text = Text(text='Recolhas: 0',
                     parent=camera.ui, x=0.5, y=0.45,
                     color=color.rgb(20, 255, 120), scale=1.6)
    if model is None:
        Text(text='SEM MODELO — acoes aleatorias',
             parent=camera.ui, x=-0.4, y=0.0,
             color=color.rgb(255, 180, 30), scale=2.0)

    # ── Loop principal ────────────────────────────────────────────────────────
    def update():
        nonlocal obs_dict

        # Calcular acções (modelo treinado ou aleatório)
        actions = {}
        for agent_id in env.agents:
            if model is None:
                actions[agent_id] = env.action_space(agent_id).sample()
            else:
                obs = np.array(obs_dict[agent_id], dtype=np.float32)
                if args.algo == 'gnn':
                    t = model(torch.tensor(obs, dtype=torch.float32))
                    actions[agent_id] = t.detach().cpu().numpy()
                else:
                    action, _ = model.predict(obs, deterministic=True)
                    actions[agent_id] = action

        obs_dict, _, terms, _, _ = env.step(actions)

        # Ninho (pode ser dinâmico)
        nest_view.position = (env.nest_pos[0], env.nest_pos[1], 0.05)
        nest_glow.position = (env.nest_pos[0], env.nest_pos[1], 0.04)

        # Obstáculos
        for i, obs_pos in enumerate(env.obstacles):
            if i < len(obs_views):
                obs_views[i].position = (obs_pos[0], obs_pos[1], 0.0)

        # Paredes
        for i, wall in enumerate(env.walls):
            if i < len(wall_views):
                wall_views[i].position = (wall['pos'][0], wall['pos'][1], 0.8)

        # Robôs: posição + orientação + cor por estado
        for idx, agent_id in enumerate(env.agents):
            pos      = env.agent_positions[idx]
            heading  = env.agent_headings[idx]
            signaling = env.signaling[idx] == 1.0
            dist_nest = float(np.linalg.norm(pos - env.nest_pos))

            body = robot_views[agent_id]
            body.position = (pos[0], pos[1], 0.0)
            body.look_at(body.position + Vec3(heading[0], heading[1], heading[2]))

            if signaling:
                body.color = color.rgb(255, 210, 0)
                body.scale = r * 3.0
            elif dist_nest < env.nest_radius * 2.5:
                body.color = color.rgb(30, 220, 90)
                body.scale = r * 2.0
            else:
                body.color = color.rgb(255, 130, 30)
                body.scale = r * 2.0

        food_text.text = f'Recolhas: {env.total_food_collected}'

        if any(terms.values()):
            obs_dict, _ = env.reset()
            food_text.text = 'Recolhas: 0'

    app.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--algo', type=str, required=True, choices=['gnn', 'ppo', 'sac'])
    args = parser.parse_args()
    main(args)
