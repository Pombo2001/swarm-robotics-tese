# -*- coding: utf-8 -*-
"""Reproduz os números da limitação «dimensão vertical» (tese, §Limitações).

Porque existe
A tese passou a afirmar quatro coisas sobre a dimensão vertical: que os
controladores a usam (altitudes médias de 0,13 a 5,67 m, máximos de 14,6 m); que
a altitude se associa negativamente às recolhas (ρ = −0,74); que acima de 1,6 m
não há entrega possível; e que o limite vertical do mapa grande NÃO explica o
zero-shot a 0,00 — porque sem ele o resultado é o mesmo e porque os campeões
param a dezenas de metros do ninho.

As três primeiras leem-se dos episódios já exportados e da configuração, e são
baratas. A quarta exige correr campeões no mapa grande (~10 min), e está atrás de
`--campeoes` para o verificador rápido não a arrastar.

Uso:
    .venv/Scripts/python.exe scripts/verificar_vertical.py
    .venv/Scripts/python.exe scripts/verificar_vertical.py --campeoes
"""
import argparse
import glob
import json
import os
import sys
from itertools import groupby

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

EPISODIOS = os.path.join(RAIZ, "results", "episodios_3d")
CFG = os.path.join(RAIZ, "configs", "foraging.yaml")

# O que a tese diz, para a verificação ser uma COMPARAÇÃO e não uma impressão.
ESPERADO = {
    "z_med_min": 0.13, "z_med_max": 5.67, "z_max": 14.62,
    "rho": -0.74, "cenarios_concordantes": 5, "limiar_entrega": 1.6,
    "faixa_sete": 13.4, "faixa_mapa": 0.4,
}
TOL = 0.02

falhas = []


def compara(rotulo, obtido, esperado, tol=TOL):
    ok = abs(obtido - esperado) <= tol
    print(f"  {'[v]' if ok else '[X]'} {rotulo:<44} obtido {obtido:8.2f}   "
          f"tese {esperado:8.2f}")
    if not ok:
        falhas.append(f"{rotulo}: {obtido:.2f} vs {esperado:.2f} na tese")


def altitudes():
    print("=" * 74)
    print("1. ALTITUDE NOS EPISÓDIOS EXPORTADOS (21 células)")
    print("=" * 74)
    # Só os SETE. A frase da tese diz «$21$ células (três controladores ×
    # sete cenários)», e a pasta passou a ter 24 ficheiros quando o mapa grande
    # foi exportado — o 8.º cenário entrava aqui calado e mudava a contagem dos
    # cenários concordantes de 5 para 6. É a armadilha do ponto 1.7 do plano de
    # qualidade outra vez: a garantia de que o 8.º cenário fica de fora não pode
    # depender de ele ainda não ter dados. A lista vem do `src/scenarios.py`,
    # que é a fonte única.
    from src.scenarios import THESIS_SCENARIOS
    linhas, fora = [], []
    for p in sorted(glob.glob(os.path.join(EPISODIOS, "*.json"))):
        algo, cen = os.path.basename(p)[:-5].split("_", 1)
        if cen not in THESIS_SCENARIOS:
            fora.append(os.path.basename(p))
            continue
        d = json.load(open(p, encoding="utf-8"))
        zs = [abs(a[2]) for q in d["quadros"] for a in q]
        linhas.append((cen, algo, float(np.mean(zs)), float(np.max(zs)),
                       int(d["meta"]["recolhas"])))
    if fora:
        print(f"  [i] {len(fora)} episódio(s) fora dos sete cenários, "
              f"ignorados: {', '.join(fora)}")
    if len(linhas) != 21:
        falhas.append(f"esperava 21 episódios dos sete cenários, "
                      f"encontrei {len(linhas)}")
    meds = [r[2] for r in linhas]
    compara("altitude média mínima (m)", min(meds), ESPERADO["z_med_min"])
    compara("altitude média máxima (m)", max(meds), ESPERADO["z_med_max"])
    compara("altitude máxima (m)", max(r[3] for r in linhas), ESPERADO["z_max"])

    # Associação com as recolhas, centrada DENTRO de cada cenário: entre cenários
    # o nº de recolhas não é comparável (o Gargalo rende o dobro da Perceção).
    from scipy.stats import spearmanr
    zc, rc, concordam = [], [], 0
    for _, grupo in groupby(sorted(linhas), key=lambda r: r[0]):
        g = list(grupo)
        z = np.array([r[2] for r in g])
        rec = np.array([r[4] for r in g])
        zc += list((z - z.mean()) / (z.std() + 1e-9))
        rc += list((rec - rec.mean()) / (rec.std() + 1e-9))
        concordam += (max(g, key=lambda r: r[2])[1] == min(g, key=lambda r: r[4])[1])
    rho, p = spearmanr(zc, rc)
    compara("ρ de Spearman (altitude × recolhas)", float(rho), ESPERADO["rho"], 0.01)
    compara("cenários onde quem voa mais alto recolhe menos",
            float(concordam), float(ESPERADO["cenarios_concordantes"]), 0.5)
    print(f"      (p = {p:.4f}; um episódio por célula ⇒ indicativo, não teste)")


