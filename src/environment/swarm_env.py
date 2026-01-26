import numpy as np
from gymnasium.spaces import Box
from pettingzoo import ParallelEnv
import yaml
import os
import pygame


class SwarmForagingEnv(ParallelEnv):
    """
    Ambiente com Colisões e Ninho Móvel.
    """
    metadata = {"name": "swarm_foraging_v1", "render_modes": ["human", "rgb_array"]}

    def __init__(self, config_path="configs/foraging.yaml"):
        # 1. Carregar configurações
        if not os.path.exists(config_path):
            config_path = os.path.join(os.getcwd(), config_path)

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Variáveis de Configuração
        n_agents = self.config["environment"]["num_agents"]
        self.max_steps = self.config["simulation"]["max_steps"]
        self.arena_radius = self.config["environment"]["arena_radius"]
        self.nest_radius = self.config["environment"]["nest_radius"]

        # Definir raio do robô (para colisões) - vamos assumir 0.15m
        self.robot_radius = 0.15

        # 2. Definir Agentes
        self.agents = [f"robot_{i}" for i in range(n_agents)]
        self.possible_agents = self.agents[:]

        # 3. Espaços de Ação e Observação
        self.action_spaces = {agent: Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for agent in self.agents}
        self.observation_spaces = {agent: Box(low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32) for agent in
                                   self.agents}

        # 4. Rendering
        self.render_mode = self.config["simulation"]["render_mode"]
        self.screen = None
        self.clock = None
        self.window_size = 800
        self.scale = self.window_size / (self.arena_radius * 2.2)

        # Estado do Ninho (Agora é dinâmico!)
        self.nest_pos = np.array([0.0, 0.0])

    def reset(self, seed=None, options=None):
        self.steps = 0
        self.agents = self.possible_agents[:]

        # Posições aleatórias dos robôs
        self.agent_positions = np.random.uniform(
            low=-self.arena_radius,
            high=self.arena_radius,
            size=(len(self.agents), 2)
        )

        # Ninho começa no centro ou aleatório? Vamos começar no centro no início
        self.nest_pos = np.array([0.0, 0.0])

        observations = self._get_observations()
        infos = {agent: {} for agent in self.agents}

        if self.render_mode == "human":
            self.render()

        return observations, infos

    def step(self, actions):
        self.steps += 1
        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}

        # 1. Movimento (Intenção)
        for idx, agent in enumerate(self.agents):
            if agent in actions:
                vel = actions[agent]
                move = vel * 0.1
                self.agent_positions[idx] += move

        # 2. FÍSICA DE COLISÕES + CONTAGEM DE BATIDAS
        agent_pos = self.agent_positions
        num_agents = len(self.agents)
        diffs = agent_pos[:, np.newaxis, :] - agent_pos[np.newaxis, :, :]
        dists = np.linalg.norm(diffs, axis=2)

        min_dist = self.robot_radius * 2.0

        # Vamos contar quantas vezes cada robô bateu neste frame
        collision_counts = {agent: 0 for agent in self.agents}

        # Matriz booleana de colisões (quem toca em quem)
        # Ignoramos a diagonal (eu cmg mesmo) e duplicados
        for i in range(num_agents):
            for j in range(i + 1, num_agents):
                dist = dists[i, j]
                if dist < min_dist:
                    # Houve colisão!
                    agent_i = self.agents[i]
                    agent_j = self.agents[j]

                    # Registar para dar penalização depois
                    collision_counts[agent_i] += 1
                    collision_counts[agent_j] += 1

                    # Resolver Física (Empurrar para trás)
                    direction = agent_pos[i] - agent_pos[j]
                    norm = np.linalg.norm(direction)
                    if norm > 0:
                        direction = direction / norm

                    overlap = min_dist - dist
                    # Empurrão mais suave para evitar vibração excessiva
                    push = direction * (overlap * 0.5)

                    self.agent_positions[i] += push
                    self.agent_positions[j] -= push

        # 3. Restrições e Recompensas
        for idx, agent in enumerate(self.agents):
            # Paredes
            self.agent_positions[idx] = np.clip(
                self.agent_positions[idx],
                -self.arena_radius,
                self.arena_radius
            )

            reward = 0.0
            pos = self.agent_positions[idx]
            dist_to_nest = np.linalg.norm(pos - self.nest_pos)

            # --- CHEGOU AO NINHO? ---
            # Aumentámos ligeiramente a tolerância da "porta" do ninho visualmente
            if dist_to_nest < (self.nest_radius + 0.1):
                reward += 10.0

                # Respawn Robô
                angle = np.random.uniform(0, 2 * np.pi)
                r = self.arena_radius * np.sqrt(np.random.uniform(0.6, 1))  # Mais longe
                self.agent_positions[idx] = np.array([r * np.cos(angle), r * np.sin(angle)])

                # Respawn Ninho (Muda de sítio!)
                nest_angle = np.random.uniform(0, 2 * np.pi)
                nest_r = self.arena_radius * np.sqrt(np.random.uniform(0, 0.7))
                self.nest_pos = np.array([nest_r * np.cos(nest_angle), nest_r * np.sin(nest_angle)])

                # Atualizar dist
                dist_to_nest = np.linalg.norm(self.agent_positions[idx] - self.nest_pos)

            # Shaping (Cheiro)
            reward += (1.0 / (dist_to_nest + 0.1)) * 0.5

            # --- NOVA PENALIZAÇÃO DE COLISÃO ---
            # Se bateu em alguém, perde pontos!
            if collision_counts[agent] > 0:
                reward -= 0.5 * collision_counts[agent]  # -0.5 pontos por batida

            # Penalização Paredes
            if dist_to_nest > self.config["environment"]["forbidden_area"]:
                reward += self.config["rewards"]["out_of_bounds"]

            # Custo Energia
            reward += self.config["rewards"]["energy_cost"]

            rewards[agent] = reward
            terminations[agent] = self.steps >= self.max_steps
            truncations[agent] = False
            infos[agent] = {}

        if self.render_mode == "human":
            self.render()

        return self._get_observations(), rewards, terminations, truncations, infos

    def _get_observations(self):
        observations = {}
        comm_radius = self.config["physics"]["communication_radius"]

        # Calcular distâncias
        diffs = self.agent_positions[:, np.newaxis, :] - self.agent_positions[np.newaxis, :, :]
        dists = np.linalg.norm(diffs, axis=2)

        for idx, agent in enumerate(self.agents):
            my_pos = self.agent_positions[idx]

            # 1. Vetor para o Ninho (Agora Dinâmico)
            vec_to_nest = self.nest_pos - my_pos

            obs_vector = np.zeros(20, dtype=np.float32)
            obs_vector[0] = vec_to_nest[0]
            obs_vector[1] = vec_to_nest[1]

            # 2. Vizinhos
            neighbor_indices = np.where((dists[idx] <= comm_radius) & (dists[idx] > 0))[0]
            neighbor_rel_positions = []
            for n_idx in neighbor_indices:
                rel_pos = self.agent_positions[n_idx] - self.agent_positions[idx]
                dist = dists[idx, n_idx]
                neighbor_rel_positions.append((dist, rel_pos))

            neighbor_rel_positions.sort(key=lambda x: x[0])

            slot = 2
            for dist, rel_pos in neighbor_rel_positions:
                if slot >= 20: break
                obs_vector[slot] = rel_pos[0]
                obs_vector[slot + 1] = rel_pos[1]
                slot += 2

            observations[agent] = obs_vector

        return observations

    def observation_space(self, agent):
        return self.observation_spaces[agent]

    def action_space(self, agent):
        return self.action_spaces[agent]

    def _world_to_screen(self, pos):
        center_offset = self.window_size / 2
        screen_x = int(pos[0] * self.scale + center_offset)
        screen_y = int(pos[1] * self.scale + center_offset)
        return (screen_x, screen_y)

    def render(self):
        if self.screen is None:
            pygame.init()
            if self.render_mode == "human":
                pygame.display.init()
                self.screen = pygame.display.set_mode((self.window_size, self.window_size))
                pygame.display.set_caption("Simulador Tese: Colisões + Ninho Móvel")
            self.clock = pygame.time.Clock()

        self.screen.fill((255, 255, 255))
        center_screen = self._world_to_screen(np.array([0, 0]))

        # Arena
        pygame.draw.circle(self.screen, (240, 240, 240), center_screen, int(self.arena_radius * self.scale))
        pygame.draw.circle(self.screen, (0, 0, 0), center_screen, int(self.arena_radius * self.scale), 1)

        # Ninho (Agora desenhamos na posição self.nest_pos!)
        nest_screen_pos = self._world_to_screen(self.nest_pos)
        pygame.draw.circle(self.screen, (200, 255, 200), nest_screen_pos, int(self.nest_radius * self.scale))

        # Agentes
        for pos in self.agent_positions:
            screen_pos = self._world_to_screen(pos)
            # Agente Azul
            pygame.draw.circle(self.screen, (0, 0, 255), screen_pos, int(self.robot_radius * self.scale))
            # Borda preta para ver colisão melhor
            pygame.draw.circle(self.screen, (0, 0, 0), screen_pos, int(self.robot_radius * self.scale), 1)

        if self.render_mode == "human":
            pygame.display.flip()
            self.clock.tick(30)

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()
            self.screen = None