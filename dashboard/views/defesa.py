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
import os
import re
import sys

import pandas as pd
from nicegui import ui

from .. import theme

CARD = theme.CARD + " p-6"
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAIN_TEX = os.path.join(_RAIZ, "Tese", "main.tex")
CSV_7D = os.path.join(_RAIZ, "results", "graficos_tese", "final_7d",
                      "eval_by_run_7d.csv")
DIR_EST = os.path.join(_RAIZ, "results", "estatisticas")
# v2 = a repetição do F1 no mundo corrigido; a pasta sem sufixo está ANULADA.
DIR_F1_V2 = os.path.join(_RAIZ, "results", "mapa_grande", "f1_zeroshot_v2")

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
    """{n: pergunta} da secção das questões de investigação."""
    if not os.path.exists(MAIN_TEX):
        return {}
    tex = open(MAIN_TEX, encoding="utf-8").read()
    saida = {}
    for m in re.finditer(r"\\item\[\\textbf\{QI(\d)\.\}\]\s*(.+)", tex):
        saida[int(m.group(1))] = _limpar(m.group(2))
    return saida


def _respostas():
    """{n: resposta} da secção «Resposta às Questões de Investigação»."""
    if not os.path.exists(MAIN_TEX):
        return {}
    tex = open(MAIN_TEX, encoding="utf-8").read()
    i = tex.find("\\label{sec:resposta_qi}")
    bloco = tex[i:tex.find("\\section{Limitações", i)] if i >= 0 else ""
    saida = {}
    for m in re.finditer(r"\\item\[QI(\d) --- ([^\]]*)\]\s*(.+)", bloco):
        saida[int(m.group(1))] = _limpar(m.group(3))
    return saida


def _numeros():
    """O número em destaque de cada questão, calculado dos CSV.

    Só para as questões cuja fonte está no disco: a QI4 é síntese das outras e
    não tem dados próprios. A QI7 passou a ter número a 2 ago — o F1 (zero-shot)
    fechou; o que falta é o F2 (treino nativo), e o ecrã di-lo.
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
        n[7] = ("%d/%d" % (zeros, celulas_f1),
                "células a zero recolhas no mapa composto, sem retreino "
                "(%d episódios, 4 condições) — o F2 ainda não correu"
                % episodios)
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
                    ui.label(perguntas.get(n, "—")).classes(
                        "text-xl font-bold leading-snug mt-1 mb-4")

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
                .props("flat dense round")
            ui.button(icon="chevron_right", on_click=lambda: andar(1)) \
                .props("flat dense round")
            ui.label("ou use as setas do teclado").classes("text-xs") \
                .style(f"color:{theme.INK_MUTED}")

        # Numa sala, procurar o rato é pior do que decorar duas teclas.
        ui.keyboard(on_key=lambda e: (
            andar(1) if (e.action.keydown and e.key.arrow_right) else
            andar(-1) if (e.action.keydown and e.key.arrow_left) else None))

        desenhar()
