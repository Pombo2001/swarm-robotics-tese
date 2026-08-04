"""Vista 'Resultados' (F3): galeria de gráficos com filtros, comparação A/B e
exportação direta para a tese.

As imagens são servidas pela rota estática '/graficos' (registada em app.py).
"""
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
NONE = "— (sem comparação)"

# Cenários e labels vêm de config (fonte única — ver dashboard/config.py).
SCEN_ORDER = config.MAIN_SCENARIO_KEYS
SCEN_LABEL = config.SCENARIO_LABEL_SHORT

# Ordem e ícone de cada secção da galeria (agrupa por tipo de gráfico).
# AVALIAÇÃO primeiro (é a métrica da tese), treino depois — a mesma hierarquia que o
# texto da dissertação usa. Os boxplots de treino ficam explicitamente rotulados para
# ninguém os citar como se fossem a eval determinística.
TYPE_ORDER = [
    # Dot plots antes dos boxplots: com n pequeno é a leitura honesta (uma caixa
    # cheia sugere densidade onde não há execução nenhuma).
    "Métricas de tarefa", "Dot plots (avaliação)", "Boxplots (avaliação)", "Escalabilidade",
    "Heatmaps de ocupação", "Heatmaps geodésicos", "Plantas dos cenários", "Painéis de vídeo",
    "Curvas por mapa", "Curvas por algoritmo", "Boxplots (treino)", "Outros",
]
TYPE_ICON = {
    "Métricas de tarefa": "leaderboard", "Dot plots (avaliação)": "scatter_plot",
    "Boxplots (avaliação)": "fact_check",
    "Escalabilidade": "open_in_full",
    "Heatmaps de ocupação": "grid_view", "Heatmaps geodésicos": "route",
    "Plantas dos cenários": "map",
    "Painéis de vídeo": "theaters",
    "Curvas por mapa": "stacked_line_chart", "Curvas por algoritmo": "show_chart",
    "Boxplots (treino)": "candlestick_chart", "Outros": "image",
}
# Prefixos conhecidos dos nomes de ficheiro (removidos para gerar o título).
_PREFIXES = ["comparacao_mapa", "curva_aprendizagem", "comparacao_barras",
             "heatmap_ocupacao", "heatmap_geodesico", "boxplot_por_algo",
             "desempenho_global", "taxa_sucesso", "recolhas", "dotplot_eval",
             "boxplot_eval", "boxplot"]


def _pretty_title(f: str) -> str:
    """'heatmap_ocupacao_gnn_u_wall.png' -> 'GNN · Muro em U' (título legível)."""
    name = f[:-4] if f.lower().endswith(".png") else f
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


