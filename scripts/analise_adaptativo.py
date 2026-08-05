"""Análise pré-registada da campanha de Novelty ADAPTATIVO (QI6).

Executa T1-T4 do docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md, exatamente como congelado
a 15-16 jul (antes do unblinding):
  - unidade estatística = MÉDIA POR RUN (n=7), nunca o episódio;
  - Mann-Whitney U exato + delta de Cliff;
  - taxa de convergência (runs a 100%) reportada como DESCRITIVO, nunca como teste;
  - todos os cenários, todos os runs — sem cherry-picking.

Braços:
  adaptativo @195  = results/novelty_adaptativo/week_{A,B}_fase1/evaluation/eval_by_run.csv
  objetivo 7d @195 = results/graficos_tese/final_7d/eval_by_run_7d.csv (GNN)
  fixo w=0.5 @195  = results/novelty_final/{uwall,bypass}/results/evaluation/eval_by_run.csv
  exploratório @390: A_fase2 (u_wall OBJETIVO), B_fase2 (u_wall adapt.), B_fase3 (bypass adapt.)
"""
import os
import sys

import pandas as pd
from scipy.stats import mannwhitneyu

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ADAPT = os.path.join(BASE, 'results', 'novelty_adaptativo')
FINAL7D = os.path.join(BASE, 'results', 'graficos_tese', 'final_7d', 'eval_by_run_7d.csv')
FIXO = {
    'u_wall': os.path.join(BASE, 'results', 'novelty_final', 'uwall', 'results', 'evaluation', 'eval_by_run.csv'),
    'cooperative_door_bypass': os.path.join(BASE, 'results', 'novelty_final', 'bypass', 'results', 'evaluation', 'eval_by_run.csv'),
}

T1_CENARIOS = ['none', 'bottleneck', 'four_rooms', 'cooperative_door', 'cooperative_perception']


def por_run(df):
    """Médias por run: food e sucesso; runs a 100% como descritivo."""
    g = df.groupby('Run').agg(food=('food_collected', 'mean'), suc=('success', 'mean'))
    return g.sort_index()


def cliffs_delta(a, b):
    n = 0
    for x in a:
        for y in b:
            # `int(...)`: com escalares NumPy, `np.bool_ - np.bool_` e um
            # TypeError desde o NumPy 2. So nao rebenta aqui porque cada
            # chamador embrulha os dados em `list()` — e isso e uma
            # convencao, nao uma garantia. O valor devolvido e o mesmo.
            n += int(x > y) - int(x < y)
    return n / (len(a) * len(b))


def compara(nome, a, b, alternative='two-sided'):
    """a, b = Series de médias por run. Reporta MW exato + delta + descritivos."""
    U, p = mannwhitneyu(a, b, alternative=alternative, method='exact')
    d = cliffs_delta(list(a), list(b))
    print(f"  {nome}")
    print(f"    A: {a.mean():6.1f} ± {a.std():5.1f}  runs: {[round(x,1) for x in a]}")
    print(f"    B: {b.mean():6.1f} ± {b.std():5.1f}  runs: {[round(x,1) for x in b]}")
    print(f"    Mann-Whitney ({alternative}): p = {p:.4f} | delta de Cliff = {d:+.2f}")
    return p, d


