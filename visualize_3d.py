import torch            # <-- PyTorch primeiro
from ursina import * # <-- Ursina numa linha
import numpy as np      # <-- Numpy noutra linha
import sys
import os
import os

# Adicionar a pasta 'src' para os novos modelos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from environment.swarm_env_3d import SwarmForagingEnv3D
from agents.gnn_agent_3d import GNNAgent3D

# Inicializar o Motor 3D
app = Ursina()

# --- CONFIGURAÇÃO DA CÂMARA E LUZ ---
window.title = 'Swarm 3D - GNN Elite'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
EditorCamera()

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

# --- CARREGAR O AMBIENTE E A IA ---
# Usamos caminho absoluto para evitar erro de diretório
base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, 'configs', 'foraging.yaml')

env = SwarmForagingEnv3D(config_path=config_path)
env.render_mode = None
obs_dict, _ = env.reset()

model = GNNAgent3D("template_3d", env.action_space("robot_0"))
model_path = os.path.join(base_dir, 'results/models/gnn_3d_best.pth')

if os.path.exists(model_path):
    os.chmod(model_path, 0o666) # [cite: 2026-02-23]
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    print(f"✅ Modelo carregado: {model_path}")

# --- CRIAR OS OBJETOS 3D (O Teu Estilo Original) ---
# Arena (O cubo branco que preferes)
Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 30), double_sided=True)

# Ninho
nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2)

# Obstáculos
obs_views = []
for i in range(env.num_obstacles):
    obs_views.append(Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2))

# Drones
robot_views = []
for i in range(env.num_agents):
    robot_views.append(Entity(model='cube', color=color.cyan, scale=env.robot_radius * 2))

# --- O LOOP DE SIMULAÇÃO ---
def update():
    global obs_dict
    obs_list = [obs_dict[a] for a in env.agents]
    obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)

    with torch.no_grad():
        actions_tensor = model(obs_tensor)
        actions = {id: act for id, act in zip(env.agents, actions_tensor.cpu().numpy())}

    obs_dict, rewards, terms, truncs, infos = env.step(actions)

    nest_view.position = tuple(env.nest_pos)
    for i, obs_pos in enumerate(env.obstacles):
        obs_views[i].position = tuple(obs_pos)

    for i, r_pos in enumerate(env.agent_positions):
        robot_views[i].position = tuple(r_pos)
        if env.signaling[i] == 1.0:
            robot_views[i].color = color.gold
            robot_views[i].scale = env.robot_radius * 4
        else:
            robot_views[i].color = color.cyan
            robot_views[i].scale = env.robot_radius * 2

    if any(terms.values()):
        obs_dict, _ = env.reset()

app.run()