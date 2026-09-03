"""Vista «Apresentação» — cada mapa com os três modelos a correr, e o melhor em destaque.

Porque existe
A Galeria e os Vídeos mostram tudo, e é isso que se quer quando se procura uma
prova. Numa sala, com o relógio a andar, a pergunta é outra: «neste mapa, como
se comportam os três, e qual foi o melhor?». Esta vista responde-a oito vezes
— um ecrã por cenário — com os três algoritmos da campanha base lado a lado
(vídeo, episódio 3D ou heatmap, à escolha), o treino vencedor assinalado, o
dot plot e as curvas por baixo, e a frase que se diz com o mapa no ecrã.

Quem decide o vencedor é o ranking do dashboard (`data.ranking_por_cenario`),
com a regra da tese: compara-se dentro do cenário, só campanhas com avaliação
determinística, e a unidade é a campanha e não a execução. Quando o vencedor é
de outra campanha (a novidade adaptativa no Muro em U), entra como quarta
coluna ao lado dos três. O `configs/apresentacao.yaml` traz a frase de cada
mapa e as exclusões — um treino que o ranking escolheria mas que não se pode
mostrar, com o motivo escrito (o GNN adaptativo A1 nas Quatro Salas explora a
costura entre o topo das paredes e o teto da esfera: atravessa-as a 14,7 m).

As figuras de baixo vêm de `results/figuras_apresentacao/` (script
`figuras_apresentacao.py`), desenhadas de novo num formato único: as das
pastas de cada campanha têm formatos diferentes, e lado a lado liam-se como
descuido. O vídeo e o 3D de cada coluna são do mesmo treino, e um episódio
que não seja dessa campanha não aparece — mostrar o modelo da final com o
rótulo do adaptativo seria mentir com um vídeo.

Navegação: setas do teclado (só com este separador aberto) ou os botões.
"""
import json
import os

import yaml
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-5"
_YAML = os.path.join(config.BASE_DIR, "configs", "apresentacao.yaml")
DIR_EPISODIOS = os.path.join(config.BASE_DIR, "results", "episodios_3d")
DIR_EP_APRES = os.path.join(DIR_EPISODIOS, "apresentacao")
FIG_DIR = os.path.join(config.BASE_DIR, "results", "figuras_apresentacao")
_ALTURA_MEDIA = "clamp(200px,36vh,440px)"
COR_ADAPTATIVO = "#00897b"
MODOS = ["Vídeo", "Episódio 3D", "Heatmap"]

# O app.py liga isto quando o separador está aberto: o `ui.keyboard` é da
# página inteira, e sem o guarda as setas mudavam de mapa aqui enquanto se
# navegava na Defesa.
ATIVA = {"v": False}


