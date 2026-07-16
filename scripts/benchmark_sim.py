# -*- coding: utf-8 -*-
"""Benchmark do simulador — fonte da tab:res_computacional da tese.

Protocolo (o mesmo da medição original): 1 arena, N=20 agentes, ações aleatórias,
3 000 passos cronometrados após 200 de aquecimento, single-thread.

Uso:  python scripts/benchmark_sim.py [--passos 3000]

Histórico de medições (máquina de desenvolvimento, cenário base 'none'):
- pré-vetorização (jun 2026):  ~139 passos/s  (~2 770 agente-passos/s)
- pós-vetorização (16 jul 2026): ~419 passos/s (~8 370 agente-passos/s)
  → ganho ~3,0×, consistente com o 2,58× medido no custo do passo
    (tests/test_obs_equivalence.py) mais variabilidade de máquina.
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Benchmark single-thread do simulador')
    parser.add_argument('--passos', type=int, default=3000)
    args = parser.parse_args()

    config = os.path.join(os.path.dirname(__file__), '..', 'configs', 'foraging.yaml')
    env = SwarmForagingEnv3D(config_path=config)
    n = env.num_agents

    def acoes():
        return {a: np.random.uniform(-1, 1, 3).astype(np.float32) for a in env.agents}

    env.reset(seed=42)
    for _ in range(200):  # aquecimento
        env.step(acoes())
    env.reset(seed=43)

    t0 = time.perf_counter()
    for _ in range(args.passos):
        env.step(acoes())
        if env.steps >= env.max_steps:
            env.reset()
    dt = time.perf_counter() - t0

    sps = args.passos / dt
    print(f'N={n} agentes | {args.passos} passos em {dt:.1f}s')
    print(f'-> {sps:.1f} passos/s | {sps * n:.0f} agente-passos/s | '
          f'episódio de 500 passos ~ {500 / sps:.2f}s')


if __name__ == '__main__':
    main()
