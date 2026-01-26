import numpy as np
import torch
import copy
import time
import os
import sys

# Ajustar caminhos
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


class GeneticTrainer:
    def __init__(self, config_path="configs/foraging.yaml"):
        # Configurações de Treino
        self.pop_size = 20  # Tamanho da população (20 cérebros diferentes)
        self.mutation_rate = 0.05  # Força da mutação
        self.generations = 100  # Quantas gerações vamos treinar
        self.elite_size = 2  # Quantos "melhores" passam sem mutação

        # Inicializar ambiente (sem render para ser rápido)
        self.env = SwarmForagingEnv(config_path=config_path)
        self.env.render_mode = None  # Desligar gráficos para treinar rápido

        # Criar um Agente "Molde" para sabermos a estrutura da rede
        # Usamos robot_0 apenas como referência
        self.template_agent = GNNAgent("template", self.env.action_space("robot_0"))

        # Inicializar População (Lista de pesos/state_dicts)
        self.population = []
        for _ in range(self.pop_size):
            # Cria pesos aleatórios
            self.population.append(copy.deepcopy(self.template_agent.policy.state_dict()))

        print(f"🧬 Treinador Genético iniciado. População: {self.pop_size}")

    def evaluate(self, weights):
        """
        Corre UM episódio com estes pesos e retorna a recompensa total.
        Todos os robôs usam o mesmo cérebro (Swarm Homogéneo).
        """
        # Carregar pesos no agente
        self.template_agent.policy.load_state_dict(weights)

        observations, _ = self.env.reset()
        total_reward = 0
        terminated = False

        # Loop de simulação (máx 500 passos para ser rápido)
        for _ in range(500):
            actions = {}

            # Todos os robôs usam o mesmo "cérebro" (partilha de pesos)
            for agent_id in self.env.agents:
                obs = observations[agent_id]
                actions[agent_id] = self.template_agent.get_action(obs)

            observations, rewards, _, _, _ = self.env.step(actions)

            # A fitness é a soma da recompensa de TODOS os robôs
            # (Queremos que o grupo todo tenha sucesso)
            total_reward += sum(rewards.values())

        return total_reward

    def mutate(self, weights):
        """
        Adiciona ruído aleatório aos pesos (Mutação).
        """
        new_weights = copy.deepcopy(weights)
        for key in new_weights.keys():
            # Adiciona ruído gaussiano aos tensores
            noise = torch.randn_like(new_weights[key]) * self.mutation_rate
            new_weights[key] += noise
        return new_weights

    def train(self):
        print("🚀 A iniciar treino...")

        for generation in range(self.generations):
            scores = []
            start_time = time.time()

            # 1. Avaliar cada indivíduo da população
            for i, weights in enumerate(self.population):
                score = self.evaluate(weights)
                scores.append((score, weights))

            # 2. Ordenar por Fitness (Melhor primeiro)
            scores.sort(key=lambda x: x[0], reverse=True)
            best_score = scores[0][0]
            avg_score = sum(s[0] for s in scores) / self.pop_size

            # 3. Log
            duration = time.time() - start_time
            print(
                f"Gen {generation + 1}/{self.generations} | Melhor: {best_score:.2f} | Média: {avg_score:.2f} | Tempo: {duration:.1f}s")

            # 4. Seleção e Reprodução
            new_population = []

            # Elitismo: Os melhores passam diretos
            for i in range(self.elite_size):
                new_population.append(scores[i][1])

            # Os outros são filhos mutados dos melhores
            # (Torneio simples: pegamos nos top 50% e mutamos)
            parents = [s[1] for s in scores[:self.pop_size // 2]]

            while len(new_population) < self.pop_size:
                # Escolhe um pai aleatório dos melhores
                parent = parents[np.random.randint(len(parents))]
                # Cria filho com mutação
                child = self.mutate(parent)
                new_population.append(child)

            self.population = new_population

            # Guardar o melhor modelo a cada 10 gerações
            if (generation + 1) % 10 == 0:
                self.save_model(scores[0][1], f"gen_{generation + 1}")

    def save_model(self, weights, name):
        path = os.path.join(os.path.dirname(__file__), '../../results/models')
        if not os.path.exists(path):
            os.makedirs(path)

        filename = os.path.join(path, f"gnn_{name}.pth")
        torch.save(weights, filename)
        print(f"💾 Modelo guardado em: {filename}")


if __name__ == "__main__":
    # Caminho absoluto para a config
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')

    trainer = GeneticTrainer(config_path)
    trainer.train()