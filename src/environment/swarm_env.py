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
                vel = actions[agent]
                # Velocidade normal (0.1) é mais segura para a física não "saltar" paredes
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

            # --- CORREÇÃO 1: Calcular a posição e distância PRIMEIRO ---
            pos = self.agent_positions[idx]
            dist_to_nest = np.linalg.norm(pos - nest_pos)

            # --- CORREÇÃO 2: Lógica de RESPAWN (A ideia do Orientador) ---
            # Se chegar ao ninho (distância menor que o raio do ninho)
            if dist_to_nest < self.nest_radius:
                reward += 10.0  # Grande prémio!

                # Teletransportar para sítio aleatório
                angle = np.random.uniform(0, 2 * np.pi)
                r = self.arena_radius * np.sqrt(np.random.uniform(0, 1))
                self.agent_positions[idx] = np.array([r * np.cos(angle), r * np.sin(angle)])

                # Recalcular distância após teletransporte (para o shaping não dar erro)
                dist_to_nest = np.linalg.norm(self.agent_positions[idx] - nest_pos)

            # --- CORREÇÃO 3: Incentivo de Distância (O "Cheiro" Forte) ---
            # Agora sim, usamos o dist_to_nest calculado acima
            reward += (1.0 / (dist_to_nest + 0.1)) * 0.5

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
        """
        Calcula o que cada robô "vê".
        Retorna um vetor fixo (tamanho 20) com:
        - [0, 1]: Vetor relativo ao Ninho (dx, dy)
        - [2, 3]: Vetor relativo ao Vizinho mais próximo 1
        - [4, 5]: Vetor relativo ao Vizinho mais próximo 2
        - ... etc
        """
        observations = {}
        comm_radius = self.config["physics"]["communication_radius"]
        nest_pos = np.array([0.0, 0.0])  # Ninho está sempre no centro

        # Calcular matriz de distâncias de todos para todos (Broadcast NumPy)
        # Isto é muito rápido: calcula distâncias de 10 robôs de uma vez
        # diffs[i, j] = pos[i] - pos[j]
        diffs = self.agent_positions[:, np.newaxis, :] - self.agent_positions[np.newaxis, :, :]
        dists = np.linalg.norm(diffs, axis=2)

        for idx, agent in enumerate(self.agents):
            my_pos = self.agent_positions[idx]

            # 1. Onde está o Ninho? (Vetor Relativo)
            vec_to_nest = nest_pos - my_pos

            # Preparar vetor de observação vazio (20 zeros)
            # Vamos normalizar valores simples para ajudar a Rede Neuronal (dividir por 10 ou raio)
            # Mas para já, usamos valores brutos (metros)
            obs_vector = np.zeros(20, dtype=np.float32)

            # Preencher Ninho (Slots 0 e 1)
            obs_vector[0] = vec_to_nest[0]
            obs_vector[1] = vec_to_nest[1]

            # 2. Processar Vizinhos
            # Filtrar quem está perto (dists[idx] < raio) e não sou eu (dists[idx] > 0)
            neighbor_indices = np.where((dists[idx] <= comm_radius) & (dists[idx] > 0))[0]

            # Buscar os vetores relativos desses vizinhos
            # Queremos saber ONDE eles estão em relação a mim (dx, dy)
            neighbor_rel_positions = []
            for n_idx in neighbor_indices:
                # diffs[n_idx, idx] dá a posição do vizinho relativa a mim
                # Nota: diffs[i, j] = pos[i] - pos[j].
                # Queremos Vizinho - Eu = pos[n_idx] - pos[idx]
                rel_pos = self.agent_positions[n_idx] - self.agent_positions[idx]
                dist = dists[idx, n_idx]
                neighbor_rel_positions.append((dist, rel_pos))

            # Ordenar vizinhos por distância (o mais perto é mais importante)
            neighbor_rel_positions.sort(key=lambda x: x[0])

            # 3. Preencher o vetor de observação
            # Temos slots do índice 2 ao 19 (18 slots = 9 vizinhos max)
            slot = 2
            for dist, rel_pos in neighbor_rel_positions:
                if slot >= 20: break  # Vetor cheio
                obs_vector[slot] = rel_pos[0]  # dx do vizinho
                obs_vector[slot + 1] = rel_pos[1]  # dy do vizinho
                slot += 2

            observations[agent] = obs_vector

        return observations

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