def _yaml():
    if not os.path.exists(_YAML):
        return {}
    with open(_YAML, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def frases():
    """{cenário: frase} do apresentacao.yaml; {} se faltar."""
    return {it["cenario"]: (it.get("frase") or "").strip()
            for it in (_yaml().get("cenarios") or []) if it.get("cenario")}


def exclusoes():
    """{(cenário, campanha): motivo} — treinos que o ranking escolheria e não se mostram."""
    return {(e["cenario"], e["campanha"]): (e.get("motivo") or "").strip()
            for e in (_yaml().get("excluir") or [])
            if e.get("cenario") and e.get("campanha")}


def campanha_base(cenario: str) -> str:
    """A campanha cujos três algoritmos se mostram lado a lado."""
    return "mapa_grande_f2" if cenario == "mapa_grande" else "final_7d"


def vencedor(cenario: str):
    """A linha do ranking que ganhou este cenário, saltando as excluídas; ou None."""
    exc = exclusoes()
    for linha in data.ranking_por_cenario().get(cenario, []):
        if (cenario, linha["campanha"]) not in exc:
            return linha
    return None


def cenarios_com_vencedor():
    return [c for c in config.SCENARIO_KEYS if vencedor(c)]


def colunas(cenario: str):
    """As colunas do ecrã: os três da campanha base e, se for de outra, o vencedor.

    Cada uma: algo, campanha, serie (o nome na figura e no cartão), rotulo da
    campanha, cor, extra (é a quarta coluna), linha (a pontuação do ranking).
    """
    base = campanha_base(cenario)
    venc = vencedor(cenario)
    out = []
    for algo in config.ALGOS:
        out.append({"algo": algo, "campanha": base, "serie": algo,
                    "rotulo": data.rotulo_campanha(base)[0],
                    "cor": config.ALGO_META[algo]["color"], "extra": False,
                    "linha": data.pontuacao_campanha(base, cenario, algo)})
    if venc and data._ALIAS.get(venc["campanha"], venc["campanha"]) != base:
        out.append({"algo": venc["algo"].upper(), "campanha": venc["campanha"],
                    "serie": "%s adaptativo" % venc["algo"].upper(),
                    "rotulo": data.rotulo_campanha(venc["campanha"])[0],
                    "cor": COR_ADAPTATIVO, "extra": True, "linha": venc})
    return out


def e_vencedor(col, cenario: str) -> bool:
    v = vencedor(cenario)
    return bool(v) and col["algo"] == v["algo"].upper() and \
        data._ALIAS.get(col["campanha"], col["campanha"]) == \
        data._ALIAS.get(v["campanha"], v["campanha"])


def _url_fig_campanha(campanha: str, ficheiro: str):
    p = os.path.join(data.GRAFICOS_DIR, campanha, ficheiro)
    return "/graficos/%s/%s" % (campanha, ficheiro) if os.path.exists(p) else None


def _url_fig_apres(ficheiro: str):
    return ("/figuras_apresentacao/" + ficheiro
            if os.path.exists(os.path.join(FIG_DIR, ficheiro)) else None)


def video(campanha: str, algo: str, cenario: str):
    """(url, campanha de onde vem) do GIF, ou (None, None).

    A pasta agregada do F2 do mapa composto tem os GIF copiados; se um dia não
    tiver, procura-se nos streams que são a mesma campanha (`_ALIAS`).
    """
    a = algo.lower()
    fn = data.video_for(campanha, a, cenario)
    if fn:
        return "/graficos/%s/videos/%s" % (campanha, fn), campanha
    for s in data.sessoes_com_video(a, cenario):
        if data._ALIAS.get(s, s) == campanha:
            return "/graficos/%s/videos/%s" % (s, data.video_for(s, a, cenario)), s
    return None, None


def episodio(campanha: str, algo: str, cenario: str):
    """URL do episódio 3D DESTA campanha, ou None.

    Primeiro o exportado para a Apresentação com a campanha no meta; depois o
    genérico do «Episódio 3D», que é dos modelos ativos — a campanha final — e
    por isso só serve às colunas dela. Um episódio de outra campanha não entra.
    """
    nome = "%s_%s.json" % (algo.lower(), cenario)
    p = os.path.join(DIR_EP_APRES, nome)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                meta = json.load(fh).get("meta", {})
        except Exception:                                    # noqa: BLE001
            meta = {}
        origem = data._ALIAS.get(meta.get("campanha", ""), meta.get("campanha", ""))
        if origem == campanha:
            return "/episodios/apresentacao/" + nome
    if campanha == "final_7d" and os.path.exists(os.path.join(DIR_EPISODIOS, nome)):
        return "/episodios/" + nome
    return None


def _js_viz3d():
    js = os.path.join(os.path.dirname(os.path.dirname(__file__)), "estatico", "viz3d.js")
    v = int(os.path.getmtime(js)) if os.path.exists(js) else 0
    ui.add_head_html('<script src="/estatico/viz3d.js?v=%d"></script>' % v)


def _vazio(icone: str, texto: str, detalhe: str = ""):
    with ui.column().classes("w-full items-center justify-center gap-1 rounded-xl") \
            .style(f"height:{_ALTURA_MEDIA};border:1px dashed rgba(255,255,255,.14)"):
        ui.icon(icone).classes("text-3xl").style(f"color:{theme.INK_MUTED}")
        ui.label(texto).classes("text-xs text-center").style(f"color:{theme.INK_MUTED}")
        if detalhe:
            ui.label(detalhe).classes("text-[10px] text-center px-3") \
                .style(f"color:{theme.INK_MUTED}")


def build():
    cens = cenarios_com_vencedor()
    textos = frases()
    if not cens:
        with ui.column().classes("w-full p-4"):
            ui.label("Sem campanhas avaliadas: não há treino vencedor para mostrar.") \
                .classes("text-sm")
        return
    _js_viz3d()

    estado = {"i": 0, "modo": MODOS[0]}

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("items-center gap-3 w-full no-wrap"):
            theme.section_title("co_present", "Apresentação",
                                "os três modelos em cada mapa, o melhor em destaque · "
                                "setas do teclado para navegar")
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

        def _media(cen, col, k):
            """O vídeo, o 3D ou o heatmap desta coluna, conforme o modo."""
            algo, campanha = col["algo"], col["campanha"]
            if estado["modo"] == "Vídeo":
                url, origem = video(campanha, algo, cen)
                if not url:
                    _vazio("videocam_off", "este treino não gravou vídeo")
                    return
                ui.image(url).classes("w-full rounded-xl bg-white") \
                    .style(f"height:{_ALTURA_MEDIA};object-fit:contain").props("decoding=async")
                if origem != campanha:
                    ui.label("gravado no stream %s" % data.rotulo_campanha(origem)[0]) \
                        .classes("text-[10px]").style(f"color:{theme.INK_MUTED}")
                return
            if estado["modo"] == "Heatmap":
                url = _url_fig_campanha(campanha, "heatmap_ocupacao_%s_%s.png" % (algo.lower(), cen))
                if not url:
                    _vazio("grid_off", "sem heatmap de ocupação para este treino")
                    return
                theme.clicavel(
                    ui.image(url).classes("w-full rounded-xl bg-white cursor-pointer")
                      .style(f"height:{_ALTURA_MEDIA};object-fit:contain")
                      .props("loading=lazy decoding=async"),
                    lambda _, u=url, t="Ocupação — %s" % col["serie"]: _ampliar(u, t),
                    "Ampliar o heatmap %s" % col["serie"])
                return
            url = episodio(campanha, algo, cen)
            if not url:
                _vazio("view_in_ar", "sem episódio 3D deste treino",
                       "os modelos desta campanha não estão arquivados nesta máquina"
                       if campanha != "final_7d" else
                       "python scripts/exportar_episodio_3d.py --algo %s --cenario %s"
                       % (algo.lower(), cen))
                return
            # O canvas traz o episódio no `data-ep`: o viz3d.js arranca-o sozinho
            # quando o vê aparecer no DOM (ver autoArranque), sem `run_javascript`.
            cid = "apres_canvas_%s_%d" % (cen, k)
            ui.html('<canvas id="%s" data-ep="%s" data-estado="%s_estado" '
                    'style="width:100%%;height:%s;display:block;border-radius:12px;'
                    'background:#0b0e11"></canvas>' % (cid, url, cid, _ALTURA_MEDIA))
            ui.label("").classes("text-[10px] mono-num").props('id=%s_estado' % cid) \
                .style(f"color:{theme.INK_MUTED}")

        def _chip(col):
            """Pontuação DESTE treino: sucesso · recolhas · execuções a 100 %."""
            d = col["linha"]
            if not d or d.get("ptask") is None:
                ui.label("sem avaliação determinística").classes("text-[10px]") \
                    .style(f"color:{theme.INK_MUTED}")
                return
            p = d["ptask"]
            cor = "#22c55e" if p >= 80 else ("#f59e0b" if p >= 40 else "#ef4444")
            with ui.row().classes("items-center gap-1 no-wrap"):
                ui.icon("check_circle" if p >= 80 else ("error" if p >= 40 else "cancel")) \
                    .style(f"color:{cor}").classes("text-sm")
                ui.label("%s%% · %s rec/ep" % (theme.num(p, 0), theme.num(d["recolhas"]))) \
                    .classes("text-xs mono-num").style(f"color:{cor};font-weight:600")
                if d.get("convergentes") is not None:
                    ui.label("(%d/%d a 100%%)" % (d["convergentes"], d["runs"])) \
                        .classes("text-[10px]").style(f"color:{theme.INK_MUTED}")

        def _coluna(cen, col, k):
            melhor = e_vencedor(col, cen)
            borda = ("2px solid %s" % col["cor"]) if melhor else "1px solid rgba(255,255,255,.08)"
            with ui.element("div").classes("glass rounded-2xl p-3 flex flex-col gap-2") \
                    .style(f"border:{borda};min-width:0;border-top:3px solid {col['cor']}"):
                with ui.row().classes("items-center gap-2 no-wrap w-full"):
                    ui.element("div").style(
                        f"width:9px;height:9px;border-radius:50%;flex:none;background:{col['cor']}")
                    ui.label(col["serie"] if col["extra"]
                             else config.ALGO_META[col["algo"]]["label"]) \
                        .classes("text-sm font-bold truncate").style(f"color:{col['cor']}")
                    ui.space()
                    if melhor:
                        with ui.row().classes("items-center gap-1 no-wrap rounded-full px-2") \
                                .style(f"background:{col['cor']}22;border:1px solid {col['cor']}"):
                            ui.icon("emoji_events").classes("text-xs").style(f"color:{col['cor']}")
                            ui.label("melhor").classes("text-[10px] font-bold") \
                                .style(f"color:{col['cor']}")
                if col["extra"]:
                    ui.label(col["rotulo"]).classes("text-[10px] -mt-1") \
                        .style(f"color:{theme.INK_MUTED}")
                _media(cen, col, k)
                _chip(col)

        def desenhar():
            cen = cens[estado["i"]]
            v = vencedor(cen)
            cols = colunas(cen)
            venc_col = next((c for c in cols if e_vencedor(c, cen)), None)
            cor = venc_col["cor"] if venc_col else theme.INK
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
                            ui.icon("emoji_events").classes("text-sm").style(f"color:{cor}")
                            ui.label("melhor treino: %s · %s"
                                     % (venc_col["serie"] if venc_col else v["algo"],
                                        data.rotulo_campanha(v["campanha"])[0])) \
                                .classes("text-sm font-bold").style(f"color:{cor}")
                        conv = ("%d/%d execuções a 100 %%" % (v["convergentes"], v["runs"])
                                if v.get("convergentes") is not None else "")
                        ui.label("%s rec/ep · %s" % (theme.num(v["recolhas"]), conv)) \
                            .classes("text-xs mono-num").style(f"color:{theme.INK_MUTED}")

                # A linha dos modelos: um cartão por algoritmo, o mesmo modo em todos.
                with ui.row().classes("items-center gap-3 no-wrap mt-3"):
                    tog = ui.toggle(MODOS, value=estado["modo"]).props("no-caps dense")
                    ui.label("arrasta para rodar o 3D · roda do rato para aproximar") \
                        .classes("text-[11px]").style(f"color:{theme.INK_MUTED}") \
                        .bind_visibility_from(tog, "value", lambda v: v == "Episódio 3D")
                linha = ui.grid().classes("w-full gap-3 mt-1").style(
                    "grid-template-columns:repeat(%d,minmax(0,1fr))" % len(cols))

                def _desenhar_linha():
                    linha.clear()
                    with linha:
                        for k, col in enumerate(cols):
                            _coluna(cen, col, k)
                _desenhar_linha()

                def _muda_modo(e):
                    estado["modo"] = e.value
                    _desenhar_linha()
                tog.on_value_change(_muda_modo)

                # As figuras, num formato único para os oito cenários.
                with ui.grid().classes("w-full gap-4 mt-4").style(
                        "grid-template-columns:minmax(0,4fr) minmax(0,6fr)"):
                    _figura("dotplot_%s.png" % cen, "Fiabilidade entre execuções")
                    _figura("curvas_%s.png" % cen, "Curvas de treino")

                # A frase.
                frase = textos.get(cen)
                if frase:
                    ui.label(frase).classes("text-lg leading-snug mt-4 pl-4") \
                        .style(f"border-left:3px solid {cor}")
                else:
                    ui.label("· sem frase para este cenário em configs/apresentacao.yaml") \
                        .classes("text-xs mt-4").style(f"color:{theme.INK_MUTED}")
                exc = [m for (c, _camp), m in exclusoes().items() if c == cen]
                theme.fonte("%s · ranking por recolhas/ep, avaliação determinística%s"
                            % (", ".join(sorted({c["campanha"] for c in cols})),
                               (" · excluído: " + "; ".join(exc)) if exc else ""))

        def _figura(ficheiro, titulo):
            url = _url_fig_apres(ficheiro)
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
                        ui.label("python scripts/figuras_apresentacao.py") \
                            .classes("text-[10px] mono-num").style(f"color:{theme.INK_MUTED}")

        def _ampliar(url, titulo):
            with ui.dialog() as dlg, ui.card().classes("max-w-[92vw]"):
                ui.label(titulo).classes("text-sm").style(f"color:{theme.INK_MUTED}")
                ui.image(url).classes("max-h-[80vh] object-contain")
                with ui.row().classes("w-full justify-end"):
                    ui.button("Fechar", on_click=dlg.close).props("flat")
            dlg.open()

        def ir(j):
            estado["i"] = j % len(cens)
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
