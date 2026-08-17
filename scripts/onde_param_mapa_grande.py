#!/usr/bin/env python3
"""
onde_param_mapa_grande.py — o zero do F2 tem um mecanismo, e ele mede-se
=========================================================================
Os 42 campeões do braço dos gradientes (PPO 21 + SAC 21, treinados de raiz no
mapa grande) recolhem **0,00** em 840 episódios de avaliação. Um zero é um
número pobre: não distingue "os agentes não se mexem" de "os agentes fazem o
percurso quase todo e ficam-se a dez metros do fim". A secção da tese não pode
afirmar nem uma coisa nem a outra sem medir, e o `total_reward` já diz que a
segunda é a mais provável — os episódios acumulam recompensa POSITIVA
(6 900 a 11 500 no PPO) num ambiente onde só a aproximação ao ninho paga.

Este script transforma essa suspeita em números. Para cada campeão corre
episódios instrumentados e regista, a cada passo, o **potencial do ambiente** de
cada agente — que no `mapa_grande` é exatamente a distância geodésica ao ninho,
o alvo da tarefa (`required_to_eat=1`: basta um agente entrar no ninho para
contar uma recolha).

⚠️ A RÉGUA É A DO AMBIENTE, de propósito. `env._potential(pos)` é a mesma
função que produz o `progress` da recompensa que treinou estes modelos. A 5 de
agosto publicou-se aqui um 13,4% que devia ser 17,0% precisamente por se ter
medido uma grandeza do ambiente com uma régua escrita à parte; medir a distância
"à mão" com `np.linalg.norm` daria a euclidiana, e nos labirintos do mapa a
euclidiana atravessa paredes. Se um dia o potencial deixar de ser a distância ao
ninho, este script passa a medir outra coisa — daí a verificação de sanidade no
arranque, que compara o potencial no ninho com zero.

O que sai (uma linha por episódio, em CSV):

  d_inicial   potencial do agente mais próximo no passo 0 (o percurso a fazer)
  d_min       o MENOR potencial atingido por qualquer agente no episódio
  passo_min   em que passo isso aconteceu (revela se pararam ou se ainda iam)
  fracao      1 - d_min/d_inicial: que fração do percurso o enxame cobriu
  d_final     potencial do agente mais próximo no último passo
  recuou      d_final - d_min: se é grande, chegaram perto e afastaram-se
  caminho     distância média efetivamente percorrida por agente (euclidiana:
              aqui a pergunta é "quanto andaram", não "quão longe estão")

Uso (no servidor, onde vivem os 42 campeões):

    python3 scripts/onde_param_mapa_grande.py \
        --models-dir ~/mapa_F2_ppo --algo ppo --episodes 3
    python3 scripts/onde_param_mapa_grande.py \
        --models-dir ~/mapa_F2_sac --algo sac --episodes 3

Custo: ~2000 passos × 20 agentes por episódio. É avaliação, não treino — mas
corre-se com `nice` para não roubar CPU ao braço do GNN, que ainda está a fechar.
"""
import argparse
import glob
import os
import re
import sys
import time

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

MAPA = "mapa_grande"


def _carregar(algo, caminho):
    """Carrega um campeão: PPO/SAC da Stable-Baselines3, ou um genoma do GNN.

    O GNN entrou aqui a 17 ago, quando o seu braço fechou. Sem ele, este script
    respondia «o PPO fica-se a 76 m» e mais nada — e a pergunta que interessa
    não é onde o PPO para, é **porque é que o GNN passa e ele não**. Medir os
    dois com a mesma régua, no mesmo mapa e com as mesmas sementes é o que
    transforma dois números soltos numa comparação.
    """
    if algo == "ppo":
        from stable_baselines3 import PPO
        return PPO.load(caminho, device="cpu")
    if algo == "sac":
        from stable_baselines3 import SAC
        return SAC.load(caminho, device="cpu")
    if algo == "gnn":
        import torch
        from src.agents.gnn_agent_3d import GNNAgent3D
        cfg = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
        env_tmp = SwarmForagingEnv3D(config_path=cfg)
        agente = GNNAgent3D("eval", env_tmp.action_space("robot_0"), cfg)
        agente.load_state_dict(torch.load(caminho, weights_only=True))
        agente.eval()
        return agente
    raise SystemExit("algo tem de ser ppo, sac ou gnn")


