"""
Teste de regressão das observações vetorizadas (SwarmForagingEnv3D._get_observations).

Garante que a construção vetorizada das observações egocêntricas (bases F/R/U +
projeções de ninho/porta/vizinhos em batch) continua BIT-EXACTA face à implementação
de referência (o loop Python por-agente original). Se divergir, este teste falha —
evitando invalidar silenciosamente os modelos já treinados (que veriam observações
diferentes) e a comparação experimental da tese.

Motivação: a vetorização foi adotada por dar ~6× em _get_observations (~2.6× no
step() inteiro), mas só é segura porque é numericamente idêntica ao loop. Aqui
exercitamos os 7 cenários × várias cenas perturbadas, comparando o dict de
observações completo contra o oráculo.

Corre diretamente (`python tests/test_obs_equivalence.py`) ou via pytest.
"""
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

SCENARIOS = ["none", "u_wall", "bottleneck", "four_rooms",
             "cooperative_door", "cooperative_door_bypass", "cooperative_perception"]


def _obs_loop_reference(env):
    """Réplica EXACTA do loop por-agente original, como oráculo do teste. Reusa o
    LiDAR batch (idêntico) e reconstrói só a parte egocêntrica com loop Python."""
    observations = {}
    if env.walls:
        w_min_arr = np.array([w['pos'] - w['size'] / 2.0 for w in env.walls])
        w_max_arr = np.array([w['pos'] + w['size'] / 2.0 for w in env.walls])
    else:
        w_min_arr = np.zeros((0, 3))
        w_max_arr = np.zeros((0, 3))
    obs_arr = np.asarray(env.obstacles, dtype=float).reshape(-1, 3)
    lidar_all = env._lidar_scan_batch(
        np.asarray(env.agent_positions, dtype=float),
        np.asarray(env.agent_headings, dtype=float),
        w_min_arr, w_max_arr, obs_arr,
    )
    for idx, agent in enumerate(env.agents):
        pos = env.agent_positions[idx]
        heading = env.agent_headings[idx]

        F = heading
        W = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(F, W)) > 0.99:
            W = np.array([0.0, 1.0, 0.0])
        R = np.cross(F, W)
        R = R / (np.linalg.norm(R) + 1e-6)
        U = np.cross(R, F)

        def to_egocentric(target_pos):
            vec = target_pos - pos
            dist = np.linalg.norm(vec)
            if dist < 1e-6:
                return np.array([0.0, 0.0, 0.0]), 0.0
            dir_w = vec / dist
            return np.array([np.dot(dir_w, F), np.dot(dir_w, R), np.dot(dir_w, U)]), dist

        local_dir_nest, dist_nest = to_egocentric(env.nest_pos)
        norm_dist_nest = dist_nest / (env.arena_radius * 2)
        lidar_sensor_vals = lidar_all[idx]

        if env.classic_scenario in ("cooperative_door", "cooperative_door_bypass"):
            local_dir_door, dist_door = to_egocentric(env.door_pos)
            norm_dist_door = dist_door / (env.arena_radius * 2)
        else:
            local_dir_door, norm_dist_door = np.array([0.0, 0.0, 0.0]), 0.0

        neighbor_feats = []
        for j, other_pos in enumerate(env.agent_positions):
            if idx == j:
                continue
            local_dir_neigh, dist_neigh = to_egocentric(other_pos)
            norm_dist_neigh = dist_neigh / (env.arena_radius * 2)
            neighbor_feats.extend(list(local_dir_neigh) + [norm_dist_neigh, env.signaling[j]])

        obs = np.concatenate([
            local_dir_nest, [norm_dist_nest],
            lidar_sensor_vals,
            local_dir_door, [norm_dist_door],
            np.array(neighbor_feats)
        ]).astype(np.float32)
        observations[agent] = obs
    return observations


def test_obs_vectorized_matches_loop():
    """Os 7 cenários × cenas perturbadas: equivalência exacta ao loop por-agente."""
    rng = np.random.default_rng(0)
    max_err = 0.0
    mismatches = 0
    total = 0
    for scen in SCENARIOS:
        env = SwarmForagingEnv3D()
        env.config['environment']['classic_scenario'] = scen
        env.reset()
        for _ in range(200):
            # perturba posições/headings/sinalização para variar as cenas
            env.agent_positions = env.agent_positions + rng.uniform(-0.3, 0.3, env.agent_positions.shape)
            h = rng.uniform(-1, 1, env.agent_headings.shape)
            n = np.linalg.norm(h, axis=1, keepdims=True)
            env.agent_headings = h / np.where(n > 1e-9, n, 1.0)
            env.signaling = rng.integers(0, 2, env.num_agents).astype(float)

            ref = _obs_loop_reference(env)
            got = env._get_observations()
            for k in ref:
                assert ref[k].shape == got[k].shape, f"shape {scen}/{k}: {ref[k].shape} vs {got[k].shape}"
                err = float(np.max(np.abs(ref[k] - got[k]))) if ref[k].size else 0.0
                max_err = max(max_err, err)
                if not np.allclose(ref[k], got[k], atol=1e-5, rtol=0):
                    mismatches += 1
                total += 1

    assert mismatches == 0, f"{mismatches}/{total} observações divergiram (erro máx {max_err:.2e})"
    assert max_err < 1e-5, f"erro máximo absoluto demasiado alto: {max_err:.2e}"


def test_obs_self_excluded_and_dim_stable():
    """A observação tem dimensão estável e exclui o próprio agente dos vizinhos."""
    env = SwarmForagingEnv3D()
    env.config['environment']['classic_scenario'] = "none"
    env.reset()
    obs = env._get_observations()
    A = env.num_agents
    # nest(3)+1 + lidar(8) + door(3)+1 + vizinhos((A-1)*5)
    expected = 3 + 1 + 8 + 3 + 1 + (A - 1) * 5
    dims = {v.shape[0] for v in obs.values()}
    assert dims == {expected}, f"dim inesperada: {dims} (esperado {expected})"


if __name__ == "__main__":
    test_obs_vectorized_matches_loop()
    test_obs_self_excluded_and_dim_stable()
    print("OK — observações vetorizadas equivalentes ao loop por-agente.")
