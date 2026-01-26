import numpy as np
from gymnasium.spaces import Box
from pettingzoo import ParallelEnv
import yaml
import os
import pygame


class SwarmForagingEnv(ParallelEnv):
    """
    Ambiente de Foraging Descentralizado.
    """
    metadata = {"name": "swarm_foraging_v0", "render_modes": ["human", "rgb_array"]}

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

        # 2. Definir Agentes
        self.agents = [f"robot_{i}" for i in range(n_agents)]
        self.possible_agents = self.agents[:]

        # 3. Espaços de Ação e Observação
        self.action_spaces = {agent: Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for agent in self.agents}
        self.observation_spaces = {agent: Box(low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32) for agent in
                                   self.agents}

        # 4. Configuração de Rendering (PyGame)
        self.render_mode = self.config["simulation"]["render_mode"]
        self.screen = None
        self.clock = None
        self.window_size = 800  # Tamanho da janela em pixéis
        # Escala: Quantos pixéis por metro? (Janela / Diâmetro da Arena)
        self.scale = self.window_size / (self.arena_radius * 2.2)

    def reset(self, seed=None, options=None):
        self.steps = 0
        self.agents = self.possible_agents[:]

        # Posições aleatórias
        self.agent_positions = np.random.uniform(
            low=-self.arena_radius,
            high=self.arena_radius,
            size=(len(self.agents), 2)
        )

        self.has_food = {agent: False for agent in self.agents}

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

        nest_pos = np.array([0.0, 0.0])

        for idx, agent in enumerate(self.agents):
            # 1. Movimento
            if agent in actions:
                # Ação [-1, 1] convertida em velocidade
                vel = actions[agent]
                # Limitar velocidade máxima (física simples)
                move = vel * 0.1
                self.agent_positions[idx] += move

                # Impedir que saiam do ecrã (Clamping simples)
                self.agent_positions[idx] = np.clip(
                    self.agent_positions[idx],
                    -self.arena_radius,
                    self.arena_radius
                )

            # 2. Recompensas (Lógica da Tese)
            reward = 0.0
            pos = self.agent_positions[idx]
            dist_to_nest = np.linalg.norm(pos - nest_pos)

            # Penalização por sair da área proibida
            if dist_to_nest > self.config["environment"]["forbidden_area"]:
                reward += self.config["rewards"]["out_of_bounds"]

            reward += self.config["rewards"]["energy_cost"]

            rewards[agent] = reward
            terminations[agent] = self.steps >= self.max_steps
            truncations[agent] = False
            infos[agent] = {}

        if self.render_mode == "human":
            self.render()

        return self._get_observations(), rewards, terminations, truncations, infos

    def _get_observations(self):
        return {agent: np.zeros(20, dtype=np.float32) for agent in self.agents}

    def observation_space(self, agent):
        return self.observation_spaces[agent]

    def action_space(self, agent):
        return self.action_spaces[agent]

    # --- LÓGICA DE RENDERIZAÇÃO (NOVO) ---

    def _world_to_screen(self, pos):
        """Converte coordenadas do mundo (metros) para o ecrã (pixéis)"""
        # Centro do ecrã é (400, 400)
        center_offset = self.window_size / 2

        screen_x = int(pos[0] * self.scale + center_offset)
        # O Y no PyGame é invertido (0 é topo), por isso subtraímos
        screen_y = int(pos[1] * self.scale + center_offset)

        return (screen_x, screen_y)

    def render(self):
        if self.screen is None:
            pygame.init()
            if self.render_mode == "human":
                pygame.display.init()
                self.screen = pygame.display.set_mode((self.window_size, self.window_size))
                pygame.display.set_caption("Simulador Tese: Swarm Foraging")
            self.clock = pygame.time.Clock()

        # 1. Fundo (Branco)
        self.screen.fill((255, 255, 255))

        center_screen = self._world_to_screen(np.array([0, 0]))

        # 2. Desenhar Arena (Círculo Cinza Claro)
        pygame.draw.circle(
            self.screen,
            (240, 240, 240),
            center_screen,
            int(self.arena_radius * self.scale)
        )
        # Borda da Arena
        pygame.draw.circle(
            self.screen,
            (0, 0, 0),
            center_screen,
            int(self.arena_radius * self.scale),
            1
        )

        # 3. Desenhar Ninho (Círculo Verde no centro)
        pygame.draw.circle(
            self.screen,
            (200, 255, 200),
            center_screen,
            int(self.nest_radius * self.scale)
        )

        # 4. Desenhar Agentes (Círculos Azuis)
        for pos in self.agent_positions:
            screen_pos = self._world_to_screen(pos)
            pygame.draw.circle(self.screen, (0, 0, 255), screen_pos, 5)

        # Atualizar Ecrã
        if self.render_mode == "human":
            pygame.display.flip()
            self.clock.tick(30)  # Limitar a 30 FPS para conseguires ver

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()
            self.screen = None