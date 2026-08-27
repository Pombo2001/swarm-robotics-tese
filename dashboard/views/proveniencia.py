"""Vista «Proveniência» — *de onde vem este número?*

A pergunta que um júri faz e que não se pode responder com "está no CSV algures":
clica-se numa célula da tabela principal da dissertação e vê-se, no mesmo ecrã,
**o valor impresso na tese, as sete médias por execução que o compõem, o ficheiro
que as contém, o modelo que as produziu (com a data) e o comando que as
reproduz** — mais a confirmação de que os três concordam.

O `docs/REPRODUZIR.md` já mapeia resultado → dados → script, mas é um documento:
numa sala, com o júri à espera, ninguém abre um Markdown e procura a linha. Isto
é o mesmo mapa, navegável em dois cliques.

⚠️ **Não recalcula a tese.** Lê o `main.tex` (o valor tal como está impresso) e o
CSV canónico (o valor tal como os dados dizem) e mostra os dois lado a lado. Se
divergirem, é isso que aparece — em vez de se esconder atrás de um número
recalculado que daria sempre razão a si próprio. A verificação em lote dos 308
valores da tese e do artigo é o `scripts/verificar_numeros_tese.py`; esta vista é
a versão interativa da mesma ideia, para uma célula de cada vez.
"""
import os
import sys
from datetime import datetime

import pandas as pd
from nicegui import ui

from .. import config, theme

# A lógica de leitura é a MESMA do verificador (nunca uma segunda cópia: duas
# implementações do mesmo mapeamento acabam por discordar, e aí não se sabe qual
# está certa).
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _RAIZ not in sys.path:
    sys.path.append(_RAIZ)
from scripts.verificar_numeros_tese import (  # noqa: E402
    CSV_7D, MAIN_TEX, ROTULO_PARA_CENARIO, ler_tabela, numero)

CARD = theme.CARD + " p-4"
ALGOS = ("GNN", "PPO", "SAC")

# Onde vive o campeão de cada célula, para se poder mostrar a DATA do modelo —
# que é o que distingue esta campanha da de junho que anulou o F1 de 25 jul.
_CAMPEAO = {"GNN": ("models", "gnn_3d_best%s.pth"),
            "PPO": ("models_ppo", "ppo_3d_final%s.zip"),
            "SAC": ("models_sac", "sac_3d_final%s.zip")}


def _sufixo(cen):
    return "" if cen == "none" else "_" + cen


def _caminho_modelo(algo, cen):
    sub, padrao = _CAMPEAO[algo]
    fp = os.path.join(_RAIZ, "results", "models_7d", sub, padrao % _sufixo(cen))
    return fp if os.path.exists(fp) else None


def _data_modelo(fp):
    if not fp:
        return None
    try:
        return datetime.fromtimestamp(os.path.getmtime(fp))
    except OSError:
        return None


def _carregar():
    """(tabela da tese, medidas do CSV, nº de episódios). Nunca levanta."""
    try:
        tabela = ler_tabela(MAIN_TEX, "tab:res_eval")
    except SystemExit:
        tabela = {}
    if not os.path.exists(CSV_7D):
        return tabela, {}, 0

    d = pd.read_csv(CSV_7D)
    medidas = {}
    for (cen, algo), g in d.groupby(["Scenario", "Algorithm"]):
        por_run = g.groupby("Run")["food_collected"].mean().sort_index()
        medidas[(cen, algo)] = {
            "por_run": por_run,
            "media": por_run.mean(),
            "dp": por_run.std(ddof=1),
            "sucesso": 100.0 * g["success"].mean(),
            "episodios": len(g),
        }
    return tabela, medidas, len(d)


def _valores_da_tese(campos, k):
    """(sucesso, média, dp) da célula k de uma linha da tabela da tese."""
    import re
    txt_suc, txt_rec = campos[2 * k], campos[2 * k + 1]
    m = re.search(r"([\d.,{}\\]+)\s*\\pm\s*([\d.,{}\\]+)", txt_rec)
    return (numero(txt_suc),
            numero(m.group(1)) if m else None,
            numero(m.group(2)) if m else None)


