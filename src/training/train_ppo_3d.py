# PPO — Proximal Policy Optimization  (Schulman et al., 2017)
# Biblioteca: stable-baselines3
#
# Paradigma: ON-POLICY  — aprende diretamente da trajectória actual, descarta
#   as experiências após cada actualização (sem replay buffer).
#
# Mecanismo de estabilidade: CLIPPING do ratio de políticas (epsilon=0.2) que
#   impede que uma única actualização altere demasiado a política — evita
#   colapso de performance que o gradiente de política simples (REINFORCE)
#   sofre frequentemente.
#
# Parameter sharing: todos os 20 agentes partilham UMA rede via
#   FlattenMultiAgentVecEnv, que aplatana 8 arenas × 20 agentes → 160
#   "agentes virtuais" vistos pelo PPO como ambientes independentes.
#   A diversidade de perspectivas entre agentes funciona como regularizador.
#
# Exploração: feita APENAS por reward shaping — não há ICM nem módulo de
#   curiosidade externo. O incentivo de exploração é:
#     1. progress_reward = factor * (dist_anterior − dist_actual)  [shaping]
#     2. energy_cost     = −0.05 por passo                        [pressão temporal]
#   Estes sinais guiam o agente para o ninho sem exploração intrínseca.
#
# Rede: MLP [obs→256→256→actions] (net_arch configurável em foraging.yaml)
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
            # Task-only reward = food collected × 100 (sem shaping de progresso).
            # Pedido pelo orientador para comparação treino vs. avaliação.
            info["task_reward"] = float(
                self.env.total_food_collected * self.env.food_collected_reward)

        return obs_array, reward_array, done, trunc, info

class FlattenMultiAgentVecEnv(VecEnvWrapper):
    def __init__(self, venv, num_agents):
        self.num_agents = num_agents
        self.num_arenas = venv.num_envs
        super().__init__(venv, observation_space=venv.observation_space, action_space=venv.action_space)
        self.num_envs = self.num_arenas * self.num_agents

    def _verificar_forma(self, obs):
        """O `num_agents` deste wrapper vem do CONFIG — e o default do código
        (25) não é o do `configs/foraging.yaml` (20).

        Quando os dois números discordam, o reshape não estoira: com (2, 20, 10)
        lido como 25 agentes por arena, 400 elementos dividem-se por 50 linhas e
        saem 8 colunas — **observações de agentes diferentes coladas na mesma
        linha**, sem uma palavra. Um treino nessas condições corre até ao fim e
        converge para outra coisa.

        Medido a 13 ago em tests/test_treino_gradientes.py, que antes desta
        guarda documentava o silêncio em vez de o impedir.
        """
        if obs.ndim == 3 and obs.shape[1] != self.num_agents:
            raise ValueError(
                "FlattenMultiAgentVecEnv construído com num_agents=%d, mas o "
                "ambiente devolve %d agentes por arena. O reshape juntaria "
                "observações de agentes diferentes na mesma linha — corrigir "
                "`environment.num_agents` no config."
                % (self.num_agents, obs.shape[1]))

    def reset(self):
        obs = self.venv.reset()
        self._verificar_forma(obs)
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
        self._task_ep_buf            = []   # task-only reward per episode

    def _on_training_start(self):
        self.start_time = time.time()

    def _on_step(self):
        elapsed_time = time.time() - self.start_time

        # Acumular task reward (sem shaping) quando episódios terminam
        for info in self.locals.get("infos", []):
            if "episode" in info and "task_reward" in info:
                self._task_ep_buf.append(info["task_reward"])

        if self.n_calls % self.log_interval == 0:
            if len(self.model.ep_info_buffer) > 0:
                ep_rew_mean  = np.mean([ep["r"] for ep in self.model.ep_info_buffer])
                task_rew_mean = (np.mean(self._task_ep_buf)
                                 if self._task_ep_buf else 0.0)
                self._task_ep_buf.clear()
                with open(self.log_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_timesteps, ep_rew_mean,
                                     task_rew_mean, elapsed_time])

        # Checkpoint periódico (evita perder 8h de treino por crash)
        if (self.checkpoint_dir and
                elapsed_time - self._last_checkpoint_time >= self.checkpoint_interval_sec):
            ckpt = os.path.join(self.checkpoint_dir,
                                f"ppo_ckpt_{int(elapsed_time // 60):04d}min")
            self.model.save(ckpt)
            print(f"[CKPT] Checkpoint guardado: {ckpt}.zip")
            self._last_checkpoint_time = elapsed_time

        if elapsed_time >= self.time_limit:
            print(f"\n[FIM DO TEMPO] ({self.time_limit / 60:.1f} minutos). A gravar modelo...")
            return False

        return True


