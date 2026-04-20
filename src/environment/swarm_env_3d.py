import gymnasium as gym
from gymnasium import spaces
import numpy as np
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

        self.num_agents = self.config['environment'].get('num_agents', 25)
        self.num_obstacles = self.config['environment'].get('num_obstacles', 50)
        self.dynamic_obstacles = self.config['environment'].get('dynamic_obstacles', True)
        self.arena_radius = self.config['environment'].get('arena_radius', 15.0)
        self.dynamic_nest = self.config['environment'].get('dynamic_nest', True)
        self.nest_velocity = np.zeros(3)

        self.nest_radius = self.config['environment']['nest_radius']
        self.max_steps = self.config['environment'].get('max_steps', 500)

        self.robot_radius = self.config['physics'].get('agent_radius', 0.15)
        self.obstacle_radius = 0.2
        self.obstacle_velocities = []

        self.required_to_eat = 3
        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        obs_size = 8 + (self.num_agents - 1) * 5
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

        self.nest_pos = np.array([0.0, 0.0, 0.0])
        self.obstacles = []
        self.walls = []
        self.prev_dist_to_nest = np.zeros(self.num_agents)
        self.signaling = np.zeros(self.num_agents)
        self.agent_headings = np.zeros((self.num_agents, 3))

    def _get_scenario_spawn_pos(self):
        if self.classic_scenario == "u_wall":
            return np.array([np.random.uniform(-3, 3), np.random.uniform(-4, 2), np.random.uniform(-0.5, 0.5)])
        elif self.classic_scenario == "bottleneck":
            return np.array([np.random.uniform(-8, 8), np.random.uniform(-12, -6), np.random.uniform(-0.5, 0.5)])
        elif self.classic_scenario == "four_rooms":
            return np.array([np.random.uniform(-12, -6), np.random.uniform(-12, -6), np.random.uniform(-0.5, 0.5)])
        else:
            return self._random_spawn()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0
        self.signaling = np.zeros(self.num_agents)
        self.walls = []

        self.classic_scenario = self.config['environment'].get('classic_scenario', 'none')

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

        else:
            self._spawn_nest()
            self._spawn_obstacles()
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])

        self.prev_dist_to_nest = np.array([np.linalg.norm(p - self.nest_pos) for p in self.agent_positions])
        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

        self.agent_headings = np.zeros((self.num_agents, 3))
        for i in range(self.num_agents):
            self.agent_headings[i] = np.array([1.0, 0.0, 0.0])

        return self._get_observations(), {}

    def _spawn_nest(self):
        self.nest_pos = self._random_spawn(max_radius=0.5)
        if self.dynamic_nest:
            vel = np.random.uniform(-1, 1, 3)
            self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * 0.015

    def _spawn_obstacles(self):
        self.obstacles = []
        self.obstacle_velocities = []
        for _ in range(self.num_obstacles):
            valid = False
            while not valid:
                pos = self._random_spawn(min_radius=0.5, max_radius=0.8)
                if np.linalg.norm(pos - self.nest_pos) > (self.nest_radius + self.obstacle_radius + 0.4):
                    self.obstacles.append(pos)
                    vel = np.random.uniform(-1, 1, 3)
                    vel /= (np.linalg.norm(vel) + 1e-6)
                    self.obstacle_velocities.append(vel * 0.02)
                    valid = True

    def _spawn_obstacles_bottleneck(self):
        self.obstacles = []
        self.obstacle_velocities = []

        # O buraco no centro vai exatamente de X = -0.2 a X = 0.2 (Largura total = 0.4)
        self.walls = [
            # Parede Esquerda (Tamanho 40, centro em -20.2 -> acaba em -0.2)
            {'pos': np.array([-20.2, 0.0, 0.0]), 'size': np.array([40.0, 8.0, 30.0])},
            # Parede Direita (Tamanho 40, centro em 20.2 -> começa em 0.2)
            {'pos': np.array([20.2, 0.0, 0.0]), 'size': np.array([40.0, 8.0, 30.0])}
        ]

    def _spawn_obstacles_maze(self):
        self.obstacles = []
        self.obstacle_velocities = []

        # LABIRINTO COM PORTAS APERTADAS E AFASTADAS
        # As portas (0.4 de largura) ficam encostadas aos limites da arena (perto do 14 e -14)

        self.walls = [
            # EIXO HORIZONTAL (Y=0)
            # Parede H Esquerda (X de -15 a -2.2)
            {'pos': np.array([-8.6, 0.0, 0.0]), 'size': np.array([12.8, 1.5, 30.0])},
            # Parede H Meio (Bloqueia o centro, X de -1.8 a 13.8) -> Porta de 0.4 em X=-2.0
            {'pos': np.array([6.0, 0.0, 0.0]), 'size': np.array([15.6, 1.5, 30.0])},
            # Parede H Direita (X de 14.2 a 15) -> Porta de 0.4 em X=14.0
            {'pos': np.array([14.6, 0.0, 0.0]), 'size': np.array([0.8, 1.5, 30.0])},

            # EIXO VERTICAL (X=0)
            # Parede V Fundo (Y de -15 a -14.2)
            {'pos': np.array([0.0, -14.6, 0.0]), 'size': np.array([1.5, 0.8, 30.0])},
            # Parede V Meio (Bloqueia o centro, Y de -13.8 a 1.8) -> Porta de 0.4 em Y=-14.0
            {'pos': np.array([0.0, -6.0, 0.0]), 'size': np.array([1.5, 15.6, 30.0])},
            # Parede V Topo (Y de 2.2 a 15) -> Porta de 0.4 em Y=2.0
            {'pos': np.array([0.0, 8.6, 0.0]), 'size': np.array([1.5, 12.8, 30.0])}
        ]

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
            heading = self.agent_headings[idx]

            F = heading
            W = np.array([0.0, 0.0, 1.0])
            if abs(np.dot(F, W)) > 0.99:
                W = np.array([0.0, 1.0, 0.0])

            R = np.cross(F, W)
            R /= (np.linalg.norm(R) + 1e-6)
            U = np.cross(R, F)

            def to_egocentric(target_pos):
                vec = target_pos - pos
                dist = np.linalg.norm(vec)
                if dist < 1e-6: return np.array([0.0, 0.0, 0.0]), 0.0
                dir_w = vec / dist
                return np.array([np.dot(dir_w, F), np.dot(dir_w, R), np.dot(dir_w, U)]), dist

            local_dir_nest, dist_nest = to_egocentric(self.nest_pos)
            norm_dist_nest = dist_nest / (self.arena_radius * 2)

            closest_dist = 5.0
            local_dir_obs = np.array([0.0, 0.0, 0.0])

            for obs in self.obstacles:
                local_dir, dist = to_egocentric(obs)
                d = dist - self.obstacle_radius - self.robot_radius
                if d < closest_dist:
                    closest_dist = d
                    local_dir_obs = local_dir

            for wall in self.walls:
                half_size = wall['size'] / 2.0
                closest_point = np.clip(pos, wall['pos'] - half_size, wall['pos'] + half_size)
                local_dir, dist = to_egocentric(closest_point)
                d = dist - self.robot_radius
                if d < closest_dist:
                    closest_dist = d
                    local_dir_obs = local_dir

            sensor_val = 1.0 - np.clip(closest_dist / 1.0, 0, 1.0)

            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                local_dir_neigh, dist_neigh = to_egocentric(other_pos)
                norm_dist_neigh = dist_neigh / (self.arena_radius * 2)
                neighbor_feats.extend(list(local_dir_neigh) + [norm_dist_neigh, self.signaling[j]])

            obs = np.concatenate([
                local_dir_nest, [norm_dist_nest],
                local_dir_obs, [sensor_val],
                np.array(neighbor_feats)
            ]).astype(np.float32)

            observations[agent] = obs
        return observations

    def step(self, actions):
        self.steps += 1
        rewards = {a: 0.0 for a in self.agents}
        terms = {a: False for a in self.agents}
        truncs = {a: False for a in self.agents}
        infos = {a: {} for a in self.agents}

        if self.dynamic_nest and self.classic_scenario == "none":
            self.nest_pos += self.nest_velocity
            if np.linalg.norm(self.nest_pos) > (self.arena_radius - self.nest_radius):
                dir_center = -self.nest_pos
                noise = np.random.uniform(-0.2, 0.2, 3)
                new_vel = dir_center + noise
                self.nest_velocity = (new_vel / (np.linalg.norm(new_vel) + 1e-6)) * 0.015

        if self.dynamic_obstacles and self.classic_scenario == "none":
            for i in range(len(self.obstacles)):
                self.obstacles[i] += self.obstacle_velocities[i]
                if np.linalg.norm(self.obstacles[i]) > (self.arena_radius - self.obstacle_radius):
                    dir_center = -self.obstacles[i]
                    dir_center /= (np.linalg.norm(dir_center) + 1e-6)
                    noise = np.random.uniform(-0.2, 0.2, 3)
                    new_vel = dir_center + noise
                    self.obstacle_velocities[i] = (new_vel / (np.linalg.norm(new_vel) + 1e-6)) * 0.02

        for idx, agent in enumerate(self.agents):
            if agent in actions:
                if self.signaling[idx] == 1.0: continue
                move_local = np.clip(actions[agent], -1, 1) * 0.2

                F = self.agent_headings[idx]
                W = np.array([0.0, 0.0, 1.0])
                if abs(np.dot(F, W)) > 0.99: W = np.array([0.0, 1.0, 0.0])
                R = np.cross(F, W)
                R /= (np.linalg.norm(R) + 1e-6)
                U = np.cross(R, F)

                move_global = move_local[0] * F + move_local[1] * R + move_local[2] * U

                if np.linalg.norm(move_global) > 1e-5:
                    self.agent_headings[idx] = move_global / np.linalg.norm(move_global)

                self.agent_positions[idx] += move_global

        obstacle_hits = {a: 0 for a in self.agents}
        for idx, agent in enumerate(self.agents):

            # 1. Colisões com esferas normais
            for obs_pos in self.obstacles:
                dist = np.linalg.norm(self.agent_positions[idx] - obs_pos)
                min_dist = self.robot_radius + self.obstacle_radius
                if dist < min_dist:
                    obstacle_hits[agent] = 1
                    direction = self.agent_positions[idx] - obs_pos
                    norm = np.linalg.norm(direction)
                    if norm > 0: direction /= norm
                    self.agent_positions[idx] += direction * (min_dist - dist)

            # 2. NOVA LÓGICA DE COLISÃO AABB ROBUSTA PARA PAREDES
            for wall in self.walls:
                delta = self.agent_positions[idx] - wall['pos']
                abs_delta = np.abs(delta)
                half_size = wall['size'] / 2.0

                # Calcular o nível de penetração em X, Y e Z
                penetration = (half_size + self.robot_radius) - abs_delta

                # Se penetrou positivamente nos 3 eixos, está a colidir ou a tentar atravessar!
                if np.all(penetration > 0):
                    obstacle_hits[agent] = 1

                    # Ejetar pelo caminho mais curto (eixo com menor penetração)
                    min_axis = np.argmin(penetration)

                    sign = np.sign(delta[min_axis])
                    if sign == 0: sign = 1.0

                    self.agent_positions[idx][min_axis] += penetration[min_axis] * sign

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
            if self.classic_scenario == "none":
                self._spawn_nest()
            for idx in range(self.num_agents):
                if idx in robots_in_nest:
                    rewards[self.agents[idx]] += 500.0
                    self.agent_positions[idx] = self._get_scenario_spawn_pos()
                    self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                self.signaling[idx] = 0.0

        for idx, agent in enumerate(self.agents):
            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            if np.linalg.norm(self.agent_positions[idx]) > self.arena_radius:
                rewards[agent] -= 100.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._get_scenario_spawn_pos()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                continue

            if self.signaling[idx] == 1.0:
                pass
            else:
                progress = self.prev_dist_to_nest[idx] - dist_nest
                rewards[agent] += progress * 50.0
                self.hunger_timers[idx] += 1

            self.prev_dist_to_nest[idx] = dist_nest

            if obstacle_hits[agent]: rewards[agent] -= 2.0

            if self.hunger_timers[idx] > 600:
                rewards[agent] -= 50.0
                self.deaths_count += 1
                self.agent_positions[idx] = self._get_scenario_spawn_pos()
                self.hunger_timers[idx] = 0
                self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            terms[agent] = self.steps >= self.max_steps

        return self._get_observations(), rewards, terms, truncs, infos

    def action_space(self, agent):
        return self.action_spaces[agent]

    def observation_space(self, agent):
        return self.observation_spaces[agent]