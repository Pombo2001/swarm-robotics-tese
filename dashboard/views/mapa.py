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
# ⚠️ `f1_zeroshot/` é a corrida ANULADA a 29 jul (paredes de 30 m numa arena de
# raio 60: os agentes voavam por cima do labirinto, env_hash 267a7b547aed). Esta
# vista lia-a — mostrava 4,96 recolhas/ep como se fosse o resultado do mapa. O F1
# que vale é a repetição de 31 jul, `f1_zeroshot_v2/` (env_hash e930abe4d992).
DIR_F1 = os.path.join(_RAIZ, "results", "mapa_grande", "f1_zeroshot_v2")
DIR_F1_ANULADO = os.path.join(_RAIZ, "results", "mapa_grande", "f1_zeroshot")
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


def _digital_do_mapa_agora():
    """Impressão digital do ambiente ATUAL, pela mesma função que a escreve no CSV.

    Importada do `eval_zeroshot_mapa`, nunca reimplementada: uma segunda cópia
    acabaria por discordar da primeira e ninguém saberia qual estava certa — é a
    regra que a vista Proveniência já segue.
    """
    try:
        import copy
        import sys
        import yaml
        if _RAIZ not in sys.path:
            sys.path.insert(0, _RAIZ)
        from scripts.eval_zeroshot_mapa import _impressao_digital
        with open(os.path.join(_RAIZ, "configs", "foraging.yaml"),
                  encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        cfg = copy.deepcopy(cfg)
        cfg["environment"]["classic_scenario"] = "mapa_grande"
        return _impressao_digital(cfg, "mapa_grande")
    except Exception:  # noqa: BLE001
        return None


def _dados_de_outro_mundo(d):
    """(anulado?, digitais_do_csv, digital_atual) — os CSV são deste simulador?

    Existe por causa de 29 jul: as quatro condições do F1 (1680 episódios, ~34 h
    de servidor) tinham sido medidas num mundo em que as paredes deixavam 45 m de
    céu aberto por cima, e os agentes atravessavam o labirinto por VOO. O
    dashboard mostrava a grelha com um ✓ verde e «as quatro condições estão no
    disco» — exatamente a leitura que não se podia fazer.

    A verificação não é um aviso escrito à mão (que envelhece e mente): compara-se
    a impressão digital gravada em cada CSV com a do simulador de agora. Se o mapa
    mudar outra vez, esta vista diz sozinha que os dados são de outro mundo, sem
    depender de alguém se lembrar de vir cá escrever.
    """
    if d is None or "env_hash" not in d.columns:
        return False, set(), None
    agora = _digital_do_mapa_agora()
    if agora is None:
        return False, set(), None
    # A condição «sem obstáculos» muda o mundo DE PROPÓSITO e por isso tem outra
    # digital — não conta como divergência. Só se olha para as condições que
    # correm no mapa tal como ele é.
    natural = d[d.get("Controlo").isin(["base", "sem_porta_obs"])] \
        if "Controlo" in d.columns else d
    do_csv = {h for h in natural.get("env_hash", pd.Series(dtype=str)).dropna().unique()}
    return (bool(do_csv) and agora not in do_csv), do_csv, agora


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
        anulado, dig_csv, dig_agora = _dados_de_outro_mundo(d)

        if anulado:
            with ui.card().classes(CARD + " w-full") \
                    .style("border-left:4px solid #ef4444"):
                ui.label("⛔ Os dados do F1 no disco são de OUTRO simulador — "
                         "estão anulados.").classes("text-sm font-bold") \
                    .style("color:#ef4444")
                ui.label(
                    "A impressão digital do ambiente gravada nos CSV (%s) não é a "
                    "do simulador de agora (%s). Foram medidos num mundo em que as "
                    "paredes tinham 30 m de altura numa arena esférica de raio 60: "
                    "sobravam 45 m de céu aberto e os agentes atravessavam o "
                    "labirinto por cima — a 59 m de altura, o episódio quase "
                    "inteiro. As células que recolheram, recolheram a voar."
                    % (", ".join(sorted(dig_csv)) or "—", dig_agora)
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
                ui.label(
                    "Corrigido a 29 jul (altura da parede = 2×raio da arena). O F1 "
                    "repete-se de raiz; a grelha abaixo fica só como registo. "
                    "Detalhe: emenda 16 do PRE_REGISTO_MAPA_GRANDE.md."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")

        with ui.card().classes(CARD + " w-full"):
            ui.label("Fases").classes("text-sm font-bold mb-2")
            fases = [
                ("F0 — smoke test", "concluído (27 jul, 3 algoritmos, 2 h cada)",
                 "#4ade80"),
                ("F1 — zero-shot de topologia",
                 ("ANULADO (29 jul) — as 4 condições correram com o simulador "
                  "antigo; por repetir de raiz")
                 if anulado else
                 "%d de 4 condições no disco: %s%s"
                 % (len(presentes), ", ".join(presentes) or "nenhuma",
                    ("; faltam " + ", ".join(faltam)) if faltam else ""),
                 "#ef4444" if anulado
                 else ("#4ade80" if len(presentes) == 4 else "#ffb020")),
                ("F2 — treino nativo",
                 "arranca 3 ago, quando o megaB largar a máquina: 3 algoritmos × "
                 "21 runs (emenda 19) + braço exploratório @2340 min × 3 "
                 "(emenda 20); diretórios já preparados no servidor",
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
            with ui.card().classes(CARD + " w-full") \
                    .style("opacity:0.45" if anulado else ""):
                sub = d[(d["NormObs"] == cond[0]) & (d["Controlo"] == cond[1])]
                zeros = sum(1 for v in g.values() if v == 0)
                ui.label("%s%s — %d episódios, %d células, %d a zero"
                         % ("ANULADO · " if anulado else "", nome, len(sub),
                            sum(1 for v in g.values() if v is not None), zeros)) \
                    .classes("text-sm font-bold mb-2") \
                    .style("color:#ef4444" if anulado else "")
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
            if anulado:
                ui.label("⚠ A QI7 continua sem resposta — e não é por faltarem "
                         "condições.").classes("text-sm font-bold") \
                    .style("color:#ffb020")
                ui.label(
                    "As quatro condições foram medidas, mas num mapa que não é "
                    "este. Repetir o F1 (~8,5 h por condição, em paralelo no "
                    "servidor) é o passo seguinte, e o F2 não arranca antes: o "
                    "contraste F1 vs F2 é, por desenho, parte do resultado."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
            elif faltam:
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
                ui.label("As quatro condições estão no disco — o F1 está fechado.") \
                    .classes("text-sm font-bold").style("color:#4ade80")
                ui.label(
                    "1680 episódios, e as 84 células a 0,00 nas quatro condições: "
                    "nenhum controlo ressuscita uma única célula, por isso as três "
                    "causas alternativas ficam EXCLUÍDAS e reporta-se a natural — "
                    "é a regra do pré-registo §3, escrita antes dos dados."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
                ui.label(
                    "O zero não é um mapa impossível: um navegador que não aprendeu "
                    "nada (descida do campo geodésico) faz 53,0 recolhas/ep neste "
                    "mesmo mapa, contra 82,0 no Quatro Salas. Há caminho e cabe no "
                    "episódio ⇒ o que o zero mede é transferência, que é o que a "
                    "QI7 pergunta."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
                ui.label(
                    "Veredicto integral: results/mapa_grande/f1_zeroshot_v2/"
                    "f1_veredicto.txt — reproduz-se com "
                    "`python scripts/analise_f1_controlos.py --csv "
                    "results/mapa_grande/f1_zeroshot_v2/*.csv --saida "
                    "results/mapa_grande/f1_zeroshot_v2`."
                ).classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")
