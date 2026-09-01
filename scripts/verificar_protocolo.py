# -*- coding: utf-8 -*-
r"""O vocabulário numérico do protocolo, em toda a dissertação.

Porque existe
Os números que a tese repete mais vezes não são os resultados: são os do
protocolo — «7 execuções», «195 minutos por execução», «20 episódios»,
«$n=28$». Aparecem em prosa espalhada por dez secções, longe das tabelas que os
verificadores conferem, e é por isso que a medição de cobertura os encontra às
centenas por verificar: `contagem de execuções` é o maior grupo do
`COBERTURA_VERIFICADOR.md`, com 124 tokens.

Um erro nestes números não se parece com um erro. Dizer «195 minutos» onde foram
780 não desalinha nenhuma tabela, não muda nenhuma figura, e descreve uma
campanha que não aconteceu — é a frase que um arguente confronta com o
pré-registo.

Este verificador não fixa os valores certos: mede-os. As execuções e os
episódios saem dos `eval_by_run.csv` de todas as campanhas; os orçamentos, dos
scripts que lançaram os treinos; os cenários, de `src/scenarios.py`. Depois
percorre o `.tex` (sem comentários) e exige que cada afirmação de protocolo use
um valor que exista de facto.

O que ele não faz é dizer que a frase certa está no sítio certo: que uma
campanha de 780 minutos não seja descrita com os 195 de outra é leitura humana.
Ele garante o passo anterior — que o número existe em alguma campanha real — e
lista o que encontrou, para que a leitura seja sobre um conjunto pequeno.

Uso:
    .venv/Scripts/python.exe scripts/verificar_protocolo.py
    .venv/Scripts/python.exe scripts/verificar_protocolo.py --listar
"""
import glob
import os
import re
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

