import numpy as np
import torch
import copy
import time
import os
import sys
import csv  # <--- Nova biblioteca para guardar dados

# Ajustar caminhos
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


class GeneticTrainer:
    def __init__(self, config_path="configs/foraging.yaml"):
        # Configurações de Treino
        self.pop_size = 20
        self.mutation_rate = 0.05
        self.generations = 50  # Podes ajustar conforme necessário
        self.elite_size = 2

        self.env = SwarmForagingEnv(config_path=config_path)
        self.env.render_mode = None

        self.template_agent = GNNAgent("template", self.env.action_space("robot_0"))

        self.population = []
        for _ in range(self.pop_size):
            self.population.append(copy.deepcopy(self.template_agent.policy.state_dict()))

        # --- NOVO: Configurar Log CSV ---
        self.results_path = os.path.join(os.path.dirname(__file__), '../../results')
        self.log_dir = os.path.join(self.results_path, 'logs')
        self.models_dir = os.path.join(self.results_path, 'models')

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)

        # Criar ficheiro CSV e escrever cabeçalho
        self.log_file = os.path.join(self.log_dir, 'training_history.csv')
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['generation', 'best_score', 'avg_score', 'time'])

        print(f"🧬 Treinador Genético iniciado. Logs em: {self.log_file}")

    def evaluate(self, weights):
        self.template_agent.policy.load_state_dict(weights)
        observations, _ = self.env.reset()
        total_reward = 0

        for _ in range(500):
            actions = {}
            for agent_id in self.env.agents:
                obs = observations[agent_id]
                actions[agent_id] = self.template_agent.get_action(obs)

            observations, rewards, _, _, _ = self.env.step(actions)
            total_reward += sum(rewards.values())

        return total_reward

    def mutate(self, weights):
        new_weights = copy.deepcopy(weights)
        for key in new_weights.keys():
            noise = torch.randn_like(new_weights[key]) * self.mutation_rate
            new_weights[key] += noise
        return new_weights

    def train(self):
        print("🚀 A iniciar treino com registo de dados...")

        for generation in range(self.generations):
            scores = []
            start_time = time.time()

            for i, weights in enumerate(self.population):
                score = self.evaluate(weights)
                scores.append((score, weights))

            scores.sort(key=lambda x: x[0], reverse=True)
            best_score = scores[0][0]
            avg_score = sum(s[0] for s in scores) / self.pop_size

            duration = time.time() - start_time
            print(f"Gen {generation + 1} | Melhor: {best_score:.2f} | Média: {avg_score:.2f}")

            # --- NOVO: Guardar no CSV ---
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([generation + 1, best_score, avg_score, duration])

            # Seleção e Reprodução
            new_population = []
            for i in range(self.elite_size):
                new_population.append(scores[i][1])

            parents = [s[1] for s in scores[:self.pop_size // 2]]
            while len(new_population) < self.pop_size:
                parent = parents[np.random.randint(len(parents))]
                child = self.mutate(parent)
                new_population.append(child)

            self.population = new_population

            if (generation + 1) % 10 == 0:
                self.save_model(scores[0][1], f"gen_{generation + 1}")

    def save_model(self, weights, name):
        filename = os.path.join(self.models_dir, f"gnn_{name}.pth")
        torch.save(weights, filename)
        print(f"💾 Modelo guardado: {filename}")


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer(config_path)
    trainer.train()