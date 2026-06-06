"""
statistical_tests.py — Testes de significância entre algoritmos
================================================================
Compara os 3 algoritmos (GNN, PPO, SAC) par-a-par, por cenário, usando os
resultados de AVALIAÇÃO determinística (results/evaluation/eval_{algo}_{cenario}.csv).

Porque a avaliação? Os logs de treino (all_best_scores.csv) misturam escalas
incompatíveis — o GNN reporta fitness evolutiva e o PPO/SAC recompensa episódica.
A avaliação, pelo contrário, mede a MESMA métrica de tarefa para todos
(food_collected / taxa de sucesso), tornando a comparação cientificamente válida.

Teste principal: Mann-Whitney U (não-paramétrico) — apropriado para amostras
pequenas e distribuições não-normais (nº de recolhas é discreto e enviesado).
Teste complementar: t de Welch (paramétrico, variâncias desiguais).
Tamanho de efeito: rank-biserial (derivado do U), interpretável independentemente de n.

Pré-requisito: correr a avaliação primeiro, idealmente com >=30 episódios:
    python scripts/eval_all.py --episodes 30 --scenario none
    python scripts/eval_all.py --episodes 30 --scenario u_wall
    ... (um por cenário)

Uso:
    python scripts/statistical_tests.py --metric food_collected
    python scripts/statistical_tests.py --metric success --alpha 0.05
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")
OUT_DIR = os.path.join(PROJECT_ROOT, "results", "estatisticas")

ALGOS = ["GNN", "PPO", "SAC"]
SCENARIO_ORDER = ["none", "u_wall", "bottleneck", "four_rooms",
                  "cooperative_door", "cooperative_perception"]
SCENARIO_LABELS = {
    "none": "Sandbox", "u_wall": "Beco Sem Saida (U)", "bottleneck": "Gargalo",
    "four_rooms": "Quatro Salas", "cooperative_door": "Porta Cooperativa",
    "cooperative_perception": "Percepcao Cooperativa",
}

# eval_{algo}_{scenario}.csv  (algo em minusculas; scenario pode ter underscores)
_FNAME_RE = re.compile(r"^eval_(gnn|ppo|sac)_(.+)\.csv$")


def load_evaluations(metric):
    """Devolve {scenario: {ALGO: np.array(valores da métrica por episódio)}}."""
    data = {}
    for path in sorted(glob.glob(os.path.join(EVAL_DIR, "eval_*.csv"))):
        fname = os.path.basename(path)
        m = _FNAME_RE.match(fname)
        if not m:
            continue  # ignora eval_comparacao_*.csv e outros
        algo, scenario = m.group(1).upper(), m.group(2)
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"[!] Falha a ler {fname}: {e}")
            continue
        if metric not in df.columns:
            print(f"[!] {fname} nao tem a coluna '{metric}' — saltado")
            continue
        vals = df[metric].astype(float).to_numpy()
        data.setdefault(scenario, {})[algo] = vals
    return data


def rank_biserial(a, b, u_stat):
    """Tamanho de efeito a partir do U de Mann-Whitney: r = 1 - 2U/(n1*n2).
    Sinal positivo => 'a' tende a ser maior que 'b'."""
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float("nan")
    return 1.0 - (2.0 * u_stat) / (n1 * n2)


def compare_pair(a, b):
    """Compara duas amostras. Devolve dict com estatísticas, ou None se inviável."""
    if len(a) < 2 or len(b) < 2:
        return None
    mean_a, mean_b = float(np.mean(a)), float(np.mean(b))
    # Se ambas as amostras forem constantes e iguais, não há nada a testar.
    degenerate = np.ptp(a) == 0 and np.ptp(b) == 0 and mean_a == mean_b

    if degenerate:
        u_stat, p_mw = float("nan"), 1.0
    else:
        u_stat, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")

    # t de Welch (pode dar nan se variância total nula)
    try:
        t_stat, p_t = stats.ttest_ind(a, b, equal_var=False)
        if np.isnan(p_t):
            p_t = 1.0
    except Exception:
        t_stat, p_t = float("nan"), 1.0

    return {
        "mean_a": mean_a, "mean_b": mean_b,
        "U": float(u_stat), "p_mannwhitney": float(p_mw),
        "t": float(t_stat), "p_welch": float(p_t),
        "effect_rank_biserial": rank_biserial(a, b, u_stat),
    }


def main():
    parser = argparse.ArgumentParser(description="Testes de significancia entre algoritmos")
    parser.add_argument("--metric", default="food_collected",
                        choices=["food_collected", "task_reward", "total_reward", "success"],
                        help="Metrica comparavel a testar (default: food_collected)")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="Nivel de significancia (default: 0.05)")
    args = parser.parse_args()

    data = load_evaluations(args.metric)
    if not data:
        print(f"\n[!] Sem dados de avaliacao em {EVAL_DIR}.")
        print("[!] Corre primeiro:  python scripts/eval_all.py --episodes 30 --scenario <cenario>")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []

    scenarios = [s for s in SCENARIO_ORDER if s in data] + \
                [s for s in data if s not in SCENARIO_ORDER]

    print(f"\n{'='*78}")
    print(f"  TESTES DE SIGNIFICANCIA  |  metrica: {args.metric}  |  alpha = {args.alpha}")
    print(f"  Teste: Mann-Whitney U (bilateral)  +  t de Welch (complementar)")
    print(f"{'='*78}")

    for scenario in scenarios:
        algos_present = [a for a in ALGOS if a in data[scenario]]
        label = SCENARIO_LABELS.get(scenario, scenario)
        n_eps = {a: len(data[scenario][a]) for a in algos_present}
        print(f"\n--- {label}  (episodios: "
              f"{', '.join(f'{a}={n_eps[a]}' for a in algos_present)}) ---")

        if len(algos_present) < 2:
            print("    (menos de 2 algoritmos avaliados — sem comparacao)")
            continue

        for i in range(len(algos_present)):
            for j in range(i + 1, len(algos_present)):
                a_name, b_name = algos_present[i], algos_present[j]
                res = compare_pair(data[scenario][a_name], data[scenario][b_name])
                if res is None:
                    print(f"    {a_name} vs {b_name}: amostras insuficientes")
                    continue

                sig = res["p_mannwhitney"] < args.alpha
                if res["mean_a"] == res["mean_b"]:
                    winner = "empate"
                else:
                    winner = a_name if res["mean_a"] > res["mean_b"] else b_name
                mark = "***" if sig else "ns "
                print(f"    {a_name} vs {b_name}: "
                      f"medias {res['mean_a']:.2f} / {res['mean_b']:.2f}  |  "
                      f"U={res['U']:.1f}  p={res['p_mannwhitney']:.4f} [{mark}]  |  "
                      f"melhor: {winner if sig else '(sem dif. significativa)'}")

                rows.append({
                    "Scenario": scenario, "Label": label,
                    "A": a_name, "B": b_name,
                    "mean_A": round(res["mean_a"], 3), "mean_B": round(res["mean_b"], 3),
                    "U": round(res["U"], 2),
                    "p_mannwhitney": round(res["p_mannwhitney"], 5),
                    "p_welch": round(res["p_welch"], 5),
                    "effect_rank_biserial": round(res["effect_rank_biserial"], 3),
                    "significant": sig,
                    "winner": winner if sig else "ns",
                })

    if not rows:
        print("\n[!] Nenhuma comparacao possivel (precisas de >=2 algoritmos por cenario).")
        sys.exit(1)

    df_out = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_DIR, f"testes_significancia_{args.metric}.csv")
    df_out.to_csv(csv_path, index=False)

    # Tabela LaTeX pronta a colar na tese (booktabs-friendly, sem dependências extra).
    tex_path = os.path.join(OUT_DIR, f"testes_significancia_{args.metric}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Gerado por scripts/statistical_tests.py\n")
        f.write("\\begin{tabular}{llrrrl}\n\\hline\n")
        f.write("Cenário & Par & média A & média B & $p$ (MW) & Significativo \\\\\n\\hline\n")
        for r in rows:
            star = "Sim" if r["significant"] else "não"
            f.write(f"{r['Label']} & {r['A']} vs {r['B']} & {r['mean_A']:.2f} & "
                    f"{r['mean_B']:.2f} & {r['p_mannwhitney']:.4f} & {star} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")

    print(f"\n{'='*78}")
    print(f"  [OK] Tabela CSV  : {csv_path}")
    print(f"  [OK] Tabela LaTeX: {tex_path}")
    print(f"  Legenda: *** p<{args.alpha} (diferença significativa) | ns = não significativa")
    print(f"{'='*78}\n")


if __name__ == "__main__":
    main()
