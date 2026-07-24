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

Uso:
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 5   # rápido
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 20  # oficial
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --origens u_wall four_rooms

Saída: results/evaluation/zeroshot_<mapa>.csv  (1 linha por episódio)
"""
import argparse
import copy
import os
import sys

import numpy as np
import pandas as pd
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
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


def avaliar(mapa="mapa_grande", origens=None, algos=None, episodes=20,
            seed_base=1000):
    from scripts.eval_all import eval_algo

    origens = origens or THESIS_SCENARIOS
    algos = algos or ["gnn", "ppo", "sac"]

    # Config temporário com o cenário-alvo — o eval_algo lê o classic_scenario
    # do config, e não queremos tocar no configs/foraging.yaml do repositório.
    with open(os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg = copy.deepcopy(cfg)
    cfg["environment"]["classic_scenario"] = mapa
    tmp_cfg = os.path.join(EVAL_DIR, f"_cfg_zeroshot_{mapa}.yaml")
    os.makedirs(EVAL_DIR, exist_ok=True)
    with open(tmp_cfg, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    linhas = []
    for algo in algos:
        for origem in origens:
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
            linhas.append(df)
            # Gravar a CADA célula, não só no fim: uma corrida destas leva ~1h e
            # se for interrompida a meio (PC desligado, Ctrl+C) perde-se tudo o
            # que já custou. Assim o CSV é sempre válido e retomável.
            pd.concat(linhas, ignore_index=True).to_csv(
                os.path.join(EVAL_DIR, f"zeroshot_{mapa}.csv"), index=False)
            print(f"     [gravado: {sum(len(x) for x in linhas)} episódios acumulados]")

    if not linhas:
        print("\n[!] Nenhuma célula avaliada — não há campeões nos caminhos esperados.")
        return pd.DataFrame()

    out = pd.concat(linhas, ignore_index=True)
    dest = os.path.join(EVAL_DIR, f"zeroshot_{mapa}.csv")
    out.to_csv(dest, index=False)
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
    a = ap.parse_args()
    avaliar(a.mapa, a.origens, a.algos, a.episodes, a.seed_base)


if __name__ == "__main__":
    main()
