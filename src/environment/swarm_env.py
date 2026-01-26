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

        # Obstáculos (Barreira à volta do ninho)
        self.obstacles = [
            np.array([0.6, 0.6]),
            np.array([-0.6, 0.2]),
            np.array([0.1, -0.7])
        ]

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        # Ação: Velocidade X, Y
        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # Observação: Adicionámos +3 inputs (Distancia Obstaculo, DirX Obstaculo, DirY Obstaculo)
        # Tamanho antigo: 6 + vizinhos. Novo: 9 + vizinhos
        obs_size = 9 + (self.num_agents - 1) * 2
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.render_mode = None
        self.window = None
        self.clock = None
        self.screen_size = 800
        self.scale = self.screen_size / (self.arena_radius * 2.2)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0

        # Posições Iniciais
        self.agent_positions = []
        for _ in range(self.num_agents):
            self.agent_positions.append(self._random_spawn())
        self.agent_positions = np.array(self.agent_positions)

        self.nest_pos = np.array([0.0, 0.0])

        # Timer de Fome (Steps desde a ultima comida)
        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        return self._get_observations(), {}

    def _random_spawn(self):
        angle = np.random.uniform(0, 2 * np.pi)
        r = self.arena_radius * np.sqrt(np.random.uniform(0.8, 1.0))
        return np.array([r * np.cos(angle), r * np.sin(angle)])

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]

            # 1. Ninho
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            # 2. Obstáculo Mais Próximo (OLHOS NOVOS! 👀)
            closest_obs_dist = 999.0
            closest_obs_dir = np.array([0.0, 0.0])

            for obs in self.obstacles:
                d = np.linalg.norm(pos - obs) - self.obstacle_radius  # Distancia até à superfície
                if d < closest_obs_dist:
                    closest_obs_dist = d
                    direction = (obs - pos)
                    if np.linalg.norm(direction) > 0:
                        closest_obs_dir = direction / np.linalg.norm(direction)

            # Normalizar distancia do obstaculo (0 = perto, 1 = longe)
            sensor_obs = np.clip(closest_obs_dist, 0, 5.0)

            # 3. Vizinhos
            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                rel_pos = other_pos - pos
                neighbor_feats.extend(rel_pos)

            obs = np.concatenate([
                [0, 0],  # Placeholder vel
                [dist_nest],
                dir_nest,  # [dx, dy] para o ninho
                [sensor_obs],  # Distancia para a pedra
                closest_obs_dir,  # [dx, dy] para a pedra
                np.array([0.0]),  # Placeholder estado
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
                vel = actions[agent]
                self.agent_positions[idx] += vel * 0.1

                # Física (Simplificada para brevidade, mas inclui obstaculos)
        agent_pos = self.agent_positions
        collision_counts = {a: 0 for a in self.agents}
        obstacle_hits = {a: 0 for a in self.agents}

        # Colisão Robô-Obstáculo
        for idx, agent in enumerate(self.agents):
            for obs_pos in self.obstacles:
                dist = np.linalg.norm(agent_pos[idx] - obs_pos)
                min_dist = self.robot_radius + self.obstacle_radius
                if dist < min_dist:
                    obstacle_hits[agent] = 1  # Bateu!
                    # Empurrar
                    direction = agent_pos[idx] - obs_pos
                    norm = np.linalg.norm(direction)
                    if norm > 0: direction /= norm
                    push = direction * (min_dist - dist)
                    self.agent_positions[idx] += push

        # Recompensas
        for idx, agent in enumerate(self.agents):
            self.agent_positions[idx] = np.clip(self.agent_positions[idx], -self.arena_radius, self.arena_radius)

            rew = -0.01  # Custo de energia base
            pos = self.agent_positions[idx]
            dist_nest = np.linalg.norm(pos - self.nest_pos)

            # Comer
            if dist_nest < (self.nest_radius + 0.1):
                rew += 30.0  # GRANDE RECOMPENSA
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0  # Reset fome
            else:
                self.hunger_timers[idx] += 1
                # Guia suave (shaping)
                rew += (1.0 / (dist_nest + 0.1)) * 0.05

            # Penalizações
            if obstacle_hits[agent]:
                rew -= 1.0  # Dói bater na pedra

            # Lógica de FOME (A tua ideia!) 💀
            if self.hunger_timers[idx] > 150:  # Se passar 150 frames sem comer
                rew -= 5.0  # Castigo por morrer
                self.agent_positions[idx] = self._random_spawn()  # Respawn noutro sitio
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
            pygame.display.set_caption("Swarm Environment")

        self.window.fill((30, 30, 30))

        def to_screen(p):
            return (int((p[0] + self.arena_radius * 1.1) * self.scale),
                    int((-p[1] + self.arena_radius * 1.1) * self.scale))

        # Ninho
        pygame.draw.circle(self.window, (0, 200, 0), to_screen(self.nest_pos), int(self.nest_radius * self.scale))
        # Obstaculos
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