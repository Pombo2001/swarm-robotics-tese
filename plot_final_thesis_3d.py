import torch
from ursina import *
import numpy as np
import sys
import os
from stable_baselines3 import PPO

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from environment.swarm_env_3d import SwarmForagingEnv3D

app = Ursina()
window.color = color.black
window.title = 'Swarm 3D - PPO Baseline'
window.borderless = False
window.exit_button.visible = False
camera.position = (0, 15, -30)
camera.rotation_x = 25

DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 1.0))

config_path = os.path.join(os.path.dirname(__file__), 'configs/foraging.yaml')
env = SwarmForagingEnv3D(config_path)
env.render_mode = None

model_path = os.path.join(os.path.dirname(__file__), 'results/models_ppo/ppo_3d_final')
if os.path.exists(model_path + ".zip"):
    os.chmod(model_path + ".zip", 0o666) # [cite: 2026-02-23]
    model = PPO.load(model_path)
else:
    sys.exit("❌ Modelo PPO não encontrado!")

obs_dict, _ = env.reset()

Grid(scale=env.arena_radius*4, color=color.dark_gray, rotation_x=90, y=-env.arena_radius)
nest_view = Entity(model='sphere', color=color.rgba(0, 255, 0, 80), scale=env.nest_radius * 2)
obs_views = [Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2) for _ in range(env.num_obstacles)]
robot_views = [Entity(model='cube', color=color.orange, scale=env.robot_radius * 2) for _ in range(env.num_agents)]

def update():
    global obs_dict
    actions = {a: model.predict(obs_dict[a], deterministic=True)[0] for a in env.agents}
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
        obs_dict, _ = env.reset()

app.run()