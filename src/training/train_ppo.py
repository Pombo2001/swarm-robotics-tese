import os
import sys
import csv
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import VecEnv

# Forçar o Python a reconhecer a pasta RAIZ
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env import SwarmForagingEnv

# --- 1. O ESPIÃO (Callback Melhorado) ---
class DashboardCallback(BaseCallback):
    def __init__(self, log_path, verbose=0):
        super().__init__(verbose)
        self.log_path = log_path
        # Garante que a pasta existe
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        # Cria o ficheiro limpo
        with open(self.log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timesteps', 'ep_rew_mean', 'ep_len_mean'])

    def _on_step(self) -> bool:
        # Tenta gravar com mais frequência (a cada 500 passos)
        if self.n_calls % 500 == 0:
            ep_info_buffer = self.model.ep_info_buffer

            # Só escreve se houver dados de episódios terminados
            if ep_info_buffer and len(ep_info_buffer) > 0:
                avg_rew = np.mean([ep_info['r'] for ep_info in ep_info_buffer])
                avg_len = np.mean([ep_info['l'] for ep_info in ep_info_buffer])

                with open(self.log_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_timesteps, avg_rew, avg_len])
        return True


# --- 2. O WRAPPER (Agora com Contagem de Pontos!) ---
class SwarmVecEnv(VecEnv):
    def __init__(self, config_path):
        self.swarm = SwarmForagingEnv(config_path=config_path)
        self.agents = self.swarm.agents
        num_agents = len(self.agents)
        obs_space = self.swarm.observation_space(self.agents[0])
        act_space = self.swarm.action_space(self.agents[0])
        super().__init__(num_agents, obs_space, act_space)

        # ACUMULADORES DE PONTOS (NOVO!)
        self.current_rewards = np.zeros(num_agents)
        self.current_lengths = np.zeros(num_agents)

    def reset(self):
        self.current_rewards.fill(0)
        self.current_lengths.fill(0)
        obs_dict, _ = self.swarm.reset()
        return np.array([obs_dict[a] for a in self.agents])

    def step_async(self, actions):
        self.actions = actions

    def step_wait(self):
        act_dict = {a: self.actions[i] for i, a in enumerate(self.agents)}
        obs, rews, terms, truncs, infos = self.swarm.step(act_dict)

        # Somar recompensas para saber o score total do episódio
        rew_array = np.array([rews[a] for a in self.agents])
        self.current_rewards += rew_array
        self.current_lengths += 1

        any_done = any(terms.values()) or any(truncs.values())

        # Preparar Info Array
        info_arr = [infos[a] for a in self.agents]

        if any_done:
            # INJETAR A PONTUAÇÃO FINAL PARA O PPO SABER (CRUCIAL!)
            for i in range(self.num_envs):
                info_arr[i]['episode'] = {
                    'r': self.current_rewards[i],
                    'l': self.current_lengths[i]
                }

            # Resetar ambiente e contadores
            obs_dict, _ = self.swarm.reset()
            final_obs = np.array([obs_dict[a] for a in self.agents])

            # Resetar acumuladores
            self.current_rewards.fill(0)
            self.current_lengths.fill(0)

            return final_obs, rew_array, np.ones(self.num_envs, dtype=bool), info_arr

        # Se não acabou, continua normal
        obs_arr = np.array([obs[a] for a in self.agents])
        return obs_arr, rew_array, np.array([False] * self.num_envs), info_arr

    def close(self):
        self.swarm.close()

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        return [None] * self.num_envs

    def get_attr(self, attr_name, indices=None):
        return [getattr(self.swarm, attr_name, None)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        setattr(self.swarm, attr_name, value)


# --- 3. TREINO PRINCIPAL ---
def train_ppo():
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    models_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')

    # Caminho do CSV
    csv_path = os.path.join(log_dir, 'training_history_ppo.csv')

    print("🤖 A iniciar treino PPO (Versão corrigida)...")
    env = SwarmVecEnv(config_path)

    callback = DashboardCallback(log_path=csv_path)

    # Nota: Baixei o batch_size ligeiramente para ser mais rápido a atualizar
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=log_dir, learning_rate=0.0003, batch_size=2048)

    model.learn(total_timesteps=500000, callback=callback)

    model.save(os.path.join(models_dir, "ppo_final"))
    print("✅ Treino PPO concluído!")


if __name__ == "__main__":
    train_ppo()