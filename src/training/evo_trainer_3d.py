# =============================================================================
# GNN — Algoritmo Neuro-Evolutivo com Rede Neuronal de Grafos
# Desenvolvido de raiz (sem bibliotecas de RL externas)
#
# Paradigma: ALGORITMO GENÉTICO / EVOLUTION STRATEGIES
#   Baseado em: Salimans et al. (2017) "Evolution Strategies as a Scalable
#   Alternative to Reinforcement Learning" — mutação Gaussiana element-wise.
#
# Genoma: vector 1D contendo TODOS os pesos e biases da GNNAgent3D.
#   A política é o mapeamento directo do genoma → acções.
#   Topologia da rede é FIXA — não evolui estrutura, apenas pesos.
#
# Estratégia de mutação (Element-wise Gaussian Mutation com máscara):
#   Para cada peso w_i do filho:
#     com probabilidade mutation_rate (10%): w_i += N(0, sigma)
#     caso contrário: w_i permanece igual ao pai
#   Isto é equivalente a (1+λ)-ES com mask esparsa — não muta todos os pesos
#   em simultâneo (reduziria demasiado a diversidade com redes grandes).
#
# Elitismo: os 20% melhores (elite_count=6 de 30) são preservados sem mutação.
#   O restante da população é gerado a partir de cópias mutadas dos elites.
#
# Sigma decay: sigma começa em 0.1 e decai 0.5%/geração até mín. 0.01.
#   Exploração agressiva no início → refinamento gradual.
#
# Exploração: NÃO há reward shaping durante a evolução. A fitness é a
#   recompensa bruta do episódio (média de eval_episodes episódios — ver
#   foraging.yaml, atualmente 3 — para reduzir variância).
#   A "exploração" vem da estocasticidade da mutação Gaussiana.
#
# Paralelismo: cada genoma é avaliado num processo separado (multiprocessing).
# =============================================================================
import os
import sys
import torch
import numpy as np
import copy
import time
import csv
import argparse
import yaml
from multiprocessing import Pool, cpu_count

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D


def evaluate_genome(args):
    weights, config_path, eval_seed = args
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    guillotine_threshold = config['simulation'].get('guillotine_threshold', -200)
    eval_episodes = config.get('evolution', {}).get('eval_episodes', 2)

    env = SwarmForagingEnv3D(config_path)
    agent = GNNAgent3D("worker_agent", env.action_space("robot_0"), config_path)
    agent.load_state_dict(weights)

    episode_rewards = []
    total_steps = 0

    for ep in range(eval_episodes):
        # Todos os genomas da mesma geração enfrentam os mesmos episódios
        # (seed por geração) — seleção menos ruidosa e reproduzível.
        ep_seed = (eval_seed + ep) if eval_seed is not None else None
        obs_dict, _ = env.reset(seed=ep_seed)
        episode_reward = 0
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

            episode_reward += sum(rewards.values())
            steps += 1

            if steps == 150 and episode_reward < guillotine_threshold:
                episode_reward -= 1000
                done = True

            if any(terms.values()) or any(truncs.values()):
                done = True

        episode_rewards.append(episode_reward)
        total_steps += steps

    avg_fitness  = float(np.mean(episode_rewards))
    food_count   = int(env.total_food_collected)   # recolhas sem shaping (tarefa pura)
    return avg_fitness, total_steps, food_count


