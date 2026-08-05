# -*- coding: utf-8 -*-
"""Auditoria do 8.º cenário (mapa grande) contra os sete cenários fechados.

Porque existe
-------------
O mapa grande é o único cenário que nunca produziu uma recolha: o F1 (zero-shot)
deu 84/84 células a 0,00, e o primeiro run nativo do F2 fechou 143 gerações e
24,4 milhões de passos com `best_task_food = 0`. Um zero pode ser o resultado
(«nem treinar de raiz resolve um mapa desta escala») ou pode ser uma avaria — e
as duas leituras são indistinguíveis sem verificar o mapa peça a peça.

Este script compara o mapa grande com os sete cenários cuja campanha fechou com
resultados válidos. Tudo o que ele afirma é medido em execução, não lido de
documentação: constrói o ambiente, mede geometria, alcançabilidade, orçamento
temporal e o campo de navegação, e assinala o que diverge dos sete.

Uso:  .venv/Scripts/python.exe scripts/auditar_mapa_grande.py
      .venv/Scripts/python.exe scripts/auditar_mapa_grande.py --verboso
"""
import argparse
import os
import sys
from collections import deque

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402
from src.scenarios import SCENARIOS  # noqa: E402

CFG = os.path.join(RAIZ, "configs", "foraging.yaml")
ALVO = "mapa_grande"

_problemas, _avisos, _ok = [], [], []


def erro(t):
    _problemas.append(t)


def aviso(t):
    _avisos.append(t)


def ok(t):
    _ok.append(t)


