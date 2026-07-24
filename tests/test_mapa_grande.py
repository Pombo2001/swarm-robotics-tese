"""
test_mapa_grande.py — Testes do 8.º cenário (mapa_grande)
=========================================================
Escrito ANTES de o mapa ir a treinar, a pedido do utilizador ("procura erros e
falhas possíveis no mapa"). Cada teste corresponde a um modo de falha concreto
que invalidaria a campanha — não a cobertura por cobertura.

Corre como os outros testes do projeto (script autónomo, não pytest):
    .venv/Scripts/python.exe tests/test_mapa_grande.py
"""
import copy
import os
import sys

import numpy as np
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

CONFIG = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
with open(CONFIG, "r", encoding="utf-8") as f:
    BASE_CFG = yaml.safe_load(f)

MAPA = "mapa_grande"
ROBOT_D = 0.30          # diâmetro do robô (2 x agent_radius)


def make_env(**over):
    cfg = copy.deepcopy(BASE_CFG)
    cfg["environment"]["classic_scenario"] = MAPA
    cfg["environment"].update(over)
    return SwarmForagingEnv3D(config=cfg)


def zero_actions(env):
    return {a: np.zeros(3, dtype=np.float32) for a in env.agents}


def _geo(env, pos):
    R, res = env.arena_radius, env.geo_res
    return env.geo_field[int((pos[0] + R) / res), int((pos[1] + R) / res)]


def test_determinismo():
    """A mesma seed tem de dar exatamente o mesmo mapa — senão a avaliação
    emparelhada (mesmas seeds para os 3 algoritmos) deixa de ser emparelhada."""
    e1, e2 = make_env(), make_env()
    e1.reset(seed=42)
    e2.reset(seed=42)
    assert np.allclose([w["pos"] for w in e1.walls], [w["pos"] for w in e2.walls])
    assert len(e1.obstacles) == len(e2.obstacles), "nº de obstáculos varia com a seed fixa"
    assert np.allclose(e1.obstacles, e2.obstacles)
    assert np.allclose(e1.agent_positions, e2.agent_positions)
    print("OK  determinismo: mesma seed => mesmo mapa, obstáculos e spawn")


def test_resets_consecutivos():
    """No treino o env é reutilizado episódio após episódio. Estado que fique
    pendurado entre resets (porta aberta, paredes a mais) corrompe o episódio
    seguinte sem dar erro."""
    e = make_env()
    n_walls, n_obs = [], []
    for _ in range(5):
        e.reset()
        n_walls.append(len(e.walls))
        n_obs.append(len(e.obstacles))
        assert e.door_active, "porta não voltou a fechar no reset"
        dentro = sum(1 for q in e.agent_positions for w in e.walls
                     if np.all(np.abs(q - w["pos"]) < w["size"] / 2))
        assert dentro == 0, f"{dentro} agentes nasceram DENTRO de paredes"
        fora = sum(1 for q in e.agent_positions
                   if np.linalg.norm(q[:2]) > e.arena_radius)
        assert fora == 0, f"{fora} agentes nasceram fora da arena"
    assert len(set(n_walls)) == 1, f"nº de paredes varia entre episódios: {n_walls}"
    assert len(set(n_obs)) == 1, f"nº de obstáculos varia entre episódios: {n_obs}"
    print("OK  5 resets consecutivos: sem fuga de estado, spawn sempre válido")


def test_ninho_alcancavel():
    """Todos os spawns têm de ter caminho ao ninho. Um só agente sem caminho é
    um run perdido; o campo geodésico infinito também parte o progress reward."""
    e = make_env()
    for seed in (1, 2, 3):
        e.reset(seed=seed)
        d = [_geo(e, q) for q in e.agent_positions]
        assert all(np.isfinite(x) for x in d), f"seed {seed}: agente sem caminho ao ninho"
        assert max(d) < 200, f"seed {seed}: distância implausível ({max(d):.0f} m)"
    print(f"OK  ninho alcançável de todos os spawns (geodésica {min(d):.0f}-{max(d):.0f} m)")


