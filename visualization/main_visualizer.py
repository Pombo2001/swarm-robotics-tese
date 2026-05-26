import torch
from ursina import *
import numpy as np
import sys
import os
import yaml
import argparse
from stable_baselines3 import PPO, SAC

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D

def main(args):
    app = Ursina()

    config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    window.title = f'Swarm 3D - Visualizer: {args.algo.upper()}'
    EditorCamera()

    env = SwarmForagingEnv3D(config=config)
    obs_dict, _ = env.reset()

    model = None
    if args.algo == 'gnn':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models', 'gnn_3d_best.pth')
        model = GNNAgent3D("visualizer", env.action_space("robot_0"), config=config)
        if os.path.exists(model_path):
            model.load_state_dict(torch.load(model_path, weights_only=True))
            model.eval()
            print(f"✅ GNN Model Loaded: {model_path}")
        else:
            print(f"❌ GNN Model not found: {model_path}")
            model = None
    elif args.algo == 'ppo':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', 'ppo_3d_final.zip')
        if os.path.exists(model_path):
            model = PPO.load(model_path)
            print(f"✅ PPO Model Loaded: {model_path}")
        else:
            print(f"❌ PPO Model not found: {model_path}")
            model = None
    elif args.algo == 'sac':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', 'sac_3d_final.zip')
        if os.path.exists(model_path):
            model = SAC.load(model_path)
            print(f"✅ SAC Model Loaded: {model_path}")
        else:
            print(f"❌ SAC Model not found: {model_path}")
            model = None

    # --- Scene Creation ---
    Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 30))
    Entity(model='sphere', color=color.green, scale=env.nest_radius * 2, position=tuple(env.nest_pos))
    for obs_pos in env.obstacles:
        Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2, position=tuple(obs_pos))
    for wall in env.walls:
        Entity(model='cube', color=color.dark_gray, scale=tuple(wall['size']), position=tuple(wall['pos']))
    
    robot_views = {agent_id: Entity(model='cube', color=color.orange, scale=env.robot_radius * 2, position=tuple(pos)) for agent_id, pos in zip(env.agents, env.agent_positions)}

    def update():
        nonlocal obs_dict
        if model:
            actions = {}
            for agent_id in env.agents:
                obs = np.array(obs_dict[agent_id], dtype=np.float32)
                if args.algo == 'gnn':
                    action_tensor = model(torch.tensor(obs, dtype=torch.float32))
                    actions[agent_id] = action_tensor.detach().cpu().numpy()
                else:
                    action, _ = model.predict(obs, deterministic=True)
                    actions[agent_id] = action
            
            obs_dict, _, _, _, _ = env.step(actions)
            
            for agent_id, view in robot_views.items():
                idx = env.agents.index(agent_id)
                view.position = tuple(env.agent_positions[idx])

    app.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--algo', type=str, required=True, choices=['gnn', 'ppo', 'sac'])
    args = parser.parse_args()
    main(args)