#!/usr/bin/env python3
"""O mapa grande é RESOLÚVEL? — teste de sanidade com um controlador de referência.

Porque existe
O F1 (zero-shot dos 21 campeões no `mapa_grande`) deu 0,00 recolhas/ep nas
quatro condições, depois de tapar o céu que deixava os agentes voarem por cima
das paredes. Um zero em todas as condições tem duas leituras muito diferentes:

  (a) as políticas treinadas em arenas de raio 15 não transferem para o mapa —
      resultado científico, reportável;
  (b) o mapa não é resolúvel de todo (episódio curto demais, passagens estreitas
      demais, ninho inalcançável) — nesse caso o zero não diz nada sobre
      transferência, diz que o cenário está mal parametrizado.

Os controlos do pré-registo não separam (a) de (b): todos eles avaliam *políticas
aprendidas*. Este script separa, usando um controlador que não aprendeu nada:
segue a descida do campo geodésico ao ninho (Dijkstra 8-conexo, já calculado pelo
ambiente para o shaping). É o melhor navegador possível dado o mapa — se ele não
recolhe, ninguém recolhe.

O que mede
Por episódio: recolhas, passo da primeira recolha, distância geodésica inicial ao
ninho (mín/média/máx sobre os agentes), quantos agentes chegaram alguma vez, e
quantos ficaram presos (potencial que não desce durante 200 passos).

Uso
---
    python scripts/sanidade_mapa_grande.py                       # mapa_grande, 3 seeds
    python scripts/sanidade_mapa_grande.py --cenario four_rooms  # referência sã
    python scripts/sanidade_mapa_grande.py --passos 8000         # o tempo é o limite?
"""
from __future__ import annotations

import argparse
import copy
import os
import sys

import numpy as np
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "src"))

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

# Direções candidatas: 16 no plano horizontal. O campo geodésico é planar (o
# Dijkstra corre numa grelha X/Y), por isso subir não ajuda — e desde a correção
# das paredes também não é atalho nenhum.
_ANGULOS = np.linspace(0, 2 * np.pi, 16, endpoint=False)
_DIRECOES = np.stack([np.cos(_ANGULOS), np.sin(_ANGULOS), np.zeros_like(_ANGULOS)], axis=1)

PASSO = 0.2  # metros por passo e por eixo (o clip de move_local no ambiente)

# Distância a que se SONDA o campo, que não é a distância que se ANDA. O campo
# geodésico vive numa grelha de `geodesic_cell_size` (0,4 m): sondar a 0,2 m cai
# quase sempre na mesma célula, todas as direções empatam a zero e o argmin
# escolhe sempre a primeira — o agente anda em linha reta para +x e encosta-se a
# uma parede. Sonda-se a 1,2 m (3 células) e anda-se 0,2 m na direção escolhida.
SONDA = 1.2


def _acao_para(direcao: np.ndarray, heading: np.ndarray) -> np.ndarray:
    """Direção no mundo -> ação nas coordenadas locais F/R/U do agente.

    O ambiente faz `move_global = a[0]*F + a[1]*R + a[2]*U` com a base ortonormal,
    portanto as componentes da direção nessa base são a ação que a reproduz.
    """
    F = heading
    W = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(F, W)) > 0.99:
        W = np.array([0.0, 1.0, 0.0])
    R = np.cross(F, W)
    R /= np.linalg.norm(R) + 1e-6
    U = np.cross(R, F)
    return np.array([np.dot(direcao, F), np.dot(direcao, R), np.dot(direcao, U)])


def politica_geodesica(env: SwarmForagingEnv3D) -> dict:
    """Cada agente vai para onde o potencial geodésico ao ninho é menor.

    Não usa a observação: é de propósito. A pergunta aqui não é «uma política
    consegue aprender isto a partir do que vê?», é «existe caminho e cabe no
    tempo do episódio?».
    """
    acoes = {}
    for idx, agente in enumerate(env.agents):
        pos = env.agent_positions[idx]
        candidatos = pos + _DIRECOES * SONDA
        potenciais = [env._potential(p) for p in candidatos]
        melhor = int(np.argmin(potenciais))
        acoes[agente] = _acao_para(_DIRECOES[melhor], env.agent_headings[idx]).astype(np.float32)
    return acoes


