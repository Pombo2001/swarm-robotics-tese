import torch
from ursina import *
import numpy as np
import sys
import os
import yaml
from stable_baselines3 import PPO

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

app = Ursina()

window.title = 'Swarm 3D - PPO Baseline'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
EditorCamera()

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
config_path = os.path.join(base_dir, 'configs', 'foraging.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

vis_config = config.get('visualization', {})
speed_slider = Slider(min=vis_config.get('speed_slider_min', 1),
                      max=vis_config.get('speed_slider_max', 120),
                      default=vis_config.get('speed_slider_default', 30),
                      text='Velocidade', dynamic=True)
speed_slider.position = (-0.85, 0.45)
speed_slider.scale = 1.2
time_accumulator = 0.0

env = SwarmForagingEnv3D(config_path=config_path)
env.render_mode = None
obs_dict, _ = env.reset()

# Convenção de nomes: Sandbox ("none") sem sufixo; restantes com "_{scenario}".
# Fallback para o modelo sem sufixo se o do cenário ainda não tiver sido treinado.
scenario = config['environment'].get('classic_scenario', 'none')
suffix = f"_{scenario}" if scenario and scenario != "none" else ""
model_path = os.path.join(base_dir, 'results', 'models_ppo', f'ppo_3d_final{suffix}')
if not os.path.exists(model_path + ".zip"):
    model_path = os.path.join(base_dir, 'results', 'models_ppo', 'ppo_3d_final')

if os.path.exists(model_path + ".zip"):
    os.chmod(model_path + ".zip", 0o666)
    model = PPO.load(model_path, device='cpu')
    print(f"[OK] Modelo PPO 3D carregado: {model_path}")
else:
    print(f"[ERRO] {model_path}.zip não encontrado!")
    sys.exit()

Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba(255, 255, 255, 30), double_sided=True)
nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2, position=tuple(env.nest_pos))

obs_views = []
for obs_pos in env.obstacles:
    obs_views.append(Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2, position=tuple(obs_pos)))

# A porta cooperativa é uma parede (door_wall_index), tratada no loop das paredes.
wall_views = []
for i, wall in enumerate(env.walls):
    is_door = (getattr(env, 'classic_scenario', '') in ("cooperative_door", "cooperative_door_bypass")
               and hasattr(env, 'door_wall_index') and i == env.door_wall_index)
    wall_color = color.red if is_door else color.rgba(50, 50, 50, 180)
    wall_views.append(Entity(
        model='cube',
        color=wall_color,
        scale=tuple(wall['size']),
        position=tuple(wall['pos'])
    ))

def wall_min_dist(pos, walls, arena_radius):
    min_d = arena_radius - float(np.linalg.norm(pos[:2]))
    for wall in walls:
        half  = wall['size'][:2] / 2.0
        delta = np.abs(pos[:2] - wall['pos'][:2]) - half
        d = float(np.linalg.norm(np.maximum(delta, 0.0)))
        if d < min_d:
            min_d = d
    return min_d

def robot_min_dist(pos, all_positions, idx):
    min_d = 999.0
    for j, other in enumerate(all_positions):
        if j == idx:
            continue
        d = float(np.linalg.norm(pos[:2] - other[:2]))
        if d < min_d:
            min_d = d
    return min_d

robot_views = []
for r_pos in env.agent_positions:
    robot = Entity(model='cube', color=color.orange, scale=env.robot_radius * 2, position=tuple(r_pos))
    Entity(parent=robot, model='cube', color=color.white, scale=(0.8, 0.3, 0.4), position=(0, 0, 0.5))
    robot_views.append(robot)


def update():
    global obs_dict, time_accumulator

    time_accumulator += time.dt
    target_delay = 1.0 / speed_slider.value

    if time_accumulator >= target_delay:
        time_accumulator = 0.0

        actions = {}
        for agent_id in env.agents:
            obs = np.array(obs_dict[agent_id], dtype=np.float32)
            action, _ = model.predict(obs, deterministic=True)
            actions[agent_id] = action

        obs_dict, rewards, terms, truncs, infos = env.step(actions)

        nest_view.position = tuple(env.nest_pos)

        for i, obs_pos in enumerate(env.obstacles):
            obs_views[i].position = tuple(obs_pos)

        for i, r_pos in enumerate(env.agent_positions):
            robot_views[i].position = tuple(r_pos)

            heading = env.agent_headings[i]
            robot_views[i].look_at(robot_views[i].position + Vec3(*heading))

            w_dist = wall_min_dist(r_pos, env.walls, env.arena_radius)
            r_dist = robot_min_dist(r_pos, env.agent_positions, i)

            if env.signaling[i] == 1.0:
                robot_views[i].color = color.gold
                robot_views[i].scale = env.robot_radius * 4
            elif w_dist < 0.8:
                robot_views[i].color = color.red
                robot_views[i].scale = env.robot_radius * 2
            elif r_dist < 1.0:
                robot_views[i].color = color.cyan
                robot_views[i].scale = env.robot_radius * 2
            else:
                robot_views[i].color = color.orange
                robot_views[i].scale = env.robot_radius * 2

        if any(terms.values()):
            obs_dict, _ = env.reset()


app.run()