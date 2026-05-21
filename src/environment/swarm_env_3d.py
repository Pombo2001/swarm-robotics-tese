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
        self.num_agents = env_config.get('num_agents', 20)
        self.arena_radius = env_config.get('arena_radius', 15.0)
        self.max_steps = env_config.get('max_steps', 1000)
        self.robot_radius = env_config.get('robot_radius', 0.25)
        
        self.stagnation_threshold = 50
        self.stagnation_penalty = -1.0
        self.stagnation_area = 0.1
        self.obstacle_penalty = env_config.get('obstacle_penalty', -1.0)

        self.agents = [f"robot_{i}" for i in range(self.num_agents)]
        self.action_space_val = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        self.sensor_directions = self._generate_sensor_directions(8)
        obs_size = 3 + 1 + len(self.sensor_directions) + 3 + 1 + 8 + 1 + (self.num_agents - 1) * 5
        self.observation_space_val = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)

        self.action_spaces = {a: self.action_space_val for a in self.agents}
        self.observation_spaces = {a: self.observation_space_val for a in self.agents}

    def _generate_sensor_directions(self, num_sensors):
        angles = np.linspace(0, 2 * np.pi, num_sensors, endpoint=False)
        return np.array([[np.cos(a), np.sin(a), 0] for a in angles])

    def _is_colliding(self, pos, return_normal=False):
        if np.linalg.norm(pos) > self.arena_radius - self.robot_radius:
            normal = -pos / (np.linalg.norm(pos) + 1e-6)
            return (True, normal) if return_normal else True
        for wall in self.walls:
            closest_point = np.clip(pos, wall['pos'] - wall['size'] / 2.0, wall['pos'] + wall['size'] / 2.0)
            if np.linalg.norm(pos - closest_point) < self.robot_radius:
                normal = pos - closest_point
                if np.linalg.norm(normal) > 1e-6:
                    normal /= np.linalg.norm(normal)
                return (True, normal) if return_normal else True
        return (False, np.zeros(3)) if return_normal else False

    def _get_scenario_spawn_pos(self):
        while True:
            if self.classic_scenario == "u_wall":
                pos = np.array([np.random.uniform(-3.5, 3.5), np.random.uniform(-4, 0), 0.0])
            elif self.classic_scenario == "cooperative_door":
                pos = np.array([np.random.uniform(-14, -2), np.random.uniform(-14, 14), 0.0])
            else:
                pos = np.array([np.random.uniform(-self.arena_radius*0.8, self.arena_radius*0.8), np.random.uniform(-self.arena_radius*0.8, self.arena_radius*0.8), 0.0])
            
            if not self._is_colliding(pos):
                return pos

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        self.walls = []
        self.obstacles = []
        self.classic_scenario = self.config['environment'].get('classic_scenario', 'none')
        
        if self.classic_scenario == "u_wall":
            self.nest_pos = np.array([0.0, 10.0, 0.0])
            self.walls = [{'pos':np.array([0,3,0]),'size':np.array([8,1.5,15])},{'pos':np.array([-3.25,1,0]),'size':np.array([1.5,5,15])},{'pos':np.array([3.25,1,0]),'size':np.array([1.5,5,15])}]
        elif self.classic_scenario == "cooperative_door":
            self.nest_pos = np.array([12.0, 0.0, 0.0])
            self.door_active = True
            self.door_pos = np.array([0.0, 0.0, 0.0])
            self.door_size = np.array([2.0, 4.0, 15.0])
            self.walls = [{'pos':np.array([0,8,0]),'size':np.array([2,12,15])},{'pos':np.array([0,-8,0]),'size':np.array([2,12,15])}]
            self.door_wall_index = len(self.walls)
            self.walls.append({'pos': self.door_pos, 'size': self.door_size})
        else:
            self.nest_pos = np.array([np.random.uniform(-self.arena_radius*0.5, self.arena_radius*0.5), np.random.uniform(-self.arena_radius*0.5, self.arena_radius*0.5), 0.0])

        self.agent_positions = np.array([self._get_scenario_spawn_pos() for _ in range(self.num_agents)])
        self.agent_headings = np.array([[1.0, 0.0, 0.0] for _ in range(self.num_agents)])
        self.min_dist_to_nest = np.linalg.norm(self.agent_positions - self.nest_pos, axis=1)
        
        self.stagnation_counters = np.zeros(self.num_agents, dtype=int)
        self.last_positions = self.agent_positions.copy()

        return self._get_observations(), {}

    def _get_observations(self):
        observations = {}
        for idx, agent in enumerate(self.agents):
            pos = self.agent_positions[idx]
            F = self.agent_headings[idx]
            R = np.cross(F, np.array([0,0,1])); R /= np.linalg.norm(R) + 1e-6
            U = np.cross(R, F)

            def to_egocentric(target):
                vec = target - pos
                dist = np.linalg.norm(vec)
                return (np.array([np.dot(vec,F),np.dot(vec,R),np.dot(vec,U)])/(dist+1e-6), dist/self.arena_radius) if dist > 1e-6 else (np.zeros(3), 0)

            local_dir_nest, norm_dist_nest = to_egocentric(self.nest_pos)
            
            door_state = 1.0 if self.classic_scenario == "cooperative_door" and self.door_active else 0.0
            local_dir_door, norm_dist_door = to_egocentric(self.door_pos) if door_state > 0 else (np.zeros(3), 1.0)

            sensor_vals = np.ones(len(self.sensor_directions))
            for i, s_dir in enumerate(self.sensor_directions):
                pass

            neighbor_feats = []
            for j, other_pos in enumerate(self.agent_positions):
                if idx == j: continue
                _, norm_dist = to_egocentric(other_pos)
                if norm_dist < 0.2:
                    local_dir, _ = to_egocentric(other_pos)
                    neighbor_feats.extend(list(local_dir) + [norm_dist, 0.0])

            obs = np.concatenate([local_dir_nest, [norm_dist_nest], sensor_vals, local_dir_door, [norm_dist_door], np.zeros(8), [door_state], np.array(neighbor_feats).flatten()])
            obs = np.pad(obs, (0, self.observation_space(agent).shape[0] - len(obs)), 'constant')
            observations[agent] = obs.astype(np.float32)
        return observations

    def step(self, actions):
        rewards = {a: 0.0 for a in self.agents}
        
        for idx, agent in enumerate(self.agents):
            move_local = np.clip(actions[agent], -1, 1) * 0.2
            F = self.agent_headings[idx]
            R = np.cross(F, np.array([0,0,1])); R /= np.linalg.norm(R) + 1e-6
            move_global = move_local[0] * F + move_local[1] * R
            
            is_colliding, normal = self._is_colliding(self.agent_positions[idx] + move_global, return_normal=True)
            
            if is_colliding:
                rewards[agent] += self.obstacle_penalty
                move_global = move_global - np.dot(move_global, normal) * normal
            
            self.agent_positions[idx] += move_global
            if np.linalg.norm(move_global) > 1e-5:
                self.agent_headings[idx] = move_global / np.linalg.norm(move_global)

            if np.linalg.norm(self.agent_positions[idx] - self.last_positions[idx]) < self.stagnation_area:
                self.stagnation_counters[idx] += 1
            else:
                self.stagnation_counters[idx] = 0
                self.last_positions[idx] = self.agent_positions[idx].copy()

            if self.stagnation_counters[idx] > self.stagnation_threshold:
                rewards[agent] += self.stagnation_penalty
                self.stagnation_counters[idx] = 0

        if self.classic_scenario == "cooperative_door" and self.door_active:
            pushing_robots = [i for i, pos in enumerate(self.agent_positions) if -1.5 < pos[0] < 0.0 and -2.0 < pos[1] < 2.0]
            for r_idx in pushing_robots: rewards[self.agents[r_idx]] += 0.5
            if len(pushing_robots) >= 3:
                self.door_active = False
                for r_idx in pushing_robots: rewards[self.agents[r_idx]] += 100.0
                self.walls.pop(self.door_wall_index)

        terms = {a: self.steps >= self.max_steps for a in self.agents}
        return self._get_observations(), rewards, terms, {}, {}

    def action_space(self, agent): return self.action_spaces[agent]
    def observation_space(self, agent): return self.observation_spaces[agent]
