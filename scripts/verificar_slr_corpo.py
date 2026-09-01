# -*- coding: utf-8 -*-
"""Os números que a tese afirma sobre o CORPO da revisão têm de onde sair?

O problema
A tese caracteriza os 58 estudos incluídos com três números:

  · «21 dos 58 estudos incluídos assentam em MARL e 23 em otimização
    bio-inspirada»
  · «30 dos 58 abordam a escalabilidade ou a generalização a dimensões de
    enxame não vistas»

Nenhum deles é reproduzível a partir do repositório. O `docs/slr/screening.csv`
regista `decisao` e `motivo` — mas os 58 incluídos têm `motivo` e `notas`
VAZIOS (o motivo serve para justificar exclusões), e o apêndice gerado só tem
autores, ano, título e publicação. A classificação por paradigma vive apenas na
leitura que o autor fez, e a tese afirma, no mesmo capítulo, que o processo é
auditável a partir do registo.

O que isto faz
Corrobora os três números por uma via independente e com as regras à vista:
recupera os RESUMOS dos exports do Scopus/IEEE (`docs/slr/raw/`) e classifica
por expressões regulares. Não é a classificação do autor nem a substitui — é uma
segunda medição, do género que se faz para confirmar uma contagem.

Resultado a 5 ago 2026 (58/58 resumos recuperados):

    só MARL          21   tese: 21   ✓
    só bio-inspirada 24   tese: 23   (+1)
    escalabilidade   31   tese: 30   (+1)

Diferenças de uma unidade são o que se espera entre palavras-chave e leitura;
os três números da tese ficam corroborados. O que continua em falta é a fonte
primária: a classificação do autor devia estar no `screening.csv`, em colunas
próprias, para quem audite não depender desta aproximação.

Uso:
    .venv/Scripts/python.exe scripts/verificar_slr_corpo.py
    .venv/Scripts/python.exe scripts/verificar_slr_corpo.py --listar
"""
import argparse
import glob
import os
import re
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENING = os.path.join(RAIZ, "docs", "slr", "screening.csv")
RAW = os.path.join(RAIZ, "docs", "slr", "raw")
TEX = os.path.join(RAIZ, "Tese", "main.tex")

# As regras, à vista. Cada uma é uma afirmação sobre o que caracteriza o grupo.
MARL = (r"reinforcement learning|q-learning|\bmarl\b|deep rl|actor.critic|"
        r"policy gradient|\bppo\b|\bdqn\b|reward function|markov decision|"
        r"learn(?:ed|ing) polic|multi.agent reinforcement")
BIO = (r"particle swarm|\bpso\b|evolutionary|evolution strateg|genetic algorithm|"
       r"novelty search|\bneat\b|ant colony|bio.inspired|swarm intelligence|"
       r"firefly|grey wolf|bee colony|physarum|automatic design|fitness function|"
       r"metaheuristic|fuzzy")
ESCALA = (r"scalab|scale (?:up|to)|scaling|generaliz|varying (?:the )?number|"
          r"swarm.scale|number of robots|large.scale|transferab|unseen|"
          r"different (?:swarm|team) size|arbitrary number")

TOLERANCIA = 3      # diferença aceitável entre palavras-chave e leitura


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())[:90]


def _resumos():
    saida = {}
    ieee = os.path.join(RAW, "ieee.csv")
    if os.path.exists(ieee):
        d = pd.read_csv(ieee)
        for _, r in d.iterrows():
            saida[_norm(r.get("Document Title"))] = str(r.get("Abstract", ""))
    sco = os.path.join(RAW, "scopus.csv")
    if os.path.exists(sco):
        d = pd.read_csv(sco)
        col = next((c for c in d.columns if "abstract" in c.lower()), None)
        for _, r in d.iterrows():
            k = _norm(r.get("Title"))
            if col and (k not in saida or not saida[k].strip()):
                saida[k] = str(r.get(col, ""))
    return saida


def _da_tese():
    """Lê os três números DO .tex — fixá-los aqui seria verificar o script."""
    tex = open(TEX, encoding="utf-8").read()
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    n = {}
    m = re.search(r"(\d+) dos 58 estudos incluídos assentam em MARL e (\d+) em "
                  r"otimização bio-inspirada", tex)
    if m:
        n["marl"], n["bio"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"\\textbf\{(\d+) dos (\d+)\} abordam a escalabilidade", tex)
    if m:
        n["escala"], n["total"] = int(m.group(1)), int(m.group(2))
    return n


