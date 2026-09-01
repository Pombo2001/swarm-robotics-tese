"""Observatório — dashboard NiceGUI da tese (entrypoint).

Executar:  python -m dashboard.app
Abre em http://localhost:8080 (e fica acessível na rede local).

Layout: tema monocromático noturno (preto e branco), barra lateral agrupada por
pergunta e a área principal com a vista selecionada. O estilo vive em
dashboard/theme.py (fonte única).

As secções, por ordem: OPERAÇÃO (só na torre — o que está a correr agora),
A TESE (o que a dissertação responde), DEFESA (como se apresenta e de onde vêm
os números), PROVAS (o material que os sustenta) e BASTIDORES (o percurso, e a
checklist de trabalho). A cópia publicada no Pi não tem OPERAÇÃO nem Prontidão.
"""
import os

from nicegui import ui, app

from . import config, theme
from .jobs import JobQueue
from .views import (overview, treinar, servidor, ciencia, resultados, curvas,
                    videos, aovivo, arquivo, proveniencia, prontidao,
                    defesa, mapa, escala, vitrine, viz3d)

# Fila partilhada (singleton): o treino continua independente do estado do browser.
queue = JobQueue()

# Serve os PNGs e GIFs das sessões de treino (vistas Resultados e Vídeos).
_graficos = os.path.join(config.BASE_DIR, "results", "graficos_tese")
if os.path.isdir(_graficos):
    app.add_static_files("/graficos", _graficos)

# JS do visualizador 3D e episódios exportados. O 3D do Ursina abre uma janela
# no ecrã de QUEM CORRE o servidor — inútil no Pi, que não tem monitor e serve
# pela internet. Estes dois caminhos deixam o desenho acontecer no browser.
_estatico = os.path.join(os.path.dirname(__file__), "estatico")
if os.path.isdir(_estatico):
    app.add_static_files("/estatico", _estatico)
_episodios = os.path.join(config.BASE_DIR, "results", "episodios_3d")
if os.path.isdir(_episodios):
    app.add_static_files("/episodios", _episodios)

# Figuras instaladas na tese (a vista Mapa usa a planta do mapa composto).
_fig_tese = os.path.join(config.BASE_DIR, "Tese", "images", "resultados")
if os.path.isdir(_fig_tese):
    app.add_static_files("/figuras_tese", _fig_tese)


