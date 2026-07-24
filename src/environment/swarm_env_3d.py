import gymnasium as gym
from gymnasium import spaces
import numpy as np
import yaml
import os
import heapq

from src.scenarios import MAZE_SCENARIOS

# ── Porta cooperativa (cenários cooperative_door / cooperative_door_bypass) ──
# A "porta" é um painel (parede normal para física/LiDAR) que fecha a abertura
# de 3 m no centro da barreira em y=0. Abre-se quando DOOR_PUSHERS_REQUIRED
# agentes ativos ocupam em simultâneo a push zone (faixa imediatamente a sul da
# abertura) — nesse momento o painel é removido e cada agente que empurrou
# recebe DOOR_OPEN_REWARD. No campo geodésico a porta é sempre PASSÁVEL, para o
# gradiente de progresso apontar para a push zone (o objetivo do cenário).
DOOR_SCENARIOS = ("cooperative_door", "cooperative_door_bypass", "mapa_grande")
DOOR_POS = (0.0, 0.0, 0.0)          # centro da abertura na barreira
DOOR_SIZE = (3.0, 2.0, 30.0)        # painel: largura 3 m (= abertura) × espessura 2 m
DOOR_PUSH_HALF_WIDTH = 1.5          # push zone: |x| < 1.5 (largura da porta)
DOOR_PUSH_Y_MIN, DOOR_PUSH_Y_MAX = -2.0, 0.0   # faixa a sul da barreira
DOOR_PUSH_CENTER = (0.0, -1.0, 0.0)  # centro da push zone (isenção de spreading)
DOOR_PUSHERS_REQUIRED = 3           # agentes em simultâneo para abrir
DOOR_OPEN_REWARD = 100.0            # bónus por agente que participou na abertura


