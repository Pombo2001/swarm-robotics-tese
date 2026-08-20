"""
eval_suite.py — Avaliação determinística de TODOS os cenários + gráficos de tarefa
==================================================================================
Resolve o desfasamento dos eval_*.csv: a rotina noturna treina mas não avaliava,
deixando as métricas de tarefa (taxa de sucesso, recolhas/ep) sempre desatualizadas
face aos modelos. Este módulo avalia os 3 algoritmos em todos os cenários de forma
EMPARELHADA (mesmas seeds) e produz:

  - results/evaluation/eval_{algo}_{cenario}.csv     (por episódio, métricas de tarefa)
  - results/evaluation/eval_comparacao_{cenario}.csv (resumo legível por cenário)
  - results/evaluation/eval_summary.csv              (long-format: 1 linha por episódio)

E, opcionalmente, os gráficos de tarefa (honestos e comparáveis entre algoritmos,
ao contrário do reward de treino que inclui shaping e mistura escalas):

  - taxa_sucesso_por_cenario.png   (Ptask: % de episódios com sucesso)
  - recolhas_por_cenario.png       (recolhas/ep, média ± desvio)

Uso (standalone):
    python scripts/eval_suite.py --episodes 20
    python scripts/eval_suite.py --episodes 30 --scenarios u_wall four_rooms
"""
import argparse
import os
import sys

import numpy as np
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
                           SCENARIO_LABELS_SHORT as SCENARIO_LABELS, ALGO_COLORS)
ALL_ALGOS = ["gnn", "ppo", "sac"]


def evaluate_all(episodes=20, scenarios=None, algos=None, seed_base=1000,
                 config_path=None):
    """Avalia (algo × cenário) de forma emparelhada e grava os CSVs.
    Devolve um DataFrame long-format (1 linha por episódio) ou vazio se nada avaliado."""
    from scripts.eval_all import eval_algo  # reutiliza o avaliador emparelhado

    if scenarios is None:
        scenarios = ALL_SCENARIOS
    if algos is None:
        algos = ALL_ALGOS
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    os.makedirs(EVAL_DIR, exist_ok=True)

    long_rows = []
    print(f"\n[EVAL-SUITE] Avaliação determinística | {episodes} ep/algo | "
          f"{len(scenarios)} cenários | emparelhada (seed-base={seed_base})")

    for sc in scenarios:
        label = SCENARIO_LABELS.get(sc, sc)
        comp = {}
        for algo in algos:
            try:
                df, path = eval_algo(algo, sc, config_path, episodes, seed_base)
            except Exception as e:
                print(f"  [!] {algo.upper()}/{sc} falhou: {e}")
                continue
            if df is None:
                continue  # modelo em falta (eval_algo já avisou)

            df.to_csv(os.path.join(EVAL_DIR, f"eval_{algo}_{sc}.csv"), index=False)
            comp[algo.upper()] = {
                "Recolhas/ep":  f"{df.food_collected.mean():.2f} +/- {df.food_collected.std():.2f}",
                "Task reward":  f"{df.task_reward.mean():.0f} +/- {df.task_reward.std():.0f}",
                "Total reward": f"{df.total_reward.mean():.0f} +/- {df.total_reward.std():.0f}",
                "Taxa sucesso": f"{df.success.mean()*100:.0f}%  ({int(df.success.sum())}/{episodes})",
                "Passos medios": f"{df.episode_length.mean():.1f}",
            }
            for _, r in df.iterrows():
                long_rows.append({
                    "Scenario": sc, "ScenarioLabel": label, "Algorithm": algo.upper(),
                    "food_collected": float(r["food_collected"]),
                    "success": bool(r["success"]),
                    "total_reward": float(r["total_reward"]),
                    # Igual ao eval_by_run: a M3 do mapa grande precisa disto, e
                    # dois CSV do mesmo pipeline com colunas diferentes é uma
                    # divergência à espera de acontecer. Vazio sem porta.
                    "door_opened": r.get("door_opened"),
                })
            sr = df.success.mean() * 100
            print(f"  [OK] {algo.upper():3s}/{sc:22s} sucesso={sr:5.1f}%  "
                  f"recolhas/ep={df.food_collected.mean():.2f}")

        if comp:
            pd.DataFrame(comp).T.to_csv(os.path.join(EVAL_DIR, f"eval_comparacao_{sc}.csv"))

    summary = pd.DataFrame(long_rows)
    if not summary.empty:
        summary.to_csv(os.path.join(EVAL_DIR, "eval_summary.csv"), index=False)
        print(f"[EVAL-SUITE] Resumo guardado: {os.path.join(EVAL_DIR, 'eval_summary.csv')}")
    else:
        print("[EVAL-SUITE] Nenhum modelo avaliado (treina primeiro).")
    return summary


def _ordered_present(summary, key, ordering, labelmap=None):
    present = list(summary[key].unique())
    out = [x for x in ordering if x in present]
    if labelmap:
        return [labelmap.get(x, x) for x in out]
    return out


