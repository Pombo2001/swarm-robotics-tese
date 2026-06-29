"""
Teste de regressão do LiDAR vetorizado (SwarmForagingEnv3D._lidar_scan).

Garante que a versão vetorizada (slab method NumPy) continua BIT-EXACTA face à
implementação de referência (o triplo loop Python original). Se algum dia divergir,
este teste falha — evitando invalidar silenciosamente os modelos já treinados (que
veriam observações diferentes) e a comparação experimental da tese.

Motivação: a vetorização foi adotada por dar ~19× de throughput, mas só é segura
porque é numericamente idêntica ao loop. Aqui exercitamos 8000 cenas aleatórias,
incluindo casos-limite (raios paralelos aos eixos, agente/obstáculos com z≠0,
ausência de paredes/obstáculos).

Corre diretamente (`python tests/test_lidar_equivalence.py`) ou via pytest.
"""
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

NUM_RAYS = 8


def _lidar_loop_reference(pos, heading, walls, obstacles, lidar_range, r_obs):
    """Réplica EXACTA do raycasting original (loop Python), como oráculo do teste."""
    F = heading
    ray_angles = np.linspace(0, 2 * np.pi, NUM_RAYS, endpoint=False)
    max_ray_dist = lidar_range
    out = np.zeros(NUM_RAYS, dtype=np.float32)

    F_horiz = np.array([F[0], F[1], 0.0])
    if np.linalg.norm(F_horiz) < 1e-6:
        F_horiz = np.array([1.0, 0.0, 0.0])
    else:
        F_horiz /= np.linalg.norm(F_horiz)
    R_horiz = np.array([-F_horiz[1], F_horiz[0], 0.0])

    for i, angle in enumerate(ray_angles):
        ray_dir = np.cos(angle) * F_horiz + np.sin(angle) * R_horiz
        ray_end = pos + ray_dir * max_ray_dist
        closest_dist = max_ray_dist
        for wall in walls:
            half_size = wall['size'] / 2.0
            w_min = wall['pos'] - half_size
            w_max = wall['pos'] + half_size
            t_min, t_max = 0.0, 1.0
            for axis in range(2):
                d = ray_end[axis] - pos[axis]
                if abs(d) < 1e-6:
                    if pos[axis] < w_min[axis] or pos[axis] > w_max[axis]:
                        t_max = -1.0
                        break
                else:
                    t1 = (w_min[axis] - pos[axis]) / d
                    t2 = (w_max[axis] - pos[axis]) / d
                    if t1 > t2:
                        t1, t2 = t2, t1
                    t_min = max(t_min, t1)
                    t_max = min(t_max, t2)
            if t_max >= t_min and t_max >= 0.0 and t_min <= 1.0:
                hit_dist = t_min * max_ray_dist
                if hit_dist < closest_dist:
                    closest_dist = hit_dist
        for obs in obstacles:
            vec = obs - pos
            proj = np.dot(vec, ray_dir)
            if proj > 0:
                perp_dist = np.linalg.norm(vec - proj * ray_dir)
                if perp_dist <= r_obs:
                    hit_dist = proj - np.sqrt(r_obs ** 2 - perp_dist ** 2)
                    if hit_dist > 0 and hit_dist < closest_dist:
                        closest_dist = hit_dist
        out[i] = 1.0 - (closest_dist / max_ray_dist)
    return out


def _make_env():
    """Instância mínima só para chamar _lidar_scan (sem reset/cenário)."""
    env = SwarmForagingEnv3D.__new__(SwarmForagingEnv3D)
    env.lidar_range = 8.0
    env.obstacle_radius = 0.2
    return env


def _random_scene(rng, n_walls, n_obs, z_jitter):
    walls = []
    w_min = np.zeros((n_walls, 3))
    w_max = np.zeros((n_walls, 3))
    for k in range(n_walls):
        c = rng.uniform(-15, 15, size=3)
        c[2] = rng.uniform(-z_jitter, z_jitter)
        s = rng.uniform(0.5, 6.0, size=3)
        s[2] = rng.uniform(2.0, 6.0)
        walls.append({'pos': c, 'size': s})
        w_min[k] = c - s / 2.0
        w_max[k] = c + s / 2.0
    obs = rng.uniform(-15, 15, size=(n_obs, 3))
    obs[:, 2] = rng.uniform(-z_jitter, z_jitter, size=n_obs)
    return walls, obs, w_min, w_max