def _acoes(env, algo, modelo, obs_dict):
    """As ações de todos os agentes, no formato de cada arquitetura.

    O GNN avalia o enxame INTEIRO de uma vez (a atenção é sobre a vizinhança);
    as políticas MLP do PPO/SAC avaliam um agente de cada vez. É a mesma
    distinção do `heatmaps._policy_actions`, e a razão pela qual só uma delas
    aceita um enxame de outro tamanho.
    """
    if algo == "gnn":
        import torch
        obs = np.array([obs_dict[a] for a in env.agents], dtype=np.float32)
        with torch.no_grad():
            acts = modelo(torch.tensor(obs)).cpu().numpy()
        return {a: acts[i] for i, a in enumerate(env.agents)}
    saida = {}
    for agente in env.agents:
        obs = np.array(obs_dict[agente], dtype=np.float32)
        accao, _ = modelo.predict(obs, deterministic=True)
        saida[agente] = accao
    return saida


def _sanidade_da_regua(env):
    """O potencial no ninho tem de ser ~0, e o potencial tem de crescer quando se
    anda para longe. Sem isto, uma alteração futura ao `_potential` transformava
    este script num gerador de números plausíveis e errados."""
    no_ninho = env._potential(env.nest_pos.copy())
    longe = env._potential(env.nest_pos + np.array([env.arena_radius * 0.5, 0.0, 0.0]))
    if no_ninho > 1.0:
        raise SystemExit(
            "[!] o potencial no ninho é %.2f, não ~0: `_potential` deixou de ser "
            "a distância ao alvo e este script mediria outra coisa." % no_ninho)
    if longe <= no_ninho:
        raise SystemExit(
            "[!] o potencial não cresce ao afastar do ninho (%.2f no ninho, %.2f "
            "a meio raio): a régua está invertida." % (no_ninho, longe))


