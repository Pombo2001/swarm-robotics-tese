"""Mission Control — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

F1 entrega a vista 'Treinar' (fila de jobs + consola integrada). As restantes vistas
são placeholders para F2 (Monitorizar) e F3 (Ciência / Resultados).
"""
from nicegui import ui

from .jobs import JobQueue
from .views import treinar

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()


def _placeholder(titulo: str, desc: str):
    with ui.column().classes("items-center w-full p-8 gap-2"):
        ui.label(titulo).classes("text-2xl font-bold")
        ui.label(desc).classes("text-gray-500 text-center")
        ui.badge("Em breve", color="orange")


@ui.page("/")
def index():
    ui.dark_mode().enable()
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("🛰  Mission Control — Swarm Robotics").classes("text-xl font-bold")
        ui.label("Tese · ISCTE").classes("text-sm opacity-70")

    with ui.tabs().classes("w-full") as tabs:
        t_treinar = ui.tab("🚀 Treinar")
        t_monitor = ui.tab("📡 Monitorizar")
        t_ciencia = ui.tab("🔬 Ciência")
        t_result  = ui.tab("🖼 Resultados")

    with ui.tab_panels(tabs, value=t_treinar).classes("w-full"):
        with ui.tab_panel(t_treinar):
            treinar.build(queue)
        with ui.tab_panel(t_monitor):
            _placeholder("Monitorizar",
                         "Curvas de aprendizagem ao vivo + painel do servidor ISCTE (tmux/SSH). [F2]")
        with ui.tab_panel(t_ciencia):
            _placeholder("Ciência",
                         "Tabela algoritmo×cenário com Ptask/Rrobust/Sscale e significância. [F3]")
        with ui.tab_panel(t_result):
            _placeholder("Resultados",
                         "Galeria com filtros, comparação A/B (24h vs 48h) e 'Enviar para a Tese'. [F3]")


def main():
    ui.run(title="Mission Control — Swarm", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
