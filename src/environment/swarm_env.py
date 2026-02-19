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

        # --- REGRAS COOPERATIVAS (Nível Mestrado) ---
        self.required_to_eat = 3  # Quantos robôs são precisos para o ninho?
        self.deaths_count = 0  # Contador de falhas críticas
        self.total_food_collected = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # --- NOVO INPUT DE COMUNICAÇÃO ---
        # Próprio: 7 inputs (Posição(2), Ninho(2), Pedra(1), Dir_Pedra(2))
        # Vizinhos: 3 inputs cada (Rel_X, Rel_Y, SINAL_DE_ALERTA)
        obs_size = 7 + (self.num_agents - 1) * 3
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
        self.prev_dist_to_nest = np.zeros(self.num_agents)
        self.signaling = np.zeros(self.num_agents)  # Quem está a gritar "Encontrei!"?
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
        r = self.arena_radius * np.sqrt(np.random.uniform(0.0, 0.8))
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

            # COMUNICAÇÃO (Ouvir os vizinhos)
            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                rel_pos = (other_pos - pos) / self.arena_radius
                # Adicionamos o sinal do vizinho (1.0 se ele achou o ninho, 0.0 senão)
                neighbor_feats.extend(list(rel_pos) + [self.signaling[j]])

            obs = np.concatenate([
                norm_pos, dir_nest, [sensor_val], closest_dir, np.array(neighbor_feats)
            ]).astype(np.float32)

            observations[agent] = obs
        return observations

    def step(self, actions):
        self.steps += 1
        rewards = {a: 0.0 for a in self.agents}
        terms = {a: False for a in self.agents}
        truncs = {a: False for a in self.agents}
        infos = {a: {} for a in self.agents}

        # Drift Obstáculos
        if self.num_obstacles > 0:
            for i in range(len(self.obstacles)):
                drift = np.random.uniform(-0.02, 0.02, size=2)
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
                    self.agent_positions[idx] += direction * (min_dist - dist)

        # --- LÓGICA COOPERATIVA DO NINHO ---
        robots_in_nest = []
        for idx in range(self.num_agents):
            if np.linalg.norm(self.agent_positions[idx] - self.nest_pos) < (self.nest_radius + 0.1):
                robots_in_nest.append(idx)
                self.signaling[idx] = 1.0  # Acende o alerta para os outros!
            else:
                self.signaling[idx] = 0.0

        self.current_nest_occupancy = len(robots_in_nest)

        # Se houver robôs suficientes, o enxame come!
        if self.current_nest_occupancy >= self.required_to_eat:
            self.total_food_collected += 1
            self._spawn_nest()  # Ninho foge

            for idx in range(self.num_agents):
                if idx in robots_in_nest:
                    rewards[self.agents[idx]] += 150.0  # Recompensa MASSIVA por cooperar
                    self.agent_positions[idx] = self._random_spawn()
                    self.hunger_timers[idx] = 0
                else:
                    # Prémio global pequeno para incentivar o espírito de equipa
                    rewards[self.agents[idx]] += 10.0

                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.signaling[idx] = 0.0

        # Recompensas Contínuas (Progresso e Sobrevivência)
        for idx, agent in enumerate(self.agents):
            if np.linalg.norm(self.agent_positions[idx]) > self.arena_radius:
                self.agent_positions[idx] = np.clip(self.agent_positions[idx], -self.arena_radius, self.arena_radius)

            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            # Se ele está no ninho a espera de ajuda, não perde energia nem é castigado
            if self.signaling[idx] == 1.0:
                rewards[agent] += 0.5  # Pequeno bónus por manter a posição
                self.hunger_timers[idx] = max(0, self.hunger_timers[idx] - 1)  # Congela a fome
            else:
                # Progresso normal
                progress = self.prev_dist_to_nest[idx] - dist_nest
                rewards[agent] += progress * 100.0
                rewards[agent] -= 0.05  # Custo de andar
                self.hunger_timers[idx] += 1

            self.prev_dist_to_nest[idx] = dist_nest

            if obstacle_hits[agent]:
                rewards[agent] -= 0.5

                # Fome Extrema (Morte Simbólica)
            if self.hunger_timers[idx] > 300:
                rewards[agent] -= 15.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._random_spawn()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            terms[agent] = self.steps >= self.max_steps

        if self.render_mode == "human": self.render()
        return self._get_observations(), rewards, terms, truncs, infos

    def render(self):
        if self.window is None:
            pygame.init()
            pygame.font.init()
            self.window = pygame.display.set_mode((self.screen_size, self.screen_size))
            pygame.display.set_caption("Swarm Robotics: Cooperative Multi-Agent Foraging")
            self.font = pygame.font.SysFont("Consolas", 18, bold=True)
            self.title_font = pygame.font.SysFont("Consolas", 22, bold=True)

        self.window.fill((20, 25, 30))  # Fundo escuro académico

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
            pygame.draw.circle(self.window, (255, 80, 80), to_screen(obs), int(self.obstacle_radius * self.scale), 1)

        # Robôs
        for idx, p in enumerate(self.agent_positions):
            screen_pos = to_screen(p)

            # Se encontrou o ninho, brilha a Dourado (Sinalizador)
            if self.signaling[idx] == 1.0:
                # Efeito de Radar/Ondas de Rádio
                pygame.draw.circle(self.window, (255, 215, 0), screen_pos, int(self.robot_radius * self.scale * 3), 1)
                pygame.draw.circle(self.window, (255, 215, 0), screen_pos, int(self.robot_radius * self.scale))
            else:
                pygame.draw.line(self.window, (0, 100, 0), screen_pos, to_screen(self.nest_pos), 1)
                pygame.draw.circle(self.window, (80, 150, 255), screen_pos, int(self.robot_radius * self.scale))

        # --- HUD AVANÇADO ---
        overlay = pygame.Surface((280, 150))
        overlay.set_alpha(200)
        overlay.fill((10, 10, 15))
        self.window.blit(overlay, (10, 10))

        texts = [
            self.title_font.render("DASHBOARD DO ENXAME", True, (255, 215, 0)),
            self.font.render(f"Tempo: {self.steps}/{self.max_steps} steps", True, (200, 200, 200)),
            self.font.render(f"Robôs no Ninho: {self.current_nest_occupancy}/{self.required_to_eat}", True,
                             (50, 255, 50) if self.current_nest_occupancy > 0 else (200, 200, 200)),
            self.font.render(f"Comida Coletada: {self.total_food_collected}", True, (100, 200, 255)),
            self.font.render(f"Mortes (Fome): {self.deaths_count}", True, (255, 100, 100))
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