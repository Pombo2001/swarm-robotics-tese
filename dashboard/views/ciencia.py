"""Vista 'Ciência' (F3): o estado científico da tese num só ecrã.

Lê o eval_summary.csv (fonte de verdade) e mostra a matriz algoritmo × cenário com
Ptask (% sucesso) e recolhas/ep, com semáforos. Avisa quando a avaliação está
desfasada dos modelos (armadilha nº3) e mostra a significância estatística.
"""
from datetime import datetime

from nicegui import ui

from .. import config, data

CARD = "bg-slate-800/70 rounded-xl shadow-lg p-4 w-full"


def _section_title(icon: str, text: str):
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(icon).classes("text-sky-400 text-xl")
        ui.label(text).classes("text-lg font-bold")


def _ptask_color(p: float) -> str:
    if p >= 80:
        return "bg-emerald-700/60"
    if p >= 40:
        return "bg-amber-700/60"
    return "bg-red-800/60"


def _echart_axis_label():
    return {"color": "#94a3b8"}


def _robustez_option(table: dict) -> dict:
    """Barras de retenção (%) por cenário, uma série por algoritmo.

    Retenção = recolhas com 10% de falhas / recolhas sem falhas. 100% = imune.
    """
    scen_keys = [k for k in config.SCENARIO_KEYS if k in table]
    labels = [config.SCENARIO_LABEL_SHORT[k] for k in scen_keys]
    series = []
    for a in config.ALGOS:
        pts = []
        for k in scen_keys:
            info = table[k].get(a)
            pts.append(round(info["retencao"], 1)
                       if info and info["retencao"] is not None else None)
        s = {"name": a, "type": "bar", "barMaxWidth": 26,
             "itemStyle": {"color": config.ALGO_META[a]["color"],
                           "borderRadius": [4, 4, 0, 0]},
             "data": pts}
        series.append(s)
    if series:
        series[0]["markLine"] = {
            "silent": True, "symbol": "none",
            "lineStyle": {"color": "#64748b", "type": "dashed"},
            "data": [{"yAxis": 100,
                      "label": {"formatter": "100% · imune", "color": "#94a3b8"}}]}
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"textStyle": {"color": "#cbd5e1"}, "top": 0},
        "grid": {"left": 48, "right": 16, "top": 36, "bottom": 64},
        "xAxis": {"type": "category", "data": labels,
                  "axisLabel": {"color": "#94a3b8", "rotate": 18}},
        "yAxis": {"type": "value", "name": "Retenção (%)",
                  "nameTextStyle": {"color": "#94a3b8"},
                  "axisLabel": _echart_axis_label(),
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,.12)"}}},
        "series": series,
    }


def _escala_option(tbl: dict) -> dict:
    """Linhas de eficiência (recolhas/agente) vs N, uma série por algoritmo.

    Pontos incompatíveis (MLP do PPO/SAC com N!=20) ficam a None → a linha
    interrompe-se, mostrando que só a GNN transfere para outro N (zero-shot).
    """
    all_n = sorted({p["N"] for pts in tbl.values() for p in pts})
    series = []
    for a in config.ALGOS:
        if a not in tbl:
            continue
        by_n = {p["N"]: p for p in tbl[a]}
        pts = []
        for n in all_n:
            p = by_n.get(n)
            ok = p and p["compatible"] and p["food_per_agent"] is not None
            pts.append(round(p["food_per_agent"], 3) if ok else None)
        series.append({"name": a, "type": "line", "connectNulls": False,
                       "symbolSize": 9, "lineStyle": {"width": 3},
                       "itemStyle": {"color": config.ALGO_META[a]["color"]},
                       "data": pts})
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"textStyle": {"color": "#cbd5e1"}, "top": 0},
        "grid": {"left": 56, "right": 20, "top": 36, "bottom": 44},
        "xAxis": {"type": "category", "data": [str(n) for n in all_n],
                  "name": "Nº de agentes (N)",
                  "nameLocation": "middle", "nameGap": 28,
                  "nameTextStyle": {"color": "#94a3b8"},
                  "axisLabel": _echart_axis_label()},
        "yAxis": {"type": "value", "name": "Recolhas / agente",
                  "nameTextStyle": {"color": "#94a3b8"},
                  "axisLabel": _echart_axis_label(),
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,.12)"}}},
        "series": series,
    }


