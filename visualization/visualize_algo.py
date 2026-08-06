"""visualize_algo.py — o visualizador 3D ao vivo, um só, para os três algoritmos.

    python visualization/visualize_algo.py --algo gnn
    python visualization/visualize_algo.py --algo ppo --scenario u_wall
    python visualization/visualize_algo.py --algo sac --agents 50

Porque existe
-------------
Substitui `visualize_gnn.py`, `visualize_ppo.py` e `visualize_sac.py`: 632 linhas
em que o `ppo` e o `sac` diferiam em SEIS sítios (o nome do algoritmo, o título da
janela, a pasta do modelo, o prefixo do ficheiro, a classe que carrega e a linha
que imprime). Tudo o que varia cabe agora no dicionário `ALGOS`.

Não é arrumação: as três cópias já tinham divergido, e cada divergência foi um
defeito que existia numas e não noutras.

  · O `visualize_gnn.py` atualizava a posição das PAREDES a cada frame --- que é
    o que faz a porta cooperativa desaparecer do ecrã quando abre. O `ppo` e o
    `sac` não o faziam: nesses dois, a porta abria na simulação e continuava
    desenhada. Corrigido aqui para os três (é o `for i, wall in enumerate(...)`
    do `update`).
  · O `main_visualizer.py` desenhava os robôs a uma altura FIXA e usava um modelo
    (`cylinder`) que este Ursina não traz --- dois defeitos que estes três não
    tinham. Corrigidos a 5 ago, lá.

Mantém tudo o que os três tinham: a barra de velocidade, o teto de passos por
frame, a telemetria de proximidade que colore os robôs, a câmara de topo, o
`--scenario`/`--agents` em memória (sem escrever no `configs/foraging.yaml`) e o
`--models-root` para espreitar campanhas arquivadas.
"""
import argparse
import math
import os
import sys

import numpy as np
import torch
import yaml
from ursina import *

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import (SwarmForagingEnv3D, DOOR_SCENARIOS,  # noqa: E402
                                          DOOR_PUSHERS_REQUIRED)
from src.agents.gnn_agent_3d import GNNAgent3D  # noqa: E402
from src.scenarios import ALGO_COLORS, label as rotulo_cenario  # noqa: E402

# ── O que varia entre algoritmos, e só isto ──────────────────────────────────
# (título da janela, pasta dos modelos, prefixo do ficheiro, extensão)
ALGOS = {
    'gnn': ('GNN (Evolutivo)', 'models', 'gnn_3d_best', '.pth'),
    'ppo': ('PPO Baseline', 'models_ppo', 'ppo_3d_final', '.zip'),
    'sac': ('SAC (Soft Actor-Critic)', 'models_sac', 'sac_3d_final', '.zip'),
}


