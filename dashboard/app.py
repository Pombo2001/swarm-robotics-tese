"""Mission Control — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

F1 entrega a vista 'Treinar' (fila de jobs + consola integrada). As restantes vistas
mostram um roadmap do que trarão em F2 (Monitorizar) e F3 (Ciência / Resultados).
"""
from nicegui import ui

from .jobs import JobQueue
from .views import treinar, servidor

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()


def _roadmap(icon: str, titulo: str, fase: str, desc: str, features: list[str]):
    """Placeholder elegante (em vez de um 'em breve' seco) para vistas por fazer."""
    with ui.column().classes("w-full items-center justify-center gap-4 py-12"):
        ui.icon(icon).classes("text-7xl text-sky-500/70")
        ui.label(titulo).classes("text-3xl font-bold")
        ui.badge(f"Planeado · {fase}", color="primary").props("rounded").classes("text-sm px-3 py-1")
        ui.label(desc).classes("text-gray-400 text-center max-w-2xl")
        with ui.card().classes("bg-slate-800/60 rounded-xl shadow-lg p-5 mt-2 w-full max-w-xl"):
            ui.label("O que esta vista vai trazer").classes("text-sm font-semibold text-sky-300 mb-1")
            for f in features:
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.icon("check_circle").classes("text-emerald-400 text-base")
                    ui.label(f).classes("text-sm text-gray-300")


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
            servidor.build()
        with ui.tab_panel(t_ciencia):
            _roadmap("science", "Ciência", "F3",
                     "O estado científico da tese num só ecrã, lido dos CSVs de avaliação.",
                     ["Matriz algoritmo × cenário com Ptask (% sucesso) e recolhas/ep",
                      "Painéis Rrobust (retenção) e Sscale (sucesso vs N agentes)",
                      "Significância estatística (p-values) e deteção de evals desfasados"])
        with ui.tab_panel(t_result):
            _roadmap("image", "Resultados", "F3",
                     "Galeria de gráficos com comparação e exportação direta para a tese.",
                     ["Filtros por sessão / tipo / cenário e zoom",
                      "Comparação A/B lado a lado (ex.: treino 24h vs 48h)",
                      "Botão 'Enviar para a Tese' (copia o PNG com o nome certo)"])


def main():
    ui.run(title="Mission Control — Swarm", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
