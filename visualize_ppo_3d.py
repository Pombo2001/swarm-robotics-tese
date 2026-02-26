import torch
from ursina import *
import numpy as np
import sys
import os
from stable_baselines3 import PPO

# Adicionar a pasta 'src' para os novos modelos
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_PATH, 'src'))
from environment.swarm_env_3d import SwarmForagingEnv3D

# Inicializar o Motor 3D
app = Ursina()

# --- CONFIGURAÇÃO DA JANELA ---
window.title = 'Swarm 3D - PPO Baseline'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
EditorCamera()

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

# --- CARREGAR AMBIENTE E PPO ---
config_path = os.path.join(BASE_PATH, 'configs', 'foraging.yaml')
env = SwarmForagingEnv3D(config_path=config_path)
env.render_mode = None

# Caminho absoluto para evitar erro de diretório [cite: 2026-02-23]
model_path = os.path.join(BASE_PATH, 'results', 'models_ppo', 'ppo_3d_final')

if os.path.exists(model_path + ".zip"):
    os.chmod(model_path + ".zip", 0o666)  # [cite: 2026-02-23]
    model = PPO.load(model_path)  # Agora o 'PPO' já está definido!
    print(f"✅ Modelo PPO 3D carregado com sucesso!")
else:
    print(f"❌ Erro: {model_path}.zip não encontrado!")
    sys.exit()

obs_dict, _ = env.reset()

# --- CRIAR OS OBJETOS 3D ---
# Arena (O cubo branco original que preferes)
Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 20), double_sided=True)

nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2)
obs_views = [Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2) for _ in range(env.num_obstacles)]
robot_views = [Entity(model='cube', color=color.orange, scale=env.robot_radius * 2) for _ in range(env.num_agents)]


# --- O LOOP DE SIMULAÇÃO ---
def update():
    global obs_dict

    # Decisão PPO para cada robô
    actions = {}
    for agent_id in env.agents:
        obs = obs_dict[agent_id]
        action, _ = model.predict(obs, deterministic=True)
        actions[agent_id] = action

    # Física
    obs_dict, rewards, terms, truncs, _ = env.step(actions)

    # Sincronização Visual
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
        obs_dict, _ = env.reset()


app.run()