def _cell(info: dict):
    if info is None:
        with ui.element("div").classes("bg-slate-900/40 rounded-lg p-2 text-center"):
            ui.label("—").classes("text-gray-600")
        return
    with ui.element("div").classes(f"{_ptask_color(info['ptask'])} rounded-lg p-2 text-center"):
        ui.label(f"{info['ptask']:.0f}%").classes("text-lg font-bold leading-tight")
        ui.label(f"{info['recolhas']:.1f} rec/ep").classes("text-xs opacity-80 leading-tight")
        ui.label(f"n={info['n']}").classes("text-[10px] opacity-50 leading-tight")


def build():
    def render():
        body.clear()
        with body:
            # ── Frescura da avaliação ────────────────────────────────────────
            eval_t, model_t, stale = data.eval_freshness()
            with ui.card().classes(CARD):
                if eval_t == 0:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("help").classes("text-gray-400")
                        ui.label("Sem eval_summary.csv — corre uma avaliação primeiro.") \
                            .classes("text-gray-400")
                    return
                fmt = lambda t: datetime.fromtimestamp(t).strftime("%d/%m %H:%M") if t else "—"
                if stale:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("warning").classes("text-amber-400 text-2xl")
                        ui.label("Avaliação DESATUALIZADA face aos modelos").classes("text-lg font-bold text-amber-300")
                    ui.label(f"eval_summary: {fmt(eval_t)}  ·  modelo mais recente: {fmt(model_t)} "
                             "→ re-avalia antes de tirar conclusões (armadilha nº3).") \
                        .classes("text-sm text-amber-200")
                else:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("verified").classes("text-emerald-400 text-2xl")
                        ui.label(f"Avaliação coerente com os modelos (eval: {fmt(eval_t)})") \
                            .classes("text-sm text-emerald-300")

            # ── Matriz Ptask × cenário ───────────────────────────────────────
            table = data.science_table()
            with ui.card().classes(CARD):
                _section_title("grid_on", "Desempenho por cenário (Ptask · recolhas/ep)")
                if not table:
                    ui.label("Sem dados de avaliação.").classes("text-gray-500")
                else:
                    cols = len(config.ALGOS) + 1
                    with ui.grid(columns=cols).classes("w-full gap-1 mt-2"):
                        ui.label("Cenário").classes("font-bold text-sm self-center")
                        for a in config.ALGOS:
                            ui.label(a).classes("font-bold text-sm text-center") \
                                .style(f"color: {config.ALGO_META[a]['color']}")
                        for key in config.SCENARIO_KEYS:
                            if key not in table:
                                continue
                            ui.label(config.SCENARIO_LABEL_BY_KEY[key]) \
                                .classes("text-sm self-center")
                            for a in config.ALGOS:
                                _cell(table[key].get(a))
                    with ui.row().classes("gap-3 mt-2 text-xs text-gray-400"):
                        ui.html('<span class="inline-block w-3 h-3 rounded bg-emerald-700"></span> ≥80%')
                        ui.html('<span class="inline-block w-3 h-3 rounded bg-amber-700"></span> 40–80%')
                        ui.html('<span class="inline-block w-3 h-3 rounded bg-red-800"></span> &lt;40%')

            # ── Significância estatística ────────────────────────────────────
            sig = data.significance()
            if sig is not None and len(sig):
                with ui.card().classes(CARD):
                    with ui.expansion("Significância estatística (recolhas)", icon="functions") \
                            .classes("w-full"):
                        rows = [{
                            "Cenário": r["Label"], "Par": f"{r['A']} vs {r['B']}",
                            "p": f"{r['p_value']:.3g}", "δ Cliff": f"{r['cliffs_delta']:.2f}",
                            "Sig.": "✓" if r["significant"] else "—", "Vencedor": r["winner"],
                        } for _, r in sig.iterrows()]
                        ui.table(rows=rows, columns=[
                            {"name": k, "label": k, "field": k, "align": "left"}
                            for k in rows[0]]).classes("w-full").props("dense")

            # ── Robustez a falhas (Rrobust) ──────────────────────────────────
            rob = data.robustness_table()
            with ui.card().classes(CARD):
                _section_title("health_and_safety",
                               "Robustez a falhas de agentes (Rrobust)")
                ui.label("Recolhas retidas quando 10% dos agentes falham a meio do "
                         "episódio (avaliação emparelhada, mesmas seeds). 100% = imune.") \
                    .classes("text-xs text-gray-400")
                if not rob:
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("info").classes("text-sky-400")
                        ui.label("Ainda sem avaliações com falhas.").classes("text-gray-400")
                    ui.label("Gera com:  python scripts/run_eval.py --algo sac "
                             "--scenario none --episodes 30 --fail-frac 0.1") \
                        .classes("text-xs font-mono text-gray-500")
                else:
                    ui.echart(_robustez_option(rob)).classes("w-full").style("height:340px")
                    with ui.expansion("Tabela (recolhas: base → com falhas)",
                                      icon="table_view").classes("w-full"):
                        rrows = []
                        for k in config.SCENARIO_KEYS:
                            if k not in rob:
                                continue
                            for a in config.ALGOS:
                                info = rob[k].get(a)
                                if not info:
                                    continue
                                rrows.append({
                                    "Cenário": config.SCENARIO_LABEL_SHORT[k], "Algo": a,
                                    "Base": f"{info['base']:.1f}",
                                    "10% falhas": f"{info['fail']:.1f}",
                                    "Retenção": (f"{info['retencao']:.0f}%"
                                                 if info["retencao"] is not None else "—"),
                                    "n": info["n"],
                                })
                        if rrows:
                            ui.table(rows=rrows, columns=[
                                {"name": c, "label": c, "field": c, "align": "left"}
                                for c in rrows[0]]).classes("w-full").props("dense")

            # ── Escalabilidade Zero-Shot (Sscale) ────────────────────────────
            scen_scale = data.scalability_scenarios()
            with ui.card().classes(CARD):
                _section_title("open_in_full", "Escalabilidade Zero-Shot (Sscale)")
                ui.label("Eficiência (recolhas/agente) ao transferir, sem retreino, a "
                         "política de N=20 para outros tamanhos de enxame. A linha do "
                         "PPO/SAC interrompe-se em N≠20 (MLP de entrada fixa); só a GNN "
                         "(atenção sobre vizinhos) é invariante a N.") \
                    .classes("text-xs text-gray-400")
                if not scen_scale:
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("info").classes("text-sky-400")
                        ui.label("Ainda sem dados de escalabilidade.").classes("text-gray-400")
                    ui.label("Gera com:  python scripts/eval_scalability.py --scenario none "
                             "--sizes 10,20,50,100 --episodes 30") \
                        .classes("text-xs font-mono text-gray-500")
                else:
                    sel = ui.select({k: config.SCENARIO_LABEL_SHORT[k] for k in scen_scale},
                                    value=scen_scale[0], label="Cenário") \
                        .props("outlined dense").classes("w-60 mt-1")
                    holder = ui.column().classes("w-full")

                    def draw_scale():
                        holder.clear()
                        tbl = data.scalability_table(sel.value)
                        with holder:
                            if not tbl:
                                ui.label("Sem dados para este cenário.").classes("text-gray-500")
                            else:
                                ui.echart(_escala_option(tbl)).classes("w-full") \
                                    .style("height:340px")

                    sel.on_value_change(draw_scale)
                    draw_scale()

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            _section_title("science", "Estado científico da tese")
            ui.button("Recarregar", icon="refresh", on_click=lambda: render()).props("outline size=sm")
        body = ui.column().classes("w-full gap-4")
    render()