class SwarmForagingEnv3D(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, config_path=None, config=None):
        super(SwarmForagingEnv3D, self).__init__()

        if config is not None:
            self.config = config
        else:
            if config_path is None:
                config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)

        env_config = self.config['environment']
        self.num_agents = env_config.get('num_agents', 25)
        self.num_obstacles = env_config.get('num_obstacles', 50)
        self.dynamic_obstacles = env_config.get('dynamic_obstacles', True)
        self.arena_radius = env_config.get('arena_radius', 15.0)
        self.dynamic_nest = env_config.get('dynamic_nest', True)
        self.nest_velocity_magnitude = env_config.get('nest_velocity', 0.015)
        self.nest_velocity = np.zeros(3)

        self.nest_radius = env_config.get('nest_radius', 0.2)
        self.max_steps = env_config.get('max_steps', 500)

        self.robot_radius = self.config['physics'].get('agent_radius', 0.15)
        # Penalização de colisão física inter-agente (sobreposição real). Ensina
        # os agentes a NÃO chocarem entre si, complementando a separação física
        # (que apenas os empurra). Proporcional à penetração.
        self.collision_penalty = self.config['physics'].get('collision_penalty', -1.0)
        self.obstacle_radius = env_config.get('obstacle_radius', 0.2)
        self.obstacle_velocity_magnitude = env_config.get('obstacle_velocity', 0.02)
        self.obstacle_velocities = []

        # Valor BASE (cenários cooperativos). Nos labirintos de navegação o reset
        # força required_to_eat=1 (ver _scenario_required_to_eat).
        self.required_to_eat_coop = env_config.get('required_to_eat', 3)
        self.required_to_eat = self.required_to_eat_coop
        self.lidar_range = env_config.get('lidar_range', 5.0)
        self.hunger_timer_max = env_config.get('hunger_timer_max', 600)
        self.progress_reward_factor = env_config.get('progress_reward_factor', 50.0)
        self.obstacle_penalty = env_config.get('obstacle_penalty', -2.0)
        self.spreading_penalty_factor = env_config.get('spreading_penalty_factor', 1.5)
        self.min_spread_distance = env_config.get('min_spread_distance', 1.0)
        self.exploration_bonus = env_config.get('exploration_bonus', 2.0)
        self.exploration_cell_size = env_config.get('exploration_cell_size', 2.0)
        self.max_steps_override = {}
        if 'max_steps_cooperative_door' in env_config:
            self.max_steps_override['cooperative_door'] = env_config['max_steps_cooperative_door']
        if 'max_steps_cooperative_door_bypass' in env_config:
            self.max_steps_override['cooperative_door_bypass'] = env_config['max_steps_cooperative_door_bypass']
        if 'max_steps_mapa_grande' in env_config:
            self.max_steps_override['mapa_grande'] = env_config['max_steps_mapa_grande']

        # O mapa_grande precisa de uma arena maior (r=60 vs 15). É um override
        # POR CENÁRIO e não uma mudança do arena_radius global — mexer no global
        # alteraria os 7 cenários das campanhas fechadas (spawn, normalização das
        # observações, grelha geodésica), invalidando resultados já na tese.
        self.arena_radius_base = self.arena_radius
        self.arena_radius_mapa_grande = env_config.get(
            'arena_radius_mapa_grande', self.MAPA_GRANDE_RADIUS)

        # Raio usado para NORMALIZAR as distâncias da observação (ninho, porta,
        # vizinhos). Por omissão é o próprio raio da arena — o comportamento de
        # sempre, bit-exacto nos 7 cenários. Pode ser fixado no config para
        # desfazer um confundente do zero-shot de topologia: como o mapa_grande
        # corre a r=60 e os 7 cenários a r=15, o MESMO modelo vê as distâncias
        # comprimidas 4x (÷120 em vez de ÷30). Sem controlo, "o campeão do Quatro
        # Salas faz 0 recolhas" confunde topologia nova com escala nova.
        self.obs_norm_radius_cfg = env_config.get('obs_norm_radius', None)
        self.obs_norm_radius = self.arena_radius

        # ── Campo geodésico (BFS/Dijkstra) para o progress reward ────────────
        # Em cenários com paredes, a distância euclidiana ao ninho cria mínimos
        # locais: contornar uma parede AFASTA do ninho (progress negativo) → os
        # agentes colam-se à parede mais próxima do ninho e nunca a contornam.
        # A distância geodésica (caminho real que contorna as paredes) elimina
        # esse mínimo: o gradiente passa a apontar SEMPRE para o desvio correto.
        self.geo_res = env_config.get('geodesic_cell_size', 0.4)
        self.geo_field = None
        self.geo_n = 0
        self.use_geodesic = False
        self._geo_cache = {}   # campo é constante por cenário (paredes+ninho fixos)

        # Rrobust (resiliência): fração de agentes que "falha" a meio do episódio.
        # 0.0 = desligado (treino normal); 0.1 = 10% dos agentes ficam inertes
        # a partir de metade do episódio. Avalia a degradação face à falha de agentes.
        self.agent_failure_fraction = env_config.get('agent_failure_fraction', 0.0)

        rewards_config = self.config.get('rewards', {})
        self.energy_cost = rewards_config.get('energy_cost', -0.05)
        self.food_collected_reward = rewards_config.get('food_collected', 100.0)

        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        # Ego-features = 16: bússola ninho (4) + LiDAR (8) + bússola porta/entrada (4).
        # Os 4 da porta (B1) só são preenchidos em cenários com porta definida
        # (cooperative_door); zeros nos restantes.
        self.ego_feats_dim = 16
        obs_size = self.ego_feats_dim + (self.num_agents - 1) * 5
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.nest_pos = np.array([0.0, 0.0, 0.0])
        self.obstacles = []
        self.walls = []
        self.prev_dist_to_nest = np.zeros(self.num_agents)
        self.signaling = np.zeros(self.num_agents)
        self.agent_headings = np.zeros((self.num_agents, 3))

        # Estado da porta cooperativa — definido para TODOS os cenários (False/None
        # fora dos DOOR_SCENARIOS), para nunca depender de getattr defensivo.
        self.has_door = False          # o cenário atual tem porta?
        self.door_active = False       # a porta está fechada (painel presente)?
        self.door_wall_index = None    # índice do painel em self.walls (se fechada)
        self.door_pos = np.zeros(3, dtype=np.float32)
        self.door_size = np.array(DOOR_SIZE)
        # Push zone POR INSTÂNCIA (x_min, x_max, y_min, y_max) + o seu centro.
        # Era fixa nas constantes DOOR_PUSH_*, o que assumia a barreira horizontal
        # em (0,0) dos cenários cooperativos. O mapa grande tem a porta numa parede
        # VERTICAL e noutro sítio, logo a zona tem de acompanhar a porta. Os valores
        # por omissão são exatamente os das constantes — os 7 cenários não mudam.
        self.door_push_bounds = (-DOOR_PUSH_HALF_WIDTH, DOOR_PUSH_HALF_WIDTH,
                                 DOOR_PUSH_Y_MIN, DOOR_PUSH_Y_MAX)
        self.door_push_center = np.array(DOOR_PUSH_CENTER, dtype=np.float64)

    def _get_scenario_spawn_pos(self):
        max_attempts = 50
        for _ in range(max_attempts):
            if self.classic_scenario == "u_wall":
                # Spawn SOUTH of the U legs (legs start at y=-5).
                # Agents approach from below, enter the bowl, hit the top bar, must find bypass.
                pos = np.array([np.random.uniform(-10, 10), np.random.uniform(-12, -6), 0.0])
            elif self.classic_scenario == "bottleneck":
                # South of the horizontal barrier (barrier covers y -1 to 1)
                pos = np.array([np.random.uniform(-10, 10), np.random.uniform(-12, -2), 0.0])
            elif self.classic_scenario == "four_rooms":
                # Spawn ESPALHADO pelas 3 salas opostas ao ninho (que está no
                # quadrante NE). Antes os 20 agentes nasciam todos na sala SW, o
                # que causava congestionamento e bloqueio nas passagens estreitas
                # de 1.5m — a maioria ficava presa a empurrar-se na sala de origem.
                # Distribuir por SW/NW/SE reduz a densidade por sala e por passagem,
                # mantendo os agentes longe do ninho (navegação de longo termo).
                # Limites a |coord|<=10 para ficar dentro da arena circular (r=15).
                sala = np.random.randint(3)
                if sala == 0:      # SW (a mais distante do ninho)
                    pos = np.array([np.random.uniform(-10, -2), np.random.uniform(-10, -2), 0.0])
                elif sala == 1:    # NW
                    pos = np.array([np.random.uniform(-10, -2), np.random.uniform(2, 10), 0.0])
                else:              # SE
                    pos = np.array([np.random.uniform(2, 10), np.random.uniform(-10, -2), 0.0])
            elif self.classic_scenario == "mapa_grande":
                # Espalhados pela sala de partida (zona S, oeste). Nascem
                # separados de propósito: amontoados, a separação física
                # empurrava-os logo no primeiro passo. A caixa vem de
                # _mapa_grande_spawn_box (a MESMA que define a clareira sem
                # obstáculos) — ver lá porquê.
                c, hx, hy = self._mapa_grande_spawn_box()
                pos = np.array([np.random.uniform(c[0] - hx, c[0] + hx),
                                np.random.uniform(c[1] - hy, c[1] + hy), 0.0])
            elif self.classic_scenario in DOOR_SCENARIOS:
                # South of the horizontal barrier (barrier covers y -1 to 1)
                pos = np.array([np.random.uniform(-10, 10), np.random.uniform(-12, -2), 0.0])
            else:
                pos = self._random_spawn()

            colisao = False
            for wall in self.walls:
                half_size = wall['size'] / 2.0
                delta = pos - wall['pos']
                if np.all(np.abs(delta) < (half_size + self.robot_radius + 0.1)):
                    colisao = True
                    break
            if not colisao:
                return pos
        pos = self._random_spawn()
        return pos

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Reprodutibilidade: o ambiente usa np.random global (spawns, obstáculos,
        # falhas). Quando recebe uma seed explícita, fixa-a — essencial para
        # avaliação emparelhada (mesmos episódios para todos os algoritmos) e
        # para runs de treino reproduzíveis. seed=None mantém a cadeia aleatória.
        if seed is not None:
            np.random.seed(seed)
        self.steps = 0
        self.deaths_count = 0
        self.total_food_collected = 0
        self.total_collisions = 0
        self.current_nest_occupancy = 0
        self.signaling = np.zeros(self.num_agents)
        self.walls = []

        self.classic_scenario = self.config['environment'].get('classic_scenario', 'none')

        # Arena por cenário: o mapa_grande corre a r=60, todos os outros ficam
        # com o raio do config (15). Ver arena_radius_mapa_grande no __init__.
        self.arena_radius = (self.arena_radius_mapa_grande
                             if self.classic_scenario == "mapa_grande"
                             else self.arena_radius_base)
        # Ver obs_norm_radius_cfg no __init__. Sem override no config isto é
        # exatamente o raio da arena => observações inalteradas em todo o lado.
        self.obs_norm_radius = self.obs_norm_radius_cfg or self.arena_radius

        # Porta cooperativa: estado limpo a cada episódio (o spawn do cenário
        # volta a fechá-la via _add_cooperative_door).
        self.has_door = self.classic_scenario in DOOR_SCENARIOS
        self.door_active = False
        self.door_wall_index = None

        # required_to_eat por cenário: navegação pura = 1 agente basta (a tarefa é
        # chegar ao ninho); cooperação (porta/perceção) = valor do config (3).
        # mapa_grande entra aqui: a cooperação que ele mede está na PORTA (zona C).
        # Exigir também 3 agentes simultâneos no ninho (raio 1,5 m) ao fim de
        # ~143 m de labirinto empilharia uma segunda tarefa cooperativa por cima
        # da navegação, e a métrica deixaria de isolar o que o mapa existe para
        # medir. A recolha é, portanto, individual — como nos cenários de
        # navegação pura.
        _nav_scenarios = ("u_wall", "bottleneck", "four_rooms", "mapa_grande")
        self.required_to_eat = 1 if self.classic_scenario in _nav_scenarios else self.required_to_eat_coop

        base_max_steps = self.config['environment'].get('max_steps', 500)
        self.max_steps = self.max_steps_override.get(self.classic_scenario, base_max_steps)

        if self.classic_scenario == "u_wall":
            self.nest_pos = np.array([0.0, 10.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_u_wall()

        elif self.classic_scenario == "bottleneck":
            self.nest_pos = np.array([0.0, 10.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_bottleneck()

        elif self.classic_scenario == "four_rooms":
            self.nest_pos = np.array([10.0, 10.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_maze()

        elif self.classic_scenario == "cooperative_door":
            # Nest is north of the horizontal barrier (barrier at y=0, nest at y=12)
            self.nest_pos = np.array([0.0, 12.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_cooperative_door()

        elif self.classic_scenario == "cooperative_door_bypass":
            # 7º cenário (sugestão do Prof. Nunes): igual à porta cooperativa, mas
            # existe um percurso ALTERNATIVO mais longo, SEM porta. Testa se a
            # aprendizagem descobre a cooperação (caminho curto pela porta, exige 3
            # agentes) mesmo havendo uma saída sub-ótima que não obriga a cooperar.
            self.nest_pos = np.array([0.0, 12.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_cooperative_door_bypass()

        elif self.classic_scenario == "mapa_grande":
            # Labirinto composto (5 zonas). Ninho na câmara D, a este; os agentes
            # nascem na sala de partida S, a oeste — o percurso mais longo do
            # projeto (~143 m contra 34 m do Quatro Salas).
            W, H, x0, x1, y0, y1 = self._mapa_grande_dims()
            self.nest_pos = np.array([x1 - 0.05 * W, 0.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos()
                                             for _ in range(self.num_agents)])
            self._spawn_obstacles_mapa_grande()

        elif self.classic_scenario == "cooperative_perception":
            # O "ninho" é o Alvo Móvel neste cenário
            self.nest_pos = self._random_spawn(max_radius=0.7)
            vel = np.random.uniform(-1, 1, 3)
            self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self.obstacles = []
            self.obstacle_velocities = []

        else:
            self._spawn_nest()
            self._spawn_obstacles()
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])

        # Cenários com paredes e ninho estático usam o campo geodésico no progress
        # reward (elimina o mínimo local). Os restantes (sandbox, perceção
        # cooperativa) têm ninho móvel e sem paredes → euclidiano basta.
        # Lista vinda de src/scenarios.py (MAZE_SCENARIOS) em vez de escrita à
        # mão: estava duplicada aqui e o mapa_grande, ao ser acrescentado, ficou
        # SEM campo geodésico — os agentes cair-se-iam no mínimo local que o
        # geodésico existe para eliminar, num mapa de 143 m de percurso.
        self.use_geodesic = self.classic_scenario in MAZE_SCENARIOS
        if self.use_geodesic:
            self._build_geodesic_field()

        self.prev_dist_to_nest = np.array([np.linalg.norm(p - self.nest_pos) for p in self.agent_positions])
        self.prev_pot = np.array([self._potential(p) for p in self.agent_positions])
        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        # Grelha de células visitadas por agente (reward de exploração count-based)
        self.visited_cells = [set() for _ in range(self.num_agents)]

        # Rrobust: nenhum agente falhou ainda no início do episódio.
        self.failed = np.zeros(self.num_agents, dtype=bool)
        self._failure_injected = False

        self.agent_headings = np.zeros((self.num_agents, 3))
        for i in range(self.num_agents):
            self.agent_headings[i] = np.array([1.0, 0.0, 0.0])

        return self._get_observations(), {}

    def _spawn_nest(self):
        # Nest within 30% of arena_radius (~4.5m) for easier discoverability
        self.nest_pos = self._random_spawn(max_radius=0.3)
        if self.dynamic_nest:
            vel = np.random.uniform(-1, 1, 3)
            self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude

    def _spawn_obstacles(self):
        self.obstacles = []
        self.obstacle_velocities = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                # Uniform spread across arena (was 50-80% ring — too restrictive)
                pos = self._random_spawn(min_radius=0.05, max_radius=0.90)
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.5):
                    self.obstacles.append(pos)
                    vel = np.random.uniform(-1, 1, 3)
                    vel /= (np.linalg.norm(vel) + 1e-6)
                    self.obstacle_velocities.append(vel * self.obstacle_velocity_magnitude)
                    valid = True

    def _spawn_obstacles_u_wall(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # Classic U-wall trap: opening faces SOUTH (toward agents).
        # Agents approach from y=-12, walk north into the open bowl, hit the top bar at y=3,
        # and must discover the detour around the legs at |x| > 8 (7m of free space per side).
        # Top bar : x -7 to +7, y 3 to 5
        # Left leg: x -8 to -6, y -5 to 5  (leg bottom at y=-5, leaving open entry from south)
        # Right leg: x 6 to 8,  y -5 to 5
        # Bypass space at |x| > 8 is ≈7m wide — discoverable but not trivial.
        self.walls = [
            {'pos': np.array([0.0,  4.0, 0.0]), 'size': np.array([14.0, 2.0, 30.0])},  # top bar
            {'pos': np.array([-7.0, 0.0, 0.0]), 'size': np.array([2.0, 10.0, 30.0])},  # left leg
            {'pos': np.array([ 7.0, 0.0, 0.0]), 'size': np.array([2.0, 10.0, 30.0])},  # right leg
        ]

    def _spawn_obstacles_bottleneck(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # PORTAS ALARGADAS: Passagem central de 1.5 metros de largura.
        # Barreira horizontal (y=0, espessura 8m) com uma ABERTURA central.
        # Antes: paredes de 40m (saíam 25m fora da arena r=15) e abertura de 1.5m
        # (20 agentes congestionavam). Agora: largura ajustada à arena e abertura
        # alargada para 2.5m (22 jun, a pedido — reduz o congestionamento).
        # Esq tapa x[-16,-1.25]; dir tapa x[1.25,16]; abertura = x[-1.25,1.25].
        self.walls = [
            {'pos': np.array([-8.625, 0.0, 0.0]), 'size': np.array([14.75, 8.0, 30.0])},
            {'pos': np.array([ 8.625, 0.0, 0.0]), 'size': np.array([14.75, 8.0, 30.0])}
        ]

    def _spawn_obstacles_maze(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # Cruz com 4 quadrantes. Espessura das paredes 1.5m. As passagens entre
        # salas foram ALARGADAS de 1.5m → 2.5m (22 jun, a pedido): cada segmento
        # adjacente a uma abertura foi encurtado 0.5m no lado da abertura, mantendo
        # a estrutura. Aberturas resultantes (2.5m): no eixo horizontal em x≈±9.4;
        # no eixo vertical em y≈±9.4 e no cruzamento central (y≈0).
        self.walls = [
            # Eixo Horizontal Y=0  (aberturas em x[-10.675,-8.175] e x[8.175,10.675])
            {'pos': np.array([-12.8375, 0.0, 0.0]), 'size': np.array([4.325, 1.5, 30.0])},
            {'pos': np.array([0.0, 0.0, 0.0]), 'size': np.array([16.35, 1.5, 30.0])},
            {'pos': np.array([12.8375, 0.0, 0.0]), 'size': np.array([4.325, 1.5, 30.0])},

            # Eixo Vertical X=0  (aberturas exteriores em y≈±9.4 alargadas para 2.5m).
            # Os 2 segmentos centrais SÓ encurtam no lado exterior — o lado interior
            # encosta à barra horizontal central (não criar frestas no cruzamento).
            {'pos': np.array([0.0, -12.8375, 0.0]), 'size': np.array([1.5, 4.325, 30.0])},
            {'pos': np.array([0.0, -4.4625, 0.0]), 'size': np.array([1.5, 7.425, 30.0])},
            {'pos': np.array([0.0, 4.4625, 0.0]), 'size': np.array([1.5, 7.425, 30.0])},
            {'pos': np.array([0.0, 12.8375, 0.0]), 'size': np.array([1.5, 4.325, 30.0])}
        ]

    # ------------------------------------------------------------------
    # MAPA GRANDE (mapa_grande) — labirinto composto, arena r=60
    # ------------------------------------------------------------------
    # Junta num só mapa as dificuldades já validadas nos 7 cenários, a uma escala
    # ~4x maior (pior percurso 143 m vs 34 m do Quatro Salas). Cinco zonas de
    # oeste para este: S sala de partida (aberta, com obstáculos) · A gargalo +
    # beco em U · B quatro salas · C porta cooperativa + alternativa longa ·
    # D câmara do ninho. Geometria desenhada e aprovada em planta 2D/3D antes de
    # entrar aqui (scripts/preview_mapa_grande.py, visualize_mapa_grande.py).
    #
    # A proporção é 5:3 inscrita no círculo (W=5k, H=3k, W²+H²=(2R)² → k=2R/√34).
    # As aberturas de zonas contíguas estão DESLOCADAS umas das outras de
    # propósito: alinhadas, anulavam-se e o mapa ficava intransponível (bug
    # apanhado na planta 2D antes de existir código).
    MAPA_GRANDE_RADIUS = 60.0

    def _mapa_grande_dims(self):
        """(W, H, x0, x1, y0, y1) do retângulo útil, a partir do raio da arena."""
        k = 2 * self.arena_radius / np.sqrt(34)
        W, H = 5 * k, 3 * k
        return W, H, -W / 2, W / 2, -H / 2, H / 2

    def _mapa_grande_spawn_box(self):
        """(centro, meia-largura, meia-altura) da caixa de spawn na zona S.

        FONTE ÚNICA: o spawn dos agentes e a clareira sem obstáculos derivam
        daqui. Estavam escritos com as mesmas constantes em dois sítios e a
        clareira era um CÍRCULO menor que a diagonal da caixa — os cantos
        ficavam de fora e ~0,2% dos agentes nasciam dentro de um obstáculo
        (penalização e empurrão no passo 0, sem qualquer erro visível).
        """
        W, H, x0, _, _, _ = self._mapa_grande_dims()
        return np.array([x0 + 0.10 * W, 0.0]), 0.075 * W, 0.12 * H

    def _spawn_obstacles_mapa_grande(self):
        """Paredes das 5 zonas + obstáculos dispersos (com clareira no spawn)."""
        t = 1.5      # espessura (a mesma do four_rooms)
        ab = 2.5     # abertura das passagens (a mesma, alargada em 22 jun)
        W, H, x0, x1, y0, y1 = self._mapa_grande_dims()

        def parede(cx, cy, sx, sy):
            return {'pos': np.array([cx, cy, 0.0]),
                    'size': np.array([sx, sy, 30.0])}

        self.walls = [
            parede(0, y1, W, t), parede(0, y0, W, t),      # fronteira N/S
            parede(x0, 0, t, H), parede(x1, 0, t, H),      # fronteira O/E
        ]

        # --- ZONA S: sala de partida (aberta) → saída ampla, 2x abertura -----
        xs = x0 + 0.20 * W
        s_baixo = -ab - y0
        s_cima = y1 - ab
        self.walls += [parede(xs, y0 + s_baixo / 2, t, s_baixo),
                       parede(xs, y1 - s_cima / 2, t, s_cima)]

        # --- ZONA A: gargalo (abertura a sul) + beco em U --------------------
        xa = x0 + 0.42 * W
        y_g = -H / 4
        b_baixo = (y_g - ab / 2) - y0
        b_cima = y1 - (y_g + ab / 2)
        self.walls += [parede(xa, y0 + b_baixo / 2, t, b_baixo),
                       parede(xa, y1 - b_cima / 2, t, b_cima)]
        ux, uy = x0 + 0.315 * W, H * 0.14
        uw, uh = 0.085 * W, 0.30 * H
        self.walls += [parede(ux - uw / 2, uy, t, uh),
                       parede(ux, uy + uh / 2, uw, t),
                       parede(ux, uy - uh / 2, uw, t)]

        # --- ZONA B: quatro salas (cruz; abertura vertical a norte) ----------
        xb = x0 + 0.63 * W
        y_pb = H / 4
        c_baixo = (y_pb - ab / 2) - y0
        c_cima = y1 - (y_pb + ab / 2)
        self.walls += [parede(xb, y0 + c_baixo / 2, t, c_baixo),
                       parede(xb, y1 - c_cima / 2, t, c_cima)]
        segh = ((xb - xa) - ab) / 2
        self.walls += [parede(xa + segh / 2, 0.0, segh, t),
                       parede(xb - segh / 2, 0.0, segh, t)]

        # --- ZONA C: porta cooperativa + alternativa longa a norte -----------
        xc = x0 + 0.82 * W
        porta_h, alt_h = 3.0, 4.0
        b1 = (-porta_h / 2) - y0
        self.walls.append(parede(xc, y0 + b1 / 2, t, b1))
        b2 = (y1 - alt_h) - (porta_h / 2)
        self.walls.append(parede(xc, porta_h / 2 + b2 / 2, t, b2))
        self.walls.append(parede(xc + 0.07 * W, y1 - alt_h - t, 0.14 * W, t))

        # A porta é VERTICAL e está em (xc, 0) — não a barreira horizontal em
        # (0,0) dos cenários cooperativos. Por isso a push zone é redefinida:
        # faixa imediatamente a OESTE da porta (o lado por onde o enxame chega).
        self.door_pos = np.array([xc, 0.0, 0.0], dtype=np.float32)
        self.door_size = np.array([2.0, porta_h, 30.0])
        self.door_push_bounds = (xc - 2.0, xc - 0.1, -porta_h / 2, porta_h / 2)
        self.door_push_center = np.array([xc - 1.0, 0.0, 0.0])

        # --- Obstáculos dispersos (esferas com colisão, como nos outros) -----
        self.obstacles = []
        self.obstacle_velocities = []
        n = int(60 * (self.arena_radius / 45.0) ** 2)
        folga = ab / 2 + self.obstacle_radius
        spawn_c, hx, hy = self._mapa_grande_spawn_box()
        # A clareira tem de cobrir a caixa de spawn INTEIRA (cantos incluídos)
        # mais o contacto robô-obstáculo — ver _mapa_grande_spawn_box.
        raio_clareira = np.hypot(hx, hy) + self.robot_radius + self.obstacle_radius
        # Disco livre à volta do ninho: a mesma regra do _spawn_obstacles
        # genérico, que aqui faltava. Sem ela, ~24% dos episódios tinham um
        # obstáculo dentro da zona de recolha (raio 1,5 m) — um estorvo à
        # entrega sorteado por episódio, ou seja, ruído entre runs que a
        # avaliação emparelhada não consegue cancelar.
        folga_ninho = self.nest_radius + self.obstacle_radius + 0.5
        tentativas = 0
        while len(self.obstacles) < n and tentativas < n * 400:
            tentativas += 1
            if np.random.rand() < 0.40:      # 40% na sala de partida
                p = np.array([np.random.uniform(x0 + 1.5, xs - 1.5),
                              np.random.uniform(y0 + 1.5, y1 - 1.5), 0.0])
            else:                            # 60% pelo resto do labirinto
                p = np.array([np.random.uniform(xs + 1.5, x1 - 1.5),
                              np.random.uniform(y0 + 1.5, y1 - 1.5), 0.0])
            if np.linalg.norm(p[:2]) > self.arena_radius - 1.0:
                continue
            if np.linalg.norm(p[:2] - spawn_c) < raio_clareira:
                continue
            if np.linalg.norm(p - self.nest_pos) < folga_ninho:
                continue
            # Nunca dentro de paredes NEM encostado: um obstáculo a menos de
            # meia-abertura podia selar um corredor de 2,5 m.
            if any(np.all(np.abs(p - w['pos']) < w['size'] / 2 + folga)
                   for w in self.walls):
                continue
            if any(np.linalg.norm(p - q) < 1.2 for q in self.obstacles):
                continue
            self.obstacles.append(p)
            self.obstacle_velocities.append(np.zeros(3))  # estáticos

        self._add_cooperative_door()

    def _add_cooperative_door(self):
        """Fecha a abertura da barreira com o painel da porta cooperativa.

        Enquanto fechada, a porta é uma parede normal (física + LiDAR). Abre em
        _update_door quando DOOR_PUSHERS_REQUIRED agentes ocupam a push zone.
        """
        self.door_active = True
        # O mapa_grande define door_pos/door_size (porta VERTICAL, noutro sítio)
        # no seu próprio _spawn_obstacles_*; os cenários cooperativos usam as
        # constantes de sempre — a barreira horizontal em (0,0).
        if self.classic_scenario != "mapa_grande":
            self.door_pos = np.array(DOOR_POS, dtype=np.float32)
            self.door_size = np.array(DOOR_SIZE)
        self.door_wall_index = len(self.walls)
        self.walls.append({'pos': self.door_pos.copy(), 'size': self.door_size})

    def _spawn_obstacles_cooperative_door(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # Redesigned as HORIZONTAL (east-west) barrier at y=0.
        # Previous design was a vertical wall (N-S) that could be bypassed at y≈±14
        # (arena boundary left a gap). A horizontal wall spanning x=-15 to x=15
        # truly blocks all south-to-north passage — the ends are at the arena boundary.
        # Door: 3m gap at x=0 center. Push zone: directly south of the door (y -2 to 0).
        self.walls = [
            {'pos': np.array([-8.25, 0.0, 0.0]), 'size': np.array([13.5, 2.0, 30.0])},  # x -15 to -1.5
            {'pos': np.array([ 8.25, 0.0, 0.0]), 'size': np.array([13.5, 2.0, 30.0])},  # x  1.5 to  15
        ]
        self._add_cooperative_door()

    def _spawn_obstacles_cooperative_door_bypass(self):
        # 7º cenário: porta cooperativa COM percurso alternativo longo (sem porta).
        # Geometria (arena r=15; ninho em (0,12); agentes nascem a sul, y<0):
        #  • Barreira horizontal em y=0 com PORTA de 3m no centro (caminho CURTO,
        #    exige 3 agentes a empurrar — idêntico à porta cooperativa).
        #  • O segmento DIREITO é mais curto (acaba em x=11) → deixa uma abertura
        #    livre de 4m em x∈[11,15]: o percurso ALTERNATIVO, que não tem porta.
        #  • Uma parede DEFLETORA em y=8 (x∈[5,15]) obriga quem usa a abertura a
        #    desviar-se para x<5 antes de subir ao ninho → o bypass é ~2x mais longo
        #    que a porta. Assim cooperar (porta) tem MAIOR fitness do que o bypass.
        self.obstacles = []
        self.obstacle_velocities = []
        self.walls = [
            {'pos': np.array([-8.25, 0.0, 0.0]), 'size': np.array([13.5, 2.0, 30.0])},  # esq: x -15 a -1.5
            {'pos': np.array([ 6.25, 0.0, 0.0]), 'size': np.array([ 9.5, 2.0, 30.0])},  # dir: x  1.5 a  11
            {'pos': np.array([10.0,  8.0, 0.0]), 'size': np.array([10.0, 2.0, 30.0])},  # defletor: x 5 a 15 @ y=8
        ]
        self._add_cooperative_door()

    def _update_door(self, rewards):
        """Abre a porta quando DOOR_PUSHERS_REQUIRED agentes ativos ocupam a push
        zone (faixa imediatamente a sul da abertura). Abrir = REMOVER o painel de
        self.walls: deixa de existir para a física e para o LiDAR. Cada agente que
        empurrou recebe DOOR_OPEN_REWARD. Agentes falhados (Rrobust) não contam."""
        pushers = []
        for i in range(self.num_agents):
            if self.failed[i]:
                continue
            pos = self.agent_positions[i]
            x_min, x_max, y_min, y_max = self.door_push_bounds
            if x_min < pos[0] < x_max and y_min < pos[1] < y_max:
                pushers.append(i)

        if len(pushers) < DOOR_PUSHERS_REQUIRED:
            return
        self.door_active = False
        self.walls.pop(self.door_wall_index)
        self.door_wall_index = None
        for idx in pushers:
            rewards[self.agents[idx]] += DOOR_OPEN_REWARD

    def _random_spawn(self, min_radius=0.0, max_radius=0.8):
        u = np.random.uniform(0, 1)
        v = np.random.uniform(0, 1)
        theta = 2 * np.pi * u
        phi = np.arccos(2 * v - 1)
        r = self.arena_radius * np.cbrt(np.random.uniform(min_radius ** 3, max_radius ** 3))
        x = r * np.sin(phi) * np.cos(theta)
        y = r * np.sin(phi) * np.sin(theta)
        z = r * np.cos(phi)
        return np.array([x, y, z])

    def _to_cell(self, pos):
        """Converte uma posição do mundo (x, y) no índice (i, j) da grelha geodésica."""
        R = self.arena_radius
        i = int((pos[0] + R) / self.geo_res)
        j = int((pos[1] + R) / self.geo_res)
        return i, j

    def _build_geodesic_field(self):
        """Calcula o campo de distância geodésica ao ninho (Dijkstra 8-conexo numa
        grelha), contornando as paredes. O resultado (em metros) é cacheado por
        cenário — as paredes e o ninho são fixos nos cenários de labirinto."""
        if self.classic_scenario in self._geo_cache:
            self.geo_field, self.geo_n = self._geo_cache[self.classic_scenario]
            return

        res = self.geo_res
        R = self.arena_radius
        n = int(2 * R / res) + 1
        dist = np.full((n, n), np.inf, dtype=np.float64)
        blocked = np.zeros((n, n), dtype=bool)

        # Inflar as paredes pelo raio do robô → o caminho geodésico é fisicamente
        # percorrível (não corta cantos nem passa por frestas mais estreitas que o robô).
        inflate = self.robot_radius
        for w_i, wall in enumerate(self.walls):
            # A porta cooperativa é tratada como PASSÁVEL no BFS: assim o gradiente
            # aponta para a porta (= push zone), que é o objetivo do cenário.
            if self.door_wall_index is not None and w_i == self.door_wall_index:
                continue
            half = wall['size'] / 2.0
            i0 = max(0, int((wall['pos'][0] - half[0] - inflate + R) / res))
            i1 = min(n - 1, int((wall['pos'][0] + half[0] + inflate + R) / res))
            j0 = max(0, int((wall['pos'][1] - half[1] - inflate + R) / res))
            j1 = min(n - 1, int((wall['pos'][1] + half[1] + inflate + R) / res))
            blocked[i0:i1 + 1, j0:j1 + 1] = True

        ni, nj = self._to_cell(self.nest_pos)
        ni = min(max(ni, 0), n - 1)
        nj = min(max(nj, 0), n - 1)
        blocked[ni, nj] = False  # o ninho tem de ser alcançável

        diag = res * np.sqrt(2.0)
        neigh = ((1, 0, res), (-1, 0, res), (0, 1, res), (0, -1, res),
                 (1, 1, diag), (1, -1, diag), (-1, 1, diag), (-1, -1, diag))
        dist[ni, nj] = 0.0
        heap = [(0.0, ni, nj)]
        while heap:
            d, i, j = heapq.heappop(heap)
            if d > dist[i, j]:
                continue
            for di, dj, cost in neigh:
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n and not blocked[ii, jj]:
                    nd = d + cost
                    if nd < dist[ii, jj]:
                        dist[ii, jj] = nd
                        heapq.heappush(heap, (nd, ii, jj))

        self.geo_field = dist
        self.geo_n = n
        self._geo_cache[self.classic_scenario] = (dist, n)

    def _potential(self, pos):
        """Potencial de navegação Φ(pos): distância (geodésica nos labirintos,
        euclidiana caso contrário) ao ninho. O progress reward é Φ(prev)−Φ(atual)."""
        if not self.use_geodesic or self.geo_field is None:
            return float(np.linalg.norm(pos - self.nest_pos))
        i, j = self._to_cell(pos)
        if 0 <= i < self.geo_n and 0 <= j < self.geo_n:
            d = self.geo_field[i, j]
            if np.isfinite(d):
                return float(d)
        # Célula bloqueada/inalcançável (ex.: dentro da margem de uma parede):
        # euclidiana + penalização grande → gradiente para sair da parede.
        return float(np.linalg.norm(pos - self.nest_pos) + 2.0 * self.arena_radius)

    def _has_line_of_sight(self, p1, p2):
        for t in np.linspace(0.1, 0.9, 10):
            point = p1 + t * (p2 - p1)
            for wall in self.walls:
                half_size = wall['size'] / 2.0
                if np.all(np.abs(point - wall['pos']) < half_size):
                    return False
        return True

    def _lidar_scan(self, pos, heading, w_min_arr, w_max_arr, obs_arr):
        """LiDAR de 8 raios, vetorizado (slab method). Bit-exacto vs. o loop original
        (ver tests/test_lidar_equivalence.py). pos/heading: (3,); w_min_arr/w_max_arr:
        (W,3) cantos das AABB; obs_arr: (O,3) centros dos obstáculos."""
        num_rays = 8
        max_d = self.lidar_range
        r_obs = self.obstacle_radius

        # Heading projetado no plano horizontal (robusto a pitch), igual ao original.
        F_horiz = np.array([heading[0], heading[1], 0.0])
        n = np.linalg.norm(F_horiz)
        F_horiz = np.array([1.0, 0.0, 0.0]) if n < 1e-6 else F_horiz / n
        R_horiz = np.array([-F_horiz[1], F_horiz[0], 0.0])

        angles = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)
        ray_dirs = (np.cos(angles)[:, None] * F_horiz[None, :]
                    + np.sin(angles)[:, None] * R_horiz[None, :])  # (R,3), z=0

        closest = np.full(num_rays, max_d, dtype=np.float64)

        # ---- Paredes (AABB, slab method em X e Y) ----
        if w_min_arr.shape[0] > 0:
            d = ray_dirs[:, :2] * max_d                       # (R,2)
            parallel = np.abs(d) < 1e-6
            d_safe = np.where(parallel, 1.0, d)
            pos2 = pos[:2]
            wmin2 = w_min_arr[:, :2]
            wmax2 = w_max_arr[:, :2]
            t_a = (wmin2[None, :, :] - pos2[None, None, :]) / d_safe[:, None, :]
            t_b = (wmax2[None, :, :] - pos2[None, None, :]) / d_safe[:, None, :]
            low = np.minimum(t_a, t_b)                        # (R,W,2)
            high = np.maximum(t_a, t_b)
            inside = ((pos2[None, None, :] >= wmin2[None, :, :])
                      & (pos2[None, None, :] <= wmax2[None, :, :]))
            par = np.broadcast_to(parallel[:, None, :], low.shape)
            low = np.where(par & inside, -np.inf, low)        # eixo paralelo+dentro: livre
            high = np.where(par & inside, np.inf, high)
            discard = np.any(par & ~inside, axis=2)           # paralelo+fora: descarta wall
            t_enter = np.maximum(0.0, np.max(low, axis=2))    # (R,W)
            t_exit = np.minimum(1.0, np.min(high, axis=2))
            hit = (t_enter <= t_exit) & (t_exit >= 0.0) & (t_enter <= 1.0) & ~discard
            hit_dist = np.where(hit, t_enter * max_d, np.inf)
            closest = np.minimum(closest, np.min(hit_dist, axis=1))

        # ---- Obstáculos (esferas projetadas no raio) ----
        if obs_arr.shape[0] > 0:
            vec = np.broadcast_to(obs_arr[None, :, :] - pos[None, None, :],
                                  (num_rays, obs_arr.shape[0], 3))
            proj = np.einsum('rod,rd->ro', vec, ray_dirs)     # (R,O)
            perp = np.linalg.norm(vec - proj[:, :, None] * ray_dirs[:, None, :], axis=2)
            under = np.clip(r_obs ** 2 - perp ** 2, 0.0, None)
            hd = proj - np.sqrt(under)
            valid = (proj > 0) & (perp <= r_obs) & (hd > 0)
            hd = np.where(valid, hd, np.inf)
            closest = np.minimum(closest, np.min(hd, axis=1))

        return (1.0 - (closest / max_d)).astype(np.float32)

    def _lidar_scan_batch(self, positions, headings, w_min_arr, w_max_arr, obs_arr):
        """Igual a _lidar_scan mas para TODOS os agentes de uma vez (vetorizado também
        sobre A agentes). positions/headings: (A,3). Devolve (A,num_rays), bit-exacto
        vs. o loop original. Elimina as A chamadas Python por step."""
        A = positions.shape[0]
        num_rays = 8
        max_d = self.lidar_range
        r_obs = self.obstacle_radius

        # Heading projetado no plano horizontal, por agente (robusto a pitch).
        F_horiz = np.array(headings, dtype=float)
        F_horiz[:, 2] = 0.0
        n = np.linalg.norm(F_horiz, axis=1)                       # (A,)
        deg = n < 1e-6
        F_horiz[deg] = np.array([1.0, 0.0, 0.0])
        n = np.where(deg, 1.0, n)
        F_horiz = F_horiz / n[:, None]
        R_horiz = np.stack([-F_horiz[:, 1], F_horiz[:, 0], np.zeros(A)], axis=1)  # (A,3)

        angles = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)
        ray_dirs = (np.cos(angles)[None, :, None] * F_horiz[:, None, :]
                    + np.sin(angles)[None, :, None] * R_horiz[:, None, :])  # (A,R,3)

        closest = np.full((A, num_rays), max_d, dtype=np.float64)

        # ---- Paredes (AABB, slab em X e Y) ----
        if w_min_arr.shape[0] > 0:
            d = ray_dirs[:, :, :2] * max_d                        # (A,R,2)
            parallel = np.abs(d) < 1e-6
            d_safe = np.where(parallel, 1.0, d)
            pos2 = positions[:, :2]                               # (A,2)
            wmin2 = w_min_arr[:, :2]                              # (W,2)
            wmax2 = w_max_arr[:, :2]
            # broadcasting: (A,1,1,2) op (1,1,W,2) / (A,R,1,2)
            t_a = (wmin2[None, None, :, :] - pos2[:, None, None, :]) / d_safe[:, :, None, :]
            t_b = (wmax2[None, None, :, :] - pos2[:, None, None, :]) / d_safe[:, :, None, :]
            low = np.minimum(t_a, t_b)                            # (A,R,W,2)
            high = np.maximum(t_a, t_b)
            inside = ((pos2[:, None, None, :] >= wmin2[None, None, :, :])
                      & (pos2[:, None, None, :] <= wmax2[None, None, :, :]))  # (A,1,W,2)
            par = parallel[:, :, None, :]                         # (A,R,1,2)
            pi = par & inside                                     # -> (A,R,W,2)
            low = np.where(pi, -np.inf, low)
            high = np.where(pi, np.inf, high)
            discard = np.any(par & ~inside, axis=3)               # (A,R,W)
            t_enter = np.maximum(0.0, np.max(low, axis=3))        # (A,R,W)
            t_exit = np.minimum(1.0, np.min(high, axis=3))
            hit = (t_enter <= t_exit) & (t_exit >= 0.0) & (t_enter <= 1.0) & ~discard
            hit_dist = np.where(hit, t_enter * max_d, np.inf)
            closest = np.minimum(closest, np.min(hit_dist, axis=2))  # (A,R)

        # ---- Obstáculos (esferas projetadas) ----
        if obs_arr.shape[0] > 0:
            vec = obs_arr[None, None, :, :] - positions[:, None, None, :]   # (A,1,O,3)
            vec = np.broadcast_to(vec, (A, num_rays, obs_arr.shape[0], 3))
            proj = np.einsum('arod,ard->aro', vec, ray_dirs)      # (A,R,O)
            perp = np.linalg.norm(vec - proj[:, :, :, None] * ray_dirs[:, :, None, :], axis=3)
            under = np.clip(r_obs ** 2 - perp ** 2, 0.0, None)
            hd = proj - np.sqrt(under)
            valid = (proj > 0) & (perp <= r_obs) & (hd > 0)
            hd = np.where(valid, hd, np.inf)
            closest = np.minimum(closest, np.min(hd, axis=2))     # (A,R)

        return (1.0 - (closest / max_d)).astype(np.float32)

    def _get_observations(self):
        observations = {}
        # Pré-computa os cantos das AABB das paredes e o array de obstáculos UMA vez
        # por step (não por agente) — entrada do LiDAR vetorizado (ver _lidar_scan).
        if self.walls:
            w_min_arr = np.array([w['pos'] - w['size'] / 2.0 for w in self.walls])
            w_max_arr = np.array([w['pos'] + w['size'] / 2.0 for w in self.walls])
        else:
            w_min_arr = np.zeros((0, 3))
            w_max_arr = np.zeros((0, 3))
        obs_arr = np.asarray(self.obstacles, dtype=float).reshape(-1, 3)
        # LiDAR de TODOS os agentes numa só passagem vetorizada (ver _lidar_scan_batch).
        P = np.asarray(self.agent_positions, dtype=float)   # (A,3)
        H = np.asarray(self.agent_headings, dtype=float)    # (A,3)
        A = P.shape[0]
        arena2 = self.obs_norm_radius * 2
        lidar_all = self._lidar_scan_batch(P, H, w_min_arr, w_max_arr, obs_arr)

        # ── Bases egocêntricas F/R/U de TODOS os agentes numa só passagem ──
        # Vetorização do antigo loop por-agente (norm/cross/dot em Python puro era
        # ~78% do step()). PROVADO bit-exacto vs. o loop original (erro 0.00e+00 em
        # 42000 cenas-agente); teste de regressão: tests/test_obs_equivalence.py.
        F = H
        W = np.tile(np.array([0.0, 0.0, 1.0]), (A, 1))
        W[np.abs(F[:, 2]) > 0.99] = np.array([0.0, 1.0, 0.0])
        R = np.cross(F, W)
        R = R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-6)
        U = np.cross(R, F)

        def ego_to(target):
            """target (3,) único → dirs ego (A,3), dist (A,). Réplica vetorizada
            exacta de to_egocentric (guard dist<1e-6 → zeros)."""
            vec = target - P
            dist = np.linalg.norm(vec, axis=1)
            safe = dist >= 1e-6
            dir_w = np.zeros_like(vec)
            dir_w[safe] = vec[safe] / dist[safe, None]
            dirs = np.stack([np.einsum('ij,ij->i', dir_w, F),
                             np.einsum('ij,ij->i', dir_w, R),
                             np.einsum('ij,ij->i', dir_w, U)], axis=1)
            dirs[~safe] = 0.0
            return dirs, np.where(safe, dist, 0.0)

        # BÚSSOLA DE HOMING: a direção+distância (euclidiana) para o ninho está
        # SEMPRE disponível, mesmo sem linha de visão. Justificação: em swarm
        # robotics assume-se homing global para a base (bússola/GPS/beacon —
        # cf. formigas/sol, pombos/campo magnético, drones/GPS), mas NÃO um mapa
        # dos obstáculos. Os obstáculos continuam invisíveis até serem detetados
        # localmente pelo LiDAR (5m) — observabilidade parcial genuína mantida.
        # Antes zerava-se a direção sem line-of-sight, o que cegava os agentes em
        # todos os cenários com paredes (u_wall, bottleneck, four_rooms, door).
        dir_nest, dist_nest = ego_to(self.nest_pos)         # (A,3), (A,)
        norm_dist_nest = dist_nest / arena2

        # ── B1: BÚSSOLA DA PORTA/ENTRADA (direção+distância egocêntricas) ──
        # Indica onde está a porta/passagem-objetivo do cenário. Preenchida
        # apenas quando existe uma porta DEFINIDA (cooperative_door) — que é um
        # sub-objetivo físico do cenário (como o ninho), não um waypoint de
        # planeamento. Nos restantes cenários fica a zeros (não revela o caminho
        # nos labirintos, o que seria batota). Mantém a dimensão da obs fixa.
        if self.has_door:
            dir_door, dist_door = ego_to(self.door_pos)
            norm_dist_door = dist_door / arena2
        else:
            dir_door = np.zeros((A, 3))
            norm_dist_door = np.zeros(A)

        # ── Vizinhos (A×A): vec[i,j] = P[j] − P[i], projeção egocêntrica de i ──
        vec = P[None, :, :] - P[:, None, :]                 # (A,A,3)
        dist = np.linalg.norm(vec, axis=2)                  # (A,A)
        safe = dist >= 1e-6
        dir_w = np.zeros_like(vec)
        dir_w[safe] = vec[safe] / dist[safe, None]
        pf = np.where(safe, np.einsum('ijk,ik->ij', dir_w, F), 0.0)
        pr = np.where(safe, np.einsum('ijk,ik->ij', dir_w, R), 0.0)
        pu = np.where(safe, np.einsum('ijk,ik->ij', dir_w, U), 0.0)
        nd = np.where(safe, dist, 0.0) / arena2
        sig = np.asarray(self.signaling, dtype=float)

        for idx, agent in enumerate(self.agents):
            neighbor_feats = []
            for j in range(A):
                if idx == j: continue
                neighbor_feats.extend([pf[idx, j], pr[idx, j], pu[idx, j], nd[idx, j], sig[j]])

            obs = np.concatenate([
                dir_nest[idx], [norm_dist_nest[idx]],
                lidar_all[idx],
                dir_door[idx], [norm_dist_door[idx]],
                np.array(neighbor_feats)
            ]).astype(np.float32)

            observations[agent] = obs
        return observations

    def step(self, actions):
        self.steps += 1

        # Rrobust: a meio do episódio, uma fração dos agentes "falha" (fica inerte).
        if (self.agent_failure_fraction > 0 and not self._failure_injected
                and self.steps >= self.max_steps // 2):
            n_fail = int(self.num_agents * self.agent_failure_fraction)
            if n_fail > 0:
                idxs = np.random.choice(self.num_agents, n_fail, replace=False)
                self.failed[idxs] = True
            self._failure_injected = True

        rewards = {a: 0.0 for a in self.agents}
        terms = {a: False for a in self.agents}
        truncs = {a: False for a in self.agents}
        infos = {a: {} for a in self.agents}

        # O Sandbox já não tem ninho dinâmico. Foi movido apenas para Perceção Cooperativa.

        if self.dynamic_obstacles and self.classic_scenario == "none":
            for i in range(len(self.obstacles)):
                self.obstacles[i] += self.obstacle_velocities[i]
                if np.linalg.norm(self.obstacles[i]) > (self.arena_radius - self.obstacle_radius):
                    dir_center = -self.obstacles[i]
                    dir_center /= (np.linalg.norm(dir_center) + 1e-6)
                    noise = np.random.uniform(-0.2, 0.2, 3)
                    new_vel = dir_center + noise
                    self.obstacle_velocities[i] = (new_vel / (
                                np.linalg.norm(new_vel) + 1e-6)) * self.obstacle_velocity_magnitude

        # --- LÓGICA DE PERCEÇÃO COOPERATIVA ---
        if self.classic_scenario == "cooperative_perception":
            # Move o Alvo Móvel (identificado pelo código como o nest)
            self.nest_pos += self.nest_velocity
            if np.linalg.norm(self.nest_pos) > (self.arena_radius - 2.0):
                dir_center = -self.nest_pos
                noise = np.random.uniform(-0.2, 0.2, 3)
                new_vel = dir_center + noise
                self.nest_velocity = (new_vel / (np.linalg.norm(new_vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
            
            observing_robots = []
            angles = []
            for i in range(self.num_agents):
                if self.failed[i]:
                    continue  # Rrobust: agente falhado não observa o alvo
                vec = self.agent_positions[i] - self.nest_pos
                dist = np.linalg.norm(vec)
                # Só contam robôs a menos de 4 metros que o estejam a rodear
                if dist < 4.0:
                    angle = np.arctan2(vec[1], vec[0])
                    observing_robots.append(i)
                    angles.append(angle)
            
            if len(observing_robots) >= 3:
                angles.sort()
                max_diff = 0
                for j in range(len(angles)):
                    diff = angles[(j+1)%len(angles)] - angles[j]
                    if diff < 0: diff += 2 * np.pi
                    if diff > max_diff:
                        max_diff = diff
                
                # Se a maior diferença de ângulo for <= 180º, o alvo está completamente rodeado/filmado!
                if max_diff <= np.pi:
                    self.total_food_collected += 1
                    for idx in observing_robots:
                        rewards[self.agents[idx]] += 300.0
                        self.hunger_timers[idx] = 0
                    
                    # O alvo móvel "foge" ou respawna numa nova localização para identificarem outro
                    self.nest_pos = self._random_spawn(max_radius=0.7)
                    vel = np.random.uniform(-1, 1, 3)
                    self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
        # --------------------------------------

        for idx, agent in enumerate(self.agents):
            if agent in actions:
                if self.signaling[idx] == 1.0: continue
                if self.failed[idx]: continue  # Rrobust: agente falhado fica inerte
                move_local = np.clip(actions[agent], -1, 1) * 0.2

                F = self.agent_headings[idx]
                W = np.array([0.0, 0.0, 1.0])
                if abs(np.dot(F, W)) > 0.99: W = np.array([0.0, 1.0, 0.0])
                R = np.cross(F, W)
                R /= (np.linalg.norm(R) + 1e-6)
                U = np.cross(R, F)

                move_global = move_local[0] * F + move_local[1] * R + move_local[2] * U

                # Projeção Vetorial para Deslizar nos Muros (Sliding Physics)
                for wall in self.walls:
                    next_pos = self.agent_positions[idx] + move_global
                    delta = next_pos - wall['pos']
                    abs_delta = np.abs(delta)
                    half_size = wall['size'] / 2.0
                    penetration = (half_size + self.robot_radius) - abs_delta
                    
                    if np.all(penetration > 0):
                        # Bateu no muro, descobrir a normal da face atingida
                        min_axis = np.argmin(penetration)
                        normal = np.zeros(3)
                        normal[min_axis] = np.sign(delta[min_axis]) if delta[min_axis] != 0 else 1.0
                        # Remover a componente do movimento que vai contra a normal (deslizar)
                        move_global = move_global - np.dot(move_global, normal) * normal
                        
                if np.linalg.norm(move_global) > 0.02:
                    self.agent_headings[idx] = move_global / np.linalg.norm(move_global)

                self.agent_positions[idx] += move_global

        if self.has_door and self.door_active:
            self._update_door(rewards)

        obstacle_hits = {a: 0 for a in self.agents}
        for idx, agent in enumerate(self.agents):

            for obs_pos in self.obstacles:
                dist = np.linalg.norm(self.agent_positions[idx] - obs_pos)
                min_dist = self.robot_radius + self.obstacle_radius
                if dist < min_dist:
                    obstacle_hits[agent] = 1
                    direction = self.agent_positions[idx] - obs_pos
                    norm = np.linalg.norm(direction)
                    if norm > 0: direction /= norm
                    self.agent_positions[idx] += direction * (min_dist - dist)

            for wall in self.walls:
                delta = self.agent_positions[idx] - wall['pos']
                abs_delta = np.abs(delta)
                half_size = wall['size'] / 2.0

                penetration = (half_size + self.robot_radius) - abs_delta

                if np.all(penetration > 0):
                    obstacle_hits[agent] = 1
                    min_axis = np.argmin(penetration)
                    sign = np.sign(delta[min_axis])
                    if sign == 0: sign = 1.0
                    self.agent_positions[idx][min_axis] += penetration[min_axis] * sign

        # --- Separação física inter-agente + penalidade de spreading ---
        # A separação física (anti-sobreposição) aplica-se SEMPRE.
        # A penalidade de spreading (reward) só durante a navegação — é ISENTA
        # em zonas de cooperação onde a tarefa exige proximidade (junto ao ninho,
        # ao alvo móvel, ou à push zone da porta), senão sabotava required_to_eat.
        self._spreading_penalties = np.zeros(self.num_agents)
        self._collision_penalties = np.zeros(self.num_agents)
        min_sep = self.robot_radius * 2
        spread_dist = self.min_spread_distance

        coop_points = [self.nest_pos]
        if self.has_door:
            coop_points.append(self.door_push_center)  # centro da push zone
        coop_zone = 4.0
        in_coop_zone = np.zeros(self.num_agents, dtype=bool)
        for idx in range(self.num_agents):
            for cp in coop_points:
                if np.linalg.norm(self.agent_positions[idx] - cp) < coop_zone:
                    in_coop_zone[idx] = True
                    break

        for i in range(self.num_agents):
            if self.signaling[i] == 1.0:
                continue
            for j in range(i + 1, self.num_agents):
                if self.signaling[j] == 1.0:
                    continue
                diff = self.agent_positions[i] - self.agent_positions[j]
                dist = np.linalg.norm(diff)
                if dist < 1e-6:
                    diff = np.array([np.random.uniform(-0.05, 0.05),
                                     np.random.uniform(-0.05, 0.05), 0.0])
                    dist = np.linalg.norm(diff) + 1e-6
                if dist < min_sep:
                    # COLISÃO física (sobreposição): separa E penaliza sempre — chocar
                    # é indesejado mesmo nas zonas de cooperação. Proporcional à penetração.
                    push = (diff / dist) * (min_sep - dist) * 0.5
                    self.agent_positions[i] += push
                    self.agent_positions[j] -= push
                    col = abs(self.collision_penalty) * (1.0 - dist / min_sep)
                    self._collision_penalties[i] += col
                    self._collision_penalties[j] += col
                    self.total_collisions += 1
                elif dist < spread_dist and not (in_coop_zone[i] or in_coop_zone[j]):
                    # PROXIMIDADE (sem sobreposição): anti-clustering só na navegação.
                    pen = self.spreading_penalty_factor * (1.0 - dist / spread_dist)
                    self._spreading_penalties[i] += pen
                    self._spreading_penalties[j] += pen
        # ---------------------------------------------------------------

        robots_in_nest = []
        for idx in range(self.num_agents):
            if self.failed[idx]:
                continue  # Rrobust: agente falhado não conta para a tarefa
            if np.linalg.norm(self.agent_positions[idx] - self.nest_pos) < (self.nest_radius + 0.1):
                robots_in_nest.append(idx)
                # No cenário de perceção cooperativa, não há o conceito físico de "entrar" no ninho e repousar
                if self.classic_scenario != "cooperative_perception":
                    self.signaling[idx] = 1.0
                    self.agent_positions[idx] = self.nest_pos.copy()
            else:
                self.signaling[idx] = 0.0

        self.current_nest_occupancy = len(robots_in_nest)

        if self.classic_scenario != "cooperative_perception":
            if self.current_nest_occupancy >= self.required_to_eat:
                self.total_food_collected += 1
                if self.classic_scenario == "none":
                    self._spawn_nest()
                for idx in range(self.num_agents):
                    if idx in robots_in_nest:
                        rewards[self.agents[idx]] += self.food_collected_reward
                        self.agent_positions[idx] = self._get_scenario_spawn_pos()
                        self.hunger_timers[idx] = 0
                    self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                    self.prev_pot[idx] = self._potential(self.agent_positions[idx])
                    self.signaling[idx] = 0.0

        for idx, agent in enumerate(self.agents):
            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
            pot = self._potential(self.agent_positions[idx])

            if np.linalg.norm(self.agent_positions[idx]) > (self.arena_radius - self.robot_radius):
                direction = -self.agent_positions[idx]
                direction /= (np.linalg.norm(direction) + 1e-6)
                self.agent_positions[idx] += direction * 0.5
                obstacle_hits[agent] = 1
                # Re-sincroniza o potencial (o empurrão para dentro não é mérito do
                # agente) para não injetar progress espúrio no passo seguinte.
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.prev_pot[idx] = self._potential(self.agent_positions[idx])
                continue

            if self.signaling[idx] == 1.0:
                pass
            else:
                # ── Reward Structure ─────────────────────────────────────────
                # NOTA: NÃO há ICM (Intrinsic Curiosity Module).
                # A exploração é incentivada exclusivamente por reward shaping:
                #
                #   progress_reward = factor × (Φ_t-1 − Φ_t)
                #     onde Φ é o POTENCIAL de navegação: distância GEODÉSICA ao
                #     ninho nos cenários com paredes (contorna-as), euclidiana nos
                #     restantes. Geodésico → contornar uma parede dá progress
                #     POSITIVO (antes, com euclidiano, contornar = afastar =
                #     negativo, prendendo os agentes nas paredes).
                #     → "Potential-Based Reward Shaping" (Ng et al., 1999):
                #        não altera a política óptima.
                #
                #   energy_cost = −0.05/passo
                #     → pressão temporal para resolver a tarefa depressa
                #
                # Recompensa de tarefa pura (sem shaping):
                #   food_collected_reward = +100 (quando required_to_eat
                #   agentes chegam simultaneamente ao ninho)
                # ─────────────────────────────────────────────────────────────
                progress = self.prev_pot[idx] - pot
                rewards[agent] += (progress * self.progress_reward_factor) + self.energy_cost
                self.hunger_timers[idx] += 1

                # ── Reward de Exploração (count-based) ───────────────────────
                # Bónus por visitar pela primeira vez uma célula da grelha.
                # Tira os agentes dos mínimos locais nas paredes (onde o progress
                # euclidiano os prende) ao premiar a cobertura de zonas novas —
                # essencial para descobrir desvios em u_wall/four_rooms/bottleneck.
                cell = (int(self.agent_positions[idx][0] // self.exploration_cell_size),
                        int(self.agent_positions[idx][1] // self.exploration_cell_size))
                if cell not in self.visited_cells[idx]:
                    self.visited_cells[idx].add(cell)
                    rewards[agent] += self.exploration_bonus
                # ─────────────────────────────────────────────────────────────

            self.prev_dist_to_nest[idx] = dist_nest
            self.prev_pot[idx] = pot

            if obstacle_hits[agent]: rewards[agent] += self.obstacle_penalty
            if self._spreading_penalties[idx] > 0:
                rewards[agent] -= self._spreading_penalties[idx]
            if self._collision_penalties[idx] > 0:
                rewards[agent] -= self._collision_penalties[idx]

            # ── Hunger / respawn ─────────────────────────────────────────────
            # Nos cenários de LABIRINTO o teleporte por hunger era "farmável":
            # aproximar-se da parede (progress +) → reset para o spawn (sem cobrar
            # o salto) → reaproximar (progress + outra vez). A política óptima
            # aprendida passava a ser "colar à parede e esperar o reset" — daí o
            # total_reward ≈ 20.000 com ZERO comida. Por isso o teleporte só está
            # ativo no foraging contínuo (sandbox); nos labirintos a pressão
            # temporal vem só do energy_cost.
            if (not self.use_geodesic
                    and self.hunger_timers[idx] > self.hunger_timer_max):
                rewards[agent] -= 50.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._get_scenario_spawn_pos()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.prev_pot[idx] = self._potential(self.agent_positions[idx])

            terms[agent] = self.steps >= self.max_steps

        return self._get_observations(), rewards, terms, truncs, infos

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]