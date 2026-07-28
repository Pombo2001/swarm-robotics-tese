"""Vista «Mapa grande» — o 8.º cenário e a QI7, que é o trabalho em curso.

O mapa composto (103×62 m, cinco zonas, 106 obstáculos) é a única questão de
investigação ainda aberta, e não tinha representação nenhuma no dashboard: quem
abrisse isto via sete cenários e uma tese fechada, quando o que está a acontecer
agora é a oitava.

Mostra a planta, o estado das fases (F0/F1/F2) e — quando os CSV existirem — a
grelha do F1 **por condição**, que é o que decide se a QI7 tem resposta.

⚠️ A leitura do F1 é a do `docs/PRE_REGISTO_MAPA_GRANDE.md` §3, fixada antes de
haver dados: um zero admite quatro causas e só uma é a pergunta da tese. Por isso
esta vista **não interpreta** — mostra as condições lado a lado e diz quantas
faltam. O veredicto formal é o `scripts/analise_f1_controlos.py`, e está dito no
ecrã para que ninguém tire conclusões daqui com metade das condições medidas.
"""
import os

import pandas as pd
from nicegui import ui

from .. import theme

CARD = theme.CARD + " p-4"
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIR_F1 = os.path.join(_RAIZ, "results", "mapa_grande", "f1_zeroshot")
PLANTA = "/figuras_tese/mapa_grande_planta.png"

ALGOS = ("GNN", "PPO", "SAC")
CONDICOES = [(("mapa", "base"), "natural"),
             (("treino", "base"), "escala"),
             (("mapa", "sem_obstaculos"), "sem obstáculos"),
             (("mapa", "sem_porta_obs"), "sem features da porta")]

ORIGENS = [("none", "Sandbox"), ("u_wall", "Muro U"), ("bottleneck", "Gargalo"),
           ("four_rooms", "Quatro Salas"),
           ("cooperative_door", "Porta Cooperativa"),
           ("cooperative_perception", "Perceção Coop."),
           ("cooperative_door_bypass", "Porta c/ Alternativa")]


def _carregar():
    """Todos os zeroshot_*.csv que existirem, concatenados."""
    if not os.path.isdir(DIR_F1):
        return None
    partes = []
    for f in sorted(os.listdir(DIR_F1)):
        if f.startswith("zeroshot_") and f.endswith(".csv"):
            try:
                partes.append(pd.read_csv(os.path.join(DIR_F1, f)))
            except Exception:  # noqa: BLE001
                pass
    return pd.concat(partes, ignore_index=True) if partes else None


def _grelha(d, cond):
    (n, c) = cond
    g = d[(d["NormObs"] == n) & (d["Controlo"] == c)]
    if not len(g):
        return None
    saida = {}
    for cen, _ in ORIGENS:
        for a in ALGOS:
            cel = g[(g["Algorithm"] == a) & (g["Origem"] == cen)]
            saida[(cen, a)] = cel["food_collected"].mean() if len(cel) else None
    return saida


