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

WALL_COLORS = {
    "none":                   color.hsv(215, 0.4, 0.65),
    "u_wall":                 color.hsv(200, 0.5, 0.70),
    "bottleneck":             color.hsv(25,  0.6, 0.75),
    "four_rooms":             color.hsv(270, 0.4, 0.70),
    "cooperative_door":       color.hsv(10,  0.7, 0.80),
    "cooperative_perception": color.hsv(150, 0.4, 0.70),
}


def heading_rotation_z(heading):
    """Converte vector de heading [hx,hy,_] para rotation_z do Ursina.
    rotation_z = atan2(hx, hy) faz o eixo Y local apontar no sentido do heading."""
    return float(np.degrees(np.arctan2(heading[0], heading[1])))


def main(args):
    app = Ursina()

    config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    scenario = config['environment'].get('classic_scenario', 'none')
    scenario_label = SCENARIO_LABELS.get(scenario, scenario.upper())

    window.title = f'Swarm 3D — {args.algo.upper()} | {scenario_label}'
    window.color = color.rgb(12, 14, 20)
    EditorCamera()

    env = SwarmForagingEnv3D(config=config)
    obs_dict, _ = env.reset()

    scenario_suffix = f"_{scenario}" if scenario else ""

    model = None
    if args.algo == 'gnn':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models', f'gnn_3d_best{scenario_suffix}.pth')
        model = GNNAgent3D("visualizer", env.action_space("robot_0"), config=config)
        if os.path.exists(model_path):
            model.load_state_dict(torch.load(model_path, weights_only=True))
            model.eval()
            print(f"[OK] GNN carregado: {model_path}")
        else:
            print(f"[ERRO] GNN nao encontrado: {model_path}")
            model = None
    elif args.algo == 'ppo':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'ppo_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = PPO.load(model_path)
            print(f"[OK] PPO carregado: {model_path}")
        else:
            print(f"[ERRO] PPO nao encontrado: {model_path}")
    elif args.algo == 'sac':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'sac_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = SAC.load(model_path)
            print(f"[OK] SAC carregado: {model_path}")
        else:
            print(f"[ERRO] SAC nao encontrado: {model_path}")

    # ── Iluminação ──────────────────────────────────────────────────────────
    DirectionalLight(y=4, z=-3, shadows=True, rotation=(45, -45, 45))
    AmbientLight(color=color.rgba(100, 110, 130, 0.4))

    # ── Chão da arena ────────────────────────────────────────────────────────
    Entity(model='quad',   scale=env.arena_radius * 2.5,
           color=color.rgb(18, 22, 30), z=0.15)                # fundo escuro
    Entity(model='circle', scale=env.arena_radius * 2,
           color=color.rgb(22, 28, 42), z=0.10)                # disco da arena
    Entity(model='circle', scale=env.arena_radius * 2,
           color=color.rgb(60, 120, 200), mode='line', z=0.05) # borda neon

    # Grelha de referência (linhas suaves)
    for d in np.arange(-env.arena_radius, env.arena_radius + 0.1, 3.0):
        Entity(model='quad', scale=(env.arena_radius*2, 0.03, 1),
               color=color.rgba(80, 100, 140, 60), z=0.09,
               position=(0, d, 0))
        Entity(model='quad', scale=(0.03, env.arena_radius*2, 1),
               color=color.rgba(80, 100, 140, 60), z=0.09,
               position=(d, 0, 0))

    # ── Ninho ───────────────────────────────────────────────────────────────
    nest_x, nest_y = env.nest_pos[0], env.nest_pos[1]
    nest_inner = Entity(model='circle', color=color.rgb(20, 220, 80),
                        scale=env.nest_radius * 2,
                        position=(nest_x, nest_y, 0.04), unlit=True)
    nest_outer = Entity(model='circle', color=color.rgba(20, 255, 80, 80),
                        scale=env.nest_radius * 4,
                        position=(nest_x, nest_y, 0.03), unlit=True)
    Text(text='NINHO', parent=scene,
         position=(nest_x, nest_y + env.nest_radius + 0.5, 0.04),
         scale=8, color=color.rgb(20, 255, 80), billboard=True)

    # ── Obstáculos ───────────────────────────────────────────────────────────
    obs_views = []
    for obs_pos in env.obstacles:
        obs_views.append(Entity(
            model='sphere',
            color=color.rgb(200, 80, 40),
            scale=env.obstacle_radius * 2,
            position=(obs_pos[0], obs_pos[1], 0.0),
        ))

    # ── Paredes ──────────────────────────────────────────────────────────────
    wall_col = WALL_COLORS.get(scenario, color.hsv(215, 0.3, 0.6))
    door_wall_index = getattr(env, 'door_wall_index', -1)

    wall_views = []
    for i, wall in enumerate(env.walls):
        w_color = color.rgb(220, 60, 40) if i == door_wall_index else wall_col
        e = Entity(
            model='cube',
            color=w_color,
            scale=(wall['size'][0], wall['size'][1], 0.35),
            position=(wall['pos'][0], wall['pos'][1], -0.05),
            texture='white_cube',
        )
        wall_views.append(e)

    # ── Robôs ────────────────────────────────────────────────────────────────
    robot_views = {}   # corpo principal
    robot_noses = {}   # indicador de direção (cone)

    r = env.robot_radius
    for agent_id, pos, heading in zip(env.agents, env.agent_positions, env.agent_headings):
        hx, hy = heading[0], heading[1]
        px, py = pos[0], pos[1]

        # Corpo: cilindro achatado no plano XY
        body = Entity(
            model='cylinder',
            color=color.rgb(30, 130, 255),
            scale=(r * 2, 0.12, r * 2),
            rotation_x=90,
            position=(px, py, 0.0),
        )
        # LED central (brilhante, sem shading)
        Entity(parent=body, model='sphere',
               color=color.rgb(0, 220, 255), scale=0.32, y=0.6, unlit=True)

        # Cone de direção (seta): tip aponta no heading
        nose = Entity(
            model='cone',
            color=color.white,
            scale=(r * 0.28, r * 0.55, r * 0.28),
            position=(px + hx * r * 1.45, py + hy * r * 1.45, 0.06),
            rotation_z=heading_rotation_z(heading),
            unlit=True,
        )

        robot_views[agent_id] = body
        robot_noses[agent_id] = nose

    # ── Label do cenário (HUD) ───────────────────────────────────────────────
    algo_label = args.algo.upper()
    Text(text=f'{algo_label}  |  {scenario_label}',
         parent=camera.ui, x=-0.75, y=0.45,
         color=color.rgb(180, 210, 255), scale=1.8)
    Text(text='ESCAPE para sair   |   scroll para zoom   |   drag para rodar',
         parent=camera.ui, x=-0.75, y=-0.46,
         color=color.rgba(140, 150, 180, 180), scale=1.1)

    # contador de recolhas
    food_text = Text(text='Recolhas: 0', parent=camera.ui,
                     x=0.55, y=0.45, color=color.rgb(20, 255, 120), scale=1.6)

    # ── Loop de simulação ────────────────────────────────────────────────────
    def update():
        nonlocal obs_dict

        if model is None:
            return

        # Calcular acções
        actions = {}
        for agent_id in env.agents:
            obs = np.array(obs_dict[agent_id], dtype=np.float32)
            if args.algo == 'gnn':
                action_tensor = model(torch.tensor(obs, dtype=torch.float32))
                actions[agent_id] = action_tensor.detach().cpu().numpy()
            else:
                action, _ = model.predict(obs, deterministic=True)
                actions[agent_id] = action

        obs_dict, _, terms, _, _ = env.step(actions)

        # Atualizar ninho (pode ser dinâmico)
        nest_inner.position = (env.nest_pos[0], env.nest_pos[1], 0.04)
        nest_outer.position = (env.nest_pos[0], env.nest_pos[1], 0.03)

        # Atualizar obstáculos
        for i, obs_pos in enumerate(env.obstacles):
            if i < len(obs_views):
                obs_views[i].position = (obs_pos[0], obs_pos[1], 0.0)

        # Atualizar paredes (porta cooperativa pode mover-se)
        for i, wall in enumerate(env.walls):
            if i < len(wall_views):
                wall_views[i].position = (wall['pos'][0], wall['pos'][1], -0.05)

        # Atualizar robôs
        for agent_id in env.agents:
            idx = env.agents.index(agent_id)
            pos     = env.agent_positions[idx]
            heading = env.agent_headings[idx]
            hx, hy  = heading[0], heading[1]
            px, py  = pos[0], pos[1]
            signaling = env.signaling[idx] == 1.0
            dist_nest = float(np.linalg.norm(pos - env.nest_pos))

            body = robot_views[agent_id]
            nose = robot_noses[agent_id]

            # Posição e rotação do corpo
            body.position  = (px, py, 0.0)
            body.rotation_z = heading_rotation_z(heading)

            # Posição e rotação do cone de direção
            nose.position   = (px + hx * r * 1.45, py + hy * r * 1.45, 0.06)
            nose.rotation_z = heading_rotation_z(heading)

            # Cor por estado
            if signaling:
                body.color = color.rgb(255, 200, 0)    # dourado: sinalizar
                nose.color = color.rgb(255, 230, 50)
                body.scale = (r * 2.4, 0.14, r * 2.4)
            elif dist_nest < env.nest_radius * 2.5:
                body.color = color.rgb(20, 220, 100)   # verde: perto do ninho
                nose.color = color.rgb(80, 255, 130)
                body.scale = (r * 2, 0.12, r * 2)
            else:
                body.color = color.rgb(30, 130, 255)   # azul: normal
                nose.color = color.white
                body.scale = (r * 2, 0.12, r * 2)

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
