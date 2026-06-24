"""Mission Control — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

Layout: barra lateral (esquerda) com a navegação organizada por fluxo de trabalho
— OPERAÇÃO (Treinar, Monitorizar) e ANÁLISE (Ciência, Resultados, Vídeos) — e a
área principal com a vista selecionada. Tema escuro (modo noturno).
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

# Tema visual ESCURO (modo noturno). As vistas já usam classes (Tailwind) escuras,
# por isso aqui só se trata da "casca": fundo, cartões glass, barra lateral, tabs,
# scrollbar e o efeito dos cartões de vídeo. As consolas já são escuras e os
# semáforos/estados mantêm a cor original.
_THEME_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .q-page, .nicegui-content { font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important; }
body { background:
    radial-gradient(1100px 560px at 12% -12%, rgba(61,158,255,.10), transparent 60%),
    radial-gradient(900px 480px at 102% -4%, rgba(0,200,150,.07), transparent 55%),
    linear-gradient(165deg,#0a0e17 0%, #0b1018 60%, #090d14 100%) !important;
  background-attachment: fixed !important; color:#e2e8f0; }

/* Cartões "glass" escuros (header, drawer, vista Vídeos) */
.glass { background: rgba(20,26,40,.72) !important; border:1px solid rgba(148,163,184,.12) !important;
  backdrop-filter: blur(10px); box-shadow:0 10px 30px rgba(0,0,0,.35) !important; }

/* Navegação (barra lateral) */
.q-drawer { background:#0b1120 !important; border-right:1px solid rgba(148,163,184,.10) !important; }
.q-tab { text-transform:none !important; font-weight:600; letter-spacing:.2px;
  justify-content:flex-start; border-radius:10px; min-height:44px; }
.q-tab__content { align-items:flex-start; }
.q-tab--active { color:#fff !important; background:rgba(61,158,255,.12); }
.q-tab:hover { background:rgba(148,163,184,.07); }

.vid-card { transition: transform .18s ease, box-shadow .18s ease; }
.vid-card:hover { transform: translateY(-4px); box-shadow:0 14px 34px rgba(0,0,0,.55); }
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:8px; border:2px solid transparent; background-clip:padding-box; }
::-webkit-scrollbar-thumb:hover { background:#334155; background-clip:padding-box; }
.q-field--outlined .q-field__control { border-radius:10px; }
"""


@ui.page("/")
def index():
    ui.dark_mode().enable()  # modo noturno
    ui.colors(primary="#3D9EFF", secondary="#00C896", accent="#FF6B6B", dark="#0b0f17")
    ui.add_head_html(f"<style>{_THEME_CSS}</style>")

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).classes("items-center gap-2 px-4 py-2 glass") \
            .style("border-radius:0 0 14px 14px"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()) \
            .props("flat round dense color=white")
        ui.icon("hub").classes("text-2xl text-sky-400")
        with ui.column().classes("gap-0"):
            ui.label("Mission Control").classes("text-lg font-extrabold leading-tight tracking-tight")
            ui.label("Swarm Robotics · Tese ISCTE").classes("text-xs opacity-60 leading-tight")
        ui.space()
        ui.label("Aprendizagem por Reforço para Controlo de Enxames") \
            .classes("text-sm opacity-50 hidden lg:block")

    # ── Navegação (barra lateral, por fluxo de trabalho) ───────────────────────
    with ui.left_drawer(value=True, bordered=False).props("width=240").classes("p-3") as drawer:
        with ui.column().classes("w-full gap-1 h-full"):
            with ui.tabs().props("vertical active-color=primary indicator-color=primary") \
                    .classes("w-full") as tabs:
                ui.label("OPERAÇÃO").classes("text-[11px] font-bold tracking-widest "
                                             "text-gray-500 px-2 pt-1 pb-1")
                t_treinar = ui.tab("Treinar", icon="rocket_launch")
                t_monitor = ui.tab("Monitorizar", icon="monitoring")
                ui.label("ANÁLISE").classes("text-[11px] font-bold tracking-widest "
                                            "text-gray-500 px-2 pt-3 pb-1")
                t_ciencia = ui.tab("Ciência", icon="science")
                t_result  = ui.tab("Resultados", icon="image")
                t_videos  = ui.tab("Vídeos", icon="smart_display")
            ui.space()
            ui.separator()
            with ui.row().classes("items-center gap-1 px-2 pt-1"):
                ui.icon("circle").classes("text-emerald-500").style("font-size:8px")
                ui.label("servidor local · :8080").classes("text-xs text-gray-500")

    # ── Conteúdo ───────────────────────────────────────────────────────────────
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
