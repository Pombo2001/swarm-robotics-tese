"""
visualize_mapa_grande.py — MAPA GRANDE no visualizador Ursina
=============================================================
MESMO visualizador dos outros mapas: Ursina, `EditorCamera()` (câmara livre),
as mesmas cores e a mesma convenção de eixos do `main_visualizer.py`. Um só
visualizador = um só sítio onde pode haver bugs.

A geometria vem do AMBIENTE (`classic_scenario: mapa_grande`), não de um
rascunho à parte: paredes, porta, ninho, spawn e obstáculos são exatamente os
que os robôs vão treinar.

Diferença face ao `main_visualizer.py`: aqui não se carrega modelo nem se
simula — a cena está PARADA, para se inspecionar o mapa (é para isso que serve).
Para ver agentes treinados a mexer neste mapa, usa o visualizador normal com
`--scenario mapa_grande`, como em qualquer outro cenário.

Uso:
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py --radius 45
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py --wall-height 8
"""
import argparse

import os
import sys

import numpy as np
from ursina import (Ursina, Entity, EditorCamera, DirectionalLight, AmbientLight,
                    Text, color, camera, window)

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Constantes reais (configs/foraging.yaml) — iguais às do ambiente.
NEST_RADIUS = 1.5
ROBOT_RADIUS = 0.15
OBSTACLE_RADIUS = 0.2
NUM_AGENTS = 20


