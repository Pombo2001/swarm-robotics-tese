"""Runner headless da simulação para a vista «Ao vivo (3D)» do dashboard.

Substitui os visualizadores Ursina (visualization/visualize_*.py) como ponto de
entrada do dia-a-dia: a mesma simulação (env + modelo treinado, um forward por passo),
mas sem janela nativa — o estado é devolvido como dicts/np.arrays e desenhado no
browser via ui.scene (three.js). Era a última razão para manter o launcher antigo.

Notas de fidelidade (para não divergir dos visualizadores originais):
  - GNN: UM forward em batch para todos os agentes (igual a visualize_gnn.py).
  - PPO/SAC: predict determinístico da Stable-Baselines3.
  - Escolha do modelo: sufixo do cenário com fallback para o modelo sem sufixo —
    a MESMA convenção dos visualizadores e da avaliação.
  - O cenário é injetado com config em memória (o env aceita config=dict);
    NUNCA se reescreve o configs/foraging.yaml só para mudar de cenário.
"""
import os

import numpy as np
import yaml

from . import config as dashcfg

BASE = dashcfg.BASE_DIR
CONFIG_PATH = os.path.join(BASE, "configs", "foraging.yaml")


def _suffix(scenario: str) -> str:
    return f"_{scenario}" if scenario and scenario != "none" else ""


def model_path_for(algo: str, scenario: str):
    """Caminho do modelo para (algo, cenário) com fallback para o sem sufixo.

    Devolve (path, usou_fallback). `usou_fallback=True` significa que o cenário
    pedido não tem modelo próprio — a vista TEM de o dizer (proveniência), senão
    o utilizador vê um modelo do Sandbox a tropeçar num labirinto e conclui que
    o treino está mau.
    """
    suf = _suffix(scenario)
    if algo == "gnn":
        p = os.path.join(BASE, "results", "models", f"gnn_3d_best{suf}.pth")
        fb = os.path.join(BASE, "results", "models", "gnn_3d_best.pth")
    elif algo == "ppo":
        p = os.path.join(BASE, "results", "models_ppo", f"ppo_3d_final{suf}.zip")
        fb = os.path.join(BASE, "results", "models_ppo", "ppo_3d_final.zip")
    else:
        p = os.path.join(BASE, "results", "models_sac", f"sac_3d_final{suf}.zip")
        fb = os.path.join(BASE, "results", "models_sac", "sac_3d_final.zip")
    if os.path.exists(p):
        return p, False
    return fb, True


class SimRunner:
    """Simulação de um modelo treinado, sem renderização."""

    def __init__(self, algo: str, scenario: str):
        # imports pesados só quando a vista é usada (torch/SB3 atrasariam o arranque)
        import torch
        from src.environment.swarm_env_3d import SwarmForagingEnv3D

        self._torch = torch
        self.algo = algo
        self.scenario = scenario

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        cfg["environment"]["classic_scenario"] = scenario
        self.env = SwarmForagingEnv3D(config=cfg)
        self.env.render_mode = None
        self.obs, _ = self.env.reset()

        self.model_path, self.fallback = model_path_for(algo, scenario)
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Sem modelo para {algo}/{scenario}: {self.model_path}")

        if algo == "gnn":
            from src.agents.gnn_agent_3d import GNNAgent3D
            self.agent = GNNAgent3D("live", self.env.action_space("robot_0"), CONFIG_PATH)
            self.agent.load_state_dict(torch.load(self.model_path, weights_only=True))
            self.agent.eval()
        elif algo == "ppo":
            from stable_baselines3 import PPO
            self.agent = PPO.load(self.model_path[:-4], device="cpu")
        else:
            from stable_baselines3 import SAC
            self.agent = SAC.load(self.model_path[:-4], device="cpu")

        self.steps = 0
        self.episodes = 0

    # ── um tick da vista = n passos de simulação ─────────────────────────────
    def step(self, n: int = 1):
        env, torch = self.env, self._torch
        for _ in range(max(1, n)):
            ids = list(env.agents)
            if self.algo == "gnn":
                batch = torch.tensor(np.stack(
                    [np.asarray(self.obs[a], dtype=np.float32) for a in ids]))
                with torch.no_grad():
                    acts = self.agent(batch).numpy()
                actions = {aid: acts[k] for k, aid in enumerate(ids)}
            else:
                batch = np.stack([np.asarray(self.obs[a], dtype=np.float32) for a in ids])
                acts, _ = self.agent.predict(batch, deterministic=True)
                actions = {aid: acts[k] for k, aid in enumerate(ids)}

            self.obs, _r, terms, _t, _i = env.step(actions)
            self.steps += 1
            if any(terms.values()):
                self.obs, _ = env.reset()
                self.episodes += 1
                break
        return self.snapshot()

    def snapshot(self):
        """Estado mínimo para desenhar: posições + sinais + contadores."""
        env = self.env
        return {
            "agents": np.asarray(env.agent_positions, dtype=float),
            "signaling": np.asarray(env.signaling, dtype=float),
            "nest": np.asarray(env.nest_pos, dtype=float),
            "obstacles": np.asarray(env.obstacles, dtype=float),
            "walls": [(np.asarray(w["pos"], dtype=float),
                       np.asarray(w["size"], dtype=float)) for w in env.walls],
            "food": int(env.total_food_collected),
            "steps": self.steps,
            "episodes": self.episodes,
        }

    # geometria fixa, para construir a cena uma única vez
    @property
    def arena_radius(self):
        return float(self.env.arena_radius)

    @property
    def nest_radius(self):
        return float(self.env.nest_radius)

    @property
    def robot_radius(self):
        return float(self.env.robot_radius)

    @property
    def obstacle_radius(self):
        return float(self.env.obstacle_radius)

    @property
    def door_wall_index(self):
        return getattr(self.env, "door_wall_index", None) \
            if self.scenario in ("cooperative_door", "cooperative_door_bypass") else None
