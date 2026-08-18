"""Vista 'Resultados' (F3): galeria de gráficos com filtros, comparação A/B e
exportação direta para a tese.

As imagens são servidas pela rota estática '/graficos' (registada em app.py).
"""
from nicegui import ui

from .. import config, data, theme
from . import ranking

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
        # O cenário pode estar colado a um prefixo que esta função não conhece:
        # `painel_videos_none` dava «Painel Videos None» em dez figuras da
        # galeria — e `none` é o Sandbox, o cenário de referência da tese. Um
        # título que diz «None» parece um erro do gráfico quando é só do nome do
        # ficheiro. Procura-se o cenário no FIM (chaves longas primeiro, senão
        # `cooperative_door` engolia `cooperative_door_bypass`).
        cen = next((c for c in sorted(SCEN_LABEL, key=len, reverse=True)
                    if rest.endswith("_" + c)), None)
        if cen:
            cabeca = rest[:-len(cen) - 1].replace("_", " ").strip()
            if cabeca:
                bits.append(cabeca.title())
            bits.append(SCEN_LABEL[cen])
        else:
            bits.append(rest.replace("_", " ").title())
    return " · ".join(bits) if bits else name


_section_title = theme.section_title




def _url(session: str, filename: str) -> str:
    return f"/graficos/{session}/{filename}"


def _opcoes_de_sessao(sessions):
    """As campanhas do seletor, **as da tese primeiro**.

    A galeria abria na campanha mais RECENTE por data — que a 18 de agosto é o
    mapa grande, um cenário à parte cujos gráficos são de $0$ a $10$ recolhas.
    Quem abrisse a vista via o resultado mais atípico do projeto como se fosse o
    principal, e as sete campanhas que a dissertação cita ficavam a meio de uma
    lista de 48 nomes de pasta.

    A ordem passa a ser: as **canónicas** (as que a tese cita), depois as
    exploratórias por data. O rótulo diz o que a pasta é — `mega_A1` não o diz.
    """
    canonicas, resto = [], []
    for s in sessions:
        rot, canon = data.rotulo_campanha(s)
        # A descrição diz o que a pasta é (cenário, execuções, data); o rótulo
        # sozinho não distingue `mega_A1` de `mega_A2`, que são o braço com
        # novidade adaptativa e o braço de controlo do mesmo cenário.
        desc = data.condicao_da_campanha(s) or data.descricao_sessao(s)
        etiqueta = "%s%s%s" % ("★ " if canon else "", rot,
                               ("  ·  %s" % desc) if desc else "")
        (canonicas if canon else resto).append((s, etiqueta))
    # Entre as canónicas, a campanha final vem primeiro: é a que produz as
    # tabelas da dissertação. O mapa composto vai para o fim das canónicas — é
    # um cenário à parte, e abrir a galeria nele mostra o resultado mais atípico
    # do projeto como se fosse o principal.
    ordem = {"final_7d": 0, "eval_7d": 1, "mega_treino": 2, "mapa_grande": 9}
    canonicas.sort(key=lambda sv: (ordem.get(sv[0], 5), sv[0]))
    ordenadas = canonicas + resto
    return {s: e for s, e in ordenadas}, (ordenadas[0][0] if ordenadas else None)


# As comparações que valem a pena ver lado a lado, e porquê. Cada uma preenche
# A e B de uma vez: escolher duas campanhas certas num seletor de 48 pastas
# exige saber de cor o que cada nome significa — que é o problema que o painel
# do melhor treino já resolvia para uma campanha só.
COMPARACOES = (
    ("Novidade adaptativa vs objetivo puro", "mega_A1", "mega_A2",
     "o resultado central da QI6, a n=28: 28/28 execuções contra 15/28"),
    ("Evolutivo vs PPO no Muro em U", "mega_A1", "mega_A3",
     "o mesmo cenário, o mesmo n, o outro paradigma"),
    ("Campanha final vs mapa composto", "final_7d", "mapa_grande",
     "o que a composição de dificuldades degrada (QI7)"),
)


