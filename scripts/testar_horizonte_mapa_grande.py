#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Os campeões que dão zero ficam sem TEMPO, ou ficam PRESOS? — a experiência.

    python scripts/testar_horizonte_mapa_grande.py --episodes 2

A instrumentação do `onde_param_mapa_grande.py` mostrou que o controlador
evolutivo atinge a sua menor distância ao ninho ao passo 1986 de 2000, e
recua 0,2 m depois disso: o episódio acaba-lhe em cima. Os métodos de gradiente
fazem o contrário — atingem o melhor por volta do passo 1200 e afastam-se.

Isso levanta uma hipótese testável e barata: se o limite for o horizonte,
alargar o episódio faz aparecer recolhas onde havia zero. Se for a política a
estar presa, mais passos não mudam nada.

Este guião faz exatamente esse teste: pega nos campeões, corre-os com o
horizonte de sempre e com um horizonte alargado, e conta recolhas. Não retreina
nada — a política é a mesma; muda só quanto tempo ela tem.

Isto não é o F2 nem entra na regra de decisão da QI7, que está fechada
com o horizonte pré-registado de 2000 passos. É uma experiência de diagnóstico
para a secção de trabalho futuro: diz o que valeria a pena tentar, não muda o
que foi medido.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

MAPA = "mapa_grande"
SAIDA = os.path.join(RAIZ, "results", "mapa_grande", "horizonte_gnn.csv")


def _campeoes(raiz):
    padrao = os.path.join(raiz, "gnn_3d_best_%s_run*.pth" % MAPA)
    return sorted(glob.glob(padrao),
                  key=lambda f: int(re.search(r"run(\d+)", f).group(1)))


def _agente(caminho, cfg_path):
    import torch
    from src.agents.gnn_agent_3d import GNNAgent3D
    env_tmp = SwarmForagingEnv3D(config_path=cfg_path)
    ag = GNNAgent3D("eval", env_tmp.action_space("robot_0"), cfg_path)
    ag.load_state_dict(torch.load(caminho, weights_only=True))
    ag.eval()
    return ag


def episodio(env, modelo, seed):
    """Um episódio determinístico. Devolve (recolhas, menor distância, passos)."""
    import torch
    obs, _ = env.reset(seed=seed)
    d_min = min(env._potential(p) for p in env.agent_positions)
    passos = 0
    while True:
        arr = np.array([obs[a] for a in env.agents], dtype=np.float32)
        with torch.no_grad():
            acts = modelo(torch.tensor(arr)).cpu().numpy()
        obs, _, terms, truncs, _ = env.step(
            {a: acts[i] for i, a in enumerate(env.agents)})
        passos += 1
        d_min = min(d_min, min(env._potential(p) for p in env.agent_positions))
        if any(terms.values()) or any(truncs.values()):
            break
    return int(env.total_food_collected), float(d_min), passos


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.path.join(RAIZ, "results",
                                                        "models_f2_gnn"))
    p.add_argument("--episodes", type=int, default=2)
    p.add_argument("--horizontes", default="2000,4000",
                   help="max_steps a comparar (o primeiro é o pré-registado)")
    p.add_argument("--seed-base", type=int, default=1000)
    a = p.parse_args()

    campeoes = _campeoes(os.path.expanduser(a.models_dir))
    if not campeoes:
        raise SystemExit("[!] nenhum campeão em %s" % a.models_dir)
    horizontes = [int(h) for h in a.horizontes.split(",")]

    cfg_path = os.path.join(RAIZ, "configs", "foraging.yaml")
    base = yaml.safe_load(open(cfg_path, encoding="utf-8"))

    print("=" * 74)
    print("HORIZONTE vs RECOLHAS — %d campeões × %d episódios × %s passos"
          % (len(campeoes), a.episodes, "/".join(map(str, horizontes))))
    print("  a política é a MESMA em todos: muda só quanto tempo ela tem")
    print("=" * 74)

    # Retomável: o que já está no CSV não se repete. Cada célula custa ~1 min
    # (um episódio de 4000 passos com 20 agentes), e a primeira corrida disto
    # levou com um `timeout` da shell a meio — sem esta leitura, recomeçar
    # custaria as oito execuções que já estavam medidas.
    linhas, feitos = [], set()
    if os.path.exists(SAIDA):
        antigo = pd.read_csv(SAIDA)
        linhas = antigo.to_dict("records")
        feitos = {(r["Run"], r["horizonte"], r["Episode"]) for r in linhas}
        print("  (retomado: %d células já medidas em %s)"
              % (len(feitos), os.path.basename(SAIDA)))

    for caminho in campeoes:
        run = int(re.search(r"run(\d+)", caminho).group(1))
        if all((run, h, ep) in feitos
               for h in horizontes for ep in range(a.episodes)):
            continue
        modelo = _agente(caminho, cfg_path)
        for h in horizontes:
            cfg = yaml.safe_load(yaml.dump(base))
            cfg["environment"]["classic_scenario"] = MAPA
            cfg["environment"]["max_steps_%s" % MAPA] = h
            env = SwarmForagingEnv3D(config=cfg)
            for ep in range(a.episodes):
                if (run, h, ep) in feitos:
                    continue
                rec, dmin, passos = episodio(env, modelo, a.seed_base + ep)
                linhas.append(dict(Run=run, horizonte=h, Episode=ep,
                                   recolhas=rec, d_min=dmin, passos=passos))
                print("  run %2d | %5d passos | ep %d | recolhas %2d | "
                      "chegou a %6.1f m" % (run, h, ep, rec, dmin))
        pd.DataFrame(linhas).to_csv(SAIDA, index=False)

    d = pd.DataFrame(linhas)
    print("-" * 74)
    for h in horizontes:
        s = d[d.horizonte == h]
        por_run = s.groupby("Run").recolhas.max()
        print("  %5d passos: %d de %d execuções com pelo menos uma recolha | "
              "mediana da distância mínima %5.1f m"
              % (h, int((por_run > 0).sum()), len(por_run), s.d_min.median()))
    print("[OK] %s" % os.path.relpath(SAIDA, RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