_section_title = theme.section_title




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
        with ui.card().classes(CARD):
            _section_title("photo_library", "Galeria de resultados")
            with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                sess_a = ui.select(sessions, value=sessions[0], label="Sessão A") \
                    .props("outlined dense").classes("flex-1")
                sess_b = ui.select([NONE] + sessions, value=NONE, label="Sessão B (A/B)") \
                    .props("outlined dense").classes("flex-1")
                tipos = ["Todos"] + sorted({data.graph_type(f) for f in data.list_pngs(sessions[0])})
                tipo = ui.select(tipos, value="Todos", label="Tipo") \
                    .props("outlined dense").classes("flex-1")
            # Só em modo A/B. Por defeito a galeria mostra apenas os gráficos que
            # EXISTEM NAS DUAS sessões: cada fase do mega-treino treina um cenário
            # só, pelo que comparar duas quaisquer enchia o ecrã de "(não existe
            # nesta sessão)" — ruído que escondia as comparações verdadeiras.
            so_pares = ui.switch("Só o que existe em ambas", value=True) \
                .classes("mt-2").props("dense")
            so_pares.bind_visibility_from(sess_b, "value",
                                          backward=lambda v: v != NONE)

        def _img_card(f: str, comparar: bool, pngs_b: set):
            with ui.card().classes("bg-slate-900/50 rounded-lg p-2"):
                ui.label(_pretty_title(f)).classes("text-sm font-semibold text-sky-200")
                ui.label(f).classes("text-[10px] font-mono text-gray-500 truncate")
                if comparar:
                    with ui.row().classes("w-full gap-2 no-wrap"):
                        for s, tag in ((sess_a.value, "A"), (sess_b.value, "B")):
                            with ui.column().classes("flex-1 gap-0 items-center"):
                                ui.badge(f"{tag} · {s}", color="primary").props("rounded").classes("text-[10px]")
                                # o ficheiro pode não existir na sessão B
                                if tag == "B" and f not in pngs_b:
                                    ui.label("(não existe nesta sessão)") \
                                        .classes("text-xs text-gray-600 italic py-4")
                                else:
                                    ui.image(_url(s, f)).classes("w-full cursor-pointer") \
                                        .on("click", lambda _, s=s, f=f: open_zoom(s, f))
                else:
                    ui.image(_url(sess_a.value, f)).classes("w-full cursor-pointer") \
                        .on("click", lambda _, f=f: open_zoom(sess_a.value, f))

        @ui.refreshable
        def galeria():
            # Proveniência: que sessão está a ser mostrada, quantos artefactos tem e se
            # está completa. Sem isto, uma sessão incompleta parece uma sessão sem
            # resultados — e foi assim que os heatmaps do treino de 7 dias passaram por
            # inexistentes quando o launcher abria (por engano) uma campanha de junho.
            todos = data.list_pngs(sess_a.value)
            n_heat = len([f for f in todos if f.startswith("heatmap")])
            n_vid = len(data.list_videos(sess_a.value))
            theme.fonte(f"sessão {sess_a.value} · {len(todos)} gráficos "
                        f"({n_heat} heatmaps) · {n_vid} vídeos")

            pngs = [f for f in todos
                    if tipo.value == "Todos" or data.graph_type(f) == tipo.value]
            comparar = sess_b.value != NONE
            pngs_b = set(data.list_pngs(sess_b.value)) if comparar else set()

            if comparar:
                so_a = [f for f in pngs if f not in pngs_b]
                so_b = sorted(pngs_b - set(todos))
                if so_pares.value:
                    pngs = [f for f in pngs if f in pngs_b]
                if so_a or so_b:
                    partes = []
                    if so_a:
                        partes.append(f"{len(so_a)} só em A ({sess_a.value})")
                    if so_b:
                        partes.append(f"{len(so_b)} só em B ({sess_b.value})")
                    escondidos = ("escondidos" if so_pares.value
                                  else "mostrados com o lugar vazio")
                    theme.fonte(f"{' · '.join(partes)} — sem par, {escondidos}. "
                                "Campanhas diferentes treinam cenários diferentes; "
                                "a ausência de um gráfico aqui não é uma falha de "
                                "dados.")

            if not pngs:
                ui.label("Nenhum gráfico em comum para este filtro."
                         if comparar and so_pares.value
                         else "Nenhum gráfico para este filtro.") \
                    .classes("text-gray-500")
                return

            # Agrupa por tipo e desenha cada grupo como uma secção com cabeçalho.
            grupos = {}
            for f in pngs:
                grupos.setdefault(data.graph_type(f), []).append(f)
            ordem = [t for t in TYPE_ORDER if t in grupos] + \
                    [t for t in grupos if t not in TYPE_ORDER]
            cols = "1" if comparar else "3"
            for tname in ordem:
                files = grupos[tname]
                with ui.row().classes("items-center gap-2 w-full mt-4 mb-1"):
                    ui.icon(TYPE_ICON.get(tname, "image")).classes("text-sky-400 text-xl")
                    ui.label(tname).classes("text-base font-bold")
                    ui.badge(str(len(files)), color="primary").props("rounded")
                ui.separator().classes("opacity-30")
                with ui.grid().classes("w-full gap-3").style(
                        f"grid-template-columns: repeat({cols}, minmax(0, 1fr))"):
                    for f in files:
                        _img_card(f, comparar, pngs_b)

        def _tipos_da_sessao():
            """O seletor de tipo seguia sempre a PRIMEIRA sessão da lista.

            Ao mudar para uma campanha com outros tipos de gráfico, o seletor
            continuava a oferecer os tipos da primeira — opções que não davam
            resultado nenhum, e tipos existentes que não estavam na lista.
            """
            novos = ["Todos"] + sorted({data.graph_type(f)
                                        for f in data.list_pngs(sess_a.value)})
            tipo.options = novos
            if tipo.value not in novos:
                tipo.value = "Todos"
            tipo.update()

        # refrescar a galeria quando muda qualquer filtro
        sess_a.on_value_change(lambda: (_tipos_da_sessao(), galeria.refresh()))
        for el in (sess_b, tipo, so_pares):
            el.on_value_change(lambda: galeria.refresh())
        galeria()