def test_max_steps_suficiente():
    """max_steps tem de chegar para a IDA e ainda sobrar. Sem isto o treino
    aprende que a tarefa não compensa — e a falha é silenciosa."""
    e = make_env()
    e.reset(seed=1)
    d_max = max(_geo(e, q) for q in e.agent_positions)
    passos_ida = d_max / 0.2          # v_max = clip(a,-1,1) * 0.2 m/passo
    folga = e.max_steps / passos_ida
    assert folga >= 2.5, (f"max_steps={e.max_steps} dá folga {folga:.1f}x sobre a ida "
                          f"({passos_ida:.0f} passos) — insuficiente")
    print(f"OK  max_steps={e.max_steps}: folga {folga:.1f}x sobre a ida mais longa")


def test_tarefa_cumprivel():
    """Teste do oráculo: teleportados para junto do ninho, os agentes comem?
    Se nem assim comerem, nenhum treino do mundo produz recolhas."""
    e = make_env()
    e.reset(seed=1)
    e.agent_positions[:] = e.nest_pos + np.array([2.0, 0.0, 0.0])
    antes = e.total_food_collected
    for _ in range(60):
        e.step({a: np.array([-0.3, 0, 0], dtype=np.float32) for a in e.agents})
    assert e.total_food_collected > antes, "agentes JUNTO ao ninho não conseguem comer"
    print(f"OK  tarefa cumprível: {e.total_food_collected - antes} recolhas junto ao ninho")


