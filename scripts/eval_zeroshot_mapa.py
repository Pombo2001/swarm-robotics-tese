"""
eval_zeroshot_mapa.py — F1 do pré-registo: Zero-Shot de TOPOLOGIA
=================================================================
Avalia os modelos campeões (treinados nos 7 cenários) num mapa em que NUNCA
treinaram — por omissão o `mapa_grande`. Responde à pergunta da QI7: o que os
algoritmos aprenderam em cenários de dificuldade ISOLADA transfere para um
ambiente que os COMBINA a 4x a escala?

É Zero-Shot de topologia, e não de dimensão do enxame (a bateria N∈{10,20,50,100}
que já existe em `eval_scalability.py`). Só é possível porque a observação tem a
mesma dimensão em todos os cenários (16+(N-1)*5 = 111 com N=20): os `.pth`/`.zip`
existentes carregam sem alteração nenhuma.

⚠️ Isto NÃO substitui a fase F2 (treino nativo). É a fase F1 do
`docs/PRE_REGISTO_MAPA_GRANDE.md`: barata (horas, não dias), corre localmente e a
sua leitura não depende do treino nativo. O contraste F1 vs F2 é, em si, um
resultado — e é reportado mesmo que dê 0 em todas as células.

⚠️ CONFUNDENTE, tratado com uma condição de CONTROLO: as distâncias da observação
são normalizadas pelo raio da arena. O mapa_grande corre a r=60 e os 7 cenários a
r=15, por isso o mesmo modelo vê tudo comprimido 4x (÷120 em vez de ÷30). Um zero
pode então vir da topologia nova OU só da mudança de escala. Correr as duas
condições (`--norm-obs mapa` e `--norm-obs treino`) separa as causas.

Uso:
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 5   # rápido
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 20  # oficial
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --origens u_wall four_rooms
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --norm-obs treino  # controlo

Retomável: se a corrida for interrompida (o PC desligou-se), basta repetir o mesmo
comando — as células já completas são saltadas. Um CSV de outro ambiente (o mapa
mudou entretanto) não é reutilizado nem apagado: vai para `*_ANTIGO.csv`.

Saída: results/evaluation/zeroshot_<mapa>.csv  (1 linha por episódio)
"""
import argparse
import copy
import hashlib
import os
import sys

import numpy as np
import pandas as pd
import yaml

try:
    # line_buffering: esta corrida leva horas e costuma ir para um ficheiro
    # (`> log 2>&1`). Sem isto o stdout fica em buffer de 8 kB e o log aparece
    # VAZIO durante quase todo o tempo — impossível saber se está a progredir ou
    # pendurado, que é precisamente o que se quer saber num job destes.
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import THESIS_SCENARIOS, SCENARIO_LABELS_SHORT, scenario_suffix

EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")

# Campeão de cada cenário de origem, por algoritmo (a convenção de nomes do projeto).
_CAMPEAO = {
    "gnn": ("models", "gnn_3d_best{suf}.pth"),
    "ppo": ("models_ppo", "ppo_3d_final{suf}.zip"),
    "sac": ("models_sac", "sac_3d_final{suf}.zip"),
}


def _caminho_campeao(algo, origem):
    sub, padrao = _CAMPEAO[algo]
    fp = os.path.join(PROJECT_ROOT, "results", sub,
                      padrao.format(suf=scenario_suffix(origem)))
    return fp if os.path.exists(fp) else None


def _impressao_digital(cfg, mapa):
    """Impressão digital do ambiente FÍSICO: geometria + o que muda o episódio.

    Vai para uma coluna do CSV. Sem isto, retomar uma corrida DEPOIS de mexer no
    mapa juntava, no mesmo ficheiro, células de dois ambientes diferentes — e a
    comparação entre origens deixava de ser emparelhada sem dar sinal nenhum.

    O normalizador da observação NÃO entra aqui de propósito: não muda o mundo,
    só o que o modelo lê dele. Fica na coluna NormObs, para as duas condições
    poderem viver no mesmo ficheiro.
    """
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    e = SwarmForagingEnv3D(config=copy.deepcopy(cfg))
    e.reset(seed=0)
    partes = [
        "|".join("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (*w["pos"], *w["size"])
                 for w in e.walls),
        "obst=%d" % len(e.obstacles),
        "ninho=%.4f,%.4f" % (e.nest_pos[0], e.nest_pos[1]),
        "N=%d steps=%d arena=%.1f req=%d" % (
            e.num_agents, e.max_steps, e.arena_radius, e.required_to_eat),
    ]
    return hashlib.sha1("¬".join(partes).encode("utf-8")).hexdigest()[:12]


