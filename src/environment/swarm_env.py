import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame
import yaml
import os


class SwarmForagingEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, config_path=None):
        super(SwarmForagingEnv, self).__init__()

        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.num_agents = self.config['environment']['num_agents']
        self.arena_radius = self.config['environment']['arena_radius']
        self.nest_radius = self.config['environment']['nest_radius']
        self.max_steps = self.config['environment'].get('max_steps', 500)

        self.robot_radius = 0.05
        self.obstacle_radius = 0.2
        self.num_obstacles = 3  # Quantas pedras queremos?

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        # Ação: Velocidade X, Y
        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # Observação: 9 inputs + vizinhos
        obs_size = 9 + (self.num_agents - 1) * 2
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.render_mode = None
        self.window = None
        self.clock = None
        self.screen_size = 800
        self.scale = self.screen_size / (self.arena_radius * 2.2)

        # Inicializar variaveis vazias
        self.nest_pos = np.array([0.0, 0.0])
        self.obstacles = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0

        # --- 1. RANDOMIZAR NINHO (Dentro de um raio seguro) ---
        # Não metemos o ninho muito na borda para não ser impossível
        nest_angle = np.random.uniform(0, 2 * np.pi)
        nest_dist = np.random.uniform(0, self.arena_radius * 0.5)
        self.nest_pos = np.array([nest_dist * np.cos(nest_angle), nest_dist * np.sin(nest_angle)])

        # --- 2. RANDOMIZAR OBSTÁCULOS ---
        self.obstacles = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                # Gerar posição aleatória na arena
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0.5, self.arena_radius * 0.8)
                pos = np.array([dist * np.cos(angle), dist * np.sin(angle)])

                # Verificar se não cai em cima do ninho
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.2):
                    self.obstacles.append(pos)
                    valid = True

        # --- 3. RANDOMIZAR ROBÔS ---
        self.agent_positions = []
        for _ in range(self.num_agents):
            self.agent_positions.append(self._random_spawn())
        self.agent_positions = np.array(self.agent_positions)

        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        return self._get_observations(), {}

    def _random_spawn(self):
        # Spawn nas bordas (longe do centro para obrigar a procurar)
        angle = np.random.uniform(0, 2 * np.pi)
        r = self.arena_radius * np.sqrt(np.random.uniform(0.9, 1.0))
        return np.array([r * np.cos(angle), r * np.sin(angle)])

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]

            # 1. Ninho (Vetor relativo muda porque o ninho mexe!)
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            # 2. Obstáculo Mais Próximo
            closest_obs_dist = 5.0  # Max range sensor
            closest_obs_dir = np.array([0.0, 0.0])

            for obs in self.obstacles:
                d = np.linalg.norm(pos - obs) - self.obstacle_radius
                if d < closest_obs_dist:
                    closest_obs_dist = d
                    direction = (obs - pos)
                    if np.linalg.norm(direction) > 0:
                        closest_obs_dir = direction / np.linalg.norm(direction)

            sensor_obs = np.clip(closest_obs_dist, 0, 5.0)

            # 3. Vizinhos
            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                rel_pos = other_pos - pos
                neighbor_feats.extend(rel_pos)

            obs = np.concatenate([
                [0, 0],
                [dist_nest],
                dir_nest,
                [sensor_obs],
                closest_obs_dir,
                np.array([0.0]),
                np.array(neighbor_feats)
            ]).astype(np.float32)

            observations[agent] = obs
        return observations

    def step(self, actions):
        self.steps += 1
        rewards = {}
        terms = {}
        truncs = {}
        infos = {}

        # Mover
        for idx, agent in enumerate(self.agents):
            if agent in actions:
                self.agent_positions[idx] += actions[agent] * 0.1

                # Física (Simplificada)
        obstacle_hits = {a: 0 for a in self.agents}

        for idx, agent in enumerate(self.agents):
            # Colisão com Obstáculos Dinâmicos
            for obs_pos in self.obstacles:
                dist = np.linalg.norm(self.agent_positions[idx] - obs_pos)
                min_dist = self.robot_radius + self.obstacle_radius
                if dist < min_dist:
                    obstacle_hits[agent] = 1
                    direction = self.agent_positions[idx] - obs_pos
                    norm = np.linalg.norm(direction)
                    if norm > 0: direction /= norm
                    push = direction * (min_dist - dist)
                    self.agent_positions[idx] += push

        # Recompensas
        for idx, agent in enumerate(self.agents):
            self.agent_positions[idx] = np.clip(self.agent_positions[idx], -self.arena_radius, self.arena_radius)

            rew = -0.01
            pos = self.agent_positions[idx]
            dist_nest = np.linalg.norm(pos - self.nest_pos)

            # Comer
            if dist_nest < (self.nest_radius + 0.1):
                rew += 30.0
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0
            else:
                self.hunger_timers[idx] += 1
                rew += (1.0 / (dist_nest + 0.1)) * 0.05

            if obstacle_hits[agent]:
                rew -= 1.0

                # Fome
            if self.hunger_timers[idx] > 150:
                rew -= 5.0
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0

            rewards[agent] = rew
            terms[agent] = self.steps >= self.max_steps
            truncs[agent] = False
            infos[agent] = {}

        if self.render_mode == "human": self.render()
        return self._get_observations(), rewards, terms, truncs, infos

    def render(self):
        if self.window is None:
            pygame.init()
            self.window = pygame.display.set_mode((self.screen_size, self.screen_size))
            pygame.display.set_caption("Swarm Environment (Dynamic)")

        self.window.fill((30, 30, 30))

        def to_screen(p):
            return (int((p[0] + self.arena_radius * 1.1) * self.scale),
                    int((-p[1] + self.arena_radius * 1.1) * self.scale))

        # Desenhar Ninho (Agora muda de sítio!)
        pygame.draw.circle(self.window, (0, 200, 0), to_screen(self.nest_pos), int(self.nest_radius * self.scale))

        # Desenhar Obstaculos (Agora mudam de sítio!)
        for obs in self.obstacles:
            pygame.draw.circle(self.window, (100, 100, 100), to_screen(obs), int(self.obstacle_radius * self.scale))

        # Robôs
        for p in self.agent_positions:
            pygame.draw.circle(self.window, (200, 50, 50), to_screen(p), int(self.robot_radius * self.scale))

        pygame.display.flip()

    def close(self):
        if self.window: pygame.quit()

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]