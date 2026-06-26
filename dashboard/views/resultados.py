"""Vista 'Resultados' (F3): galeria de gráficos com filtros, comparação A/B e
exportação direta para a tese.

As imagens são servidas pela rota estática '/graficos' (registada em app.py).
"""
from nicegui import ui

from .. import config, data

CARD = "bg-slate-800/70 rounded-xl shadow-lg p-4 w-full"
NONE = "— (sem comparação)"

# Cenários e labels vêm de config (fonte única — ver dashboard/config.py).
SCEN_ORDER = config.MAIN_SCENARIO_KEYS
SCEN_LABEL = config.SCENARIO_LABEL_SHORT

# Ordem e ícone de cada secção da galeria (agrupa por tipo de gráfico).
TYPE_ORDER = [
    "Métricas de tarefa", "Curvas por algoritmo", "Curvas por mapa",
    "Boxplots por cenário", "Boxplots por algoritmo",
    "Heatmaps de ocupação", "Heatmaps geodésicos", "Outros",
]
TYPE_ICON = {
    "Métricas de tarefa": "leaderboard", "Curvas por algoritmo": "show_chart",
    "Curvas por mapa": "stacked_line_chart",
    "Boxplots por cenário": "candlestick_chart",
    "Boxplots por algoritmo": "candlestick_chart",
    "Heatmaps de ocupação": "grid_view", "Heatmaps geodésicos": "route",
    "Outros": "image",
}
# Prefixos conhecidos dos nomes de ficheiro (removidos para gerar o título).
_PREFIXES = ["comparacao_mapa", "comparacao_barras", "heatmap_ocupacao",
             "heatmap_geodesico", "boxplot_por_algo", "desempenho_global",
             "taxa_sucesso", "recolhas", "boxplot"]
# Nomes descritivos (sem algo nem cenário) que a heurística de prefixo não
# resolve bem — título fixo e legível (com acentos que o ficheiro não tem).
_FULL_TITLE = {
    "taxa_sucesso_por_cenario": "Taxa de sucesso por cenário",
    "recolhas_por_cenario": "Recolhas por cenário",
    "comparacao_barras_geral": "Comparação geral (barras)",
}


def _pretty_title(f: str) -> str:
    """'heatmap_ocupacao_gnn_u_wall.png' -> 'GNN · Muro em U' (título legível)."""
    name = f[:-4] if f.lower().endswith(".png") else f
    if name in _FULL_TITLE:
        return _FULL_TITLE[name]
    rest = name
    for p in sorted(_PREFIXES, key=len, reverse=True):
        if name.startswith(p):
            rest = name[len(p):].lstrip("_")
            break
    bits = []
    for a in ("gnn", "ppo", "sac"):
        if rest == a or rest.startswith(a + "_"):
            bits.append(a.upper())
            rest = rest[len(a):].lstrip("_")
            break
    if rest in SCEN_LABEL:
        bits.append(SCEN_LABEL[rest])
    elif rest:
        bits.append(rest.replace("_", " ").title())
    return " · ".join(bits) if bits else name


def _section_title(icon: str, text: str):
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(icon).classes("text-sky-400 text-xl")
        ui.label(text).classes("text-lg font-bold")