def _conferir_registo(incl):
    """O `screening.csv` regista a classificação? E bate com esta medição?

    A partir de 14 ago o registo tem colunas próprias (`scripts/classificar_slr.py`),
    e é isso que torna os números da tese auditáveis por quem não corra este
    script. O papel daqui muda em conformidade: em vez de ser a única medição,
    passa a ser a SEGUNDA — mede outra vez, e compara com o que está escrito.

    Uma divergência não é forçosamente um erro. Uma linha marcada `manual` é a
    leitura do autor sobre o texto integral, que ganha às palavras-chave; o que
    se exige é que esteja declarada como tal. O que é mesmo um problema é uma
    linha incluída sem classificação nenhuma: aí o número da tese volta a não
    ter de onde sair.
    """
    print()
    print("  ── o registo (docs/slr/screening.csv) ──")
    if "paradigma" not in incl.columns:
        print("  ⚠️ SEM as colunas de classificação: os números da tese não são")
        print("     auditáveis a partir do registo. Correr:")
        print("       python scripts/classificar_slr.py --escrever")
        return ["screening.csv sem colunas de classificação"]

    par = incl["paradigma"].fillna("").astype(str).str.strip()
    fonte = incl["classificacao_fonte"].fillna("").astype(str).str.strip()
    por_classificar = int((par == "").sum())
    manuais = int((fonte == "manual").sum())
    print("  %d de %d classificados no registo (%d à mão, %d por regra)"
          % (len(incl) - por_classificar, len(incl), manuais,
             len(incl) - por_classificar - manuais))

    esperado = incl.apply(
        lambda r: ("ambos" if r["marl"] and r["bio"] else
                   "marl" if r["marl"] else "bio" if r["bio"] else "nenhum"),
        axis=1)
    divergem = incl[(par != "") & (par != esperado)]
    for _, r in divergem.iterrows():
        marca = "leitura do autor" if str(
            r["classificacao_fonte"]).strip() == "manual" else "⚠ POR EXPLICAR"
        print("    · registo diz «%s», palavras-chave dizem «%s» — %s: %s"
              % (r["paradigma"], esperado[r.name], marca,
                 str(r["titulo"])[:52]))

    problemas = []
    if por_classificar:
        print("  ⚠️ %d incluídos SEM classificação no registo." % por_classificar)
        problemas.append("%d incluídos sem classificação" % por_classificar)
    nao_explicadas = divergem[divergem["classificacao_fonte"].astype(str).str.strip()
                              != "manual"]
    if len(nao_explicadas):
        problemas.append("%d linhas divergem sem estarem marcadas `manual`"
                         % len(nao_explicadas))
    if not problemas:
        print("  ✓ o registo cobre os 58 e é consistente com esta medição.")
    return problemas


