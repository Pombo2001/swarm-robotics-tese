import torch
from ursina import *
import numpy as np
import sys
import os
import yaml
import argparse
from stable_baselines3 import PPO, SAC

# Adicionar a raiz do projeto ao path para encontrar os módulos src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D

# --- PARSER DE ARGUMENTOS ---
parser = argparse.ArgumentParser(description="Visualizador 3D para os modelos da Tese.")
parser.add_argument("--algo", type=str, required=True, choices=['gnn', 'ppo', 'sac'], help="Algoritmo a visualizar (gnn, ppo, sac).")
args, unknown = parser.parse_known_args() # Ignorar argumentos extra que o Ursina possa enviar

# --- APLICAÇÃO URSINA (ÚNICA) ---
app = Ursina()

# --- CONFIGURAÇÕES E AMBIENTE ---
base_dir = PROJECT_ROOT
config_path = os.path.join(base_dir, 'configs', 'foraging.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Extrair o cenário atual para carregar o modelo correto
current_scenario = config['environment'].get('classic_scenario', 'none')
if current_scenario == 'none':
    # Se for 'none', usamos um nome de modelo genérico que pode corresponder ao modo sandbox
    model_suffix = "final" 
    print("INFO: A carregar modelo do modo SANDBOX (sem cenário clássico).")
else:
    model_suffix = current_scenario
    print(f"INFO: A carregar modelo para o cenário: {model_suffix}")

window.title = f'Swarm 3D - Visualizador: {args.algo.upper()} ({model_suffix.upper()})'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
EditorCamera()

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

vis_config = config.get('visualization', {})
speed_slider = Slider(min=vis_config.get('speed_slider_min', 1),
                      max=vis_config.get('speed_slider_max', 120),
                      default=vis_config.get('speed_slider_default', 30),
                      text='Velocidade', dynamic=True)
speed_slider.position = (-0.85, 0.45)
speed_slider.scale = 1.2
time_accumulator = 0.0

env = SwarmForagingEnv3D(config_path=config_path)
obs_dict, _ = env.reset()

# --- LÓGICA DE CARREGAMENTO DE MODELOS ---
model = None
if args.algo == 'gnn':
    # O GNN pode ter uma convenção de nome diferente, ajuste se necessário
    model_filename = f'gnn_3d_{model_suffix}.pth'
    model_path = os.path.join(base_dir, 'results', 'models', model_filename)
    model = GNNAgent3D("gnn_viewer", env.action_space("robot_0"), config_path)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, weights_only=True))
        model.eval()
        print(f"✅ Modelo GNN carregado: {model_path}")
    else:
        print(f"❌ Erro: Modelo GNN não encontrado em {model_path}!")
        application.quit()
elif args.algo == 'ppo':
    model_filename = f'ppo_3d_{model_suffix}.zip'
    model_path = os.path.join(base_dir, 'results', 'models_ppo', model_filename)
    if os.path.exists(model_path):
        model = PPO.load(model_path, device='cpu')
        print(f"✅ Modelo PPO carregado: {model_path}")
    else:
        print(f"❌ Erro: Modelo PPO não encontrado em {model_path}!")
        application.quit()
elif args.algo == 'sac':
    model_filename = f'sac_3d_{model_suffix}.zip'
    model_path = os.path.join(base_dir, 'results', 'models_ppo', model_filename)
    if os.path.exists(model_path):
        model = SAC.load(model_path, device='cpu')
        print(f"✅ Modelo SAC carregado: {model_path}")
    else:
        print(f"❌ Erro: Modelo SAC não encontrado em {model_path}!")
        application.quit()

# --- CRIAÇÃO DE ENTIDADES (CÓDIGO COMUM) ---
Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 30), double_sided=True)
nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2, position=tuple(env.nest_pos))

obs_views = [Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2, position=tuple(obs_pos)) for obs_pos in env.obstacles]
wall_views = []
for i, wall in enumerate(env.walls):
    is_door = getattr(env, 'classic_scenario', '') == "cooperative_door" and hasattr(env, 'door_wall_index') and i == env.door_wall_index
    wall_color = color.red if is_door else color.rgba(50, 50, 50, 180)
    wall_views.append(Entity(model='cube', color=wall_color, scale=tuple(wall['size']), position=tuple(wall['pos'])))

robot_views, arrow_views = [], []
for r_pos in env.agent_positions:
    robot = Entity(model='cube', color=color.orange, scale=env.robot_radius * 2, position=tuple(r_pos))
    arrow = Entity(model='cube', color=color.red, scale=(0.05, 0.05, 0.6), position=tuple(r_pos))
    robot_views.append(robot)
    arrow_views.append(arrow)

# --- LOOP DE UPDATE ---
def update():
    global obs_dict, time_accumulator
    time_accumulator += time.dt
    target_delay = 1.0 / speed_slider.value

    if time_accumulator >= target_delay:
        time_accumulator = 0.0
        actions = {}
        for agent_id in env.agents:
            obs = np.array(obs_dict[agent_id], dtype=np.float32)
            if args.algo == 'gnn':
                obs_tensor = torch.tensor(obs).unsqueeze(0)
                with torch.no_grad():
                    action = model(obs_tensor).squeeze(0).numpy()
            else: # PPO ou SAC
                action, _ = model.predict(obs, deterministic=True)
            actions[agent_id] = action

        obs_dict, _, terms, _, _ = env.step(actions)

        nest_view.position = tuple(env.nest_pos)
        for i, obs_pos in enumerate(env.obstacles):
            obs_views[i].position = tuple(obs_pos)
        for i, wall in enumerate(env.walls):
            wall_views[i].position = tuple(wall['pos'])

        for i, r_pos in enumerate(env.agent_positions):
            robot_views[i].position = tuple(r_pos)
            heading = env.agent_headings[i]
            arrow_pos = r_pos + heading * (env.robot_radius + 0.2)
            arrow_views[i].position = tuple(arrow_pos)
            
            # Garantir que passamos um tuple seguro para o Ursina
            look_target = arrow_pos + heading
            arrow_views[i].look_at(tuple(look_target))
            
            if env.signaling[i] == 1.0:
                robot_views[i].color = color.gold
                robot_views[i].scale = env.robot_radius * 4
                arrow_views[i].visible = False
            else:
                robot_views[i].color = color.orange
                robot_views[i].scale = env.robot_radius * 2
                arrow_views[i].visible = True

        if any(terms.values()):
            obs_dict, _ = env.reset()

app.run()
