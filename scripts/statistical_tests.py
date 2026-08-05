"""
statistical_tests.py — Testes de significância entre algoritmos
================================================================
Compara os 3 algoritmos (GNN, PPO, SAC) par-a-par, por cenário, usando os
resultados de AVALIAÇÃO determinística (results/evaluation/eval_{algo}_{cenario}.csv).

Porque a avaliação? Os logs de treino (all_best_scores.csv) misturam escalas
incompatíveis — o GNN reporta fitness evolutiva e o PPO/SAC recompensa episódica.
A avaliação, pelo contrário, mede a MESMA métrica de tarefa para todos
(food_collected / taxa de sucesso), tornando a comparação cientificamente válida.

⚠️ A UNIDADE AQUI É O EPISÓDIO — E A DA TESE NÃO É
---------------------------------------------------
Este script compara **episódios** (20 por célula). A tese compara **execuções de
treino**: «a unidade estatística é a execução de treino --- e não o episódio ---,
o que evita a inflação de n que é comum na literatura comparada» (Contributos).
Vinte episódios do mesmo modelo não são vinte observações independentes: são vinte
amostras do mesmo treino, e tratá-las como tal multiplica o n por 20 e faz
significâncias aparecer do nada.

A tabela da tese (`tab:res_signif`) vem do `gerar_figuras_7d.py`, que agrega por
run antes de testar. **Este ficheiro não alimenta a tese** — serve para inspeção
rápida de uma avaliação isolada.

Por isso escreve em `testes_significancia_por_episodio_*.csv`, e não no nome
canónico: escrevia no MESMO ficheiro que a tese e o dashboard leem, e a única
coisa que separava as duas metodologias era a ordem por que se corriam os scripts
(o `gerar_figuras_7d.py --install-oficial` vinha a seguir e reescrevia por cima).
O backup `testes_significancia_food_collected_pre7d.csv` guarda 42 comparações
com `wilcoxon` — prova de que a sobrescrita chegou a acontecer.

Testes: Wilcoxon signed-rank quando as amostras têm o mesmo tamanho (tratadas
como emparelhadas), Mann-Whitney U caso contrário; t de Welch como complementar;
efeito por δ de Cliff. ⚠️ O emparelhamento por igualdade de tamanho é uma
heurística frágil — dois algoritmos com 20 episódios cada não têm pares naturais
a não ser que as seeds de avaliação coincidam. Ver `docs/PLANO_QUALIDADE.md`.

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
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")
OUT_DIR = os.path.join(PROJECT_ROOT, "results", "estatisticas")

from src.scenarios import SCENARIOS as SCENARIO_ORDER, SCENARIO_LABELS_SHORT as SCENARIO_LABELS
ALGOS = ["GNN", "PPO", "SAC"]

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


def cliffs_delta(a, b):
    """Tamanho de efeito não-paramétrico (Cliff's delta), em [-1, 1].
    Positivo => 'a' tende a ser maior que 'b'. Válido pareado ou não."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a) * len(b)
    if n == 0:
        return float("nan")
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return float(gt - lt) / n


def compare_pair(a, b):
    """Compara duas amostras. Usa Wilcoxon signed-rank (PAREADO) quando têm o
    mesmo tamanho --- caso da avaliação emparelhada (mesmos episódios/seeds) ---,
    mais poderoso com n pequeno; caso contrário, Mann-Whitney U (não-pareado).
    Devolve dict com estatísticas, ou None se inviável."""
    if len(a) < 2 or len(b) < 2:
        return None
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    mean_a, mean_b = float(np.mean(a)), float(np.mean(b))

    paired = (len(a) == len(b))
    if paired:
        test = "wilcoxon"
        diffs = a - b
        if np.all(diffs == 0):           # sem diferenças => nada a testar
            stat, p = float("nan"), 1.0
        else:
            try:
                stat, p = stats.wilcoxon(a, b)
            except ValueError:
                stat, p = float("nan"), 1.0
    else:
        test = "mannwhitney"
        if np.ptp(a) == 0 and np.ptp(b) == 0 and mean_a == mean_b:
            stat, p = float("nan"), 1.0
        else:
            stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")

    # t de Welch (complementar; pode dar nan se variância total nula)
    try:
        t_stat, p_t = stats.ttest_ind(a, b, equal_var=False)
        if np.isnan(p_t):
            p_t = 1.0
    except Exception:
        t_stat, p_t = float("nan"), 1.0

    return {
        "mean_a": mean_a, "mean_b": mean_b,
        "test": test, "stat": float(stat), "p_value": float(p),
        "t": float(t_stat), "p_welch": float(p_t),
        "effect_cliffs_delta": cliffs_delta(a, b),
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
    print(f"  Wilcoxon signed-rank (PAREADO, n iguais) ou Mann-Whitney U (nao-pareado)")
    print(f"  + t de Welch (complementar) | efeito: Cliff's delta")
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

                sig = res["p_value"] < args.alpha
                if res["mean_a"] == res["mean_b"]:
                    winner = "empate"
                else:
                    winner = a_name if res["mean_a"] > res["mean_b"] else b_name
                mark = "***" if sig else "ns "
                print(f"    {a_name} vs {b_name} [{res['test']}]: "
                      f"medias {res['mean_a']:.2f} / {res['mean_b']:.2f}  |  "
                      f"p={res['p_value']:.4f} [{mark}]  delta={res['effect_cliffs_delta']:+.2f}  |  "
                      f"melhor: {winner if sig else '(sem dif. significativa)'}")

                rows.append({
                    "Scenario": scenario, "Label": label,
                    "A": a_name, "B": b_name,
                    "mean_A": round(res["mean_a"], 3), "mean_B": round(res["mean_b"], 3),
                    "test": res["test"],
                    "statistic": round(res["stat"], 2),
                    "p_value": round(res["p_value"], 5),
                    "p_welch": round(res["p_welch"], 5),
                    "cliffs_delta": round(res["effect_cliffs_delta"], 3),
                    "significant": sig,
                    "winner": winner if sig else "ns",
                })

    if not rows:
        print("\n[!] Nenhuma comparacao possivel (precisas de >=2 algoritmos por cenario).")
        sys.exit(1)

    df_out = pd.DataFrame(rows)
    # Nome PRÓPRIO: o canónico (`testes_significancia_{metric}.csv`) é escrito
    # pelo `gerar_figuras_7d.py` com a unidade certa (médias por run) e é o que a
    # tese e o dashboard leem. Ver o cabeçalho deste ficheiro.
    csv_path = os.path.join(OUT_DIR,
                            f"testes_significancia_por_episodio_{args.metric}.csv")
    df_out.to_csv(csv_path, index=False)
    canonico = os.path.join(OUT_DIR, f"testes_significancia_{args.metric}.csv")
    print(f"\n[!] AVISO: a unidade destes testes é o EPISÓDIO, não a execução de")
    print(f"    treino. A tese usa médias por run — estes números NÃO são os dela.")
    print(f"    Escrito em: {os.path.relpath(csv_path, PROJECT_ROOT)}")
    if os.path.exists(canonico):
        print(f"    (o ficheiro da tese, {os.path.basename(canonico)}, fica intacto)")

    # Tabela LaTeX pronta a colar na tese (booktabs-friendly, sem dependências extra).
    tex_path = os.path.join(OUT_DIR,
                            f"testes_significancia_por_episodio_{args.metric}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Gerado por scripts/statistical_tests.py — unidade: EPISÓDIO.\n"
                "% NÃO é a tabela da tese: essa agrega por execução de treino e é\n"
                "% gerada pelo gerar_figuras_7d.py. Ver o cabeçalho do script.\n")
        f.write("\\begin{tabular}{llrrrl}\n\\hline\n")
        f.write("Cenário & Par & média A & média B & $p$ & Significativo \\\\\n\\hline\n")
        for r in rows:
            star = "Sim" if r["significant"] else "não"
            f.write(f"{r['Label']} & {r['A']} vs {r['B']} & {r['mean_A']:.2f} & "
                    f"{r['mean_B']:.2f} & {r['p_value']:.4f} & {star} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")

    print(f"\n{'='*78}")
    print(f"  [OK] Tabela CSV  : {csv_path}")
    print(f"  [OK] Tabela LaTeX: {tex_path}")
    print(f"  Legenda: *** p<{args.alpha} (diferença significativa) | ns = não significativa")
    print(f"{'='*78}\n")


if __name__ == "__main__":
    main()