def corre_episodio(cfg: dict, seed: int, passos_max: int | None) -> dict:
    env = SwarmForagingEnv3D(config=copy.deepcopy(cfg))
    if passos_max is not None:
        env.max_steps = passos_max
    env.reset(seed=seed)

    pot_inicial = np.array([env._potential(p) for p in env.agent_positions])
    chegou = np.zeros(env.num_agents, dtype=bool)
    pot_anterior = pot_inicial.copy()
    parado_ha = np.zeros(env.num_agents, dtype=int)
    primeira = None

    for passo in range(env.max_steps):
        _, _, _, _, _ = env.step(politica_geodesica(env))

        pot = np.array([env._potential(p) for p in env.agent_positions])
        parado_ha = np.where(pot < pot_anterior - 1e-9, 0, parado_ha + 1)
        pot_anterior = pot
        chegou |= pot < (env.nest_radius + 0.2)

        if primeira is None and env.total_food_collected > 0:
            primeira = passo + 1

    return {
        "seed": seed,
        "passos": env.max_steps,
        "recolhas": env.total_food_collected,
        "primeira": primeira,
        "geo_min": float(pot_inicial.min()),
        "geo_med": float(pot_inicial.mean()),
        "geo_max": float(pot_inicial.max()),
        "chegaram": int(chegou.sum()),
        "presos": int((parado_ha > 200).sum()),
        "agentes": env.num_agents,
        "raio": env.arena_radius,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cenario", default="mapa_grande")
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--passos", type=int, default=None,
                   help="força max_steps (por omissão usa o do cenário)")
    args = p.parse_args()

    # A consola do Windows é cp1252 e rebenta com setas/travessões a meio de um
    # resultado já calculado — o diagnóstico perder-se-ia por causa da impressão.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    with open(os.path.join(RAIZ, "configs", "foraging.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = args.cenario

    print(f"[i] cenário: {args.cenario}   controlador: descida do campo geodésico (não aprendido)")
    linhas = []
    for seed in range(1, args.seeds + 1):
        r = corre_episodio(cfg, seed, args.passos)
        linhas.append(r)
        primeira = r["primeira"] if r["primeira"] is not None else "—"
        print(f"    seed {seed}: recolhas={r['recolhas']:3d}  1.ª recolha ao passo {primeira}"
              f"  chegaram ao ninho {r['chegaram']}/{r['agentes']}  presos {r['presos']}"
              f"  |  distância geodésica inicial min/média/máx ="
              f" {r['geo_min']:.1f}/{r['geo_med']:.1f}/{r['geo_max']:.1f} m")

    recolhas = np.array([r["recolhas"] for r in linhas])
    ref = linhas[0]
    passos_para_ida = ref["geo_med"] / PASSO
    print()
    print(f"[=] {recolhas.mean():.2f} recolhas/ep (n={len(linhas)}), arena r={ref['raio']:.0f} m,"
          f" {ref['passos']} passos por episódio")
    print(f"[=] a ida média até ao ninho custa ~{passos_para_ida:.0f} passos a 0,2 m/passo"
          f"  ⇒  teto teórico ~{ref['passos'] / max(passos_para_ida, 1):.1f} viagens por agente")
    if recolhas.sum() == 0:
        print("[!] NEM O CONTROLADOR DE REFERÊNCIA RECOLHE: o zero do F1 não é sobre "
              "transferência — o cenário está mal parametrizado (tempo, passagens ou ninho).")
    else:
        print("[v] o mapa é resolúvel: o zero do F1 é das políticas, não do cenário.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
