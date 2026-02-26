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

        self.required_to_eat = 3
        self.deaths_count = 0
        self.total_food_collected = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]
        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        obs_size = 7 + (self.num_agents - 1) * 3
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.render_mode = None
        self.window = None
        self.scale = 800 / (self.arena_radius * 2.2)

        self.nest_pos = np.array([0.0, 0.0])
        self.obstacles = []
        self.prev_dist_to_nest = np.zeros(self.num_agents)
        self.signaling = np.zeros(self.num_agents)
        self.current_nest_occupancy = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0
        self.signaling = np.zeros(self.num_agents)

        self._spawn_nest()
        self._spawn_obstacles()

        self.agent_positions = np.array([self._random_spawn() for _ in range(self.num_agents)])
        self.prev_dist_to_nest = np.array([np.linalg.norm(p - self.nest_pos) for p in self.agent_positions])
        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        return self._get_observations(), {}

    def _spawn_nest(self):
        nest_angle = np.random.uniform(0, 2 * np.pi)
        nest_dist = np.random.uniform(0, self.arena_radius * 0.5)
        self.nest_pos = np.array([nest_dist * np.cos(nest_angle), nest_dist * np.sin(nest_angle)])

    def _spawn_obstacles(self):
        self.obstacles = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0.5, self.arena_radius * 0.8)
                pos = np.array([dist * np.cos(angle), dist * np.sin(angle)])
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.4):
                    self.obstacles.append(pos)
                    valid = True

    def _random_spawn(self):
        angle = np.random.uniform(0, 2 * np.pi)
        r = self.arena_radius * np.sqrt(np.random.uniform(0.0, 0.7))  # Nasce mais perto do centro
        return np.array([r * np.cos(angle), r * np.sin(angle)])

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]
            norm_pos = pos / self.arena_radius
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            closest_dist = 5.0
            closest_dir = np.array([0.0, 0.0])
            for obs in self.obstacles:
                d = np.linalg.norm(pos - obs) - self.obstacle_radius - self.robot_radius
                if d < closest_dist:
                    closest_dist = d
                    direction = (obs - pos)
                    if np.linalg.norm(direction) > 0:
                        closest_dir = direction / np.linalg.norm(direction)

            sensor_val = 1.0 - np.clip(closest_dist / 1.0, 0, 1.0)

            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                rel_pos = (other_pos - pos) / self.arena_radius
                neighbor_feats.extend(list(rel_pos) + [self.signaling[j]])

            obs = np.concatenate([norm_pos, dir_nest, [sensor_val], closest_dir, np.array(neighbor_feats)]).astype(
                np.float32)
            observations[agent] = obs
        return observations

    def step(self, actions):
        self.steps += 1
        rewards = {a: 0.0 for a in self.agents}
        terms = {a: False for a in self.agents}
        truncs = {a: False for a in self.agents}
        infos = {a: {} for a in self.agents}

        # Mover
        for idx, agent in enumerate(self.agents):
            if agent in actions:
                if self.signaling[idx] == 1.0: continue  # Travão no ninho
                move = np.clip(actions[agent], -1, 1) * 0.1
                self.agent_positions[idx] += move

        # Obstáculos
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

        # Ninho
        robots_in_nest = []
        for idx in range(self.num_agents):
            if np.linalg.norm(self.agent_positions[idx] - self.nest_pos) < (self.nest_radius + 0.1):
                robots_in_nest.append(idx)
                self.signaling[idx] = 1.0
                self.agent_positions[idx] = self.nest_pos.copy()
            else:
                self.signaling[idx] = 0.0

        self.current_nest_occupancy = len(robots_in_nest)

        if self.current_nest_occupancy >= self.required_to_eat:
            self.total_food_collected += 1
            self._spawn_nest()
            for idx in range(self.num_agents):
                if idx in robots_in_nest:
                    rewards[self.agents[idx]] += 500.0  # RECOMPENSA MASSIVA
                    self.agent_positions[idx] = self._random_spawn()
                    self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.signaling[idx] = 0.0

        # FÍSICA IMPLACÁVEL E RECOMPENSAS
        for idx, agent in enumerate(self.agents):
            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            # TERAPIA DE CHOQUE: Bateu na parede? Morre logo.
            if np.linalg.norm(self.agent_positions[idx]) > self.arena_radius:
                rewards[agent] -= 100.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                continue

            if self.signaling[idx] == 1.0:
                rewards[agent] += 1.0
            else:
                progress = self.prev_dist_to_nest[idx] - dist_nest
                rewards[agent] += progress * 50.0  # Bússola densa
                self.hunger_timers[idx] += 1

            self.prev_dist_to_nest[idx] = dist_nest

            if obstacle_hits[agent]: rewards[agent] -= 2.0

            if self.hunger_timers[idx] > 300:
                rewards[agent] -= 50.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            terms[agent] = self.steps >= self.max_steps

        return self._get_observations(), rewards, terms, truncs, infos

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]

    def render(self):
        if self.render_mode != "human": return
        if self.window is None:
            pygame.init()
            pygame.font.init()
            self.window = pygame.display.set_mode((800, 800))
            pygame.display.set_caption("Swarm Robotics: Terapia de Choque")
            self.font = pygame.font.SysFont("Consolas", 18, bold=True)

        self.window.fill((20, 25, 30))

        def to_screen(p):
            return (int((p[0] + self.arena_radius * 1.1) * self.scale),
                    int((-p[1] + self.arena_radius * 1.1) * self.scale))

        # Ninho
        pygame.draw.circle(self.window, (40, 200, 80), to_screen(self.nest_pos), int(self.nest_radius * self.scale))
        pygame.draw.circle(self.window, (255, 255, 255), to_screen(self.nest_pos), int(self.nest_radius * self.scale),
                           2)

        # Obstáculos
        for obs in self.obstacles:
            pygame.draw.circle(self.window, (100, 100, 110), to_screen(obs), int(self.obstacle_radius * self.scale))

        # Robôs
        for idx, p in enumerate(self.agent_positions):
            screen_pos = to_screen(p)
            if self.signaling[idx] == 1.0:
                pygame.draw.circle(self.window, (255, 215, 0), screen_pos, int(self.robot_radius * self.scale * 2), 2)
                pygame.draw.circle(self.window, (255, 215, 0), screen_pos, int(self.robot_radius * self.scale))
            else:
                pygame.draw.circle(self.window, (80, 150, 255), screen_pos, int(self.robot_radius * self.scale))

        pygame.display.flip()

    def close(self):
        if self.window is not None:
            pygame.quit()
            self.window = None