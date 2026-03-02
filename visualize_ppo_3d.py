import torch
from ursina import *
import numpy as np
import sys
import os
from stable_baselines3 import PPO

# --- 1. CONFIGURAÇÃO DE CAMINHOS ---
# Forçar o Python a reconhecer a pasta RAIZ
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# A LINHA QUE CORRIGE O ERRO (já com o "src." incluído!)
from src.environment.swarm_env_3d import SwarmForagingEnv3D

# --- 2. INICIALIZAÇÃO DA URSINA ---
app = Ursina(development_mode=False, size=(1280, 720))

window.title = 'Swarm 3D - PPO Baseline'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True
window.color = color.black
window.center_on_screen()

camera.position = (0, 20, -40)
camera.rotation_x = 25
EditorCamera()

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

# --- 3. CARREGAR AMBIENTE E PPO ---
config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
env = SwarmForagingEnv3D(config_path=config_path)
env.render_mode = None

model_path = os.path.join(PROJECT_ROOT, 'results', 'models_ppo', 'ppo_3d_final')

if os.path.exists(model_path + ".zip"):
    os.chmod(model_path + ".zip", 0o666)  # Permissões de leitura/escrita garantidas
    model = PPO.load(model_path)
    print("✅ Modelo PPO 3D carregado com sucesso!")
else:
    print(f"❌ Erro: {model_path}.zip não encontrado! Tens a certeza que o treino já acabou?")
    sys.exit()

obs_dict, _ = env.reset()

# --- 4. OBJETOS VISUAIS 3D ---
Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 30), wireframe=True, double_sided=True)
Entity(model=Grid(20, 20), scale=env.arena_radius * 4, color=color.dark_gray, rotation_x=90, y=-env.arena_radius)

nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2)
obs_views = [Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2) for _ in range(env.num_obstacles)]
robot_views = [Entity(model='cube', color=color.orange, scale=env.robot_radius * 2) for _ in range(env.num_agents)]


# --- 5. LOOP DE SIMULAÇÃO ---
def update():
    global obs_dict

    actions = {}
    for agent_id in env.agents:
        obs = obs_dict[agent_id]
        action, _ = model.predict(obs, deterministic=True)
        actions[agent_id] = action

    obs_dict, rewards, terms, truncs, _ = env.step(actions)

    nest_view.position = tuple(env.nest_pos)
    for i, obs_pos in enumerate(env.obstacles):
        obs_views[i].position = tuple(obs_pos)

    for i, r_pos in enumerate(env.agent_positions):
        robot_views[i].position = tuple(r_pos)
        if env.signaling[i] == 1.0:
            robot_views[i].color = color.gold
            robot_views[i].scale = env.robot_radius * 4
        else:
            robot_views[i].color = color.orange
            robot_views[i].scale = env.robot_radius * 2

    if any(terms.values()):
        obs_dict, _