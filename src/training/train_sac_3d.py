# =============================================================================
# SAC — Soft Actor-Critic  (Haarnoja et al., 2018)
# Biblioteca: stable-baselines3
#
# Paradigma: OFF-POLICY — mantém um replay buffer e aprende de experiências
#   passadas. Mais eficiente em termos de amostras do que o PPO.
#
# Mecanismo de estabilidade: ENTROPIA REGULARIZADA — o objectivo inclui um
#   termo de maximização de entropia da política (H[π]), que incentiva
#   comportamento estocástico e previne convergência prematura.
#   Com ent_coef="auto" (default), o SAC ajusta dinamicamente o coeficiente
#   de entropia, o que pode causar REGRESSÃO em treinos longos (o SAC aumenta
#   entropia para "explorar mais" e desfaz o que aprendeu). Por isso usamos
#   ent_coef=0.1 fixo (configurável em foraging.yaml).
#
# Parameter sharing: mesma estratégia do PPO — FlattenMultiAgentVecEnv com
#   160 agentes virtuais partilhando uma política.
#
# Exploração: igual ao PPO — APENAS reward shaping (progress + energy cost).
#   NÃO há ICM (Intrinsic Curiosity Module) nem exploração intrínseca.
#   O SAC explora naturalmente pela estocasticidade da política (entropia).
#
# Rede: MLP [obs→256→256→actions] (net_arch configurável em foraging.yaml)
# =============================================================================
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

        done  = any(terms.values())
        trunc = any(truncs.values())

        info = dict(infos.get("robot_0", {}))
        if done or trunc:
            info["task_reward"] = float(
                self.env.total_food_collected * self.env.food_collected_reward)

        return obs_array, reward_array, done, trunc, info

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
            if "terminal_observation" in info:
                term_obs = info["terminal_observation"]
                for j in range(self.num_agents):
                    inf = info.copy()
                    inf["terminal_observation"] = term_obs[j]
                    expanded_infos.append(inf)
            else:
                for _ in range(self.num_agents):
                    expanded_infos.append(info.copy() if isinstance(info, dict) else info)
                
        return obs, rewards, dones, expanded_infos


class TimeLimitAndLoggingCallback(BaseCallback):
    def __init__(self, log_file, time_limit_seconds, log_interval,
                 checkpoint_dir=None, checkpoint_interval_sec=1800, verbose=0):
        super().__init__(verbose)
        self.log_file                = log_file
        self.time_limit              = time_limit_seconds
        self.log_interval            = log_interval
        self.checkpoint_dir          = checkpoint_dir
        self.checkpoint_interval_sec = checkpoint_interval_sec
        self.start_time              = None
        self._last_checkpoint_time   = 0.0
        self._task_ep_buf            = []

    def _on_training_start(self):
        self.start_time = time.time()

    def _on_step(self):
        elapsed_time = time.time() - self.start_time

        for info in self.locals.get("infos", []):
            if "episode" in info and "task_reward" in info:
                self._task_ep_buf.append(info["task_reward"])

        if self.n_calls % self.log_interval == 0:
            if len(self.model.ep_info_buffer) > 0:
                ep_rew_mean   = np.mean([ep["r"] for ep in self.model.ep_info_buffer])
                task_rew_mean = (np.mean(self._task_ep_buf)
                                 if self._task_ep_buf else 0.0)
                self._task_ep_buf.clear()
                with open(self.log_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_timesteps, ep_rew_mean,
                                     task_rew_mean, elapsed_time])

        if (self.checkpoint_dir and
                elapsed_time - self._last_checkpoint_time >= self.checkpoint_interval_sec):
            ckpt = os.path.join(self.checkpoint_dir,
                                f"sac_ckpt_{int(elapsed_time // 60):04d}min")
            self.model.save(ckpt)
            print(f"[CKPT] Checkpoint guardado: {ckpt}.zip")
            self._last_checkpoint_time = elapsed_time

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

    # Sufixo do cenário para não sobrescrever modelos entre cenários.
    scenario = config['environment'].get('classic_scenario', 'none')
    model_suffix = f"_{scenario}" if scenario and scenario != "none" else ""

    time_limit_seconds = time_limit_minutes * 60
    print(f"[START] SAC 3D a iniciar com {num_cpu} NÚCLEOS EM PARALELO! Orçamento: {time_limit_minutes} min.")

    env = SubprocVecEnv([make_env(config_path) for i in range(num_cpu)])
    env = FlattenMultiAgentVecEnv(env, config['environment'].get('num_agents', 25))
    env = VecMonitor(env)

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_sac')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_sac')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'training_history_sac_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean', 'ep_task_mean', 'time'])

    os.chmod(log_file, 0o666)

    ckpt_interval = int(sac_config.get('checkpoint_interval_min', 30) * 60)

    model = SAC(
        "MlpPolicy", env,
        learning_rate=sac_config.get("learning_rate", 1e-4),
        buffer_size=sac_config.get("buffer_size", 500_000),
        ent_coef=sac_config.get("ent_coef", 0.1),
        policy_kwargs=dict(net_arch=sac_config.get("net_arch", [256, 256])),
        verbose=1,
        device="auto",
    )
    callback = TimeLimitAndLoggingCallback(
        log_file, time_limit_seconds, log_interval,
        checkpoint_dir=model_dir, checkpoint_interval_sec=ckpt_interval)

    print(f"[RUNNING] Simulação SAC a correr nos {num_cpu} clones da arena...")
    model.learn(total_timesteps=100000000, callback=callback)

    model_path = os.path.join(model_dir, f"sac_3d_final{model_suffix}")
    model.save(model_path)
    os.chmod(model_path + ".zip", 0o666)
    print(f"[DONE] Treino SAC 3D Multi-Core concluído! Modelo: {os.path.basename(model_path)}.zip")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    train_sac_3d(time_limit_minutes=args.time_limit)