def plot_evaluation(summary=None, out_dir=None):
    """Gera os gráficos de TAREFA por cenário (taxa de sucesso + recolhas/ep).
    Lê eval_summary.csv se `summary` não for dado. Devolve a lista de PNGs criados."""
    import matplotlib
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.pyplot as plt
    import seaborn as sns

    if summary is None:
        path = os.path.join(EVAL_DIR, "eval_summary.csv")
        if not os.path.exists(path):
            print("[EVAL-SUITE] Sem eval_summary.csv — corre a avaliação primeiro.")
            return []
        summary = pd.read_csv(path)
    if summary.empty:
        return []

    if out_dir is None:
        out_dir = EVAL_DIR
    os.makedirs(out_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    scen_order = _ordered_present(summary, "Scenario", ALL_SCENARIOS, SCENARIO_LABELS)
    algo_order = [a for a in ["GNN", "PPO", "SAC"] if a in summary["Algorithm"].unique()]
    palette = {a: ALGO_COLORS[a] for a in algo_order}
    created = []

    # ── 1. Taxa de sucesso (Ptask) por cenário ───────────────────────────────
    succ = (summary.groupby(["ScenarioLabel", "Algorithm"])["success"]
            .mean().mul(100).reset_index(name="SuccessRate"))
    # 8,5x5 polegadas (era 13x7): a figura entra na tese a 0,98 da largura do
    # texto, o que reduz tudo para ~0,73 — com 13x7 a redução era 0,50 e os
    # rótulos dos cenários chegavam ao papel com 5 pt.
    fig, ax = plt.subplots(figsize=(8.5, 5))
    sns.barplot(data=succ, x="ScenarioLabel", y="SuccessRate", hue="Algorithm",
                order=scen_order, hue_order=algo_order, palette=palette, ax=ax)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.0f%%", fontsize=8.5, padding=2)
    ax.set_title("Taxa de Sucesso por Cenário (Ptask) — avaliação determinística",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Episódios com sucesso (%)", fontsize=12)
    ax.set_xlabel("Cenário", fontsize=12)
    ax.tick_params(labelsize=10.5)
    ax.set_ylim(0, 105)
    # Legenda FORA dos eixos: dentro tapava as barras (todas chegam aos 100%).
    ax.legend(title="Algoritmo", loc="upper left", bbox_to_anchor=(1.01, 1.0),
              borderaxespad=0)
    plt.xticks(rotation=20, ha="right", fontsize=10.5)
    fig.text(0.5, 0.005, "Sucesso = pelo menos 1 recolha no episódio. Métrica de tarefa, "
             "comparável entre algoritmos (ao contrário do reward de treino).",
             ha="center", fontsize=8.5, color="#555555", style="italic")
    plt.tight_layout(rect=[0, 0.04, 0.88, 1])
    p1 = os.path.join(out_dir, "taxa_sucesso_por_cenario.png")
    fig.savefig(p1, dpi=300, bbox_inches="tight")
    plt.close(fig)
    created.append(p1)
    print(f"[OK] Gráfico de taxa de sucesso: {p1}")

    # ── 2. Recolhas/ep por cenário (média ± desvio) ──────────────────────────
    fig, ax = plt.subplots(figsize=(8.5, 5))
    sns.barplot(data=summary, x="ScenarioLabel", y="food_collected", hue="Algorithm",
                order=scen_order, hue_order=algo_order, palette=palette,
                errorbar="sd", ax=ax)
    ax.set_title("Recolhas por Episódio por Cenário — avaliação determinística",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Recolhas por episódio (média ± desvio)", fontsize=12)
    ax.set_xlabel("Cenário", fontsize=12)
    ax.tick_params(labelsize=10.5)
    ax.set_ylim(bottom=0)  # recolhas nunca são negativas — corta os bigodes de sd abaixo de 0
    ax.legend(title="Algoritmo", loc="upper right")
    plt.xticks(rotation=20, ha="right", fontsize=10.5)
    fig.text(0.5, 0.005, "Média de recolhas (food_collected) por episódio; barras de erro = "
             "desvio padrão entre episódios. Mede magnitude do desempenho, não só sucesso/falha.",
             ha="center", fontsize=8.5, color="#555555", style="italic")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    p2 = os.path.join(out_dir, "recolhas_por_cenario.png")
    fig.savefig(p2, dpi=300, bbox_inches="tight")
    plt.close(fig)
    created.append(p2)
    print(f"[OK] Gráfico de recolhas/ep: {p2}")

    return created


def main():
    parser = argparse.ArgumentParser(description="Avaliação de todos os cenários + gráficos de tarefa")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--scenarios", nargs="*", default=None,
                        help="Subconjunto de cenários (default: todos os 6)")
    parser.add_argument("--algos", nargs="*", default=None,
                        help="Subconjunto de algoritmos (default: gnn ppo sac)")
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--no-plots", action="store_true", help="Só avaliar, sem gráficos")
    args = parser.parse_args()

    summary = evaluate_all(episodes=args.episodes, scenarios=args.scenarios,
                           algos=args.algos, seed_base=args.seed_base)
    if not args.no_plots and not summary.empty:
        plot_evaluation(summary, out_dir=EVAL_DIR)


if __name__ == "__main__":
    main()