def geometria():
    print()
    print("=" * 74)
    print("2. O LIMIAR DE ENTREGA E A FAIXA IMPRODUTIVA")
    print("=" * 74)
    import yaml
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    with open(CFG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = "mapa_grande"
    e = SwarmForagingEnv3D(config=cfg)
    e.reset(seed=0)
    limiar = e.nest_radius + 0.1
    compara("acima desta altura não há entrega (m)", float(limiar),
            ESPERADO["limiar_entrega"])
    compara("faixa improdutiva no mapa grande (m)",
            float(e.MAPA_GRANDE_TETO - limiar), ESPERADO["faixa_mapa"])
    cfg["environment"]["classic_scenario"] = "u_wall"
    e7 = SwarmForagingEnv3D(config=cfg)
    e7.reset(seed=0)
    compara("faixa improdutiva nos sete (m)",
            float(e7.arena_radius - (e7.nest_radius + 0.1)), ESPERADO["faixa_sete"])


def campeoes():
    print()
    print("=" * 74)
    print("3. O LIMITE VERTICAL EXPLICA O ZERO-SHOT? (lento)")
    print("=" * 74)
    import torch
    import yaml
    from src.agents.gnn_agent_3d import GNNAgent3D
    from src.environment.swarm_env_3d import SwarmForagingEnv3D

    def episodio(caminho, com_teto, seed):
        with open(CFG, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        cfg["environment"]["classic_scenario"] = "mapa_grande"
        env = SwarmForagingEnv3D(config=cfg)
        if not com_teto:
            env.MAPA_GRANDE_TETO = float(env.arena_radius)
        obs, _ = env.reset(seed=seed)
        ag = GNNAgent3D("v", env.action_space("robot_0"), config_path=CFG)
        ag.load_state_dict(torch.load(caminho, weights_only=True))
        ag.eval()
        d2 = []
        for _ in range(env.max_steps):
            with torch.no_grad():
                acoes = {a: ag(torch.tensor(np.asarray(obs[a], dtype=np.float32))
                               ).numpy() for a in env.agents}
            obs, _, term, trunc, _ = env.step(acoes)
            d2.append(float(np.min(np.linalg.norm(
                env.agent_positions[:, :2] - env.nest_pos[:2], axis=1))))
            if any(term.values()) or any(trunc.values()):
                break
        return int(env.total_food_collected), min(d2)

    print(f"  {'campeão':<16} {'teto':>6} {'recolhas':>9} {'dist. mín. ao ninho (m)':>24}")
    d2_todas = []
    for cen in ("four_rooms", "u_wall", "bottleneck", "none"):
        sufixo = "" if cen == "none" else f"_{cen}"
        mp = os.path.join(RAIZ, "results", "models", f"gnn_3d_best{sufixo}.pth")
        if not os.path.exists(mp):
            print(f"  {cen:<16} (sem modelo — saltado)")
            continue
        for rotulo, com in (("2 m", True), ("sem", False)):
            recs, ds = [], []
            for seed in (1, 2, 3):
                r, d = episodio(mp, com, seed)
                recs.append(r)
                ds.append(d)
            print(f"  {cen:<16} {rotulo:>6} {np.mean(recs):9.2f} {min(ds):24.1f}")
            if com:
                d2_todas.append(min(ds))
            if np.mean(recs) != 0.0:
                falhas.append(f"{cen} ({rotulo} teto): {np.mean(recs):.2f} recolhas — "
                              f"a tese afirma 0,00 nas duas condições")
    # A tese arredonda para «entre 37 e 79 m»: o valor exato move-se ~0,1 m com
    # a semente, e um número com décima na tese faria este verificador acusar
    # uma divergência que não é uma.
    if d2_todas:
        compara("distância mínima ao ninho, menor (m)", min(d2_todas), 37.0, 1.0)
        compara("distância mínima ao ninho, maior (m)", max(d2_todas), 79.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campeoes", action="store_true",
                    help="corre também os campeões no mapa grande (~10 min)")
    args = ap.parse_args()

    altitudes()
    geometria()
    if args.campeoes:
        campeoes()

    print()
    print("=" * 74)
    if falhas:
        for f in falhas:
            print(f"  DIVERGE  {f}")
        print(f"\n{len(falhas)} divergência(s) entre a tese e os dados")
        return 1
    print("  Os números da limitação «dimensão vertical» batem com os dados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
