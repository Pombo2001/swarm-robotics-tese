"""Vista 'Vídeos': ver e comparar os episódios gravados (GIF 2D top-down).

Os GIFs vivem em results/graficos_tese/<sessão>/videos/<algo>_<cenario>.gif e são
servidos pela rota estática '/graficos' (registada em app.py). Três modos:
  • Comparar algoritmos — GNN/PPO/SAC lado a lado para um cenário (com Ptask);
  • Galeria — todos os vídeos com filtros (algo/cenário) e zoom;
  • Comparar treinos — o mesmo algo×cenário em dois treinos (ex.: 48h vs novo).
"""
from nicegui import ui

from .. import config, data, theme
from . import ranking

CARD = theme.CARD + " p-4"
NONE = "— (nenhum)"
ALGO_ORDER = ["gnn", "ppo", "sac"]
_section_title = theme.section_title


def _url(session: str, filename: str) -> str:
    return f"/graficos/{session}/videos/{filename}"


def _metric_chip(session: str, algo: str, scenario: str):
    """Chip com Ptask·recolhas do eval oficial (se houver), por baixo do vídeo."""
    table = data.science_table() or {}
    info = table.get(scenario, {}).get(algo.upper())
    if not info:
        return
    p = info["ptask"]
    color = "#22c55e" if p >= 80 else ("#f59e0b" if p >= 40 else "#ef4444")
    icon = "check_circle" if p >= 80 else ("error" if p >= 40 else "cancel")
    with ui.row().classes("items-center gap-1 no-wrap mt-1"):
        ui.icon(icon).style(f"color:{color}").classes("text-sm")
        ui.label(f"{p:.0f}% · {info['recolhas']:.1f} rec/ep").classes("text-xs") \
            .style(f"color:{color};font-weight:600")


def _zoom(session: str, filename: str):
    algo, scen = data.parse_video(filename)
    with ui.dialog() as dlg, ui.card().classes("glass max-w-[92vw] rounded-2xl"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"{config.ALGO_META.get(algo.upper(), {}).get('label', algo.upper())}"
                     f"  ·  {config.SCENARIO_LABEL_BY_KEY.get(scen, scen)}") \
                .classes("text-base font-semibold")
            ui.button(icon="close", on_click=dlg.close).props("flat round dense")
        ui.image(_url(session, filename)).classes("max-h-[78vh] rounded-lg object-contain")
        ui.label(filename).classes("text-xs font-mono text-gray-500 self-center")
    dlg.open()


def _video_card(session: str, algo: str, scenario: str, show_metric=True, height="clamp(180px,26vh,340px)"):
    """Cartão de um vídeo (algo×cenário) com badge colorido, GIF e métrica."""
    meta = config.ALGO_META.get(algo.upper(), {"color": "#64748b", "icon": "❓", "label": algo.upper()})
    fn = data.video_for(session, algo, scenario)
    with ui.element("div").classes("vid-card glass rounded-2xl p-3 flex flex-col gap-2").style(
            f"border-top:3px solid {meta['color']}"):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label(meta["icon"]).classes("text-lg")
            ui.label(meta["label"]).classes("text-sm font-bold").style(f"color:{meta['color']}")
        if fn:
            ui.image(_url(session, fn)).classes("w-full rounded-lg cursor-pointer bg-black/30") \
                .style(f"height:{height};object-fit:contain") \
                .on("click", lambda _, f=fn: _zoom(session, f))
            if show_metric:
                _metric_chip(session, algo, scenario)
        else:
            with ui.element("div").classes(
                    "w-full rounded-lg bg-slate-900/50 flex flex-col items-center "
                    "justify-center text-gray-600 gap-1").style(f"height:{height}"):
                ui.icon("videocam_off").classes("text-3xl")
                ui.label("sem vídeo").classes("text-xs")


