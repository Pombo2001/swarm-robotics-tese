# -*- coding: utf-8 -*-
"""Testes do mecanismo da porta cooperativa (cooperative_door / _bypass).

Contrato testado (ver constantes DOOR_* em swarm_env_3d.py):
- no reset a porta está fechada (painel presente em walls);
- com 2 agentes na push zone NÃO abre; com 3 abre;
- abrir remove o painel de self.walls e recompensa (+DOOR_OPEN_REWARD) apenas
  quem empurrou; agentes falhados (Rrobust) não contam;
- cenários sem porta ficam com has_door/door_active a False.

Uso: .venv/Scripts/python.exe tests/test_door.py
"""
import sys
import os
import copy

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.environment.swarm_env_3d import (
    SwarmForagingEnv3D, DOOR_SCENARIOS, DOOR_PUSHERS_REQUIRED, DOOR_OPEN_REWARD)

CONFIG = os.path.join(os.path.dirname(__file__), "..", "configs", "foraging.yaml")
with open(CONFIG, "r") as f:
    BASE_CFG = yaml.safe_load(f)

PUSH_SPOTS = np.array([[0.6, -1.0, 0.0], [0.0, -1.2, 0.0], [-0.6, -0.8, 0.0]])


def push_spots(env, n=3):
    """n pontos DENTRO da push zone do ambiente, derivados de door_push_bounds.

    Antes o teste usava só os PUSH_SPOTS fixos acima, que assumem a barreira
    horizontal em (0,0) dos cenários cooperativos. O mapa_grande tem a porta
    numa parede VERTICAL e noutro sítio, logo esses pontos caem fora da zona e
    a porta nunca abriria. Derivar da zona real testa qualquer cenário com porta.
    """
    x_min, x_max, y_min, y_max = env.door_push_bounds
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    dx, dy = (x_max - x_min) / 2, (y_max - y_min) / 2
    # espalhados dentro da zona, com folga para a fronteira
    offs = [(-0.4, 0.4), (0.0, 0.0), (0.4, -0.4)]
    return np.array([[cx + ox * dx, cy + oy * dy, 0.0] for ox, oy in offs[:n]])


def make_env(scenario):
    cfg = copy.deepcopy(BASE_CFG)
    cfg["environment"]["classic_scenario"] = scenario
    env = SwarmForagingEnv3D(config=cfg)
    np.random.seed(42)
    env.reset()
    return env


def zero_actions(env):
    return {a: np.zeros(3, dtype=np.float32) for a in env.agents}


def test_fechada_no_reset():
    for scen in DOOR_SCENARIOS:
        env = make_env(scen)
        assert env.has_door and env.door_active, scen
        assert env.door_wall_index == len(env.walls) - 1, scen
    print("OK  porta fechada no reset (painel presente)")


def test_nao_abre_com_menos_agentes():
    env = make_env("cooperative_door")
    env.agent_positions[:DOOR_PUSHERS_REQUIRED - 1] = PUSH_SPOTS[:DOOR_PUSHERS_REQUIRED - 1]
    # afastar os restantes da push zone
    env.agent_positions[DOOR_PUSHERS_REQUIRED - 1:, 1] = -8.0
    env.step(zero_actions(env))
    assert env.door_active, "abriu com menos agentes do que o exigido"
    print(f"OK  não abre com {DOOR_PUSHERS_REQUIRED - 1} agentes")


def test_abre_remove_e_recompensa():
    for scen in DOOR_SCENARIOS:
        env = make_env(scen)
        n_walls = len(env.walls)
        env.agent_positions[:3] = push_spots(env)
        # afastar os restantes da push zone (para lá do limite da zona)
        env.agent_positions[3:, 1] = env.door_push_bounds[2] - 6.0
        _, rewards, *_ = env.step(zero_actions(env))
        assert not env.door_active, scen
        assert len(env.walls) == n_walls - 1, f"{scen}: painel não removido"
        assert env.door_wall_index is None, scen
        pushers = [env.agents[i] for i in range(3)]
        assert all(rewards[a] >= DOOR_OPEN_REWARD for a in pushers), scen
        assert all(rewards[a] < DOOR_OPEN_REWARD for a in env.agents[3:]), scen
    print("OK  abre com 3, remove o painel e recompensa só quem empurrou")


def test_agente_falhado_nao_conta():
    env = make_env("cooperative_door")
    env.agent_positions[:3] = PUSH_SPOTS.copy()
    env.agent_positions[3:, 1] = -8.0
    env.failed[0] = True   # Rrobust: um dos 3 está inerte
    env.step(zero_actions(env))
    assert env.door_active, "agente falhado contou para abrir a porta"
    print("OK  agente falhado (Rrobust) não conta como empurrador")


def test_cenarios_sem_porta():
    for scen in ("none", "u_wall", "bottleneck"):
        env = make_env(scen)
        assert not env.has_door and not env.door_active, scen
        assert env.door_wall_index is None, scen
    print("OK  cenários sem porta: has_door/door_active a False")


if __name__ == "__main__":
    test_fechada_no_reset()
    test_nao_abre_com_menos_agentes()
    test_abre_remove_e_recompensa()
    test_agente_falhado_nao_conta()
    test_cenarios_sem_porta()
    print("\n5/5 testes da porta cooperativa passaram ✅")
