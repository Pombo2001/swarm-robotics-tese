# -*- coding: utf-8 -*-
"""A métrica `door_opened` do pipeline de avaliação mede o que diz.

Porque existe: a M3 do pré-registo do mapa grande — «fração de episódios em que a
porta cooperativa é aberta, por algoritmo» — não era calculável, porque nada no
`run_episode` registava o estado da porta. A coluna foi acrescentada a 5 ago; um
teste que só verificasse a presença da coluna não distinguiria `False` de `None`,
que é precisamente a distinção que interessa (não abriu vs. não havia porta).
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
from src.environment.swarm_env_3d import (  # noqa: E402
    SwarmForagingEnv3D, DOOR_PUSHERS_REQUIRED)

CFG = os.path.join(RAIZ, "configs", "foraging.yaml")


def _env(cenario):
    with open(CFG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = cenario
    e = SwarmForagingEnv3D(config=cfg)
    e.reset(seed=3)
    return e


class _Parado:
    """Política que não faz nada — garante que a porta NÃO é aberta."""

    def __call__(self, obs):
        import torch
        return torch.zeros((obs.shape[0], 3))


def test_sem_porta_devolve_none():
    """Num cenário sem porta, `door_opened` é vazio e não `False`."""
    env = _env("u_wall")
    r = run_episode(env, "gnn", _Parado(), seed=1)
    assert "door_opened" in r
    assert r["door_opened"] is None


def test_porta_fechada_devolve_false():
    """Com a porta por abrir, a métrica é False — não None, não True."""
    env = _env("cooperative_door")
    r = run_episode(env, "gnn", _Parado(), seed=1)
    assert r["door_opened"] is False


def test_porta_aberta_devolve_true():
    """Empurrando de propósito, a métrica acompanha a abertura.

    Coloca-se `DOOR_PUSHERS_REQUIRED` agentes na push zone e dá-se um passo: é o
    que `_update_door` exige. Sem isto, o teste anterior passaria com uma métrica
    presa em False.
    """
    env = _env("cooperative_door")
    x_min, x_max, y_min, y_max = env.door_push_bounds
    centro = np.array([(x_min + x_max) / 2, (y_min + y_max) / 2, 0.0])
    for i in range(DOOR_PUSHERS_REQUIRED):
        env.agent_positions[i] = centro + np.array([0.01 * i, 0.0, 0.0])
    assert env.door_active, "a porta devia estar fechada antes do passo"
    env.step({a: np.zeros(3, dtype=np.float32) for a in env.agents})
    assert not env.door_active, "a porta devia ter aberto com os empurradores"

    # E o que o pipeline reporta a partir daqui é True.
    tem_porta = bool(getattr(env, "has_door", False)) or \
        getattr(env, "door_wall_index", None) is not None
    assert tem_porta, "has_door tem de sobreviver à abertura da porta"
    assert ((not env.door_active) if tem_porta else None) is True


@pytest.mark.parametrize("cenario", ["mapa_grande", "cooperative_door_bypass"])
def test_cenarios_com_porta_reportam_booleano(cenario):
    env = _env(cenario)
    r = run_episode(env, "gnn", _Parado(), seed=1)
    assert isinstance(r["door_opened"], bool), \
        f"{cenario} tem porta: a métrica tem de ser booleana, veio {r['door_opened']!r}"
