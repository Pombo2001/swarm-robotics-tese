"""
=======================================================================================
CÁBULA PARA A TESE: Proximal Policy Optimization (PPO)
=======================================================================================
Tipo de Algoritmo: Reinforcement Learning (RL) -> Policy Gradient -> On-Policy
Biblioteca: Stable-Baselines3 (SB3)

Como funciona na teoria:
1. Actor-Critic: O PPO usa duas redes neurais. O 'Actor' decide a ação a tomar com base
   na observação atual (política). O 'Critic' estima o valor (Value Function) desse estado 
   (quantas recompensas futuras se esperam se estivermos naquele estado).
2. On-Policy: O PPO aprende "fazendo". Ele recolhe um batch de experiências na arena usando 
   a política atual, usa essas experiências para atualizar os pesos da rede, e depois descarta-as.
   Não há "memória de longo prazo" de experiências muito antigas (Replay Buffer).
3. Clipping (A grande inovação): Para evitar que o algoritmo "esqueça" o que aprendeu
   com atualizações demasiado drásticas (Catastrophic Forgetting), o PPO "corta" (clips) 
   a probabilidade de mudar a política de forma extrema. A função de perda (Surrogate Loss) 
   garante que a nova política não se afasta muito da política antiga (Trust Region).

Implementação no nosso código (Dissertação):
- Setup: O PPO controla APENAS o 'robot_0'. Os outros robôs movem-se aleatoriamente para 
  gerar ruído e dinamismo (Tratados como parte do ambiente). Isto simplifica o espaço de 
  estado (Single-Agent RL num ambiente Multi-Agent).
- Vetorização: O ambiente é clonado (SubprocVecEnv) para correr em N núcleos em simultâneo, 
  permitindo recolher experiências N vezes mais depressa.
- Política: Usamos 'MlpPolicy' (Multi-Layer Perceptron), uma rede neural feedforward padrão.
=======================================================================================
"""

import os
import sys
import csv
import numpy as np
import argparse
import time
import yaml
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D


class PPOFriendlyWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        self.observation_space = env.observation_space_val
        self.action_space = env.action_space_val

    def reset(self, seed=None, options=None):
        obs_dict, info = self.env.reset(seed=seed, options=options)
        return obs_dict["robot_0"], info

    def step(self, action):
        actions = {"robot_0": action}
        for agent in self.env.agents:
            if agent != "robot_0":
                actions[agent] = self.env.action_space(agent).sample()
        obs_dict, rewards, terms, truncs, infos = self.env.step(actions)
        return obs_dict["robot_0"], rewards["robot_0"], terms["robot_0"], truncs["robot_0"], infos.get("robot_0", {})


class TimeLimitAndLoggingCallback(BaseCallback):
    def __init__(self, log_file, time_limit_seconds, log_interval, verbose=0):
        super().__init__(verbose)
        self.log_file = log_file
        self.time_limit = time_limit_seconds
        self.log_interval = log_interval
        self.start_time = None

    def _on_training_start(self):
        self.start_time = time.time()

    def _on_step(self):
        elapsed_time = time.time() - self.start_time

        if self.n_calls % self.log_interval == 0:
            if len(self.model.ep_info_buffer) > 0:
                ep_rew_mean = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
                with open(self.log_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_timesteps, ep_rew_mean, elapsed_time])

        if elapsed_time >= self.time_limit:
            print(f"\n⏱️ FIM DO TEMPO! ({self.time_limit / 60:.1f} minutos). A gravar modelo...")
            return False

        return True


def make_env(config_path):
    def _init():
        raw_env = SwarmForagingEnv3D(config_path)
        wrapped_env = PPOFriendlyWrapper(raw_env)
        return Monitor(wrapped_env)

    return _init


def train_ppo_3d(time_limit_minutes):
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    ppo_config = config.get('ppo', {})
    num_cpu = ppo_config.get('num_cpu', 8)
    log_interval = ppo_config.get('log_interval', 2000)

    time_limit_seconds = time_limit_minutes * 60
    print(f"🤖 PPO 3D a iniciar com {num_cpu} NÚCLEOS EM PARALELO! Orçamento: {time_limit_minutes} min.")

    env = SubprocVecEnv([make_env(config_path) for i in range(num_cpu)])

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'training_history_ppo_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean', 'time'])

    os.chmod(log_file, 0o666)

    model = PPO("MlpPolicy", env, verbose=1, device="auto")
    callback = TimeLimitAndLoggingCallback(log_file, time_limit_seconds, log_interval)

    print(f"🚀 Simulação PPO a correr nos {num_cpu} clones da arena...")
    model.learn(total_timesteps=100000000, callback=callback)

    model_path = os.path.join(model_dir, "ppo_3d_final")
    model.save(model_path)
    os.chmod(model_path + ".zip", 0o666)
    print("✅ Treino PPO 3D Multi-Core concluído de forma segura!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    train_ppo_3d(time_limit_minutes=args.time_limit)