# ──────────────────────────────────────────────────────────────────────────────
def build():
    sessions = data.video_sessions()
    if not sessions:
        with ui.column().classes("w-full items-center py-16 gap-3"):
            ui.icon("movie_filter").classes("text-6xl text-gray-700")
            ui.label("Ainda não há vídeos.").classes("text-gray-400 text-lg")
            ui.label("Gera-os com  python scripts/record_episode.py --all  "
                     "(ou correm no fim de cada treino).").classes("text-xs text-gray-600 font-mono")
        return

    st = {"session": sessions[0], "mode": "Comparar algoritmos",
          "scenario": (data.scenarios_with_video(sessions[0]) or [config.SCENARIO_KEYS[0]])[0]}

    # Quantas campanhas ficam DE FORA deste seletor, e porquê. Sem esta linha, a
    # lista curta lia-se como "faltam vídeos" — quando o que falta são os
    # MODELOS: as campanhas antigas foram sobrescritas pelas seguintes (só a
    # partir de julho é que cada uma passou a arquivar os seus), e sem modelo não
    # há episódio para gravar. Não é uma lacuna que se possa fechar.
    todas = data.list_sessions()
    sem_video = [s for s in todas if s not in sessions]

    with ui.column().classes("w-full gap-4 p-4 max-w-[1400px] mx-auto"):
        # ── Barra de controlo ────────────────────────────────────────────────
        with ui.card().classes(CARD):
            with ui.row().classes("w-full items-center justify-between no-wrap gap-4"):
                _section_title("smart_display", "Vídeos dos episódios",
                               "Vê o enxame a agir e compara algoritmos lado a lado.")
                sess_sel = ui.select(sessions, value=st["session"], label="Treino") \
                    .props("outlined dense").classes("min-w-[230px]")
            mode = ui.toggle(["Comparar algoritmos", "Galeria", "Comparar treinos"],
                             value=st["mode"]).props("no-caps").classes("mt-1")
            # Que algoritmos têm vídeo NESTA sessão. Uma campanha lançada com --algo GNN
            # só grava vídeos do GNN (o PPO/SAC não foram treinados nela) — sem isto
            # escrito, a ausência parece um bug do dashboard em vez de uma consequência
            # de como a campanha foi lançada.
            fonte_lbl = theme.fonte("")
            if sem_video:
                ui.label(
                    f"{len(sem_video)} das {len(todas)} campanhas não aparecem aqui: são "
                    "as antigas, cujos modelos foram sobrescritos pelos treinos "
                    "seguintes. Sem modelo não há episódio para gravar — e um vídeo "
                    "de ações aleatórias com o nome do algoritmo seria pior do que "
                    "vídeo nenhum."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")

        # O mesmo painel da Galeria: o seletor «Treino» aqui em cima tem os
        # mesmos nomes opacos, e escolher um vídeo para mostrar a alguém era
        # adivinhar qual dos treinos era o bom. Realça o que está selecionado.
        alvo_ranking = ui.column().classes("w-full")

        def _desenhar_ranking():
            alvo_ranking.clear()
            with alvo_ranking:
                ranking.painel(campanha_atual=sess_sel.value,
                               titulo="Qual treino mostrar, por cenário")

        body = ui.column().classes("w-full gap-4")

        # ── Render por modo ──────────────────────────────────────────────────
        def render():
            body.clear()
            st["session"] = sess_sel.value
            vids = data.list_videos(st["session"])
            algos = sorted({data.parse_video(v)[0] for v in vids} - {None})
            faltam = [a for a in data.VIDEO_ALGOS if a not in algos]
            txt = f"sessão {st['session']} · {len(vids)} vídeos · algoritmos: " \
                  f"{', '.join(a.upper() for a in algos) or '—'}"
            if faltam:
                txt += f"  (sem vídeo: {', '.join(a.upper() for a in faltam)} — " \
                       f"a campanha não treinou estes algoritmos)"
            fonte_lbl.text = ("⚠ " if faltam else "fonte: ") + txt
            with body:
                if mode.value == "Comparar algoritmos":
                    _render_compare_algos(st)
                elif mode.value == "Galeria":
                    _render_gallery(st)
                else:
                    _render_compare_sessions(sessions, st)

        sess_sel.on_value_change(render)
        sess_sel.on_value_change(lambda _: _desenhar_ranking())
        mode.on_value_change(render)
        _desenhar_ranking()
        render()


def _render_compare_algos(st):
    session = st["session"]
    scens = data.scenarios_with_video(session) or config.SCENARIO_KEYS
    with ui.card().classes(CARD):
        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            ui.icon("filter_alt").classes("text-gray-400")
            ui.label("Cenário:").classes("text-sm text-gray-400")
            for k in scens:
                active = (k == st["scenario"])
                btn = ui.button(
                    config.SCENARIO_LABEL_BY_KEY.get(k, k),
                    on_click=lambda _, key=k: (st.update(scenario=key), grid.refresh())) \
                    .props(f"{'unelevated' if active else 'outline'} no-caps size=sm dense") \
                    .props(f"color={'primary' if active else 'grey-7'}")

    @ui.refreshable
    def grid():
        scen = st["scenario"] if st["scenario"] in scens else (scens[0] if scens else None)
        st["scenario"] = scen
        with ui.column().classes("w-full gap-2"):
            ui.label(config.SCENARIO_LABEL_BY_KEY.get(scen, scen)) \
                .classes("text-lg font-bold text-sky-200")
            with ui.grid().classes("w-full gap-4").style(
                    "grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))"):
                for algo in ALGO_ORDER:
                    _video_card(session, algo, scen)
    grid()


def _render_gallery(st):
    session = st["session"]
    vids = data.list_videos(session)
    scens = data.scenarios_with_video(session)
    with ui.card().classes(CARD):
        with ui.row().classes("w-full items-center gap-3 no-wrap flex-wrap"):
            ui.icon("filter_alt").classes("text-gray-400")
            algo_f = ui.select(["Todos", "GNN", "PPO", "SAC"], value="Todos", label="Algoritmo") \
                .props("outlined dense").classes("min-w-[150px]")
            scen_opts = {"Todos": "Todos"}
            scen_opts.update({k: config.SCENARIO_LABEL_BY_KEY.get(k, k) for k in scens})
            scen_f = ui.select(scen_opts, value="Todos", label="Cenário") \
                .props("outlined dense").classes("min-w-[200px]")

    @ui.refreshable
    def grid():
        items = []
        for f in vids:
            a, s = data.parse_video(f)
            if algo_f.value != "Todos" and a != algo_f.value.lower():
                continue
            if scen_f.value != "Todos" and s != scen_f.value:
                continue
            items.append((f, a, s))
        if not items:
            ui.label("Nenhum vídeo para este filtro.").classes("text-gray-500")
            return
        with ui.grid().classes("w-full gap-4").style(
                "grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))"):
            for f, a, s in items:
                meta = config.ALGO_META.get(a.upper(), {"color": "#64748b", "icon": "❓"})
                with ui.element("div").classes("vid-card glass rounded-2xl p-3 flex flex-col gap-2") \
                        .style(f"border-top:3px solid {meta['color']}"):
                    with ui.row().classes("items-center justify-between no-wrap"):
                        ui.label(f"{meta['icon']} {a.upper()}").classes("text-sm font-bold") \
                            .style(f"color:{meta['color']}")
                        ui.label(config.SCENARIO_LABEL_BY_KEY.get(s, s)) \
                            .classes("text-xs text-gray-400 truncate")
                    ui.image(_url(session, f)).classes("w-full rounded-lg cursor-pointer bg-black/30") \
                        .style("height:clamp(160px,22vh,300px);object-fit:contain") \
                        .on("click", lambda _, fn=f: _zoom(session, fn))

    algo_f.on_value_change(grid.refresh)
    scen_f.on_value_change(grid.refresh)
    grid()


def _render_compare_sessions(sessions, st):
    with ui.card().classes(CARD):
        ui.label("Compara o mesmo algoritmo e cenário em dois treinos diferentes "
                 "(ex.: GNN-48h vs treino novo).").classes("text-xs text-gray-400")
        with ui.row().classes("w-full items-center gap-3 no-wrap flex-wrap mt-1"):
            sess_a = ui.select(sessions, value=sessions[0], label="Treino A") \
                .props("outlined dense").classes("flex-1 min-w-[200px]")
            sess_b = ui.select(sessions, value=sessions[min(1, len(sessions) - 1)], label="Treino B") \
                .props("outlined dense").classes("flex-1 min-w-[200px]")
            algo_s = ui.select(["GNN", "PPO", "SAC"], value="GNN", label="Algoritmo") \
                .props("outlined dense").classes("min-w-[130px]")
            scen_s = ui.select(
                {k: config.SCENARIO_LABEL_BY_KEY.get(k, k) for k in config.SCENARIO_KEYS},
                value=config.SCENARIO_KEYS[1], label="Cenário") \
                .props("outlined dense").classes("min-w-[200px]")

    @ui.refreshable
    def pair():
        algo = algo_s.value.lower()
        scen = scen_s.value
        with ui.grid().classes("w-full gap-4").style("grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))"):
            for tag, sess in (("A", sess_a.value), ("B", sess_b.value)):
                with ui.column().classes("gap-1"):
                    ui.badge(f"{tag} · {sess}", color="primary").props("rounded").classes("text-[11px]")
                    _video_card(sess, algo, scen, height="clamp(220px,34vh,420px)")

    for el in (sess_a, sess_b, algo_s, scen_s):
        el.on_value_change(pair.refresh)
    pair()
