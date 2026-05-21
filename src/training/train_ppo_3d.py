import os
import sys
import csv
import numpy as np
import argparse
import time
import yaml
import torch
import torch.nn.functional as F
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.icm_module import ICM

class PPOWithICM(PPO):
    def __init__(self, policy, env, icm_learning_rate=1e-4, icm_beta=0.2, intrinsic_reward_weight=0.01, **kwargs):
        super(PPOWithICM, self).__init__(policy, env, **kwargs)
        obs_space = self.observation_space
        action_space = self.action_space
        self.icm = ICM(obs_space.shape[0], action_space.shape[0]).to(self.device)
        self.icm_optimizer = torch.optim.Adam(self.icm.parameters(), lr=icm_learning_rate)
        self.beta = icm_beta
        self.intrinsic_reward_weight = intrinsic_reward_weight

    def train(self) -> None:
        super().train()
        rollout_data = self.rollout_buffer.get(batch_size=None)
        states = rollout_data.observations
        next_states = self.rollout_buffer.next_observations
        actions = rollout_data.actions
        if isinstance(self.action_space, gym.spaces.Discrete):
            actions = F.one_hot(actions.long(), self.action_space.n).float()
        forward_loss, inverse_loss = self.icm(states, next_states, actions)
        icm_loss = (1 - self.beta) * inverse_loss + self.beta * forward_loss.mean()
        self.icm_optimizer.zero_grad()
        icm_loss.backward()
        self.icm_optimizer.step()

    def _store_transition(self, replay_buffer, buffer_action, new_obs, reward, done, infos):
        obs = self._last_obs
        action = buffer_action
        obs_tensor = torch.tensor(obs, dtype=torch.float32).to(self.device)
        next_obs_tensor = torch.tensor(new_obs, dtype=torch.float32).to(self.device)
        action_tensor = torch.tensor(action, dtype=torch.float32).to(self.device)
        intrinsic_reward = self.icm.get_intrinsic_reward(obs_tensor, next_obs_tensor, action_tensor)
        intrinsic_reward = intrinsic_reward.cpu().numpy() * self.intrinsic_reward_weight
        reward += intrinsic_reward
        super()._store_transition(replay_buffer, buffer_action, new_obs, reward, done, infos)

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

class SwarmEvalAndLoggingCallback(BaseCallback):
    def __init__(self, eval_env, log_file, time_limit_seconds, log_interval, verbose=0):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.log_file = log_file
        self.time_limit = time_limit_seconds
        self.log_interval = log_interval
        self.start_time = None
    def _on_training_start(self):
        self.start_time = time.time()
    def _on_step(self):
        elapsed_time = time.time() - self.start_time
        if self.n_calls % self.log_interval == 0:
            obs_dict, _ = self.eval_env.reset()
            done = False
            total_reward = 0.0
            while not done:
                actions = {}
                for agent_id in self.eval_env.agents:
                    obs = np.array(obs_dict[agent_id], dtype=np.float32)
                    action, _ = self.model.predict(obs, deterministic=True)
                    actions[agent_id] = action
                obs_dict, rewards, terms, truncs, infos = self.eval_env.step(actions)
                total_reward += sum(rewards.values())
                if any(terms.values()) or any(truncs.values()):
                    done = True
            ep_rew_mean = total_reward / self.eval_env.num_agents
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([self.num_timesteps, ep_rew_mean, elapsed_time])
        if elapsed_time >= self.time_limit:
            return False
        return True

def make_env(config_path):
    def _init():
        raw_env = SwarmForagingEnv3D(config_path)
        wrapped_env = PPOFriendlyWrapper(raw_env)
        return Monitor(wrapped_env)
    return _init

def train_ppo_3d(args):
    config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    ppo_config = config.get('ppo', {})
    num_cpu = ppo_config.get('num_cpu', 8)
    log_interval = ppo_config.get('log_interval', 2000)
    time_limit_seconds = args.time_limit * 60
    
    env = SubprocVecEnv([make_env(config_path) for i in range(num_cpu)])
    eval_env = SwarmForagingEnv3D(config_path)

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'training_history_ppo_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean', 'time'])
    os.chmod(log_file, 0o666)

    model = PPOWithICM("MlpPolicy", env, verbose=0, device="auto",
                       learning_rate=args.learning_rate,
                       gamma=args.gamma,
                       gae_lambda=args.gae_lambda,
                       clip_range=args.clip_range,
                       n_steps=args.n_steps,
                       icm_learning_rate=args.icm_learning_rate,
                       icm_beta=args.icm_beta,
                       intrinsic_reward_weight=args.intrinsic_reward_weight)
    
    callback = SwarmEvalAndLoggingCallback(eval_env, log_file, time_limit_seconds, log_interval)
    model.learn(total_timesteps=100000000, callback=callback)
    model.save(os.path.join(model_dir, "ppo_3d_final"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    parser.add_argument("--learning_rate", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--gae_lambda", type=float, default=0.95)
    parser.add_argument("--clip_range", type=float, default=0.2)
    parser.add_argument("--n_steps", type=int, default=2048)
    parser.add_argument("--icm_learning_rate", type=float, default=1e-4)
    parser.add_argument("--icm_beta", type=float, default=0.2)
    parser.add_argument("--intrinsic_reward_weight", type=float, default=0.01)
    args = parser.parse_args()
    from multiprocessing import freeze_support
    freeze_support()
    train_ppo_3d(args)