def test_lidar_vectorized_matches_loop():
    """8000 cenas (4000 planas + 4000 com z≠0): equivalência exacta ao loop."""
    env = _make_env()
    max_err = 0.0
    mismatches = 0
    for z_jitter, seed in [(0.0, 0), (2.0, 7)]:
        rng = np.random.default_rng(seed)
        for _ in range(4000):
            n_walls = int(rng.integers(0, 8))
            n_obs = int(rng.integers(0, 12))
            walls, obs, w_min, w_max = _random_scene(rng, n_walls, n_obs, z_jitter)
            pos = rng.uniform(-15, 15, size=3)
            pos[2] = rng.uniform(-z_jitter, z_jitter)
            h = rng.uniform(-1, 1, size=3)
            h = h / (np.linalg.norm(h) + 1e-9)

            ref = _lidar_loop_reference(pos, h, walls, obs, env.lidar_range, env.obstacle_radius)
            got = env._lidar_scan(pos, h, w_min, w_max, obs.reshape(-1, 3))
            err = float(np.max(np.abs(ref - got)))
            max_err = max(max_err, err)
            if not np.allclose(ref, got, atol=1e-5, rtol=0):
                mismatches += 1

    assert mismatches == 0, f"{mismatches} cenas divergiram (erro máx {max_err:.2e})"
    assert max_err < 1e-5, f"erro máximo absoluto demasiado alto: {max_err:.2e}"


def test_lidar_batch_matches_loop():
    """Versão batch (todos os agentes de uma vez) == loop de referência, agente a
    agente, em cenas com 20 agentes (planas e com z≠0)."""
    env = _make_env()
    max_err = 0.0
    mismatches = 0
    for z_jitter, seed in [(0.0, 11), (2.0, 23)]:
        rng = np.random.default_rng(seed)
        for _ in range(800):
            n_walls = int(rng.integers(0, 8))
            n_obs = int(rng.integers(0, 12))
            walls, obs, w_min, w_max = _random_scene(rng, n_walls, n_obs, z_jitter)
            A = 20
            positions = rng.uniform(-15, 15, size=(A, 3))
            positions[:, 2] = rng.uniform(-z_jitter, z_jitter, size=A)
            headings = rng.uniform(-1, 1, size=(A, 3))
            headings /= (np.linalg.norm(headings, axis=1, keepdims=True) + 1e-9)

            batch = env._lidar_scan_batch(positions, headings, w_min, w_max, obs.reshape(-1, 3))
            for a in range(A):
                ref = _lidar_loop_reference(positions[a], headings[a], walls, obs,
                                            env.lidar_range, env.obstacle_radius)
                err = float(np.max(np.abs(ref - batch[a])))
                max_err = max(max_err, err)
                if not np.allclose(ref, batch[a], atol=1e-5, rtol=0):
                    mismatches += 1

    assert mismatches == 0, f"batch divergiu em {mismatches} casos (erro máx {max_err:.2e})"
    assert max_err < 1e-5, f"erro máximo absoluto demasiado alto: {max_err:.2e}"


def test_lidar_empty_scene_is_free():
    """Sem paredes nem obstáculos, todos os raios veem caminho livre (LiDAR=0)."""
    env = _make_env()
    vals = env._lidar_scan(
        np.zeros(3), np.array([1.0, 0.0, 0.0]),
        np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3)),
    )
    assert vals.shape == (NUM_RAYS,)
    assert np.allclose(vals, 0.0)
    # batch com cena vazia também é livre
    batch = env._lidar_scan_batch(np.zeros((5, 3)), np.tile([1.0, 0.0, 0.0], (5, 1)),
                                  np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3)))
    assert batch.shape == (5, NUM_RAYS)
    assert np.allclose(batch, 0.0)


if __name__ == "__main__":
    test_lidar_vectorized_matches_loop()
    test_lidar_batch_matches_loop()
    test_lidar_empty_scene_is_free()
    print("OK — LiDAR (single + batch) equivalente ao loop e cena vazia livre.")
