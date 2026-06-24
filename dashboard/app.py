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
from .views import treinar, servidor, ciencia, resultados, curvas, videos

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()

# Serve os PNGs e GIFs das sessões de treino (vistas Resultados e Vídeos).
_graficos = os.path.join(config.BASE_DIR, "results", "graficos_tese")
if os.path.isdir(_graficos):
    app.add_static_files("/graficos", _graficos)

# Tema visual — injetado uma vez por página. Tipografia Inter, fundo com gradientes
# subtis, cartões "glass", scrollbar e transições. Dá o ar de "site profissional"
# sem tocar na lógica das vistas.
_THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .q-page, .nicegui-content { font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important; }
body {
  background:
    radial-gradient(1100px 560px at 12% -12%, rgba(61,158,255,.12), transparent 60%),
    radial-gradient(900px 480px at 102% -4%, rgba(0,200,150,.10), transparent 55%),
    linear-gradient(165deg,#0a0f1c 0%, #0b1120 60%, #0a0e1a 100%) !important;
  background-attachment: fixed !important;
}
.glass { background: rgba(15,23,42,.62) !important; backdrop-filter: blur(10px);
         border:1px solid rgba(148,163,184,.12) !important; }
.vid-card { transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.vid-card:hover { transform: translateY(-4px); box-shadow:0 14px 34px rgba(0,0,0,.5); }
/* Tabs com ar de navegação de produto */
.q-tabs { border-bottom:1px solid rgba(148,163,184,.12); }
.q-tab { text-transform:none !important; font-weight:600; letter-spacing:.2px; border-radius:10px 10px 0 0; }
.q-tab--active { color:#3D9EFF !important; background:rgba(61,158,255,.06); }
.q-tab:hover { background:rgba(148,163,184,.06); }
/* Scrollbar discreta */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:8px; border:2px solid transparent; background-clip:padding-box; }
::-webkit-scrollbar-thumb:hover { background:#334155; background-clip:padding-box; }
.q-field--outlined .q-field__control { border-radius:10px; }
"""


@ui.page("/")
def index():
    ui.dark_mode().enable()
    ui.colors(primary="#3D9EFF", secondary="#00C896", accent="#FF6B6B", dark="#0b1220")
    ui.add_head_html(f"<style>{_THEME_CSS}</style>")

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).classes(
            "items-center justify-between px-6 py-3 glass").style(
            "border-radius:0 0 16px 16px"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon("hub").classes("text-3xl text-sky-400")
            with ui.column().classes("gap-0"):
                ui.label("Mission Control").classes("text-xl font-extrabold leading-tight tracking-tight")
                ui.label("Swarm Robotics · Tese ISCTE").classes("text-xs opacity-60 leading-tight")
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label("Aprendizagem por Reforço para Controlo de Enxames") \
                .classes("text-sm opacity-50 hidden md:block")
            ui.element("div").classes("h-6 w-px bg-slate-600 hidden md:block")
            with ui.row().classes("items-center gap-1 no-wrap"):
                ui.icon("circle").classes("text-emerald-400").style("font-size:9px")
                ui.label("local").classes("text-xs opacity-60")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    with ui.tabs().classes("w-full").props("align=left active-color=primary indicator-color=primary") as tabs:
        t_treinar = ui.tab("Treinar", icon="rocket_launch")
        t_monitor = ui.tab("Monitorizar", icon="monitoring")
        t_ciencia = ui.tab("Ciência", icon="science")
        t_result  = ui.tab("Resultados", icon="image")
        t_videos  = ui.tab("Vídeos", icon="smart_display")

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
        with ui.tab_panel(t_videos):
            videos.build()


def main():
    ui.run(title="Mission Control — Swarm", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
