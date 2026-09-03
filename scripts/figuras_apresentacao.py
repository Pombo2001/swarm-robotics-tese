# -*- coding: utf-8 -*-
"""As figuras da vista «Apresentação», num formato único para os oito cenários.

Porquê um script à parte
A Apresentação mostrava as figuras da pasta de cada treino vencedor, e essas
pastas não têm o mesmo formato: a campanha final tem o dot plot com os três
algoritmos e as curvas em três painéis; as campanhas adaptativas (só GNN) têm
um dot plot de uma linha, largo, com o título cortado, e uma curva de um
painel com a banda a tapar a média. Lado a lado, num ecrã, lia-se como
descuido. Aqui desenha-se tudo de novo, com o mesmo tamanho, a mesma fonte e a
mesma nota, a partir dos CSV:

* `dotplot_<cenário>.png` — os três algoritmos da campanha base (a final; o F2
  para o mapa composto) e, quando o treino vencedor é de outra campanha, uma
  linha a mais («GNN adaptativo»). A altura é a mesma com três ou quatro
  linhas.
* `curvas_<cenário>.png` — sempre três painéis (GNN, PPO, SAC), da campanha
  base; um algoritmo sem curva arquivada fica com o painel a dizê-lo, em vez
  de a figura mudar de forma.

Quem decide as colunas (base + vencedor) é `dashboard.views.apresentacao`, o
mesmo módulo que a vista usa — não há aqui uma segunda regra.

Uso:  .venv/Scripts/python.exe scripts/figuras_apresentacao.py
Saída: results/figuras_apresentacao/
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.scenarios import SCENARIO_LABELS, ALGO_COLORS  # noqa: E402
from scripts.gerar_figuras_7d import dotplot_por_run, YLABEL_TREINO  # noqa: E402
from scripts.curvas_agregadas import desenhar_curva_media  # noqa: E402
from scripts.figuras_campanha import carregar_curvas  # noqa: E402
from dashboard import config  # noqa: E402
from dashboard.views import apresentacao as ap  # noqa: E402

DESTINO = ap.FIG_DIR
GRAFICOS = os.path.join(RAIZ, "results", "graficos_tese")
ALGOS = ["GNN", "PPO", "SAC"]
# Fontes das curvas de treino por campanha base. A final tem-nas fundidas; o
# F2 do mapa composto correu em três streams, e as curvas ficaram nas pastas
# datadas de cada um (o GNN na de 16 ago, o PPO e o SAC na de 10 ago) — a
# pasta agregada `mapa_grande_f2` só copiou as do GNN.
CURVAS = {
    "final_7d": ("csv", [os.path.join(GRAFICOS, "final_7d", "all_curves_data_7d.csv")]),
    "mapa_grande_f2": ("csv", [
        os.path.join(GRAFICOS, "16-08-2026_16h14m", "dados_historicos.csv"),
        os.path.join(GRAFICOS, "10-08-2026_16h34m", "dados_historicos.csv"),
    ]),
}


def eval_csv(campanha: str) -> pd.DataFrame | None:
    d = os.path.join(GRAFICOS, campanha)
    for nome in ("eval_by_run.csv", "eval_by_run_7d.csv"):
        p = os.path.join(d, nome)
        if os.path.exists(p):
            return pd.read_csv(p)
    return None


def por_execucao(df: pd.DataFrame, cenario: str, algo: str, serie: str) -> pd.DataFrame:
    """Uma linha por execução: recolhas e sucesso médios dos 20 episódios."""
    sub = df[(df["Scenario"] == cenario) & (df["Algorithm"].str.upper() == algo)]
    g = sub.groupby("Run").agg(recolhas=("food_collected", "mean"),
                               sucesso=("success", "mean")).reset_index()
    g["Serie"] = serie
    return g


def figura_dotplot(cenario: str) -> str | None:
    partes, ordem, cores = [], [], {}
    for col in ap.colunas(cenario):
        df = eval_csv(col["campanha"])
        if df is None:
            continue
        d = por_execucao(df, cenario, col["algo"], col["serie"])
        if d.empty:
            continue
        partes.append(d)
        ordem.append(col["serie"])
        cores[col["serie"]] = col["cor"]
    if not partes:
        return None
    d = pd.concat(partes, ignore_index=True)
    n = int(d.groupby("Serie")["Run"].nunique().max())
    extra = [c for c in ap.colunas(cenario) if c["extra"]]
    nota = ("" if not extra else
            " «%s» é o treino vencedor deste cenário, de outra campanha (%s)."
            % (extra[0]["serie"], extra[0]["rotulo"]))
    # A mesma altura com três ou quatro linhas: o `dotplot_por_run` cresce por
    # linha, e ao lado das curvas as duas figuras têm de alinhar.
    altura_rel = 6.2 / ((1.35 * len(ordem) + 2.4) * 1.15)
    saida = os.path.join(DESTINO, "dotplot_%s.png" % cenario)
    dotplot_por_run(d, "Fiabilidade entre execuções — %s" % SCENARIO_LABELS.get(cenario, cenario),
                    saida, col_algo="Serie", n_por_algo=n, ordem=ordem, cores=cores,
                    nota_extra=nota, largura=9.0, altura_rel=altura_rel)
    return saida


def _curvas(campanha: str) -> pd.DataFrame:
    tipo, origem = CURVAS.get(campanha, (None, None))
    if tipo == "csv":
        partes = [pd.read_csv(p) for p in origem if os.path.exists(p)]
        c = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    elif tipo == "pasta" and os.path.isdir(origem):
        c = carregar_curvas(origem, ["mapa_grande"])
    else:
        return pd.DataFrame(columns=["Scenario", "Algorithm", "Run", "Step", "Score"])
    if c.empty:
        return c
    # Progresso 0-100 % por execução: os passos absolutos não são comparáveis
    # entre algoritmos, a fração do orçamento é.
    ss = c.groupby(["Scenario", "Algorithm", "Run"])["Step"].agg(["min", "max"])
    ss.columns = ["lo", "hi"]
    c = c.join(ss, on=["Scenario", "Algorithm", "Run"])
    c["TrainingProgress"] = (c["Step"] - c["lo"]) / (c["hi"] - c["lo"]).clip(lower=1) * 100
    return c.drop(columns=["lo", "hi"])


def figura_curvas(cenario: str) -> str | None:
    base = ap.campanha_base(cenario)
    curvas = _curvas(base)
    d = curvas[curvas["Scenario"] == cenario] if not curvas.empty else curvas
    fig, axes = plt.subplots(1, 3, figsize=(3.15 * 3, 4.2), squeeze=False)
    grelhas, presentes = [], []
    for ax, algo in zip(axes[0], ALGOS):
        da = d[d["Algorithm"] == algo] if not d.empty else d
        ax.set_title("%s%s" % (algo, " (%d execuções)" % da["Run"].nunique() if len(da) else ""),
                     fontsize=12.5, fontweight="bold", pad=14)
        if len(da):
            grelhas.append(str(desenhar_curva_media(ax, da, cor=ALGO_COLORS[algo])))
            presentes.append(algo)
            ax.yaxis.get_offset_text().set_fontsize(8.5)
            ax.set_ylabel(YLABEL_TREINO.get(algo, "Score"), fontsize=10.5)
            ax.grid(True, linestyle="--", alpha=0.5)
        else:
            ax.text(0.5, 0.5, "curva de treino\nnão arquivada", ha="center", va="center",
                    fontsize=10, color="#777777", style="italic", transform=ax.transAxes)
            ax.set_yticks([])
        ax.set_xlabel("Progresso do Treino (%)", fontsize=11)
        ax.tick_params(labelsize=9.5)
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: "%d%%" % v))
    fig.suptitle("Curvas de Aprendizagem — %s" % SCENARIO_LABELS.get(cenario, cenario),
                 fontsize=14, fontweight="bold")
    if presentes:
        fig.text(0.5, 0.005,
                 "Linha = média entre execuções; banda = ±1 desvio padrão entre execuções. Cada "
                 "execução é interpolada numa grelha comum de progresso (%s pontos, %s), porque as "
                 "execuções não logam nos mesmos passos. Painéis separados porque as métricas não "
                 "são comparáveis (GNN = fitness evolutiva; PPO/SAC = recompensa episódica); o eixo "
                 "X (0–100%% do orçamento de treino) é que é comparável."
                 % ("/".join(grelhas), "/".join(presentes)),
                 ha="center", va="bottom", fontsize=7.5, color="#555555", style="italic", wrap=True)
    plt.tight_layout(rect=[0, 0.11, 1, 0.94])
    saida = os.path.join(DESTINO, "curvas_%s.png" % cenario)
    fig.savefig(saida, dpi=300)
    plt.close(fig)
    return saida


def main() -> int:
    os.makedirs(DESTINO, exist_ok=True)
    sns.set_theme(style="whitegrid")
    falhas = 0
    for cen in config.SCENARIO_KEYS:
        if ap.vencedor(cen) is None:
            print("[!] %s: sem treino avaliado — sem figuras" % cen)
            continue
        for f in (figura_dotplot, figura_curvas):
            saida = f(cen)
            if saida:
                print("[v] %s" % os.path.relpath(saida, RAIZ))
            else:
                falhas += 1
                print("[!] %s: %s falhou" % (cen, f.__name__))
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
