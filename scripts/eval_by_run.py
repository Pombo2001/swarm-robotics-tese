"""
eval_by_run.py — Avaliação determinística de TODOS os runs de uma campanha
===========================================================================
Os boxplots por run existentes usam o score de TREINO (fitness/reward, escalas
diferentes entre algoritmos). Para estatística honesta a tese precisa de
boxplots de AVALIAÇÃO: cada modelo `_run{n}` (preservado desde o fix da
armadilha nº8) avaliado com o protocolo emparelhado (mesmas seeds).

Produz results/evaluation/eval_by_run.csv (long-format: 1 linha por episódio,
com coluna Run) — é o input para boxplots de eval e statistical_tests por run.

Uso (standalone):
    python scripts/eval_by_run.py --episodes 20
    python scripts/eval_by_run.py --episodes 20 --scenarios u_wall,none --algos gnn
"""
import argparse
import glob
import os
import re
import sys

import pandas as pd

# Windows: evita UnicodeEncodeError (cp1252) ao imprimir caracteres de caixa.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")

from src.scenarios import (SCENARIOS as ALL_SCENARIOS,
                           SCENARIO_LABELS_SHORT as SCENARIO_LABELS,
                           scenario_suffix)
ALL_ALGOS = ["gnn", "ppo", "sac"]

# Onde vivem os modelos por run de cada algoritmo (padrão do nome com {suf}).
_RUN_GLOBS = {
    "gnn": ("models", "gnn_3d_best{suf}_run*.pth"),
    "ppo": ("models_ppo", "ppo_3d_final{suf}_run*.zip"),
    "sac": ("models_sac", "sac_3d_final{suf}_run*.zip"),
}


def _run_models(algo, scenario):
    """[(run, path)] dos modelos por run existentes para (algo, cenário)."""
    sub, pattern = _RUN_GLOBS[algo]
    suf = scenario_suffix(scenario)
    out = []
    for fp in glob.glob(os.path.join(PROJECT_ROOT, "results", sub,
                                     pattern.format(suf=suf))):
        m = re.search(r"_run(\d+)\.(pth|zip)$", os.path.basename(fp))
        if m:
            out.append((int(m.group(1)), fp))
    return sorted(out)


def evaluate_by_run(episodes=20, scenarios=None, algos=None, seed_base=1000,
                    config_path=None):
    """Avalia cada modelo _run{n} (emparelhado) e grava eval_by_run.csv.
    Devolve o DataFrame long-format (vazio se não há modelos por run)."""
    from scripts.eval_all import eval_algo

    if scenarios is None:
        scenarios = ALL_SCENARIOS
    if algos is None:
        algos = ALL_ALGOS
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    os.makedirs(EVAL_DIR, exist_ok=True)

    long_rows = []
    n_models = sum(len(_run_models(a, sc)) for sc in scenarios for a in algos)
    print(f"\n[EVAL-BY-RUN] {n_models} modelos por run | {episodes} ep cada | "
          f"emparelhada (seed-base={seed_base})")

    for sc in scenarios:
        label = SCENARIO_LABELS.get(sc, sc)
        for algo in algos:
            for run, fp in _run_models(algo, sc):
                try:
                    df, _ = eval_algo(algo, sc, config_path, episodes,
                                      seed_base, model_path=fp)
                except Exception as e:
                    print(f"  [!] {algo.upper()}/{sc}/run{run} falhou: {e}")
                    continue
                if df is None:
                    continue
                for _, r in df.iterrows():
                    long_rows.append({
                        "Scenario": sc, "ScenarioLabel": label,
                        "Algorithm": algo.upper(), "Run": run,
                        "food_collected": float(r["food_collected"]),
                        "success": bool(r["success"]),
                        "total_reward": float(r["total_reward"]),
                    })
                print(f"  [OK] {algo.upper():3s}/{sc:22s} run {run}: "
                      f"sucesso={df.success.mean()*100:5.1f}%  "
                      f"recolhas/ep={df.food_collected.mean():.2f}")

    out = pd.DataFrame(long_rows)
    if not out.empty:
        path = os.path.join(EVAL_DIR, "eval_by_run.csv")
        out.to_csv(path, index=False)
        print(f"[EVAL-BY-RUN] Guardado: {path}")
    else:
        print("[EVAL-BY-RUN] Nenhum modelo _run{n} encontrado — nada avaliado.")
    return out


def main():
    p = argparse.ArgumentParser(description="Avaliação por run (modelos _run{n})")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--scenarios", type=str, default=None,
                   help="Cenários separados por vírgula. Omitir = todos.")
    p.add_argument("--algos", type=str, default=None,
                   help="Algoritmos separados por vírgula (gnn,ppo,sac). Omitir = todos.")
    p.add_argument("--seed-base", type=int, default=1000)
    args = p.parse_args()

    scenarios = None
    if args.scenarios:
        req = [s.strip() for s in args.scenarios.split(",")]
        scenarios = [s for s in ALL_SCENARIOS if s in req]
    algos = None
    if args.algos:
        algos = [a.strip().lower() for a in args.algos.split(",")
                 if a.strip().lower() in ALL_ALGOS]

    evaluate_by_run(episodes=args.episodes, scenarios=scenarios, algos=algos,
                    seed_base=args.seed_base)


if __name__ == "__main__":
    main()