def _carregar_parciais(dest, digital, norm_obs, episodes):
    """Lê o CSV de uma corrida interrompida e devolve (linhas, células feitas).

    As duas condições de normalização convivem no mesmo ficheiro (é esse o
    objetivo: compará-las), por isso as linhas da OUTRA condição preservam-se.
    O que não se mistura é ambiente: se o mapa mudou desde a última corrida, o
    ficheiro inteiro é posto de lado — nunca apagado, nunca escrito por cima."""
    if not os.path.exists(dest):
        return [], set()
    velho = pd.read_csv(dest)

    def _arquivar(porque):
        bak = dest.replace(".csv", "_ANTIGO.csv")
        os.replace(dest, bak)
        print("[!] %s\n    O CSV que lá estava foi guardado em %s; a começar do zero."
              % (porque, os.path.relpath(bak, PROJECT_ROOT)))
        return [], set()

    if "env_hash" not in velho.columns or "NormObs" not in velho.columns:
        return _arquivar("CSV de uma versão anterior do script (sem env_hash).")
    if (velho["env_hash"] != digital).any():
        return _arquivar("O mapa mudou desde essa corrida (env_hash diferente).")

    desta = velho[velho["NormObs"] == norm_obs]
    feitas = {(a, o) for (a, o), g in desta.groupby(["Algorithm", "Origem"])
              if len(g) >= episodes}
    # Descarta células a meio: um bloco incompleto não é comparável com os outros.
    incompletas = [(a, o) for a, o in zip(desta["Algorithm"], desta["Origem"])
                   if (a, o) not in feitas]
    manter = velho[[(n != norm_obs) or ((a, o) in feitas) for n, a, o
                    in zip(velho["NormObs"], velho["Algorithm"], velho["Origem"])]]
    if feitas:
        print("[=] Retomada: %d células já completas nesta condição — a saltar."
              % len(feitas))
    if incompletas:
        print("[=] %d episódios de células incompletas descartados (voltam a correr)."
              % len(incompletas))
    outras = len(manter) - sum(1 for n in manter["NormObs"] if n == norm_obs)
    if outras:
        print("[=] %d episódios da outra condição de normalização preservados."
              % outras)
    return ([manter] if not manter.empty else []), feitas


