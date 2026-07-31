"""Vista 'Vitrine' — o que se mostra na defesa, e só isso.

Porque existe
-------------
A galeria (Resultados) e o Arquivo mostram TUDO: 31 campanhas, centenas de
figuras. É o que se quer quando se procura uma prova. Não é o que se quer numa
sala com o relógio a andar — ali a pergunta é «mostra-me o essencial», e passar
30 campanhas à procura da boa é a pior forma de responder.

Esta vista mostra uma seleção **declarada** em `configs/vitrine.yaml`, com a
regra escrita ao lado de cada figura. A regra está em `docs/VITRINE_DEFESA.md`
e resume-se a: a unidade é a campanha e não a execução (nada de «o melhor run»);
quando os três algoritmos correram, aparecem os três; e a métrica é sempre
recolhas/episódio, nunca a fitness ao lado da recompensa.

Uma figura em falta aparece como **falta**, com o caminho — nunca em silêncio. A
alternativa (esconder o que não existe) faria a vitrine parecer completa numa
altura em que não está, que é exatamente quando isso custa caro.
"""
import os

import yaml
from nicegui import ui

from .. import config, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title

_YAML = os.path.join(config.BASE_DIR, "configs", "vitrine.yaml")
_GRAFICOS = os.path.join(config.BASE_DIR, "results", "graficos_tese")


def _seleccao():
    """Blocos do vitrine.yaml. Devolve [] (e a vista explica-se) se faltar."""
    if not os.path.exists(_YAML):
        return []
    with open(_YAML, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("blocos", []) or []


def _existe(campanha: str, figura: str) -> bool:
    return os.path.exists(os.path.join(_GRAFICOS, campanha, figura))


def _cartao_figura(campanha: str, figura: str, nota: str, abrir):
    # `min-width:0` não é cosmético: sem ele, uma célula de grelha assume a
    # largura NATURAL do conteúdo (a imagem a 2400 px) em vez de encolher. A
    # página cresce para a direita e — como todas as vistas partilham o mesmo
    # `ui.tab_panels` — os outros separadores ficam espremidos num canto. Foi o
    # que aconteceu ao Monitorizar assim que esta vista entrou.
    with ui.column().classes("gap-1 w-full").style("min-width:0"):
        if _existe(campanha, figura):
            ui.image(f"/graficos/{campanha}/{figura}") \
                .classes("w-full max-w-full rounded cursor-pointer") \
                .style("height:auto") \
                .on("click", lambda c=campanha, f=figura: abrir(c, f))
        else:
            with ui.column().classes("w-full items-center justify-center py-8 rounded") \
                    .style("border:1px dashed rgba(255,255,255,.18)"):
                ui.icon("image_not_supported", size="28px").style(f"color:{theme.INK_MUTED}")
                ui.label("figura em falta").classes("text-xs mt-1") \
                    .style(f"color:{theme.INK_MUTED}")
                ui.label(f"{campanha}/{figura}").classes("text-[10px] mono-num") \
                    .style(f"color:{theme.INK_MUTED}")
                ui.label("gerar: python scripts/figuras_campanha.py --todas --heatmaps") \
                    .classes("text-[10px] mono-num").style(f"color:{theme.INK_MUTED}")
        ui.label(nota).classes("text-xs leading-snug")
        ui.label(f"{campanha} · {figura}").classes("text-[10px] mono-num") \
            .style(f"color:{theme.INK_MUTED}")


def build():
    blocos = _seleccao()

    def abrir(campanha: str, figura: str):
        with ui.dialog() as dlg, ui.card().classes("max-w-[92vw]"):
            ui.label(f"{campanha} · {figura}").classes("text-sm mono-num") \
                .style(f"color:{theme.INK_MUTED}")
            ui.image(f"/graficos/{campanha}/{figura}").classes("max-h-[78vh] object-contain")
            with ui.row().classes("w-full justify-end"):
                ui.button("Fechar", on_click=dlg.close).props("flat")
        dlg.open()

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.card().classes(CARD):
            _section_title("slideshow", "Vitrine da defesa",
                           "a seleção, e a regra que a justifica")
            ui.label(
                "A unidade é a campanha, nunca a execução — mostra-se a distribuição "
                "das execuções com a média marcada e a contagem a 100%, não o melhor "
                "run. Quando os três algoritmos correram, aparecem os três: um "
                "algoritmo que colapsa não sai da figura, porque o colapso é o "
                "resultado. Seleção em configs/vitrine.yaml; regra em "
                "docs/VITRINE_DEFESA.md."
            ).classes("text-xs").style(f"color:{theme.INK_MUTED}")

        if not blocos:
            with ui.card().classes(CARD):
                ui.label("Sem configs/vitrine.yaml — não há seleção declarada.") \
                    .classes("text-sm")
            return

        for bloco in blocos:
            with ui.card().classes(CARD):
                _section_title("push_pin", bloco.get("titulo", "—"),
                               bloco.get("subtitulo", ""))
                itens = bloco.get("itens", []) or []
                # A campanha pode estar no bloco (todas as figuras da mesma) ou
                # item a item (o mesmo cenário em campanhas diferentes, que é
                # como se comparam os quatro braços do Muro em U).
                campanha_bloco = bloco.get("campanha")
                n_falta = sum(1 for it in itens
                              if not _existe(it.get("campanha", campanha_bloco) or "",
                                             it.get("figura", "")))
                if n_falta:
                    ui.label(f"{n_falta} de {len(itens)} figuras em falta neste bloco") \
                        .classes("text-xs mb-2").style("color:#f0a04b")
                with ui.grid(columns=2).classes("w-full gap-4") \
                        .style("grid-template-columns:repeat(2,minmax(0,1fr))"):
                    for it in itens:
                        _cartao_figura(it.get("campanha", campanha_bloco) or "",
                                       it.get("figura", ""), it.get("nota", ""), abrir)
