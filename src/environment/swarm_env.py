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
        self.num_obstacles = 3

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

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

        self.nest_pos = np.array([0.0, 0.0])
        self.obstacles = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0

        # 1. Randomizar Ninho
        nest_angle = np.random.uniform(0, 2 * np.pi)
        nest_dist = np.random.uniform(0, self.arena_radius * 0.5)
        self.nest_pos = np.array([nest_dist * np.cos(nest_angle), nest_dist * np.sin(nest_angle)])

        # 2. Randomizar Obstáculos
        self.obstacles = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0.5, self.arena_radius * 0.8)
                pos = np.array([dist * np.cos(angle), dist * np.sin(angle)])
                # Verificar se não cai em cima do ninho
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.2):
                    self.obstacles.append(pos)
                    valid = True

        # 3. Randomizar Robôs
        self.agent_positions = []
        for _ in range(self.num_agents):
            self.agent_positions.append(self._random_spawn())
        self.agent_positions = np.array(self.agent_positions)

        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        return self._get_observations(), {}

    def _random_spawn(self):
        angle = np.random.uniform(0, 2 * np.pi)
        # Spawn um pouco mais espalhado (0.0 a 0.8) para não nascerem todos na parede
        r = self.arena_radius * np.sqrt(np.random.uniform(0.0, 0.8))
        return np.array([r * np.cos(angle), r * np.sin(angle)])

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]

            # 1. Ninho
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            # 2. Obstáculos
            closest_obs_dist = 5.0
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

            # VOLTAMOS AO INPUT ORIGINAL (Sem GPS) para estabilidade
            obs = np.concatenate([
                [0, 0],  # Placeholder [0,0] em vez de GPS
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

                # Física (Obstáculos)
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

        # Recompensas
        for idx, agent in enumerate(self.agents):

            # --- PAREDES (Versão Suave: Empurra e Castiga, NÃO MATA) ---
            hit_wall = False
            if np.linalg.norm(self.agent_positions[idx]) > self.arena_radius:
                self.agent_positions[idx] = np.clip(self.agent_positions[idx], -self.arena_radius, self.arena_radius)
                hit_wall = True
            # -----------------------------------------------------------

            rew = -0.01
            pos = self.agent_positions[idx]
            dist_nest = np.linalg.norm(pos - self.nest_pos)

            # Coesão (Pequena mesada para andarem juntos)
            neighbors_count = 0
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                dist_friend = np.linalg.norm(pos - other_pos)
                if dist_friend < 1.0:
                    neighbors_count += 1
            rew += neighbors_count * 0.005

            # Comer
            if dist_nest < (self.nest_radius + 0.1):
                rew += 30.0
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0

                # Ninho Fugitivo
                new_angle = np.random.uniform(0, 2 * np.pi)
                new_dist = np.random.uniform(0, self.arena_radius * 0.7)
                self.nest_pos = np.array([new_dist * np.cos(new_angle), new_dist * np.sin(new_angle)])
            else:
                self.hunger_timers[idx] += 1
                rew += (1.0 / (dist_nest + 0.1)) * 0.05

            if obstacle_hits[agent]:
                rew -= 1.0

                # Castigo na Parede
            if hit_wall:
                rew -= 2.0

                # Fome
            if self.hunger_timers[idx] > 150:
                rew -= 10.0
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
            pygame.display.set_caption("Swarm Environment (Thesis Mode)")
            self.font = pygame.font.SysFont("Consolas", 18, bold=True)

        self.window.fill((30, 30, 30))

        def to_screen(p):
            return (int((p[0] + self.arena_radius * 1.1) * self.scale),
                    int((-p[1] + self.arena_radius * 1.1) * self.scale))

        # Desenhar Ninho e Obstáculos
        pygame.draw.circle(self.window, (0, 200, 0), to_screen(self.nest_pos), int(self.nest_radius * self.scale))
        for obs in self.obstacles:
            pygame.draw.circle(self.window, (100, 100, 100), to_screen(obs), int(self.obstacle_radius * self.scale))

        # Desenhar Linhas de Vizinhos (Azul)
        for i in range(len(self.agent_positions)):
            for j in range(i + 1, len(self.agent_positions)):
                pos_i = self.agent_positions[i]
                pos_j = self.agent_positions[j]
                dist = np.linalg.norm(pos_i - pos_j)
                if dist < 1.5:
                    thickness = max(1, int(4 - dist * 2))
                    start = to_screen(pos_i)
                    end = to_screen(pos_j)
                    pygame.draw.line(self.window, (50, 200, 255), start, end, thickness)

        # Desenhar Robôs e Lasers
        for idx, p in enumerate(self.agent_positions):
            screen_pos = to_screen(p)
            nest_screen = to_screen(self.nest_pos)
            pygame.draw.line(self.window, (0, 100, 0), screen_pos, nest_screen, 1)

            closest_obs_dist = 999.0
            closest_obs_pos = None
            for obs in self.obstacles:
                dist = np.linalg.norm(p - obs)
                if dist < closest_obs_dist:
                    closest_obs_dist = dist
                    closest_obs_pos = obs

            if closest_obs_pos is not None and closest_obs_dist < 1.5:
                obs_screen = to_screen(closest_obs_pos)
                pygame.draw.line(self.window, (255, 50, 50), screen_pos, obs_screen, 2)

            pygame.draw.circle(self.window, (200, 50, 50), screen_pos, int(self.robot_radius * self.scale))

        # HUD
        overlay = pygame.Surface((250, 90))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.window.blit(overlay, (10, 10))

        live_agents = sum([1 for t in self.hunger_timers if t < 150])
        text_steps = self.font.render(f"Step: {self.steps}/{self.max_steps}", True, (255, 255, 255))
        self.window.blit(text_steps, (20, 20))

        color_live = (0, 255, 0) if live_agents > self.num_agents / 2 else (255, 0, 0)
        text_agents = self.font.render(f"Alive: {live_agents}/{self.num_agents}", True, color_live)
        self.window.blit(text_agents, (20, 45))

        if self.clock:
            text_fps = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (100, 100, 255))
            self.window.blit(text_fps, (20, 70))

        pygame.display.flip()

    def close(self):
        if self.window: pygame.quit()

    # ESTAS SÃO AS FUNÇÕES QUE ESTAVAM A DAR ERRO (Agora estão bem indentadas)
    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]