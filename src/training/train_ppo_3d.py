import os
import sys
import csv
import numpy as np
import argparse
import time
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor  # <--- 1. IMPORTAR O MONITOR!

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
        actions = {agent: action for agent in self.env.agents}
        obs_dict, rewards, terms, truncs, infos = self.env.step(actions)
        avg_reward = sum(rewards.values()) / len(rewards)
        return obs_dict["robot_0"], avg_reward, terms["robot_0"], truncs["robot_0"], infos["robot_0"]


class TimeLimitAndLoggingCallback(BaseCallback):
    def __init__(self, log_file, time_limit_seconds, verbose=0):
        super().__init__(verbose)
        self.log_file = log_file
        self.time_limit = time_limit_seconds
        self.start_time = None

    def _on_training_start(self):
        self.start_time = time.time()

    def _on_step(self):
        elapsed_time = time.time() - self.start_time

        if self.n_calls % 2000 == 0:
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
        return Monitor(wrapped_env)  # <--- 2. EMBRULHAR NO MONITOR!

    return _init


def train_ppo_3d(time_limit_minutes):
    time_limit_seconds = time_limit_minutes * 60
    num_cpu = 8
    print(f"🤖 PPO 3D a iniciar com {num_cpu} NÚCLEOS EM PARALELO! Orçamento: {time_limit_minutes} min.")

    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
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
    callback = TimeLimitAndLoggingCallback(log_file, time_limit_seconds)

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