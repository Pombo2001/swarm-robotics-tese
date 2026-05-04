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
        self.obstacle_radius = env_config.get('obstacle_radius', 0.2)
        self.obstacle_velocity_magnitude = env_config.get('obstacle_velocity', 0.02)
        self.obstacle_velocities = []

        self.required_to_eat = env_config.get('required_to_eat', 3)
        self.hunger_timer_max = env_config.get('hunger_timer_max', 600)
        self.progress_reward_factor = env_config.get('progress_reward_factor', 50.0)
        self.obstacle_penalty = env_config.get('obstacle_penalty', -2.0)

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
        elif self.classic_scenario == "cooperative_door":
            return np.array([-10 + np.random.uniform(-2, 2), np.random.uniform(-4, 4), np.random.uniform(-0.5, 0.5)])
        elif self.classic_scenario == "cooperative_perception":
            # Espalhados pela arena toda
            return self._random_spawn()
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

        elif self.classic_scenario == "cooperative_door":
            self.nest_pos = np.array([12.0, 0.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_cooperative_door()

        elif self.classic_scenario == "cooperative_perception":
            # O "ninho" é o Alvo Móvel neste cenário
            self.nest_pos = self._random_spawn(max_radius=0.7)
            vel = np.random.uniform(-1, 1, 3)
            vel[2] = 0.0
            self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self.obstacles = []
            self.obstacle_velocities = []

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
            self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude

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
                    self.obstacle_velocities.append(vel * self.obstacle_velocity_magnitude)
                    valid = True

    def _spawn_obstacles_u_wall(self):
        self.obstacles = []
        self.obstacle_velocities = []
        self.walls = [
            {'pos': np.array([0.0, 5.0, 0.0]), 'size': np.array([20.0, 2.0, 30.0])},
            {'pos': np.array([-9.0, 0.0, 0.0]), 'size': np.array([2.0, 10.0, 30.0])},
            {'pos': np.array([9.0, 0.0, 0.0]), 'size': np.array([2.0, 10.0, 30.0])}
        ]

    def _spawn_obstacles_bottleneck(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # PORTAS À JUSTA: Para um diâmetro de robot de 0.3m, a porta tem exatamente 0.35m de largura.
        self.walls = [
            {'pos': np.array([-20.175, 0.0, 0.0]), 'size': np.array([40.0, 8.0, 30.0])},
            {'pos': np.array([20.175, 0.0, 0.0]), 'size': np.array([40.0, 8.0, 30.0])}
        ]

    def _spawn_obstacles_maze(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # LABIRINTO À JUSTA: Passagens estreitas de 0.35m encostadas às paredes exteriores.
        self.walls = [
            # Eixo Horizontal Y=0
            {'pos': np.array([-12.5875, 0.0, 0.0]), 'size': np.array([4.825, 1.5, 30.0])},
            {'pos': np.array([0.0, 0.0, 0.0]), 'size': np.array([19.65, 1.5, 30.0])},
            {'pos': np.array([12.5875, 0.0, 0.0]), 'size': np.array([4.825, 1.5, 30.0])},
            
            # Eixo Vertical X=0
            {'pos': np.array([0.0, -12.5875, 0.0]), 'size': np.array([1.5, 4.825, 30.0])},
            {'pos': np.array([0.0, -5.2875, 0.0]), 'size': np.array([1.5, 9.075, 30.0])},
            {'pos': np.array([0.0, 5.2875, 0.0]), 'size': np.array([1.5, 9.075, 30.0])},
            {'pos': np.array([0.0, 12.5875, 0.0]), 'size': np.array([1.5, 4.825, 30.0])}
        ]

    def _spawn_obstacles_cooperative_door(self):
        self.obstacles = []
        self.obstacle_velocities = []

        self.walls = [
            {'pos': np.array([0.0, 8.0, 0.0]), 'size': np.array([2.0, 12.0, 30.0])},
            {'pos': np.array([0.0, -8.0, 0.0]), 'size': np.array([2.0, 12.0, 30.0])}
        ]

        self.door_active = True
        self.door_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.door_size = np.array([2.0, 4.0, 30.0])

        self.door_wall_index = len(self.walls)
        self.walls.append({'pos': self.door_pos, 'size': self.door_size})

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

    def _has_line_of_sight(self, p1, p2):
        for t in np.linspace(0.1, 0.9, 10):
            point = p1 + t * (p2 - p1)
            for wall in self.walls:
                half_size = wall['size'] / 2.0
                if np.all(np.abs(point - wall['pos']) < half_size):
                    return False
        return True

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

            if not self._has_line_of_sight(pos, self.nest_pos):
                local_dir_nest = np.array([0.0, 0.0, 0.0])
                norm_dist_nest = 1.0

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
                self.nest_velocity = (new_vel / (np.linalg.norm(new_vel) + 1e-6)) * self.nest_velocity_magnitude

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
                new_vel[2] = 0
                self.nest_velocity = (new_vel / (np.linalg.norm(new_vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
            
            observing_robots = []
            angles = []
            for i in range(self.num_agents):
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
                    vel[2] = 0.0
                    self.nest_velocity = (vel / (np.linalg.norm(vel) + 1e-6)) * self.nest_velocity_magnitude * 2.0
        # --------------------------------------

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

        if self.classic_scenario == "cooperative_door" and getattr(self, 'door_active', False):
            pushing_robots = []
            for i in range(self.num_agents):
                pos = self.agent_positions[i]
                if -1.5 < pos[0] < 0.0 and -2.0 < pos[1] < 2.0:
                    pushing_robots.append(i)

            if len(pushing_robots) >= 3:
                self.door_active = False
                for idx in pushing_robots:
                    rewards[self.agents[idx]] += 100.0
                self.walls[self.door_wall_index]['pos'] = np.array([999.0, 999.0, 999.0], dtype=np.float32)

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

        robots_in_nest = []
        for idx in range(self.num_agents):
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
                rewards[agent] += progress * self.progress_reward_factor
                self.hunger_timers[idx] += 1

            self.prev_dist_to_nest[idx] = dist_nest

            if obstacle_hits[agent]: rewards[agent] += self.obstacle_penalty

            if self.hunger_timers[idx] > self.hunger_timer_max:
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