def main():
    # --- carregar os braços ---
    adapt = pd.concat([
        pd.read_csv(os.path.join(ADAPT, 'week_A_fase1', 'evaluation', 'eval_by_run.csv')),
        pd.read_csv(os.path.join(ADAPT, 'week_B_fase1', 'evaluation', 'eval_by_run.csv')),
    ], ignore_index=True)
    obj7d = pd.read_csv(FINAL7D)
    obj7d = obj7d[obj7d.Algorithm == 'GNN']

    print('=' * 74)
    print('CAMPANHA NOVELTY ADAPTATIVO — análise pré-registada (T1-T4)')
    print('=' * 74)

    print('\n--- Descritivo: adaptativo @195, todos os cenários, todos os runs ---')
    resumo = {}
    for cen in sorted(adapt.Scenario.unique()):
        r = por_run(adapt[adapt.Scenario == cen])
        cem = int((r.suc == 1.0).sum())
        resumo[cen] = (r.food, cem)
        print(f"  {cen:24s} {r.food.mean():6.1f} ± {r.food.std():5.1f}  [{cem}/7 runs a 100%]  "
              f"runs: {[round(x,1) for x in r.food]}")

    # --- T1: não-degradação nos 5 fáceis (bilateral) ---
    print('\n--- T1 — Não-degradação (adaptativo vs objetivo 7d; bilateral) ---')
    t1_falhas = []
    for cen in T1_CENARIOS:
        a = resumo[cen][0]
        b = por_run(obj7d[obj7d.Scenario == cen]).food
        p, d = compara(f"[{cen}] adaptativo (A) vs objetivo 7d (B)", a, b)
        if p < 0.05 and d < 0:
            t1_falhas.append(cen)
    print(f"  => T1: {'FALHA em ' + ', '.join(t1_falhas) if t1_falhas else 'PASSA (sem degradação significativa)'}")

    # --- T2: ganho no Muro em U (unilateral adaptativo > objetivo) ---
    print('\n--- T2 — Ganho no Muro em U (unilateral: adaptativo > objetivo 7d) ---')
    a = resumo['u_wall'][0]
    b = por_run(obj7d[obj7d.Scenario == 'u_wall']).food
    p2, d2 = compara('[u_wall] adaptativo (A) vs objetivo 7d (B)', a, b, alternative='greater')
    conv_a = resumo['u_wall'][1]
    print(f"    Convergência (descritivo): adaptativo {conv_a}/7 vs objetivo 3/7 vs fixo 7/7")
    t2_passa = (p2 < 0.05) or (conv_a >= 7)
    print(f"  => T2: {'PASSA' if t2_passa else 'FALHA'} (magnitude p={p2:.4f}; convergência {conv_a}/7)")

    # --- T3: sem custo no bypass (bilateral; esperar delta ~ 0) ---
    print('\n--- T3 — Sem custo no bypass (adaptativo vs objetivo 7d; bilateral) ---')
    a = resumo['cooperative_door_bypass'][0]
    b = por_run(obj7d[obj7d.Scenario == 'cooperative_door_bypass']).food
    p3, d3 = compara('[bypass] adaptativo (A) vs objetivo 7d (B)', a, b)
    t3_passa = not (p3 < 0.05 and d3 < 0)
    print(f"  => T3: {'PASSA (sem custo significativo)' if t3_passa else 'FALHA (o adaptativo paga custo no bypass)'}")

    # --- T4: adaptativo vs fixo w=0.5 (u_wall e bypass) ---
    print('\n--- T4 — Adaptativo vs Novelty FIXO w=0.5 (bilateral) ---')
    for cen in ['u_wall', 'cooperative_door_bypass']:
        fixo = por_run(pd.read_csv(FIXO[cen])).food
        compara(f"[{cen}] adaptativo (A) vs fixo w=0.5 (B)", resumo[cen][0], fixo)

    # --- Regra de decisão pré-comprometida ---
    print('\n' + '=' * 74)
    print('REGRA DE DECISÃO (pré-comprometida a 15 jul):')
    if t1_falhas:
        print('  => CONTRAINDICAÇÃO HONESTA: o adaptativo degrada cenários fáceis '
              f'({", ".join(t1_falhas)}). Não recomendar; reportar na mesma.')
    elif t2_passa and t3_passa:
        print('  => SOBE A RESULTADO: T1 sem degradação + T2 ganho no u_wall + T3 sem custo '
              'no bypass. Reescrever QI6 + Trabalhos Futuros.')
    else:
        print('  => RESULTADO NULO LIMPO: adaptativo "seguro mas não benéfico". QI6 não muda; '
              'acrescentar uma linha em sec:res_novelty.')
    print('=' * 74)

    # --- Exploratório @390 (não entra na decisão) ---
    print('\n--- EXPLORATÓRIO (rotulado como tal; fora da regra de decisão) ---')
    braços = [
        ('u_wall OBJETIVO @390 (A_fase2)', 'week_A_fase2', 'u_wall'),
        ('u_wall ADAPTATIVO @390 (B_fase2)', 'week_B_fase2', 'u_wall'),
        ('bypass ADAPTATIVO @390 (B_fase3)', 'week_B_fase3', 'cooperative_door_bypass'),
    ]
    for nome, pasta, cen in braços:
        df = pd.read_csv(os.path.join(ADAPT, pasta, 'evaluation', 'eval_by_run.csv'))
        r = por_run(df[df.Scenario == cen])
        cem = int((r.suc == 1.0).sum())
        print(f"  {nome:34s} {r.food.mean():6.1f} ± {r.food.std():5.1f}  [{cem}/7 a 100%]  "
              f"runs: {[round(x,1) for x in r.food]}")


if __name__ == '__main__':
    main()
