"""Mission Control — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

F1 entrega a vista 'Treinar' (fila de jobs + consola integrada). As restantes vistas
mostram um roadmap do que trarão em F2 (Monitorizar) e F3 (Ciência / Resultados).
"""
import os

from nicegui import ui, app

from . import config
from .jobs import JobQueue
from .views import treinar, servidor, ciencia, resultados, curvas

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()

# Serve os PNGs das sessões de treino para a galeria (vista Resultados).
_graficos = os.path.join(config.BASE_DIR, "results", "graficos_tese")
if os.path.isdir(_graficos):
    app.add_static_files("/graficos", _graficos)


@ui.page("/")
def index():
    ui.dark_mode().enable()
    ui.colors(primary="#3D9EFF", secondary="#00C896", accent="#FF6B6B", dark="#0b1220")

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=True).classes(
            "bg-gradient-to-r from-slate-900 to-slate-800 text-white items-center "
            "justify-between px-6 py-2"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon("hub").classes("text-3xl text-sky-400")
            with ui.column().classes("gap-0"):
                ui.label("Mission Control").classes("text-xl font-bold leading-tight")
                ui.label("Swarm Robotics · Tese ISCTE").classes("text-xs opacity-60 leading-tight")
        ui.label("Aprendizagem por Reforço para Controlo de Enxames") \
            .classes("text-sm opacity-50 hidden sm:block")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    with ui.tabs().classes("w-full").props("align=left active-color=primary indicator-color=primary") as tabs:
        t_treinar = ui.tab("Treinar", icon="rocket_launch")
        t_monitor = ui.tab("Monitorizar", icon="monitoring")
        t_ciencia = ui.tab("Ciência", icon="science")
        t_result  = ui.tab("Resultados", icon="image")

    with ui.tab_panels(tabs, value=t_treinar).classes("w-full bg-transparent"):
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


def main():
    ui.run(title="Mission Control — Swarm", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
