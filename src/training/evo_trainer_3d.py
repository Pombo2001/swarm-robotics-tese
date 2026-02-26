import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from environment.swarm_env_3d import SwarmForagingEnv3D
from agents.gnn_agent_3d import GNNAgent3D


class GeneticTrainer3D:
    def __init__(self, config_path, generations=50):
        self.config_path = config_path
        self.env = SwarmForagingEnv3D(config_path)

        # Aponta para o novo Cérebro 3D
        self.template_agent = GNNAgent3D("template_3d", self.env.action_space("robot_0"))

        self.pop_size = 30
        self.generations = generations
        self.mutation_rate = 0.10
        self.sigma = 0.2

        # --- CORREÇÃO DO PACIENTE ZERO ---
        # 30 cérebros matematicamente únicos logo na Geração 1
        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent3D(f"temp_{i}", self.env.action_space("robot_0"))
            self.population.append(copy.deepcopy(random_brain.state_dict()))

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, 'gnn_3d_training.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Métricas justas para a Tese!
            writer.writerow(['timestep', 'best_fitness', 'avg_fitness', 'time'])

        os.chmod(self.history_file, 0o666)  # Acesso garantido

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

            # --- A GUILHOTINA 3D (Early Stopping) ---
            if steps == 150 and total_reward < -200:
                total_reward -= 1000
                done = True

            if any(terms.values()) or any(truncs.values()):
                done = True

        return total_reward, steps

    def train(self):
        print(f"🚁 Treino 3D Iniciado (Meta: {self.generations} Gerações)")
        print("🔧 Funcionalidades ativas: Pure Evolution (Sem Crossover) + Guilhotina")

        global_timestep = 0
        overall_start_time = time.time()

        for gen in range(1, self.generations + 1):
            scores = []
            total_steps_this_gen = 0

            for i in range(self.pop_size):
                score, steps = self.evaluate(self.population[i])
                scores.append(score)
                total_steps_this_gen += steps

            global_timestep += total_steps_this_gen
            cumulative_time = time.time() - overall_start_time

            sorted_indices = np.argsort(scores)[::-1]
            scores = np.array(scores)[sorted_indices]
            population_sorted = [self.population[i] for i in sorted_indices]

            # 1. ELITISMO AUMENTADO (Top 20%)
            elite_count = max(3, int(self.pop_size * 0.2))
            new_population = [copy.deepcopy(population_sorted[i]) for i in range(elite_count)]

            # 2. MUTAÇÃO PURA (Clones mutados da Elite)
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

            # Logs compatíveis com o PPO
            with open(self.history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([global_timestep, scores[0], np.mean(scores), cumulative_time])

            # Guarda o ficheiro Campeão 3D
            if gen % 10 == 0 or gen == self.generations:
                save_path = os.path.join(self.model_dir, "gnn_3d_best.pth")
                self.template_agent.load_state_dict(population_sorted[0])
                torch.save(self.template_agent.state_dict(), save_path)
                os.chmod(save_path, 0o666)  # Acesso garantido


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=50)
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer3D(config_path, generations=args.generations)
    trainer.train()