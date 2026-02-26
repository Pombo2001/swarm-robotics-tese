import os
import sys
import csv
import numpy as np
import torch
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from environment.swarm_env_3d import SwarmForagingEnv3D


# --- WRAPPER PARA TORNAR O ENXAME COMPATÍVEL COM PPO ---
class PPOFriendlyWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        self.observation_space = env.observation_space_val
        self.action_space = env.action_space_val

    def reset(self, seed=None, options=None):
        obs_dict, info = self.env.reset(seed=seed, options=options)
        # Devolvemos apenas a observação do primeiro robô para o PPO aprender o comportamento base
        return obs_dict["robot_0"], info

    def step(self, action):
        # O PPO decide para 1, nós aplicamos a mesma lógica a todos para manter o enxame
        actions = {agent: action for agent in self.env.agents}
        obs_dict, rewards, terms, truncs, infos = self.env.step(actions)

        # Média das recompensas para o PPO saber como o grupo está a ir
        avg_reward = sum(rewards.values()) / len(rewards)

        return obs_dict["robot_0"], avg_reward, terms["robot_0"], truncs["robot_0"], infos["robot_0"]


class LoggingCallback(BaseCallback):
    def __init__(self, log_file, verbose=0):
        super().__init__(verbose)
        self.log_file = log_file

    def _on_step(self):
        if self.n_calls % 2000 == 0:
            if len(self.model.ep_info_buffer) > 0:
                ep_rew_mean = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
                with open(self.log_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_timesteps, ep_rew_mean])
        return True


def train_ppo_3d():
    print("🤖 A iniciar treino PPO em 3D (Modo Multi-Agent Wrapper)...")
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')

    # Inicializar e Envolver o ambiente
    raw_env = SwarmForagingEnv3D(config_path)
    env = PPOFriendlyWrapper(raw_env)

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'training_history_ppo_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean'])

    os.chmod(log_file, 0o666)

    model = PPO("MlpPolicy", env, verbose=1, device="cpu")
    callback = LoggingCallback(log_file)

    print("🚀 Treino PPO 3D a começar efetivamente!")
    model.learn(total_timesteps=500000, callback=callback)

    model_path = os.path.join(model_dir, "ppo_3d_final")
    model.save(model_path)
    os.chmod(model_path + ".zip", 0o666)
    print("✅ Treino PPO 3D concluído!")


if __name__ == "__main__":
    train_ppo_3d()