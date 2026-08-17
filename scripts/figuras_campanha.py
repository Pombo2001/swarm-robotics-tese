#!/usr/bin/env python3
"""Figuras de QUALQUER campanha, com os nomes que a tese usa.

O buraco que isto tapa
----------------------
As campanhas longas correm no servidor por FASES, e o arquivo entre fases
(`week_stream*.sh`, `mega_stream*.sh`) copia isto:

    cp -r results/evaluation results/models results/logs  ~/<fase>/

`results/graficos_tese/` não está na lista. As figuras foram geradas no servidor
— e continuam lá, em pastas datadas órfãs — mas nunca vieram. Resultado medido a
31 jul: a campanha adaptativa (a da QI6, que está NA TESE) tinha 268 CSV e
**zero** imagens; o mapa grande tinha uma; o mega-treino nenhuma.

Regenerar aqui é melhor do que ir buscá-las: os gráficos do servidor misturam
runs de campanhas anteriores, porque o `all_best_scores.csv` de lá acumula — foi
exatamente por isso que o `gerar_figuras_7d.py` teve de existir para a campanha
da tese. Os CSV trazidos, esses, são limpos.

Nomes
-----
Os nomes canónicos são **os que a tese e o artigo já citam** (`\\includegraphics`),
não os do script que por acaso os gerou. Havia duas convenções para a mesma
figura — `boxplot_eval_X` vs `boxplot_X`, `comparacao_mapa_X` vs
`curva_aprendizagem_X` — e o contrato do verificador exigia a que a campanha da
tese não usa. Aqui há uma só, em NOMES, e é dela que o resto passa a depender.

Estilo
------
Nada de desenho novo: o dot plot e as figuras de avaliação vêm por importação de
`gerar_figuras_7d.py` e `eval_suite.py`. Uma segunda cópia do estilo divergiria,
e depois não se saberia qual das duas está certa.

Uso
---
    python scripts/figuras_campanha.py --listar
    python scripts/figuras_campanha.py --todas
    python scripts/figuras_campanha.py --campanha adaptativo_A1
    python scripts/figuras_campanha.py --todas --heatmaps      # corre modelos, lento
    python scripts/figuras_campanha.py --origem <dir> --nome <slug> --rotulo "..."
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.scenarios import SCENARIOS, SCENARIO_LABELS, ALGO_COLORS  # noqa: E402
from scripts.gerar_figuras_7d import dotplot_por_run, ALGOS, YLABEL_TREINO  # noqa: E402
from scripts.curvas_agregadas import desenhar_curva_media  # noqa: E402
from scripts.eval_suite import plot_evaluation  # noqa: E402

GRAFICOS = os.path.join(RAIZ, "results", "graficos_tese")

# ── NOMES CANÓNICOS ──────────────────────────────────────────────────────────
# Fonte única. Quem quiser mudar um nome muda-o aqui E nas referências do
# main.tex/artigo.tex — nunca só num dos lados (foi assim que a pasta de imagens
# da tese ficou com `boxplot_u_wall.png` de junho ao lado de
# `boxplot_eval_u_wall.png` de julho, com um nome a um caractere do outro).
NOMES = {
    "curvas":          "comparacao_mapa_{cenario}.png",
    "boxplot":         "boxplot_eval_{cenario}.png",
    "dotplot":         "dotplot_eval_{cenario}.png",
    "global":          "desempenho_global_{algo}.png",
    "barras":          "comparacao_barras_geral.png",
    "recolhas":        "recolhas_por_cenario.png",
    "sucesso":         "taxa_sucesso_por_cenario.png",
    "heat_ocupacao":   "heatmap_ocupacao_{algo}_{cenario}.png",
    "heat_geodesico":  "heatmap_geodesico_{cenario}.png",
}

# ── CAMPANHAS CANÓNICAS ──────────────────────────────────────────────────────
# As fases da adaptativa vêm do dashboard (mesma ordem e mesmos rótulos do
# pré-registo) em vez de serem reescritas aqui.
def _campanhas():
    from dashboard.data import ADAPT_FASES, ADAPT_DIR
    camp = {}
    for rotulo, sub in ADAPT_FASES:
        slug = "adaptativo_" + sub.replace("week_", "").replace("_fase", "")
        camp[slug] = (os.path.join(ADAPT_DIR, sub), rotulo)
    # O mega-treino segue o mesmo padrão de arquivo por fase, e chega a 2-3 ago.
    for d in sorted(glob.glob(os.path.join(RAIZ, "results", "mega_1mes", "*fase*"))):
        if os.path.isdir(d):
            camp["mega_" + os.path.basename(d).replace("mega_", "").replace("_fase", "")] = (
                d, f"Mega-treino · {os.path.basename(d)}")
    # F2 do mapa grande: os três braços numa só campanha, porque a figura que
    # interessa é a que os põe lado a lado. A origem é a pasta-mãe e o
    # `carregar_eval` apanha os três `eval_by_run.csv` — de propósito.
    #
    # ⚠️ É esta entrada que impede a repetição do defeito medido a 17 ago: as
    # figuras desta campanha que vieram do servidor foram desenhadas a partir do
    # `eval_summary.csv`, que só tem o **modelo campeão**, e mostravam 7,6
    # recolhas/ep onde as 21 execuções dão 1,69. Aqui a fonte é sempre o
    # `eval_by_run.csv`.
    f2 = os.path.join(RAIZ, "results", "mapa_grande")
    if glob.glob(os.path.join(f2, "f2_*", "**", "eval_by_run.csv"), recursive=True):
        camp["mapa_grande_f2"] = (f2, "Mapa Grande · F2 (3 algoritmos × 21 execuções)")
    return camp


# ── LEITURA ──────────────────────────────────────────────────────────────────
def carregar_eval(origem: str) -> pd.DataFrame | None:
    """eval_by_run.csv da campanha (uma linha por episódio avaliado)."""
    hits = glob.glob(os.path.join(origem, "**", "eval_by_run*.csv"), recursive=True)
    if not hits:
        return None
    ev = pd.concat([pd.read_csv(h) for h in sorted(hits)], ignore_index=True)
    ev["success"] = ev["success"].astype(bool)
    return ev


_RE_LOG = re.compile(r"gnn_3d_training_(?P<cen>.+?)_run(?P<run>\d+)\.csv$")


_RE_LOG_ANON = re.compile(r"gnn_3d_training_run(?P<run>\d+)\.csv$")


def carregar_curvas(origem: str, cen_avaliados=None) -> pd.DataFrame:
    """Curvas de treino no formato canónico (Scenario, Algorithm, Run, Step, Score).

    Três fontes, por ordem de preferência:
      1. um CSV já no formato canónico (`dados_historicos.csv`,
         `all_curves_data*.csv`) — é o que as campanhas ANTIGAS têm;
      2. um CSV por run em `logs/` — é o que vem do servidor;
      3. os `training_history_*` do PPO/SAC.
    A primeira faltava, e era por isso que as campanhas de maio ficavam com seis
    figuras e mais nada: tinham as curvas todas num ficheiro que ninguém lia.
    """
    linhas = []
    for nome in ("dados_historicos.csv", "all_curves_data.csv", "all_curves_data_7d.csv"):
        for caminho in glob.glob(os.path.join(origem, "**", nome), recursive=True):
            try:
                d = pd.read_csv(caminho)
            except Exception:
                continue
            if {"Scenario", "Algorithm", "Run", "Step", "Score"}.issubset(d.columns):
                linhas.append(d[["Scenario", "Algorithm", "Run", "Step", "Score"]])
    if linhas:
        return pd.concat(linhas, ignore_index=True).drop_duplicates()
    anonimos = []          # gnn_3d_training_run<N>.csv — sem cenário no nome
    for caminho in glob.glob(os.path.join(origem, "**", "gnn_3d_training_*.csv"), recursive=True):
        base = os.path.basename(caminho)
        m = _RE_LOG.search(base)
        m_anon = None if m else _RE_LOG_ANON.search(base)
        if not m and not m_anon:
            continue                      # ex.: gnn_3d_training.csv (o log corrente)
        try:
            d = pd.read_csv(caminho)
        except Exception:
            continue
        if d.empty or "best_fitness" not in d.columns:
            continue
        curva = pd.DataFrame({
            "Scenario": m.group("cen") if m else None,
            "Algorithm": "GNN",
            "Run": int((m or m_anon).group("run")),
            "Step": d["timestep"].astype(float),
            "Score": d["best_fitness"].astype(float),
        })
        (linhas if m else anonimos).append(curva)

    # O treinador só põe o cenário no nome a partir do SEGUNDO cenário da sessão:
    # o primeiro grava `gnn_3d_training_run<N>.csv`. Estas curvas existem e são
    # reais — ficavam de fora por causa do nome, e com elas a campanha inteira do
    # Sandbox (mega_A5: 21 runs) aparecia "sem curva de treino". Atribuem-se ao
    # único cenário avaliado que ficou por explicar; com mais do que um candidato
    # não se adivinha, avisa-se.
    if anonimos:
        com_nome = {c["Scenario"].iloc[0] for c in linhas if c["Scenario"].iloc[0]}
        candidatos = [s for s in (cen_avaliados or []) if s not in com_nome]
        if len(candidatos) == 1:
            for c in anonimos:
                c["Scenario"] = candidatos[0]
            linhas += anonimos
            print(f"    [i] {len(anonimos)} curvas sem cenário no nome atribuídas "
                  f"a '{candidatos[0]}' (é o único avaliado sem curva)")
        else:
            print(f"    [!] {len(anonimos)} curvas em `gnn_3d_training_run*.csv` sem "
                  f"cenário no nome e {len(candidatos)} candidatos "
                  f"({', '.join(candidatos) or 'nenhum'}) — não se adivinha, ficam de fora")
    # PPO/SAC: uma curva por cenário (não por run) no formato do SB3.
    for algo, padrao in (("PPO", "training_history_ppo*.csv"), ("SAC", "training_history_sac*.csv")):
        for caminho in glob.glob(os.path.join(origem, "**", padrao), recursive=True):
            try:
                d = pd.read_csv(caminho)
            except Exception:
                continue
            if d.empty or "ep_rew_mean" not in d.columns:
                continue
            cen = re.sub(r"training_history_(ppo|sac)_?3?d?_?", "", os.path.basename(caminho))
            cen = cen.replace(".csv", "") or "none"
            linhas.append(pd.DataFrame({
                "Scenario": cen, "Algorithm": algo, "Run": 1,
                "Step": d["timesteps"].astype(float),
                "Score": d["ep_rew_mean"].astype(float),
            }))
    return pd.concat(linhas, ignore_index=True) if linhas else pd.DataFrame(
        columns=["Scenario", "Algorithm", "Run", "Step", "Score"])


def _progresso(curves: pd.DataFrame) -> pd.DataFrame:
    """Eixo X comparável: 0-100% do orçamento de treino.

    Os passos absolutos NÃO são comparáveis entre algoritmos (o evolutivo conta
    passos de simulação de uma população inteira), mas a fração do orçamento é —
    e o orçamento é o mesmo por desenho (195 min/run).
    """
    c = curves.copy()
    ss = c.groupby(["Scenario", "Algorithm", "Run"])["Step"].agg(["min", "max"])
    ss.columns = ["lo", "hi"]
    c = c.join(ss, on=["Scenario", "Algorithm", "Run"])
    c["TrainingProgress"] = (c["Step"] - c["lo"]) / (c["hi"] - c["lo"]).clip(lower=1) * 100
    return c.drop(columns=["lo", "hi"])


# ── FIGURAS ──────────────────────────────────────────────────────────────────
def figura_curvas(curves, scen, destino):
    d = curves[curves["Scenario"] == scen]
    algos = [a for a in ALGOS if a in set(d["Algorithm"])]
    if not algos:
        return None
    fig, axes = plt.subplots(1, len(algos), figsize=(5.2 * len(algos), 6), squeeze=False)
    # Média entre runs numa grelha comum — ver scripts/curvas_agregadas.py. Com o
    # sns.lineplot sobre os x crus, cada ponto da linha vinha de um run só (os
    # runs não logam nos mesmos passos) e saíam dentes de serra.
    pontos_grelha = {}
    for ax, algo in zip(axes[0], algos):
        da = d[d["Algorithm"] == algo]
        pontos_grelha[algo] = desenhar_curva_media(ax, da, cor=ALGO_COLORS[algo])
        ax.set_title(f"{algo} ({da['Run'].nunique()} runs)", fontsize=13, fontweight="bold")
        ax.set_xlabel("Progresso do Treino (%)", fontsize=10)
        ax.set_ylabel(YLABEL_TREINO.get(algo, "Score"), fontsize=10)
        ax.set_xlim(0, 100)
        ax.grid(True, linestyle="--", alpha=0.5)
    fig.suptitle(f"Curvas de Aprendizagem — {SCENARIO_LABELS.get(scen, scen)}",
                 fontsize=15, fontweight="bold")
    grelhas = "/".join(str(pontos_grelha[a]) for a in algos)
    fig.text(0.5, 0.005,
             "Linha = média entre runs; banda = ±1 desvio padrão entre runs. Cada run é "
             f"interpolado numa grelha comum de progresso ({grelhas} pontos, {'/'.join(algos)}), "
             "porque os runs não logam nos mesmos passos. Painéis separados porque as "
             "métricas não são comparáveis (GNN = fitness evolutiva; PPO/SAC = recompensa "
             "episódica); o eixo X (0-100% do orçamento) é que é comparável.",
             ha="center", va="bottom", fontsize=8, color="#555555", style="italic", wrap=True)
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    saida = os.path.join(destino, NOMES["curvas"].format(cenario=scen))
    fig.savefig(saida, dpi=300)
    plt.close(fig)
    return saida


def figura_global(curves, algo, destino):
    da = curves[curves["Algorithm"] == algo].copy()
    if da.empty:
        return None
    cen_presentes = [s for s in SCENARIOS if s in set(da["Scenario"])]
    da["bin"] = (da["TrainingProgress"] / 2).round() * 2
    agg = da.groupby(["Scenario", "bin"])["Score"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(12, 7))
    for cor, scen in zip(sns.color_palette("husl", len(cen_presentes)), cen_presentes):
        a = agg[agg["Scenario"] == scen].sort_values("bin")
        if not a.empty:
            ax.plot(a["bin"], a["Score"], color=cor, linewidth=2.5,
                    label=SCENARIO_LABELS.get(scen, scen))
    ax.set_title(f"Desempenho Global — {algo} ({da['Run'].nunique()} runs)",
                 fontsize=15, fontweight="bold", pad=14)
    ax.set_xlabel("Progresso do Treino (%)", fontsize=11)
    ax.set_ylabel(YLABEL_TREINO.get(algo, "Score"), fontsize=11)
    ax.set_xlim(0, 100)
    ax.legend(title="Cenário", fontsize=9, title_fontsize=10, loc="upper left", framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    saida = os.path.join(destino, NOMES["global"].format(algo=algo.lower()))
    fig.savefig(saida, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return saida


def figura_boxplot(run_means, scen, destino):
    d = run_means[run_means["Scenario"] == scen]
    if d.empty:
        return None
    # Jitter reprodutível: o stripplot usa o RNG global (ver gerar_figuras_7d).
    np.random.seed(7)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(data=d, x="Algorithm", y="recolhas", order=ALGOS, palette=ALGO_COLORS, ax=ax)
    sns.stripplot(data=d, x="Algorithm", y="recolhas", order=ALGOS,
                  color="black", size=5, alpha=0.6, jitter=0.12, ax=ax)
    ax.set_title(f"Fiabilidade entre Runs — {SCENARIO_LABELS.get(scen, scen)}",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Recolhas por episódio (média do run, 20 ep)", fontsize=10)
    ax.set_xlabel("Algoritmo", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")
    nr = int(d.groupby("Algorithm")["Run"].nunique().max())
    fig.text(0.5, 0.01, f"Cada ponto = 1 run independente ({nr} runs/algoritmo, 20 episódios "
                        "determinísticos). Métrica de tarefa: mesma unidade para os três.",
             ha="center", va="bottom", fontsize=8.5, color="#555555", style="italic")
    plt.tight_layout(rect=[0, 0.07, 1, 1])
    saida = os.path.join(destino, NOMES["boxplot"].format(cenario=scen))
    fig.savefig(saida, dpi=300)
    plt.close(fig)
    # O dot plot vai a par (não em vez): com n pequeno os quartis são ruído e a
    # caixa cheia sugere densidade onde não há um único run.
    dotplot_por_run(d, f"Fiabilidade entre Runs — {SCENARIO_LABELS.get(scen, scen)}",
                    os.path.join(destino, NOMES["dotplot"].format(cenario=scen)), n_por_algo=nr)
    return saida


def figura_barras(ev, destino):
    dd = ev.copy()
    dd["Cenário"] = dd["Scenario"].map(lambda s: SCENARIO_LABELS.get(s, s))
    ordem = [SCENARIO_LABELS.get(s, s) for s in SCENARIOS if s in set(ev["Scenario"])]
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.barplot(data=dd, x="Cenário", y="food_collected", hue="Algorithm",
                order=ordem, hue_order=ALGOS, errorbar="sd", palette=ALGO_COLORS, ax=ax)
    ax.set_title("Resumo Geral — Recolhas por Episódio (avaliação determinística)",
                 fontsize=15, fontweight="bold", pad=14)
    ax.set_ylabel("Recolhas Médias por Episódio (± Desvio Padrão)", fontsize=11)
    ax.set_xlabel("Cenário", fontsize=11)
    ax.legend(title="Algoritmo", loc="upper right", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")
    plt.xticks(rotation=18, ha="right", fontsize=10)
    plt.tight_layout()
    saida = os.path.join(destino, NOMES["barras"])
    fig.savefig(saida, dpi=300)
    plt.close(fig)
    return saida


# ── UMA CAMPANHA ─────────────────────────────────────────────────────────────
def gerar(origem: str, nome: str, rotulo: str = "", heatmaps: bool = False,
          videos: bool = False) -> int:
    destino = os.path.join(GRAFICOS, nome)
    print(f"\n=== {nome} ===\n    origem:  {os.path.relpath(origem, RAIZ)}")
    ev = carregar_eval(origem)
    # Uma campanha SEM avaliação não é uma campanha sem figuras: as antigas (maio,
    # início de junho) só guardaram curvas de treino, e ficavam com meia dúzia de
    # imagens porque este script desistia à primeira. Sem eval não há boxplots
    # nem barras — mas há curvas, e é isso que essas campanhas têm para mostrar.
    so_curvas = ev is None or ev.empty
    if so_curvas:
        print("    [i] sem avaliação — só as curvas de treino (campanha exploratória)")
    os.makedirs(destino, exist_ok=True)
    sns.set_theme(style="whitegrid")

    feitas = []
    cen_presentes = []
    if not so_curvas:
        cen_presentes = [s for s in SCENARIOS if s in set(ev["Scenario"])]
        n_runs = ev.groupby("Algorithm")["Run"].nunique().to_dict()
        print(f"    dados:   {len(ev)} episódios · {len(cen_presentes)} cenários · runs {n_runs}")

        # Auto-contida: a avaliação vive DENTRO da campanha, senão perde-se quando a
        # pasta global for sobrescrita pela campanha seguinte (contrato do pos_campanha).
        ev.to_csv(os.path.join(destino, "eval_by_run.csv"), index=False)
        for extra in ("eval_summary.csv",):
            hit = glob.glob(os.path.join(origem, "**", extra), recursive=True)
            if hit:
                shutil.copy2(hit[0], os.path.join(destino, extra))

        run_means = (ev.groupby(["Scenario", "ScenarioLabel", "Algorithm", "Run"])
                     .agg(recolhas=("food_collected", "mean"), sucesso=("success", "mean"))
                     .reset_index())
        run_means.to_csv(os.path.join(destino, "eval_medias_por_run.csv"), index=False)

        for scen in cen_presentes:
            if figura_boxplot(run_means, scen, destino):
                feitas.append(NOMES["boxplot"].format(cenario=scen))

        feitas.append(os.path.basename(figura_barras(ev, destino)))
        plot_evaluation(summary=ev, out_dir=destino)   # recolhas_ / taxa_sucesso_por_cenario
        feitas += [NOMES["recolhas"], NOMES["sucesso"]]

    curvas = carregar_curvas(origem, cen_presentes)
    if curvas.empty:
        print("    [!] sem logs de treino: as curvas ficam por fazer (só a avaliação veio do servidor)")
    else:
        curvas = _progresso(curvas)
        com_curva = set(curvas["Scenario"])
        # Os dados por trás das figuras ficam ao lado delas, com os nomes que o
        # contrato conhece: uma figura sem o CSV que a gerou não se pode auditar,
        # e a auditoria é o que se pede numa defesa.
        curvas.to_csv(os.path.join(destino, "all_curves_data.csv"), index=False)
        (curvas.groupby(["Scenario", "Algorithm", "Run"])["Score"].max()
               .reset_index().rename(columns={"Score": "BestScore"})
               .to_csv(os.path.join(destino, "all_best_scores.csv"), index=False))
        for scen in [s for s in SCENARIOS if s in com_curva]:
            if figura_curvas(curvas, scen, destino):
                feitas.append(NOMES["curvas"].format(cenario=scen))
        for algo in ALGOS:
            if figura_global(curvas, algo, destino):
                feitas.append(NOMES["global"].format(algo=algo.lower()))
        # Um cenário avaliado sem curva de treino não é um erro do desenho: é um
        # log que não veio (o treinador só escreve `..._<cenario>_run<N>.csv` a
        # partir do 2.º cenário; o 1.º fica no `gnn_3d_training.csv` corrente e é
        # sobrescrito). Dizê-lo alto vale mais do que uma figura em falta calada.
        sem_curva = [s for s in cen_presentes if s not in com_curva]
        if sem_curva:
            print(f"    [!] avaliados mas sem curva de treino nos logs: {', '.join(sem_curva)}")

    if videos:
        from scripts import record_episode as rec
        tem_modelos_v = os.path.isdir(os.path.join(origem, "models"))
        algos_v = (tuple(a.lower() for a in ALGOS) if so_curvas
                   else tuple(a.lower() for a in ALGOS if a in set(ev["Algorithm"])))
        print(f"    vídeos: {len(algos_v)}×{len(cen_presentes)} episódios a gravar...")
        rec.generate_all(destino, algos=algos_v, scenarios=cen_presentes or None,
                         models_root=origem if tem_modelos_v else None)

    if heatmaps:
        from scripts import heatmaps as hm
        # Os modelos vêm da PRÓPRIA campanha (`<origem>/models*`), nunca de
        # results/models — os ativos são os campeões 7d da tese, e copiá-los para
        # cá "só para gerar as figuras" é a armadilha n.º 9 à espera de acontecer.
        tem_modelos = os.path.isdir(os.path.join(origem, "models"))
        raiz_modelos = origem if tem_modelos else None
        algos_aqui = (tuple(a.lower() for a in ALGOS) if so_curvas
                      else tuple(a.lower() for a in ALGOS if a in set(ev["Algorithm"])))
        print(f"    heatmaps: a correr {len(algos_aqui)}×{len(cen_presentes)} modelos de "
              f"{'da campanha' if tem_modelos else 'results/ (campanha sem models/)'} — lento...")
        hm.generate_all(out_dir=destino, episodes=4, algos=algos_aqui,
                        scenarios=cen_presentes or None, models_root=raiz_modelos)

    with open(os.path.join(destino, "CAMPANHA.md"), "w", encoding="utf-8") as f:
        f.write(f"# {rotulo or nome}\n\n"
                f"- Origem dos dados: `{os.path.relpath(origem, RAIZ)}`\n")
        if so_curvas:
            f.write("- **Sem avaliação determinística** — esta campanha só guardou "
                    "curvas de treino, por isso não tem boxplots nem barras. As "
                    "curvas dizem como o treino evoluiu; não dizem o que o modelo "
                    "final recolhe.\n")
        else:
            f.write(f"- Episódios avaliados: {len(ev)}\n"
                    f"- Cenários: {', '.join(cen_presentes)}\n"
                    f"- Runs por algoritmo: {n_runs}\n")
        f.write("- Figuras geradas por `scripts/figuras_campanha.py` "
                "(nomes canónicos = os que a tese cita)\n")

    n_png = len(glob.glob(os.path.join(destino, "*.png")))
    print(f"    [v] {n_png} figuras em results/graficos_tese/{nome}/")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--todas", action="store_true", help="todas as campanhas canónicas")
    p.add_argument("--listar", action="store_true", help="mostra as campanhas conhecidas")
    p.add_argument("--campanha", help="slug de uma campanha canónica")
    p.add_argument("--origem", help="pasta de origem (uso avulso)")
    p.add_argument("--nome", help="slug de saída (com --origem)")
    p.add_argument("--rotulo", default="", help="descrição legível")
    p.add_argument("--heatmaps", action="store_true",
                   help="também os heatmaps de ocupação (corre os modelos, lento)")
    p.add_argument("--videos", action="store_true",
                   help="também os GIFs por algoritmo×cenário (corre os modelos, lento)")
    args = p.parse_args()

    camp = _campanhas()
    if args.listar:
        for slug, (origem, rotulo) in camp.items():
            existe = "ok " if os.path.isdir(origem) else "SEM "
            print(f"  [{existe}] {slug:22} {rotulo}")
        return 0

    if args.origem:
        return gerar(args.origem, args.nome or os.path.basename(args.origem.rstrip("/\\")),
                     args.rotulo, args.heatmaps, args.videos)
    if args.campanha:
        if args.campanha not in camp:
            print(f"[X] campanha desconhecida: {args.campanha} (usa --listar)")
            return 2
        origem, rotulo = camp[args.campanha]
        return gerar(origem, args.campanha, rotulo, args.heatmaps, args.videos)
    if args.todas:
        falhas = 0
        for slug, (origem, rotulo) in camp.items():
            if os.path.isdir(origem):
                falhas += gerar(origem, slug, rotulo, args.heatmaps, args.videos)
        return 1 if falhas else 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
