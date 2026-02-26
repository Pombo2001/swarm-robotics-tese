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


class ContinuousTrainer:
    def __init__(self, config_path, total_timesteps=500000):
        self.config_path = config_path
        self.env = SwarmForagingEnv(config_path)
        self.env.max_steps = float('inf')  # Contínuo real
        self.total_timesteps = total_timesteps

        self.num_agents = self.env.num_agents
        self.mutation_rate = 0.10
        self.sigma = 0.2

        # 30 agentes com cérebros independentes e únicos no arranque
        self.brains = [GNNAgent(f"robot_{i}", self.env.action_space(f"robot_{i}")) for i in range(self.num_agents)]
        self.fitness = np.zeros(self.num_agents)
        self.lifespans = np.zeros(self.num_agents)

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, 'gnn_continuous_fair.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'best_fitness', 'avg_fitness', 'time'])

        os.chmod(self.history_file, 0o666)

    def train(self):
        print(f"🧬 Treino Contínuo (Steady-State) Iniciado - {self.total_timesteps} Timesteps")
        obs_dict, _ = self.env.reset()
        start_time = time.time()

        for step in range(1, self.total_timesteps + 1):
            actions = {}
            for i, agent_name in enumerate(self.env.agents):
                obs_tensor = torch.tensor(obs_dict[agent_name], dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    action = self.brains[i](obs_tensor).squeeze(0).numpy()
                actions[agent_name] = action

            next_obs_dict, rewards, terms, truncs, _ = self.env.step(actions)

            # Atualizar Fitness (Média Móvel)
            alpha = 0.05
            for i, agent_name in enumerate(self.env.agents):
                self.fitness[i] = (1 - alpha) * self.fitness[i] + alpha * rewards[agent_name]
                self.lifespans[i] += 1

            # SELEÇÃO NATURAL CONTÍNUA (A Promessa ao Professor)
            current_avg_fitness = np.mean(self.fitness)
            good_agents = [idx for idx in range(self.num_agents) if self.fitness[idx] >= current_avg_fitness]
            if not good_agents: good_agents = [np.argmax(self.fitness)]

            for i in range(self.num_agents):
                if self.lifespans[i] > 200:  # Tempo para provar valor
                    if self.fitness[i] < (current_avg_fitness - 0.5):  # Morre quem está abaixo da média
                        parent_idx = np.random.choice(good_agents)
                        child_weights = copy.deepcopy(self.brains[parent_idx].state_dict())

                        # Mutar o filho
                        for key in child_weights.keys():
                            if np.random.rand() < self.mutation_rate:
                                child_weights[key] += torch.randn_like(child_weights[key]) * self.sigma

                        self.brains[i].load_state_dict(child_weights)
                        self.fitness[i] = current_avg_fitness
                        self.lifespans[i] = 0

            obs_dict = next_obs_dict

            # Logs compatíveis com o PPO (a cada 1000 steps)
            if step % 1000 == 0:
                elapsed = time.time() - start_time
                best_fit = np.max(self.fitness)
                avg_fit = np.mean(self.fitness)
                print(
                    f"Step {step}/{self.total_timesteps} | Melhor Fit: {best_fit:.2f} | Média Fit: {avg_fit:.2f} | Tempo: {elapsed:.2f}s")

                with open(self.history_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([step, best_fit, avg_fit, elapsed])

            # Gravar Modelo
            if step % 50000 == 0 or step == self.total_timesteps:
                best_idx = np.argmax(self.fitness)
                save_path = os.path.join(self.model_dir, "gnn_continuous_fair_best.pth")
                torch.save(self.brains[best_idx].state_dict(), save_path)
                os.chmod(save_path, 0o666)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=500000)
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = ContinuousTrainer(config_path, total_timesteps=args.timesteps)
    trainer.train()