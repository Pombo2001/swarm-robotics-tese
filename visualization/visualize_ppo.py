import torch
from ursina import *
import numpy as np
import argparse
import sys
import os
import yaml
from stable_baselines3 import PPO

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D, DOOR_SCENARIOS

app = Ursina()

window.title = 'Swarm 3D - PPO Baseline'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
_camera_editor = EditorCamera()   # rato: orbitar, roda: zoom

DirectionalLight(y=2, z=3, shadows=False)  # sombras dinamicas em ~140 entidades eram caras
AmbientLight(color=color.rgba32(100, 100, 100, 255))

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
config_path = os.path.join(base_dir, 'configs', 'foraging.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Cenário/dimensão por ARGUMENTO, com override em memória. Antes, mudar de cenário
# obrigava a reescrever configs/foraging.yaml (era o que o launcher antigo fazia) —
# o ficheiro ficava alterado no disco e o config do repositório perdia-se.
# parse_known_args: o Ursina também olha para o sys.argv e não queremos colidir.
_ap = argparse.ArgumentParser(add_help=False)
_ap.add_argument('--scenario', type=str, default=None)
_ap.add_argument('--agents', type=int, default=None)
# Raiz dos modelos: por omissão a pasta ATIVA (results/), mas pode apontar para os
# modelos arquivados de uma campanha — results/graficos_tese/<sessão>/modelos —,
# que têm a mesma estrutura (models/, models_ppo/, models_sac/). Evita ter de
# restaurar modelos por cima dos ativos só para espreitar um treino antigo.
_ap.add_argument('--models-root', type=str, default=None)
_args, _ = _ap.parse_known_args()
MODELS_ROOT = _args.models_root or os.path.join(base_dir, 'results')
if _args.scenario:
    config['environment']['classic_scenario'] = _args.scenario
if _args.agents:
    config['environment']['num_agents'] = _args.agents

vis_config = config.get('visualization', {})
speed_slider = Slider(min=vis_config.get('speed_slider_min', 1),
                      max=vis_config.get('speed_slider_max', 120),
                      default=vis_config.get('speed_slider_default', 30),
                      text='Velocidade', dynamic=True)
speed_slider.position = (-0.85, 0.45)
speed_slider.scale = 1.2
time_accumulator = 0.0

env = SwarmForagingEnv3D(config=config)   # config já com o override do --scenario
env.render_mode = None
obs_dict, _ = env.reset()

# Convenção de nomes: Sandbox ("none") sem sufixo; restantes com "_{scenario}".
# Fallback para o modelo sem sufixo se o do cenário ainda não tiver sido treinado.
scenario = config['environment'].get('classic_scenario', 'none')
suffix = f"_{scenario}" if scenario and scenario != "none" else ""
model_path = os.path.join(MODELS_ROOT, 'models_ppo', f'ppo_3d_final{suffix}')
if not os.path.exists(model_path + ".zip"):
    model_path = os.path.join(MODELS_ROOT, 'models_ppo', 'ppo_3d_final')

if os.path.exists(model_path + ".zip"):
    os.chmod(model_path + ".zip", 0o666)
    model = PPO.load(model_path, device='cpu')
    print(f"[OK] Modelo PPO 3D carregado: {model_path}")
else:
    print(f"[ERRO] {model_path}.zip não encontrado!")
    sys.exit()

# Vista inicial: de cima e recuada o suficiente para a arena caber toda no ecrã — a
# mesma perspetiva das figuras do relatório. Sem isto, a câmara arranca dentro dos
# muros (que têm 30 de profundidade) e a primeira coisa que se vê é uma parede colada
# à lente. O EditorCamera continua livre a partir daqui.
_camera_editor.rotation_x = 89
_camera_editor.position = (0, 0, 0)
camera.z = -(env.arena_radius * 6)
_camera_editor.target_z = camera.z   # o EditorCamera faz lerp de camera.z para target_z

# ATENÇÃO ao rgba32: nesta versão do Ursina, color.rgba() recebe componentes 0–1 e é
# color.rgba32() que recebe 0–255. Com rgba(255,255,255,30) o alfa 30 era saturado para
# 1.0 — a "caixa" da arena ficava BRANCA OPACA e tapava a cena inteira, e era por isso
# que só se via o mapa depois de carregar F10 (que passa para wireframe).
Entity(model='cube', scale=env.arena_radius * 2, color=color.rgba32(255, 255, 255, 30), double_sided=True)
nest_view = Entity(model='sphere', color=color.green, scale=env.nest_radius * 2, position=tuple(env.nest_pos))

obs_views = []
for obs_pos in env.obstacles:
    obs_views.append(Entity(model='sphere', color=color.gray, scale=env.obstacle_radius * 2, position=tuple(obs_pos)))

# A porta cooperativa é uma parede (door_wall_index), tratada no loop das paredes.
wall_views = []
for i, wall in enumerate(env.walls):
    is_door = (getattr(env, 'classic_scenario', '') in DOOR_SCENARIOS
               and hasattr(env, 'door_wall_index') and i == env.door_wall_index)
    wall_color = color.red if is_door else color.rgba32(50, 50, 50, 180)
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


# Teto de passos de simulação por frame de render. Permite que a barra de
# velocidade ultrapasse o limite de FPS: antes fazia-se 1 passo por frame,
# logo ~60 passos/s no máximo mesmo com a barra a 120 (era a causa do "lento").
MAX_STEPS_PER_FRAME = 20


def update():
    global obs_dict, time_accumulator

    time_accumulator += time.dt
    target_delay = 1.0 / speed_slider.value

    # Avança a simulação tantos passos quantos couberem neste frame (não só 1).
    stepped = False
    n_steps = 0
    while time_accumulator >= target_delay and n_steps < MAX_STEPS_PER_FRAME:
        time_accumulator -= target_delay
        n_steps += 1
        stepped = True

        # Um único predict (batch) para todos os agentes — SB3 aceita um lote de
        # observações e é bem mais rápido que N predicts individuais.
        agent_ids = list(env.agents)
        obs_batch = np.stack([np.asarray(obs_dict[a], dtype=np.float32) for a in agent_ids])
        act_batch, _ = model.predict(obs_batch, deterministic=True)
        actions = {aid: act_batch[k] for k, aid in enumerate(agent_ids)}

        obs_dict, rewards, terms, truncs, infos = env.step(actions)

        if any(terms.values()):
            obs_dict, _ = env.reset()
            break

    if not stepped:
        return

    # Atualiza a parte visual uma vez por frame (última posição da simulação).
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


app.run()