@ui.page("/")
def index(v: str = ""):
    """Painel. `v` é a vista a abrir (ex.: `/?v=ciencia`) — ver `_percurso`.

    O separador vive no URL para o painel se poder MANDAR: sem isto, um link
    abria sempre na Overview e o destinatário tinha de ser instruído a navegar
    até onde interessava. É parâmetro de query e não fragmento (`#`) porque o
    fragmento nunca chega ao servidor — o separador inicial tem de ser decidido
    aqui, antes de a página ser desenhada.
    """
    theme.apply()

    # Header
    with ui.header(elevated=False).classes("items-center gap-3 px-4 py-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()) \
            .props('flat round dense color=white '
                   'aria-label="Mostrar ou esconder a navegação"')
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

    # Navegação (barra lateral, por fluxo de trabalho)
    def _sec(titulo):
        """Cabeçalho de secção na barra lateral."""
        ui.label(titulo).classes("text-[10px] font-bold tracking-[.2em] px-2 pt-3 pb-1") \
            .style(f"color:{theme.INK_MUTED}")

    # `show-if-above`: aberta em ecrã grande, fechada no telemóvel. Só com
    # `value=True`, o Quasar punha-a em overlay a tapar 60% de um ecrã de 390 px.
    with ui.left_drawer(value=True, bordered=False) \
            .props("width=236 show-if-above").classes("p-3") as drawer:
        with ui.column().classes("w-full gap-1 h-full"):
            with ui.tabs().props("vertical active-color=white indicator-color=white") \
                    .classes("w-full") as tabs:
                t_overview = ui.tab("Overview", icon="public")
                # Em modo leitura (a cópia publicada) não existe secção de
                # OPERAÇÃO: nem separador, nem painel, nem rota. Esconder só o
                # botão deixaria o painel construído e o trabalho a poder ser
                # lançado por quem soubesse o nome da vista.
                t_treinar = t_aovivo = None
                if not config.READONLY:
                    _sec("OPERAÇÃO")
                    t_treinar = ui.tab("Treinar", icon="rocket_launch")
                # Fora em modo leitura: sem o painel do servidor (password SSH),
                # sobravam curvas de um treino local sob o nome «Servidor», a
                # remeter para si próprio.
                t_monitor = None
                if not config.READONLY:
                    t_monitor = ui.tab("Servidor", icon="dns")
                    # O 3D do treino a decorrer é OPERAÇÃO, não prova: mostra o
                    # que está a correr agora, e só existe onde há treino.
                    t_aovivo = ui.tab("Ao vivo (3D)", icon="view_in_ar")

                # Quatro secções em vez de uma lista plana sob «ANÁLISE»: o que a
                # tese responde, como se defende, o que o prova, e o percurso.
                _sec("A TESE")
                t_ciencia = ui.tab("Ciência", icon="science")
                t_escala  = ui.tab("Escala e robustez", icon="groups")
                # Última: é a questão em aberto, e vem depois do que já fechou.
                t_mapa    = ui.tab("Mapa composto", icon="map")

                _sec("DEFESA")
                t_defesa  = ui.tab("Defesa", icon="record_voice_over")
                t_vitrine = ui.tab("Vitrine", icon="slideshow")
                # "De onde vem este número?" respondido em dois cliques, em vez
                # de procurado no REPRODUZIR.md com o júri à espera.
                t_proven  = ui.tab("Proveniência", icon="fact_check")

                _sec("PROVAS")
                t_result  = ui.tab("Galeria", icon="image")
                t_videos  = ui.tab("Vídeos", icon="smart_display")
                # Existe TAMBÉM em modo leitura: ao contrário do Ursina,
                # desenha no browser de quem vê, não no ecrã do servidor.
                t_viz3d   = ui.tab("Episódio 3D", icon="view_in_ar")

                _sec("BASTIDORES")
                t_arquivo = ui.tab("Arquivo", icon="history_edu")
                # Checklist interna (commits por enviar, PDF atrás do .tex).
                # No Pi lê-se como «isto tem problemas»; fica na torre.
                t_pronto = None
                if not config.READONLY:
                    t_pronto = ui.tab("Prontidão", icon="checklist")
            ui.space()
            ui.separator()
            # Os três sítios apontam uns para os outros de propósito: o painel
            # mostra tudo, a página resume, o repositório prova.
            _sec("TAMBÉM EM")
            with ui.column().classes("w-full gap-1 px-2"):
                for _rot, _icone, _url in (
                        ("Página de resultados", "language",
                         "https://pombo2001.github.io/swarm-robotics-tese/"),
                        ("Código no GitHub", "code",
                         "https://github.com/Pombo2001/swarm-robotics-tese")):
                    with ui.link(target=_url, new_tab=True).classes(
                            "no-underline flex items-center gap-2 py-1"):
                        ui.icon(_icone).classes("text-[15px]") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label(_rot).classes("text-[12px]") \
                            .style(f"color:{theme.INK_MUTED}")

            # Rodapé operacional: útil a trabalhar, ruído numa defesa (e no Modo
            # Defesa a letra maior partia-o em duas linhas). Ver theme.py.
            with ui.row().classes("items-center gap-2 px-2 pt-2 no-wrap op-footer"):
                ui.element("div").classes("live-dot live-dot--ok").style("width:6px;height:6px")
                # A porta vem do ambiente (o Pi corre na 8090, com a 8080 ocupada
                # pelo Pi-hole). Estava «:8080» em duro, e o Pi anunciava uma
                # porta que não era a dele.
                _porta = os.environ.get("PORT", "8080")
                _onde = "Raspberry Pi" if config.READONLY else "servidor local"
                ui.label(f"{_onde} · :{_porta}").classes("text-[11px] mono-num") \
                    .style(f"color:{theme.INK_MUTED}")

    # A Overview salta para outras vistas por nome (cartões de estado clicáveis).
    _by_name = {"treinar": t_treinar, "monitorizar": t_monitor,
                "ciencia": t_ciencia, "mapa": t_mapa,
                "escala": t_escala,
                "proveniencia": t_proven,
                "resultados": t_result, "prontidao": t_pronto,
                "defesa": t_defesa,
                "videos": t_videos, "viz3d": t_viz3d,
                "aovivo": t_aovivo, "arquivo": t_arquivo}

    def goto(name: str):
        tab = _by_name.get(name)
        if tab is not None:
            tabs.set_value(tab)


    # Rodapé de navegação
    # A ordem da barra lateral. As entradas que não existem em modo leitura
    # entram a None e caem fora, senão o Pi teria setas para painéis inexistentes.
    # O 3.º campo vai para o URL (`/?v=ciencia`): sem acentos nem espaços.
    _percurso = [(t, r, s) for t, r, s in (
        (t_overview, "Overview",           "overview"),
        (t_treinar,  "Treinar",            "treinar"),
        (t_monitor,  "Servidor",           "servidor"),
        (t_aovivo,   "Ao vivo (3D)",       "aovivo"),
        (t_ciencia,  "Ciência",            "ciencia"),
        (t_escala,   "Escala e robustez",  "escala"),
        (t_mapa,     "Mapa composto",      "mapa"),
        (t_defesa,   "Defesa",             "defesa"),
        (t_vitrine,  "Vitrine",            "vitrine"),
        (t_proven,   "Proveniência",       "proveniencia"),
        (t_result,   "Galeria",            "galeria"),
        (t_videos,   "Vídeos",             "videos"),
        (t_viz3d,    "Episódio 3D",        "episodio3d"),
        (t_arquivo,  "Arquivo",            "arquivo"),
        (t_pronto,   "Prontidão",          "prontidao"),
    ) if t is not None]

    # Vista pedida no URL. Um nome desconhecido — ou o de uma vista que não
    # existe nesta cópia (`/?v=treinar` no Pi) — cai na Overview em vez de dar
    # erro: o link pode vir de alguém que só conhece a versão da torre.
    _inicial = t_overview
    for _t, _r, _s in _percurso:
        if _s == v.strip().lower():
            _inicial = _t
            break

    def _ir_para(tab):
        tabs.set_value(tab)
        # Sem isto, saltar de um painel longo (a Galeria) para o seguinte deixa
        # a página a meio do scroll do anterior — abre-se já lá para baixo.
        ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'})")

    def _url_segue_separador(e):
        """Mantém o `?v=` a par do separador aberto.

        `replaceState` e não `pushState`: mudar de vista não é navegar para
        outra página, e empilhar histórico faria o botão «voltar» do browser
        percorrer separadores um a um em vez de sair do painel.
        """
        for tab, rotulo, slug in _percurso:
            # `tabs.value` tanto pode ser o elemento (quando o código chama
            # `set_value`) como o nome (quando é o utilizador a clicar).
            if e.value is tab or e.value == rotulo:
                ui.run_javascript(
                    "history.replaceState(null, '', '?v=%s')" % slug)
                return

    tabs.on_value_change(_url_segue_separador)

    def _rodape_nav(atual):
        """Rodapé «← anterior / continuar para →» no fim de um painel.

        Ler o painel de ponta a ponta obrigava a voltar à barra lateral em cada
        vista e a lembrar-se de qual era a próxima. As pontas do percurso levam
        só uma seta: a primeira vista não tem anterior, a última não tem
        seguinte. O `div` vazio ocupa o lugar da seta que falta — sem ele, o
        `justify-between` com um só filho encostava o «seguinte» à esquerda.
        """
        nomes = [t for t, _r, _s in _percurso]
        pos = nomes.index(atual)
        ant = _percurso[pos - 1] if pos > 0 else None
        prox = _percurso[pos + 1] if pos + 1 < len(_percurso) else None
        if ant is None and prox is None:
            return
        with ui.row().classes(
                "w-full items-center justify-between pt-8 pb-2 px-4"):
            if ant is not None:
                # `color=None`: sem isto o NiceGUI põe color='primary' e a
                # classe do Quasar ganha ao .style() — o «anterior» saía tão
                # destacado como o «seguinte», quando é o caminho secundário.
                voltar = ui.button(ant[1], color=None,
                                   on_click=lambda t=ant[0]: _ir_para(t))
                voltar.props("flat dense no-caps icon=arrow_back")
                voltar.classes("text-[13px]")
                voltar.style(f"color:{theme.INK_MUTED}")
            else:
                ui.element("div")
            if prox is not None:
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.label("continuar para") \
                        .classes("text-[11px]") \
                        .style(f"color:{theme.INK_MUTED}")
                    seguir = ui.button(prox[1],
                                       on_click=lambda t=prox[0]: _ir_para(t))
                    seguir.props("flat dense no-caps color=white "
                                 "icon-right=arrow_forward")
                    seguir.classes("text-[13px]")
            else:
                ui.element("div")

    # Conteúdo
    with ui.tab_panels(tabs, value=_inicial).classes("w-full bg-transparent"):
        with ui.tab_panel(t_overview).classes("p-0"):
            overview.build(queue, goto)
            _rodape_nav(t_overview)
        if t_treinar is not None:
            with ui.tab_panel(t_treinar):
                treinar.build(queue)
                _rodape_nav(t_treinar)
        if t_monitor is not None:
            with ui.tab_panel(t_monitor):
                # O servidor PRIMEIRO: é onde os treinos correm. As curvas locais
                # em cima estavam sempre obsoletas e a vista parecia avariada.
                # (Pede a password SSH do ISCTE — daí não existir no Pi.)
                servidor.build()
                with ui.column().classes("w-full gap-4 p-4"):
                    curvas.build()
                _rodape_nav(t_monitor)
        with ui.tab_panel(t_ciencia):
            ciencia.build()
            _rodape_nav(t_ciencia)
        with ui.tab_panel(t_mapa):
            mapa.build()
            _rodape_nav(t_mapa)
        with ui.tab_panel(t_escala):
            escala.build()
            _rodape_nav(t_escala)
        with ui.tab_panel(t_proven):
            proveniencia.build()
            _rodape_nav(t_proven)
        with ui.tab_panel(t_vitrine):
            vitrine.build()
            _rodape_nav(t_vitrine)
        with ui.tab_panel(t_result):
            resultados.build()
            _rodape_nav(t_result)
        if t_pronto is not None:
            with ui.tab_panel(t_pronto):
                prontidao.build()
                _rodape_nav(t_pronto)
        with ui.tab_panel(t_defesa):
            defesa.build()
            _rodape_nav(t_defesa)
        with ui.tab_panel(t_videos):
            videos.build()
            _rodape_nav(t_videos)
        with ui.tab_panel(t_viz3d):
            viz3d.build()
            _rodape_nav(t_viz3d)
        if t_aovivo is not None:
            with ui.tab_panel(t_aovivo):
                aovivo.build()
                _rodape_nav(t_aovivo)
        with ui.tab_panel(t_arquivo):
            arquivo.build()
            _rodape_nav(t_arquivo)

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
    # A porta vem do ambiente: no Pi a 8080 já está ocupada (Pi-hole) e o serviço
    # corre na 8090. `show` abre o browser — o que faz sentido na torre e nenhum
    # num serviço systemd sem ecrã.
    ui.run(title="Swarm Observatory",
           port=int(os.environ.get("PORT", "8080")),
           reload=False,
           show=not config.READONLY)


if __name__ in {"__main__", "__mp_main__"}:
    main()
