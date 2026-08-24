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
    """Chip com Ptask·recolhas DESTE treino, por baixo do vídeo.

    ⚠️ Recebia a `session` e não a usava: lia a `science_table()`, que é a
    avaliação oficial (a campanha final), e mostrava-a por baixo de qualquer
    vídeo. No «Comparar treinos» punha o mesmo «86% · 38,3 rec/ep» debaixo dos
    dois — dois treinos diferentes com a mesma pontuação, a ler-se como um
    empate que ninguém mediu. Agora o número é o da campanha do vídeo, e quando
    essa campanha não tem avaliação determinística diz-se isso em vez de se
    emprestar o número de outra.
    """
    info = data.pontuacao_campanha(session, scenario, algo)
    if not info or info.get("ptask") is None:
        ui.label("treino sem avaliação determinística").classes("text-[10px] mt-1") \
            .style(f"color:{theme.INK_MUTED}")
        return
    p = info["ptask"]
    color = "#22c55e" if p >= 80 else ("#f59e0b" if p >= 40 else "#ef4444")
    icon = "check_circle" if p >= 80 else ("error" if p >= 40 else "cancel")
    with ui.row().classes("items-center gap-1 no-wrap mt-1"):
        ui.icon(icon).style(f"color:{color}").classes("text-sm")
        ui.label(f"{p:.0f}% · {theme.num(info['recolhas'])} rec/ep").classes("text-xs") \
            .style(f"color:{color};font-weight:600")
        if info.get("convergentes") is not None:
            # «a 100%» não é enfeite: esta contagem são as execuções em que
            # TODOS os episódios têm sucesso, e a dissertação, no mapa composto,
            # conta outra coisa — as execuções com pelo menos uma recolha (4 de
            # 21). Sem a qualificação, o cartão dizia «2/21 execuções» ao lado
            # de um texto que diz 4, e as duas contagens estão ambas certas.
            ui.label("(%d/%d execuções a 100%%)"
                     % (info["convergentes"], info["runs"])) \
                .classes("text-[10px]").style(f"color:{theme.INK_MUTED}")


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
    """Cartão de um vídeo (algo×cenário) com badge colorido, GIF e métrica.

    Quando o vídeo não existe NESTA campanha mas existe noutra, mostra-se o de
    lá **com a campanha escrita por cima**. O mapa composto obrigou a isto: os
    três braços correram em campanhas separadas (GNN a 16 ago, PPO a 7, SAC a
    10), por serem streams independentes no servidor. Sem esta procura, a vista
    que existe para comparar algoritmos mostrava um vídeo e dois «sem vídeo» —
    e a comparação que o cenário existe para fazer não se via em lado nenhum.

    O rótulo não é decoração: sem ele, três GIFs lado a lado leem-se como a
    mesma campanha, e as recolhas por baixo passariam a comparar-se como se
    tivessem corrido no mesmo dia com o mesmo código.
    """
    meta = config.ALGO_META.get(algo.upper(), {"color": "#64748b", "icon": "❓", "label": algo.upper()})
    fn = data.video_for(session, algo, scenario)
    fonte = session
    if not fn:
        outras = [s for s in data.sessoes_com_video(algo, scenario) if s != session]
        if outras:
            fonte = outras[0]
            fn = data.video_for(fonte, algo, scenario)
    # `w-full`: dentro de uma `ui.column()` os filhos alinham ao início e não
    # esticam, e o cartão encolhia à largura do rótulo «GNN (Evolutivo)» —
    # levando o vídeo atrás dele. Nos modos que põem o cartão direito na grelha
    # isto não se notava, porque a célula da grelha já o esticava; no «Comparar
    # treinos», que o embrulha numa coluna, saíam duas tiras espremidas.
    with ui.element("div").classes(
            "vid-card glass rounded-2xl p-3 flex flex-col gap-2 w-full").style(
            f"border-top:3px solid {meta['color']}"):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label(meta["icon"]).classes("text-lg")
            ui.label(meta["label"]).classes("text-sm font-bold").style(f"color:{meta['color']}")
        if fn:
            ui.image(_url(fonte, fn)).classes("w-full rounded-lg cursor-pointer bg-black/30") \
                .style(f"height:{height};object-fit:contain") \
                .on("click", lambda _, f=fn, s=fonte: _zoom(s, f))
            if fonte != session:
                ui.label("de outra campanha: %s" % fonte).classes("text-[10px]") \
                    .style(f"color:{theme.INK_MUTED}")
            if show_metric:
                # A métrica é a da campanha DE ONDE VEIO o vídeo, não a da
                # sessão escolhida: emprestar o número da outra é o defeito que
                # o `pontuacao_campanha` foi criado para fechar.
                _metric_chip(fonte, algo, scenario)
        else:
            with ui.element("div").classes(
                    "w-full rounded-lg bg-slate-900/50 flex flex-col items-center "
                    "justify-center text-gray-600 gap-1").style(f"height:{height}"):
                ui.icon("videocam_off").classes("text-3xl")
                ui.label("sem vídeo").classes("text-xs")


