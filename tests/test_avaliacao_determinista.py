# -*- coding: utf-8 -*-
"""A avaliação é mesmo determinística e emparelhada?

Toda a inferência da tese assenta nisto: «avaliação determinística emparelhada
(20 episódios com sementes fixas)». Se a mesma chamada devolvesse números
diferentes, os p-values comparariam ruído; se dois algoritmos vissem mundos
diferentes com a mesma seed, o emparelhamento seria falso.

Nunca tinha sido testado — verificava-se lendo o código, que é onde as duas
propriedades *parecem* estar garantidas.
"""
import os
import sys

import numpy as np
import pytest
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from scripts.eval_all import run_episode  # noqa: E402
from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

CFG = os.path.join(RAIZ, "configs", "foraging.yaml")


class _Politica:
    """Determinística e sem estado: isola o ambiente do controlador."""

    def __init__(self, escala=0.4):
        self.escala = escala

    def __call__(self, obs):
        import torch
        t = obs if hasattr(obs, "shape") else torch.tensor(obs)
        # função das observações, não do acaso
        return torch.tanh(t[:, :3] * self.escala)


def _env(cenario):
    with open(CFG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = cenario
    return SwarmForagingEnv3D(config=cfg)


@pytest.mark.parametrize("cenario", ["u_wall", "bottleneck", "mapa_grande"])
def test_mesma_seed_mesmo_resultado(cenario):
    """Duas execuções com a mesma seed dão o mesmo episódio, ao bit."""
    a = run_episode(_env(cenario), "gnn", _Politica(), seed=1000)
    b = run_episode(_env(cenario), "gnn", _Politica(), seed=1000)
    assert a == b, f"{cenario}: a mesma seed deu resultados diferentes\n{a}\n{b}"


def test_seeds_diferentes_dao_episodios_diferentes():
    """O contrário também importa: se a seed não mudasse nada, não haveria
    variabilidade nenhuma para medir e as 20 amostras seriam uma só."""
    vistos = {tuple(sorted(run_episode(_env("u_wall"), "gnn", _Politica(),
                                       seed=s).items())) for s in (1000, 1001, 1002)}
    assert len(vistos) > 1, "seeds diferentes deram exatamente o mesmo episódio"


@pytest.mark.parametrize("cenario", ["u_wall", "cooperative_door"])
def test_emparelhamento_mesma_seed_mesmo_mundo(cenario):
    """Com a mesma seed, dois algoritmos encontram o MESMO mundo.

    É o que torna a comparação emparelhada legítima: posições iniciais,
    obstáculos e ninho têm de coincidir antes de a política agir. Sem isto, o
    «emparelhado» da tese seria só uma palavra.
    """
    e1, e2 = _env(cenario), _env(cenario)
    e1.reset(seed=4242)
    e2.reset(seed=4242)
    assert np.allclose(e1.agent_positions, e2.agent_positions)
    assert np.allclose(e1.nest_pos, e2.nest_pos)
    assert len(e1.obstacles) == len(e2.obstacles)
    if len(e1.obstacles):
        assert np.allclose(np.asarray(e1.obstacles), np.asarray(e2.obstacles))
    assert len(e1.walls) == len(e2.walls)


def test_reset_sem_seed_nao_repete():
    """Um reset sem seed tem de dar mundos diferentes — senão a «seed fixa» da
    avaliação não estaria a fazer nada e ninguém daria por isso."""
    e = _env("none")
    e.reset(seed=None)
    p1 = e.agent_positions.copy()
    e.reset(seed=None)
    assert not np.allclose(p1, e.agent_positions), \
        "dois resets sem seed deram o mesmo mundo"
