import torch
from ursina import *
import numpy as np
import sys
import os
import yaml
import argparse
from stable_baselines3 import PPO, SAC

# Prevent UnicodeEncodeError on Windows terminals when printing emojis
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

def main(args):
    app = Ursina()

    config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
    print(f"DEBUG: Loading configuration from {config_path}")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    print(f"DEBUG: Selected classic scenario: {config['environment'].get('classic_scenario')}")

    window.title = f'Swarm 3D - Visualizer: {args.algo.upper()}'
    EditorCamera()

    env = SwarmForagingEnv3D(config_path=config_path)
    obs_dict, _ = env.reset()

    scenario = config['environment'].get('classic_scenario', 'none')
    # Convenção de nomes: o Sandbox ("none") é guardado SEM sufixo;
    # os restantes cenários com "_{scenario}". Tem de bater certo com os trainers.
    scenario_suffix = f"_{scenario}" if scenario and scenario != "none" else ""

    model = None
    if args.algo == 'gnn':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models', f'gnn_3d_best{scenario_suffix}.pth')
        model = GNNAgent3D("visualizer", env.action_space("robot_0"), config_path=config_path)
        if os.path.exists(model_path):
            model.load_state_dict(torch.load(model_path, weights_only=True))
            model.eval()
            print(f"GNN Model Loaded: {model_path}")
        else:
            print(f"GNN Model not found: {model_path}")
            model = None
    elif args.algo == 'ppo':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'ppo_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = PPO.load(model_path)
            print(f"PPO Model Loaded: {model_path}")
        else:
            print(f"PPO Model not found: {model_path}")
            model = None
    elif args.algo == 'sac':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_sac', f'sac_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = SAC.load(model_path)
            print(f"SAC Model Loaded: {model_path}")
        else:
            print(f"SAC Model not found: {model_path}")
            model = None

    # --- Estética Premium (Modern Sci-Fi 3D) ---
    window.color = color.rgb(15, 18, 22)

    DirectionalLight(y=2, z=-3, shadows=True, rotation=(45, -45, 45))
    AmbientLight(color=color.rgba(120, 120, 120, 0.3))

    Entity(model='quad', scale=env.arena_radius * 2.5, color=color.hsv(0, 0, 0.08), texture='white_cube', z=0.1)
    Entity(model='circle', scale=env.arena_radius * 2, color=color.hsv(220, 0.2, 0.15), z=0.05)
    Entity(model='circle', scale=env.arena_radius * 2, color=color.hsv(180, 0.8, 0.8), mode='line', z=0.0)

    # Ninho: entidades dinâmicas (posição atualizada em update)
    nest_entity = Entity(model='sphere', color=color.hsv(130, 0.8, 0.9),
                         scale=env.nest_radius * 2,
                         position=(env.nest_pos[0], env.nest_pos[1], 0), unlit=True)
    nest_glow = Entity(model='circle', color=color.hsv(130, 0.8, 0.9, 0.3),
                       scale=env.nest_radius * 4,
                       position=(env.nest_pos[0], env.nest_pos[1], 0.01), unlit=True)

    # Obstáculos: lista de entidades atualizadas em update
    obs_entities = []
    for obs_pos in env.obstacles:
        e = Entity(model='sphere', color=color.hsv(10, 0.8, 0.7),
                   scale=env.obstacle_radius * 2,
                   position=(obs_pos[0], obs_pos[1], -0.15), texture='noise')
        obs_entities.append(e)

    # Paredes (incluindo porta cooperativa)
    wall_entities = []
    for wall in env.walls:
        pos_3d = (wall['pos'][0], wall['pos'][1], -0.2)
        size_3d = (wall['size'][0], wall['size'][1], 0.4)
        e = Entity(model='cube', color=color.hsv(215, 0.3, 0.6),
                   scale=size_3d, position=pos_3d, texture='white_cube')
        wall_entities.append(e)

    # Robôs
    robot_views = {}
    for agent_id, pos in zip(env.agents, env.agent_positions):
        r = Entity(model='cylinder', color=color.hsv(210, 0.9, 0.9),
                   scale=(env.robot_radius * 2, 0.15, env.robot_radius * 2),
                   rotation_x=90, position=(pos[0], pos[1], -0.15))
        Entity(parent=r, model='sphere', color=color.white, scale=0.4, y=0.5, unlit=True)
        robot_views[agent_id] = r

    state = {'obs_dict': obs_dict, 'needs_reset': False, 'episode': 1,
             'door_animated': False}

    def _rebuild_obstacles():
        for e in obs_entities:
            destroy(e)
        obs_entities.clear()
        for obs_pos in env.obstacles:
            e = Entity(model='sphere', color=color.hsv(10, 0.8, 0.7),
                       scale=env.obstacle_radius * 2,
                       position=(obs_pos[0], obs_pos[1], -0.15), texture='noise')
            obs_entities.append(e)

    def _rebuild_walls():
        for e in wall_entities:
            destroy(e)
        wall_entities.clear()
        for wall in env.walls:
            pos_3d = (wall['pos'][0], wall['pos'][1], -0.2)
            size_3d = (wall['size'][0], wall['size'][1], 0.4)
            e = Entity(model='cube', color=color.hsv(215, 0.3, 0.6),
                       scale=size_3d, position=pos_3d, texture='white_cube')
            wall_entities.append(e)

    def update():
        if state['needs_reset']:
            state['obs_dict'], _ = env.reset()
            state['needs_reset'] = False
            state['episode'] += 1
            print(f"Episódio {state['episode']} iniciado")
            _rebuild_obstacles()
            _rebuild_walls()
            return

        if not model:
            return

        actions = {}
        for agent_id in env.agents:
            obs = np.array(state['obs_dict'][agent_id], dtype=np.float32)
            if args.algo == 'gnn':
                action_tensor = model(torch.tensor(obs, dtype=torch.float32))
                actions[agent_id] = action_tensor.detach().cpu().numpy()
            else:
                action, _ = model.predict(obs, deterministic=True)
                actions[agent_id] = action

        state['obs_dict'], _, terms, truncs, _ = env.step(actions)

        # Atualizar robôs
        for agent_id, view in robot_views.items():
            idx = env.agents.index(agent_id)
            new_p = env.agent_positions[idx]
            view.position = (new_p[0], new_p[1], -0.15)

        # Atualizar ninho (move em cooperative_perception)
        nest_entity.position = (env.nest_pos[0], env.nest_pos[1], 0)
        nest_glow.position = (env.nest_pos[0], env.nest_pos[1], 0.01)

        # Atualizar posições dos obstáculos dinâmicos
        for i, obs_e in enumerate(obs_entities):
            if i < len(env.obstacles):
                obs_e.position = (env.obstacles[i][0], env.obstacles[i][1], -0.15)

        # Porta cooperativa: animação de abertura (deslize para cima)
        if scenario in ('cooperative_door', 'cooperative_door_bypass') and not state['door_animated']:
            door_idx = getattr(env, 'door_wall_index', None)
            if door_idx is not None and not getattr(env, 'door_active', True):
                if door_idx < len(wall_entities):
                    door_e = wall_entities[door_idx]
                    door_e.color = color.hsv(45, 0.9, 1.0)  # amarelo brilhante
                    door_e.animate_position(
                        Vec3(door_e.x, door_e.y + 6, door_e.z),
                        duration=0.8, curve=curve.out_expo)
                    door_e.animate_color(
                        color.hsv(45, 0.9, 1.0, 0.0),
                        duration=0.8)
                    state['door_animated'] = True

        if any(terms.values()) or any(truncs.values()):
            state['needs_reset'] = True
            state['door_animated'] = False

    app.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--algo', type=str, required=True, choices=['gnn', 'ppo', 'sac'])
    args = parser.parse_args()
    main(args)