def _cadeia_prisma(scr, incl):
    """Os três números do fluxograma somam, e vêm dos ficheiros que os produzem?

    O PRISMA do Capítulo 3 é uma cadeia: $883$ registos identificados nas duas
    bases, $680$ depois de desduplicar, $622$ excluídos e $58$ incluídos. Cada
    elo tem uma fonte no repositório — os exports em `docs/slr/raw/`, o registo
    de triagem —, e nenhum verificador os ligava. É o capítulo em que este
    projeto já teve um PRISMA fabricado (13 jul), e é por isso que os
    números dele são os que menos se podem afirmar sem prova.

    Confere-se a soma dos exports contra o total identificado, e a aritmética
    da triagem contra o registo. A desduplicação (883 → 680) não se recalcula:
    o critério vive no `slr_pipeline.py` e repeti-lo aqui seria criar uma
    segunda resposta para a mesma pergunta; o que se exige é que o número que
    a tese escreve seja o que o registo tem.
    """
    tex = "\n".join(l for l in open(TEX, encoding="utf-8").read().split("\n")
                    if not l.lstrip().startswith("%"))
    problemas = []
    print("\n  ── a cadeia do PRISMA ──")

    brutos = {}
    for f in sorted(glob.glob(os.path.join(RAIZ, "docs", "slr", "raw", "*.csv"))):
        brutos[os.path.basename(f)[:-4]] = len(pd.read_csv(f, on_bad_lines="skip"))
    total_bruto = sum(brutos.values())

    m = re.search(r"\b(\d{3})\b registos", tex) or re.search(r"n = (\d{3})", tex)
    identificados = int(m.group(1)) if m else None
    detalhe = " + ".join("%s %d" % (k, v) for k, v in sorted(brutos.items()))
    ok = identificados == total_bruto
    print("  %s identificados: exports %s = %d | tese %s"
          % ("[v]" if ok else "[X]", detalhe, total_bruto, identificados))
    if not ok:
        problemas.append("identificados: os exports somam %d e a tese diz %s"
                         % (total_bruto, identificados))

    excluidos = int((scr["decisao"] == "excluir").sum())
    ok = len(scr) == excluidos + len(incl)
    print("  %s triagem: %d no registo = %d excluídos + %d incluídos"
          % ("[v]" if ok else "[X]", len(scr), excluidos, len(incl)))
    if not ok:
        problemas.append("a triagem não fecha: %d != %d + %d"
                         % (len(scr), excluidos, len(incl)))

    for valor, rotulo in ((len(scr), "registos após desduplicação"),
                          (excluidos, "excluídos"), (len(incl), "incluídos")):
        na_tese = re.search(r"\b%d\b" % valor, tex) is not None
        print("  %s %-28s %d %s" % ("[v]" if na_tese else "[X]", rotulo, valor,
                                    "" if na_tese else "— não aparece no main.tex"))
        if not na_tese:
            problemas.append("o número %d (%s) não aparece na tese" % (valor, rotulo))
    return problemas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listar", action="store_true",
                    help="mostra a classificação estudo a estudo")
    args = ap.parse_args()

    scr = pd.read_csv(SCREENING)
    incl = scr[scr["decisao"] == "incluir"].copy()
    res = _resumos()
    incl["resumo"] = incl["titulo"].map(lambda t: res.get(_norm(t), ""))

    campo = (incl["titulo"].fillna("") + " " + incl["resumo"].fillna("")).str.lower()
    incl["marl"] = campo.str.contains(MARL, regex=True)
    incl["bio"] = campo.str.contains(BIO, regex=True)
    incl["escala"] = campo.str.contains(ESCALA, regex=True)

    com_resumo = int((incl["resumo"].str.len() > 60).sum())
    tese = _da_tese()

    print("=" * 74)
    print("CORPO DA REVISÃO — a tese afirma, os resumos corroboram?")
    print("=" * 74)
    print(f"  {len(incl)} estudos incluídos; {com_resumo} com resumo nos exports")
    if com_resumo < len(incl):
        print(f"  ⚠️ {len(incl) - com_resumo} sem resumo: a contagem subestima")
    print()

    medido = {"marl": int((incl["marl"] & ~incl["bio"]).sum()),
              "bio": int((incl["bio"] & ~incl["marl"]).sum()),
              "escala": int(incl["escala"].sum())}
    rotulos = {"marl": "assentam em MARL", "bio": "otimização bio-inspirada",
               "escala": "abordam escalabilidade"}
    falhas = []
    for k, rot in rotulos.items():
        if k not in tese:
            print(f"  [?] {rot:26s} medido {medido[k]:3d}   (não li o número na tese)")
            continue
        dif = abs(medido[k] - tese[k])
        ok = dif <= TOLERANCIA
        print(f"  {'[v]' if ok else '[X]'} {rot:26s} medido {medido[k]:3d}   "
              f"tese {tese[k]:3d}   (dif {dif})")
        if not ok:
            falhas.append(f"{rot}: medido {medido[k]}, tese {tese[k]}")

    print(f"\n  ambos os paradigmas: {int((incl['marl'] & incl['bio']).sum())}   "
          f"nenhum: {int((~incl['marl'] & ~incl['bio']).sum())}")
    print("  (a tese soma 44 de 58 nos dois paradigmas ⇒ 14 sem paradigma dominante)")

    falhas += _cadeia_prisma(scr, incl)

    if args.listar:
        print("\n" + "=" * 74)
        for _, r in incl.sort_values("ano").iterrows():
            tags = "".join(["M" if r["marl"] else "-", "B" if r["bio"] else "-",
                            "E" if r["escala"] else "-"])
            print(f"  {tags}  {r['ano']}  {str(r['titulo'])[:78]}")
        print("  (M=MARL  B=bio-inspirada  E=escalabilidade, por título+resumo)")

    falhas += _conferir_registo(incl)

    if falhas:
        print()
        for f in falhas:
            print(f"  DIVERGE  {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
