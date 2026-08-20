"""
gerar_figuras_7d.py — Figuras definitivas da campanha de 7 dias (tese, Cap. 6)
==============================================================================
A campanha de 7 dias correu em DUAS instalações separadas do servidor:
  - GNN  (7 runs × 7 cenários): ~/swarm-robotics-tese  → estatisticas_7d_gnn/ + eval_7d/evaluation_gnn/
  - PPO+SAC (7 runs × 7 cenários): ~/run7d_mlp          → estatisticas_7d_mlp/ + eval_7d/evaluation_mlp/

Os gráficos gerados DENTRO de cada campanha misturam modelos antigos da outra
família (o all_best_scores.csv do servidor acumulava runs de campanhas
anteriores), pelo que NÃO servem para a tese. Este script funde as duas fontes
— GNN da campanha GNN, PPO/SAC da campanha MLP — e regenera as figuras com o
estilo canónico de plot_results.py / eval_suite.py.

Também produz o eval por run fundido (eval_by_run_7d.csv), o resumo por
cenário e os testes de significância entre algoritmos (Mann-Whitney U +
delta de Cliff sobre as MÉDIAS POR RUN, n=7 por grupo — a unidade
estatística independente é o run, não o episódio).

Uso:  .venv/Scripts/python.exe scripts/gerar_figuras_7d.py
Saída: results/graficos_tese/final_7d/
"""
import os
import sys
import itertools

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import seaborn as sns

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import (SCENARIOS, THESIS_SCENARIOS, SCENARIO_LABELS,
                           SCENARIO_LABELS_SHORT, ALGO_COLORS)
from scripts.curvas_agregadas import curva_media_entre_runs, desenhar_curva_media

GT = os.path.join(PROJECT_ROOT, 'results', 'graficos_tese')
SRC_GNN_STATS = os.path.join(GT, 'estatisticas_7d_gnn')
SRC_MLP_STATS = os.path.join(GT, 'estatisticas_7d_mlp')
SRC_GNN_EVAL = os.path.join(GT, 'eval_7d', 'evaluation_gnn', 'eval_by_run.csv')
SRC_MLP_EVAL = os.path.join(GT, 'eval_7d', 'evaluation_mlp', 'eval_by_run.csv')
OUT = os.path.join(GT, 'final_7d')

ALGOS = ['GNN', 'PPO', 'SAC']
YLABEL_TREINO = {
    'GNN': 'Fitness Evolutiva (melhor genoma)',
    'PPO': 'Recompensa Episódica',
    'SAC': 'Recompensa Episódica',
}


def _merge(fname_gnn, fname_mlp, keep_gnn, keep_mlp):
    """Funde um CSV das duas campanhas, filtrando cada fonte pelos seus algoritmos."""
    df_g = pd.read_csv(fname_gnn)
    df_m = pd.read_csv(fname_mlp)
    df_g = df_g[df_g['Algorithm'].isin(keep_gnn)]
    df_m = df_m[df_m['Algorithm'].isin(keep_mlp)]
    return pd.concat([df_g, df_m], ignore_index=True)


def cliffs_delta(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a) * len(b)
    if n == 0:
        return float('nan')
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return float(gt - lt) / n