class GeneticTrainer3D:
    def __init__(self, config_path, time_limit_minutes=120, seed=None):
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.time_limit_seconds = time_limit_minutes * 60
        # Reprodutibilidade: semeia a população inicial e as mutações.
        self.seed = seed
        if seed is not None:
            np.random.seed(seed)
            torch.manual_seed(seed)

        temp_env = SwarmForagingEnv3D(config_path)
        self.template_agent = GNNAgent3D("template_3d", temp_env.action_space("robot_0"), config_path)

        evo_config = self.config.get('evolution', {})
        self.pop_size = evo_config.get('pop_size', 30)
        self.mutation_rate = evo_config.get('mutation_rate', 0.10)
        self.sigma = evo_config.get('sigma', 0.1)  # desvio da mutação Gaussiana (foraging.yaml)
        self.sigma_min = 0.01
        self.sigma_decay = 0.995

        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent3D(f"temp_{i}", temp_env.action_space("robot_0"), config_path)
            self.population.append(copy.deepcopy(random_brain.state_dict()))

        self.log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        # Sufixo do cenário para não sobrescrever modelos entre cenários.
        # Convenção: none → sem sufixo; outros → _{scenario}
        scenario = self.config['environment'].get('classic_scenario', 'none')
        self.model_suffix = f"_{scenario}" if scenario and scenario != "none" else ""

        self.history_file = os.path.join(self.log_dir, 'gnn_3d_training.csv')
        with open(self.history_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'best_fitness', 'avg_fitness',
                             'best_task_food', 'time'])

        os.chmod(self.history_file, 0o666)

    def train(self):
        num_cores = min(8, cpu_count())

        print(f"[START] Treino GNN 3D Iniciado (Meta: Orcamento de {self.time_limit_seconds / 60:.1f} minutos)")
        print(f"[ACELERACAO] {num_cores} NUCLEOS DO RYZEN A AVALIAR EM PARALELO!")
        print("[INFO] Funcionalidades: Pure Evolution + Guilhotina")

        global_timestep = 0
        overall_start_time = time.time()
        gen = 1
        # Fallback: se o tempo esgotar antes da 1ª geração terminar, ainda há algo
        # para guardar (evita NameError no save final).
        population_sorted = self.population

        with Pool(processes=num_cores) as pool:
            while True:
                cumulative_time = time.time() - overall_start_time
                if cumulative_time >= self.time_limit_seconds:
                    print(f"\n[FIM DO TEMPO] O cronometro atingiu o limite. A fechar e guardar o modelo...")
                    break

                gen_seed = (self.seed + gen) if self.seed is not None else None
                args_list = [(self.population[i], self.config_path, gen_seed)
                             for i in range(self.pop_size)]
                results = pool.map(evaluate_genome, args_list)

                scores       = [res[0] for res in results]
                food_counts  = [res[2] for res in results]
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
                        # Element-wise mutation
                        mask = (torch.rand_like(child[key]) < self.mutation_rate).float()
                        child[key] += mask * torch.randn_like(child[key]) * self.sigma

                    new_population.append(child)

                self.population = new_population

                best_food = food_counts[sorted_indices[0]]
                print(
                    f"Gen {gen} | Steps: {global_timestep} | "
                    f"Fitness: {scores[0]:.1f} | Média: {np.mean(scores):.1f} | "
                    f"Comida (melhor): {best_food} | Sigma: {self.sigma:.4f} | "
                    f"Tempo: {cumulative_time:.1f}s")

                # Apply Adaptive Mutation (Decay)
                self.sigma = max(self.sigma_min, self.sigma * self.sigma_decay)

                with open(self.history_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([global_timestep, scores[0], np.mean(scores),
                                     best_food, cumulative_time])

                if gen % 10 == 0:
                    save_path = os.path.join(self.model_dir, f"gnn_3d_best{self.model_suffix}.pth")
                    self.template_agent.load_state_dict(population_sorted[0])
                    torch.save(self.template_agent.state_dict(), save_path)
                    os.chmod(save_path, 0o666)

                gen += 1

        save_path = os.path.join(self.model_dir, f"gnn_3d_best{self.model_suffix}.pth")
        self.template_agent.load_state_dict(population_sorted[0])
        torch.save(self.template_agent.state_dict(), save_path)
        os.chmod(save_path, 0o666)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=None,
                        help="Semente de reprodutibilidade (omitir = aleatorio)")
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer3D(config_path, time_limit_minutes=args.time_limit, seed=args.seed)
    trainer.train()