def build():
    with ui.column().classes("w-full gap-4 p-4"):
        theme.section_title(
            "map", "Mapa grande (8.º cenário)",
            "QI7 — as conclusões dos sete cenários transferem para um mapa "
            "que os compõe?")

        with ui.row().classes("w-full gap-4 items-start no-wrap flex-wrap"):
            # ── a planta ──────────────────────────────────────────────────────
            with ui.card().classes(CARD + " grow"):
                ui.label("A planta, lida da geometria do simulador") \
                    .classes("text-sm font-bold mb-2")
                caminho = os.path.join(_RAIZ, "Tese", "images", "resultados",
                                       "mapa_grande_planta.png")
                if os.path.exists(caminho):
                    # A planta é uma figura de tese (quadrada e de alta
                    # resolução): a tamanho natural ocupa dois ecrãs e empurra as
                    # fases e a grelha do F1 para fora de vista. Limitada em
                    # altura, com `contain` para não deformar a geometria — que é
                    # o ponto da figura.
                    ui.image(PLANTA).classes("w-full rounded").style(
                        "max-height:52vh; object-fit:contain")
                else:
                    ui.label("planta não encontrada em Tese/images/resultados/") \
                        .classes("text-xs").style(f"color:{theme.INK_MUTED}")
                ui.label(
                    "Cinco zonas de oeste para este: sala de partida · gargalo "
                    "com beco em U (boca virada ao lado por onde o enxame chega) "
                    "· quatro salas em cruz · porta cooperativa com alternativa "
                    "· câmara do ninho. 106 obstáculos, 20 agentes."
                ).classes("text-xs mt-2").style(f"color:{theme.INK_MUTED}")

            # ── números congelados antes de treinar ───────────────────────────
            with ui.card().classes(CARD).style("min-width:280px"):
                ui.label("Congelado antes de qualquer treino") \
                    .classes("text-sm font-bold mb-2")
                for rotulo, valor in (
                        ("dimensão", "103 × 62 m (arena r=60)"),
                        ("do centro do spawn ao ninho", "128,8 m"),
                        ("ponto mais distante do ninho", "155,4 m"),
                        ("custo de a porta estar fechada", "+20%"),
                        ("N", "20 agentes (obs_dim=111, como os 7)"),
                        ("max_steps", "2000 (folga 2,6×)"),
                        ("required_to_eat", "1")):
                    with ui.row().classes("w-full justify-between no-wrap gap-4"):
                        ui.label(rotulo).classes("text-xs") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label(valor).classes("text-xs mono-num text-right")
                ui.label(
                    "Cada um destes está justificado no pré-registo — e as "
                    "emendas #14/#15 corrigiram a descrição de dois deles."
                ).classes("text-[11px] mt-3").style(f"color:{theme.INK_MUTED}")

        # ── as fases ─────────────────────────────────────────────────────────
        d = _carregar()
        presentes = [n for c, n in CONDICOES if d is not None and _grelha(d, c)]
        faltam = [n for c, n in CONDICOES if n not in presentes]

        with ui.card().classes(CARD + " w-full"):
            ui.label("Fases").classes("text-sm font-bold mb-2")
            fases = [
                ("F0 — smoke test", "concluído (27 jul, 3 algoritmos, 2 h cada)",
                 "#4ade80"),
                ("F1 — zero-shot de topologia",
                 "%d de 4 condições no disco: %s%s"
                 % (len(presentes), ", ".join(presentes) or "nenhuma",
                    ("; faltam " + ", ".join(faltam)) if faltam else ""),
                 "#4ade80" if len(presentes) == 4 else "#ffb020"),
                ("F2 — treino nativo",
                 "por lançar — só depois de o mega-treino libertar o servidor "
                 "(~3 ago); script pronto em scripts/mapa_streamF2.sh",
                 theme.INK_MUTED),
            ]
            for nome, estado, cor in fases:
                with ui.row().classes("items-center gap-3 no-wrap w-full py-1"):
                    ui.element("div").style(
                        "width:8px;height:8px;border-radius:50%%;background:%s;"
                        "flex:none" % cor)
                    ui.label(nome).classes("text-xs font-bold w-56 shrink-0")
                    ui.label(estado).classes("text-xs") \
                        .style(f"color:{theme.INK_MUTED}")

        # ── a grelha do F1, por condição ─────────────────────────────────────
        if d is None:
            with ui.card().classes(CARD + " w-full"):
                ui.label("Ainda não há dados do F1 no disco.") \
                    .classes("text-sm font-bold")
            return

        for cond, nome in CONDICOES:
            g = _grelha(d, cond)
            if not g:
                continue
            with ui.card().classes(CARD + " w-full"):
                sub = d[(d["NormObs"] == cond[0]) & (d["Controlo"] == cond[1])]
                zeros = sum(1 for v in g.values() if v == 0)
                ui.label("%s — %d episódios, %d células, %d a zero"
                         % (nome, len(sub),
                            sum(1 for v in g.values() if v is not None), zeros)) \
                    .classes("text-sm font-bold mb-2")
                with ui.grid(columns=4).classes("w-full gap-px"):
                    ui.label("campeão treinado em").classes("text-[10px] py-1") \
                        .style(f"color:{theme.INK_MUTED}")
                    for a in ALGOS:
                        ui.label(a).classes(
                            "text-[10px] font-bold text-center py-1") \
                            .style(f"color:{theme.INK_MUTED}")
                    for cen, rotulo in ORIGENS:
                        ui.label(rotulo).classes("text-xs py-1")
                        for a in ALGOS:
                            v = g.get((cen, a))
                            txt = "—" if v is None else ("0" if v == 0
                                                         else "%.1f" % v)
                            lbl = ui.label(txt).classes(
                                "text-xs mono-num text-center py-1 rounded")
                            if v:
                                lbl.style("background: rgba(74,222,128,%.2f)"
                                          % min(0.45, 0.10 + v / 60.0))
                            elif v == 0:
                                lbl.style(f"color:{theme.INK_MUTED}")

        with ui.card().classes(CARD + " w-full"):
            if faltam:
                ui.label("⚠ Isto ainda não responde à QI7.") \
                    .classes("text-sm font-bold").style("color:#ffb020")
                ui.label(
                    "O pré-registo (§3) fixa que um zero no F1 tem quatro causas "
                    "possíveis e só uma é a pergunta da tese. Faltam %d condição "
                    "(ões) de controlo: %s. Ler a grelha acima como resposta "
                    "seria confundir topologia com escala da observação, "
                    "obstáculos ou features da porta."
                    % (len(faltam), ", ".join(faltam))
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
            else:
                ui.label("As quatro condições estão no disco.") \
                    .classes("text-sm font-bold")
                ui.label(
                    "O veredicto formal — que causa está excluída e qual "
                    "confunde o resultado — sai de "
                    "`python scripts/analise_f1_controlos.py`, que aplica a "
                    "regra pré-comprometida em vez de a interpretar aqui."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