def _env(cenario, seed=0):
    import yaml
    with open(CFG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = cenario
    e = SwarmForagingEnv3D(config=cfg)
    e.reset(seed=seed)
    return e


# ── 1. Propriedades básicas, lado a lado ────────────────────────────────────
def tabela_comparativa(envs):
    print("=" * 78)
    print("1. O MAPA GRANDE AO LADO DOS SETE — propriedades do ambiente")
    print("=" * 78)
    print(f"{'cenário':<26} {'arena':>6} {'passos':>7} {'k_eat':>6} {'obst':>6} "
          f"{'paredes':>8} {'obs_dim':>8}")
    for cen, e in envs.items():
        marca = " ←" if cen == ALVO else ""
        print(f"{cen:<26} {e.arena_radius:6.0f} {e.max_steps:7d} "
              f"{e.required_to_eat:6d} {len(getattr(e, "obstacles", [])):6d} "
              f"{len(getattr(e, 'walls', [])):8d} "
              f"{e.observation_space_val.shape[0]:8d}{marca}")

    alvo = envs[ALVO]
    dims = {c: e.observation_space_val.shape[0] for c, e in envs.items()}
    if len(set(dims.values())) == 1:
        ok(f"a observação tem a mesma dimensão nos oito cenários ({alvo.observation_space_val.shape[0]})")
    else:
        erro(f"dimensões de observação diferentes entre cenários: {dims}")


# ── 2. Paredes: altura e estanqueidade ──────────────────────────────────────
def verificar_paredes(envs):
    print()
    print("=" * 78)
    print("2. PAREDES — altura e vedação (o defeito de 29 jul)")
    print("=" * 78)
    for cen, e in envs.items():
        paredes = getattr(e, "walls", [])
        if not len(paredes):
            continue
        alturas = [float(w["size"][2]) for w in paredes]      # tamanho em z
        teto = 2.0 * e.arena_radius
        menor = min(alturas)
        estado = "ok" if menor >= teto - 1e-6 else "BAIXA"
        print(f"  {cen:<26} altura mín {menor:7.1f}   teto exigido {teto:7.1f}   {estado}")
        if menor < teto - 1e-6:
            erro(f"{cen}: paredes de {menor:.1f} m numa arena de raio "
                 f"{e.arena_radius:.0f} — há {teto - menor:.1f} m de céu aberto "
                 f"(é o defeito que anulou o F1 a 29 jul)")
    ok("altura das paredes verificada nos cenários com paredes")


# ── 3. Alcançabilidade: do spawn ao ninho, e a comida ───────────────────────
def _grelha_livre(e, passo=0.5):
    """Grelha booleana de células navegáveis (True = livre), no plano z=0."""
    R = e.arena_radius
    n = int(2 * R / passo) + 1
    eixo = np.linspace(-R, R, n)
    xx, yy = np.meshgrid(eixo, eixo, indexing="ij")
    dentro = (xx ** 2 + yy ** 2) <= R ** 2
    livre = dentro.copy()
    folga = float(getattr(e, "robot_radius", 0.15))
    idx_porta = getattr(e, "door_wall_index", None)
    for i, parede in enumerate(getattr(e, "walls", [])):
        if idx_porta is not None and i == idx_porta:
            continue          # o painel da porta abre-se durante o episódio
        centro, tamanho = parede["pos"], parede["size"]
        cx, cy = float(centro[0]), float(centro[1])
        hx, hy = float(tamanho[0]) / 2 + folga, float(tamanho[1]) / 2 + folga
        dentro_parede = (np.abs(xx - cx) <= hx) & (np.abs(yy - cy) <= hy)
        livre &= ~dentro_parede
    return eixo, livre


def _bfs(livre, origem_ij):
    alcancado = np.zeros_like(livre, dtype=bool)
    if not livre[origem_ij]:
        return alcancado
    fila = deque([origem_ij])
    alcancado[origem_ij] = True
    n, m = livre.shape
    while fila:
        i, j = fila.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < m and livre[a, b] and not alcancado[a, b]:
                alcancado[a, b] = True
                fila.append((a, b))
    return alcancado


def _idx(eixo, v):
    return int(np.argmin(np.abs(eixo - v)))


def verificar_alcancabilidade(envs, verboso=False):
    """Devolve {cenário: (eixo, alcançado)} — a secção 5 reusa as máscaras."""
    print()
    print("=" * 78)
    print("3. ALCANÇABILIDADE — o ninho vê-se do spawn? e a comida?")
    print("=" * 78)
    mapas, pcts = {}, {}
    for cen, e in envs.items():
        eixo, livre = _grelha_livre(e)
        spawn = np.mean(e.agent_positions[:, :2], axis=0)
        ini = (_idx(eixo, spawn[0]), _idx(eixo, spawn[1]))
        alc = _bfs(livre, ini)
        ninho = e.nest_pos[:2]
        i_n, j_n = _idx(eixo, ninho[0]), _idx(eixo, ninho[1])
        # o ninho tem raio: procura-se qualquer célula alcançada dentro dele
        raio_n = float(getattr(e, "nest_radius", 1.5))
        xx, yy = np.meshgrid(eixo, eixo, indexing="ij")
        zona_ninho = ((xx - ninho[0]) ** 2 + (yy - ninho[1]) ** 2) <= (raio_n + 0.5) ** 2
        ninho_ok = bool((alc & zona_ninho).any())
        pct = 100.0 * alc.sum() / max(livre.sum(), 1)
        nota = "  (porta contada como passável)" if getattr(e, "has_door", False) else ""
        print(f"  {cen:<26} ninho alcançável: {'sim' if ninho_ok else 'NÃO':<4}"
              f"   área navegável ligada ao spawn: {pct:5.1f}%{nota}")
        if not ninho_ok:
            erro(f"{cen}: o ninho NÃO é alcançável a partir do spawn (BFS no plano)")
        mapas[cen] = (eixo, alc, livre)
        pcts[cen] = pct

    # A comparação é com os SETE, não com um limiar inventado: o script existe
    # para dizer em que é que o 8.º cenário difere dos que deram resultados. Um
    # `pct < 50` fixo deixava passar em silêncio um mapa a 53,7% ao lado de sete
    # a 100,0% — precisamente a diferença que se quer ver.
    #
    # Mas «53,7% ligado» não é, por si, um defeito: no mapa grande o labirinto
    # é uma caixa dentro de uma arena circular MAIOR, e a coroa entre os dois é
    # área livre que nenhum robô alcança nem precisa de alcançar. O que seria
    # defeito é uma bolsa DENTRO do labirinto — sala fechada, comida ou ninho
    # atrás de parede sem abertura. Medem-se as duas coisas em separado; dizer
    # só a percentagem global levaria a tese a afirmar que metade do mapa está
    # inacessível, quando o labirinto está 100% ligado (medido, 5 ago).
    sete = [p for c, p in pcts.items() if c != ALVO]
    if ALVO in pcts and sete and pcts[ALVO] < min(sete) - 1.0:
        eixo, alc, livre = mapas[ALVO]
        e = envs[ALVO]
        xx, yy = np.meshgrid(eixo, eixo, indexing="ij")
        px = np.array([w["pos"][0] for w in e.walls])
        py = np.array([w["pos"][1] for w in e.walls])
        sx = np.array([w["size"][0] for w in e.walls])
        sy = np.array([w["size"][1] for w in e.walls])
        caixa = ((xx >= (px - sx / 2).min()) & (xx <= (px + sx / 2).max())
                 & (yy >= (py - sy / 2).min()) & (yy <= (py + sy / 2).max()))
        desligado = livre & ~alc
        dentro = int((desligado & caixa).sum())
        pct_lab = 100.0 * (alc & caixa).sum() / max((livre & caixa).sum(), 1)
        print(f"    └ {ALVO}: dentro do labirinto {pct_lab:.1f}% ligado ao spawn; "
              f"o desligado são {int(desligado.sum()) - dentro} células da coroa "
              f"entre o labirinto e a arena (r={e.arena_radius:.0f} m) e {dentro} "
              f"dentro do labirinto")
        if dentro:
            erro(f"{ALVO}: {dentro} células livres DENTRO do labirinto sem ligação "
                 f"ao spawn — há sala fechada (só {pct_lab:.1f}% do labirinto ligado)")
    return mapas


# ── 4. Orçamento temporal: dá para ir e voltar? ─────────────────────────────
def verificar_orcamento(envs):
    print()
    print("=" * 78)
    print("4. ORÇAMENTO TEMPORAL — os passos chegam para recolher e entregar?")
    print("=" * 78)
    print(f"{'cenário':<26} {'passos':>7} {'passo(m)':>9} {'alcance':>9} "
          f"{'ida+volta':>10} {'folga':>7}")
    for cen, e in envs.items():
        passo_m = 0.2   # escalamento da acao no step() (ver _apply_actions)
        alcance = e.max_steps * passo_m
        spawn = np.mean(e.agent_positions[:, :2], axis=0)
        d_ninho = float(np.linalg.norm(spawn - e.nest_pos[:2]))
        # a comida mais próxima do spawn (o melhor caso possível)
        # Neste simulador nao ha comida espalhada: "recolher" e CHEGAR ao ninho
        # (o agente e depois devolvido ao spawn). O percurso minimo de uma
        # recolha e, portanto, a distancia GEODESICA do spawn ao ninho — a
        # euclidiana subestima-a em mapas com paredes.
        pot_spawn = float(e._potential(np.array([spawn[0], spawn[1], 0.0])))
        percurso = pot_spawn if np.isfinite(pot_spawn) else d_ninho
        folga = alcance / max(percurso, 1e-9)
        marca = ""
        if folga < 2.0:
            marca = "  ← APERTADO"
            (erro if folga < 1.2 else aviso)(
                f"{cen}: o orçamento dá {folga:.1f}× o percurso mínimo "
                f"(comida mais próxima + regresso ao ninho); abaixo de 2× não há "
                f"margem para procurar")
        print(f"  {cen:<24} {e.max_steps:7d} {passo_m:9.2f} {alcance:9.0f} "
              f"{percurso:10.0f} {folga:6.1f}×{marca}")


# ── 5. Campo geodésico ──────────────────────────────────────────────────────
def _cobertura_util(e, eixo, alc):
    """% das células ONDE OS ROBÔS PODEM ANDAR (livres e ligadas ao spawn) que
    têm potencial finito.

    A percentagem de células finitas do campo inteiro engana: a grelha do
    Dijkstra é o quadrado que envolve a arena, e boa parte dela é parede ou
    está fora do círculo. O que decide se há sinal de progresso é a cobertura
    da zona navegável — onde um robô se encontra de facto quando procura o
    ninho. Fora dela, `_potential` cai no ramo euclidiano + penalização.
    """
    ii, jj = np.nonzero(alc)
    if ii.size == 0:
        return float("nan")
    xs, ys = eixo[ii], eixo[jj]
    ci = ((xs + e.arena_radius) / e.geo_res).astype(int)
    cj = ((ys + e.arena_radius) / e.geo_res).astype(int)
    dentro = (ci >= 0) & (ci < e.geo_n) & (cj >= 0) & (cj < e.geo_n)
    finito = np.zeros(ii.size, dtype=bool)
    finito[dentro] = np.isfinite(e.geo_field[ci[dentro], cj[dentro]])
    return 100.0 * finito.sum() / finito.size


def verificar_geodesico(envs, mapas=None):
    print()
    print("=" * 78)
    print("5. CAMPO GEODÉSICO — existe, cobre o mapa e aponta para o ninho?")
    print("=" * 78)
    uteis = {}
    for cen, e in envs.items():
        if not getattr(e, "use_geodesic", False):
            print(f"  {cen:<26} (euclidiano — sem campo geodésico)")
            continue
        campo = getattr(e, "geo_field", None)
        if campo is None:
            erro(f"{cen}: use_geodesic ativo mas o campo não foi construído")
            continue
        finito = np.isfinite(campo)
        pct = 100.0 * finito.sum() / campo.size
        spawn = np.mean(e.agent_positions[:2], axis=0) if e.agent_positions.ndim == 1 \
            else np.mean(e.agent_positions[:, :2], axis=0)
        pot_spawn = e._potential(np.array([spawn[0], spawn[1], 0.0]))
        pot_ninho = e._potential(e.nest_pos)
        util = ""
        if mapas and cen in mapas:
            eixo_c, alc_c, _ = mapas[cen]
            u = _cobertura_util(e, eixo_c, alc_c)
            uteis[cen] = u
            util = f"   zona navegável com Φ: {u:5.1f}%"
        print(f"  {cen:<26} células com valor: {pct:5.1f}%   "
              f"Φ(spawn)={pot_spawn:8.1f}   Φ(ninho)={pot_ninho:6.1f}{util}")
        if not np.isfinite(pot_spawn):
            erro(f"{cen}: o potencial no spawn é infinito — o campo não liga o "
                 f"spawn ao ninho, e o sinal de progresso não existe ali")
        elif pot_spawn <= pot_ninho:
            erro(f"{cen}: Φ(spawn) ≤ Φ(ninho) — o gradiente não aponta para o ninho")
        else:
            ok(f"{cen}: campo geodésico coerente (Φ decresce do spawn para o ninho)")

    sete = [u for c, u in uteis.items() if c != ALVO]
    if ALVO in uteis and sete and uteis[ALVO] < min(sete) - 1.0:
        aviso(f"{ALVO}: o potencial só existe em {uteis[ALVO]:.1f}% da zona "
              f"navegável (pior dos sete: {min(sete):.1f}%) — no resto o robô "
              f"navega sem sinal de progresso")


# ── 6. Um episódio a sério, com política aleatória ──────────────────────────
def episodio_de_fumo(envs, passos=300):
    print()
    print("=" * 78)
    print("6. EPISÓDIO DE FUMO — o ambiente corre sem rebentar e o Φ desce?")
    print("=" * 78)
    rng = np.random.default_rng(0)
    for cen, e in envs.items():
        e.reset(seed=1)
        pot0 = float(np.mean([e._potential(p) for p in e.agent_positions]))
        rec = 0
        for _ in range(min(passos, e.max_steps)):
            acoes = {a: rng.uniform(-1, 1, size=3).astype(np.float32) for a in e.agents}
            _, r, term, trunc, _ = e.step(acoes)
            rec += float(e.total_food_collected)
            if any(term.values()) or any(trunc.values()):
                break
        pot1 = float(np.mean([e._potential(p) for p in e.agent_positions]))
        print(f"  {cen:<26} Φ médio {pot0:8.1f} → {pot1:8.1f}   "
              f"recolhas (aleatório): {int(e.total_food_collected)}")
        if not np.isfinite(pot1):
            erro(f"{cen}: potencial infinito depois de {passos} passos — algum "
                 f"agente saiu para uma zona sem campo")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verboso", action="store_true")
    args = ap.parse_args()

    cenarios = list(SCENARIOS)
    if ALVO not in cenarios:
        cenarios.append(ALVO)
    print("A construir os", len(cenarios), "cenários...")
    envs = {}
    for c in cenarios:
        try:
            envs[c] = _env(c)
        except Exception as exc:                              # pragma: no cover
            erro(f"{c}: não construiu ({exc})")
    print()

    tabela_comparativa(envs)
    verificar_paredes(envs)
    mapas = verificar_alcancabilidade(envs, args.verboso)
    verificar_orcamento(envs)
    verificar_geodesico(envs, mapas)
    episodio_de_fumo(envs)

    print()
    print("=" * 78)
    print("RESUMO")
    print("=" * 78)
    for t in _problemas:
        print(f"  ERRO   {t}")
    for t in _avisos:
        print(f"  AVISO  {t}")
    if not _problemas and not _avisos:
        print("  Nada a assinalar: o mapa grande comporta-se como os sete.")
    print(f"\n{len(_problemas)} erro(s), {len(_avisos)} aviso(s)")
    return 1 if _problemas else 0


if __name__ == "__main__":
    sys.exit(main())
