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
                            ui.label(a).classes("font-bold text-sm text-center "
                                                f"text-[{config.ALGO_META[a]['color']}]")
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

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            _section_title("science", "Estado científico da tese")
            ui.button("Recarregar", icon="refresh", on_click=lambda: render()).props("outline size=sm")
        body = ui.column().classes("w-full gap-4")
    render()
