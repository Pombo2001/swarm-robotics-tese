"""Vista «Mapa composto» — o 8.º cenário e a QI7, que é o trabalho em curso.

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
import json
import os
import sys

import pandas as pd
from nicegui import ui

from .. import data, theme

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


ESTADO_F2 = os.path.join(_RAIZ, "results", "estado_f2.json")


def _estado_f2():
    """O instantâneo do servidor gravado por `scripts/estado_f2.sh`, ou None.

    ⚠️ Aqui estava escrito à mão «F2 — arranca 3 ago, quando o megaB largar a
    máquina». A 6 de agosto o F2 corria havia três dias, com 19 de 21 runs de PPO
    fechados — e a frase continuava no ecrã. Uma vista que descreve uma campanha
    viva não pode fazê-lo em prosa fixa: ou lê um instantâneo datado, ou mente
    passado um dia. Quem abre isto no Pi não tem VPN para confirmar nada.
    """
    try:
        with open(ESTADO_F2, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _veredicto_final():
    """A leitura da QI7 pela avaliação, ou None enquanto o GNN não tiver eval.

    A projeção do limiar conta execuções pelo **treino**; esta conta-as pela
    **avaliação determinística**, que é a régua do pré-registo. Enquanto só
    existir a primeira, o painel diz que a decisão está por tomar; assim que o
    `eval_by_run.csv` do GNN aparece, passa a dizer o resultado.

    A regra não vive aqui: importa-se do `medir_f2()` do
    `analise_mapa_grande.py`, o mesmo que o `fechar_qi7.py` usa para escrever
    na dissertação. Duas cópias da regra seriam duas respostas possíveis para a
    mesma pergunta.
    """
    try:
        sys.path.insert(0, os.path.join(_RAIZ, "scripts"))
        from analise_mapa_grande import medir_f2
        m = medir_f2()
    except Exception:                                        # noqa: BLE001
        return None
    if not m or "GNN" not in m.get("por_algo", {}):
        return None
    return m


def _estado_na_dissertacao():
    """A QI7 já está escrita no `.tex`? A frase da vista sai daqui, não à mão.

    Duas condições, ambas lidas do `Tese/main.tex` e ambas necessárias: a
    resposta à QI7 na secção das respostas, e a secção do mapa composto
    incluída (ela viveu meses em comentário, e um `\\input` comentado não
    imprime nada). Enquanto isto foi uma frase fixa, a vista pediu o
    `fechar_qi7.py --escrever` durante três dias depois de a QI7 estar escrita.
    """
    tex_path = os.path.join(_RAIZ, "Tese", "main.tex")
    if not os.path.exists(tex_path):
        return "Falta escrever na dissertação: scripts/fechar_qi7.py --escrever."
    vivas = [linha for linha in open(tex_path, encoding="utf-8").read().splitlines()
             if not linha.lstrip().startswith("%")]
    tem_resposta = any("\\item[QI7" in linha for linha in vivas)
    tem_seccao = any("seccao_mapa_grande" in linha for linha in vivas)
    if tem_resposta and tem_seccao:
        return "Escrito na dissertação: secção do mapa composto e resposta à QI7."
    if tem_seccao:
        return "Secção escrita; falta a resposta à QI7: scripts/fechar_qi7.py --escrever."
    return "Falta escrever na dissertação: scripts/fechar_qi7.py --escrever."


def _limiar_projetado():
    """O limiar ainda é alcançável? Aritmética sobre o que já fechou.

    A tabela por baixo mostra os braços com avaliação no disco (PPO e SAC, a
    zero). O braço do GNN ainda corre, e é dele que o limiar depende — sem esta
    linha, um leitor com 17 de 21 execuções à frente não tem como saber que a
    resposta já está selada desde 13 de agosto: faltam mais convergências do que
    execuções restantes, e a contagem que as conta é a de TREINO, que é o
    majorante otimista da avaliação.

    A conta não vive aqui: importa-se do `projetar_limiar_f2.py`, que é onde o
    pré-registo a fixou. Duplicá-la seria criar duas réguas para o mesmo número.
    """
    e = _estado_f2()
    if not e or "gnn" not in e:
        return
    try:
        sys.path.insert(0, os.path.join(_RAIZ, "scripts"))
        from projetar_limiar_f2 import projetar
        p = projetar(e)
    except Exception:                                        # noqa: BLE001
        return
    if p["estado"] == "em_aberto":
        texto, cor = ("Limiar ainda em aberto: faltam %d convergências e restam "
                      "%d execuções (GNN, contagem de treino)."
                      % (p["faltam"], p["restantes"]), theme.INK_MUTED)
    elif p["estado"] == "atingido":
        texto, cor = ("Limiar ATINGIDO: %d execuções convergentes de %d."
                      % (p["n_convergentes"], p["n_fechados"]), "#4ade80")
    else:
        texto, cor = (
            "Limiar INALCANÇÁVEL: faltam %d convergências e restam %d execuções "
            "(GNN: %d convergentes em %d fechadas, contagem de TREINO — o "
            "majorante otimista da avaliação). Pela emenda 21 do pré-registo, a "
            "QI7 reporta-se como negativa com o número declarado. Qual das "
            "leituras da secção — nenhum resolve, ou resolve em k das %d — "
            "decide-se com a avaliação do GNN, que ainda não existe."
            % (p["faltam"], p["restantes"], p["n_convergentes"],
               p["n_fechados"], p["total"]), "#ffb020")
        # …e quando ela passa a existir, esta frase deixa de ser verdade. A
        # avaliação do GNN chegou a 17 ago; sem esta condição, o dashboard
        # continuava a mandar esperar por um ficheiro que já está no disco —
        # exatamente o género de frase escrita à mão que este painel existe
        # para não ter. O k final sai do `medir_f2()`, que é onde a regra vive.
        final = _veredicto_final()
        if final:
            # O «falta escrever» era uma frase FIXA: continuou a pedir o
            # `fechar_qi7.py --escrever` durante os três dias em que a QI7 já
            # estava escrita, impressa e verificada. Passa a ser lida do
            # `.tex`, como tudo o resto nesta vista.
            texto, cor = (
                "QI7 FECHADA: %d execuções convergentes de %d na avaliação "
                "determinística (limiar %d) ⇒ negativo, leitura (%s). O GNN é o "
                "único que alguma vez resolve o mapa; PPO e SAC ficam a 0. %s"
                % (final["max_convergentes"], final["n_runs"], final["limiar"],
                   final["leitura"], _estado_na_dissertacao()), "#4ade80")
    ui.label(texto).classes("text-xs mb-2").style(f"color:{cor}")
    ui.label("Projeção sobre o instantâneo de %s · scripts/projetar_limiar_f2.py"
             % p["medido_utc"]).classes("text-[10px] mb-2") \
        .style(f"color:{theme.INK_MUTED}")


def _texto_f2():
    """A linha do F2 nas fases, construída do instantâneo (nunca inventada)."""
    e = _estado_f2()
    if e is None:
        return ("lançado a 3 ago (3 algoritmos × 21 execuções, emenda 19); sem "
                "instantâneo do servidor — correr scripts/estado_f2.sh")
    g, n = e.get("grad", {}), e.get("gnn", {})
    prev = g.get("runs_previstos") or 21
    partes = [
        "PPO %s/%s execuções" % (g.get("ppo_runs_concluidos", "?"), prev),
        "SAC %s/%s" % (g.get("sac_runs_concluidos", "?"), prev),
        "GNN adaptativo %s/%s execuções fechadas"
        % (n.get("fechados", "?"), n.get("runs_previstos") or prev),
    ]
    fechados, com = n.get("fechados", 0), n.get("fechados_com_recolha", 0)
    if fechados:
        # O número que interessa e que nenhuma frase dizia: em quantas
        # execuções o mapa composto é RESOLVIDO. Uma execução com 6 recolhas e
        # outra com 0 não é «o mapa composto foi resolvido» — é uma proporção, e
        # é ela que M1 mede.
        partes.append("%d de %d com recolha (%s)"
                      % (com, fechados,
                         ", ".join(theme.num(r["recolhas"], 2)
                                   for r in n.get("runs_fechados", []))))
    if e.get("exploratorio_armado"):
        partes.append("exploratório armado (f2lwatch)")
    return "%s · medido %s" % ("; ".join(partes), e.get("medido_utc", "?"))


def _cor_f2():
    """Verde quando corre — e também quando ACABOU.

    A cor era `verde se tmux_vivos else laranja`, o que servia enquanto a
    campanha estava viva: parada = alguma coisa a precisar de atenção. Fechadas
    as 21 execuções dos três braços, o F2 ficou laranja por baixo de um F0 e um
    F1 verdes, a dizer «pendente» sobre a campanha que respondeu à QI7.
    """
    e = _estado_f2()
    if e is None:
        return theme.INK_MUTED
    if e.get("tmux_vivos"):
        return "#4ade80"
    g, n = e.get("grad", {}), e.get("gnn", {})
    prev = g.get("runs_previstos") or 21
    prev_gnn = n.get("runs_previstos") or prev
    concluido = (g.get("ppo_runs_concluidos", 0) >= prev
                 and g.get("sac_runs_concluidos", 0) >= prev
                 and n.get("fechados", 0) >= prev_gnn)
    return "#4ade80" if concluido else "#ffb020"


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


def _painel_f2():
    """Os resultados MEDIDOS do F2, quando existirem no disco.

    A vista mostrava o F1 inteiro e, do F2, só a linha de estado do servidor —
    quantos runs fecharam. A 10 de agosto o braço dos gradientes terminou e os
    840 episódios ficaram no disco sem aparecer aqui: o resultado mais recente da
    tese, invisível no sítio que existe para o mostrar.

    Ver também `_limiar_projetado`, que diz se o limiar ainda é alcançável.

    Não ESCOLHE a leitura da secção — mas desde 17 ago pode dizer qual é. Há
    duas coisas diferentes, e a vista faz as duas em separado: dizer se o limiar
    ainda é alcançável é aritmética sobre o que já fechou, pelo TREINO; dizer se
    é (B) «nenhum resolve» ou (C) «resolve em k das 21» exige o
    `eval_by_run.csv` do GNN. Enquanto ele não existia, a vista dizia que a
    decisão estava por tomar; agora que existe, mostra o k medido (4 de 21) e a
    leitura que a regra dá. Confundir as duas contagens foi o erro que o
    `projetar_limiar_f2.py` cometeu e que se corrigiu a 13 ago — continuam
    separadas, cada uma com a sua régua.

    Escrever isto na dissertação é um ato à parte (`fechar_qi7.py --escrever`).
    A vista diz em que pé está — lendo o `.tex`, não uma frase fixa: a QI7 foi
    escrita a 17 de agosto e o painel continuou a pedir que a escrevessem.
    """
    r = data.f2_resultados()
    if not r:
        return
    with ui.card().classes(CARD + " w-full"):
        ui.label("F2 — treino nativo: o que já está medido") \
            .classes("text-sm font-bold mb-1")
        ui.label(
            "%d episódios de avaliação determinística, %d execuções por braço. "
            "Limiar do pré-registo para a QI7: ⌈5/7 × %d⌉ = %d execuções "
            "convergentes em pelo menos um algoritmo."
            % (r["episodios"], r["n"], r["n"], r["limiar"])
        ).classes("text-xs mb-2").style(f"color:{theme.INK_MUTED}")
        _limiar_projetado()

        with ui.grid(columns=5).classes("w-full gap-px"):
            for cab in ("algoritmo", "execuções", "convergentes",
                        "recolhas/ep", "porta aberta"):
                ui.label(cab).classes("text-[10px] py-1") \
                    .style(f"color:{theme.INK_MUTED}")
            for a in r["algos"]:
                ui.label(a["algo"]).classes("text-xs font-bold py-1")
                ui.label("%d" % a["runs"]).classes("text-xs mono-num py-1")
                lbl = ui.label("%d de %d" % (a["convergentes"], a["runs"])) \
                    .classes("text-xs mono-num py-1")
                if a["convergentes"] >= r["limiar"]:
                    lbl.style("color:#4ade80")
                elif a["convergentes"] == 0:
                    lbl.style(f"color:{theme.INK_MUTED}")
                ui.label("%s ± %s" % (theme.num(a["media"], 2),
                                     theme.num(a["dp"], 2))) \
                    .classes("text-xs mono-num py-1")
                ui.label("—" if a["porta"] is None else "%.0f%%" % (100 * a["porta"])) \
                    .classes("text-xs mono-num py-1")

        em_falta = [a for a in ALGOS if a not in {x["algo"] for x in r["algos"]}]
        if em_falta:
            ui.label("A correr, ainda sem avaliação no disco: %s."
                     % ", ".join(em_falta)) \
                .classes("text-xs mt-2").style("color:#ffb020")
        if r["falhas"]:
            # O sidecar do eval_by_run.py: execuções que não entraram no CSV. O n
            # decide o limiar, por isso isto não pode ficar só no terminal de
            # quem correu a avaliação.
            ui.label("⚠ Há execuções que falharam a avaliar (%s). O n em cima "
                     "está incompleto e o limiar desceu com ele."
                     % ", ".join(r["falhas"])) \
                .classes("text-xs mt-2 font-bold").style("color:#ef4444")
        ui.label("Fonte: %s" % ", ".join(r["fontes"])) \
            .classes("text-[10px] mt-2").style(f"color:{theme.INK_MUTED}")


def build():
    with ui.column().classes("w-full gap-4 p-4"):
        theme.section_title(
            "map", "Mapa composto (8.º cenário)",
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
                ("F2 — treino nativo", _texto_f2(), _cor_f2()),
            ]
            for nome, estado, cor in fases:
                with ui.row().classes("items-center gap-3 no-wrap w-full py-1"):
                    ui.element("div").style(
                        "width:8px;height:8px;border-radius:50%%;background:%s;"
                        "flex:none" % cor)
                    ui.label(nome).classes("text-xs font-bold w-56 shrink-0")
                    ui.label(estado).classes("text-xs") \
                        .style(f"color:{theme.INK_MUTED}")

        _painel_f2()

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
                                                         else theme.num(v))
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
