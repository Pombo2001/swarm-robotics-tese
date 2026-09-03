"""Vista «Apresentação» — o melhor treino de cada mapa, um ecrã de cada vez.

Porque existe
A Galeria e os Vídeos mostram tudo, e é isso que se quer quando se procura uma
prova. Numa sala, com o relógio a andar, a pergunta é outra: «neste mapa, qual
foi o melhor, e como se vê?». Esta vista responde-a oito vezes — um ecrã por
cenário — com o vídeo do treino vencedor de um lado, as três figuras que o
sustentam do outro, e a frase que se diz com o mapa no ecrã.

Quem decide o vencedor é o ranking do dashboard (`data.ranking_por_cenario`),
com a regra da tese: compara-se dentro do cenário, só campanhas com avaliação
determinística, e a unidade é a campanha e não a execução. Esta vista não tem
lista própria de treinos; se o ranking mudar, muda com ele. O que vem do
`configs/apresentacao.yaml` é só a frase.

O vídeo e o episódio 3D são do MESMO treino: os episódios de
`results/episodios_3d/apresentacao/` trazem a campanha no meta, e um episódio
de outra campanha aparece como tal, nunca em silêncio — mostrar o modelo da
campanha final com o rótulo do adaptativo seria mentir com um vídeo.

Navegação: setas do teclado (só com este separador aberto) ou os botões.
"""
import json
import os

import yaml
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-5"
_YAML = os.path.join(config.BASE_DIR, "configs", "apresentacao.yaml")
DIR_EPISODIOS = os.path.join(config.BASE_DIR, "results", "episodios_3d", "apresentacao")
_ALTURA_MEDIA = "clamp(280px,54vh,680px)"

# O app.py liga isto quando o separador está aberto: o `ui.keyboard` é da
# página inteira, e sem o guarda as setas mudavam de mapa aqui enquanto se
# navegava na Defesa.
ATIVA = {"v": False}

# (ficheiro na pasta da campanha, título curto). O algoritmo entra no nome do
# heatmap; o dot plot e a curva são do cenário e mostram os três.
FIGURAS = (
    ("dotplot_eval_{cen}.png", "Fiabilidade entre execuções"),
    ("heatmap_ocupacao_{algo}_{cen}.png", "Ocupação do espaço"),
    ("comparacao_mapa_{cen}.png", "Curvas de treino"),
)


def frases():
    """{cenário: frase} do apresentacao.yaml; {} se faltar."""
    if not os.path.exists(_YAML):
        return {}
    with open(_YAML, encoding="utf-8") as fh:
        itens = (yaml.safe_load(fh) or {}).get("cenarios", []) or []
    return {it["cenario"]: (it.get("frase") or "").strip()
            for it in itens if it.get("cenario")}


def vencedor(cenario: str):
    """A linha do ranking que ganhou este cenário, ou None."""
    linhas = data.ranking_por_cenario().get(cenario, [])
    return linhas[0] if linhas else None


def cenarios_com_vencedor():
    return [c for c in config.SCENARIO_KEYS if vencedor(c)]


def _url_fig(campanha: str, ficheiro: str):
    p = os.path.join(data.GRAFICOS_DIR, campanha, ficheiro)
    return "/graficos/%s/%s" % (campanha, ficheiro) if os.path.exists(p) else None


def video(campanha: str, algo: str, cenario: str):
    """(url, campanha de onde vem) do GIF, ou (None, None).

    O ranking pode escolher a pasta agregada de uma campanha (o F2 do mapa
    composto junta três streams) e o GIF estar numa das pastas de origem —
    `sessoes_com_video` cobre isso, e a origem fica escrita.
    """
    fn = data.video_for(campanha, algo, cenario)
    if fn:
        return "/graficos/%s/videos/%s" % (campanha, fn), campanha
    for s in data.sessoes_com_video(algo, cenario):
        if data._ALIAS.get(s, s) == campanha:
            return "/graficos/%s/videos/%s" % (s, data.video_for(s, algo, cenario)), s
    return None, None


def episodio(campanha: str, algo: str, cenario: str):
    """(url, é do treino vencedor) do episódio 3D, ou (None, False).

    Primeiro o exportado para a Apresentação com a campanha certa no meta;
    senão o genérico do «Episódio 3D» (modelos ativos), marcado como tal.
    """
    nome = "%s_%s.json" % (algo, cenario)
    p = os.path.join(DIR_EPISODIOS, nome)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                meta = json.load(fh).get("meta", {})
        except Exception:                                    # noqa: BLE001
            meta = {}
        origem = data._ALIAS.get(meta.get("campanha", ""), meta.get("campanha", ""))
        if origem == campanha:
            return "/episodios/apresentacao/" + nome, True
    generico = os.path.join(config.BASE_DIR, "results", "episodios_3d", nome)
    if os.path.exists(generico):
        return "/episodios/" + nome, campanha == "final_7d"
    return None, False


def _js_viz3d():
    js = os.path.join(os.path.dirname(os.path.dirname(__file__)), "estatico", "viz3d.js")
    v = int(os.path.getmtime(js)) if os.path.exists(js) else 0
    ui.add_head_html('<script src="/estatico/viz3d.js?v=%d"></script>' % v)


