"""Vista «Defesa» — a tese contada por questão de investigação, um ecrã de cada vez.

O F4 que faltava no plano. A ideia não é substituir os *slides*: é ter, na sala,
um ecrã por **pergunta** com a resposta ao lado do número que a sustenta — e que
esse número venha dos **dados**, não de um `.pptx` escrito há três semanas.

O texto (pergunta e resposta) é lido do `Tese/main.tex`: as perguntas da secção
`sec:questoes_investigacao`, as respostas da `sec:resposta_qi`. Não há aqui uma
segunda versão da narrativa — se a tese mudar, isto muda com ela. O que este
módulo acrescenta é o **número em destaque** de cada questão, calculado dos CSV
canónicos no momento em que se abre a vista.

Navegação: setas ← → do teclado (numa sala não se procura o rato), ou os botões.
"""
import glob
import json
import os
import re
import sys

import pandas as pd
from nicegui import ui

from .. import theme
# Os meses vêm do `data`, e não de uma cópia local: já há três listas iguais no
# projeto, e cinco vocabulários de cenário foi o que a segunda passagem gastou
# uma manhã a juntar.
from ..data import _MESES_PT

CARD = theme.CARD + " p-6"
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAIN_TEX = os.path.join(_RAIZ, "Tese", "main.tex")
CSV_7D = os.path.join(_RAIZ, "results", "graficos_tese", "final_7d",
                      "eval_by_run_7d.csv")
DIR_EST = os.path.join(_RAIZ, "results", "estatisticas")
ESTADO_F2 = os.path.join(_RAIZ, "results", "estado_f2.json")


