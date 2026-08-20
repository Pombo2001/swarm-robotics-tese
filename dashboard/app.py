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
    def _sec(titulo):
        """Cabeçalho de secção na barra lateral."""
        ui.label(titulo).classes("text-[10px] font-bold tracking-[.2em] px-2 pt-3 pb-1") \
            .style(f"color:{theme.INK_MUTED}")

    with ui.left_drawer(value=True, bordered=False).props("width=236").classes("p-3") as drawer:
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
                # "monitoring" só existe nos Material Symbols (conjunto novo); o
                # NiceGUI carrega os Material Icons clássicos, onde esse nome não
                # resolve — o separador ficava como o ÚNICO sem ícone. "insights"
                # existe nos dois conjuntos.
                # Em modo leitura este separador também não existe. Não é só
                # o painel do servidor que desaparece (esse já desaparecia, por
                # causa da password SSH): o que sobrava eram as curvas do último
                # treino LOCAL, na torre, sob o nome «Servidor», com
                # um aviso a mandar ver o treino a decorrer «na vista Servidor»,
                # que era aquela mesma. Um separador que não mostra o que promete
                # e remete para si próprio.
                t_monitor = None
                if not config.READONLY:
                    t_monitor = ui.tab("Servidor", icon="dns")
                    # O 3D do treino a decorrer é OPERAÇÃO, não prova: mostra o
                    # que está a correr agora, e só existe onde há treino.
                    t_aovivo = ui.tab("Ao vivo (3D)", icon="view_in_ar")

                # As doze entradas viviam todas sob um único rótulo «ANÁLISE»,
                # numa lista plana: os resultados repartidos por quatro vistas
                # sem ordem de leitura, quatro vistas de imagens, e o arquivo
                # das campanhas exploratórias ao mesmo nível dos números da
                # tese. Quem abre o link não tem por onde começar. Passam a
                # quatro secções que respondem a quatro perguntas diferentes —
                # o que a tese responde, como se defende, o que o prova, e o
                # percurso — sem que nenhuma vista mude ou desapareça.
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
                # A Prontidão é a checklist de trabalho de quem escreve a tese:
                # anuncia commits por enviar, testes por correr e se o PDF está
                # atrás do .tex. Publicada no Pi, é estado interno exposto a
                # quem abre o link — e lê-se como «isto tem problemas» quando
                # está apenas a fazer o seu trabalho. Fica na torre.
                t_pronto = None
                if not config.READONLY:
                    t_pronto = ui.tab("Prontidão", icon="checklist")
            ui.space()
            ui.separator()
            # Rodapé operacional: útil a trabalhar, ruído numa defesa (e no Modo
            # Defesa a letra maior partia-o em duas linhas). Ver theme.py.
            with ui.row().classes("items-center gap-2 px-2 pt-2 no-wrap op-footer"):
                ui.element("div").classes("live-dot live-dot--ok").style("width:6px;height:6px")
                # A porta vem do ambiente (o Pi corre na 8090 porque a 8080 está
                # ocupada pelo Pi-hole), e o rodapé tinha «:8080» em duro: no Pi
                # anunciava uma porta que não era a dele, ao lado de «servidor
                # local», que ali também não é verdade. Um rodapé que se engana
                # sobre onde está é o género de detalhe que quem vê o ecrã nota
                # e não diz.
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

    # ── Conteúdo ───────────────────────────────────────────────────────────────
    with ui.tab_panels(tabs, value=t_overview).classes("w-full bg-transparent"):
        with ui.tab_panel(t_overview).classes("p-0"):
            overview.build(queue, goto)
        if t_treinar is not None:
            with ui.tab_panel(t_treinar):
                treinar.build(queue)
        if t_monitor is not None:
            with ui.tab_panel(t_monitor):
                # O servidor PRIMEIRO: é onde os treinos correm de facto (a regra
                # do projeto é essa). As curvas locais vinham em cima e estavam
                # sempre obsoletas — o CSV mais recente tinha 4 dias —, o que
                # fazia a vista parecer avariada quando só estava a dizer a
                # verdade sobre uma máquina onde não se treina.
                # O painel do servidor pede a password SSH do ISCTE. Numa cópia
                # publicada isso é uma caixa de credenciais num site aberto.
                servidor.build()
                with ui.column().classes("w-full gap-4 p-4"):
                    curvas.build()
        with ui.tab_panel(t_ciencia):
            ciencia.build()
        with ui.tab_panel(t_mapa):
            mapa.build()
        with ui.tab_panel(t_escala):
            escala.build()
        with ui.tab_panel(t_proven):
            proveniencia.build()
        with ui.tab_panel(t_vitrine):
            vitrine.build()
        with ui.tab_panel(t_result):
            resultados.build()
        if t_pronto is not None:
            with ui.tab_panel(t_pronto):
                prontidao.build()
        with ui.tab_panel(t_defesa):
            defesa.build()
        with ui.tab_panel(t_videos):
            videos.build()
        with ui.tab_panel(t_viz3d):
            viz3d.build()
        if t_aovivo is not None:
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
    # A porta vem do ambiente: no Pi a 8080 já está ocupada (Pi-hole) e o serviço
    # corre na 8090. `show` abre o browser — o que faz sentido na torre e nenhum
    # num serviço systemd sem ecrã.
    ui.run(title="Swarm Observatory",
           port=int(os.environ.get("PORT", "8080")),
           reload=False,
           show=not config.READONLY)


if __name__ in {"__main__", "__mp_main__"}:
    main()
