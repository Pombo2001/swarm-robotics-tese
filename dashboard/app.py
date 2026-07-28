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
from .views import (overview, treinar, servidor, ciencia, resultados, curvas,
                    videos, aovivo, arquivo, proveniencia, prontidao,
                    defesa, mapa, escala)

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()

# Serve os PNGs e GIFs das sessões de treino (vistas Resultados e Vídeos).
_graficos = os.path.join(config.BASE_DIR, "results", "graficos_tese")
if os.path.isdir(_graficos):
    app.add_static_files("/graficos", _graficos)

# Figuras instaladas na tese (a vista Mapa usa a planta do mapa grande).
_fig_tese = os.path.join(config.BASE_DIR, "Tese", "images", "resultados")
if os.path.isdir(_fig_tese):
    app.add_static_files("/figuras_tese", _fig_tese)


@ui.page("/")
def index():
    theme.apply()

    # ── Header ────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).classes("items-center gap-3 px-4 py-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()) \
            .props("flat round dense color=white")
        hub = ui.icon("hub").classes("text-xl").style(f"color:{theme.INK}")
        with ui.column().classes("gap-0"):
            ui.label("Swarm Observatory").classes(
                "text-base font-bold mono-title leading-tight tracking-tight")
            ui.label("Aprendizagem por Reforço para Controlo de Enxames · ISCTE") \
                .classes("text-[11px] leading-tight").style(f"color:{theme.INK_MUTED}")
        ui.space()
        # Modo Defesa: o mesmo dashboard, com os parâmetros de uma sala (texto
        # maior, mais contraste, sem animações). Ver theme.py.
        theme.defesa_button()
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
                # "monitoring" só existe nos Material Symbols (conjunto novo); o
                # NiceGUI carrega os Material Icons clássicos, onde esse nome não
                # resolve — o separador ficava como o ÚNICO sem ícone. "insights"
                # existe nos dois conjuntos.
                t_monitor = ui.tab("Monitorizar", icon="insights")
                ui.label("ANÁLISE").classes("text-[10px] font-bold tracking-[.2em] "
                                            "px-2 pt-3 pb-1").style(f"color:{theme.INK_MUTED}")
                t_ciencia = ui.tab("Ciência", icon="science")
                t_mapa    = ui.tab("Mapa grande", icon="map")
                t_escala  = ui.tab("Escalabilidade", icon="groups")
                # Defesa: "de onde vem este número?" respondido em dois cliques,
                # em vez de procurado no REPRODUZIR.md com o júri à espera.
                t_proven  = ui.tab("Proveniência", icon="fact_check")
                t_result  = ui.tab("Resultados", icon="image")
                t_pronto  = ui.tab("Prontidão", icon="checklist")
                t_defesa  = ui.tab("Defesa", icon="record_voice_over")
                t_videos  = ui.tab("Vídeos", icon="smart_display")
                t_aovivo  = ui.tab("Ao vivo (3D)", icon="view_in_ar")
                t_arquivo = ui.tab("Arquivo", icon="history_edu")
            ui.space()
            ui.separator()
            # Rodapé operacional: útil a trabalhar, ruído numa defesa (e no Modo
            # Defesa a letra maior partia-o em duas linhas). Ver theme.py.
            with ui.row().classes("items-center gap-2 px-2 pt-2 no-wrap op-footer"):
                ui.element("div").classes("live-dot live-dot--ok").style("width:6px;height:6px")
                ui.label("servidor local · :8080").classes("text-[11px] mono-num") \
                    .style(f"color:{theme.INK_MUTED}")

    # A Overview salta para outras vistas por nome (cartões de estado clicáveis).
    _by_name = {"treinar": t_treinar, "monitorizar": t_monitor,
                "ciencia": t_ciencia, "mapa": t_mapa,
                "escala": t_escala,
                "proveniencia": t_proven,
                "resultados": t_result, "prontidao": t_pronto,
                "defesa": t_defesa,
                "videos": t_videos,
                "aovivo": t_aovivo, "arquivo": t_arquivo}

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
        with ui.tab_panel(t_mapa):
            mapa.build()
        with ui.tab_panel(t_escala):
            escala.build()
        with ui.tab_panel(t_proven):
            proveniencia.build()
        with ui.tab_panel(t_result):
            resultados.build()
        with ui.tab_panel(t_pronto):
            prontidao.build()
        with ui.tab_panel(t_defesa):
            defesa.build()
        with ui.tab_panel(t_videos):
            videos.build()
        with ui.tab_panel(t_aovivo):
            aovivo.build()
        with ui.tab_panel(t_arquivo):
            arquivo.build()

    # Timer do estado live, criado no slot RAIZ da página (não dentro do header):
    # se o browser desligar e os elementos morrerem, cancela-se em vez de crashar
    # ("The parent slot of the element has been deleted").
    def _tick_live():
        try:
            running = queue.is_running
            dot.classes(remove="live-dot--idle", add="" if running else "live-dot--idle")
            lbl.text = "treino a correr" if running else "inativo"
            # O "hub" do header roda devagar enquanto há treino a correr.
            if running:
                hub.classes(add="spin-slow")
            else:
                hub.classes(remove="spin-slow")
        except Exception:
            live_timer.cancel()
    live_timer = ui.timer(2.0, _tick_live)


def main():
    ui.run(title="Swarm Observatory", port=8080, reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
