"""
visualize_mapa_grande.py — MAPA GRANDE (rascunho) no visualizador Ursina
=======================================================================
MESMO visualizador dos outros mapas: Ursina, `EditorCamera()` (câmara livre),
as mesmas cores e a mesma convenção de eixos do `main_visualizer.py`. Um só
visualizador = um só sítio onde pode haver bugs.

Diferença face ao `main_visualizer.py`: aqui NÃO há modelo nem simulação — só a
geometria, parada, para se julgar tamanho e aspeto. Os robôs estão pousados no
spawn, o ninho está quieto e nada se mexe. É de propósito: o mapa ainda não
existe no simulador (a geometria vive em `scripts/preview_mapa_grande.py` até
ser aprovada), portanto não há nada para simular.

Quando o mapa for aprovado, isto deixa de ser preciso: a geometria passa a um
`_spawn_obstacles_mapa_grande()` no ambiente e o mapa abre-se pelo visualizador
normal, como qualquer outro cenário.

Uso:
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py --radius 60
    .venv/Scripts/python.exe visualization/visualize_mapa_grande.py --wall-height 8
"""
import argparse
import importlib.util
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


def _geometria(raio):
    """Importa a geometria do rascunho por caminho (scripts/ não é um pacote).
    A fonte das paredes é UMA só — não se duplicam aqui."""
    caminho = os.path.join(PROJECT_ROOT, 'scripts', 'preview_mapa_grande.py')
    spec = importlib.util.spec_from_file_location('preview_mapa_grande', caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    walls, porta, (W, H) = mod.build_walls(raio)
    spawn, ninho = mod.spawn_e_ninho(raio)
    obs = mod.obstaculos(raio, walls)
    return walls, porta, ninho, spawn, obs, (W, H)


def main(args):
    raio = args.radius
    altura = max(0.4, args.wall_height)
    walls, porta, ninho, spawn, obs, (W, H) = _geometria(raio)

    app = Ursina()
    window.title = f'Swarm 3D - MAPA GRANDE (rascunho) - r={raio:.0f} m'
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
    for w in walls:
        Entity(model='cube', color=color.hsv(215, 0.3, 0.6), texture='white_cube',
               scale=(float(w['size'][0]), float(w['size'][1]), altura),
               position=(float(w['pos'][0]), float(w['pos'][1]), -altura / 2))

    # Porta cooperativa: amarela, como fica no main_visualizer ao abrir.
    Entity(model='cube', color=color.hsv(45, 0.9, 1.0), texture='white_cube',
           scale=(float(porta['size'][0]), float(porta['size'][1]), altura * 0.55),
           position=(float(porta['pos'][0]), float(porta['pos'][1]), -altura * 0.275))

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
    # primeiro passo). O main_visualizer usa model='cylinder', mas este Ursina
    # (8.3.0) não traz esse modelo — dá "warning: missing model" e a entidade
    # fica invisível. Usa-se 'sphere', que existe.
    if not args.sem_robos:
        rng = np.random.default_rng(7)
        postos = []
        while len(postos) < NUM_AGENTS:
            p = spawn + rng.uniform(-0.075 * W, 0.075 * W, 2) * np.array([1.0, 1.6])
            if any(np.linalg.norm(p - q) < 1.6 for q in postos):
                continue
            if len(obs) and min(np.linalg.norm(obs - p, axis=1)) < 1.2:
                continue
            postos.append(p)
        for p in postos:
            Entity(model='sphere', color=color.hsv(210, 0.9, 0.9),
                   scale=ROBOT_RADIUS * 2,
                   position=(float(p[0]), float(p[1]), -0.15))

    Text(text=f'MAPA GRANDE (rascunho)  ·  arena r={raio:.0f} m  ·  '
              f'labirinto {W:.0f}x{H:.0f} m  ·  paredes {altura:.1f} m\n'
              f'5 zonas: S partida · A gargalo+U · B 4 salas · C porta coop. · D ninho'
              f'  ·  {len(obs)} obstaculos\n'
              f'{"sem robos" if args.sem_robos else f"{NUM_AGENTS} robos (raio real 0,15 m)"}'
              f'  ·  cena PARADA: so geometria, sem simulacao',
         position=(-0.86, 0.47), scale=0.7, color=color.hsv(0, 0, 0.75))

    Text(text='BOTAO DIREITO arrasta = rodar  ·  RODA = zoom  ·  '
              'BOTAO DO MEIO arrasta = deslocar  ·  F = focar onde o rato aponta',
         position=(-0.86, -0.45), scale=0.65, color=color.hsv(0, 0, 0.55))

    print(f'[OK] mapa grande r={raio:.0f} | labirinto {W:.1f}x{H:.1f} | '
          f'{len(walls)} paredes | altura {altura:.1f} m')
    app.run()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--radius', type=float, default=45.0)
    ap.add_argument('--wall-height', type=float, default=3.0)
    ap.add_argument('--sem-robos', action='store_true')
    main(ap.parse_args())
