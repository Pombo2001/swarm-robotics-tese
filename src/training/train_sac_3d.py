import os
import sys
import csv
import numpy as np
import argparse
import time
import yaml
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecEnvWrapper, VecMonitor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D


class MultiAgentArenaWrapper(gym.Env):
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.num_agents = env.num_agents
        self.observation_space = env.observation_space_val
        self.action_space = env.action_space_val

    def reset(self, seed=None, options=None):
        obs_dict, info = self.env.reset(seed=seed, options=options)
        obs_array = np.array([obs_dict[a] for a in self.env.agents], dtype=np.float32)
        return obs_array, info

    def step(self, action_array):
        actions = {a: action_array[i] for i, a in enumerate(self.env.agents)}
        obs_dict, rewards, terms, truncs, infos = self.env.step(actions)
        
        obs_array = np.array([obs_dict[a] for a in self.env.agents], dtype=np.float32)
        reward_array = np.array([rewards[a] for a in self.env.agents], dtype=np.float32)
        
        done = any(terms.values())
        trunc = any(truncs.values())
        
        return obs_array, reward_array, done, trunc, infos.get("robot_0", {})

class FlattenMultiAgentVecEnv(VecEnvWrapper):
    def __init__(self, venv, num_agents):
        self.num_agents = num_agents
        self.num_arenas = venv.num_envs
        super().__init__(venv, observation_space=venv.observation_space, action_space=venv.action_space)
        self.num_envs = self.num_arenas * self.num_agents

    def reset(self):
        obs = self.venv.reset()
        return obs.reshape(self.num_envs, -1)

    def step_async(self, actions):
        actions = actions.reshape(self.num_arenas, self.num_agents, -1)
        self.venv.step_async(actions)

    def step_wait(self):
        obs, rewards, dones, infos = self.venv.step_wait()
        obs = obs.reshape(self.num_envs, -1)
        rewards = rewards.flatten()
        dones = np.repeat(dones, self.num_agents)
        
        expanded_infos = []
        for info in infos:
            for _ in range(self.num_agents):
                expanded_infos.append(info.copy() if isinstance(info, dict) else info)
                
        return obs, rewards, dones, expanded_infos


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
            print(f"\n[FIM DO TEMPO] ({self.time_limit / 60:.1f} minutos). A gravar modelo...")
            return False

        return True


def make_env(config_path):
    def _init():
        raw_env = SwarmForagingEnv3D(config_path)
        wrapped_env = MultiAgentArenaWrapper(raw_env)
        return wrapped_env
    return _init


def train_sac_3d(time_limit_minutes):
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    sac_config = config.get('sac', {})
    num_cpu = sac_config.get('num_cpu', 8)
    log_interval = sac_config.get('log_interval', 2000)

    time_limit_seconds = time_limit_minutes * 60
    print(f"[START] SAC 3D a iniciar com {num_cpu} NÚCLEOS EM PARALELO! Orçamento: {time_limit_minutes} min.")

    env = SubprocVecEnv([make_env(config_path) for i in range(num_cpu)])
    env = FlattenMultiAgentVecEnv(env, config['environment'].get('num_agents', 25))
    env = VecMonitor(env)

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'training_history_sac_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean', 'time'])

    os.chmod(log_file, 0o666)

    model = SAC("MlpPolicy", env, verbose=1, device="auto")
    callback = TimeLimitAndLoggingCallback(log_file, time_limit_seconds, log_interval)

    print(f"[RUNNING] Simulação SAC a correr nos {num_cpu} clones da arena...")
    model.learn(total_timesteps=100000000, callback=callback)

    model_path = os.path.join(model_dir, "sac_3d_final")
    model.save(model_path)
    os.chmod(model_path + ".zip", 0o666)
    print("[DONE] Treino SAC 3D Multi-Core concluído de forma segura!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    train_sac_3d(time_limit_minutes=args.time_limit)