def build():
    cens = cenarios_com_vencedor()
    textos = frases()
    if not cens:
        with ui.column().classes("w-full p-4"):
            ui.label("Sem campanhas avaliadas: não há treino vencedor para mostrar.") \
                .classes("text-sm")
        return
    _js_viz3d()

    estado = {"i": 0, "media": "Vídeo"}

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("items-center gap-3 w-full no-wrap"):
            theme.section_title("co_present", "Apresentação",
                                "o melhor treino de cada mapa · setas do teclado para navegar")
            ui.space()
            pontos = ui.row().classes("items-center gap-1 no-wrap")
            passos = ui.label("").classes("text-xs mono-num ml-3") \
                .style(f"color:{theme.INK_MUTED}")

        alvo = ui.column().classes("w-full")

        def _pontos():
            pontos.clear()
            with pontos:
                for j, c in enumerate(cens):
                    ativo = (j == estado["i"])
                    p = ui.element("div").style(
                        "width:%s;height:8px;border-radius:4px;cursor:pointer;background:%s"
                        % ("22px" if ativo else "8px",
                           theme.INK if ativo else "rgba(255,255,255,.22)"))
                    p.tooltip(config.SCENARIO_LABEL_SHORT.get(c, c))
                    theme.clicavel(p, lambda _, j=j: ir(j),
                                   "Ir para %s" % config.SCENARIO_LABEL_SHORT.get(c, c))

        def _media(cen, v, campanha, algo):
            """O vídeo ou o 3D do treino vencedor, no mesmo espaço."""
            if estado["media"] == "Vídeo":
                url, origem = video(campanha, algo, cen)
                if url:
                    ui.image(url).classes("w-full rounded-xl bg-black/30") \
                        .style(f"height:{_ALTURA_MEDIA};object-fit:contain") \
                        .props("decoding=async")
                    if origem != campanha:
                        ui.label("vídeo gravado no stream %s desta campanha"
                                 % data.rotulo_campanha(origem)[0]) \
                            .classes("text-[11px]").style(f"color:{theme.INK_MUTED}")
                else:
                    with ui.column().classes("w-full items-center justify-center") \
                            .style(f"height:{_ALTURA_MEDIA}"):
                        ui.icon("videocam_off").classes("text-4xl") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label("este treino não gravou vídeo").classes("text-xs") \
                            .style(f"color:{theme.INK_MUTED}")
                return
            url, proprio = episodio(campanha, algo, cen)
            if not url:
                with ui.column().classes("w-full items-center justify-center") \
                        .style(f"height:{_ALTURA_MEDIA}"):
                    ui.icon("view_in_ar").classes("text-4xl").style(f"color:{theme.INK_MUTED}")
                    ui.label("sem episódio 3D exportado para este treino") \
                        .classes("text-xs").style(f"color:{theme.INK_MUTED}")
                    ui.label("python scripts/exportar_episodio_3d.py --algo %s --cenario %s "
                             "--subpasta apresentacao --campanha %s" % (algo, cen, campanha)) \
                        .classes("text-[10px] mono-num").style(f"color:{theme.INK_MUTED}")
                return
            # O canvas traz o episódio no `data-ep`: o viz3d.js arranca-o sozinho
            # quando o vê aparecer no DOM (ver autoArranque), sem `run_javascript`.
            ui.html('<canvas id="apres_canvas_%s" data-ep="%s" data-estado="apres_estado_%s" '
                    'style="width:100%%;height:%s;display:block;border-radius:12px;'
                    'background:#0b0e11"></canvas>' % (cen, url, cen, _ALTURA_MEDIA))
            with ui.row().classes("items-center gap-3 no-wrap w-full"):
                ui.label("").classes("text-xs mono-num").props('id=apres_estado_%s' % cen) \
                    .style(f"color:{theme.INK_MUTED}")
                ui.space()
                ui.label("arrasta para rodar · roda do rato para aproximar") \
                    .classes("text-[11px]").style(f"color:{theme.INK_MUTED}")
            if not proprio:
                ui.label("⚠ episódio dos modelos ativos (campanha final), não deste treino") \
                    .classes("text-[11px]").style("color:#d97706")

        def desenhar():
            cen = cens[estado["i"]]
            v = vencedor(cen)
            campanha, algo = v["campanha"], v["algo"].lower()
            meta_algo = config.ALGO_META.get(v["algo"], {})
            cor = meta_algo.get("color", theme.INK)
            rot_campanha = data.rotulo_campanha(campanha)[0]
            passos.text = "%d de %d" % (estado["i"] + 1, len(cens))
            _pontos()
            alvo.clear()
            with alvo, ui.card().classes(CARD + " w-full"):
                # Cabeçalho: o mapa, quem ganhou e com quanto.
                with ui.row().classes("w-full items-end gap-4 no-wrap flex-wrap"):
                    with ui.column().classes("gap-0"):
                        ui.label("CENÁRIO %d" % (config.SCENARIO_KEYS.index(cen) + 1)) \
                            .classes("text-[10px] font-bold tracking-[.25em]") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label(config.SCENARIO_LABEL_BY_KEY.get(cen, cen)) \
                            .classes("text-2xl font-bold mono-title leading-tight")
                    ui.space()
                    with ui.column().classes("gap-0 items-end"):
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.element("div").style(
                                f"width:10px;height:10px;border-radius:50%;background:{cor}")
                            ui.label("%s · %s" % (meta_algo.get("label", v["algo"]), rot_campanha)) \
                                .classes("text-sm font-bold").style(f"color:{cor}")
                        conv = ("%d/%d execuções a 100 %%" % (v["convergentes"], v["runs"])
                                if v.get("convergentes") is not None else "")
                        ui.label("%s rec/ep · %s" % (theme.num(v["recolhas"]), conv)) \
                            .classes("text-xs mono-num").style(f"color:{theme.INK_MUTED}")

                # Corpo: media à esquerda, as três figuras à direita.
                with ui.grid().classes("w-full gap-4 mt-3").style(
                        "grid-template-columns:minmax(0,11fr) minmax(0,9fr)"):
                    with ui.column().classes("gap-2").style("min-width:0"):
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            tog = ui.toggle(["Vídeo", "Episódio 3D"], value=estado["media"]) \
                                .props("no-caps dense")
                        media = ui.column().classes("w-full gap-1").style("min-width:0")
                        with media:
                            _media(cen, v, campanha, algo)

                        def _muda_media(e):
                            estado["media"] = e.value
                            media.clear()
                            with media:
                                _media(cen, v, campanha, algo)
                        tog.on_value_change(_muda_media)

                    with ui.column().classes("gap-3").style("min-width:0"):
                        with ui.grid(columns=2).classes("w-full gap-3") \
                                .style("grid-template-columns:repeat(2,minmax(0,1fr))"):
                            for padrao, titulo in FIGURAS[:2]:
                                _figura(campanha, padrao.format(cen=cen, algo=algo), titulo)
                        padrao, titulo = FIGURAS[2]
                        _figura(campanha, padrao.format(cen=cen, algo=algo), titulo)

                # A frase.
                frase = textos.get(cen)
                if frase:
                    ui.label(frase).classes("text-lg leading-snug mt-4 pl-4") \
                        .style(f"border-left:3px solid {cor}")
                else:
                    ui.label("· sem frase para este cenário em configs/apresentacao.yaml") \
                        .classes("text-xs mt-4").style(f"color:{theme.INK_MUTED}")
                theme.fonte("%s · ranking por recolhas/ep, avaliação determinística"
                            % campanha)

        def _figura(campanha, ficheiro, titulo):
            url = _url_fig(campanha, ficheiro)
            with ui.column().classes("gap-1 w-full").style("min-width:0"):
                ui.label(titulo).classes("text-[11px] font-bold tracking-wide") \
                    .style(f"color:{theme.INK_MUTED}")
                if url:
                    theme.clicavel(
                        ui.image(url).classes("w-full rounded-lg cursor-pointer bg-white")
                          .style("height:auto").props("loading=lazy decoding=async"),
                        lambda _, u=url, t=titulo: _ampliar(u, t),
                        "Ampliar: %s" % titulo)
                else:
                    with ui.column().classes("w-full items-center py-6 rounded") \
                            .style("border:1px dashed rgba(255,255,255,.18)"):
                        ui.label("figura em falta").classes("text-xs") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label("%s/%s" % (campanha, ficheiro)).classes("text-[10px] mono-num") \
                            .style(f"color:{theme.INK_MUTED}")

        def _ampliar(url, titulo):
            with ui.dialog() as dlg, ui.card().classes("max-w-[92vw]"):
                ui.label(titulo).classes("text-sm").style(f"color:{theme.INK_MUTED}")
                ui.image(url).classes("max-h-[80vh] object-contain")
                with ui.row().classes("w-full justify-end"):
                    ui.button("Fechar", on_click=dlg.close).props("flat")
            dlg.open()

        def ir(j):
            estado["i"] = j % len(cens)
            # Pausa o 3D anterior, se houver: o canvas sai do DOM mas o ciclo de
            # desenho continuava a correr às escuras. Só aqui, e não no primeiro
            # desenho — na construção da página ainda não há cliente para
            # receber JavaScript.
            ui.run_javascript("window._viz3dAtual && window._viz3dAtual.pausa && "
                              "window._viz3dAtual.pausa()")
            desenhar()

        def andar(passo):
            ir(estado["i"] + passo)

        with ui.row().classes("items-center gap-2"):
            ui.button(icon="chevron_left", on_click=lambda: andar(-1)) \
                .props('flat dense round aria-label="Mapa anterior"')
            ui.button(icon="chevron_right", on_click=lambda: andar(1)) \
                .props('flat dense round aria-label="Mapa seguinte"')
            ui.label("ou use as setas do teclado").classes("text-xs") \
                .style(f"color:{theme.INK_MUTED}")

        ui.keyboard(on_key=lambda e: (
            None if not (ATIVA["v"] and e.action.keydown) else
            andar(1) if e.key.arrow_right else
            andar(-1) if e.key.arrow_left else None))

        desenhar()