def episodio_instrumentado(env, algo, modelo, seed):
    """Corre um episódio e devolve o que se passou com as DISTÂNCIAS.

    O laço é o mesmo do `scripts/eval_all.py:run_episode` — a política é
    determinística e as seeds são as mesmas —, com a instrumentação por passo
    acrescentada. Não substitui a avaliação oficial: as recolhas continuam a vir
    de lá, e este script só existe para explicar o zero que ela reporta.
    """
    obs_dict, _ = env.reset(seed=seed)

    pot0 = np.array([env._potential(p) for p in env.agent_positions])
    pos_ant = env.agent_positions.copy()
    caminho = np.zeros(env.num_agents)

    d_min, passo_min = float(pot0.min()), 0
    passos = 0
    while True:
        acoes = _acoes(env, algo, modelo, obs_dict)
        obs_dict, _, terms, truncs, _ = env.step(acoes)
        passos += 1

        # Andado neste passo, ANTES de qualquer teletransporte: quando um agente
        # entra no ninho o ambiente repõe-no no spawn, e sem este cuidado o salto
        # de 128 m entrava na conta como se ele o tivesse percorrido.
        d = np.linalg.norm(env.agent_positions - pos_ant, axis=1)
        caminho += np.where(d < env.arena_radius * 0.5, d, 0.0)
        pos_ant = env.agent_positions.copy()

        pot = np.array([env._potential(p) for p in env.agent_positions])
        if pot.min() < d_min:
            d_min, passo_min = float(pot.min()), passos

        if any(terms.values()) or any(truncs.values()):
            break

    pot_fim = np.array([env._potential(p) for p in env.agent_positions])
    d_inicial = float(pot0.min())
    return {
        "d_inicial": d_inicial,
        "d_min": d_min,
        "passo_min": passo_min,
        "fracao": 1.0 - d_min / d_inicial if d_inicial > 0 else np.nan,
        "d_final": float(pot_fim.min()),
        "recuou": float(pot_fim.min()) - d_min,
        "caminho": float(caminho.mean()),
        "passos": passos,
        "recolhas": int(env.total_food_collected),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", required=True,
                   help="pasta da campanha (ex.: ~/mapa_F2_ppo)")
    p.add_argument("--algo", required=True, choices=["ppo", "sac", "gnn"])
    p.add_argument("--episodes", type=int, default=3,
                   help="episódios por campeão (o objetivo é o mecanismo, não a "
                        "precisão da média: 3 chegam para separar 10 m de 100 m)")
    p.add_argument("--runs", type=int, default=0,
                   help="limitar aos primeiros N campeões (0 = todos)")
    p.add_argument("--seed-base", type=int, default=1000,
                   help="a mesma da avaliação oficial, para os episódios serem "
                        "os mesmos")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    raiz = os.path.expanduser(args.models_dir)
    if args.algo == "gnn":
        # O evolutivo guarda um `.pth` por execução na própria pasta, e o
        # ficheiro SEM sufixo `_runN` é o campeão global — entraria como uma
        # execução a mais, duplicando a melhor. O padrão exige o sufixo.
        padroes = [os.path.join(raiz, "gnn_3d_best_%s_run*.pth" % MAPA),
                   os.path.join(raiz, "models", "gnn_3d_best_%s_run*.pth" % MAPA)]
    else:
        padroes = [os.path.join(raiz, "models_%s" % args.algo,
                                "%s_3d_final_%s_run*.zip" % (args.algo, MAPA))]
    campeoes = []
    for padrao in padroes:
        campeoes = sorted(glob.glob(padrao),
                          key=lambda f: int(re.search(r"run(\d+)", f).group(1)))
        if campeoes:
            break
    if not campeoes:
        raise SystemExit("[!] nenhum campeão em %s" % " nem ".join(padroes))
    if args.runs:
        campeoes = campeoes[:args.runs]

    destino = args.out or os.path.join(
        PROJECT_ROOT, "results", "mapa_grande",
        "onde_param_%s.csv" % args.algo)
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    cfg = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    env = SwarmForagingEnv3D(config_path=cfg)
    env.config["environment"]["classic_scenario"] = MAPA
    env.reset(seed=0)
    _sanidade_da_regua(env)

    print("=" * 74)
    print("ONDE PARAM OS AGENTES — %s, %d campeões × %d episódios"
          % (args.algo.upper(), len(campeoes), args.episodes))
    print("  régua: env._potential (distância geodésica ao ninho, a mesma que "
          "paga o progress)")
    print("=" * 74)

    linhas = []
    t0 = time.time()
    for caminho_modelo in campeoes:
        run = int(re.search(r"run(\d+)", caminho_modelo).group(1))
        modelo = _carregar(args.algo, caminho_modelo)
        for ep in range(args.episodes):
            r = episodio_instrumentado(env, args.algo, modelo,
                                       seed=args.seed_base + ep)
            r.update(Algorithm=args.algo.upper(), Run=run, Episode=ep)
            linhas.append(r)
            print("  run %2d ep %d | inicial %6.1f m -> mínimo %6.1f m "
                  "(%.0f%% do percurso, passo %4d) | fim %6.1f m | "
                  "andou %6.1f m | recolhas %d"
                  % (run, ep, r["d_inicial"], r["d_min"], 100 * r["fracao"],
                     r["passo_min"], r["d_final"], r["caminho"], r["recolhas"]))
        # Gravar a cada campeão: são 21 modelos e a corrida leva o seu tempo.
        pd.DataFrame(linhas).to_csv(destino, index=False)

    df = pd.DataFrame(linhas)
    print("-" * 74)
    print("RESUMO %s — %d episódios em %.0f min"
          % (args.algo.upper(), len(df), (time.time() - t0) / 60))
    print("  percurso inicial a fazer  : %6.1f m (mediana)" % df.d_inicial.median())
    print("  distância mínima atingida : %6.1f m (mediana)  [min %.1f, máx %.1f]"
          % (df.d_min.median(), df.d_min.min(), df.d_min.max()))
    print("  fração do percurso coberta: %6.1f%% (mediana)" % (100 * df.fracao.median()))
    print("  andado por agente         : %6.1f m (mediana)" % df.caminho.median())
    print("  passo do mínimo           : %6.0f de %d (mediana)"
          % (df.passo_min.median(), df.passos.median()))
    print("  recuo depois do mínimo    : %6.1f m (mediana)" % df.recuou.median())
    print("  recolhas                  : %d em %d episódios"
          % (df.recolhas.sum(), len(df)))
    print("\n[OK] %s" % os.path.relpath(destino, PROJECT_ROOT))


if __name__ == "__main__":
    main()
