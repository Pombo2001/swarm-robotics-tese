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

    env = SwarmForagingEnv3D(config=config)
    obs_dict, _ = env.reset()

    scenario = config['environment'].get('classic_scenario', 'none')
    scenario_suffix = f"_{scenario}" if scenario else ""

    model = None
    if args.algo == 'gnn':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models', f'gnn_3d_best{scenario_suffix}.pth')
        model = GNNAgent3D("visualizer", env.action_space("robot_0"), config=config)
        if os.path.exists(model_path):
            model.load_state_dict(torch.load(model_path, weights_only=True))
            model.eval()
            print(f"✅ GNN Model Loaded: {model_path}")
        else:
            print(f"❌ GNN Model not found: {model_path}")
            model = None
    elif args.algo == 'ppo':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'ppo_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = PPO.load(model_path)
            print(f"✅ PPO Model Loaded: {model_path}")
        else:
            print(f"❌ PPO Model not found: {model_path}")
            model = None
    elif args.algo == 'sac':
        model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', f'sac_3d_final{scenario_suffix}.zip')
        if os.path.exists(model_path):
            model = SAC.load(model_path)
            print(f"✅ SAC Model Loaded: {model_path}")
        else:
            print(f"❌ SAC Model not found: {model_path}")
            model = None

    # --- Estética Premium (Modern Sci-Fi 3D) ---
    window.color = color.rgb(15, 18, 22)  # Fundo noturno elegante
    
    # Iluminação e Sombras
    DirectionalLight(y=2, z=-3, shadows=True, rotation=(45, -45, 45))
    AmbientLight(color=color.rgba(120, 120, 120, 0.3))
    
    # Arena Base
    Entity(model='quad', scale=env.arena_radius * 2.5, color=color.hsv(0, 0, 0.08), texture='white_cube', z=0.1) # Grelha fundo
    Entity(model='circle', scale=env.arena_radius * 2, color=color.hsv(220, 0.2, 0.15), z=0.05)
    Entity(model='circle', scale=env.arena_radius * 2, color=color.hsv(180, 0.8, 0.8), mode='line', z=0.0)
    
    # Ninho: Efeito holográfico/Glow
    Entity(model='sphere', color=color.hsv(130, 0.8, 0.9), scale=env.nest_radius * 2, position=(env.nest_pos[0], env.nest_pos[1], 0), unlit=True)
    Entity(model='circle', color=color.hsv(130, 0.8, 0.9, 0.3), scale=env.nest_radius * 4, position=(env.nest_pos[0], env.nest_pos[1], 0.01), unlit=True)
    
    # Obstáculos
    for obs_pos in env.obstacles:
        Entity(model='sphere', color=color.hsv(10, 0.8, 0.7), scale=env.obstacle_radius * 2, position=(obs_pos[0], obs_pos[1], -0.15), texture='noise')
        
    # Paredes: Textura metálica/concreto
    for wall in env.walls:
        pos_3d = (wall['pos'][0], wall['pos'][1], -0.2)
        size_3d = (wall['size'][0], wall['size'][1], 0.4) # Dar profundidade real 3D (Z)
        Entity(model='cube', color=color.hsv(215, 0.3, 0.6), scale=size_3d, position=pos_3d, texture='white_cube')
    
    # Robôs: Design tipo Khepera (Cilindros achatados com LED)
    robot_views = {}
    for agent_id, pos in zip(env.agents, env.agent_positions):
        # O cilindro aponta para Y no Ursina. Rodamos 90 graus no X para apontar para o Z (para fora do ecrã)
        r = Entity(model='cylinder', color=color.hsv(210, 0.9, 0.9), scale=(env.robot_radius * 2, 0.15, env.robot_radius * 2), rotation_x=90, position=(pos[0], pos[1], -0.15))
        # Adicionar um pequeno "LED" ou "Olho" brilhante no centro
        Entity(parent=r, model='sphere', color=color.white, scale=0.4, y=0.5, unlit=True)
        robot_views[agent_id] = r

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
                new_p = env.agent_positions[idx]
                # Atualizar a posição (adicionando Z=-0.15 para os manter fisicamente acima do chão)
                view.position = (new_p[0], new_p[1], -0.15)

    app.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--algo', type=str, required=True, choices=['gnn', 'ppo', 'sac'])
    args = parser.parse_args()
    main(args)