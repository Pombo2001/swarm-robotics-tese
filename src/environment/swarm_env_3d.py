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

        rewards_config = self.config.get('rewards', {})
        self.energy_cost = rewards_config.get('energy_cost', -0.05)
        self.food_collected_reward = rewards_config.get('food_collected', 100.0)

        self.deaths_count = 0
        self.total_food_collected = 0
        self.current_nest_occupancy = 0

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]

        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        obs_size = 12 + (self.num_agents - 1) * 5
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
        max_attempts = 50
        for _ in range(max_attempts):
            if self.classic_scenario == "u_wall":
                # Spawn SOUTH of the U legs (legs start at y=-5).
                # Agents approach from below, enter the bowl, hit the top bar, must find bypass.
                pos = np.array([np.random.uniform(-10, 10), np.random.uniform(-12, -6), 0.0])
            elif self.classic_scenario == "bottleneck":
                # OESTE do muro vertical (x=0, gap a y=2..6)
                # x de -12 a -3 (oeste), y de -7 a 7 (cobre a altura do gap)
                pos = np.array([np.random.uniform(-12, -3), np.random.uniform(-7, 7), 0.0])
            elif self.classic_scenario == "four_rooms":
                # SW quadrant, bounded to stay inside circular arena (r≤15)
                # Original (-13,-13) corner had distance ≈18 > 15 → out of bounds
                pos = np.array([np.random.uniform(-10, -2), np.random.uniform(-10, -2), 0.0])
            elif self.classic_scenario == "cooperative_door":
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
            # Ninho a ESTE do muro vertical (x=0), perto do gap (y=2..6)
            self.nest_pos = np.array([10.0, 4.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self._spawn_obstacles_bottleneck()  # spawna as paredes antes do spawn dos agentes
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])

        elif self.classic_scenario == "four_rooms":
            # Ninho na sala NE (x>0, y>0), longe das paredes
            self.nest_pos = np.array([9.0, 9.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self._spawn_obstacles_maze()  # paredes antes do spawn dos agentes
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])

        elif self.classic_scenario == "cooperative_door":
            # Nest is north of the horizontal barrier (barrier at y=0, nest at y=12)
            self.nest_pos = np.array([0.0, 12.0, 0.0])
            self.nest_velocity = np.zeros(3)
            self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
            self._spawn_obstacles_cooperative_door()

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

        self.prev_dist_to_nest = np.array([np.linalg.norm(p - self.nest_pos) for p in self.agent_positions])
        self.hunger_timers = np.zeros(self.num_agents, dtype=int)

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
        # Barreira VERTICAL (N-S) em x=0. Passagem de 4m deslocada para norte.
        # Antes: dois muros horizontais enormes (x=±20) com gap de 1.5m ao centro
        #        → layout idêntico à porta cooperativa. Sem distinção visual.
        # Agora: muro vertical com gap a y=2..6 (norte do centro).
        #   Agentes spawn a OESTE (x<0), ninho a ESTE (x=10, y=4).
        #   Todos devem encontrar o gap offset e passar sem colisão mútua.
        self.walls = [
            # Segmento sul do muro vertical: y=-15 a y=2
            {'pos': np.array([0.0, -6.5, 0.0]), 'size': np.array([2.0, 17.0, 30.0])},
            # Segmento norte do muro vertical: y=6 a y=15
            {'pos': np.array([0.0, 10.5, 0.0]), 'size': np.array([2.0,  9.0, 30.0])},
        ]
        # Gap: y=2 a y=6 (4m, deslocado para norte)

    def _spawn_obstacles_maze(self):
        self.obstacles = []
        self.obstacle_velocities = []
        # Quatro Salas (Sutton & Barto, 1999) adaptado para arena de raio 15m.
        # Cruz de paredes com 4 passagens — uma por par de salas adjacentes:
        #
        #   Parede H (y=0): gap em x=-6..-3  (sala SW↔NW, esquerda do centro)
        #                   gap em x= 3.. 6  (sala SE↔NE, direita do centro)
        #   Parede V (x=0): gap em y=-6..-3  (sala SW↔SE, abaixo do centro)
        #                   gap em y= 3.. 6  (sala NW↔NE, acima do centro)
        #
        # Ninho em NE (10, 10), spawn em SW (-10..-4, -10..-4).
        # Caminho óptimo: SW → SE (gap V, y≈-4.5) → NE (gap H, x≈4.5).
        #             ou: SW → NW (gap H, x≈-4.5) → NE (gap V, y≈4.5).
        self.walls = [
            # Parede H (y=0) — 3 segmentos, 2 gaps
            {'pos': np.array([-10.5,  0.0, 0.0]), 'size': np.array([ 9.0, 2.0, 30.0])},  # x=-15..-6
            {'pos': np.array([  0.0,  0.0, 0.0]), 'size': np.array([ 6.0, 2.0, 30.0])},  # x= -3..3
            {'pos': np.array([ 10.5,  0.0, 0.0]), 'size': np.array([ 9.0, 2.0, 30.0])},  # x=  6..15
            # Parede V (x=0) — 3 segmentos, 2 gaps
            {'pos': np.array([0.0, -10.5, 0.0]), 'size': np.array([2.0,  9.0, 30.0])},   # y=-15..-6
            {'pos': np.array([0.0,   0.0, 0.0]), 'size': np.array([2.0,  6.0, 30.0])},   # y= -3..3
            {'pos': np.array([0.0,  10.5, 0.0]), 'size': np.array([2.0,  9.0, 30.0])},   # y=  6..15
        ]

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
        self.door_active = True
        self.door_pos  = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.door_size = np.array([3.0, 2.0, 30.0])   # 3m wide door at center
        self.door_wall_index = len(self.walls)
        self.walls.append({'pos': self.door_pos.copy(), 'size': self.door_size})

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

            # ---------------- LiDAR RAYCASTING (8 Rays) ----------------
            num_rays = 8
            ray_angles = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)
            max_ray_dist = 5.0
            lidar_sensor_vals = np.zeros(num_rays, dtype=np.float32)

            # Project heading to horizontal plane for LiDAR to ensure robust wall detection even if pitching
            F_horiz = np.array([F[0], F[1], 0.0])
            if np.linalg.norm(F_horiz) < 1e-6:
                F_horiz = np.array([1.0, 0.0, 0.0])
            else:
                F_horiz /= np.linalg.norm(F_horiz)
            R_horiz = np.array([-F_horiz[1], F_horiz[0], 0.0])

            for i, angle in enumerate(ray_angles):
                # Calculate global direction of the ray based on robot's horizontal heading
                ray_dir = np.cos(angle) * F_horiz + np.sin(angle) * R_horiz
                ray_end = pos + ray_dir * max_ray_dist
                
                closest_dist = max_ray_dist
                
                # Check intersection with walls (AABB)
                for wall in self.walls:
                    half_size = wall['size'] / 2.0
                    w_min = wall['pos'] - half_size
                    w_max = wall['pos'] + half_size
                    
                    t_min = 0.0
                    t_max = 1.0
                    
                    for axis in range(2): # Only X and Y
                        d = ray_end[axis] - pos[axis]
                        if abs(d) < 1e-6:
                            if pos[axis] < w_min[axis] or pos[axis] > w_max[axis]:
                                t_max = -1.0
                                break
                        else:
                            t1 = (w_min[axis] - pos[axis]) / d
                            t2 = (w_max[axis] - pos[axis]) / d
                            if t1 > t2:
                                t1, t2 = t2, t1
                            t_min = max(t_min, t1)
                            t_max = min(t_max, t2)
                            
                    if t_max >= t_min and t_max >= 0.0 and t_min <= 1.0:
                        hit_dist = t_min * max_ray_dist
                        if hit_dist < closest_dist:
                            closest_dist = hit_dist
                            
                # Check intersection with moving obstacles
                for obs in self.obstacles:
                    vec = obs - pos
                    proj = np.dot(vec, ray_dir)
                    if proj > 0:
                        perp_dist = np.linalg.norm(vec - proj * ray_dir)
                        if perp_dist <= self.obstacle_radius:
                            hit_dist = proj - np.sqrt(self.obstacle_radius**2 - perp_dist**2)
                            if hit_dist > 0 and hit_dist < closest_dist:
                                closest_dist = hit_dist

                # Normalize lidar: 1.0 means crash, 0.0 means free path
                lidar_sensor_vals[i] = 1.0 - (closest_dist / max_ray_dist)

            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                local_dir_neigh, dist_neigh = to_egocentric(other_pos)
                norm_dist_neigh = dist_neigh / (self.arena_radius * 2)
                neighbor_feats.extend(list(local_dir_neigh) + [norm_dist_neigh, self.signaling[j]])

            obs = np.concatenate([
                local_dir_nest, [norm_dist_nest],
                lidar_sensor_vals,
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
                        
                if np.linalg.norm(move_global) > 1e-5:
                    self.agent_headings[idx] = move_global / np.linalg.norm(move_global)

                self.agent_positions[idx] += move_global

        if self.classic_scenario == "cooperative_door" and getattr(self, 'door_active', False):
            pushing_robots = []
            for i in range(self.num_agents):
                pos = self.agent_positions[i]
                # Push zone: directly south of the door (x -1.5 to 1.5, y -2 to 0)
                if -1.5 < pos[0] < 1.5 and -2.0 < pos[1] < 0.0:
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
                        rewards[self.agents[idx]] += self.food_collected_reward
                        self.agent_positions[idx] = self._get_scenario_spawn_pos()
                        self.hunger_timers[idx] = 0
                    self.prev_dist_to_nest[idx] = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)
                    self.signaling[idx] = 0.0

        for idx, agent in enumerate(self.agents):
            dist_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            if np.linalg.norm(self.agent_positions[idx]) > (self.arena_radius - self.robot_radius):
                direction = -self.agent_positions[idx]
                direction /= (np.linalg.norm(direction) + 1e-6)
                self.agent_positions[idx] += direction * 0.5
                obstacle_hits[agent] = 1
                continue

            if self.signaling[idx] == 1.0:
                pass
            else:
                # ── Reward Structure ─────────────────────────────────────────
                # NOTA: NÃO há ICM (Intrinsic Curiosity Module).
                # A exploração é incentivada exclusivamente por reward shaping:
                #
                #   progress_reward = factor × (dist_t-1 − dist_t)
                #     → positivo se o agente se aproximou do ninho
                #     → negativo se se afastou (desincentiva desvios)
                #     → funciona como "Potential-Based Reward Shaping"
                #        (Ng et al., 1999) — não altera a política óptima
                #
                #   energy_cost = −0.05/passo
                #     → pressão temporal para resolver a tarefa depressa
                #
                # Recompensa de tarefa pura (sem shaping):
                #   food_collected_reward = +100 (quando required_to_eat
                #   agentes chegam simultaneamente ao ninho)
                # ─────────────────────────────────────────────────────────────
                progress = self.prev_dist_to_nest[idx] - dist_nest
                rewards[agent] += (progress * self.progress_reward_factor) + self.energy_cost
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