def build():
    sessions = data.list_sessions()

    def open_zoom(session: str, filename: str):
        with ui.dialog() as dlg, ui.card().classes("max-w-[90vw]"):
            ui.label(filename).classes("text-sm font-mono text-gray-300")
            na_tese = data.figura_na_tese(session, filename)
            if na_tese:
                ui.label(f"Está na dissertação como images/{na_tese}") \
                    .classes("text-xs text-emerald-300")
            else:
                # Dizer que NÃO está é tão útil como dizer que está: é o aviso
                # de que carregar em «Enviar para a Tese» muda mesmo o PDF.
                ui.label("Não está na dissertação (ou a cópia lá dentro já "
                         "divergiu desta).").classes("text-xs text-amber-300")
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
            opcoes, primeira = _opcoes_de_sessao(sessions)
            with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                sess_a = ui.select(opcoes, value=primeira, label="Sessão A") \
                    .props("outlined dense").classes("flex-1")
                opcoes_b = {NONE: NONE}
                opcoes_b.update(opcoes)
                sess_b = ui.select(opcoes_b, value=NONE, label="Sessão B (A/B)") \
                    .props("outlined dense").classes("flex-1")
                tipos = ["Todos"] + sorted({data.graph_type(f)
                                            for f in data.list_pngs(primeira)})
                tipo = ui.select(tipos, value="Todos", label="Tipo") \
                    .props("outlined dense").classes("flex-1")

            # Comparações prontas: um clique põe as duas campanhas certas nos
            # seletores. Sem isto, ver o resultado central da QI6 lado a lado
            # exigia saber que ele vive em `mega_A1` e `mega_A2`.
            existentes = set(sessions)
            prontas = [c for c in COMPARACOES
                       if c[1] in existentes and c[2] in existentes]
            if prontas:
                with ui.row().classes("w-full gap-2 items-center mt-2 flex-wrap"):
                    ui.label("Comparações que valem a pena:") \
                        .classes("text-[11px] uppercase tracking-wide text-gray-500")
                    for rot, a, b, porque in prontas:
                        def _por(a=a, b=b):
                            sess_a.value, sess_b.value = a, b
                        ui.button(rot, on_click=_por) \
                            .props("flat dense no-caps color=secondary") \
                            .classes("text-[12px]").tooltip(porque)
            # Só em modo A/B. Por defeito a galeria mostra apenas os gráficos que
            # EXISTEM NAS DUAS sessões: cada fase do mega-treino treina um cenário
            # só, pelo que comparar duas quaisquer enchia o ecrã de "(não existe
            # nesta sessão)" — ruído que escondia as comparações verdadeiras.
            so_pares = ui.switch("Só o que existe em ambas", value=True) \
                .classes("mt-2").props("dense")
            so_pares.bind_visibility_from(sess_b, "value",
                                          backward=lambda v: v != NONE)
            # ⚠️ Os dois lados são PNG independentes, cada um com o eixo que o
            # matplotlib lhe deu: no par A1/A2 o eixo da esquerda vai a 80 e o da
            # direita a 60, e as duas barras parecem mais próximas do que são.
            # Quem compara alturas lê o gráfico errado; os números certos estão
            # na tabela do melhor treino, aqui em cima.
            aviso_escala = ui.label(
                "As duas imagens são independentes — as escalas dos eixos podem "
                "não ser as mesmas. Comparar os valores, não a altura das barras."
            ).classes("text-[11px] text-amber-300/80 mt-1")
            aviso_escala.bind_visibility_from(sess_b, "value",
                                              backward=lambda v: v != NONE)
            # Das 1099 figuras da galeria, umas dezenas é que estão mesmo na
            # dissertação, e nada as distinguia: para mostrar uma a alguém era
            # preciso saber de cor quais entraram.
            so_tese = ui.switch("Só as que estão na dissertação", value=False) \
                .classes("mt-1").props("dense")

        # Qual destas 48 campanhas vale alguma coisa? O seletor em cima não o
        # dizia, e os nomes das pastas (`mega_A1`, `09-07-2026_12h52m`) também
        # não. O painel responde por cenário e realça a campanha escolhida, para
        # se ver onde ela cai — ou que não tem avaliação nenhuma.
        alvo_ranking = ui.column().classes("w-full")

        def _mostrar(campanha):
            """Clicar numa linha do ranking abre as imagens desse treino."""
            if campanha not in sessions:
                # Uma campanha pode ter avaliação e não ter pasta de figuras
                # (o `eval_7d` é o caso). Dizer porquê é melhor do que um
                # clique que não faz nada.
                ui.notify("«%s» tem avaliação mas não tem figuras próprias "
                          "nesta galeria." % campanha, type="warning")
                return

            # Os filtros ficavam os do treino ANTERIOR e podiam esconder tudo o
            # que este tem: o clique dava uma galeria vazia, que se lê como
            # «esta campanha não tem gráficos». Tem — o filtro é que não a
            # deixava passar. Quem carrega na tabela quer VER o treino, por isso
            # o filtro que o esconderia por inteiro é desligado, e diz-se qual.
            pngs = data.list_pngs(campanha)
            largados = []
            if tipo.value != "Todos" and not any(data.graph_type(f) == tipo.value
                                                 for f in pngs):
                tipo.set_value("Todos")
                largados.append("tipo")
            if so_tese.value and not any(data.figura_na_tese(campanha, f)
                                         for f in pngs):
                so_tese.set_value(False)
                largados.append("só na dissertação")

            # A notificação vem ANTES de trocar a sessão: trocá-la redesenha o
            # ranking, o que apaga a própria linha em que se carregou — e
            # notificar a partir de um elemento já apagado rebenta com
            # RuntimeError («parent slot has been deleted»), que matava o
            # servidor a meio do clique.
            msg = "Galeria: %s" % data.rotulo_campanha(campanha)[0]
            if largados:
                msg += " · filtro «%s» desligado (escondia tudo)" % \
                       "» e «".join(largados)
            ui.notify(msg, type="positive", position="top")
            sess_a.set_value(campanha)

        def _desenhar_ranking():
            alvo_ranking.clear()
            with alvo_ranking:
                ranking.painel(campanha_atual=sess_a.value,
                               ao_escolher=_mostrar, escolhiveis=set(sessions))

        _desenhar_ranking()
        sess_a.on_value_change(lambda _: _desenhar_ranking())

        def _selo_tese(session: str, f: str):
            """Marca a figura que a dissertação usa DE FACTO.

            Compara-se conteúdo, não nome: as figuras da tese são cópias das da
            campanha e já derivaram em silêncio uma vez (8 delas, até 21 jul).
            Uma figura regenerada e ainda não copiada deixa de ter selo — que é
            a resposta certa, porque já não é a que está no PDF.
            """
            rel = data.figura_na_tese(session, f)
            if rel:
                ui.badge("na dissertação", color="positive").props("rounded") \
                    .classes("text-[10px]").tooltip(f"images/{rel}")

        def _img_card(f: str, comparar: bool, pngs_b: set):
            with ui.card().classes("bg-slate-900/50 rounded-lg p-2"):
                with ui.row().classes("w-full items-center gap-2 no-wrap"):
                    ui.label(_pretty_title(f)).classes("text-sm font-semibold text-sky-200")
                    if not comparar:
                        _selo_tese(sess_a.value, f)
                ui.label(f).classes("text-[10px] font-mono text-gray-500 truncate")
                if comparar:
                    with ui.row().classes("w-full gap-2 no-wrap"):
                        for s, tag in ((sess_a.value, "A"), (sess_b.value, "B")):
                            with ui.column().classes("flex-1 gap-0 items-center"):
                                ui.badge(f"{tag} · {s}", color="primary").props("rounded").classes("text-[10px]")
                                # O selo é por lado: em A/B o mesmo nome pode ser
                                # a figura que está no PDF de um lado e uma versão
                                # antiga do outro.
                                if not (tag == "B" and f not in pngs_b):
                                    _selo_tese(s, f)
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
            n_tese = len([f for f in todos if data.figura_na_tese(sess_a.value, f)])
            theme.fonte(f"sessão {sess_a.value} · {len(todos)} gráficos "
                        f"({n_heat} heatmaps · {n_tese} na dissertação) · "
                        f"{n_vid} vídeos")

            pngs = [f for f in todos
                    if tipo.value == "Todos" or data.graph_type(f) == tipo.value]
            if so_tese.value:
                pngs = [f for f in pngs if data.figura_na_tese(sess_a.value, f)]
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
                if so_tese.value:
                    msg = ("Nenhum gráfico desta campanha está na dissertação. "
                           "A maioria das figuras do PDF vem do treino de 7 dias.")
                elif comparar and so_pares.value:
                    msg = "Nenhum gráfico em comum para este filtro."
                else:
                    msg = "Nenhum gráfico para este filtro."
                ui.label(msg).classes("text-gray-500")
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
        for el in (sess_b, tipo, so_pares, so_tese):
            el.on_value_change(lambda: galeria.refresh())
        galeria()
