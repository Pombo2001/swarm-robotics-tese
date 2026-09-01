"""Vista «Episódio 3D» — o enxame a mexer, dentro do browser.

Porque existe ao lado do «Ao vivo (3D)»
O visualizador Ursina abre uma janela no ecrã de quem corre o servidor. Na
torre é o que se quer. No Raspberry Pi — sem monitor, a servir o orientador pela
internet — não serve de nada: a janela abriria numa máquina onde ninguém está.

Aqui o servidor não renderiza nada. Serve um JSON com a geometria do cenário e as
posições dos agentes ao longo do episódio (`scripts/exportar_episodio_3d.py`), e
o desenho acontece no browser de quem está a ver — funciona na torre, no Pi e no
telemóvel, com a mesma página.

Não substitui o Ursina: ali há câmara livre em tempo real sobre uma simulação a
correr; aqui há um episódio gravado, que é o que se quer mostrar a alguém.
"""
import glob
import json
import os

from nicegui import ui

from .. import config, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title

DIR_EPISODIOS = os.path.join(config.BASE_DIR, "results", "episodios_3d")


def _episodios():
    """{rótulo legível: nome do ficheiro} dos episódios exportados."""
    if not os.path.isdir(DIR_EPISODIOS):
        return {}
    out = {}
    for f in sorted(os.listdir(DIR_EPISODIOS)):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(DIR_EPISODIOS, f), encoding="utf-8") as fh:
                m = json.load(fh).get("meta", {})
        except Exception:
            continue
        # O nome vem da CHAVE, pelo vocabulário do dashboard, e não do `rotulo`
        # gravado no JSON: esse é anterior à uniformização dos nomes e o seletor
        # oferecia três formas já abandonadas. O `rotulo` fica só de recurso,
        # para um cenário que o dashboard não conheça.
        cen = m.get("cenario")
        nome = (config.SCENARIO_LABEL_SHORT.get(cen)
                or m.get("rotulo") or cen or f)
        rot = (f"{m.get('algo','?')} · {nome} "
               f"— {theme.plural(m.get('recolhas', 0), 'recolha')}")
        out[rot] = f
    return out


def build():
    eps = _episodios()

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.card().classes(CARD):
            _section_title("view_in_ar", "Episódio 3D",
                           "gravado no servidor, desenhado no teu browser")
            if not eps:
                ui.label("Ainda não há episódios exportados.") \
                    .classes("text-sm").style(f"color:{theme.INK_MUTED}")
                ui.label("Gera com:  python scripts/exportar_episodio_3d.py --todos") \
                    .classes("text-xs mono-num").style(f"color:{theme.INK_MUTED}")
                return

            rotulos = list(eps)
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                sel = ui.select(rotulos, value=rotulos[0], label="Episódio") \
                    .props("outlined dense").classes("min-w-[320px]")
                btn = ui.button("Pausa", icon="pause").props("flat dense")
                vel = ui.select({0.5: "0,5×", 1: "1×", 2: "2×", 4: "4×"},
                                value=1, label="Velocidade") \
                    .props("outlined dense").classes("w-28")
                ui.label("arrasta para rodar · roda do rato para aproximar") \
                    .classes("text-xs").style(f"color:{theme.INK_MUTED}")
            estado = ui.label("").classes("text-xs mono-num mt-1") \
                .style(f"color:{theme.INK_MUTED}")

        with ui.card().classes(CARD + " p-0 overflow-hidden"):
            # `data-ep`: o episódio inicial vai no próprio HTML, e o viz3d.js
            # arranca a partir dele. Não depende de o servidor conseguir executar
            # JS no cliente — que na construção da vista ainda não consegue.
            primeiro = eps[rotulos[0]]
            ui.html(f'<canvas id="viz3d_canvas" data-ep="/episodios/{primeiro}" '
                    f'style="width:100%;height:62vh;display:block"></canvas>')

        with ui.card().classes(CARD):
            ui.label(
                "As paredes são desenhadas com 2,2 m de altura VISUAL. No simulador têm "
                "2× o raio da arena (30 m nos sete cenários, 120 no mapa composto) — é o "
                "que as torna estanques desde a correção de 29 de julho, mas desenhadas "
                "assim tapavam a cena inteira."
            ).classes("text-xs").style(f"color:{theme.INK_MUTED}")

        # O JS vive num ficheiro servido, não numa string: cacheável, com sintaxe
        # destacada, e sem duas cópias a divergir. O `?v=<mtime>` existe porque
        # sem ele uma correção só aparecia depois de um Ctrl+F5 — meia hora a
        # depurar código já corrigido.
        _js = os.path.join(os.path.dirname(os.path.dirname(__file__)), "estatico", "viz3d.js")
        _v = int(os.path.getmtime(_js)) if os.path.exists(_js) else 0
        ui.add_head_html(f'<script src="/estatico/viz3d.js?v={_v}"></script>')

        def _carregar():
            ficheiro = eps[sel.value]
            # Espera que o `viz3d.js` esteja carregado antes de o chamar. O
            # `add_head_html` acontece durante a construção da vista e o script
            # chega DEPOIS; sem esta espera, a primeira carga falhava em silêncio
            # e ficava um canvas preto — que se lê como "o 3D não funciona".
            ui.run_javascript(
                f'(function esperar(n) {{'
                f'  if (window.viz3d) {{'
                f'    viz3d.carregar("viz3d_canvas", "/episodios/{ficheiro}", e => {{'
                f'      const el = document.getElementById("viz3d_estado");'
                f'      if (el) el.textContent = "passo " + e.passo + " · quadro " +'
                f'        (e.quadro+1) + "/" + e.total + " · " + e.recolhas + " recolhas";'
                f'    }});'
                f'  }} else if (n > 0) {{ setTimeout(() => esperar(n-1), 100); }}'
                f'}})(50)'
            )

        # O rótulo do estado é atualizado pelo JS (a cada quadro seria demasiado
        # tráfego pelo websocket do NiceGUI — o browser já tem a informação).
        estado.props('id=viz3d_estado')

        sel.on_value_change(lambda: _carregar())   # aqui o cliente já está ligado
        vel.on_value_change(lambda e: ui.run_javascript(
            f'window._viz3dAtual && window._viz3dAtual.velocidade({e.value})'))

        def _alternar():
            ui.run_javascript('window._viz3dAtual && window._viz3dAtual.alterna()')
            btn.props(f'icon={"play_arrow" if btn.text == "Pausa" else "pause"}')
            btn.text = "Play" if btn.text == "Pausa" else "Pausa"
        btn.on("click", _alternar)

        # (sem timer de arranque: quem carrega o primeiro episódio é o próprio JS)