TEX = [os.path.join(RAIZ, "Tese", "main.tex"),
       os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex")]

falhas = []
conferidos = 0


def sem_comentarios(caminho):
    with open(caminho, encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", l) for l in linhas)


# O que existe de facto
def medir():
    """Os valores de protocolo que as campanhas realmente usaram."""
    runs, episodios = set(), set()
    for csv in glob.glob(os.path.join(RAIZ, "results", "**", "eval_by_run*.csv"),
                         recursive=True):
        try:
            df = pd.read_csv(csv)
        except Exception:  # noqa: BLE001
            continue
        if not {"Scenario", "Algorithm", "Run"}.issubset(df.columns):
            continue
        por_celula = df.groupby(["Scenario", "Algorithm"])["Run"].nunique()
        runs |= set(int(v) for v in por_celula)
        por_run = df.groupby(["Scenario", "Algorithm", "Run"]).size()
        episodios |= set(int(v) for v in por_run)

    # Os orçamentos vêm dos scripts que lançaram os treinos — **incluindo os
    # arquivados** em `results/novelty_adaptativo/week_stream*.sh`. Sem esses, os
    # braços @390 min da campanha adaptativa apareciam como «campanha que não
    # existiu», que é o oposto do que se quer: eles existiram, e o script que os
    # lançou está guardado ao lado dos dados precisamente para isto.
    minutos = set()
    for sh in (glob.glob(os.path.join(RAIZ, "scripts", "*.sh")) +
               glob.glob(os.path.join(RAIZ, "results", "**", "*.sh"), recursive=True)):
        texto = open(sh, encoding="utf-8", errors="replace").read()
        minutos |= {int(v) for v in re.findall(r"--time[a-z-]*\s+(\d+)", texto)}
        minutos |= {int(v) for v in re.findall(r"MIN_[A-Z]+=\$\{[^:]+:-(\d+)\}", texto)}
        minutos |= {int(v) for v in re.findall(r"TEMPO[A-Z_]*=\$\{[^:]+:-(\d+)\}", texto)}

    # Episódios por geração no treino evolutivo: é protocolo, e vive no config.
    import yaml
    cfg = yaml.safe_load(open(os.path.join(RAIZ, "configs", "foraging.yaml"),
                              encoding="utf-8"))
    for seccao in cfg.values():
        if isinstance(seccao, dict) and "eval_episodes" in seccao:
            episodios.add(int(seccao["eval_episodes"]))

    # O n da revisão sistemática é medido do próprio `screening.csv`.
    estudos = set()
    csv_slr = os.path.join(RAIZ, "docs", "slr", "screening.csv")
    if os.path.exists(csv_slr):
        df = pd.read_csv(csv_slr)
        if "decisao" in df.columns:
            estudos.add(int((df["decisao"] == "incluir").sum()))
            estudos.add(int(len(df)))

    from src.scenarios import SCENARIOS, THESIS_SCENARIOS
    return {
        "execuções": runs,
        "episódios": episodios,
        "minutos": minutos,
        "cenários": {len(SCENARIOS), len(THESIS_SCENARIOS)},
        "estudos": estudos,
    }


# O que a dissertação afirma
# (grupo, padrão). O `(?:\\textit\{|\\emph\{|\\textbf\{)?` cobre as três
# maneiras como a tese escreve «runs» — é assim que a contagem de cobertura os
# viu espalhados por dez secções.
PADROES = [
    ("execuções", r"\$?(\d+)\$?\s*(?:\\textit\{|\\emph\{|\\textbf\{)?"
                  r"(?:execuções|execu\\c\{c\}ões|runs\}|runs\b)"),
    # `\$n\s*=` e não `n\s*=`: sem o cifrão, o padrão apanhava
    # `margin=2.5cm` do preâmbulo e o `\varepsilon = 0{,}2` da equação do PPO —
    # dois «achados» que eram pontuação.
    ("n", r"\$n\s*=\s*(\d+)\$?"),
    ("episódios", r"\$?(\d+)\$?\s*(?:\\textit\{)?episódios?"),
    ("minutos", r"\$?(\d+)\$?\s*(?:\\,)?min(?:utos)?\b"),
    ("cenários", r"\$?(\d+)\$?\s*(?:\\textit\{)?cenários"),
]

# Valores que NÃO descrevem uma campanha, com a razão. Sem isto, o verificador
# acusaria a dissertação de inventar campanhas onde ela mede outra coisa — e a
# resposta seria alargar o conjunto medido até nada falhar, que é a maneira mais
# rápida de tornar um verificador inútil.
EXCECOES = {
    ("episódios", 3): "instrumentação por distância geodésica: 3 episódios "
                      "determinísticos por execução, diagnóstico e não avaliação",
    ("episódios", 6): "heatmaps de ocupação do pipeline canónico (plot_results.py)",
    ("episódios", 50): "teste de geometria do spawn (50 ep × 20 agentes), não é "
                       "avaliação de política",
    ("minutos", 5): "quadro de tempos do pipeline: a avaliação determinística "
                    "demora 5 min, não é orçamento de treino",
    ("minutos", 600): "braço Novelty preliminar de 2 jul — campanha real cujos "
                      "artefactos foram sobrescritos no servidor; a tese "
                      "despromove-a a «indício» e declara a perda",
}

# Totais legítimos que não são «por célula»: produtos do protocolo (7×20=140,
# 21×20=420, 3×21×20=1260, 4×21×20=1680, 3×7×7×20=2940) e somas declaradas.
# Calculam-se, não se escrevem: um total é legítimo se for um produto de valores
# medidos.
def totais_legitimos(medido):
    prod = set()
    for r in medido["execuções"]:
        for e in medido["episódios"]:
            prod.add(r * e)
            for celulas in (2, 3, 4, 7, 8, 21, 24, 28):
                prod.add(r * e * celulas)
    return prod


def verificar(texto=None):
    """`texto=None` lê a dissertação; um texto dado serve os ensaios."""
    global conferidos
    medido = medir()
    totais = totais_legitimos(medido)
    print()
    print("=" * 78)
    print("PROTOCOLO: o que a dissertação afirma  vs  o que as campanhas usaram")
    print("=" * 78)
    for chave in sorted(medido):
        print("  %-11s medidos: %s" % (chave, sorted(medido[chave])))

    # O `$n=...$` da tese não é sempre execuções: é a unidade estatística do que
    # está a ser discutido — execuções, episódios (o único caso declarado como
    # tal no capítulo) ou estudos da revisão sistemática.
    medido["n"] = (medido["execuções"] | medido["episódios"] | medido["estudos"])

    if texto is None:
        texto = "\n".join(sem_comentarios(t) for t in TEX)
    achados = {}
    isentos = 0
    for grupo, padrao in PADROES:
        for m in re.finditer(padrao, texto):
            valor = int(m.group(1))
            conferidos += 1
            if (grupo, valor) in EXCECOES:
                isentos += 1
                continue
            # «4 execuções convergentes» é uma contagem de RESULTADO (quantas
            # resolveram), não o tamanho da campanha — e essa está conferida
            # pelo verificar_mapa_grande.py contra o CSV. Sem esta distinção, o
            # verificador exigiria que todo o resultado fosse também um n de
            # campanha, o que é falso por construção.
            depois = texto[m.end():m.end() + 40].lower()
            if grupo in ("execuções", "n") and re.match(
                    r"\s*(convergentes|que resolvem|que param|a 100|degeneradas|"
                    r"falhadas|com recolha|sem recolha)", depois):
                isentos += 1
                continue
            ok = valor in medido[grupo]
            if grupo in ("episódios", "execuções", "n") and not ok:
                # Um total (7×20=140, 21×20×4=1680) é legítimo se for produto de
                # valores medidos.
                ok = valor in totais
            if not ok:
                ctx = " ".join(texto[max(0, m.start() - 70):m.end() + 40].split())
                achados.setdefault((grupo, valor), []).append(ctx)

    print()
    print("  %d valores de protocolo lidos do texto · %d isentos por razão "
          "declarada" % (conferidos, isentos))
    if not achados:
        print("  [v] todos existem nas campanhas que correram")
        return
    print("  %d valor(es) de protocolo que nenhuma campanha usou:" % len(achados))
    for (grupo, valor), ctxs in sorted(achados.items()):
        print("    [X] %s = %d  (%d ocorrência(s))" % (grupo, valor, len(ctxs)))
        for c in ctxs[:2]:
            print("        …%s…" % c[:110])
        falhas.append("%s = %d não corresponde a nenhuma campanha (%d vezes)"
                      % (grupo, valor, len(ctxs)))


def main():
    verificar()
    print()
    print("=" * 78)
    if falhas:
        print("%d achado(s) — cada um é uma frase a descrever uma campanha que "
              "não existiu, ou um padrão a apanhar prosa" % len(falhas))
    else:
        print("Os %d valores de protocolo batem com as campanhas ✓" % conferidos)
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
