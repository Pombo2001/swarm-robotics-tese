#!/usr/bin/env python3
"""Exporta um episódio para o browser o desenhar em 3D.

Porquê
------
O visualizador que existe (Ursina/Panda3D) abre uma janela no ecrã de **quem
corre o servidor**. Na torre isso é o que se quer; no Raspberry Pi — sem monitor,
e a servir o orientador pela internet — não serve de nada: a janela abriria numa
máquina onde ninguém está.

A alternativa é o 3D acontecer no browser de quem está a ver. Para isso o
servidor não precisa de renderizar nada: basta gravar **o que aconteceu** — a
geometria do cenário e a posição de cada agente ao longo do episódio — e deixar o
desenho para o lado do cliente.

Peso: um episódio de 2000 passos subamostrado de 3 em 3 dá ~280 KB de JSON
(~70 KB comprimido pelo servidor). A geometria (paredes, obstáculos, ninho) é
irrelevante ao lado disso.

Uso
---
    python scripts/exportar_episodio_3d.py --algo gnn --cenario u_wall
    python scripts/exportar_episodio_3d.py --algo gnn --cenario mapa_grande --passo 5
    python scripts/exportar_episodio_3d.py --todos              # os 7 da tese, GNN
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402
from src.scenarios import SCENARIO_LABELS, THESIS_SCENARIOS  # noqa: E402
from scripts.heatmaps import _policy_actions  # noqa: E402
from scripts.run_eval import load_model  # noqa: E402

DESTINO = os.path.join(RAIZ, "results", "episodios_3d")


def exportar(algo: str, cenario: str, seed: int = 2024, passo: int = 3,
             models_root: str | None = None, config_path: str | None = None) -> str:
    config_path = config_path or os.path.join(RAIZ, "configs", "foraging.yaml")
    env = SwarmForagingEnv3D(config_path=config_path)
    env.config["environment"]["classic_scenario"] = cenario

    # Sem modelo NÃO se exporta: um episódio de ações aleatórias com o nome do
    # algoritmo por cima é pior do que episódio nenhum (a mesma regra que se
    # aplicou aos GIFs).
    modelo = load_model(algo, cenario, config_path, models_root=models_root)

    obs, _ = env.reset(seed=seed)
    # A geometria é lida DEPOIS do reset: o ninho e os obstáculos só existem aí.
    paredes = [{"p": [round(float(v), 2) for v in w["pos"]],
                "s": [round(float(v), 2) for v in w["size"]]} for w in env.walls]
    obstaculos = [[round(float(v), 2) for v in o] for o in np.asarray(env.obstacles).reshape(-1, 3)]

    quadros, ninhos, recolhas_por_quadro = [], [], []
    recolhas = 0
    for i in range(env.max_steps):
        acoes = _policy_actions(env, algo, modelo, obs)
        obs, _, _, _, _ = env.step(acoes)
        if i % passo == 0:
            quadros.append([[round(float(v), 2) for v in p] for p in env.agent_positions])
            ninhos.append([round(float(v), 2) for v in env.nest_pos])
            recolhas_por_quadro.append(int(env.total_food_collected))
        recolhas = int(env.total_food_collected)

    dados = {
        "meta": {
            "algo": algo.upper(), "cenario": cenario,
            "rotulo": SCENARIO_LABELS.get(cenario, cenario),
            "seed": seed, "passo": passo,
            "passos": env.max_steps, "quadros": len(quadros),
            "agentes": env.num_agents, "recolhas": recolhas,
            "raio_arena": float(env.arena_radius),
            "raio_ninho": float(env.nest_radius),
            "raio_robo": float(env.robot_radius),
            "raio_obstaculo": float(env.obstacle_radius),
        },
        # `alturaParede` fica separado: as paredes têm todas a mesma altura
        # (2×raio da arena, desde a correção de 29 jul) e repeti-la em cada uma
        # seria um terço do ficheiro. O browser desenha-as até uma altura VISUAL
        # menor — a 120 m tapavam a cena toda.
        "geometria": {"paredes": paredes, "obstaculos": obstaculos},
        "quadros": quadros, "ninho": ninhos, "recolhas": recolhas_por_quadro,
    }

    os.makedirs(DESTINO, exist_ok=True)
    saida = os.path.join(DESTINO, f"{algo.lower()}_{cenario}.json")
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(dados, f, separators=(",", ":"))
    kb = os.path.getsize(saida) / 1024
    print(f"[v] {os.path.relpath(saida, RAIZ)}  ({kb:.0f} KB · {len(quadros)} quadros · "
          f"{recolhas} recolhas)")
    return saida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algo", default="gnn", choices=["gnn", "ppo", "sac"])
    p.add_argument("--cenario", default="u_wall")
    p.add_argument("--seed", type=int, default=2024)
    p.add_argument("--passo", type=int, default=3, help="guarda 1 em cada N passos")
    p.add_argument("--models-root", default=None,
                   help="pasta com models/ (por omissão: os modelos ativos)")
    p.add_argument("--todos", action="store_true",
                   help="os 7 cenários da tese com o GNN")
    a = p.parse_args()

    if a.todos:
        falhas = 0
        for cen in THESIS_SCENARIOS:
            try:
                exportar("gnn", cen, a.seed, a.passo, a.models_root)
            except Exception as e:                       # noqa: BLE001
                falhas += 1
                print(f"[!] {cen}: {type(e).__name__}: {str(e)[:70]}")
        return 1 if falhas else 0

    exportar(a.algo, a.cenario, a.seed, a.passo, a.models_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
