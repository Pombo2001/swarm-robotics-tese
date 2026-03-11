import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse
from multiprocessing import Pool, cpu_count  # <--- MAGIA MULTI-CORE DO GNN

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D


# --- FUNÇÃO ISOLADA PARA MULTIPROCESSAMENTO ---
# Esta função corre de forma independente em cada núcleo do teu Ryzen 9800X3D!
def evaluate_genome(args):
    weights, config_path = args

    # Cada núcleo constrói a sua própria micro-arena e o seu próprio cérebro
    env = SwarmForagingEnv3D(config_path)
    agent = GNNAgent3D("worker_agent", env.action_space("robot_0"))
    agent.load_state_dict(weights)

    obs_dict, _ = env.reset()
    total_reward = 0
    steps = 0
    done = False

    while not done:
        obs_list = [obs_dict[a] for a in env.agents]
        obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)

        with torch.no_grad():
            actions_tensor = agent(obs_tensor)
            actions_np = actions_tensor.cpu().numpy()

        actions = {id: act for id, act in zip(env.agents, actions_np)}
        obs_dict, rewards, terms, truncs, _ = env.step(actions)

        total_reward += sum(rewards.values())
        steps += 1

        if steps == 150 and total_reward < -200:
            total_reward -= 1000
            done = True

        if any(terms.values()) or any(truncs.values()):
            done = True

    return total_reward, steps


class GeneticTrainer3D:
    def __init__(self, config_path, time_limit_minutes=120):
        self.config_path = config_path
        self.time_limit_seconds = time_limit_minutes * 60

        # Criamos o agente "molde" só para obter a estrutura da rede
        temp_env = SwarmForagingEnv3D(config_path)
        self.template_agent = GNNAgent3D("template_3d", temp_env.action_space("robot_0"))

        self.pop_size = 30
        self.mutation_rate = 0.10
        self.sigma = 0.2

        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent3D(f"temp_{i}", temp_env.action_space("robot_0"))
            self.population.append(copy.deepcopy(random_brain.state_dict()))

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, 'gnn_3d_training.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'best_fitness', 'avg_fitness', 'time'])

        os.chmod(self.history_file, 0o666)

    def train(self):
        # Vamos buscar até 8 núcleos do teu processador
        num_cores = min(8, cpu_count())

        print(f"🚁 Treino GNN 3D Iniciado (Meta: Orçamento de {self.time_limit_seconds / 60:.1f} minutos)")
        print(f"⚡ ACELERAÇÃO ATIVA: {num_cores} NÚCLEOS DO RYZEN A AVALIAR EM PARALELO!")
        print("🔧 Funcionalidades: Pure Evolution + Guilhotina")

        global_timestep = 0
        overall_start_time = time.time()
        gen = 1

        # O Pool é o "gestor" que distribui os cérebros pelos núcleos
        with Pool(processes=num_cores) as pool:
            while True:
                cumulative_time = time.time() - overall_start_time
                if cumulative_time >= self.time_limit_seconds:
                    print(f"\n⏱️ FIM DO TEMPO! O cronómetro atingiu o limite. A fechar e guardar o modelo...")
                    break

                # Preparamos os dados para enviar para os núcleos
                args_list = [(self.population[i], self.config_path) for i in range(self.pop_size)]

                # AQUI ACONTECE A MAGIA: 8 cérebros avaliados ao mesmo tempo!
                results = pool.map(evaluate_genome, args_list)

                scores = [res[0] for res in results]
                total_steps_this_gen = sum(res[1] for res in results)
                global_timestep += total_steps_this_gen

                cumulative_time = time.time() - overall_start_time

                sorted_indices = np.argsort(scores)[::-1]
                scores = np.array(scores)[sorted_indices]
                population_sorted = [self.population[i] for i in sorted_indices]

                elite_count = max(3, int(self.pop_size * 0.2))
                new_population = [copy.deepcopy(population_sorted[i]) for i in range(elite_count)]

                while len(new_population) < self.pop_size:
                    parent_idx = np.random.randint(0, elite_count)
                    child = copy.deepcopy(population_sorted[parent_idx])

                    for key in child.keys():
                        if np.random.rand() < self.mutation_rate:
                            child[key] += torch.randn_like(child[key]) * self.sigma

                    new_population.append(child)

                self.population = new_population

                print(
                    f"Gen {gen} | Timesteps: {global_timestep} | Melhor: {scores[0]:.2f} | Média: {np.mean(scores):.2f} | Tempo: {cumulative_time:.2f}s")

                with open(self.history_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([global_timestep, scores[0], np.mean(scores), cumulative_time])

                if gen % 10 == 0:
                    save_path = os.path.join(self.model_dir, "gnn_3d_best.pth")
                    self.template_agent.load_state_dict(population_sorted[0])
                    torch.save(self.template_agent.state_dict(), save_path)
                    os.chmod(save_path, 0o666)

                gen += 1

        save_path = os.path.join(self.model_dir, "gnn_3d_best.pth")
        self.template_agent.load_state_dict(population_sorted[0])
        torch.save(self.template_agent.state_dict(), save_path)
        os.chmod(save_path, 0o666)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    args = parser.parse_args()

    # OBRIGATÓRIO no Windows para usar múltiplos núcleos sem dar erro
    from multiprocessing import freeze_support

    freeze_support()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer3D(config_path, time_limit_minutes=args.time_limit)
    trainer.train()