def _comparison_html(metrics_a: dict, metrics_b: dict) -> str:
    """Tabela HTML A vs B com Ptask% e recolhas/ep e delta colorido (maior=melhor)."""
    def delta(va, vb, unit=""):
        if va is None or vb is None:
            return "<span style='color:#64748b'>—</span>"
        d = vb - va
        if abs(d) < 1e-9:
            return "<span style='color:#64748b'>0</span>"
        col = "#22c55e" if d > 0 else "#ef4444"
        sign = "+" if d > 0 else ""
        return f"<span style='color:{col};font-weight:600'>{sign}{d:.1f}{unit}</span>"

    def cell(m, key, fmt):
        if m is None:
            return "<span style='color:#475569'>n/d</span>"
        return fmt.format(m[key])

    th = ("padding:4px 10px;text-align:center;border-bottom:1px solid #334155;"
          "font-weight:600;color:#cbd5e1")
    td = "padding:3px 10px;text-align:center;border-bottom:1px solid #1e293b"
    rows = []
    algos = ["GNN", "PPO", "SAC"]
    for s in SCEN_ORDER:
        a_s = metrics_a.get(s, {}) if metrics_a else {}
        b_s = metrics_b.get(s, {}) if metrics_b else {}
        for i, alg in enumerate(algos):
            ma, mb = a_s.get(alg), b_s.get(alg)
            scen_cell = (f"<td style='{td};text-align:left;font-weight:600;color:#93c5fd' "
                         f"rowspan='3'>{SCEN_LABEL.get(s, s)}</td>") if i == 0 else ""
            rows.append(
                f"<tr>{scen_cell}"
                f"<td style='{td};text-align:left;color:#e2e8f0'>{alg}</td>"
                f"<td style='{td}'>{cell(ma, 'ptask', '{:.0f}%')}</td>"
                f"<td style='{td}'>{cell(mb, 'ptask', '{:.0f}%')}</td>"
                f"<td style='{td}'>{delta(ma['ptask'] if ma else None, mb['ptask'] if mb else None, '%')}</td>"
                f"<td style='{td}'>{cell(ma, 'recolhas', '{:.1f}')}</td>"
                f"<td style='{td}'>{cell(mb, 'recolhas', '{:.1f}')}</td>"
                f"<td style='{td}'>{delta(ma['recolhas'] if ma else None, mb['recolhas'] if mb else None)}</td>"
                f"</tr>")
    return (
        "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        "<thead><tr>"
        f"<th style='{th};text-align:left'>Cenário</th>"
        f"<th style='{th};text-align:left'>Algo</th>"
        f"<th style='{th}' colspan='3'>Ptask (sucesso %)</th>"
        f"<th style='{th}' colspan='3'>Recolhas / ep</th>"
        "</tr><tr>"
        f"<th style='{th}'></th><th style='{th}'></th>"
        f"<th style='{th}'>A</th><th style='{th}'>B</th><th style='{th}'>Δ</th>"
        f"<th style='{th}'>A</th><th style='{th}'>B</th><th style='{th}'>Δ</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def _url(session: str, filename: str) -> str:
    return f"/graficos/{session}/{filename}"


def build():
    sessions = data.list_sessions()

    def open_zoom(session: str, filename: str):
        with ui.dialog() as dlg, ui.card().classes("max-w-[90vw]"):
            ui.label(filename).classes("text-sm font-mono text-gray-300")
            ui.image(_url(session, filename)).classes("max-h-[75vh] object-contain")
            with ui.row().classes("w-full justify-end gap-2"):
                def enviar():
                    ok, msg = data.send_to_thesis(session, filename)
                    ui.notify(f"Enviado para a tese: {msg}" if ok else f"Falhou: {msg}",
                              type="positive" if ok else "negative")
                ui.button("Enviar para a Tese", icon="upload_file", on_click=enviar) \
                    .props("color=secondary")
                ui.button("Fechar", on_click=dlg.close).props("flat")
        dlg.open()

    if not sessions:
        with ui.column().classes("w-full items-center py-10 gap-2"):
            ui.icon("image_not_supported").classes("text-5xl text-gray-600")
            ui.label("Sem sessões em results/graficos_tese/.").classes("text-gray-500")
        return

    with ui.column().classes("w-full gap-4 p-4"):
        # ── Comparar treinos (métricas) ──────────────────────────────────────
        eval_sessions = data.sessions_with_eval()
        if len(eval_sessions) >= 1:
            with ui.card().classes(CARD):
                _section_title("compare_arrows", "Comparar treinos (métricas de avaliação)")
                ui.label("Escolhe dois treinos para comparar Ptask e recolhas por cenário. "
                         "Δ verde = B melhor que A.").classes("text-xs text-gray-400")
                default_a = eval_sessions[0]
                default_b = eval_sessions[1] if len(eval_sessions) > 1 else eval_sessions[0]
                with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                    cmp_a = ui.select(eval_sessions, value=default_a, label="Treino A") \
                        .props("outlined dense").classes("flex-1")
                    ui.icon("arrow_forward").classes("text-gray-500")
                    cmp_b = ui.select(eval_sessions, value=default_b, label="Treino B") \
                        .props("outlined dense").classes("flex-1")

                @ui.refreshable
                def tabela_cmp():
                    ma = data.session_metrics(cmp_a.value)
                    mb = data.session_metrics(cmp_b.value)
                    if ma is None and mb is None:
                        ui.label("Sem métricas para os treinos escolhidos.") \
                            .classes("text-gray-500")
                        return
                    ui.html(_comparison_html(ma or {}, mb or {})).classes("w-full mt-2")

                for el in (cmp_a, cmp_b):
                    el.on_value_change(lambda: tabela_cmp.refresh())
                tabela_cmp()

        with ui.card().classes(CARD):
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                _section_title("photo_library", "Galeria de resultados")
                contagem = ui.label("").classes("text-xs text-gray-400 ml-auto")
            with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                sess_a = ui.select(sessions, value=sessions[0], label="Sessão A") \
                    .props("outlined dense").classes("flex-1")
                sess_b = ui.select([NONE] + sessions, value=NONE, label="Sessão B (A/B)") \
                    .props("outlined dense").classes("flex-1")
                tipo = ui.select(["Todos"], value="Todos", label="Tipo") \
                    .props("outlined dense").classes("flex-1")
            busca = ui.input(placeholder="Pesquisar por nome ou título…") \
                .props("outlined dense clearable").classes("w-full mt-1")

        def _session_for(f: str, a_set: set, b_set: set):
            """Sessão de onde copiar o ficheiro (A tem prioridade)."""
            if f in a_set:
                return sess_a.value
            if f in b_set:
                return sess_b.value
            return None

        def _enviar(f: str, session: str):
            ok, msg = data.send_to_thesis(session, f)
            ui.notify(f"Enviado: {msg}" if ok else f"Falhou: {msg}",
                      type="positive" if ok else "negative")
            galeria.refresh()

        def _enviar_seccao(files: list, a_set: set, b_set: set):
            n = 0
            for f in files:
                s = _session_for(f, a_set, b_set)
                if s and data.send_to_thesis(s, f)[0]:
                    n += 1
            ui.notify(f"Enviados {n}/{len(files)} gráficos para a tese",
                      type="positive" if n else "warning")
            galeria.refresh()

        def _card_title(f: str):
            with ui.row().classes("w-full items-center no-wrap gap-1"):
                ui.label(_pretty_title(f)).classes("text-sm font-semibold text-sky-200 truncate")
                if data.is_in_thesis(f):
                    ui.icon("check_circle").classes("text-emerald-400 text-sm") \
                        .tooltip("Já está na tese")

        def _img_card(f: str, comparar: bool, a_set: set, b_set: set):
            with ui.card().classes("bg-slate-900/50 rounded-lg p-2"):
                _card_title(f)
                ui.label(f).classes("text-[10px] font-mono text-gray-500 truncate")
                if comparar:
                    with ui.row().classes("w-full gap-2 no-wrap"):
                        for s, tag, present in ((sess_a.value, "A", f in a_set),
                                                (sess_b.value, "B", f in b_set)):
                            with ui.column().classes("flex-1 gap-0 items-center"):
                                ui.badge(f"{tag} · {s}", color="primary") \
                                    .props("rounded").classes("text-[10px]")
                                if not present:
                                    ui.label("(não existe nesta sessão)") \
                                        .classes("text-xs text-gray-600 italic py-4")
                                else:
                                    ui.image(_url(s, f)).classes("w-full cursor-pointer") \
                                        .on("click", lambda _, s=s, f=f: open_zoom(s, f))
                else:
                    ui.image(_url(sess_a.value, f)).classes("w-full cursor-pointer") \
                        .on("click", lambda _, f=f: open_zoom(sess_a.value, f))
                send_s = _session_for(f, a_set, b_set)
                if send_s:
                    ui.button(icon="upload_file",
                              on_click=lambda f=f, s=send_s: _enviar(f, s)) \
                        .props("flat dense size=sm color=secondary") \
                        .classes("self-end -mt-1").tooltip("Enviar para a tese")

        @ui.refreshable
        def galeria():
            comparar = sess_b.value != NONE
            a_set = set(data.list_pngs(sess_a.value))
            b_set = set(data.list_pngs(sess_b.value)) if comparar else set()
            universo = sorted(a_set | b_set) if comparar else sorted(a_set)
            q = (busca.value or "").strip().lower()

            def _match(f):
                if tipo.value != "Todos" and data.graph_type(f) != tipo.value:
                    return False
                if q and q not in f.lower() and q not in _pretty_title(f).lower():
                    return False
                return True

            pngs = [f for f in universo if _match(f)]

            # Agrupa por tipo e desenha cada grupo como uma secção com cabeçalho.
            grupos = {}
            for f in pngs:
                grupos.setdefault(data.graph_type(f), []).append(f)
            contagem.text = f"{len(pngs)} gráficos · {len(grupos)} secções"
            if not pngs:
                ui.label("Nenhum gráfico para este filtro.").classes("text-gray-500")
                return
            ordem = [t for t in TYPE_ORDER if t in grupos] + \
                    [t for t in grupos if t not in TYPE_ORDER]
            cols = "1" if comparar else "3"
            for tname in ordem:
                files = grupos[tname]
                with ui.row().classes("items-center gap-2 w-full mt-4 mb-1 no-wrap"):
                    ui.icon(TYPE_ICON.get(tname, "image")).classes("text-sky-400 text-xl")
                    ui.label(tname).classes("text-base font-bold")
                    ui.badge(str(len(files)), color="primary").props("rounded")
                    ui.button("Enviar secção", icon="drive_folder_upload",
                              on_click=lambda fs=files: _enviar_seccao(fs, a_set, b_set)) \
                        .props("flat dense size=sm color=secondary").classes("ml-auto") \
                        .tooltip("Copiar todos estes gráficos para a tese")
                ui.separator().classes("opacity-30")
                with ui.grid().classes("w-full gap-3").style(
                        f"grid-template-columns: repeat({cols}, minmax(0, 1fr))"):
                    for f in files:
                        _img_card(f, comparar, a_set, b_set)

        def _refresh_tipos():
            files = set(data.list_pngs(sess_a.value))
            if sess_b.value != NONE:
                files |= set(data.list_pngs(sess_b.value))
            presentes = {data.graph_type(f) for f in files}
            opts = ["Todos"] + [t for t in TYPE_ORDER if t in presentes] + \
                   sorted(t for t in presentes if t not in TYPE_ORDER)
            tipo.set_options(opts, value=tipo.value if tipo.value in opts else "Todos")

        # filtros: trocar de sessão reconstrói os tipos disponíveis
        for el in (sess_a, sess_b):
            el.on_value_change(lambda: (_refresh_tipos(), galeria.refresh()))
        for el in (tipo, busca):
            el.on_value_change(lambda: galeria.refresh())
        _refresh_tipos()
        galeria()