def build():
    # `video_sessions()` dá todas as que têm GIF; a exibição fica pelas que a
    # regra deixa mostrar (canónicas ou completas).
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
    # MODELOS: sem modelo arquivado não há episódio para gravar, e as fases de
    # gradiente do mega-treino ficaram sem os seus (LEIA-ME_modelos.md). As
    # exploratórias incompletas já não entram aqui: a galeria mostra as
    # campanhas canónicas e as completas (ver `data.campanhas_visiveis`).
    todas = data.campanhas_visiveis()
    sessions = [s for s in sessions if s in todas]
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
                    f"{len(sem_video)} das {len(todas)} campanhas mostradas não têm "
                    "vídeo: são fases cujos modelos não vieram do servidor "
                    "(LEIA-ME_modelos.md). Sem modelo não há episódio para gravar — "
                    "e um vídeo de ações aleatórias com o nome do algoritmo seria "
                    "pior do que vídeo nenhum. As campanhas exploratórias "
                    "incompletas não entram nesta lista: ficam no Arquivo."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")

        # O mesmo painel da Galeria: o seletor «Treino» aqui em cima tem os
        # mesmos nomes opacos, e escolher um vídeo para mostrar a alguém era
        # adivinhar qual dos treinos era o bom. Realça o que está selecionado.
        alvo_ranking = ui.column().classes("w-full")

        def _mostrar(campanha):
            """Clicar numa linha do ranking passa a mostrar os vídeos desse treino."""
            sess_sel.set_value(campanha)
            ui.notify("Vídeos: %s" % data.rotulo_campanha(campanha)[0],
                      type="positive", position="top")

        def _desenhar_ranking():
            alvo_ranking.clear()
            with alvo_ranking:
                # Só são clicáveis os treinos que gravaram vídeo: os outros têm
                # pontuação mas não há nada para mostrar aqui.
                ranking.painel(campanha_atual=sess_sel.value,
                               titulo="Qual treino mostrar, por cenário",
                               ao_escolher=_mostrar, escolhiveis=set(sessions))

        body = ui.column().classes("w-full gap-4")

        # ── Render por modo ──────────────────────────────────────────────────
        def render():
            body.clear()
            st["session"] = sess_sel.value
            vids = data.list_videos(st["session"])
            algos = sorted({data.parse_video(v)[0] for v in vids} - {None})
            faltam = [a for a in data.VIDEO_ALGOS if a not in algos]
            # `theme.plural` e não `{len(vids)} vídeos`: 14 das 30 campanhas
            # exibidas gravaram UM episódio — a que abre por omissão é uma
            # delas —, e a linha lia-se «· 1 vídeos ·».
            txt = f"sessão {st['session']} · {theme.plural(len(vids), 'vídeo')}" \
                  f" · algoritmos: " \
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
    """Dois treinos lado a lado, no mesmo algoritmo e cenário.

    Este modo tinha dois defeitos que se somavam para o fazer parecer avariado:

    · o cartão ia dentro de uma `ui.column()` SEM `w-full`. Uma coluna encolhe
      ao conteúdo, e o `w-full` do vídeo passava a ser relativo a essa largura —
      o GIF colapsava para a largura do badge e ficava uma tira espremida ao
      lado de meio ecrã vazio. Os outros dois modos põem o cartão direito na
      grelha, e é por isso que só este partia;
    · os treinos A e B eram os dois primeiros da lista, e o cenário o segundo do
      catálogo, sem se verificar se essa combinação existe. Como cada fase do
      mega-treino treinou um cenário só, o mais provável era abrir com dois
      «sem vídeo». Agora a ESCOLHA vem primeiro (algoritmo e cenário) e os
      seletores de treino oferecem apenas os que têm mesmo esse vídeo.
    """
    algo_ini, scen_ini = "GNN", st.get("scenario") or config.SCENARIO_KEYS[0]
    if not data.sessoes_com_video(algo_ini.lower(), scen_ini):
        # O cenário herdado do outro modo pode não ter vídeo neste algoritmo:
        # procura-se o primeiro par que exista, em vez de abrir vazio.
        for k in config.SCENARIO_KEYS:
            if data.sessoes_com_video(algo_ini.lower(), k):
                scen_ini = k
                break

    with ui.card().classes(CARD):
        ui.label("Compara o mesmo algoritmo e cenário em dois treinos diferentes. "
                 "Escolhe primeiro o que queres ver; os treinos oferecidos são os "
                 "que têm esse vídeo.").classes("text-xs text-gray-400")
        with ui.row().classes("w-full items-center gap-3 no-wrap flex-wrap mt-1"):
            algo_s = ui.select(["GNN", "PPO", "SAC"], value=algo_ini, label="Algoritmo") \
                .props("outlined dense").classes("min-w-[130px]")
            scen_s = ui.select(
                {k: config.SCENARIO_LABEL_BY_KEY.get(k, k) for k in config.SCENARIO_KEYS},
                value=scen_ini, label="Cenário") \
                .props("outlined dense").classes("min-w-[200px]")
            sess_a = ui.select([], label="Treino A") \
                .props("outlined dense").classes("flex-1 min-w-[200px]")
            sess_b = ui.select([], label="Treino B") \
                .props("outlined dense").classes("flex-1 min-w-[200px]")
        aviso = ui.label("").classes("text-xs mt-1").style("color:#ffb020")

    def _opcoes():
        """Repõe as opções de A e B para o (algoritmo, cenário) escolhidos."""
        disponiveis = data.sessoes_com_video(algo_s.value.lower(), scen_s.value)
        rotulos = {s: "%s%s" % (data.rotulo_campanha(s)[0],
                                " · " + s if data.rotulo_campanha(s)[0] != s else "")
                   for s in disponiveis}
        for el in (sess_a, sess_b):
            el.options = rotulos
            el.update()
        if not disponiveis:
            sess_a.value = sess_b.value = None
            aviso.text = ("Nenhum treino gravou vídeo desta combinação — as "
                          "campanhas treinaram um cenário de cada vez, e sem "
                          "modelo não há episódio para gravar.")
            return
        aviso.text = ("" if len(disponiveis) > 1 else
                      "Só um treino tem este vídeo: A e B mostram o mesmo.")
        sess_a.value = disponiveis[0]
        sess_b.value = disponiveis[min(1, len(disponiveis) - 1)]

    @ui.refreshable
    def pair():
        algo, scen = algo_s.value.lower(), scen_s.value
        if not sess_a.value:
            return
        with ui.grid().classes("w-full gap-4").style(
                "grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))"):
            for tag, sess in (("A", sess_a.value), ("B", sess_b.value)):
                # `w-full`: sem isto a coluna encolhe e leva o vídeo com ela.
                with ui.column().classes("gap-1 w-full"):
                    # O rótulo sozinho não chega: as campanhas datadas chamam-se
                    # todas «Exploratória», e os dois badges ficavam iguais num
                    # ecrã cujo objetivo é distingui-las.
                    rot = data.rotulo_campanha(sess)[0]
                    ui.badge("%s · %s" % (tag, rot if rot != "Exploratória" else sess),
                             color="primary").props("rounded").classes("text-[11px]")
                    _video_card(sess, algo, scen, height="clamp(220px,34vh,420px)")

    def _mudou_filtro():
        _opcoes()
        pair.refresh()

    for el in (algo_s, scen_s):
        el.on_value_change(lambda _: _mudou_filtro())
    for el in (sess_a, sess_b):
        el.on_value_change(pair.refresh)
    _opcoes()
    pair()
