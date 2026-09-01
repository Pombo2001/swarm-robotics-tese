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

from src.environment.swarm_env_3d import SwarmForagingEnv3D, DOOR_SCENARIOS
from src.agents.gnn_agent_3d import GNNAgent3D
from src.scenarios import SCENARIOS

def main(args):
    app = Ursina()

    config_path = args.config or os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
    print(f"DEBUG: Loading configuration from {config_path}")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # --scenario: sem isto, ver outro cenário obrigava a EDITAR o
    # configs/foraging.yaml partilhado — o mesmo ficheiro que os trainers leem e
    # que as campanhas do servidor reescrevem por sed. O ambiente é construído a
    # partir do dicionário já alterado, para que nada seja escrito no disco.
    if args.scenario:
        config['environment']['classic_scenario'] = args.scenario
    scenario = config['environment'].get('classic_scenario', 'none')
    print(f"DEBUG: Selected classic scenario: {scenario}")

    window.title = f'Swarm 3D - Visualizer: {args.algo.upper()} · {scenario}'

    env = SwarmForagingEnv3D(config=config)
    obs_dict, _ = env.reset()

    # EIXOS E ALTURA
    # Convenção da cena (a mesma do visualize_mapa_grande.py): o mapa é o plano XY
    # e a vertical é -Z (o chão está em z=+0.1 e o que sobe tem z menor).
    #
    # A altura REAL dos agentes é desenhada. Fixá-los num z constante apaga do
    # ecrã a dimensão onde vivem os defeitos de física — foi assim que campeões a
    # 59 m de altura, a atravessar o mapa por cima de paredes de 30 m, apareciam
    # colados ao chão.
    def cena_z(mundo_z, pousado=-0.15):
        return pousado - float(mundo_z)

    # As paredes são caixas de 2x arena_radius (120 m no mapa grande): desenhadas
    # à altura real tapam a cena inteira. Desenham-se mais baixas, mas nunca
    # abaixo do que os agentes conseguem subir — senão o ecrã mostra um robô
    # legítimo a passar «por cima» de uma parede que na verdade o veda. O HUD diz
    # sempre a altura real, e avisa quando algum robô passa acima do que está
    # desenhado, que é o sintoma a apanhar.
    alcance_z = (env.MAPA_GRANDE_TETO if scenario == 'mapa_grande'
                 else float(env.arena_radius))
    altura_real = float(env.walls[0]['size'][2]) if len(env.walls) else 0.0
    altura_visual = (args.altura_paredes if args.altura_paredes is not None
                     else min(max(2.0 * alcance_z, 0.4), altura_real or 0.4, 8.0))

    # Câmara enquadrada pelo raio: com `EditorCamera()` cru, o mapa grande (r=60,
    # 4× os outros) abria fora do enquadramento. O pivô é o centro do mapa e a
    # distância vem do raio, como no visualize_mapa_grande.py.
    editor_cam = EditorCamera(rotation=(45, 0, 0))
    editor_cam.position = (0, 0, 0)
    camera.z = -env.arena_radius * 2.2
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

    # Estética Premium (Modern Sci-Fi 3D)
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
    def _criar_parede(wall):
        return Entity(model='cube', color=color.hsv(215, 0.3, 0.6),
                      texture='white_cube',
                      scale=(wall['size'][0], wall['size'][1], altura_visual),
                      position=(wall['pos'][0], wall['pos'][1],
                                -altura_visual / 2))

    wall_entities = [_criar_parede(w) for w in env.walls]

    # Robôs
    # `model='cylinder'` NÃO existe no Ursina 8.3.0 (só sphere/cube/quad/circle/
    # diamond/plane): dá «missing model» e a entidade fica INVISÍVEL, ou seja, o
    # visualizador corre episódios inteiros sem mostrar um robô. Escala =
    # diâmetro real (0,30 m).
    robot_views = {}
    for agent_id, pos in zip(env.agents, env.agent_positions):
        r = Entity(model='sphere', color=color.hsv(210, 0.9, 0.9),
                   scale=env.robot_radius * 2,
                   position=(pos[0], pos[1], cena_z(pos[2])))
        # Ponto claro por cima (−z é a vertical), para se ver que é um agente e
        # não um obstáculo: os obstáculos são esferas vermelhas de raio 0,2.
        Entity(parent=r, model='sphere', color=color.white, scale=0.45,
               z=-0.9, unlit=True)
        robot_views[agent_id] = r

    # HUD: o que se vê tem de dizer o que é. A altura desenhada das paredes é
    # menor que a real, e sem esta linha o ecrã afirmaria uma geometria falsa.
    hud = Text(text='', position=(-0.86, 0.47), scale=0.7,
               color=color.hsv(0, 0, 0.75))

    def _hud():
        zs = env.agent_positions[:, 2]
        acima = float(np.max(np.abs(zs))) > altura_visual
        hud.color = color.hsv(35, 0.9, 1.0) if acima else color.hsv(0, 0, 0.75)
        hud.text = (
            f'{scenario}  ·  {args.algo.upper()}  ·  arena r={env.arena_radius:.0f} m'
            f'  ·  episódio {state["episode"]}\n'
            f'recolhas: {int(env.total_food_collected)}  ·  '
            f'altura dos robôs: {zs.min():+.2f} a {zs.max():+.2f} m'
            + (f' (teto {env.MAPA_GRANDE_TETO:.0f} m)' if scenario == 'mapa_grande' else '')
            + '\n'
            f'paredes desenhadas a {altura_visual:.1f} m; vedam de facto até '
            f'{altura_real:.0f} m (2×raio da arena)'
            + ('\n⚠ ha robos ACIMA da altura desenhada — o que se ve por cima '
               'das paredes nao e uma passagem' if acima else ''))

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
        wall_entities.extend(_criar_parede(w) for w in env.walls)

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

        # Atualizar robôs — com a altura REAL (ver cena_z)
        for agent_id, view in robot_views.items():
            idx = env.agents.index(agent_id)
            new_p = env.agent_positions[idx]
            view.position = (new_p[0], new_p[1], cena_z(new_p[2]))
        _hud()

        # Atualizar ninho (move em cooperative_perception)
        nest_entity.position = (env.nest_pos[0], env.nest_pos[1], 0)
        nest_glow.position = (env.nest_pos[0], env.nest_pos[1], 0.01)

        # Atualizar posições dos obstáculos dinâmicos
        for i, obs_e in enumerate(obs_entities):
            if i < len(env.obstacles):
                obs_e.position = (env.obstacles[i][0], env.obstacles[i][1], -0.15)

        # Porta cooperativa: animação de abertura (deslize para cima)
        if scenario in DOOR_SCENARIOS and not state['door_animated']:
            door_idx = getattr(env, 'door_wall_index', None)
            if door_idx is not None and not getattr(env, 'door_active', True):
                if door_idx < len(wall_entities):
                    door_e = wall_entities[door_idx]
                    door_e.color = color.hsv(45, 0.9, 1.0)  # amarelo brilhante
                    # Sobe: a vertical da cena é −Z (ver cena_z). Estava
                    # `y + 6`, que desliza a porta 6 m para NORTE, ao longo do
                    # chão — o comentário dizia «deslize para cima» e o ecrã
                    # mostrava a porta a afastar-se pelo mapa.
                    door_e.animate_position(
                        Vec3(door_e.x, door_e.y, door_e.z - altura_visual * 1.5),
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
    parser.add_argument('--scenario', type=str, default=None,
                        # dict.fromkeys desduplica: o mapa_grande já entrou no
                        # src.scenarios e aparecia duas vezes na ajuda.
                        choices=list(dict.fromkeys(list(SCENARIOS) + ['mapa_grande'])),
                        help='cenário a visualizar (default: o do config). '
                             'Não escreve no configs/foraging.yaml.')
    parser.add_argument('--config', type=str, default=None,
                        help='caminho do YAML (default: configs/foraging.yaml)')
    parser.add_argument('--altura-paredes', type=float, default=None,
                        help='altura VISUAL das paredes em metros (default: o '
                             'alcance vertical dos agentes no cenário). A altura '
                             'real é sempre 2×raio da arena e está no HUD.')
    args = parser.parse_args()
    main(args)