def test_porta_abre_e_tem_alternativa():
    """A porta tem de (a) abrir com 3 agentes e (b) NÃO ser obrigatória — senão
    um enxame que não coopera fica bloqueado e o mapa mede só cooperação."""
    from collections import deque
    e = make_env()
    e.reset(seed=1)
    x0, x1, y0, y1 = e.door_push_bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    n_walls = len(e.walls)
    e.agent_positions[:3] = np.array([[cx, cy + 0.8, 0], [cx, cy, 0], [cx, cy - 0.8, 0]])
    e.agent_positions[3:, 0] = x0 - 15
    e.step(zero_actions(e))
    assert not e.door_active, "porta não abriu com 3 agentes na push zone"
    assert len(e.walls) == n_walls - 1, "painel da porta não foi removido"

    # (b) com a porta FECHADA ainda há caminho? (BFS igual ao do ambiente)
    e.reset(seed=1)
    res, n, R = e.geo_res, e.geo_n, e.arena_radius
    bloq = np.zeros((n, n), dtype=bool)
    for w in e.walls:                       # inclui o painel: porta fechada
        half = w["size"] / 2.0
        i0 = max(0, int((w["pos"][0] - half[0] - e.robot_radius + R) / res))
        i1 = min(n - 1, int((w["pos"][0] + half[0] + e.robot_radius + R) / res))
        j0 = max(0, int((w["pos"][1] - half[1] - e.robot_radius + R) / res))
        j1 = min(n - 1, int((w["pos"][1] + half[1] + e.robot_radius + R) / res))
        bloq[i0:i1 + 1, j0:j1 + 1] = True
    dist = np.full((n, n), np.inf)
    si, sj = int((e.nest_pos[0] + R) / res), int((e.nest_pos[1] + R) / res)
    dist[si, sj] = 0.0
    fila = deque([(si, sj)])
    viz = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
           (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
    while fila:
        i, j = fila.popleft()
        for di, dj, c in viz:
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < n and not bloq[a, b] \
                    and dist[i, j] + c * res < dist[a, b] - 1e-9:
                dist[a, b] = dist[i, j] + c * res
                fila.append((a, b))
    sp = e.agent_positions[0]
    d_fechada = dist[int((sp[0] + R) / res), int((sp[1] + R) / res)]
    assert np.isfinite(d_fechada), "porta FECHADA bloqueia o mapa — deveria haver alternativa"
    print(f"OK  porta abre com 3 e NÃO é obrigatória (alternativa a {d_fechada:.0f} m)")


def test_obstaculos_nao_selam_passagens():
    """Um obstáculo encostado a uma parede pode fechar um corredor de 2,5 m —
    e o mapa fica impossível sem dar erro nenhum."""
    piores_parede, piores_par = [], []
    for seed in range(1, 6):
        e = make_env()
        e.reset(seed=seed)
        O = np.array([o[:2] for o in e.obstacles])
        mg = min((max(abs(o[0] - w["pos"][0]) - w["size"][0] / 2,
                      abs(o[1] - w["pos"][1]) - w["size"][1] / 2) - e.obstacle_radius)
                 for o in O for w in e.walls
                 if max(abs(o[0] - w["pos"][0]) - w["size"][0] / 2,
                        abs(o[1] - w["pos"][1]) - w["size"][1] / 2) - e.obstacle_radius > 0)
        D = np.linalg.norm(O[:, None, :] - O[None, :, :], axis=2) + np.eye(len(O)) * 99
        piores_parede.append(mg)
        piores_par.append(D.min() - 2 * e.obstacle_radius)
    assert min(piores_parede) > ROBOT_D, "obstáculo demasiado perto de parede"
    assert min(piores_par) > ROBOT_D, "dois obstáculos fecham a passagem entre si"
    print(f"OK  obstáculos não selam passagens (folga mín. {min(piores_par):.2f} m "
          f"para um robô de {ROBOT_D:.2f} m)")


def test_escalabilidade_N():
    """A bateria Zero-Shot avalia N ∈ {10,20,50,100} — o mapa tem de aguentar."""
    for N in (10, 20, 50, 100):
        e = make_env(num_agents=N)
        e.reset(seed=1)
        assert e.observation_space_val.shape[0] == 16 + (N - 1) * 5
        dentro = sum(1 for q in e.agent_positions for w in e.walls
                     if np.all(np.abs(q - w["pos"]) < w["size"] / 2))
        assert dentro == 0, f"N={N}: agentes dentro de paredes"
        assert all(np.isfinite(_geo(e, q)) for q in e.agent_positions), \
            f"N={N}: agente sem caminho"
        e.step({a: np.zeros(3, dtype=np.float32) for a in e.agents})
    print("OK  escala para N=10/20/50/100 (spawn válido, caminho e step)")


def test_obs_dim_igual_aos_7():
    """Com N=20 a observação tem de ter 111 dims, como nos 7 cenários — é o que
    permite carregar os modelos existentes e comparar campanhas."""
    e = make_env()
    e.reset(seed=1)
    assert e.observation_space_val.shape[0] == 111, \
        f"obs_dim={e.observation_space_val.shape[0]} != 111 — modelos existentes não carregam"
    print("OK  obs_dim=111 — compatível com os modelos GNN/PPO/SAC já treinados")


def test_sem_fuga_entre_cenarios():
    """O run_experiments percorre cenários no mesmo processo. Se o mapa_grande
    deixar a arena a 60 ou o max_steps a 2000, CORROMPE os 7 cenários da tese."""
    cfg = copy.deepcopy(BASE_CFG)
    cfg["environment"]["classic_scenario"] = "four_rooms"
    e = SwarmForagingEnv3D(config=cfg)
    e.reset(seed=1)
    base = (e.arena_radius, e.max_steps, e.required_to_eat, len(e.walls))

    e.config["environment"]["classic_scenario"] = MAPA
    e.reset(seed=1)
    assert e.arena_radius == 60.0 and e.max_steps == 2000

    e.config["environment"]["classic_scenario"] = "four_rooms"
    e.reset(seed=1)
    assert (e.arena_radius, e.max_steps, e.required_to_eat, len(e.walls)) == base, \
        "o mapa_grande contaminou o four_rooms ao voltar atrás"
    print("OK  sem fuga de estado entre cenários (arena/steps/req_eat repostos)")


def test_robustez_ligavel():
    """Rrobust: com agent_failure_fraction>0 os agentes têm de falhar a meio."""
    e = make_env(agent_failure_fraction=0.10)
    e.reset(seed=1)
    assert e.failed.sum() == 0
    for _ in range(e.max_steps // 2 + 5):
        e.step(zero_actions(e))
    assert e.failed.sum() > 0, "injeção de falhas não funciona no mapa_grande"
    print(f"OK  Rrobust: {e.failed.sum()}/{e.num_agents} agentes falham a meio")


def test_ninho_desimpedido():
    """Nenhum obstáculo dentro da zona de recolha. Um obstáculo sorteado em cima
    do ninho estorva a entrega em alguns episódios e não noutros: ruído entre
    runs que a avaliação emparelhada NÃO cancela (o layout muda com a seed)."""
    e = make_env()
    piores = []
    for seed in range(30):
        e.reset(seed=seed)
        d = min(np.linalg.norm(np.asarray(o) - e.nest_pos) for o in e.obstacles)
        piores.append(d)
    minimo = e.nest_radius + e.obstacle_radius
    assert min(piores) > minimo, (
        f"obstáculo a {min(piores):.2f} m do ninho (zona de recolha = "
        f"{e.nest_radius:.1f} m) — entrega estorvada por sorteio")
    print(f"OK  ninho desimpedido em 30 episódios (obstáculo mais próximo: "
          f"{min(piores):.2f} m, zona de recolha {e.nest_radius:.1f} m)")


def test_spawn_livre_de_obstaculos():
    """Os agentes não podem nascer dentro de um obstáculo. A clareira é um
    círculo e a caixa de spawn um retângulo: se a clareira não cobrir a
    DIAGONAL, os cantos ficam de fora e o episódio começa com penalização e
    empurrão — silenciosamente, e só para alguns agentes."""
    e = make_env()
    contacto = e.robot_radius + e.obstacle_radius
    maus = 0
    for seed in range(30):
        e.reset(seed=seed)
        O = np.asarray(e.obstacles)
        d = np.linalg.norm(e.agent_positions[:, None, :] - O[None, :, :], axis=2)
        maus += int((d < contacto).any(axis=1).sum())
    assert maus == 0, f"{maus} agentes nasceram dentro de um obstáculo (30 episódios)"
    print("OK  spawn livre: 0 em 600 agentes nasce dentro de um obstáculo")


def test_normalizador_da_obs():
    """O normalizador das distâncias é o raio da arena — logo o mapa_grande
    comprime tudo 4x face ao treino. É um CONFUNDENTE do zero-shot, e por isso
    tem de existir a condição de controlo (obs_norm_radius). Este teste fixa as
    duas metades: por omissão nada muda; com override, muda só a escala."""
    e = make_env()
    e.reset(seed=1)
    assert e.obs_norm_radius == e.arena_radius == 60.0, "omissão deixou de ser o raio da arena"
    o_mapa = e._get_observations()["robot_0"]

    c = make_env(obs_norm_radius=15.0)
    c.reset(seed=1)
    assert c.arena_radius == 60.0, "o controlo NÃO pode mexer na física da arena"
    assert c.obs_norm_radius == 15.0
    o_ctrl = c._get_observations()["robot_0"]

    # Só as distâncias reescalam (4x); as direções egocêntricas ficam iguais.
    assert np.allclose(o_mapa[:3], o_ctrl[:3]), "as direções não podiam mudar"
    assert np.isclose(o_ctrl[3], o_mapa[3] * 4.0), "a distância ao ninho não reescalou 4x"

    # E os 7 cenários da tese continuam bit-exactos sem override.
    cfg = copy.deepcopy(BASE_CFG)
    cfg["environment"]["classic_scenario"] = "four_rooms"
    f = SwarmForagingEnv3D(config=cfg)
    f.reset(seed=1)
    assert f.obs_norm_radius == 15.0, "o four_rooms mudou de normalizador"
    print("OK  normalizador: 120 no mapa vs 30 no treino (4x) e controlo isolado")


if __name__ == "__main__":
    testes = [test_determinismo, test_resets_consecutivos, test_ninho_alcancavel,
              test_max_steps_suficiente, test_tarefa_cumprivel,
              test_porta_abre_e_tem_alternativa, test_obstaculos_nao_selam_passagens,
              test_escalabilidade_N, test_obs_dim_igual_aos_7,
              test_sem_fuga_entre_cenarios, test_robustez_ligavel,
              test_ninho_desimpedido, test_spawn_livre_de_obstaculos,
              test_normalizador_da_obs]
    for t in testes:
        t()
    print(f"\n{len(testes)}/{len(testes)} testes do mapa grande passaram ✅")