def _data_pt(iso):
    """'2026-08-17T08:37Z' -> '17 ago'.

    O instantâneo é escrito por um script de shell e traz a hora em ISO/UTC,
    que é a forma certa de a gravar. Não é a forma de a mostrar: este texto
    aparece no ecrã da QI7 — o último da defesa — e lia-se «em
    2026-08-17T08:37Z» num painel em português. É o mesmo defeito que a segunda
    passagem encontrou no cartão Prontidão, onde o `%b` escrevia «22 Aug».
    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return None
    return "%d %s" % (int(m.group(3)), _MESES_PT[int(m.group(2)) - 1])


def _estado_f2_curto():
    """Uma frase sobre o F2, do instantâneo datado — ou o reconhecimento de que
    não há instantâneo. Nunca uma afirmação escrita à mão sobre o presente.

    São TRÊS estados, e não dois. A versão anterior só distinguia «a correr» de
    tudo o resto, e escrevia para tudo o resto «F2 sem sessões vivas» — jargão
    de tmux, que num ecrã de defesa se lê como avaria. O F2 fechou: as 21
    execuções do GNN e as 21 de cada gradiente estão todas concluídas. Estar
    sem sessões vivas é, aqui, o fim do trabalho, e não a sua interrupção.

    É o defeito nº3 da segunda passagem — «o F2 laranja por estar parado,
    quando parado ali quer dizer concluído» —, que tinha sido corrigido na
    vista do mapa composto e sobreviveu aqui, em texto.
    """
    try:
        with open(ESTADO_F2, encoding="utf-8") as fh:
            e = json.load(fh)
    except (OSError, ValueError):
        return "estado do F2 por medir (scripts/estado_f2.sh)"
    n, g = e.get("gnn", {}), e.get("grad", {})
    quando = _data_pt(e.get("medido_utc"))
    em = " em %s" % quando if quando else ""
    if e.get("tmux_vivos"):
        return ("F2 a correr%s: PPO %s/%s execuções, GNN %s de %s execuções "
                "fechadas com recolha"
                % (em, g.get("ppo_runs_concluidos", "?"),
                   g.get("runs_previstos", "?"),
                   n.get("fechados_com_recolha", "?"), n.get("fechados", "?")))

    # Parado. Concluído ou interrompido? Quem responde é a contagem, não o
    # tmux: se as execuções previstas fecharam todas, o F2 acabou.
    previstas = g.get("runs_previstos")
    fecharam = [n.get("fechados"), g.get("ppo_runs_concluidos"),
                g.get("sac_runs_concluidos")]
    if previstas and all(x == previstas for x in fecharam):
        return ("F2 concluído%s: %d execuções por algoritmo"
                % (em, previstas))
    return ("F2 parado%s com execuções por fechar (GNN %s, PPO %s, SAC %s "
            "de %s)" % (em, n.get("fechados", "?"),
                        g.get("ppo_runs_concluidos", "?"),
                        g.get("sac_runs_concluidos", "?"), previstas or "?"))
# v2 = a repetição do F1 no mundo corrigido; a pasta sem sufixo está ANULADA.
DIR_F1_V2 = os.path.join(_RAIZ, "results", "mapa_grande", "f1_zeroshot_v2")

# QI6 — o mega-treino de um mês, no Muro em U. As duas fases são os dois braços
# que o `verificar_numeros_tese.py` compara para o M1 do pré-registo: a fase 1 é
# a dosagem adaptativa, a fase 2 o objetivo puro.
MEGA_QI6 = {b: os.path.join(_RAIZ, "results", "mega_1mes", f,
                            "evaluation", "eval_by_run.csv")
            for b, f in (("adaptativo", "mega_A_fase1"),
                         ("objetivo", "mega_A_fase2"))}

# Cenários com gargalo — os quatro que a fitness de homing desbloqueou (QI5).
GARGALOS = ("bottleneck", "four_rooms", "cooperative_door",
            "cooperative_door_bypass")


def _limpar(tex):
    """LaTeX -> texto corrido legível. Conservador: o que não sabe, deixa."""
    t = tex
    t = re.sub(r"\\(label|index)\{[^}]*\}", "", t)
    t = re.sub(r"\\cite\{[^}]*\}", "", t)
    t = re.sub(r"(Secção|Capítulo|Tabela|Figura|Apêndice)~\\ref\{[^}]*\}", "", t)
    t = re.sub(r"\\ref\{[^}]*\}", "", t)
    t = re.sub(r"\\(textbf|textit|emph|texttt|mathbf)\{([^{}]*)\}", r"\2", t)
    t = re.sub(r"\\(textbf|textit|emph|texttt|mathbf)\{([^{}]*)\}", r"\2", t)
    t = t.replace("\\%", "%").replace("{,}", ",").replace("\\,", " ")
    t = re.sub(r"\$([^$]*)\$", r"\1", t)
    t = t.replace("\\times", "×").replace("\\pm", "±").replace("\\delta", "δ")
    t = t.replace("\\neq", "≠").replace("\\approx", "≈").replace("\\geq", "≥")
    # `vs.\ MLP`: espaço escapado do LaTeX. Tem de sair ANTES de se comerem
    # as barras soltas, senão fica "vs.MLP" colado.
    t = t.replace("\\ ", " ")
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("{", "").replace("}", "")
    t = t.replace("---", "—").replace("--", "–").replace("``", "\u201c") \
         .replace("''", "\u201d")
    # Tirar uma referência deixa a pontuação que a rodeava:
    # `(Capítulo~\ref{...})` fica `()`, e `(ver \ref{...}, p. 3)` fica
    # `(ver , p. 3)`. Sem isto a resposta à QI1 acabava em "(Muro U) ()." —
    # que foi exatamente o que apareceu no primeiro ecrã desta vista.
    t = re.sub(r"\(\s*[,;.]?\s*\)", "", t)
    t = re.sub(r"\(\s*,\s*", "(", t)
    t = re.sub(r"\s+([,.;:])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _questoes():
    """{n: (pergunta, declarada)} da secção das questões de investigação.

    Duas subtilezas, ambas apanhadas a 14 ago no ecrã da QI7:

    · a pergunta pode ocupar VÁRIAS linhas do `.tex`. O `.+` da versão anterior
      parava na primeira, e a QI7 aparecia na defesa como «Composição de
      dificuldades: As conclusões» — cortada a meio da frase, num ecrã feito
      para ser projetado;
    · a QI7 vive em COMENTÁRIO até a secção do mapa composto entrar, e o regex
      não distinguia comentário de texto. A pergunta mostra-se na mesma (não
      depende do resultado — é a pergunta, não a resposta), mas quem defende
      tem de saber que ainda não está na tese: é para isso que serve o segundo
      elemento do par.
    """
    if not os.path.exists(MAIN_TEX):
        return {}
    tex = open(MAIN_TEX, encoding="utf-8").read()
    i = tex.find(r"\label{sec:questoes_investigacao}")
    if i < 0:
        return {}
    # Só a lista das questões: fora dela há três respostas comentadas à QI7,
    # nos três desfechos possíveis, e nenhuma delas é uma pergunta.
    bloco = tex[i:tex.find(r"\end{enumerate}", i)]
    saida = {}
    # Cada \item vai até ao \item seguinte (ou ao fim do bloco) — é assim que
    # se apanha uma pergunta escrita em cinco linhas. O `%?` no lookahead
    # existe porque a QI7 está comentada e o item seguinte também começa por %.
    for m in re.finditer(r"\\item\[\\textbf\{QI(\d)\.\}\](.*?)(?=\s*%?\s*\\item\[|\Z)",
                         bloco, re.S):
        linha = bloco.rfind("\n", 0, m.start()) + 1
        declarada = not bloco[linha:m.start()].lstrip().startswith("%")
        # O `%` quer dizer coisas opostas conforme o item esteja comentado ou
        # não, e tratá-lo de uma só maneira custou o ecrã da QI6.
        #
        # · Numa pergunta COMENTADA, o `%` que abre cada linha é decoração do
        #   ficheiro, não texto da pergunta: tira-se e o texto fica.
        # · Numa pergunta DECLARADA, uma linha comentada dentro do corpo é uma
        #   nota do autor sobre o ficheiro. Tirar-lhe o `%` promove-a a texto.
        #   Foi o que aconteceu quando a QI7 foi descomentada a 17 de agosto e
        #   a nota que explicava a mudança ficou entre a QI6 e a QI7: a QI6
        #   passou a ler-se, no ecrã projetado, «...face à otimização puramente
        #   objetiva? ── QI7: a PERGUNTA, não a resposta. (...) Reposta na
        #   ordem a 18 de agosto.» Aqui a linha inteira sai.
        linhas = m.group(2).split("\n")
        if declarada:
            linhas = [l for l in linhas if not l.lstrip().startswith("%")]
        else:
            linhas = [re.sub(r"^\s*%", "", l) for l in linhas]
        texto = "\n".join(linhas)
        saida[int(m.group(1))] = (_limpar(texto), declarada)
    return saida


def _respostas():
    """{n: resposta} da secção «Resposta às Questões de Investigação».

    A resposta vai do fecho do `\\item[...]` até ao `\\item` seguinte — e não
    até ao fim da linha. As respostas às QI1-QI6 estão escritas numa linha só e
    o `(.+)` de antes servia-as por acaso; a da QI7, escrita pelo
    `fechar_qi7.py` com o parágrafo mudado de linha, aparecia na vista da Defesa
    como **«Parcialmente, e ao preço»** — meia frase, no último ecrã, que é o
    que o júri lê no fim. Ver `test_dashboard_conteudo.py`, que passou a exigir
    que cada resposta acabe em ponto final.
    """
    if not os.path.exists(MAIN_TEX):
        return {}
    tex = open(MAIN_TEX, encoding="utf-8").read()
    i = tex.find("\\label{sec:resposta_qi}")
    bloco = tex[i:tex.find("\\section{Limitações", i)] if i >= 0 else ""
    saida = {}
    padrao = (r"\\item\[QI(\d) --- ([^\]]*)\]\s*(.+?)"
              r"(?=\\item\[QI|\\end\{description\}|\\end\{itemize\}|\Z)")
    for m in re.finditer(padrao, bloco, re.DOTALL):
        saida[int(m.group(1))] = _limpar(m.group(3))
    return saida


def _numeros():
    """O número em destaque de cada questão, calculado dos CSV.

    Só para as questões cuja fonte está no disco: a QI4 é síntese das outras e
    não tem dados próprios. A QI7 passou a ter número a 2 ago — o F1 (zero-shot)
    fechou; o que falta é o F2 (treino nativo), e o ecrã di-lo.

    A QI6 esteve sem número até 24 ago, e o ecrã dizia dela «número não
    disponível no disco» — o que era falso. O mega-treino de um mês está em
    `results/mega_1mes/` desde 3 de agosto, é dele que a tese tira o `28/28`
    contra `15/28`, e é o resultado mais forte da dissertação: a única condição
    sem uma única execução falhada no cenário que resistia aos três algoritmos
    base. Ficar sem número em destaque punha-o abaixo da QI3 num ecrã de defesa.
    """
    n = {}
    if os.path.exists(CSV_7D):
        d = pd.read_csv(CSV_7D)
        # QI5 — a fitness de homing nos quatro cenários de gargalo
        g = d[d["Scenario"].isin(GARGALOS) & (d["Algorithm"] == "GNN")]
        if len(g):
            por_run = g.groupby(["Scenario", "Run"])["success"].mean()
            n[5] = ("%d/%d" % ((por_run == 1.0).sum(), len(por_run)),
                    "execuções do GNN a 100% nos quatro cenários de gargalo")
        # QI1 — em quantos cenários há diferença significativa
        fp = os.path.join(DIR_EST, "testes_significancia_food_collected.csv")
        if os.path.exists(fp):
            s = pd.read_csv(fp, encoding="utf-8", encoding_errors="replace")
            n[1] = ("%d/%d" % (int(s["significant"].sum()), len(s)),
                    "comparações com diferença significativa (21 pares)")

    # QI2 — escalabilidade: células a 100% de sucesso
    celulas = total = 0
    for fp in os.listdir(DIR_EST) if os.path.isdir(DIR_EST) else []:
        # ...e só os CSV: a mesma pasta tem `escalabilidade_zeroshot_*.png`, que
        # o prefixo sozinho apanhava (e o pandas rebentava a lê-los como texto).
        if not (fp.startswith("escalabilidade_") and fp.endswith(".csv")):
            continue
        e = pd.read_csv(os.path.join(DIR_EST, fp))
        g = e[e["Algorithm"] == "GNN"]
        total += len(g)
        celulas += int((g["success_rate"] >= 1.0).sum())
    if total:
        n[2] = ("%d/%d" % (celulas, total),
                "células cenário × dimensão a 100% de sucesso (N=10 a 100)")

    # QI3 — robustez: intervalo de retenção
    d_eval = os.path.join(_RAIZ, "results", "evaluation")
    ret = []
    if os.path.isdir(d_eval):
        for f in os.listdir(d_eval):
            if not f.endswith("_fail10.csv"):
                continue
            base = os.path.join(d_eval, f.replace("_fail10", ""))
            if not os.path.exists(base):
                continue
            b = pd.read_csv(base)["food_collected"].mean()
            k = pd.read_csv(os.path.join(d_eval, f))["food_collected"].mean()
            if b > 0:
                ret.append(100.0 * k / b)
    if ret:
        n[3] = ("%.0f–%.0f%%" % (min(ret), max(ret)),
                "retenção com 10%% de falhas, nas %d combinações" % len(ret))

    # QI6 — dosagem adaptativa da novidade no Muro em U, no mega-treino (n=28).
    # Uma execução conta como resolvida quando faz 100% dos episódios, que é o
    # critério do Fisher exato do M1 — o mesmo que o verificador da tese aplica.
    conv = {}
    for braco, fp in MEGA_QI6.items():
        if not os.path.exists(fp):
            continue
        d = pd.read_csv(fp)
        d = d[d["Scenario"] == "u_wall"] if "Scenario" in d.columns else d
        if d.empty:
            continue
        por_run = d.groupby("Run" if "Run" in d.columns else d.columns[0]) \
                   ["success"].mean()
        conv[braco] = (int((por_run >= 1.0).sum()), len(por_run))
    if "adaptativo" in conv:
        ok, tot = conv["adaptativo"]
        contra = (", contra %d/%d do objetivo puro" % conv["objetivo"]
                  if "objetivo" in conv else "")
        n[6] = ("%d/%d" % (ok, tot),
                "execuções da dosagem adaptativa a 100%% no Muro em U%s"
                % contra)

    # QI7 — zero-shot de topologia (F1). Lê a pasta v2: a `f1_zeroshot/` é a
    # corrida anulada de 27-28 jul (mundo com 45 m de céu por cima das paredes).
    zeros = celulas_f1 = episodios = 0
    for fp in sorted(glob.glob(os.path.join(DIR_F1_V2, "zeroshot_*.csv"))):
        z = pd.read_csv(fp)
        episodios += len(z)
        por_celula = z.groupby(["Algorithm", "Origem"])["food_collected"].mean()
        celulas_f1 += len(por_celula)
        zeros += int((por_celula == 0).sum())
    if celulas_f1:
        # Dizia «o F2 ainda não correu» depois de ele ter corrido, e de já
        # tinha runs fechados. O estado do F2 lê-se do instantâneo, para esta
        # frase não voltar a envelhecer sozinha (scripts/estado_f2.sh).
        n[7] = ("%d/%d" % (zeros, celulas_f1),
                "células a zero recolhas no mapa composto, sem retreino "
                "(%d episódios, 4 condições) — %s"
                % (episodios, _estado_f2_curto()))
    return n


def build():
    perguntas, respostas, numeros = _questoes(), _respostas(), _numeros()
    ordem = sorted(set(perguntas) | set(respostas))
    if not ordem:
        with ui.column().classes("w-full p-4"):
            ui.label("Não consegui ler as questões do main.tex.") \
                .classes("text-sm font-bold")
        return

    estado = {"i": 0}

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("items-center gap-3 w-full no-wrap"):
            theme.section_title("record_voice_over", "Defesa",
                                "uma questão por ecrã · setas ← → para navegar")
            ui.space()
            passos = ui.label("").classes("text-xs mono-num") \
                .style(f"color:{theme.INK_MUTED}")

        alvo = ui.column().classes("w-full")

        def desenhar():
            n = ordem[estado["i"]]
            passos.text = "QI%d · %d de %d" % (n, estado["i"] + 1, len(ordem))
            alvo.clear()
            with alvo:
                with ui.card().classes(CARD + " w-full"):
                    ui.label("QUESTÃO DE INVESTIGAÇÃO %d" % n).classes(
                        "text-[10px] font-bold tracking-[.25em]") \
                        .style(f"color:{theme.INK_MUTED}")
                    texto_q, declarada = perguntas.get(n, ("—", True))
                    ui.label(texto_q).classes(
                        "text-xl font-bold leading-snug mt-1"
                        + ("" if declarada else " mb-1"))
                    if not declarada:
                        ui.label("· pergunta ainda não declarada na tese — "
                                 "entra com a secção do mapa composto") \
                            .classes("text-xs mb-4") \
                            .style(f"color:{theme.INK_MUTED}")
                    else:
                        ui.element("div").classes("mb-4")

                    if n in numeros:
                        valor, legenda = numeros[n]
                        with ui.row().classes("items-baseline gap-3 mb-4"):
                            ui.label(valor).classes(
                                "text-5xl font-bold mono-num")
                            ui.label(legenda).classes("text-sm") \
                                .style(f"color:{theme.INK_MUTED}")

                    ui.separator()
                    ui.label("RESPOSTA").classes(
                        "text-[10px] font-bold tracking-[.25em] mt-3") \
                        .style(f"color:{theme.INK_MUTED}")
                    ui.label(respostas.get(n, "—")).classes(
                        "text-sm leading-relaxed mt-1")

                    if n not in numeros:
                        ui.label(
                            "· sem número próprio: a QI4 sintetiza as outras"
                            if n == 4 else "· número não disponível no disco"
                        ).classes("text-xs mt-3").style(f"color:{theme.INK_MUTED}")

        def andar(passo):
            estado["i"] = (estado["i"] + passo) % len(ordem)
            desenhar()

        with ui.row().classes("items-center gap-2"):
            ui.button(icon="chevron_left", on_click=lambda: andar(-1)) \
                .props('flat dense round aria-label="Questão anterior"')
            ui.button(icon="chevron_right", on_click=lambda: andar(1)) \
                .props('flat dense round aria-label="Questão seguinte"')
            ui.label("ou use as setas do teclado").classes("text-xs") \
                .style(f"color:{theme.INK_MUTED}")

        # Numa sala, procurar o rato é pior do que decorar duas teclas.
        ui.keyboard(on_key=lambda e: (
            andar(1) if (e.action.keydown and e.key.arrow_right) else
            andar(-1) if (e.action.keydown and e.key.arrow_left) else None))

        desenhar()