# ── Paleta ───────────────────────────────────────────────────────────────────
# A cor do robô é a MESMA que o algoritmo tem nas figuras da tese
# (`src/scenarios.ALGO_COLORS`): quem vir o ecrã ao lado de um gráfico reconhece
# o braço sem legenda. Os cinzentos vêm do tema do dashboard, pela mesma razão.
def _hex(s):
    s = s.lstrip('#')
    return color.rgb32(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ⚠️ Os tons têm de SEPARAR-SE, não só combinar. Na 1.ª versão o chão era
# rgb(18,23,28) e as paredes rgb(52,60,69) — perto demais: a parede só se via do
# lado que a luz apanhava, e na captura de teste UMA DAS DUAS do gargalo
# desaparecia consoante a direção da luz. Agora há três degraus claros entre
# fundo, chão e parede, e as arestas são bem mais claras do que ambos.
FUNDO      = color.rgb32(11, 14, 17)     # o mesmo #0b0e11 do dashboard
CHAO       = color.rgb32(31, 38, 46)     # um degrau claro acima do fundo
GRELHA     = color.rgb32(96, 112, 128)   # arestas e grelha: leem-se sempre
PAREDE     = color.rgb32(104, 118, 134)
PORTA      = color.rgb32(232, 163, 61)   # âmbar, como no viz3d do browser
NINHO      = color.rgb32(16, 185, 129)
OBSTACULO  = color.rgb32(124, 92, 58)
SINALIZA   = color.rgb32(250, 204, 21)
PERTO_MURO = color.rgb32(239, 68, 68)
PERTO_ROBO = color.rgb32(56, 189, 248)

# `parse_known_args`: o Ursina também lê o sys.argv e não queremos colidir.
_ap = argparse.ArgumentParser(add_help=False)
_ap.add_argument('--algo', choices=sorted(ALGOS), required=True)
_ap.add_argument('--scenario', type=str, default=None)
_ap.add_argument('--agents', type=int, default=None)
# Raiz dos modelos: por omissão a pasta ATIVA (results/), mas pode apontar para os
# modelos arquivados de uma campanha — results/graficos_tese/<sessão>/modelos —,
# que têm a mesma estrutura. Evita restaurar modelos por cima dos ativos só para
# espreitar um treino antigo.
_ap.add_argument('--models-root', type=str, default=None)
# ⚠️ Rastos e grafo: DESLIGADOS por omissão. Na captura de teste as linhas
# leem-se como uma teia de riscos emaranhados — com 20 agentes, ligar cada um aos
# vizinhos e às suas posições anteriores dá centenas de segmentos cruzados sobre
# a mesma área, e o que devia mostrar o padrão coletivo tapa a cena. Ficam
# disponíveis para quem quiser ver a topologia ou o caminho num momento
# específico, que é onde informam.
_ap.add_argument('--grafo', action='store_true',
                 help='desenha as ligações entre vizinhos (a topologia da GNN)')
_ap.add_argument('--rastos', action='store_true',
                 help='desenha o caminho recente de cada robô')
_ap.add_argument('--sombras', action='store_true',
                 help='liga as sombras projetadas (o shadow map desta escala '
                      'desenha borrões grandes; as de contacto ficam sempre)')
_ap.add_argument('--angulo', type=float, default=52.0,
                 help='inclinação inicial da câmara em graus '
                      '(90 = topo, 0 = ao nível do chão; por omissão 48)')
# Captura: corre N passos sem intervenção, grava um PNG e fecha. Serve para
# mostrar a cena a quem não a pode abrir, para pôr uma imagem num documento e
# para comparar duas versões do visualizador sem depender de memória visual.
_ap.add_argument('--recuo', type=float, default=2.8,
                 help='distância da câmara, em raios de arena')
_ap.add_argument('--chao', choices=('plano', 'disco'), default='plano',
                 help="'plano': chão contínuo que morre na névoa (omissão); "
                      "'disco': o disco recortado da versão anterior")
_ap.add_argument('--captura', type=str, default=None,
                 help='grava um PNG da cena e sai (ex.: --captura fig.png)')
_ap.add_argument('--passos-antes', type=int, default=140,
                 help='passos de simulação a correr antes da captura')
_args, _ = _ap.parse_known_args()

ALGO = _args.algo
TITULO, PASTA, PREFIXO, EXT = ALGOS[ALGO]
MODELS_ROOT = _args.models_root or os.path.join(PROJECT_ROOT, 'results')

config_path = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
# Cenário/dimensão por ARGUMENTO, com override em memória: mudar de cenário não
# reescreve o configs/foraging.yaml (era o que o launcher antigo fazia, e o config
# do repositório perdia-se).
if _args.scenario:
    config['environment']['classic_scenario'] = _args.scenario
if _args.agents:
    config['environment']['num_agents'] = _args.agents

app = Ursina()
window.title = f'Swarm 3D · {TITULO}'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
window.color = FUNDO
_camera_editor = EditorCamera()   # rato: orbitar, roda: zoom

# Iluminação a três pontos, como numa montagem de estúdio: uma luz principal que
# define a forma, uma de preenchimento que abre as sombras (senão o lado escuro
# fica preto e os robôs desaparecem contra o fundo) e uma rasante que separa os
# contornos do chão. Era uma direcional e um ambiente chapado.
_luz = DirectionalLight(y=3, z=-2, x=1, rotation=(50, -30, 0),
                        color=color.rgb32(255, 250, 240))   # principal, quente
# Sombras projetadas: é o que mais faz uma cena parecer 3D — sem elas, os
# objetos flutuam sobre o chão e a vista lê-se como um diagrama. Os três
# originais tinham-nas desligadas por custo (~140 entidades), mas só a luz
# PRINCIPAL as projeta e a caixa de sombra é limitada à arena, o que as torna
# baratas. Se alguma máquina sofrer, `--sem-sombras` desliga-as.
if _args.sombras:
    _luz.shadows = True
    try:
        _luz.shadow_map_resolution = Vec2(2048, 2048)
    except Exception:
        pass
DirectionalLight(y=2, z=3, x=-2, rotation=(30, 140, 0), shadows=False,
                 color=color.rgb32(120, 140, 170))          # preenchimento, fria
AmbientLight(color=color.rgba32(86, 94, 106, 255))

vis_config = config.get('visualization', {})
speed_slider = Slider(min=vis_config.get('speed_slider_min', 1),
                      max=vis_config.get('speed_slider_max', 120),
                      default=vis_config.get('speed_slider_default', 30),
                      text='Velocidade', dynamic=True)
speed_slider.position = (-0.85, 0.45)
speed_slider.scale = 1.2
time_accumulator = 0.0

env = SwarmForagingEnv3D(config=config)   # já com o override do --scenario
env.render_mode = None
obs_dict, _ = env.reset()


# ── O modelo, e a política que dele sai ──────────────────────────────────────
def _caminho_do_modelo():
    """Convenção de nomes: Sandbox ("none") sem sufixo, restantes com
    "_{scenario}". Recai no modelo sem sufixo se o do cenário ainda não foi
    treinado."""
    cen = config['environment'].get('classic_scenario', 'none')
    sufixo = f"_{cen}" if cen and cen != "none" else ""
    alvo = os.path.join(MODELS_ROOT, PASTA, f"{PREFIXO}{sufixo}")
    return alvo if os.path.exists(alvo + EXT) else \
        os.path.join(MODELS_ROOT, PASTA, PREFIXO)


def _carregar_politica():
    """Devolve `politica(obs_batch) -> act_batch`, um lote de cada vez.

    Em lote de propósito: cada agente é independente na sua observação, pelo que
    um forward sobre o lote dá o mesmo resultado que N forwards individuais e é
    cerca de dez vezes mais rápido — era a principal causa de lentidão do GNN.
    """
    base = _caminho_do_modelo()
    if not os.path.exists(base + EXT):
        print(f"[ERRO] {base}{EXT} não encontrado!")
        sys.exit(1)
    os.chmod(base + EXT, 0o666)

    if ALGO == 'gnn':
        agente = GNNAgent3D("tester", env.action_space("robot_0"), config_path)
        agente.load_state_dict(torch.load(base + EXT, weights_only=True))
        agente.eval()

        def politica(obs_batch):
            with torch.no_grad():
                return agente(torch.tensor(obs_batch)).numpy()
    else:
        from stable_baselines3 import PPO, SAC
        modelo = (PPO if ALGO == 'ppo' else SAC).load(base, device='cpu')

        def politica(obs_batch):
            act, _ = modelo.predict(obs_batch, deterministic=True)
            return act

    print(f"[OK] Modelo {ALGO.upper()} 3D carregado: {base}{EXT}")
    return politica


politica = _carregar_politica()

# Vista inicial ISOMÉTRICA, não de topo. Os três originais usavam 89° — vista de
# topo, que achata tudo e faz o 3D parecer um mapa 2D. Só era necessária porque
# as paredes eram desenhadas com os seus 30 m reais; com a altura visual acima, a
# câmara pode inclinar e a cena ganha profundidade. `--angulo` ajusta.
#
# O campo de visão também importa: com a câmara muito recuada a projeção fica
# quase ortográfica (linhas paralelas, sem fuga) e o resultado volta a parecer um
# diagrama. Aproxima-se a câmara e alarga-se o fov, o que dá perspetiva visível
# sem cortar a arena.
_camera_editor.rotation_x = _args.angulo
# ⚠️ O plano do MAPA (x,y do simulador) é vertical no espaço do Ursina, porque
# a cena é desenhada 1:1 com o mundo. Consequência: `rotation_x=90` dá a vista de
# topo do mapa (era o 89 dos originais) e baixar o ângulo inclina. Ao inclinar, o
# centro da arena sobe no ecrã e sobra uma faixa preta em baixo — desloca-se o
# pivô ao longo de Y (norte-sul do mapa) para recentrar.
_desvio = env.arena_radius * 0.42 * max(0.0, (90.0 - _args.angulo) / 90.0)
_camera_editor.position = (0, _desvio, 0)
camera.fov = 50
camera.z = -(env.arena_radius * _args.recuo)
_camera_editor.target_z = camera.z   # o EditorCamera faz lerp para target_z

# ── Chão ─────────────────────────────────────────────────────────────────────
# O disco recortado no preto lia-se como uma panqueca a flutuar no vazio: um
# objeto, e não um sítio. E os anéis concêntricos da grelha métrica agravavam-no,
# porque desenhavam um alvo — o olho ia para o centro geométrico da arena, que
# não é onde a ação está.
#
# Passa a haver CHÃO CONTÍNUO, que se estende muito para lá da arena e morre na
# névoa (a mesma que já esbate as paredes distantes). Não tem bordo visível, por
# isso não pode ler-se como um objeto. A fronteira real da arena — que existe e
# importa — fica marcada por um anel de luz no chão e outro à altura de 2,5 m: o
# recinto lê-se como recinto, sem uma superfície a competir com os robôs.
R = env.arena_radius
CHAO_EXT = R * 3.4          # onde o plano acaba já a névoa o dissolveu


def _linhas(v, thickness=1):
    """Um `Mesh` de SEGMENTOS soltos a partir de uma lista de pares de vértices.

    ⚠️ `Mesh(vertices=v, mode='line')` sozinho desenha uma linha CONTÍNUA: liga
    também o fim de cada segmento ao início do seguinte. Era isso que enchia a
    cena de riscos diagonais — a grelha do chão e as arestas das paredes vinham
    atravessadas por diagonais que ninguém tinha desenhado. Os pares têm de ir
    explicitamente em `triangles`.
    """
    return Mesh(vertices=v, triangles=[(i, i + 1) for i in range(0, len(v), 2)],
                mode='line', thickness=thickness)


def _anel(raio, z, cor, alpha=1.0, thickness=1, lados=96):
    """Um círculo DE LINHA, no plano do mapa.

    ⚠️ Era `Entity(model='circle', mode='line')` — e essa combinação NÃO faz
    wireframe nenhum: o `mode` só é lido quando se constrói um `Mesh`; com um
    modelo pedido pelo nome, o Ursina carrega o disco CHEIO e ignora-o. Os
    "anéis" da grelha métrica eram portanto discos opacos empilhados a alturas
    diferentes — é isso que dava o efeito de donut/panqueca que se via na cena,
    e que nenhuma mudança de cor ia resolver, porque o problema era geometria.
    """
    v = []
    for k in range(lados):
        a0 = 2 * math.pi * k / lados
        a1 = 2 * math.pi * (k + 1) / lados
        v += [Vec3(math.cos(a0) * raio, math.sin(a0) * raio, z),
              Vec3(math.cos(a1) * raio, math.sin(a1) * raio, z)]
    return Entity(model=_linhas(v, thickness), color=cor, alpha=alpha,
                  unlit=True)


def _esfera_arame(raio, cor, alpha=0.16, meridianos=8, paralelos=5, lados=72):
    """O VOLUME da arena, em arame: paralelos + meridianos.

    ⚠️ Sem isto a cena mente por omissão. A arena não é um recinto plano: é uma
    ESFERA de raio `arena_radius`, e o eixo z dos agentes é livre dentro dela
    (`move_local[2]`; só o `mapa_grande` tem teto). Com um chão desenhado e nada
    por cima, a vista lê-se como um tabuleiro de 2D — que é precisamente a
    geometria que o `_altura_paredes` teve de corrigir em 29 jul, quando os
    robôs passavam POR CIMA das paredes de 30 m e ninguém via porquê.
    """
    v = []
    for k in range(1, paralelos + 1):          # paralelos: círculos em z
        z = raio * (2.0 * k / (paralelos + 1) - 1.0)
        r = math.sqrt(max(0.0, raio * raio - z * z))
        for s in range(lados):
            a0, a1 = 2 * math.pi * s / lados, 2 * math.pi * (s + 1) / lados
            v += [Vec3(math.cos(a0) * r, math.sin(a0) * r, z),
                  Vec3(math.cos(a1) * r, math.sin(a1) * r, z)]
    for m in range(meridianos):                # meridianos: círculos verticais
        th = math.pi * m / meridianos
        cx, cy = math.cos(th), math.sin(th)
        for s in range(lados):
            a0, a1 = 2 * math.pi * s / lados, 2 * math.pi * (s + 1) / lados
            v += [Vec3(cx * math.cos(a0) * raio, cy * math.cos(a0) * raio,
                       math.sin(a0) * raio),
                  Vec3(cx * math.cos(a1) * raio, cy * math.cos(a1) * raio,
                       math.sin(a1) * raio)]
    return Entity(model=_linhas(v), color=cor, alpha=alpha, unlit=True)


def _arestas_caixa(escala):
    """As 12 arestas de um paralelepípedo centrado na origem, como segmentos."""
    sx, sy, sz = (e / 2.0 for e in escala)
    c = [Vec3(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    pares = [(0, 1), (2, 3), (4, 5), (6, 7),      # verticais (em z)
             (0, 2), (1, 3), (4, 6), (5, 7),      # em y
             (0, 4), (1, 5), (2, 6), (3, 7)]      # em x
    v = []
    for a, b in pares:
        v += [c[a], c[b]]
    return v


if _args.chao == 'plano':
    Entity(model='quad', scale=CHAO_EXT * 2, color=CHAO, unlit=True,
           position=(0, 0, 0.08))
    # Grelha quadrada de 5 m: dá escala sem apontar para o centro. Uma só malha
    # (não uma entidade por linha) — são ~90 segmentos.
    # A grelha acaba ANTES do plano (2,2 R contra 3,4 R): levada até ao fim, as
    # linhas mais distantes chegavam ao ecrã quase rasantes e emaranhavam-se num
    # feixe no canto. O chão continua para lá dela e morre na névoa.
    _v, _passo, _lim = [], 5, int(R * 1.3 // 5) * 5
    for _k in range(-_lim, _lim + 1, _passo):
        _v += [Vec3(_k, -_lim, 0.07), Vec3(_k, _lim, 0.07),
               Vec3(-_lim, _k, 0.07), Vec3(_lim, _k, 0.07)]
    Entity(model=_linhas(_v), color=GRELHA, alpha=0.22, unlit=True)
    # A fronteira ao nível do plano de referência, bem visível…
    _anel(R, 0.04, GRELHA, alpha=0.75, thickness=3)
    # … e a ESFERA inteira em arame, que é o espaço onde os robôs se podem mexer.
    _esfera_arame(R, GRELHA, alpha=0.20)
else:                       # 'disco': a versão anterior, para comparar
    Entity(model='circle', scale=R * 2, color=CHAO, position=(0, 0, 0.06))
    _anel(R, 0.04, GRELHA, alpha=0.55, thickness=2)
    for _raio in range(5, int(R) + 1, 5):
        _anel(_raio, 0.03, GRELHA, alpha=0.25)

# ── Ninho: disco marcado no chão, não uma bola ───────────────────────────────
# Era uma esfera de raio×2 mais um halo de raio×4 — no ecrã, uma bola verde que
# competia com o enxame inteiro. O ninho é uma ZONA (raio 1,5 m), não um objeto:
# lê-se melhor como alvo desenhado no chão, com uma cúpula baixa que lhe dá
# presença sem o transformar no protagonista.
nest_halo = Entity(model='circle', color=NINHO, alpha=0.18, unlit=True,
                   scale=env.nest_radius * 2.6, position=tuple(env.nest_pos))
# Sombra do ninho no plano de referência: quando ele nasce a 8 m de altura, é o
# que diz DE ONDE ele está pendurado. Sem isto, o alvo da tarefa aparecia a
# flutuar sem sítio no mapa.
nest_shadow = Entity(model='circle', color=color.black, alpha=0.14, unlit=True,
                     scale=env.nest_radius * 1.6,
                     position=(env.nest_pos[0], env.nest_pos[1], 0.02))
nest_ring = _anel(env.nest_radius, 0.0, NINHO, thickness=3)
nest_ring.position = (env.nest_pos[0], env.nest_pos[1], 0.01)
nest_view = Entity(model='sphere', color=NINHO, unlit=True, alpha=0.85,
                   scale=(env.nest_radius * 1.1, env.nest_radius * 1.1,
                          env.nest_radius * 0.5),
                   position=tuple(env.nest_pos))

obs_views = [Entity(model='sphere', color=OBSTACULO, texture='noise',
                    scale=env.obstacle_radius * 2, position=tuple(p))
             for p in env.obstacles]
# Sombra de contacto dos obstáculos, pela mesma razão dos robôs — e aqui é mais
# do que estética: a arena é uma ESFERA, os obstáculos ocupam-na em altura, e sem
# a marca no chão os que estão a 10 m de altura projetam-se para fora do anel da
# arena e parecem pedras a flutuar no vazio, ou um erro de geometria.
obs_shadows = [Entity(model='circle', color=color.black, alpha=0.22, unlit=True,
                      scale=env.obstacle_radius * 1.8,
                      position=(p[0], p[1], 0.02))
               for p in env.obstacles]


def _e_porta(i):
    return (getattr(env, 'classic_scenario', '') in DOOR_SCENARIOS
            and getattr(env, 'door_wall_index', None) == i)


# ── Paredes: opacas, com aresta, e à ALTURA CERTA para se ver ────────────────
# ⚠️ Aqui estava a razão de a cena parecer 2D. As paredes têm 2×raio de altura
# (30 m numa arena de raio 15) — é isso que as torna estanques desde 29 jul, mas
# desenhadas a essa escala transformam o mapa num poço: inclinar a câmara mostra
# muros de 30 m e mais nada. A saída dos três visualizadores originais era pôr a
# câmara a 89°, ou seja, uma vista de topo — 3D a fingir.
#
# Desenham-se a `ALTURA_VISUAL` (um sexto do raio, mínimo 2 m), o que permite
# inclinar a câmara e ver volume de facto. O HUD diz sempre a altura REAL, para
# o ecrã não afirmar uma geometria que não é a do simulador — a mesma solução do
# `viz3d.js` do dashboard e do `main_visualizer.py`.
ALTURA_VISUAL = max(3.5, R / 4.0)
ALTURA_REAL = float(env.walls[0]['size'][2]) if len(env.walls) else 0.0

wall_views, wall_edges, wall_altas = [], [], []
for i, w in enumerate(env.walls):
    cor = PORTA if _e_porta(i) else PAREDE
    escala = (float(w['size'][0]), float(w['size'][1]), ALTURA_VISUAL)
    pos = (float(w['pos'][0]), float(w['pos'][1]), -ALTURA_VISUAL / 2)
    wall_views.append(Entity(model='cube', color=cor, texture='white_cube',
                             scale=escala, position=pos))
    # ⚠️ Mesma armadilha do `circle`: `model='cube', mode='line'` desenhava um
    # CUBO CHEIO cinzento por cima da parede — era ele que a deixava chapada,
    # sem sombreamento nem volume, e a esconder a cor âmbar da porta. As doze
    # arestas têm de ser construídas à mão.
    wall_edges.append(Entity(model=_linhas(_arestas_caixa(escala), 2),
                             color=GRELHA, alpha=0.55, unlit=True,
                             position=pos))
    # A parede REAL vai até `ALTURA_REAL` (2× o raio da arena). Desenhá-la sólida
    # faz da cena um poço; não a desenhar de todo faz a cena parecer 2D — foi
    # esta a queixa. Fica em arame: vê-se até onde veda, e vê-se através.
    wall_altas.append(Entity(
        model=_linhas(_arestas_caixa((escala[0], escala[1], ALTURA_REAL))),
        color=cor, alpha=0.22, unlit=True,
        position=(pos[0], pos[1], 0.0)))

# ── Névoa: profundidade atmosférica ──────────────────────────────────────────
# O que está longe esbate-se na cor do fundo. É o truque mais antigo do desenho
# de paisagem e o mais eficaz: sem ele, uma parede a 5 m e outra a 40 m têm
# exatamente o mesmo tom, e o cérebro lê a cena como um plano.
try:
    from panda3d.core import Fog as _Fog
    _nevoa = _Fog('atmosfera')
    _nevoa.setColor(11 / 255, 14 / 255, 17 / 255)      # a cor do fundo
    _nevoa.setLinearRange(R * 1.2, R * 4.2)
    scene.setFog(_nevoa)
except Exception:
    pass          # sem névoa continua a funcionar; é só menos bonito


# ── Robôs: corpo + cúpula, na cor do algoritmo ───────────────────────────────
# Eram cubos laranja iguais para os três algoritmos. Passam a ter o corpo na cor
# que o algoritmo tem nas figuras da tese, uma cúpula clara que dá volume e um
# visor que continua a mostrar a direção.
def _aviva(c, f=1.75):
    """Clareia mantendo a matiz. A paleta da tese foi escolhida para papel
    branco; no ecrã escuro, o verde #2E7D32 do GNN desaparece contra o cinzento
    do chão. Sobe-se o brilho e conserva-se a cor — é ela que liga o ecrã às
    figuras."""
    return color.rgb32(min(255, int(c.r * 255 * f)),
                       min(255, int(c.g * 255 * f)),
                       min(255, int(c.b * 255 * f)))


COR_ALGO = _aviva(_hex(ALGO_COLORS[ALGO.upper()]))

# ⚠️ Escala VISUAL dos robôs. Ao tamanho físico (raio 0,15 m numa arena de raio
# 15) um robô ocupa um centésimo do diâmetro da arena: na captura de teste eram
# pontinhos que não se distinguiam do fundo. Desenham-se 3,5× maiores — é a
# convenção de qualquer visualização de enxame, e o HUD diz o raio real. O que
# NÃO se exagera é a posição: essa é a do simulador, ao milímetro.
ESCALA_ROBO = 3.0
_r = env.robot_radius * ESCALA_ROBO
CORPO = (_r * 2, _r * 2, _r * 1.35)

robot_views, robot_shadows = [], []
for r_pos in env.agent_positions:
    robot = Entity(model='sphere', color=COR_ALGO, position=tuple(r_pos),
                   scale=CORPO)
    Entity(parent=robot, model='sphere', color=color.white, alpha=0.45,
           scale=(0.6, 0.6, 0.6), position=(0, 0, -0.36), unlit=True)
    Entity(parent=robot, model='cube', color=color.white,
           scale=(0.66, 0.24, 0.32), position=(0, 0, 0.5))  # visor: direção
    robot_views.append(robot)
    # Sombra de contacto: um disco escuro colado ao chão, por baixo de cada robô.
    # É o que o "assenta" na superfície — sem ela, mesmo com sombras projetadas,
    # os robôs parecem flutuar a poucos centímetros do plano.
    robot_shadows.append(Entity(model='circle', color=color.black, alpha=0.16,
                                scale=_r * 1.15, unlit=True,
                                position=(r_pos[0], r_pos[1], 0.015)))

# ── O GRAFO: as ligações que a política vê ───────────────────────────────────
# A tese é sobre uma rede de grafo com ATENÇÃO SOBRE OS VIZINHOS — e esse grafo,
# que existe a cada passo, nunca era desenhado. Mostrá-lo faz duas coisas ao
# mesmo tempo: dá à cena a malha que a torna visualmente interessante, e mostra
# a arquitetura a funcionar (a topologia densifica-se quando o enxame se junta
# no gargalo e rarefaz-se quando se dispersa).
#
# Desenha-se em UM só `Mesh` de linhas, reconstruído por frame: 20 agentes dão
# até 190 pares, e criar uma entidade por aresta seria insustentável.
RAIO_VIZINHO = 4.0          # metros; a mesma ordem do alcance de interação
grafo = (Entity(model=Mesh(vertices=[], mode='line', thickness=1),
                color=COR_ALGO, alpha=0.18, unlit=True)
         if _args.grafo else None)


MAX_ARESTAS = 600           # acima disto a malha vira borrão e deixa de informar


def _atualizar_grafo():
    """Pares a menos de RAIO_VIZINHO, em NumPy.

    O duplo ciclo em Python custava 11,5 ms por frame a N=100 (o número de pares
    cresce com N²) — mais do que todo o resto do desenho junto. A matriz de
    distâncias resolve o mesmo em NumPy; é a técnica que o projeto já aplicou ao
    LiDAR e às observações, pela mesma razão.
    """
    if grafo is None:
        return
    p = env.agent_positions
    if len(p) < 2:
        return
    xy = p[:, :2]
    d = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=-1)
    i, j = np.triu_indices(len(p), k=1)
    perto = d[i, j] < RAIO_VIZINHO
    i, j = i[perto], j[perto]
    if len(i) > MAX_ARESTAS:          # fica com as mais curtas: a estrutura local
        ordem = np.argsort(d[i, j])[:MAX_ARESTAS]
        i, j = i[ordem], j[ordem]
    v = [Vec3(*x) for par in zip(p[i], p[j]) for x in par]
    grafo.model.vertices = v
    # ⚠️ Sem os pares em `triangles`, o Mesh liga o fim de cada aresta ao início
    # da seguinte: o que aparecia não era o grafo dos vizinhos, mas um caminho a
    # atravessar a arena de lado a lado. Era esse o "emaranhado" que levou a
    # desligar o grafo por omissão — o desenho é que estava errado, não a ideia.
    grafo.model.triangles = [(k, k + 1) for k in range(0, len(v), 2)]
    grafo.model.generate()


# ── Rastos: o padrão coletivo, que é o que interessa num enxame ──────────────
# Um enxame não se lê pela pose instantânea, mas pelo caminho que desenha: o
# funil à entrada do gargalo, o beco onde alguns ficam presos, a fila que se
# forma na porta. Guarda-se uma janela curta das posições e desenha-se como
# linhas esbatidas — de novo num só Mesh, por causa do custo.
PASSOS_RASTO = 26
historico = []
rastos = (Entity(model=Mesh(vertices=[], mode='line', thickness=1),
                 color=COR_ALGO, alpha=0.28, unlit=True)
          if _args.rastos else None)


# ── HUD ──────────────────────────────────────────────────────────────────────
# Nenhum dos três visualizadores dizia o que estava no ecrã: nem o algoritmo,
# nem o cenário, nem quantas recolhas iam feitas. Com três janelas abertas lado
# a lado — que é como se comparam — não havia forma de saber qual era qual.
_cen = config['environment'].get('classic_scenario', 'none')
Text(text=f"{TITULO}  ·  {rotulo_cenario(_cen)}  ·  N={env.num_agents}",
     position=(-0.86, 0.47), scale=0.85, color=color.rgb32(245, 245, 245))
Text(text=f"arena r={R:.0f} m  ·  grelha 5 m  ·  {len(env.walls)} paredes  ·  "
          f"{len(env.obstacles)} obstáculos  ·  paredes desenhadas a "
          f"{ALTURA_VISUAL:.1f} m (vedam até {ALTURA_REAL:.0f} m)",
     position=(-0.86, 0.43), scale=0.62, color=color.rgb32(125, 125, 125))
hud_estado = Text(text="", position=(-0.86, -0.44), scale=0.7,
                  color=color.rgb32(163, 163, 163))
Text(text="BOTÃO DIREITO = rodar   ·   RODA = zoom   ·   BOTÃO DO MEIO = deslocar",
     position=(-0.86, -0.47), scale=0.58, color=color.rgb32(110, 110, 110))


def wall_min_dist(pos, walls, arena_radius):
    """Distância do robô à parede mais próxima, ou à borda da arena."""
    min_d = arena_radius - float(np.linalg.norm(pos[:2]))
    for wall in walls:
        half = wall['size'][:2] / 2.0
        delta = np.abs(pos[:2] - wall['pos'][:2]) - half
        min_d = min(min_d, float(np.linalg.norm(np.maximum(delta, 0.0))))
    return min_d


def robot_min_dist(pos, all_positions, idx):
    """Distância ao vizinho mais próximo."""
    return min((float(np.linalg.norm(pos[:2] - o[:2]))
                for j, o in enumerate(all_positions) if j != idx), default=999.0)


# Teto de passos de simulação por frame. Permite que a barra de velocidade
# ultrapasse o limite de FPS: com 1 passo por frame ficava-se em ~60 passos/s
# mesmo com a barra a 120, e era essa a causa do "está lento".
MAX_STEPS_PER_FRAME = 20


def _atualizar_cena():
    """Põe o desenho a par do estado do ambiente.

    Separada do `update()` porque a captura (`--captura`) precisa exatamente do
    mesmo trabalho sem o ciclo de eventos do Ursina — e duas cópias divergiriam,
    que é o defeito que juntar os três visualizadores veio corrigir.
    """
    porta = ""
    if getattr(env, 'has_door', False):
        porta = ("   ·   porta ABERTA" if not env.door_active
                 else f"   ·   porta fechada (precisa de {DOOR_PUSHERS_REQUIRED})")
    hud_estado.text = (f"passo {env.steps}/{env.max_steps}"
                       f"   ·   recolhas {int(env.total_food_collected)}{porta}")

    nest_view.position = tuple(env.nest_pos)
    nest_halo.position = tuple(env.nest_pos)
    nest_shadow.position = (env.nest_pos[0], env.nest_pos[1], 0.02)
    # ⚠️ O anel também: no Sandbox o ninho MUDA de sítio a cada recolha
    # (`_spawn_nest`), e o anel ficava para trás — no ecrã apareciam dois ninhos,
    # o verdadeiro e um anel verde vazio onde ele tinha estado.
    # ⚠️ O ninho tem TRÊS coordenadas — no Sandbox nasce dentro da esfera, e
    # pode estar a 8 m de altura. O anel colado ao plano z=0 deixava-o a apontar
    # para um sítio onde não estava; agora acompanha-o, e a marca no chão fica
    # por conta da sombra.
    nest_ring.position = tuple(env.nest_pos)

    for i, obs_pos in enumerate(env.obstacles):
        obs_views[i].position = tuple(obs_pos)
        obs_shadows[i].position = (obs_pos[0], obs_pos[1], 0.02)

    # ⚠️ As PAREDES têm de ser atualizadas: quando a porta cooperativa abre, o
    # ambiente REMOVE-A de `env.walls`, e é este ciclo que a faz desaparecer do
    # ecrã. O `visualize_gnn.py` fazia-o; o `visualize_ppo.py` e o
    # `visualize_sac.py` NÃO — nesses dois, a porta abria na simulação e ficava
    # desenhada. É a divergência que motivou juntar os três.
    for i, wall in enumerate(env.walls):
        if i < len(wall_views):
            # ⚠️ O z tem de continuar a ser o VISUAL (-ALTURA_VISUAL/2, que
            # assenta a caixa no chão). Copiar `wall['pos']` inteiro punha-a
            # centrada em z=0 a partir do primeiro passo — metade enterrada, e
            # a mudar de sítio entre o arranque e o resto da simulação.
            wall_views[i].position = (float(wall['pos'][0]),
                                      float(wall['pos'][1]),
                                      -ALTURA_VISUAL / 2)
            wall_edges[i].position = wall_views[i].position
            wall_altas[i].position = (float(wall['pos'][0]),
                                      float(wall['pos'][1]), 0.0)
    for i in range(len(env.walls), len(wall_views)):
        wall_views[i].enabled = False        # porta aberta: sai do ecrã
        wall_edges[i].enabled = False

    # Grafo e rastos — opcionais, cada um num só Mesh reconstruído por frame.
    _atualizar_grafo()
    if rastos is not None:
        historico.append(env.agent_positions.copy())
        if len(historico) > PASSOS_RASTO:
            historico.pop(0)
        if len(historico) > 1:
            v = []
            for k in range(1, len(historico)):
                for a, b in zip(historico[k - 1], historico[k]):
                    v.extend([Vec3(*a), Vec3(*b)])
            rastos.model.vertices = v
            rastos.model.triangles = [(k, k + 1) for k in range(0, len(v), 2)]
            rastos.model.generate()

    normal = CORPO
    for i, r_pos in enumerate(env.agent_positions):
        robot_views[i].position = tuple(r_pos)
        robot_views[i].look_at(robot_views[i].position
                               + Vec3(*env.agent_headings[i]))
        robot_shadows[i].position = (r_pos[0], r_pos[1], 0.015)

        # A telemetria de proximidade fica só para o SINAL e para o contacto
        # com paredes. Na captura de teste, o enxame agrupado no gargalo
        # ficava TODO ciano ("perto de outro robô") — e a cor do algoritmo,
        # que é o que liga o ecrã às figuras da tese, desaparecia.
        w_dist = wall_min_dist(r_pos, env.walls, env.arena_radius)
        if env.signaling[i] == 1.0:
            robot_views[i].color = SINALIZA          # a sinalizar
            robot_views[i].scale = tuple(x * 1.7 for x in normal)
        else:
            robot_views[i].scale = normal
            robot_views[i].color = (PERTO_MURO if w_dist < 0.45
                                    else COR_ALGO)


def update():
    global obs_dict, time_accumulator

    time_accumulator += time.dt
    target_delay = 1.0 / speed_slider.value

    stepped = False
    n_steps = 0
    while time_accumulator >= target_delay and n_steps < MAX_STEPS_PER_FRAME:
        time_accumulator -= target_delay
        n_steps += 1
        stepped = True

        agent_ids = list(env.agents)
        obs_batch = np.stack([np.asarray(obs_dict[a], dtype=np.float32)
                              for a in agent_ids])
        act_batch = politica(obs_batch)
        obs_dict, _, terms, _, _ = env.step(
            {aid: act_batch[k] for k, aid in enumerate(agent_ids)})

        if any(terms.values()):
            obs_dict, _ = env.reset()
            break

    if stepped:
        _atualizar_cena()


def _capturar_e_sair():
    """Avança a simulação, grava um PNG e fecha.

    Corre os passos ANTES de gravar para a cena ter história: com o enxame ainda
    no spawn não há rastos nem topologia para ver, que é precisamente o que a
    imagem deve mostrar. O `renderFrame` explícito é preciso porque o Panda3D só
    desenha quando lhe pedem, e aqui não há ciclo de eventos a correr.
    """
    from panda3d.core import Filename

    alvo = os.path.abspath(_args.captura)
    os.makedirs(os.path.dirname(alvo) or '.', exist_ok=True)
    for _ in range(_args.passos_antes):
        agent_ids = list(env.agents)
        obs = np.stack([np.asarray(obs_dict[a], dtype=np.float32)
                        for a in agent_ids])
        act = politica(obs)
        globals()['obs_dict'], _, terms, _, _ = env.step(
            {aid: act[k] for k, aid in enumerate(agent_ids)})
        _atualizar_cena()
        if any(terms.values()):
            break
    for _ in range(3):                     # deixa o render assentar
        base.graphicsEngine.renderFrame()
    base.win.saveScreenshot(Filename.fromOsSpecific(alvo))
    print(f"[OK] captura: {alvo}")
    application.quit()


if _args.captura:
    _capturar_e_sair()
else:
    app.run()