def make_env(config_path, seed=None, rank=0):
    def _init():
        # Cada subprocesso semeia o seu np.random para arenas distintas mas
        # reproduzíveis (seed=None mantém o comportamento aleatório anterior).
        if seed is not None:
            np.random.seed(seed + rank)
        raw_env = SwarmForagingEnv3D(config_path)
        wrapped_env = MultiAgentArenaWrapper(raw_env)
        return wrapped_env
    return _init


def train_ppo_3d(time_limit_minutes, seed=None, config_path=None):
    # Ver a nota igual no train_sac_3d: sem config_path, correr isto noutro
    # cenário obriga a editar o configs/foraging.yaml partilhado. Omitir mantém
    # o caminho de sempre.
    config_path = config_path or os.path.join(
        os.path.dirname(__file__), '../../configs/foraging.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    ppo_config = config.get('ppo', {})
    num_cpu = ppo_config.get('num_cpu', 8)
    log_interval = ppo_config.get('log_interval', 2000)

    # Sufixo do cenário para não sobrescrever modelos entre cenários.
    scenario = config['environment'].get('classic_scenario', 'none')
    model_suffix = f"_{scenario}" if scenario and scenario != "none" else ""

    time_limit_seconds = time_limit_minutes * 60
    print(f"[START] PPO 3D a iniciar com {num_cpu} NÚCLEOS EM PARALELO! Orçamento: {time_limit_minutes} min.")

    env = SubprocVecEnv([make_env(config_path, seed, i) for i in range(num_cpu)])
    env = FlattenMultiAgentVecEnv(env, config['environment'].get('num_agents', 25))
    env = VecMonitor(env)

    log_dir = os.path.join(os.path.dirname(__file__), '../../results/logs_ppo')
    model_dir = os.path.join(os.path.dirname(__file__), '../../results/models_ppo')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'training_history_ppo_3d.csv')
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timesteps', 'ep_rew_mean', 'ep_task_mean', 'time'])

    os.chmod(log_file, 0o666)

    ckpt_interval = int(ppo_config.get('checkpoint_interval_min', 30) * 60)

    model = PPO(
        "MlpPolicy", env,
        learning_rate=ppo_config.get("learning_rate", 1e-4),
        n_steps=ppo_config.get("n_steps", 64),
        batch_size=ppo_config.get("batch_size", 512),
        n_epochs=ppo_config.get("n_epochs", 4),
        policy_kwargs=dict(net_arch=ppo_config.get("net_arch", [256, 256])),
        verbose=1,
        device="auto",
        seed=seed,
    )
    callback = TimeLimitAndLoggingCallback(
        log_file, time_limit_seconds, log_interval,
        checkpoint_dir=model_dir, checkpoint_interval_sec=ckpt_interval)

    print(f"[RUNNING] Simulação PPO a correr nos {num_cpu} clones da arena...")
    model.learn(total_timesteps=100000000, callback=callback)

    model_path = os.path.join(model_dir, f"ppo_3d_final{model_suffix}")
    model.save(model_path)
    os.chmod(model_path + ".zip", 0o666)

    # Preserva o modelo DESTE run: em treinos multi-run o ..._final é
    # sobrescrito pelo último run (armadilha nº8) — sem isto, os runs
    # anteriores perdem-se e a avaliação por run fica impossível.
    if seed is not None:
        run_path = os.path.join(model_dir, f"ppo_3d_final{model_suffix}_run{seed}")
        model.save(run_path)
        os.chmod(run_path + ".zip", 0o666)
    print(f"[DONE] Treino PPO 3D Multi-Core concluído! Modelo: {os.path.basename(model_path)}.zip")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=None,
                        help="Semente de reprodutibilidade (omitir = aleatorio)")
    parser.add_argument("--config", type=str, default=None,
                        help="Caminho do config YAML (default: configs/foraging.yaml). "
                             "Permite correr um treino isolado sem mexer no config "
                             "partilhado — o mesmo que o evo_trainer_3d já aceitava.")
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    train_ppo_3d(time_limit_minutes=args.time_limit, seed=args.seed,
                 config_path=args.config)