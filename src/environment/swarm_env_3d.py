import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame
import yaml
import os


class SwarmForagingEnv3D(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, config_path=None):
        super(SwarmForagingEnv3D, self).__init__()

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
        self.num_obstacles = 10

        # --- REGRAS COOPERATIVAS (Iguais ao 2D vencedor) ---
        self.required_to_eat = 3
        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        # --- AÇÕES E OBSERVAÇÕES 3D ---
        # 3 Motores: X, Y, Z
        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        # 10 inputs próprios + (N-1)*4 inputs vizinhos
        obs_size = 10 + (self.num_agents - 1) * 4
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.render_mode = None
        self.window = None
        self.screen_size = 800
        self.fov = 5.0
        self.scale = self.screen_size / 3.0

        self.nest_pos = np.array([0.0, 0.0, 0.0])
        self.obstacles = []
        self.prev_dist_to_nest = np.zeros(self.num_agents)
        self.signaling = np.zeros(self.num_agents)

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
        self.nest_pos = self._random_spawn(max_radius=0.5)

    def _spawn_obstacles(self):
        self.obstacles = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                pos = self._random_spawn(min_radius=0.5, max_radius=0.8)
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.4):
                    self.obstacles.append(pos)
                    valid = True

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

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]
            norm_pos = pos / self.arena_radius
            dist_nest = np.linalg.norm(pos - self.nest_pos)
            dir_nest = (self.nest_pos - pos) / (dist_nest + 1e-6)

            closest_dist = 5.0
            closest_dir = np.array([0.0, 0.0, 0.0])
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

        # Mover Drones 3D
        for idx, agent in enumerate(self.agents):
            if agent in actions:
                if self.signaling[idx] == 1.0: continue  # Travão no ninho
                move = np.clip(actions[agent], -1, 1) * 0.1
                self.agent_positions[idx] += move

        # FÍSICA: Colisões 3D
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

        # LÓGICA COOPERATIVA DO NINHO
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
                    rewards[self.agents[idx]] += 500.0  # RECOMPENSA MASSIVA (Terapia de Choque)
                    self.agent_positions[idx] = self._random_spawn()
                    self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.signaling[idx] = 0.0

        # FÍSICA IMPLACÁVEL E RECOMPENSAS (A Guilhotina)
        for idx, agent in enumerate(self.agents):
            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            # TERAPIA DE CHOQUE: Bateu na "parede" esférica do céu? Morre logo.
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

    # --- MOTOR DE RENDERIZAÇÃO FAKE 3D (Sombras e Shading) ---
    def render(self):
        if self.render_mode != "human": return
        if self.window is None:
            pygame.init()
            pygame.font.init()
            self.window = pygame.display.set_mode((self.screen_size, self.screen_size))
            pygame.display.set_caption("Swarm Robotics: 3D Drones (Terapia de Choque)")
            self.font = pygame.font.SysFont("Consolas", 18, bold=True)
            self.title_font = pygame.font.SysFont("Consolas", 22, bold=True)

        # Céu e Chão
        self.window.fill((20, 25, 35))
        pygame.draw.rect(self.window, (15, 20, 25), (0, self.screen_size // 2, self.screen_size, self.screen_size // 2))

        entities = []
        entities.append({"type": "nest", "pos": self.nest_pos, "radius": self.nest_radius, "color": (50, 220, 100)})
        for obs in self.obstacles:
            entities.append({"type": "obstacle", "pos": obs, "radius": self.obstacle_radius, "color": (120, 120, 130)})
        for idx, pos in enumerate(self.agent_positions):
            entities.append({"type": "robot", "pos": pos, "radius": self.robot_radius, "idx": idx,
                             "signaling": self.signaling[idx]})

        # Algoritmo do Pintor (Z-Sort)
        entities.sort(key=lambda e: e["pos"][2])
        floor_y = -self.arena_radius

        for e in entities:
            x, y, z = e["pos"]
            z_shifted = z + self.arena_radius + self.fov
            factor = self.fov / max(0.1, z_shifted)

            screen_x = int((x * factor * self.scale) + self.screen_size / 2)
            screen_y = int((-y * factor * self.scale) + self.screen_size / 2)
            projected_radius = max(2, int(e["radius"] * factor * self.scale))
            shadow_y_screen = int((-floor_y * factor * self.scale) + self.screen_size / 2)
            fog = np.clip(factor * 0.9, 0.2, 1.0)

            # Sombras e Tethers
            if y > floor_y:
                shadow_w = int(projected_radius * 1.5)
                shadow_h = max(2, int(projected_radius * 0.5))
                shadow_rect = pygame.Rect(screen_x - shadow_w // 2, shadow_y_screen - shadow_h // 2, shadow_w, shadow_h)
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, int(150 * fog)), (0, 0, shadow_w, shadow_h))
                self.window.blit(shadow_surf, shadow_rect.topleft)
                pygame.draw.line(self.window, (100, 100, 100), (screen_x, screen_y), (screen_x, shadow_y_screen), 1)

            # Shading 3D
            if e["type"] == "nest":
                base_color = tuple(int(col * fog) for col in e["color"])
                pygame.draw.circle(self.window, base_color, (screen_x, screen_y), projected_radius)
                pygame.draw.circle(self.window, (255, 255, 255), (screen_x, screen_y), int(projected_radius * 0.8), 2)
            elif e["type"] == "obstacle":
                base_color = tuple(int(col * fog) for col in e["color"])
                highlight = tuple(min(255, int(col * fog * 1.5)) for col in e["color"])
                pygame.draw.circle(self.window, base_color, (screen_x, screen_y), projected_radius)
                pygame.draw.circle(self.window, highlight,
                                   (screen_x - projected_radius // 4, screen_y - projected_radius // 4),
                                   int(projected_radius * 0.6))
            elif e["type"] == "robot":
                nx, ny, nz = self.nest_pos
                nz_shifted = nz + self.arena_radius + self.fov
                n_factor = self.fov / max(0.1, nz_shifted)
                n_screen_x = int((nx * n_factor * self.scale) + self.screen_size / 2)
                n_screen_y = int((-ny * n_factor * self.scale) + self.screen_size / 2)

                if e["signaling"] == 1.0:
                    pygame.draw.circle(self.window, (255, 215, 0), (screen_x, screen_y), projected_radius * 2, 1)
                    pygame.draw.circle(self.window, tuple(int(c * fog) for c in (255, 215, 0)), (screen_x, screen_y),
                                       projected_radius)
                else:
                    pygame.draw.line(self.window, (0, int(80 * fog), 0), (screen_x, screen_y), (n_screen_x, n_screen_y),
                                     1)
                    pygame.draw.circle(self.window, tuple(int(c * fog) for c in (50, 100, 200)), (screen_x, screen_y),
                                       projected_radius)
                    pygame.draw.circle(self.window, tuple(int(c * fog) for c in (100, 180, 255)),
                                       (screen_x - max(1, projected_radius // 4),
                                        screen_y - max(1, projected_radius // 4)), int(projected_radius * 0.5))

        overlay = pygame.Surface((280, 150))
        overlay.set_alpha(220)
        overlay.fill((10, 12, 18))
        self.window.blit(overlay, (10, 10))

        texts = [
            self.title_font.render("DASHBOARD 3D DRONES", True, (255, 215, 0)),
            self.font.render(f"Tempo: {self.steps}/{self.max_steps} steps", True, (200, 200, 200)),
            self.font.render(f"Drones no Ninho: {self.current_nest_occupancy}/{self.required_to_eat}", True,
                             (50, 255, 50) if self.current_nest_occupancy > 0 else (200, 200, 200)),
            self.font.render(f"Comida Coletada: {self.total_food_collected}", True, (100, 200, 255)),
            self.font.render(f"Mortes (Fome/Queda): {self.deaths_count}", True, (255, 100, 100))
        ]
        for i, txt in enumerate(texts):
            self.window.blit(txt, (20, 20 + i * 25))

        pygame.display.flip()

    def close(self):
        if self.window: pygame.quit()

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]