def build():
    tabela, medidas, n_episodios = _carregar()

    with ui.column().classes("w-full gap-4 p-4"):
        theme.section_title("fact_check", "De onde vem este número?")
        ui.label(
            "Cada célula da tabela principal da dissertação (tab:res_eval). "
            "Clica numa para ver as sete execuções que a compõem, o ficheiro "
            "que as contém, o modelo que as produziu e o comando que as "
            "reproduz."
        ).classes("text-sm").style(f"color:{theme.INK_MUTED}")

        if not tabela or not medidas:
            with ui.card().classes(CARD):
                ui.label("Sem dados para cruzar.").classes("text-sm font-bold")
                ui.label(
                    "Falta o main.tex ou o eval_by_run_7d.csv da campanha de 7 "
                    "dias. Este CSV vive na torre — ver docs/REPRODUZIR.md, "
                    "secção «onde vivem os dados»."
                ).classes("text-xs").style(f"color:{theme.INK_MUTED}")
            return

        # O painel é criado DEPOIS da tabela (ver o fim desta função): se ficasse
        # em cima, a tabela saltava para baixo a cada clique e a célula seguinte
        # já não estava onde o rato a deixou. A closure resolve-o na chamada, que
        # é sempre posterior ao build.
        def mostrar(rotulo, algo):
            cen = ROTULO_PARA_CENARIO[rotulo]
            m = medidas.get((cen, algo))
            campos = tabela[rotulo]
            k = ALGOS.index(algo)
            t_suc, t_med, t_dp = _valores_da_tese(campos, k)

            painel.clear()
            with painel:
                with ui.card().classes(CARD + " w-full"):
                    with ui.row().classes("items-baseline gap-3"):
                        ui.label("%s · %s" % (rotulo, algo)).classes(
                            "text-lg font-bold mono-title")
                        ui.label(cen).classes("text-xs mono-num") \
                            .style(f"color:{theme.INK_MUTED}")

                    # ── o que a tese diz vs o que os dados dizem ──────────────
                    with ui.row().classes("w-full gap-6 mt-2 flex-wrap"):
                        for titulo, suc, med, dp in (
                                ("impresso na tese", t_suc, t_med, t_dp),
                                ("medido no CSV", m["sucesso"], m["media"],
                                 m["dp"])):
                            with ui.column().classes("gap-0"):
                                ui.label(titulo).classes(
                                    "text-[10px] font-bold tracking-[.15em]") \
                                    .style(f"color:{theme.INK_MUTED}")
                                ui.label(
                                    "—" if med is None else
                                    "%s ± %s" % (theme.num(med), theme.num(dp))
                                ).classes("text-2xl font-bold mono-num")
                                ui.label(
                                    "—" if suc is None
                                    else "%s%% sucesso" % theme.num(suc)
                                ).classes("text-xs mono-num") \
                                    .style(f"color:{theme.INK_MUTED}")

                    bate = (t_med is not None and abs(t_med - m["media"]) <= 0.05
                            and t_dp is not None and abs(t_dp - m["dp"]) <= 0.05)
                    ui.label("✓ a tese e os dados concordam" if bate else
                             "✗ DIVERGEM — ver scripts/verificar_numeros_tese.py") \
                        .classes("text-xs font-bold mt-1") \
                        .style("color:%s" % (theme.INK if bate else "#ff6b6b"))

                    ui.separator().classes("my-3")

                    # ── as 7 execuções ───────────────────────────────────────
                    ui.label("As %d execuções independentes (a unidade "
                             "estatística da tese é esta, não o episódio)"
                             % len(m["por_run"])).classes("text-xs font-bold")
                    with ui.row().classes("items-end gap-1 mt-2 h-24"):
                        alto = max(m["por_run"].max(), 1e-9)
                        cor = config.ALGO_META.get(algo, {}).get("color", "#7d7d7d")
                        for run, v in m["por_run"].items():
                            with ui.column().classes("items-center gap-1"):
                                ui.element("div").style(
                                    "width:26px;height:%dpx;background:%s;"
                                    "border-radius:2px" % (
                                        max(2, int(70 * v / alto)), cor))
                                ui.label("%.0f" % v).classes("text-[10px] mono-num") \
                                    .style(f"color:{theme.INK_MUTED}")
                                ui.label("#%d" % run).classes("text-[9px] mono-num") \
                                    .style(f"color:{theme.INK_MUTED}")

                    ui.separator().classes("my-3")

                    # ── proveniência ─────────────────────────────────────────
                    fp_modelo = _caminho_modelo(algo, cen)
                    quando = _data_modelo(fp_modelo)
                    linhas = [
                        ("dados",
                         "results/graficos_tese/final_7d/eval_by_run_7d.csv"
                         "  (%d episódios no total; %d nesta célula)"
                         % (n_episodios, m["episodios"])),
                        ("gerado por",
                         "scripts/gerar_figuras_7d.py --install-oficial"),
                        ("modelo",
                         (os.path.relpath(fp_modelo, _RAIZ).replace("\\", "/")
                          + ("  ·  %s" % quando.strftime("%d %b %Y")
                             if quando else ""))
                         if fp_modelo else
                         "não está no disco (ver results/mapa_grande/LEIA-ME.md)"),
                        # Opções no plural, como no `eval_by_run.py`. No singular
                        # corriam à mesma (o argparse aceita prefixos), mas isso
                        # parte-se sozinho quando o script ganhar outra opção
                        # começada por «algo». O
                        # `verificar_comandos_dashboard.py` confere-os.
                        ("reproduzir",
                         "python scripts/eval_by_run.py --algos %s --scenarios %s "
                         "--episodes 20" % (algo.lower(), cen)),
                        ("verificar tudo",
                         "python scripts/verificar_numeros_tese.py"),
                    ]
                    for rotulo_l, valor in linhas:
                        with ui.row().classes("w-full gap-3 no-wrap items-start"):
                            ui.label(rotulo_l).classes(
                                "text-[10px] font-bold tracking-[.15em] w-28 "
                                "shrink-0 pt-[2px]").style(f"color:{theme.INK_MUTED}")
                            ui.label(valor).classes("text-xs mono-num break-all")

                    if quando and not (datetime(2026, 7, 2) <= quando
                                       <= datetime(2026, 7, 10)):
                        ui.label(
                            "⚠ este modelo está FORA da janela da campanha de 7 "
                            "dias (2-9 jul) — foi um caso destes que anulou o F1 "
                            "de 25 jul"
                        ).classes("text-xs font-bold mt-2").style("color:#ffb020")

        # ── a tabela clicável ────────────────────────────────────────────────
        with ui.card().classes(CARD + " w-full"):
            with ui.grid(columns=4).classes("w-full gap-px"):
                ui.label("cenário").classes(
                    "text-[10px] font-bold tracking-[.15em] py-1") \
                    .style(f"color:{theme.INK_MUTED}")
                for a in ALGOS:
                    ui.label(a).classes(
                        "text-[10px] font-bold tracking-[.15em] py-1 text-center") \
                        .style("color:%s" % config.ALGO_META.get(a, {})
                               .get("color", theme.INK_MUTED))

                for rotulo in tabela:
                    cen = ROTULO_PARA_CENARIO[rotulo]
                    ui.label(rotulo).classes("text-xs py-2 pr-2")
                    for a in ALGOS:
                        m = medidas.get((cen, a))
                        texto = "—" if not m else theme.num(m["media"])
                        b = ui.button(
                            texto,
                            on_click=lambda r=rotulo, al=a: mostrar(r, al))
                        b.props("flat dense no-caps").classes(
                            "w-full mono-num text-sm")
                        if m:
                            r, g, bl = tuple(int(config.ALGO_META.get(a, {})
                                                 .get("color", "#7d7d7d")
                                                 .lstrip("#")[i:i + 2], 16)
                                             for i in (0, 2, 4))
                            alfa = 0.10 + 0.45 * min(1.0, m["sucesso"] / 100.0)
                            b.style("background: rgba(%d,%d,%d,%.3f)"
                                    % (r, g, bl, alfa))

        painel = ui.column().classes("w-full")
        with painel:
            ui.label("Clica numa célula acima.").classes("text-sm") \
                .style(f"color:{theme.INK_MUTED}")
