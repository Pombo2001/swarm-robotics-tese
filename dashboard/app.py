"""Observatório — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

Layout: tema monocromático noturno (preto e branco), barra lateral com a navegação
por fluxo de trabalho — INÍCIO (Overview), OPERAÇÃO (Treinar, Monitorizar) e
ANÁLISE (Ciência, Resultados, Vídeos) — e a área principal com a vista selecionada.
O estilo vive em dashboard/theme.py (fonte única).
"""
import os

from nicegui import ui, app

from . import config, theme
from .jobs import JobQueue
from .views import overview, treinar, servidor, ciencia, resultados, curvas, videos

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()

# Serve os PNGs e GIFs das sessões de treino (vistas Resultados e Vídeos).
_graficos = os.path.join(config.BASE_DIR, "results", "graficos_tese")
if os.path.isdir(_graficos):
    app.add_static_files("/graficos", _graficos)


@ui.page("/")
def index():
    theme.apply()

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).classes("items-center gap-3 px-4 py-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()) \
            .props("flat round dense color=white")
        ui.icon("hub").classes("text-xl").style(f"color:{theme.INK}")
        with ui.column().classes("gap-0"):
            ui.label("Swarm Observatory").classes(
                "text-base font-bold mono-title leading-tight tracking-tight")
            ui.label("Aprendizagem por Reforço para Controlo de Enxames · ISCTE") \
                .classes("text-[11px] leading-tight").style(f"color:{theme.INK_MUTED}")
        ui.space()
        # Estado vivo da fila local (ponto a pulsar quando há treino a correr)
        with ui.row().classes("items-center gap-2 no-wrap"):
            dot = ui.element("div").classes("live-dot live-dot--idle")
            lbl = ui.label("inativo").classes("text-xs mono-num") \
                .style(f"color:{theme.INK_MUTED}")

    # ── Navegação (barra lateral, por fluxo de trabalho) ───────────────────────
    with ui.left_drawer(value=True, bordered=False).props("width=236").classes("p-3") as drawer:
        with ui.column().classes("w-full gap-1 h-full"):
            with ui.tabs().props("vertical active-color=white indicator-color=white") \
                    .classes("w-full") as tabs:
                t_overview = ui.tab("Overview", icon="public")
                ui.label("OPERAÇÃO").classes("text-[10px] font-bold tracking-[.2em] "
                                             "px-2 pt-3 pb-1").style(f"color:{theme.INK_MUTED}")
                t_treinar = ui.tab("Treinar", icon="rocket_launch")
                t_monitor = ui.tab("Monitorizar", icon="monitoring")
                ui.label("ANÁLISE").classes("text-[10px] font-bold tracking-[.2em] "
                                            "px-2 pt-3 pb-1").style(f"color:{theme.INK_MUTED}")
                t_ciencia = ui.tab("Ciência", icon="science")
                t_result  = ui.tab("Resultados", icon="image")
                t_videos  = ui.tab("Vídeos", icon="smart_display")
            ui.space()
            ui.separator()
            with ui.row().classes("items-center gap-2 px-2 pt-2 no-wrap"):
                ui.element("div").classes("live-dot live-dot--ok").style("width:6px;height:6px")
                ui.label("servidor local · :8080").classes("text-[11px] mono-num") \
                    .style(f"color:{theme.INK_MUTED}")

    # A Overview salta para outras vistas por nome (cartões de estado clicáveis).
    _by_name = {"treinar": t_treinar, "monitorizar": t_monitor,
                "ciencia": t_ciencia, "resultados": t_result, "videos": t_videos}

    def goto(name: str):
        tab = _by_name.get(name)
        if tab is not None:
            tabs.set_value(tab)

    # ── Conteúdo ───────────────────────────────────────────────────────────────
    with ui.tab_panels(tabs, value=t_overview).classes("w-full bg-transparent"):
        with ui.tab_panel(t_overview).classes("p-0"):
            overview.build(queue, goto)
        with ui.tab_panel(t_treinar):
            treinar.build(queue)
        with ui.tab_panel(t_monitor):
            with ui.column().classes("w-full gap-4 p-4"):
                curvas.build()
            servidor.build()
        with ui.tab_panel(t_ciencia):
            ciencia.build()
        with ui.tab_panel(t_result):
            resultados.build()
        with ui.tab_panel(t_videos):
            videos.build()

    # Timer do estado live, criado no slot RAIZ da página (não dentro do header):
    # se o browser desligar e os elementos morrerem, cancela-se em vez de crashar
    # ("The parent slot of the element has been deleted").
    def _tick_live():
        try:
            running = queue.is_running
            dot.classes(remove="live-dot--idle", add="" if running else "live-dot--idle")
            lbl.text = "treino a correr" if running else "inativo"
        except Exception:
            live_timer.cancel()
    live_timer = ui.timer(2.0, _tick_live)


def main():
    ui.run(title="Swarm Observatory", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
