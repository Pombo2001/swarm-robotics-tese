import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


class GeneticTrainer:
    def __init__(self, config_path, generations=50):
        self.config_path = config_path
        self.env = SwarmForagingEnv(config_path)
        self.template_agent = GNNAgent("template", self.env.action_space("robot_0"))

        self.pop_size = 30
        self.generations = generations
        # Taxas biológicas saudáveis para não "fritar" a rede
        self.mutation_rate = 0.10
        self.sigma = 0.2

        # A VERDADEIRA DIVERSIDADE INICIAL
        # Criar 30 cérebros matematicamente únicos desde a Geração 1
        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent(f"temp_{i}", self.env.action_space("robot_0"))
            self.population.append(copy.deepcopy(random_brain.state_dict()))

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, 'gnn_fair_training.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'best_fitness', 'avg_fitness', 'time'])

        os.chmod(self.history_file, 0o666)

    def evaluate(self, weights):
        self.template_agent.load_state_dict(weights)
        obs_dict, _ = self.env.reset()
        total_reward = 0
        steps = 0
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
            steps += 1

            # --- EARLY STOPPING (A Guilhotina) ---
            # Se aos 150 steps o robô estiver com pontuação muito negativa
            # (significa que está a bater na parede ou perdido), matamos a avaliação!
            if steps == 150 and total_reward < -200:
                total_reward -= 1000  # Penalização severa por ter reprovado cedo
                done = True           # Termina o episódio imediatamente poupando 350 steps!

            if any(terms.values()) or any(truncs.values()):
                done = True

        return total_reward, steps

    def train(self):
        print(f"🧬 Treino Genético Iniciado (Meta: {self.generations} Gerações)")
        print("🔧 Funcionalidades ativas: Pure Evolution Strategies (Elitismo + Mutação)")

        global_timestep = 0
        overall_start_time = time.time()

        for gen in range(1, self.generations + 1):
            scores = []
            total_steps_this_gen = 0

            # 1. Avaliar todos os indivíduos
            for i in range(self.pop_size):
                score, steps = self.evaluate(self.population[i])
                scores.append(score)
                total_steps_this_gen += steps

            global_timestep += total_steps_this_gen
            cumulative_time = time.time() - overall_start_time

            sorted_indices = np.argsort(scores)[::-1]
            scores = np.array(scores)[sorted_indices]
            population_sorted = [self.population[i] for i in sorted_indices]

            # 2. ELITISMO AUMENTADO (Top 20% passam intactos)
            elite_count = max(3, int(self.pop_size * 0.2))
            new_population = [copy.deepcopy(population_sorted[i]) for i in range(elite_count)]

            # 3. MUTAÇÃO PURA (Clones mutados da Elite, sem Crossover)
            while len(new_population) < self.pop_size:
                parent_idx = np.random.randint(0, elite_count)
                child = copy.deepcopy(population_sorted[parent_idx])

                for key in child.keys():
                    if np.random.rand() < self.mutation_rate:
                        child[key] += torch.randn_like(child[key]) * self.sigma

                new_population.append(child)

            self.population = new_population

            print(
                f"Gen {gen}/{self.generations} | Timesteps: {global_timestep} | Melhor: {scores[0]:.2f} | Média: {np.mean(scores):.2f} | Tempo Total: {cumulative_time:.2f}s")

            with open(self.history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([global_timestep, scores[0], np.mean(scores), cumulative_time])

            if gen % 10 == 0 or gen == self.generations:
                save_path = os.path.join(self.model_dir, f"gnn_fair_best.pth")
                self.template_agent.load_state_dict(population_sorted[0])
                torch.save(self.template_agent.state_dict(), save_path)
                os.chmod(save_path, 0o666)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=50)
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer(config_path, generations=args.generations)
    trainer.train()