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

        # --- FASE 2: OBSTÁCULOS ATIVOS ---
        self.num_obstacles = 3
        # ---------------------------------

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # --- INPUT ATUALIZADO (COM VISÃO) ---
        # 1. Pos (2)
        # 2. Ninho (2)
        # 3. Pedra Mais Perto (Distância + Direção X + Direção Y) = 3
        # Total = 7 inputs + Vizinhos
        obs_size = 7 + (self.num_agents - 1) * 2
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.render_mode = None
        self.window = None
        self.clock = None
        self.screen_size = 800
        self.scale = self.screen_size / (self.arena_radius * 2.2)

        self.nest_pos = np.array([0.0, 0.0])
        self.obstacles = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0

        # 1. Ninho
        nest_angle = np.random.uniform(0, 2 * np.pi)
        nest_dist = np.random.uniform(0, self.arena_radius * 0.5)
        self.nest_pos = np.array([nest_dist * np.cos(nest_angle), nest_dist * np.sin(nest_angle)])

        # 2. Obstáculos (Agora existem!)
        self.obstacles = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0.5, self.arena_radius * 0.8)
                pos = np.array([dist * np.cos(angle), dist * np.sin(angle)])
                # Não nascer em cima do ninho
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.4):
                    self.obstacles.append(pos)
                    valid = True

        # 3. Robôs
        self.agent_positions = []
        for _ in range(self.num_agents):
            self.agent_positions.append(self._random_spawn())
        self.agent_positions = np.array(self.agent_positions)

        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        return self._get_observations(), {}

    def _random_spawn(self):
        angle = np.random.uniform(0, 2 * np.pi)
        r = self.arena_radius * np.sqrt(np.random.uniform(0.0, 0.8))
        return np.array([r * np.cos(angle), r * np.sin(angle)])

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]

            # 1. Posição
            norm_pos = pos / self.arena_radius

            # 2. Ninho
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            # 3. OBSTÁCULO MAIS PRÓXIMO (O Novo Sensor) 👁️
            closest_dist = 5.0  # Alcance máximo
            closest_dir = np.array([0.0, 0.0])

            for obs in self.obstacles:
                # Distância da superfície do robô à superfície da pedra
                d = np.linalg.norm(pos - obs) - self.obstacle_radius - self.robot_radius
                if d < closest_dist:
                    closest_dist = d
                    direction = (obs - pos)
                    if np.linalg.norm(direction) > 0:
                        closest_dir = direction / np.linalg.norm(direction)

            # Normalizar distância (0 = tocou, 1 = longe)
            sensor_dist_norm = np.clip(closest_dist / 2.0, 0, 1.0)

            # 4. Vizinhos
            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                rel_pos = (other_pos - pos) / self.arena_radius
                neighbor_feats.extend(rel_pos)

            # CONCATENAR (Total = 7 + Vizinhos)
            obs = np.concatenate([
                norm_pos,  # 2
                dir_nest,  # 2
                [sensor_dist_norm],  # 1 (Distância à pedra)
                closest_dir,  # 2 (Direção da pedra)
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

        # Mover Obstáculos (Drift)
        if self.num_obstacles > 0:
            for i in range(len(self.obstacles)):
                drift = np.random.uniform(-0.015, 0.015, size=2)
                new_pos = self.obstacles[i] + drift
                if np.linalg.norm(new_pos) < self.arena_radius * 0.9:
                    self.obstacles[i] = new_pos

        # Mover Robôs
        for idx, agent in enumerate(self.agents):
            if agent in actions:
                move = np.clip(actions[agent], -1, 1) * 0.1
                self.agent_positions[idx] += move

        # Física e Colisões
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
                    push = direction * (min_dist - dist)
                    self.agent_positions[idx] += push

        # RECOMPENSAS (Ajustadas para evitar "Pânico de Grupo")
        for idx, agent in enumerate(self.agents):

            # Paredes
            if np.linalg.norm(self.agent_positions[idx]) > self.arena_radius:
                self.agent_positions[idx] = np.clip(self.agent_positions[idx], -self.arena_radius, self.arena_radius)

            rew = -0.01
            pos = self.agent_positions[idx]
            dist_nest = np.linalg.norm(pos - self.nest_pos)

            # --- MUDANÇA 1: ATRAÇÃO FATAL PELO NINHO ---
            # Aumentei de 0.1 para 0.5. O sinal do ninho agora é 5x mais forte.
            rew += (1.0 / (dist_nest + 0.1)) * 0.5

            # Comer
            if dist_nest < (self.nest_radius + 0.1):
                rew += 20.0
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0

                new_angle = np.random.uniform(0, 2 * np.pi)
                new_dist = np.random.uniform(0, self.arena_radius * 0.7)
                self.nest_pos = np.array([new_dist * np.cos(new_angle), new_dist * np.sin(new_angle)])
            else:
                self.hunger_timers[idx] += 1

            # --- MUDANÇA 2: MENOS MEDO ---
            # Se baterem na pedra, perdem pouco (-0.2).
            # Antes era -1.0 e eles entravam em pânico.
            if obstacle_hits[agent]:
                rew -= 0.2

                # Fome
            if self.hunger_timers[idx] > 200:
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
            pygame.font.init()
            self.window = pygame.display.set_mode((self.screen_size, self.screen_size))
            pygame.display.set_caption("Swarm Environment (Moving Obstacles)")
            self.font = pygame.font.SysFont("Consolas", 18, bold=True)

        self.window.fill((30, 30, 30))

        def to_screen(p):
            return (int((p[0] + self.arena_radius * 1.1) * self.scale),
                    int((-p[1] + self.arena_radius * 1.1) * self.scale))

        # Ninho
        pygame.draw.circle(self.window, (0, 200, 0), to_screen(self.nest_pos), int(self.nest_radius * self.scale))

        # Obstáculos
        for obs in self.obstacles:
            pygame.draw.circle(self.window, (100, 100, 100), to_screen(obs), int(self.obstacle_radius * self.scale))

        # Robôs
        for idx, p in enumerate(self.agent_positions):
            screen_pos = to_screen(p)
            nest_screen = to_screen(self.nest_pos)
            pygame.draw.line(self.window, (0, 100, 0), screen_pos, nest_screen, 1)

            # Laser Vermelho para Pedra se estiver perto
            closest_dist = 999
            closest_pos = None
            for obs in self.obstacles:
                d = np.linalg.norm(p - obs)
                if d < closest_dist:
                    closest_dist = d
                    closest_pos = obs

            if closest_pos is not None and closest_dist < 1.0:
                pygame.draw.line(self.window, (255, 50, 50), screen_pos, to_screen(closest_pos), 2)

            pygame.draw.circle(self.window, (200, 50, 50), screen_pos, int(self.robot_radius * self.scale))

        # HUD
        overlay = pygame.Surface((250, 60))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.window.blit(overlay, (10, 10))

        text_steps = self.font.render(f"Step: {self.steps}/{self.max_steps}", True, (255, 255, 255))
        self.window.blit(text_steps, (20, 20))
        if self.clock:
            text_fps = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (100, 100, 255))
            self.window.blit(text_fps, (20, 40))

        pygame.display.flip()

    def close(self):
        if self.window: pygame.quit()

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]