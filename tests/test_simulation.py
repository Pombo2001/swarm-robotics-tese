"""
Smoke test funcional do simulador 3D + agente GNN.

Valida, sem abrir janela gráfica, que:
  - o ambiente reseta e produz observações com a dimensão esperada;
  - um passo (step) devolve a estrutura correta (obs, rewards, terms, truncs, infos);
  - o GNNAgent3D produz ações com a forma certa a partir das observações;
  - vários passos correm sem exceções em todos os cenários.

Pode correr-se diretamente (`python tests/test_simulation.py`) ou via pytest.
"""
import os
import sys

import numpy as np
import torch

# Tornar o pacote `src` importável independentemente de onde se corre o teste.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')
SCENARIOS = ['none', 'u_wall', 'bottleneck', 'four_rooms',
             'cooperative_door', 'cooperative_perception', 'cooperative_door_bypass']


def _make_env(scenario='none'):
    env = SwarmForagingEnv3D(config_path=CONFIG_PATH)
    env.config['environment']['classic_scenario'] = scenario
    return env


def test_reset_observation_shape():
    """O reset devolve uma observação por agente com a dimensão correta."""
    env = _make_env('none')
    obs_dict, info = env.reset()

    assert isinstance(obs_dict, dict)
    assert len(obs_dict) == env.num_agents

    expected_dim = 16 + (env.num_agents - 1) * 5
    for agent_id in env.agents:
        assert obs_dict[agent_id].shape == (expected_dim,), (
            f"{agent_id}: esperado {expected_dim}, obtido {obs_dict[agent_id].shape}")
    # Tem de bater certo com o espaço de observação declarado.
    assert env.observation_space_val.shape == (expected_dim,)


def test_step_contract():
    """Um step devolve as 5 estruturas do Gymnasium com as chaves dos agentes."""
    env = _make_env('none')
    obs_dict, _ = env.reset()

    actions = {a: env.action_space_val.sample() for a in env.agents}
    obs_dict, rewards, terms, truncs, infos = env.step(actions)

    for d in (obs_dict, rewards, terms, truncs, infos):
        assert set(d.keys()) == set(env.agents)
    assert all(np.isfinite(r) for r in rewards.values())


def test_gnn_agent_action_shape():
    """O GNNAgent3D produz ações em [-1, 1] com forma (num_agents, 3)."""
    env = _make_env('none')
    obs_dict, _ = env.reset()
    agent = GNNAgent3D("tester", env.action_space("robot_0"), CONFIG_PATH)

    obs_batch = torch.tensor(
        np.array([obs_dict[a] for a in env.agents]), dtype=torch.float32)
    with torch.no_grad():
        actions = agent(obs_batch).cpu().numpy()

    assert actions.shape == (env.num_agents, 3)
    assert np.all(actions >= -1.0) and np.all(actions <= 1.0)


def test_all_scenarios_run():
    """Cada cenário reseta e corre alguns passos sem exceções."""
    for scenario in SCENARIOS:
        env = _make_env(scenario)
        obs_dict, _ = env.reset()
        for _ in range(20):
            actions = {a: env.action_space_val.sample() for a in env.agents}
            obs_dict, rewards, terms, truncs, infos = env.step(actions)
            if any(terms.values()) or any(truncs.values()):
                break


if __name__ == "__main__":
    tests = [
        test_reset_observation_shape,
        test_step_contract,
        test_gnn_agent_action_shape,
        test_all_scenarios_run,
    ]
    falhas = 0
    for t in tests:
        try:
            t()
            print(f"[OK]  {t.__name__}")
        except Exception as e:
            falhas += 1
            print(f"[FALHOU] {t.__name__}: {e}")
    print(f"\n{len(tests) - falhas}/{len(tests)} testes passaram.")
    sys.exit(1 if falhas else 0)