def avaliar(mapa="mapa_grande", origens=None, algos=None, episodes=20,
            seed_base=1000, norm_obs="mapa", refazer=False):
    from scripts.eval_all import eval_algo

    origens = origens or THESIS_SCENARIOS
    algos = algos or ["gnn", "ppo", "sac"]

    # Config temporário com o cenário-alvo — o eval_algo lê o classic_scenario
    # do config, e não queremos tocar no configs/foraging.yaml do repositório.
    with open(os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg = copy.deepcopy(cfg)
    cfg["environment"]["classic_scenario"] = mapa

    # ── Normalizador das distâncias na observação ────────────────────────────
    # 'mapa'  : o do próprio mapa (r=60 -> ÷120). É a condição natural.
    # 'treino': o dos 7 cenários (r=15 -> ÷30). CONTROLO — ver o pré-registo.
    # Sem o par, um zero decorre de duas causas que não se distinguem:
    # topologia nova OU todas as distâncias comprimidas 4x à entrada do modelo.
    if norm_obs == "treino":
        cfg["environment"]["obs_norm_radius"] = float(
            cfg["environment"].get("arena_radius", 15.0))
    elif norm_obs != "mapa":
        raise ValueError("--norm-obs tem de ser 'mapa' ou 'treino'")

    # Guarda: os campeões só carregam se obs_dim bater certo (16+(N-1)*5).
    n_ag = cfg["environment"].get("num_agents")
    if n_ag != 20:
        raise SystemExit(
            f"[X] num_agents={n_ag} no configs/foraging.yaml. Os campeões dos 7 "
            f"cenários foram treinados com 20 (obs_dim=111) e com {n_ag} a "
            f"observação passa a {16 + (n_ag - 1) * 5} dims. Corrige o config "
            f"antes de correr o zero-shot.")

    os.makedirs(EVAL_DIR, exist_ok=True)
    tmp_cfg = os.path.join(EVAL_DIR, f"_cfg_zeroshot_{mapa}.yaml")
    with open(tmp_cfg, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    dest = os.path.join(EVAL_DIR, f"zeroshot_{mapa}.csv")
    digital = _impressao_digital(cfg, mapa)
    print(f"[i] ambiente {digital} | normalizador da obs: {norm_obs} "
          f"(÷{2 * (cfg['environment'].get('obs_norm_radius') or 60.0):.0f})")

    if refazer and os.path.exists(dest):
        os.replace(dest, dest.replace(".csv", "_ANTIGO.csv"))
        linhas, feitas = [], set()
    else:
        linhas, feitas = _carregar_parciais(dest, digital, norm_obs, episodes)

    def _gravar():
        todo = pd.concat(linhas, ignore_index=True)
        todo.to_csv(dest, index=False)
        return todo

    for algo in algos:
        for origem in origens:
            if (algo.upper(), origem) in feitas:
                continue
            fp = _caminho_campeao(algo, origem)
            if fp is None:
                print(f"[--] {algo.upper():4s} treinado em {origem}: sem campeão — saltar")
                continue
            print(f"\n[>>] {algo.upper()} treinado em '{origem}' -> avaliado em '{mapa}'")
            df, _ = eval_algo(algo, mapa, tmp_cfg, episodes,
                              seed_base=seed_base, model_path=fp)
            if df is None or df.empty:
                continue
            df = df.copy()
            df["Algorithm"] = algo.upper()
            df["Origem"] = origem
            df["Mapa"] = mapa
            df["NormObs"] = norm_obs
            df["env_hash"] = digital
            linhas.append(df)
            # Gravar a CADA célula, não só no fim: uma corrida destas leva ~1h e
            # se for interrompida a meio (PC desligado, Ctrl+C) o que já custou
            # fica no disco — e a corrida seguinte RETOMA daqui (as células
            # completas são saltadas), em vez de escrever por cima.
            print(f"     [gravado: {len(_gravar())} episódios acumulados]")

    if not linhas:
        print("\n[!] Nenhuma célula avaliada — não há campeões nos caminhos esperados.")
        return pd.DataFrame()

    out = _gravar()
    print(f"\n[OK] {len(out)} episódios -> {os.path.relpath(dest, PROJECT_ROOT)}")

    # Resumo por célula (descritivo — a inferência faz-se depois, no pré-registo)
    print("\nRECOLHAS/EP (média ± dp) [taxa de sucesso]")
    print("-" * 62)
    for algo in out["Algorithm"].unique():
        sub = out[out["Algorithm"] == algo]
        for origem in sub["Origem"].unique():
            c = sub[sub["Origem"] == origem]
            print("%-5s treinado em %-24s %5.1f ± %4.1f  [%3.0f%%]" % (
                algo, SCENARIO_LABELS_SHORT.get(origem, origem),
                c["food_collected"].mean(), c["food_collected"].std(ddof=0),
                100 * c["success"].mean()))
    try:
        os.remove(tmp_cfg)
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapa", default="mapa_grande")
    ap.add_argument("--origens", nargs="*", default=None,
                    help="cenários de origem dos campeões (por omissão: os 7 da tese)")
    ap.add_argument("--algos", nargs="*", default=None)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--norm-obs", choices=["mapa", "treino"], default="mapa",
                    help="normalizador das distâncias na observação: 'mapa' (r=60, "
                         "natural) ou 'treino' (r=15, condição de CONTROLO)")
    ap.add_argument("--refazer", action="store_true",
                    help="ignora o CSV existente e recomeça (guarda-o em _ANTIGO)")
    a = ap.parse_args()
    avaliar(a.mapa, a.origens, a.algos, a.episodes, a.seed_base,
            norm_obs=a.norm_obs, refazer=a.refazer)


if __name__ == "__main__":
    main()
