import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse  # <--- Para receber ordens do Dashboard

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


class GeneticTrainer:
    def __init__(self, config_path, generations=100):
        self.config_path = config_path
        self.env = SwarmForagingEnv(config_path)
        self.template_agent = GNNAgent("template", self.env.action_space("robot_0"))

        self.pop_size = 30
        self.generations = generations  # Usa o valor que vem do Dashboard
        self.mutation_rate = 0.05
        self.sigma = 0.1

        self.population = []
        for _ in range(self.pop_size):
            self.population.append(copy.deepcopy(self.template_agent.state_dict()))

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, 'training_history.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['generation', 'best_score', 'avg_score', 'time'])

    def evaluate(self, weights):
        self.template_agent.load_state_dict(weights)
        obs_dict, _ = self.env.reset()
        total_reward = 0
        done = False

        while not done:
            obs_list = [obs_dict[a] for a in self.env.agents]
            obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)
            with torch.no_grad():
                actions_tensor = self.template_agent(obs_tensor)
                actions_np = actions_tensor.cpu().numpy()
            actions = {id: act for id, act in zip(self.env.agents, actions_np)}

            obs_dict, rewards, terms, truncs, _ = self.env.step(actions)
            total_reward += sum(rewards.values())
            if any(terms.values()) or any(truncs.values()):
                done = True
        return total_reward

    def train(self):
        print(f"🧬 Treino Genético Iniciado (Meta: {self.generations} Gerações)")

        for gen in range(1, self.generations + 1):
            start_time = time.time()
            scores = []

            for i in range(self.pop_size):
                scores.append(self.evaluate(self.population[i]))

            sorted_indices = np.argsort(scores)[::-1]
            scores = np.array(scores)[sorted_indices]
            population_sorted = [self.population[i] for i in sorted_indices]

            elite_count = int(self.pop_size * 0.1)
            new_population = population_sorted[:elite_count]

            while len(new_population) < self.pop_size:
                parent_idx = np.random.randint(0, elite_count)
                child = copy.deepcopy(population_sorted[parent_idx])
                for key in child.keys():
                    if np.random.rand() < self.mutation_rate:
                        child[key] += torch.randn_like(child[key]) * self.sigma
                new_population.append(child)

            self.population = new_population
            elapsed = time.time() - start_time

            print(
                f"Gen {gen}/{self.generations} | Melhor: {scores[0]:.2f} | Média: {np.mean(scores):.2f} | Tempo: {elapsed:.2f}s")

            with open(self.history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([gen, scores[0], np.mean(scores), elapsed])

            # Guardar a cada 10 OU na última
            if gen % 10 == 0 or gen == self.generations:
                save_path = os.path.join(self.model_dir, f"gnn_gen_{gen}.pth")
                self.template_agent.load_state_dict(population_sorted[0])
                torch.save(self.template_agent.state_dict(), save_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=100, help="Número de gerações")
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer(config_path, generations=args.generations)
    trainer.train()