def _raio_do_config():
    """O raio que o ambiente usa de facto (`arena_radius_mapa_grande`).

    Estava aqui um default de 45 m em duro, de quando o mapa era rascunho; o
    config foi para 60 m e a pré-visualização passou a mostrar um mapa que não
    é o que se treina — sem nada no ecrã a dizê-lo. O default passa a ser lido.
    """
    import yaml
    with open(os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')) as f:
        cfg = yaml.safe_load(f)
    return float(cfg['environment'].get('arena_radius_mapa_grande', 45.0))


def _geometria(raio):
    """Geometria vinda do AMBIENTE REAL (`classic_scenario: mapa_grande`).

    Enquanto o mapa era rascunho, isto lia de `scripts/preview_mapa_grande.py`.
    Agora que está integrado, lê do simulador: o que se vê aqui é exatamente o
    que os robôs vão treinar — paredes, porta, ninho, spawn e obstáculos. Sem
    duas fontes, não há divergência possível.
    """
    import copy
    import yaml
    from src.environment.swarm_env_3d import SwarmForagingEnv3D

    with open(os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')) as f:
        cfg = yaml.safe_load(f)
    cfg = copy.deepcopy(cfg)
    cfg['environment']['classic_scenario'] = 'mapa_grande'
    cfg['environment']['arena_radius_mapa_grande'] = raio

    env = SwarmForagingEnv3D(config=cfg)
    np.random.seed(7)
    env.reset(seed=7)

    W = 5 * (2 * raio / np.sqrt(34))
    H = 3 * (2 * raio / np.sqrt(34))
    porta = ({'pos': env.door_pos, 'size': env.door_size}
             if env.door_active else None)
    return (env.walls, porta, env.nest_pos[:2], env.agent_positions,
            [o[:2] for o in env.obstacles], (W, H), env)


def main(args):
    raio = args.radius if args.radius is not None else _raio_do_config()
    altura = max(0.4, args.wall_height)
    walls, porta, ninho, posicoes, obs, (W, H), env = _geometria(raio)

    app = Ursina()
    window.title = f'Swarm 3D - MAPA GRANDE - r={raio:.0f} m'
    window.color = color.rgb(15, 18, 22)          # igual ao main_visualizer

    # Câmara livre — IGUAL à dos outros mapas. O EditorCamera é uma entidade-pivô:
    # orbita à volta da SUA posição e o zoom aproxima/afasta ao longo de camera.z.
    # Enquadra-se movendo o PIVÔ e definindo a distância; mexer em camera.position
    # ou camera.rotation à mão descoordena-o do seu estado interno e os controlos
    # ficam trocados (o zoom deixa de ampliar para onde se olha). Foi o que
    # aconteceu na 1ª versão — daí só se passarem parâmetros ao construtor.
    editor_cam = EditorCamera(rotation=(45, 0, 0))
    editor_cam.position = (0, 0, 0)               # orbita à volta do centro do mapa
    camera.z = -raio * 2.2                        # distância inicial: mapa todo à vista

    DirectionalLight(y=2, z=-3, shadows=True, rotation=(45, -45, 45))
    AmbientLight(color=color.rgba(120, 120, 120, 0.3))

    # Chão + arena circular — mesmas cores/ordem do main_visualizer.
    Entity(model='quad', scale=raio * 2.5, color=color.hsv(0, 0, 0.08),
           texture='white_cube', z=0.1)
    Entity(model='circle', scale=raio * 2, color=color.hsv(220, 0.2, 0.15), z=0.05)
    Entity(model='circle', scale=raio * 2, color=color.hsv(180, 0.8, 0.8),
           mode='line', z=0.0)

    # Paredes. No main_visualizer são achatadas (0.4) porque a câmara olha de
    # cima para a simulação; aqui a altura é ajustável para se julgar o volume
    # do labirinto — no ambiente elas são intransponíveis de qualquer maneira.
    # O painel da porta JÁ vem dentro de env.walls (índice door_wall_index) —
    # pinta-se de amarelo em vez de se desenhar uma segunda caixa por cima.
    idx_porta = env.door_wall_index
    for i, w in enumerate(walls):
        e_porta = (i == idx_porta)
        Entity(model='cube', texture='white_cube',
               color=color.hsv(45, 0.9, 1.0) if e_porta else color.hsv(215, 0.3, 0.6),
               scale=(float(w['size'][0]), float(w['size'][1]),
                      altura * (0.55 if e_porta else 1.0)),
               position=(float(w['pos'][0]), float(w['pos'][1]),
                         -altura * (0.275 if e_porta else 0.5)))

    # Ninho (esfera + halo), igual ao main_visualizer.
    Entity(model='sphere', color=color.hsv(130, 0.8, 0.9), scale=NEST_RADIUS * 2,
           position=(float(ninho[0]), float(ninho[1]), 0), unlit=True)
    Entity(model='circle', color=color.hsv(130, 0.8, 0.9, 0.3), scale=NEST_RADIUS * 4,
           position=(float(ninho[0]), float(ninho[1]), 0.01), unlit=True)

    # Obstáculos dispersos — as MESMAS esferas que o ambiente já simula
    # (num_obstacles/obstacle_radius), com a cor e a textura do main_visualizer.
    for p in obs:
        Entity(model='sphere', color=color.hsv(10, 0.8, 0.7),
               scale=OBSTACLE_RADIUS * 2, texture='noise',
               position=(float(p[0]), float(p[1]), -0.15))

    # Robôs parados no spawn, BEM SEPARADOS (o utilizador pediu-os espalhados;
    # e nascer empilhado faz a separação física do ambiente empurrá-los logo no
    # primeiro passo). Este Ursina (8.3.0) NÃO traz o modelo 'cylinder' — dá
    # "warning: missing model" e a entidade fica invisível; usa-se 'sphere', que
    # existe. O main_visualizer usava 'cylinder' e corria sem mostrar um único
    # robô; corrigido a 5 ago para 'sphere' também.
    # Posições REAIS do spawn do ambiente (env.agent_positions após reset), não
    # uma amostragem à parte: é onde os robôs vão mesmo nascer.
    if not args.sem_robos:
        for p in posicoes:
            Entity(model='sphere', color=color.hsv(210, 0.9, 0.9),
                   scale=ROBOT_RADIUS * 2,
                   position=(float(p[0]), float(p[1]), -0.15))

    Text(text=f'MAPA GRANDE  ·  arena r={raio:.0f} m  ·  '
              f'labirinto {W:.0f}x{H:.0f} m  ·  paredes {altura:.1f} m\n'
              f'5 zonas: S partida · A gargalo+U · B 4 salas · C porta coop. · D ninho'
              f'  ·  {len(obs)} obstaculos\n'
              f'{"sem robos" if args.sem_robos else f"{NUM_AGENTS} robos (raio real 0,15 m)"}'
              f'  ·  cena PARADA (geometria do ambiente real)',
         position=(-0.86, 0.47), scale=0.7, color=color.hsv(0, 0, 0.75))

    Text(text='BOTAO DIREITO arrasta = rodar  ·  RODA = zoom  ·  '
              'BOTAO DO MEIO arrasta = deslocar  ·  F = focar onde o rato aponta',
         position=(-0.86, -0.45), scale=0.65, color=color.hsv(0, 0, 0.55))

    print(f'[OK] mapa grande r={raio:.0f} | labirinto {W:.1f}x{H:.1f} | '
          f'{len(walls)} paredes | altura {altura:.1f} m')
    app.run()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--radius', type=float, default=None,
                    help='raio da arena (default: o do configs/foraging.yaml)')
    ap.add_argument('--wall-height', type=float, default=3.0)
    ap.add_argument('--sem-robos', action='store_true')
    main(ap.parse_args())
