"""Painel «qual foi o melhor treino» — partilhado pela Galeria e pelos Vídeos.

Porque existe
-------------
A Galeria tem 48 campanhas num seletor e não dizia nada sobre qual delas valia
alguma coisa. Para mostrar a alguém o melhor resultado num cenário era preciso
saber de cor em que pasta ele estava — e as pastas chamam-se `mega_A1` ou
`09-07-2026_12h52m`. Quem abre o dashboard tem de adivinhar.

As duas regras que este painel não quebra
-----------------------------------------
1. **Compara-se dentro de um cenário, nunca entre cenários.** As 123 recolhas/ep
   do Gargalo e as 88 da Porta com Alternativa não são a mesma régua: muda o
   mapa, mudam os itens, muda a dificuldade. Um «melhor treino de todos» somando
   os sete seria um número sem significado, e por isso não existe aqui.
2. **Só entram treinos com avaliação determinística** (20 episódios de sementes
   fixas). As campanhas exploratórias de maio a junho guardaram curvas de
   TREINO, que é outra régua; pô-las na mesma tabela daria a um número de treino
   o estatuto de resultado — que é precisamente o erro que a tese documenta no
   colapso evolutivo.
"""
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
_COR_ALGO = {a: config.ALGO_META[a]["color"] for a in config.ALGO_META}


def _linha(d, melhor, destacar):
    """Uma linha do ranking de um cenário."""
    rotulo, canonica = data.rotulo_campanha(d["campanha"])
    e_o_melhor = d is melhor
    fundo = ("background:rgba(255,255,255,.05);" if destacar else "")
    with ui.row().classes("w-full items-center gap-3 no-wrap py-1 px-2") \
            .style(f"border-radius:6px; {fundo}"):
        ui.label("★" if e_o_melhor else "").classes("text-xs w-3") \
            .style("color:#facc15")
        ui.element("div").style(
            f"width:7px;height:7px;border-radius:50%;flex:none;"
            f"background:{_COR_ALGO.get(d['algo'], theme.INK_MUTED)}")
        ui.label(d["algo"]).classes("text-xs font-bold w-10")
        with ui.column().classes("gap-0 flex-1 min-w-0"):
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.label(rotulo).classes("text-xs truncate")
                if canonica:
                    ui.label("na tese").classes("text-[9px] px-1") \
                        .style("border:1px solid #4ade80; border-radius:4px; "
                               "color:#4ade80")
            desc = data.descricao_sessao(d["campanha"])
            ui.label("%s%s" % (d["campanha"], " · " + desc if desc else "")) \
                .classes("text-[10px] truncate").style(f"color:{theme.INK_MUTED}")
        ui.label("%.1f" % d["recolhas"]).classes("text-sm mono-num font-bold w-16 text-right")
        conv = ("%d/%d" % (d["convergentes"], d["runs"])
                if d["convergentes"] is not None else "—")
        ui.label(conv).classes("text-[10px] mono-num w-12 text-right") \
            .style(f"color:{theme.INK_MUTED}")


def painel(campanha_atual=None, titulo="Qual foi o melhor treino, por cenário"):
    """Constrói o painel. `campanha_atual` realça as linhas dessa campanha."""
    rank = data.ranking_por_cenario()
    if not rank:
        return

    with ui.card().classes(CARD + " w-full"):
        theme.section_title("emoji_events", titulo,
                            "recolhas por episódio · avaliação determinística")
        ui.label(
            "Cada cenário é uma corrida à parte: só se comparam treinos DENTRO "
            "do mesmo cenário, porque as recolhas de mapas diferentes não são a "
            "mesma régua. A coluna da direita é quantas execuções resolveram o "
            "cenário por completo. Campanhas sem avaliação determinística — as "
            "exploratórias de maio e junho, que só têm curvas de treino — não "
            "entram."
        ).classes("text-xs mb-3").style(f"color:{theme.INK_MUTED}")

        for cen in config.MAIN_SCENARIO_KEYS:
            linhas = rank.get(cen, [])
            if not linhas:
                continue
            melhor = linhas[0]
            rot_cen = config.SCENARIO_LABEL_SHORT.get(cen, cen)
            with ui.expansion().classes("w-full").props("dense") as exp:
                with exp.add_slot("header"):
                    with ui.row().classes("w-full items-center gap-3 no-wrap"):
                        ui.label(rot_cen).classes("text-xs font-bold w-40 truncate")
                        rotulo, _ = data.rotulo_campanha(melhor["campanha"])
                        ui.element("div").style(
                            f"width:7px;height:7px;border-radius:50%;flex:none;"
                            f"background:{_COR_ALGO.get(melhor['algo'], theme.INK_MUTED)}")
                        ui.label("%s · %s" % (melhor["algo"], rotulo)) \
                            .classes("text-xs flex-1 truncate")
                        ui.label("%.1f rec/ep" % melhor["recolhas"]) \
                            .classes("text-xs mono-num font-bold")
                # Dentro: o ranking completo do cenário.
                for d in linhas:
                    _linha(d, melhor, destacar=(d["campanha"] == campanha_atual))
