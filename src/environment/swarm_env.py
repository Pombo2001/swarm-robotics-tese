import numpy as np
from gymnasium.spaces import Box
from pettingzoo import ParallelEnv
import yaml
import os


class SwarmForagingEnv(ParallelEnv):
    """
    Ambiente de Foraging Descentralizado.
    Herda de PettingZoo ParallelEnv (agentes agem em simultâneo).
    """
    metadata = {"name": "swarm_foraging_v0"}

    def __init__(self, config_path="configs/foraging.yaml"):
        # Carregar configurações
        if not os.path.exists(config_path):
            # Tenta encontrar o caminho relativo se correr da raiz
            config_path = os.path.join(os.getcwd(), config_path)

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.num_agents = self.config["environment"]["num_agents"]
        self.max_steps = self.config["simulation"]["max_steps"]

        # Agentes
        self.agents = [f"robot_{i}" for i in range(self.num_agents)]
        self.possible_agents = self.agents[:]

        # Espaço de Ação: [Velocidade X, Velocidade Y]
        self.action_spaces = {agent: Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for agent in self.agents}

        # Espaço de Observação: 20 valores (sensores simulados)
        self.observation_spaces = {agent: Box(low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32) for agent in
                                   self.agents}

    def reset(self, seed=None, options=None):
        self.steps = 0
        self.agents = self.possible_agents[:]

        # Inicializar posições aleatórias
        radius = self.config["environment"]["arena_radius"]
        self.agent_positions = np.random.uniform(low=-radius, high=radius, size=(self.num_agents, 2))

        observations = self._get_observations()
        infos = {agent: {} for agent in self.agents}

        return observations, infos

    def step(self, actions):
        self.steps += 1
        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}

        nest_pos = np.array([0.0, 0.0])

        for idx, agent in enumerate(self.agents):
            # 1. Movimento simples
            if agent in actions:
                move = actions[agent] * 0.1
                self.agent_positions[idx] += move

            # 2. Cálculo de Recompensa (Lógica da Tese)
            reward = 0.0
            pos = self.agent_positions[idx]
            dist_to_nest = np.linalg.norm(pos - nest_pos)

            # Penalização por sair da área
            if dist_to_nest > self.config["environment"]["forbidden_area"]:
                reward += self.config["rewards"]["out_of_bounds"]

            # Custo energético
            reward += self.config["rewards"]["energy_cost"]

            rewards[agent] = reward
            terminations[agent] = self.steps >= self.max_steps
            truncations[agent] = False
            infos[agent] = {}

        observations = self._get_observations()
        return observations, rewards, terminations, truncations, infos

    def _get_observations(self):
        return {agent: np.zeros(20, dtype=np.float32) for agent in self.agents}