def dotplot_por_run(d, titulo, caminho, *, col_valor="recolhas", col_algo="Algorithm",
                    col_sucesso="sucesso", unidade="execução independente",
                    nota_extra="", n_por_algo=None, ordem=None, cores=None,
                    largura=9.0):
    """Um ponto por RUN, em vez de uma caixa. Guarda o PNG em `caminho`.

    PORQUÊ (e porque é que não é só estética): com n=7, os quartis de um boxplot
    são ruído — e a caixa CHEIA sugere densidade onde não há nenhuma. No Muro em
    U, o GNN tem 4 runs a ZERO e 3 entre 43 e 80: a caixa pinta os 0-46 como se
    estivessem ocupados, quando ali não está um único run. O capítulo gasta um
    parágrafo a explicar que o comportamento é BIMODAL e a figura ao lado
    esconde-o. Sete pontos mostram-no de imediato.

    Escolhas de desenho:
    · faixa HORIZONTAL por algoritmo — o nome fica no eixo, logo a identidade da
      série não depende da cor (nem do daltonismo de quem lê);
    · a MÉDIA (que é o que a tese reporta, ±dp) é uma barra vertical; a mediana
      não entra, porque em distribuição bimodal não descreve run nenhum;
    · anel branco à volta de cada ponto — dois runs com o mesmo valor têm de se
      ler como dois;
    · a contagem de runs que resolvem (sucesso=100%) fica escrita à direita: é o
      "3/7" que o texto cita, aqui visível em vez de calculado pelo leitor.

    `ordem`/`cores` servem as figuras cujas séries não são os três algoritmos —
    o mega-treino compara quatro BRAÇOS no mesmo cenário (GNN adaptativo, GNN
    objetivo, PPO, SAC). Sem elas, `ALGOS` filtrava os braços todos e a figura
    saía vazia. Por omissão, nada muda para quem já chamava a função.
    """
    import textwrap

    # A ordem lê-se de cima para baixo (o eixo y do matplotlib cresce ao
    # contrário, daí a inversão): GNN em cima, como em todas as tabelas.
    ordem = ordem if ordem is not None else ALGOS
    cores = cores if cores is not None else ALGO_COLORS
    algos_presentes = [a for a in ordem if a in set(d[col_algo])]
    # `largura` em polegadas. Quem entra na tese a meia largura de página (os
    # dotplots por cenário, dois por linha) pede uma figura ESTREITA: desenhada
    # a 9 polegadas e reduzida para 7,8 cm, o eixo chegava ao papel com 3,4 pt.
    # As fontes acompanham a largura (`esc`), para que a figura estreita não
    # fique com letra proporcionalmente minúscula.
    esc = min(1.15, 9.0 / largura)
    altura = (1.35 * len(algos_presentes) + 2.4) * (largura / 9.0) * 1.15
    fig, ax = plt.subplots(figsize=(largura, altura))
    rng = np.random.default_rng(7)          # jitter reprodutível

    x_max = float(d[col_valor].max()) if len(d) else 1.0
    for i, algo in enumerate(algos_presentes):
        sub = d[d[col_algo] == algo]
        vals = sub[col_valor].to_numpy(dtype=float)
        y = i + rng.uniform(-0.16, 0.16, size=len(vals))
        ax.scatter(vals, y, s=95, color=cores.get(algo, "#666"),
                   edgecolors="white", linewidths=1.6, zorder=3,
                   alpha=.95, clip_on=False)
        m = float(np.mean(vals)) if len(vals) else 0.0
        ax.vlines(m, i - 0.30, i + 0.30, color="#222222", linewidth=2.4, zorder=4)
        # O rótulo da média encosta-se ao lado que tiver espaço: com média 0 (um
        # algoritmo que nunca resolve) ficava metade fora da figura.
        perto_da_esquerda = m < 0.12 * max(x_max, 1e-9)
        ax.text(m, i + 0.40, f"média {m:.1f}",
                ha="left" if perto_da_esquerda else "center", va="bottom",
                fontsize=9 * esc, color="#222222", fontweight="bold")
        if col_sucesso in sub.columns:
            n_ok = int((sub[col_sucesso] >= 1.0).sum())
            ax.text(1.02, i, f"{n_ok}/{len(sub)} a 100%",
                    transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=9.5 * esc, color="#444444")

    ax.set_yticks(range(len(algos_presentes)))
    ax.set_yticklabels(algos_presentes, fontsize=12 * esc, fontweight="bold")
    ax.set_ylim(len(algos_presentes) - 0.45, -0.55)      # GNN no topo
    # Folga à esquerda do zero: os runs que NÃO resolvem valem 0 exato e, com
    # `clip_on=False`, empilham-se por cima do rótulo do eixo. A n=7 passava
    # despercebido; a n=28 são catorze pontos e o "PPO" deixa de se ler.
    ax.set_xlim(left=-0.035 * max(x_max, 1e-9))
    # Numa figura estreita, o rótulo longo do eixo e o título de uma linha
    # saem pelas bordas: encurta-se um e quebra-se o outro.
    estreita = largura < 7.0
    ax.set_xlabel("Recolhas/ep (média da execução, 20 ep)" if estreita
                  else "Recolhas por episódio (média da execução, 20 episódios)",
                  fontsize=10 * esc)
    ax.tick_params(axis="x", labelsize=10 * esc)
    titulo_desenhado = "\n".join(textwrap.wrap(titulo, 34)) if estreita else titulo
    ax.set_title(titulo_desenhado, fontsize=(12 if estreita else 14) * esc,
                 fontweight="bold", pad=10)
    ax.grid(True, axis="x", linestyle="--", alpha=.4)
    ax.grid(False, axis="y")
    ax.tick_params(axis="y", length=0)                   # sem traços de escala
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)

    n = n_por_algo if n_por_algo is not None else int(
        d.groupby(col_algo)[col_valor].size().max())
    nota = (f"Cada ponto = 1 {unidade} ({n} por algoritmo). A barra vertical é a "
            f"média reportada na tese.{nota_extra}")
    # Quebrar a nota: numa linha só, saía pelos dois lados da figura.
    largura_nota = max(28, int(118 * (largura / 9.0) / esc))
    fig.text(0.5, 0.015, "\n".join(textwrap.wrap(nota, largura_nota)),
             ha="center", va="bottom", fontsize=8.5 * esc, color="#555555",
             style="italic")
    plt.tight_layout(rect=[0, 0.10, 0.86, 1])
    fig.savefig(caminho, dpi=300)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # ── Dados fundidos ──────────────────────────────────────────────────────
    curves = _merge(os.path.join(SRC_GNN_STATS, 'all_curves_data.csv'),
                    os.path.join(SRC_MLP_STATS, 'all_curves_data.csv'),
                    ['GNN'], ['PPO', 'SAC'])
    best = _merge(os.path.join(SRC_GNN_STATS, 'all_best_scores.csv'),
                  os.path.join(SRC_MLP_STATS, 'all_best_scores.csv'),
                  ['GNN'], ['PPO', 'SAC'])
    ev = _merge(SRC_GNN_EVAL, SRC_MLP_EVAL, ['GNN'], ['PPO', 'SAC'])
    ev['success'] = ev['success'].astype(bool)
    ev.to_csv(os.path.join(OUT, 'eval_by_run_7d.csv'), index=False)
    best.to_csv(os.path.join(OUT, 'all_best_scores_7d.csv'), index=False)
    curves.to_csv(os.path.join(OUT, 'all_curves_data_7d.csv'), index=False)

    # THESIS_SCENARIOS e não SCENARIOS: é este script que produz `tab:res_eval` e
    # `tab:res_signif`, e o compromisso 3 do pré-registo do mapa grande diz que
    # «o mapa NÃO entra nas tabelas dos 7 cenários — os 7 têm campanhas com
    # orçamento e protocolo próprios, e misturá-los seria comparar coisas
    # diferentes na mesma linha». Até hoje a proteção era não haver dados do
    # 8.º cenário; a partir de ~16 ago passa a haver, e um CSV que os contenha
    # punha o mapa grande dentro das tabelas dos sete sem ninguém decidir isso.
    fora = sorted(set(ev['Scenario']) - set(THESIS_SCENARIOS))
    scen_present = [s for s in THESIS_SCENARIOS if s in set(ev['Scenario'])]
    n_runs = ev.groupby('Algorithm')['Run'].nunique().to_dict()
    print(f"[i] Runs por algoritmo (eval): {n_runs}; cenários: {len(scen_present)}")
    if fora:
        print(f"[i] Fora das tabelas da tese (compromisso 3 do pré-registo): "
              f"{', '.join(fora)}")

    # ── Normalização do eixo X (progresso de treino 0–100%) ────────────────
    curves = curves.copy()
    ss = curves.groupby(['Scenario', 'Algorithm', 'Run'])['Step'].agg(['min', 'max'])
    ss.columns = ['step_min', 'step_max']
    curves = curves.join(ss, on=['Scenario', 'Algorithm', 'Run'])
    rng = (curves['step_max'] - curves['step_min']).clip(lower=1)
    curves['TrainingProgress'] = (curves['Step'] - curves['step_min']) / rng * 100
    curves = curves.drop(columns=['step_min', 'step_max'])

    # ── 1. Curvas "1 mapa, 3 modelos" (painéis separados, banda ±sd) ────────
    # A média entre runs passa por uma grelha comum (curvas_agregadas): os runs
    # logam em passos diferentes — o SAC escreve 7-11 pontos por run — e o
    # sns.lineplot, que agrupa pelos x EXATOS, desenhava um run de cada vez
    # sempre que os x não coincidiam. Daí os dentes de serra das figuras de
    # e daí a legenda prometer uma média que a linha não era.
    for scen in scen_present:
        d = curves[curves['Scenario'] == scen]
        algos_here = [a for a in ALGOS if a in set(d['Algorithm'])]
        if not algos_here:
            continue
        # 3,15x4,2 polegadas por painel (era 5,2x6): a figura entra na tese a
        # 0,98 da largura do texto, pelo que tudo o que aqui se desenha chega a
        # papel reduzido a ~0,65. Com os 5,2x6 antigos a reducao era 0,32 e os
        # rotulos dos eixos chegavam com ~3 pt.
        fig, axes = plt.subplots(1, len(algos_here),
                                 figsize=(3.15 * len(algos_here), 4.2), squeeze=False)
        pontos_grelha = {}
        for ax, algo in zip(axes[0], algos_here):
            da = d[d['Algorithm'] == algo]
            pontos_grelha[algo] = desenhar_curva_media(ax, da, cor=ALGO_COLORS[algo])
            nr = da['Run'].nunique()
            # pad=14: no Gargalo o fitness do GNN chega a 1,2 milhões e o
            # matplotlib escreve o fator ("1e6") por cima do título do painel.
            ax.set_title(f"{algo} ({nr} execuções)", fontsize=12.5,
                         fontweight='bold', pad=14)
            ax.yaxis.get_offset_text().set_fontsize(8.5)
            ax.set_xlabel('Progresso do Treino (%)', fontsize=11)
            ax.set_ylabel(YLABEL_TREINO.get(algo, 'Score'), fontsize=10.5)
            ax.tick_params(labelsize=9.5)
            ax.set_xlim(0, 100)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))
            ax.grid(True, linestyle='--', alpha=0.5)
        fig.suptitle(f"Curvas de Aprendizagem — {SCENARIO_LABELS.get(scen, scen)}",
                     fontsize=14, fontweight='bold')
        grelhas = "/".join(str(pontos_grelha[a]) for a in algos_here)
        fig.text(0.5, 0.005,
                 "Linha = média entre as 7 execuções; banda = ±1 desvio padrão entre execuções. Cada execução é interpolada "
                 f"numa grelha comum de progresso ({grelhas} pontos, {'/'.join(algos_here)}), porque as execuções "
                 "não logam nos mesmos passos. Painéis separados porque as métricas não são comparáveis "
                 "(GNN = fitness evolutiva; PPO/SAC = recompensa episódica); o eixo X (0–100% do orçamento "
                 "de treino) é que é comparável.",
                 ha='center', va='bottom', fontsize=7.5, color='#555555', style='italic', wrap=True)
        plt.tight_layout(rect=[0, 0.11, 1, 0.94])
        fig.savefig(os.path.join(OUT, f'comparacao_mapa_{scen}.png'), dpi=300)
        plt.close(fig)
        print(f"[OK] comparacao_mapa_{scen}.png")

    # ── 2. "1 modelo, todos os mapas" ───────────────────────────────────────
    # Os bins de 2% resolveram a mancha ilegível, mas não o
    # problema de fundo: com 51 bins e um SAC que loga 9 pontos por execução,
    # cada bin continuava a receber um punhado de execuções — e a linha do SAC
    # saía serrilhada, a saltar entre execuções. Aqui usa-se a mesma agregação
    # das curvas por cenário: interpolar cada execução numa grelha comum e só
    # depois tirar a média (scripts/curvas_agregadas.py).
    pal_scen = sns.color_palette("husl", len(scen_present))
    for algo in ALGOS:
        da = curves[curves['Algorithm'] == algo].copy()
        if da.empty:
            continue
        # 8x4,8 polegadas (era 12x7): impressa a 0,95 da largura do texto, a
        # redução fica em ~0,75 e os 11 pt do eixo chegam ao papel com 8 pt.
        fig, ax = plt.subplots(figsize=(8, 4.8))
        pontos = 0
        for color, scen in zip(pal_scen, scen_present):
            sub = da[da['Scenario'] == scen]
            if sub.empty:
                continue
            x, media, _, _, n_grelha = curva_media_entre_runs(sub)
            if x.size == 0:
                continue
            pontos = max(pontos, n_grelha)
            ax.plot(x, media, color=color, linewidth=2.5,
                    label=SCENARIO_LABELS.get(scen, scen))
        ax.set_title(f'Desempenho Global — {algo} ({da["Run"].nunique()} execuções)',
                     fontsize=15, fontweight='bold', pad=14)
        ax.set_xlabel('Progresso do Treino (%)', fontsize=12)
        ax.set_ylabel(YLABEL_TREINO.get(algo, 'Score'), fontsize=12)
        ax.tick_params(labelsize=10.5)
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.legend(title='Cenário', fontsize=9.5, title_fontsize=10,
                  loc='upper left', framealpha=0.9)
        ax.grid(True, linestyle='--', alpha=0.5)
        fig.text(0.5, 0.005,
                 f"Linha = média entre as 7 execuções, cada uma interpolada numa grelha comum "
                 f"de {pontos} pontos de progresso. A dispersão por execução está nos painéis "
                 "por cenário (curvas de aprendizagem).",
                 ha='center', va='bottom', fontsize=8.5, color='#555555', style='italic')
        plt.tight_layout(rect=[0, 0.04, 1, 1])
        fig.savefig(os.path.join(OUT, f'desempenho_global_{algo.lower()}.png'), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"[OK] desempenho_global_{algo.lower()}.png")

    # ── 3. Boxplots de FIABILIDADE em métrica de TAREFA (recolhas/ep por run) ──
    # Cada ponto = média de recolhas/ep de um run (20 episódios) → 7 pontos/algoritmo.
    run_means = (ev.groupby(['Scenario', 'ScenarioLabel', 'Algorithm', 'Run'])
                 .agg(recolhas=('food_collected', 'mean'), sucesso=('success', 'mean'))
                 .reset_index())
    run_means.to_csv(os.path.join(OUT, 'eval_medias_por_run_7d.csv'), index=False)

    for scen in scen_present:
        d = run_means[run_means['Scenario'] == scen]
        # O jitter do stripplot vem do RNG GLOBAL do numpy: sem semente, a mesma
        # figura sai diferente a cada geração (mesmos dados, pontos noutro sítio).
        # Isso quebra a comparação bit-a-bit entre a figura instalada na tese e a
        # que o gerador produz hoje — e faz parecer que os dados mudaram quando
        # não mudaram. O dot plot ao lado já usava um rng semeado.
        np.random.seed(7)
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.boxplot(data=d, x='Algorithm', y='recolhas', order=ALGOS,
                    palette=ALGO_COLORS, ax=ax)
        sns.stripplot(data=d, x='Algorithm', y='recolhas', order=ALGOS,
                      color='black', size=5, alpha=0.6, jitter=0.12, ax=ax)
        ax.set_title(f'Fiabilidade entre Execuções — {SCENARIO_LABELS.get(scen, scen)}',
                     fontsize=14, fontweight='bold', pad=12)
        ax.set_ylabel('Recolhas por episódio (média do run, 20 ep)', fontsize=10)
        ax.set_xlabel('Algoritmo', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.4, axis='y')
        nr = int(d.groupby('Algorithm')['Run'].nunique().max())
        fig.text(0.5, 0.01,
                 f"Cada ponto = 1 run independente ({nr} runs/algoritmo; média de 20 episódios "
                 "determinísticos). Métrica de tarefa: mesma unidade para os três algoritmos.",
                 ha='center', va='bottom', fontsize=8.5, color='#555555', style='italic')
        fig.subplots_adjust(bottom=0.12)
        plt.tight_layout(rect=[0, 0.07, 1, 1])
        fig.savefig(os.path.join(OUT, f'boxplot_eval_{scen}.png'), dpi=300)
        plt.close(fig)
        print(f"[OK] boxplot_eval_{scen}.png")

        # Alternativa em DOT PLOT (um ponto por run). Gerada A PAR do boxplot,
        # não em vez dele: a escolha de qual entra na tese é do autor, e nos
        # cenários bimodais (Muro U, Sandbox, Gargalo) a diferença é grande.
        dotplot_por_run(
            d, f'Fiabilidade entre Execuções — {SCENARIO_LABELS.get(scen, scen)}',
            os.path.join(OUT, f'dotplot_eval_{scen}.png'), n_por_algo=nr,
            largura=5.0)   # entra na tese a 0,49 da largura do texto
        print(f"[OK] dotplot_eval_{scen}.png")

    # ── 4. Barras agregadoras (recolhas/ep, avaliação) ──────────────────────
    dd = ev.copy()
    dd['Cenário'] = dd['Scenario'].map(lambda s: SCENARIO_LABELS.get(s, s))
    scen_lab_order = [SCENARIO_LABELS.get(s, s) for s in scen_present]
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.barplot(data=dd, x='Cenário', y='food_collected', hue='Algorithm',
                order=scen_lab_order, hue_order=ALGOS, errorbar='sd',
                palette=ALGO_COLORS, ax=ax)
    ax.set_title('Resumo Geral — Recolhas por Episódio (Avaliação, 7 runs × 20 ep)',
                 fontsize=15, fontweight='bold', pad=14)
    ax.set_ylabel('Recolhas Médias por Episódio (± Desvio Padrão)', fontsize=11)
    ax.set_xlabel('Cenário', fontsize=11)
    ax.legend(title="Algoritmo", loc='upper right', fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
    plt.xticks(rotation=18, ha='right', fontsize=10)
    fig.text(0.5, 0.01,
             "Métrica de TAREFA (recolhas/episódio em avaliação determinística, 140 episódios por barra): "
             "mesma unidade para os três algoritmos, diretamente comparável.",
             ha='center', va='bottom', fontsize=9, color='#555555', style='italic')
    fig.subplots_adjust(bottom=0.14)
    plt.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(os.path.join(OUT, 'comparacao_barras_geral.png'), dpi=300)
    plt.close(fig)
    print("[OK] comparacao_barras_geral.png")

    # ── 5. Taxa de sucesso + recolhas (estilo eval_suite) ───────────────────
    from scripts.eval_suite import plot_evaluation
    plot_evaluation(summary=ev, out_dir=OUT)

    # ── 6. Resumo por cenário (para as tabelas da tese) ─────────────────────
    rows = []
    for scen in scen_present:
        for algo in ALGOS:
            d = run_means[(run_means['Scenario'] == scen) & (run_means['Algorithm'] == algo)]
            de = ev[(ev['Scenario'] == scen) & (ev['Algorithm'] == algo)]
            rows.append({
                'Scenario': scen, 'Algorithm': algo,
                'runs': len(d),
                'recolhas_media_runs': d['recolhas'].mean(),
                'recolhas_std_runs': d['recolhas'].std(ddof=1),
                'sucesso_medio_%': 100 * de['success'].mean(),
                'runs_sucesso_total': int((d['sucesso'] >= 0.999).sum()),
                'melhor_run': d['recolhas'].max(),
                'pior_run': d['recolhas'].min(),
            })
    resumo = pd.DataFrame(rows)
    resumo.to_csv(os.path.join(OUT, 'resumo_por_cenario_7d.csv'), index=False)
    print("\n=== RESUMO (recolhas/ep: média±sd entre runs | sucesso médio | runs 100%) ===")
    for _, r in resumo.iterrows():
        print(f"{r['Scenario']:<24} {r['Algorithm']:<4} "
              f"{r['recolhas_media_runs']:7.2f} ± {r['recolhas_std_runs']:6.2f} | "
              f"{r['sucesso_medio_%']:5.1f}% | {r['runs_sucesso_total']}/{r['runs']} "
              f"[{r['pior_run']:.2f}, {r['melhor_run']:.2f}]")

    # ── 7. Testes de significância sobre as médias por run (n=7 por grupo) ──
    # Import LOCAL de propósito: o scipy só é preciso aqui, e tê-lo no topo do
    # módulo impedia importar as FUNÇÕES DE FIGURA a partir de uma máquina sem
    # scipy instalado (o PC de trabalho é uma delas).
    from scipy import stats
    sig_rows = []
    for scen in scen_present:
        for a, b in itertools.combinations(ALGOS, 2):
            va = run_means[(run_means['Scenario'] == scen) & (run_means['Algorithm'] == a)]['recolhas'].values
            vb = run_means[(run_means['Scenario'] == scen) & (run_means['Algorithm'] == b)]['recolhas'].values
            if len(va) == 0 or len(vb) == 0:
                continue
            try:
                u, p = stats.mannwhitneyu(va, vb, alternative='two-sided')
            except ValueError:  # todos os valores iguais
                u, p = float('nan'), 1.0
            sig_rows.append({
                'Scenario': scen, 'Par': f'{a} vs {b}',
                'media_A': va.mean(), 'media_B': vb.mean(),
                'U': u, 'p': p, 'cliffs_delta': cliffs_delta(va, vb),
                'significativo_0.05': 'Sim' if p < 0.05 else 'não',
            })
    sig = pd.DataFrame(sig_rows)
    sig.to_csv(os.path.join(OUT, 'testes_significancia_runs_7d.csv'), index=False)

    # Tabela LaTeX pronta a incluir
    with open(os.path.join(OUT, 'testes_significancia_runs_7d.tex'), 'w', encoding='utf-8') as f:
        f.write("% Gerado por scripts/gerar_figuras_7d.py — Mann-Whitney U sobre as médias por run "
                "(7 runs/algoritmo, 20 ep/run), delta de Cliff como tamanho de efeito.\n")
        f.write("\\begin{tabular}{llrrrrl}\n\\hline\n")
        f.write("Cenário & Par & média A & média B & $p$ & $\\delta$ de Cliff & Signif. \\\\\n\\hline\n")
        for _, r in sig.iterrows():
            lab = SCENARIO_LABELS_SHORT.get(r['Scenario'], r['Scenario'])
            p_str = f"{r['p']:.4f}" if r['p'] >= 0.0001 else "$<0{,}0001$"
            f.write(f"{lab} & {r['Par']} & {r['media_A']:.2f} & {r['media_B']:.2f} & "
                    f"{p_str} & {r['cliffs_delta']:+.2f} & {r['significativo_0.05']} \\\\\n".replace('.', ','))
        f.write("\\hline\n\\end{tabular}\n")

    print("\n=== SIGNIFICÂNCIA (Mann-Whitney sobre médias por run, n=7) ===")
    for _, r in sig.iterrows():
        print(f"{r['Scenario']:<24} {r['Par']:<11} {r['media_A']:7.2f} vs {r['media_B']:7.2f}  "
              f"p={r['p']:.4f}  δ={r['cliffs_delta']:+.2f}  {r['significativo_0.05']}")

    # ── 8. Instalação como "eval oficial" do dashboard (--install-oficial) ──
    # eval_summary.csv (por episódio) + testes de significância no formato que a
    # vista Ciência consome (Label/A/B/p_value/cliffs_delta/significant/winner).
    if '--install-oficial' in sys.argv:
        eval_dir = os.path.join(PROJECT_ROOT, 'results', 'evaluation')
        stats_dir = os.path.join(PROJECT_ROOT, 'results', 'estatisticas')
        os.makedirs(eval_dir, exist_ok=True)
        os.makedirs(stats_dir, exist_ok=True)

        summary_path = os.path.join(eval_dir, 'eval_summary.csv')
        if os.path.exists(summary_path):
            bkp = os.path.join(eval_dir, 'eval_summary_pre7d.csv')
            if not os.path.exists(bkp):
                os.replace(summary_path, bkp)
        ev.to_csv(summary_path, index=False)
        print(f"[OK] Eval oficial instalado: {summary_path} ({len(ev)} episódios)")

        sig_dash_rows = []
        for _, r in sig.iterrows():
            a, b = r['Par'].split(' vs ')
            is_sig = r['p'] < 0.05
            winner = 'empate' if r['media_A'] == r['media_B'] else (a if r['media_A'] > r['media_B'] else b)
            sig_dash_rows.append({
                'Scenario': r['Scenario'],
                'Label': SCENARIO_LABELS_SHORT.get(r['Scenario'], r['Scenario']),
                'A': a, 'B': b,
                'mean_A': round(r['media_A'], 3), 'mean_B': round(r['media_B'], 3),
                'test': 'mannwhitney (médias por run, n=7)',
                'statistic': round(r['U'], 2) if pd.notna(r['U']) else float('nan'),
                'p_value': round(r['p'], 5), 'p_welch': float('nan'),
                'cliffs_delta': round(r['cliffs_delta'], 3),
                'significant': is_sig, 'winner': winner if is_sig else 'ns',
            })
        sig_dash = pd.DataFrame(sig_dash_rows)
        sig_path = os.path.join(stats_dir, 'testes_significancia_food_collected.csv')
        if os.path.exists(sig_path):
            bkp = os.path.join(stats_dir, 'testes_significancia_food_collected_pre7d.csv')
            if not os.path.exists(bkp):
                os.replace(sig_path, bkp)
        sig_dash.to_csv(sig_path, index=False)
        print(f"[OK] Significância do dashboard instalada: {sig_path}")

    print(f"\n[*] Concluído — tudo em {OUT}")


if __name__ == '__main__':
    main()
