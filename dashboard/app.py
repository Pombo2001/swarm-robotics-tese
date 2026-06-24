"""Mission Control — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

Layout: barra lateral (esquerda) com a navegação organizada por fluxo de trabalho
— OPERAÇÃO (Treinar, Monitorizar) e ANÁLISE (Ciência, Resultados, Vídeos) — e a
área principal com a vista selecionada. Tema claro (branco/preto, monocromático).
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

# Tema visual CLARO (branco/preto). Remapeia as classes (Tailwind) que as vistas já
# usam para valores claros, por isso TODAS as vistas mudam de forma coerente sem ter
# de reescrever cada uma. Tipografia Inter; cartões brancos; acentos a preto
# (monocromático); semáforos/estados mantêm a cor (significado); consolas ficam
# escuras de propósito (legibilidade de terminal).
_THEME_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .q-page, .nicegui-content { font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important; }
body { background:
    radial-gradient(900px 500px at 100% -10%, rgba(15,23,42,.04), transparent 60%),
    linear-gradient(180deg,#fbfcfe 0%, #f2f4f8 100%) !important;
  background-attachment: fixed !important; color:#0f172a !important; }

/* Cartões claros */
.glass { background:#ffffff !important; border:1px solid #e7e9f0 !important;
  box-shadow:0 1px 2px rgba(15,23,42,.05), 0 10px 30px rgba(15,23,42,.05) !important;
  backdrop-filter:none !important; }
.bg-slate-800\/70 { background:#ffffff !important; border:1px solid #e7e9f0;
  box-shadow:0 1px 2px rgba(15,23,42,.05); }
.bg-slate-900\/40, .bg-slate-900\/50, .bg-slate-900\/60 { background:#f1f4f9 !important; }
.bg-slate-900 { background:#eef2f7 !important; }
.bg-slate-600 { background:#cbd5e1 !important; }
.bg-black\/30 { background:#f1f4f9 !important; }
/* Consolas ficam escuras de propósito */
.bg-\[\#0d1117\] { background:#0f172a !important; }

/* Texto — cinzentos escuros sobre fundo claro */
.text-gray-200 { color:#334155 !important; }
.text-gray-300 { color:#475569 !important; }
.text-gray-400 { color:#64748b !important; }
.text-gray-500 { color:#6b7280 !important; }
.text-gray-600 { color:#4b5563 !important; }
.text-gray-700 { color:#334155 !important; }
/* Acentos a preto (monocromático) */
.text-sky-200, .text-sky-300, .text-sky-400 { color:#0f172a !important; }

/* Semáforos / estados (mantêm o significado) */
.bg-emerald-700\/60, .bg-emerald-700 { background:#059669 !important; }
.bg-amber-700\/60, .bg-amber-700 { background:#d97706 !important; }
.bg-red-800\/60, .bg-red-800 { background:#dc2626 !important; }
.bg-red-900\/40 { background:#fef2f2 !important; border:1px solid #fecaca; }
.text-red-200 { color:#b91c1c !important; }
.text-red-400 { color:#dc2626 !important; }
.text-emerald-300, .text-emerald-400 { color:#059669 !important; }
.text-amber-200, .text-amber-300, .text-amber-400 { color:#b45309 !important; }

/* Navegação (barra lateral) */
.q-drawer { background:#ffffff !important; border-right:1px solid #e7e9f0 !important; }
.q-tab { text-transform:none !important; font-weight:600; letter-spacing:.2px;
  justify-content:flex-start; border-radius:10px; min-height:44px; }
.q-tab__content { align-items:flex-start; }
.q-tab--active { color:#0f172a !important; background:#eef2f7; }
.q-tab:hover { background:#f3f5f9; }

.vid-card { transition: transform .18s ease, box-shadow .18s ease; }
.vid-card:hover { transform: translateY(-4px); box-shadow:0 14px 30px rgba(15,23,42,.12); }
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#d1d5db; border-radius:8px; border:2px solid transparent; background-clip:padding-box; }
::-webkit-scrollbar-thumb:hover { background:#9ca3af; background-clip:padding-box; }
.q-field--outlined .q-field__control { border-radius:10px; }
"""


@ui.page("/")
def index():
    ui.dark_mode().disable()  # tema claro
    ui.colors(primary="#111827", secondary="#475569", accent="#334155", dark="#0f172a")
    ui.add_head_html(f"<style>{_THEME_CSS}</style>")

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).classes("items-center gap-2 px-4 py-2 glass") \
            .style("border-radius:0 0 14px 14px"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()) \
            .props("flat round dense color=dark")
        ui.icon("hub").classes("text-2xl").style("color:#111827")
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
