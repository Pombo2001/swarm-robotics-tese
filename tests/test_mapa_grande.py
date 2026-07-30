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


def _grelha_livre(e, res=0.3, com_obstaculos=True, porta_fechada=False):
    """bloq[i,j] do espaço navegável: paredes + obstáculos + bordo da arena.

    O `_build_geodesic_field` do ambiente só bloqueia PAREDES — é o que ele
    precisa para o gradiente. Para saber se o mapa é atravessável faltam os
    obstáculos, que aqui são 106 e sorteados por episódio."""
    R = e.arena_radius
    n = int(2 * R / res) + 1
    xs = -R + (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    bloq = (X ** 2 + Y ** 2) > (R - e.robot_radius) ** 2
    for k, w in enumerate(e.walls):
        if (not porta_fechada) and e.door_wall_index is not None and k == e.door_wall_index:
            continue
        h = w["size"] / 2.0
        bloq |= ((np.abs(X - w["pos"][0]) < h[0] + e.robot_radius) &
                 (np.abs(Y - w["pos"][1]) < h[1] + e.robot_radius))
    if com_obstaculos:
        rr = (e.obstacle_radius + e.robot_radius) ** 2
        for o in e.obstacles:
            bloq |= ((X - o[0]) ** 2 + (Y - o[1]) ** 2) < rr
    return bloq, n, res


def _alcancavel(e, bloq, n, res):
    """Células alcançáveis a partir do ninho (BFS 8-conexo)."""
    from collections import deque
    vis = np.zeros((n, n), bool)
    c0 = (int((e.nest_pos[0] + e.arena_radius) / res),
          int((e.nest_pos[1] + e.arena_radius) / res))
    vis[c0] = True
    fila = deque([c0])
    while fila:
        i, j = fila.popleft()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                a, b = i + di, j + dj
                if 0 <= a < n and 0 <= b < n and not bloq[a, b] and not vis[a, b]:
                    vis[a, b] = True
                    fila.append((a, b))
    return vis


def test_atravessavel_com_obstaculos():
    """Os 106 obstáculos não podem fechar o mapa — e o teste do campo geodésico
    NÃO apanha isso, porque o campo do ambiente só conhece paredes.

    Um obstáculo que sele um corredor de 2,5 m torna o mapa impossível a partir
    de uma seed e possível na seguinte: uma campanha inteira com metade dos
    episódios insolúveis, sem um único erro no log."""
    e = make_env()
    for seed in (1, 2):
        e.reset(seed=seed)
        for fechada in (False, True):
            bloq, n, res = _grelha_livre(e, porta_fechada=fechada)
            vis = _alcancavel(e, bloq, n, res)
            maus = [q for q in e.agent_positions
                    if not vis[int((q[0] + e.arena_radius) / res),
                              int((q[1] + e.arena_radius) / res)]]
            estado = "FECHADA" if fechada else "aberta"
            assert not maus, (f"seed {seed}, porta {estado}: {len(maus)} agentes "
                              f"sem caminho ao ninho depois dos obstáculos")
    print("OK  mapa atravessável com os 106 obstáculos, de porta aberta E fechada")


def test_controlo_sem_obstaculos():
    """CONTROLO do F1: dos 8 cenários só o Sandbox e o mapa_grande têm
    obstáculos — os 5 labirintos têm ZERO. Um campeão do Gargalo nunca viu um
    obstáculo, logo '0 recolhas no mapa' pode ser a topologia OU só os
    obstáculos. Este teste fixa as duas metades: por omissão nada muda; a 0, o
    mundo perde os obstáculos e mais nada."""
    e = make_env()
    e.reset(seed=1)
    assert len(e.obstacles) == 106, f"o mapa base deixou de ter 106 obstáculos ({len(e.obstacles)})"

    c = make_env(num_obstacles_mapa_grande=0)
    c.reset(seed=1)
    assert len(c.obstacles) == 0, "o controlo não removeu os obstáculos"
    # Só os obstáculos: paredes, ninho e spawn têm de ficar iguais.
    assert np.allclose([w["pos"] for w in c.walls], [w["pos"] for w in e.walls]), \
        "o controlo mexeu nas paredes"
    assert np.allclose(c.nest_pos, e.nest_pos), "o controlo mexeu no ninho"
    c.step({a: np.zeros(3, dtype=np.float32) for a in c.agents})

    # E os 5 labirintos que o controlo imita continuam mesmo sem obstáculos.
    for scen in ("u_wall", "bottleneck", "four_rooms", "cooperative_door"):
        cfg = copy.deepcopy(BASE_CFG)
        cfg["environment"]["classic_scenario"] = scen
        f = SwarmForagingEnv3D(config=cfg)
        f.reset(seed=1)
        assert len(f.obstacles) == 0, \
            f"{scen} passou a ter obstáculos — o controlo deixa de fazer sentido"
    print("OK  controlo sem_obstaculos: 106 -> 0, resto do mundo intacto")


def test_controlo_porta_na_obs():
    """CONTROLO do F1: as 4 features da porta (obs[12:16]) são identicamente 0
    no treino de quem não tem porta e ficam VIVAS no mapa_grande. São 4 entradas
    mortas que passam a carregar sinal — causa possível de um zero que nada tem
    a ver com a topologia. O controlo repõe os zeros SEM tirar a porta do mundo."""
    e = make_env()
    e.reset(seed=1)
    o_base = e._get_observations()["robot_0"]
    assert np.any(o_base[12:16] != 0), "o mapa_grande devia ter a bússola da porta viva"

    c = make_env(obs_zero_door_feats=True)
    c.reset(seed=1)
    o_ctrl = c._get_observations()["robot_0"]
    assert np.all(o_ctrl[12:16] == 0), "o controlo não zerou as features da porta"
    assert c.has_door and c.door_active, "o controlo tirou a porta do MUNDO (só devia zerar a obs)"
    assert len(c.walls) == len(e.walls), "o controlo mexeu nas paredes"
    # Tudo o resto bit-a-bit igual: se mudar mais alguma coisa, o controlo mede
    # duas coisas ao mesmo tempo e deixa de ser controlo.
    assert np.array_equal(np.delete(o_base, np.s_[12:16]),
                          np.delete(o_ctrl, np.s_[12:16])), \
        "o controlo mexeu em features que não são as da porta"

    # Nos cenários sem porta já era zero: o controlo não pode mudar nada lá.
    for scen in ("u_wall", "four_rooms"):
        for zerar in (False, True):
            cfg = copy.deepcopy(BASE_CFG)
            cfg["environment"]["classic_scenario"] = scen
            cfg["environment"]["obs_zero_door_feats"] = zerar
            f = SwarmForagingEnv3D(config=cfg)
            f.reset(seed=1)
            assert np.all(f._get_observations()["robot_0"][12:16] == 0)
    print("OK  controlo sem_porta_obs: obs[12:16] a zero, porta física intacta")


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


def test_aperto_nao_atravessa_paredes():
    """Enxame amontoado contra uma parede não passa para o outro lado.

    Antes da 2.ª passagem do push-out (27 jul), 20 agentes empurrados contra a
    divisória B→C durante 120 passos punham 12 do outro lado, e contra o painel
    da PORTA punham 4 — isto é, o enxame chegava ao ninho sem cooperar, o que
    esvaziava a métrica M3 do pré-registo. O mecanismo: a separação inter-agente
    corre DEPOIS do push-out e enterra agentes no painel; no passo seguinte o
    push-out escolhia o eixo de menor penetração e expulsava-os pelo lado errado.
    """
    for n in (10, 20, 30):
        env = make_env(num_agents=n)
        env.reset(seed=1)
        # Paredes longas (>3 m) — as curtas contornam-se legitimamente pela ponta.
        alvos = [k for k, w in enumerate(env.walls)
                 if max(w['size'][0], w['size'][1]) > 3.0]
        alvos.append(env.door_wall_index)          # o painel da porta, sempre
        for wi in alvos:
            env.reset(seed=1)
            wp = env.walls[wi]['pos'].copy()
            ws = env.walls[wi]['size'].copy()
            eixo = 0 if ws[0] < ws[1] else 1
            base = wp.copy()
            base[eixo] += ws[eixo] / 2 + env.robot_radius + 0.02
            base[2] = 0.0
            np.random.seed(0)
            for i in range(n):
                env.agent_positions[i] = base + np.random.uniform(-0.5, 0.5, 3) * np.array([1, 1, 0])
                h = np.zeros(3)
                h[eixo] = -1.0
                env.agent_headings[i] = h
            for _ in range(120):
                env.step({a: np.array([1.0, 0.0, 0.0], dtype=np.float32) for a in env.agents})
                for i in range(n):          # manter a pressão contra a parede
                    h = np.zeros(3)
                    h[eixo] = -1.0
                    env.agent_headings[i] = h
            do_outro_lado = int((np.sign(env.agent_positions[:, eixo] - wp[eixo]) < 0).sum())
            assert do_outro_lado == 0, (
                f"{do_outro_lado}/{n} agentes atravessaram a parede #{wi} "
                f"(centro {wp[:2]}, tamanho {ws[:2]})")
    print("OK  aperto: nenhum agente atravessa parede, até 30 agentes empilhados")


def test_fisica_dos_7_inalterada():
    """A correção do push-out é EXCLUSIVA do mapa_grande.

    Referência capturada com o código anterior à correção (27 jul): soma, média,
    mínimo e máximo de posições+recompensas ao longo de 200 passos com ações
    fixas. Se alguma mudar, uma alteração à física entrou nos cenários cujos
    números já estão na tese, e as campanhas fechadas deixam de ser reproduzíveis.

    **Porque é uma tolerância e não um hash:** a primeira versão deste teste
    comparava um SHA-256 dos floats. Passava aqui e FALHAVA no servidor — não por
    regressão, mas porque a ordem das somas em vírgula flutuante difere entre
    plataformas (Python 3.13/numpy 2.4.2 vs 3.12/2.4.6): as duas máquinas dão
    266,003105779438 e 266,003105779439. Um teste que acusa regressão por mudar
    de máquina é pior do que não ter teste — ou faz perder tempo, ou ensina a
    ignorá-lo. A tolerância de 1e-9 relativa engole esse ruído (que vive em
    1e-12) e continua a apanhar qualquer alteração real da física, que move
    estes valores em ordens de grandeza.
    """
    REFERENCIA = {
        "none":                    (266.003105779, 0.831259706, -11.758723981, 12.292120540),
        "u_wall":                  (-729.128611656, -2.278526911, -14.354598594, 9.752095924),
        "bottleneck":              (-640.630318067, -2.001969744, -14.396867115, 9.752095924),
        "four_rooms":              (-486.287732330, -1.519649164, -10.345279756, 10.380971855),
        "cooperative_door":        (-551.198892680, -1.722496540, -14.396867115, 9.752095924),
        "cooperative_perception":  (-340.497943678, -1.064056074, -13.130892904, 8.860656961),
        "cooperative_door_bypass": (-551.198892680, -1.722496540, -14.396867115, 9.752095924),
    }
    for cen, esperado in REFERENCIA.items():
        cfg = copy.deepcopy(BASE_CFG)
        cfg["environment"]["classic_scenario"] = cen
        e = SwarmForagingEnv3D(config=cfg)
        e.reset(seed=7)
        np.random.seed(123)
        acc = []
        for t in range(200):
            ac = {a: np.random.uniform(-1, 1, 3).astype(np.float32) for a in e.agents}
            _, rew, _, _, _ = e.step(ac)
            if t % 50 == 0:
                acc.append(e.agent_positions.copy().ravel())
                acc.append(np.array([rew[a] for a in e.agents]))
        v = np.concatenate(acc)
        obtido = (v.sum(), v.mean(), v.min(), v.max())
        assert np.allclose(obtido, esperado, rtol=1e-9, atol=1e-9), (
            f"{cen}: física alterada\n  esperado {esperado}\n  obtido   {obtido}")
    print("OK  os 7 cenários da tese continuam com a física inalterada")


def _empurra_contra(env, plano, eixo, transv, valor_transv, z, passos=250):
    """Põe o agente 1,5 m antes de um plano e empurra-o contra ele. True = passou."""
    p = np.zeros(3, dtype=np.float32)
    p[eixo] = plano - 1.5
    p[transv] = valor_transv
    p[2] = z
    env.agent_positions[0] = p
    direcao = np.zeros(3, dtype=np.float32)
    direcao[eixo] = 1.0
    nome = env.agents[0]
    for _ in range(passos):
        env.agent_headings[0] = direcao.copy()
        ac = zero_actions(env)
        ac[nome] = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        env.step(ac)
        if env.agent_positions[0][eixo] > plano + 1.5:
            return True
    return False


def test_paredes_tao_altas_como_a_arena():
    """Não pode haver céu aberto por cima das paredes, em cenário nenhum.

    O mundo é 3D (`move_local[2]` dá componente vertical) e a arena é uma ESFERA
    de raio `arena_radius`. Uma parede só veda se for tão alta quanto o espaço
    onde os agentes podem estar.

    Estava `30.0` em duro em todas as paredes — certo por coincidência, porque
    2×15 é o diâmetro da arena dos 7 cenários. O `mapa_grande` corre a r=60 e
    ficava com **45 m de espaço livre por cima de todas as paredes**: medido a
    29 jul, um agente atravessava a divisória mais longa a z≥16 m, e chegava lá
    em 75 passos dos 2000 do episódio. Os campeões do F1 andaram a 59 m de
    altura durante o episódio inteiro — o F1 de 28 jul foi anulado por isto.
    """
    for cen in ["u_wall", "bottleneck", "four_rooms", "cooperative_door",
                "cooperative_door_bypass", MAPA]:
        cfg = copy.deepcopy(BASE_CFG)
        cfg["environment"]["classic_scenario"] = cen
        e = SwarmForagingEnv3D(config=cfg)
        e.reset(seed=1)
        for w in e.walls:
            assert w["size"][2] / 2 >= e.arena_radius - 1e-9, (
                f"{cen}: parede em {w['pos'][:2]} vai a z={w['size'][2]/2:.1f} mas a "
                f"arena vai a {e.arena_radius:.1f} — passa-se por cima")

    # E a prova empírica no mapa grande, que é onde o buraco existiu: a divisória
    # mais longa bloqueia a TODAS as alturas alcançáveis, não só a z≈0.
    env = make_env()
    env.reset(seed=1)
    divisorias = [w for w in env.walls if w["size"][1] > w["size"][0]]
    parede = max(divisorias, key=lambda w: w["size"][1])
    for z in (0.0, 10.0, 16.0, 30.0, 45.0, 55.0):
        env.reset(seed=1)
        assert not _empurra_contra(env, float(parede["pos"][0]), 0, 1,
                                   float(parede["pos"][1]), z), (
            f"mapa_grande: atravessou a divisória a z={z} m")
    print("OK  nenhuma parede deixa céu aberto (6 cenários + travessia a 6 alturas)")


def test_porta_fechada_veda_a_toda_a_altura():
    """A porta fechada é uma parede a sério: em toda a altura e sem frestas.

    O painel herdava a altura de `DOOR_SIZE` (30 m) e, no mapa_grande, ficava
    mais baixo que a parede que fecha — passava-se por cima da porta fechada
    sem a abrir, o que esvaziaria a M3 (uso da porta cooperativa) do pré-registo.
    Testa-se também as JUNTAS com as paredes vizinhas: uma fresta de 20 cm ali
    dava o mesmo resultado sem se notar na planta.
    """
    for cen, eixo in [(MAPA, 0), ("cooperative_door", 1),
                      ("cooperative_door_bypass", 1)]:
        cfg = copy.deepcopy(BASE_CFG)
        cfg["environment"]["classic_scenario"] = cen
        e = SwarmForagingEnv3D(config=cfg)
        e.reset(seed=1)
        transv = 1 - eixo
        assert e.door_active, f"{cen}: a porta devia começar fechada"
        assert e.door_size[2] >= 2 * e.arena_radius - 1e-9, (
            f"{cen}: painel da porta com {e.door_size[2]/2:.1f} m de meia-altura "
            f"numa arena de raio {e.arena_radius:.1f}")

        plano = float(e.door_pos[eixo])
        y_porta = float(e.door_pos[transv])
        alturas = [z for z in (0.0, 5.0, 16.0, 30.0, 55.0) if z < e.arena_radius - 2]
        for z in alturas:
            e.reset(seed=1)
            assert not _empurra_contra(e, plano, eixo, transv, y_porta, z), (
                f"{cen}: passou pela porta FECHADA a z={z} m")
        # Juntas: o painel tem de encostar às paredes que fecha.
        meio = float(e.door_size[transv]) / 2
        for d in (meio - 0.1, meio + 0.1, meio + 0.4):
            e.reset(seed=1)
            assert not _empurra_contra(e, plano, eixo, transv, y_porta + d, 0.0), (
                f"{cen}: fresta na junta do painel, a {d:.2f} m do centro")
    print("OK  a porta fechada veda em toda a altura e sem frestas (3 cenários)")


def test_teto_e_shaping_telescopico():
    """No mapa_grande os agentes não saem do plano, e o shaping fecha a soma.

    Duas propriedades ligadas, e a segunda é a razão de ser da primeira.

    O teto: o mapa é um labirinto planar numa arena esférica de r=60, que abria
    45 m de altura sem labirinto nenhum. Não era espaço morto — era uma fuga à
    economia da tarefa: encostado ao limite da esfera, o agente cai no ramo do
    empurrão da arena, que faz `continue`, e nesse passo NÃO paga energia e a
    variação de potencial é engolida. Medido a 30 jul no modelo do shakedown
    (25 gerações): agentes a |z| 40-57 m, 10,7% dos passos-agente sem recompensa
    nenhuma, 47 887 de aproximação nunca creditada.

    O shaping: sendo potential-based (Ng et al., 1999), a soma ao longo do
    episódio TEM de ser (Φ_0 − Φ_T)·factor e nada mais — é isso que garante que
    não altera a política ótima. Qualquer passo que atualize `prev_pot` sem pagar
    quebra essa igualdade, e é assim que aparecem bombas de recompensa.
    """
    env = make_env()
    env.reset(seed=3)
    teto = env.MAPA_GRANDE_TETO

    # Ações que empurram todos os agentes para cima o episódio inteiro.
    rng = np.random.default_rng(0)
    phi0 = np.array(env.prev_pot, dtype=float).copy()
    soma_shaping = 0.0
    sem_pagamento = 0
    for _ in range(400):
        antes = np.array(env.prev_pot, dtype=float).copy()
        ac = {}
        for a in env.agents:
            env.agent_headings[list(env.agents).index(a)] = np.array(
                [1.0, 0.0, 0.0], dtype=np.float32)
            ac[a] = np.array([0.0, 0.0, 1.0], dtype=np.float32)   # U = +z
        _, rew, terms, truncs, _ = env.step(ac)
        assert np.all(np.abs(env.agent_positions[:, 2]) <= teto + 1e-9), (
            f"agente acima do teto: |z| max = "
            f"{np.abs(env.agent_positions[:, 2]).max():.2f} > {teto}")
        depois = np.array(env.prev_pot, dtype=float)
        soma_shaping += float(((antes - depois) * env.progress_reward_factor).sum())
        sem_pagamento += sum(1 for a in env.agents if rew[a] == 0.0)
        if any(terms.values()) or any(truncs.values()):
            break

    assert sem_pagamento == 0, (
        f"{sem_pagamento} passos-agente sem recompensa nenhuma — cada um deles "
        f"atualiza prev_pot sem pagar e quebra o telescópio do shaping")

    phiT = np.array(env.prev_pot, dtype=float)
    telescopico = float(((phi0 - phiT) * env.progress_reward_factor).sum())
    assert abs(soma_shaping - telescopico) < 1e-6, (
        f"shaping não telescópico: somado {soma_shaping:.2f} vs "
        f"(Φ_0−Φ_T)·factor {telescopico:.2f} — diferença "
        f"{soma_shaping - telescopico:.2f} injetada de algum lado")
    print(f"OK  teto de ±{teto} m respeitado e shaping telescópico "
          f"(0 passos sem pagamento)")


if __name__ == "__main__":
    testes = [test_determinismo, test_resets_consecutivos, test_ninho_alcancavel,
              test_max_steps_suficiente, test_tarefa_cumprivel,
              test_porta_abre_e_tem_alternativa, test_obstaculos_nao_selam_passagens,
              test_escalabilidade_N, test_obs_dim_igual_aos_7,
              test_sem_fuga_entre_cenarios, test_robustez_ligavel,
              test_ninho_desimpedido, test_spawn_livre_de_obstaculos,
              test_normalizador_da_obs, test_atravessavel_com_obstaculos,
              test_controlo_sem_obstaculos, test_controlo_porta_na_obs,
              test_aperto_nao_atravessa_paredes, test_fisica_dos_7_inalterada,
              test_paredes_tao_altas_como_a_arena,
              test_porta_fechada_veda_a_toda_a_altura,
              test_teto_e_shaping_telescopico]
    for t in testes:
        t()
    print(f"\n{len(testes)}/{len(testes)} testes do mapa grande passaram ✅")
