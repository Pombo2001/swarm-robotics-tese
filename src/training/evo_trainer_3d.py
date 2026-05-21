"""
=======================================================================================
CÁBULA PARA A TESE: Evolução Neuro-Evolutiva (Genetic Algorithm + GNN)
=======================================================================================
Tipo de Algoritmo: Neuro-Evolução / Algoritmo Genético Puro (Pure GA)
Biblioteca: Nenhuma / PyTorch nativo para a rede neural. Todo o algoritmo genético foi
            implementado de raiz nesta dissertação, usando a biblioteca nativa 
            'multiprocessing' para paralelizar a avaliação das populações.

Como funciona na teoria:
1. Representação do Genoma: Cada "indivíduo" na nossa população é representado
   inteiramente pelos pesos e biases ('State Dictionary') da sua rede neural em PyTorch.
   Não há descodificação intermédia; a política de navegação é a genética direta do robô.
2. Homogeneous Swarm: O algoritmo não treina um indivíduo isolado no mapa. Avalia-se 
   o enxame como um todo. Uma única política (rede neural) é copiada para todos os N robôs
   na mesma simulação. O fitness desse "genoma" é a média das recompensas de todos os robôs
   após um episódio completo (ou até acionarem a guilhotina temporal).
3. Seleção Fortemente Elitista: O algoritmo ordena toda a população do melhor para o 
   pior score. O top 20% (Elite) passa diretamente, sem qualquer alteração, para a próxima
   geração, assegurando que o ótimo local encontrado nunca regride.
4. Reprodução e Mutação Gaussiana: Os restantes 80% da população são criados através 
   da seleção aleatória de um 'pai' do grupo de Elite. Não aplicamos Crossover (cruzamento) 
   para evitar a destruição de representações neurais coesas. Em vez disso, aplicamos uma
   Mutação Gaussiana: iteramos por todos os tensores da rede e adicionamos ruído aleatório
   com uma probabilidade de 'mutation_rate' e intensidade ditada pelo desvio padrão 'sigma'.
5. Guilhotina Genética (Early Stopping): Para otimizar massivamente o tempo computacional,
   se uma nova mutação resultar numa política que obtenha um score terrivelmente baixo logo 
   nos primeiros passos da simulação (ex: andar em círculos contra a parede), a avaliação
   deste indivíduo é abortada e recebe uma penalização massiva.

Justificação e Parâmetros (Configurados no YAML):
- População: Tipicamente 30 indivíduos avaliados em paralelo em 8 cores (multiprocessing).
- O Elite-size estrito, aliado ao ruído gaussiano, encoraja uma navegação "cautelosa", o que 
  explica o seu enorme sucesso na evitação de obstáculos em relação aos algoritmos clássicos
  de RL (PPO/SAC) que dependem de descida de gradiente contínua.
=======================================================================================
"""

import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse
import yaml
from multiprocessing import Pool, cpu_count, freeze_support

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D

def evaluate_genome(args):
    weights, config = args

    env = SwarmForagingEnv3D(config=config)
    agent = GNNAgent3D("worker_agent", env.action_space("robot_0"), config=config)
    agent.load_state_dict(weights)

    obs_dict, _ = env.reset()
    total_reward = 0
    steps = 0
    done = False

    guillotine_threshold = config['simulation'].get('guillotine_threshold', -200)

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

        if steps == 150 and total_reward < guillotine_threshold:
            total_reward -= 1000
            done = True

        if any(terms.values()) or any(truncs.values()):
            done = True

    return total_reward / env.num_agents, steps

class GeneticTrainer3D:
    def __init__(self, config_path, time_limit_minutes=120):
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.time_limit_seconds = time_limit_minutes * 60

        temp_env = SwarmForagingEnv3D(config=self.config)
        self.template_agent = GNNAgent3D("template_3d", temp_env.action_space("robot_0"), config=self.config)

        evo_config = self.config.get('evolution', {})
        self.pop_size = evo_config.get('pop_size', 30)
        self.mutation_rate = evo_config.get('mutation_rate', 0.10)
        self.sigma = evo_config.get('sigma', 0.2)

        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent3D(f"temp_{i}", temp_env.action_space("robot_0"), config=self.config)
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
        num_cores = min(8, cpu_count())

        print(f"🚁 Treino GNN 3D Iniciado (Meta: Orçamento de {self.time_limit_seconds / 60:.1f} minutos)")
        print(f"⚡ ACELERAÇÃO ATIVA: {num_cores} NÚCLEOS DO RYZEN A AVALIAR EM PARALELO!")
        print("🔧 Funcionalidades: Pure Evolution + Guilhotina")

        global_timestep = 0
        overall_start_time = time.time()
        gen = 1

        with Pool(processes=num_cores) as pool:
            while True:
                cumulative_time = time.time() - overall_start_time
                if cumulative_time >= self.time_limit_seconds:
                    print(f"\n⏱️ FIM DO TEMPO! O cronómetro atingiu o limite. A fechar e guardar o modelo...")
                    break

                args_list = [(self.population[i], self.config) for i in range(self.pop_size)]
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer3D(config_path, time_limit_minutes=args.time_limit)
    trainer.train()

if __name__ == "__main__":
    freeze_support()
    main()
