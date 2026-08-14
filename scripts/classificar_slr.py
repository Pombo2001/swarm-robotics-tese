# -*- coding: utf-8 -*-
"""Escreve a classificação dos 58 incluídos no `screening.csv`, com proveniência.

O problema
----------
A tese caracteriza os 58 estudos incluídos por paradigma («21 assentam em MARL
e 23 em otimização bio-inspirada») e por tema («30 dos 58 abordam a
escalabilidade»), e afirma, no mesmo capítulo, que o processo de revisão é
auditável a partir do registo. Não é: os 58 incluídos têm `motivo` e `notas`
VAZIOS — o `motivo` serve para justificar exclusões —, e o apêndice gerado só
traz autores, ano, título e publicação. Quem quisesse conferir aqueles números
não tinha por onde: a classificação vivia só na leitura do autor.

O que este script faz, e o que NÃO faz
--------------------------------------
Preenche quatro colunas novas para as linhas incluídas. **Não inventa a leitura
do autor**: classifica pelos resumos dos exports, com as mesmas expressões
regulares do `verificar_slr_corpo.py` (importadas de lá, para não haver duas
versões da regra), e diz na própria linha que foi assim que o fez:

    paradigma                 marl | bio | ambos | nenhum
    escalabilidade            sim | nao
    classificacao_fonte       regex_v1  (ou `manual`, se alguém a corrigir)
    classificacao_evidencia   os termos que dispararam, para se poder conferir

A diferença face ao que existia não é ter mais certeza — é ter a classificação
**escrita, reproduzível e corrigível**. Uma linha lida à mão passa a
`classificacao_fonte = manual` e este script deixa de lhe tocar; é assim que a
leitura do autor entra no registo, uma linha de cada vez, sem que ninguém
confunda uma coisa com a outra. Foi a fabricação do PRISMA (13 jul) que ensinou
a este projeto que a diferença entre «medido» e «afirmado» tem de estar no
ficheiro, não na memória de quem o escreveu.

Uso:
    python scripts/classificar_slr.py              # só mostra o que faria
    python scripts/classificar_slr.py --escrever   # escreve no screening.csv
"""
import argparse
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from verificar_slr_corpo import (  # noqa: E402
    BIO, ESCALA, MARL, RAIZ, SCREENING, _norm, _resumos)

COLUNAS = ["paradigma", "escalabilidade", "classificacao_fonte",
           "classificacao_evidencia"]
FONTE_AUTO = "regex_v1"


def _termos(texto, padrao):
    """Os termos que efetivamente dispararam — é isto que torna a linha auditável.

    Guardar só `marl=True` obrigaria quem auditasse a reconstruir a regra a
    partir do código para perceber porquê. Com os termos à frente, confere-se
    lendo o resumo.
    """
    return sorted({m.group(0).strip().lower()
                   for m in re.finditer(padrao, texto)})


def classificar():
    scr = pd.read_csv(SCREENING)
    for c in COLUNAS:
        if c not in scr.columns:
            scr[c] = ""
        scr[c] = scr[c].fillna("")

    res = _resumos()
    incluidos = scr["decisao"].astype(str).str.strip() == "incluir"
    novas, mantidas, sem_resumo = 0, 0, 0

    for i in scr.index[incluidos]:
        # Uma linha classificada à mão é a fonte primária: não se toca.
        if str(scr.at[i, "classificacao_fonte"]).strip() == "manual":
            mantidas += 1
            continue
        titulo = str(scr.at[i, "titulo"])
        resumo = res.get(_norm(titulo), "")
        if len(resumo.strip()) <= 60:
            sem_resumo += 1
        campo = (titulo + " " + resumo).lower()
        t_marl, t_bio = _termos(campo, MARL), _termos(campo, BIO)
        t_esc = _termos(campo, ESCALA)
        par = ("ambos" if t_marl and t_bio else
               "marl" if t_marl else "bio" if t_bio else "nenhum")
        provas = []
        if t_marl:
            provas.append("marl: " + ", ".join(t_marl[:4]))
        if t_bio:
            provas.append("bio: " + ", ".join(t_bio[:4]))
        if t_esc:
            provas.append("escala: " + ", ".join(t_esc[:3]))
        if not resumo.strip():
            provas.append("(sem resumo no export — só pelo título)")
        scr.at[i, "paradigma"] = par
        scr.at[i, "escalabilidade"] = "sim" if t_esc else "nao"
        scr.at[i, "classificacao_fonte"] = FONTE_AUTO
        scr.at[i, "classificacao_evidencia"] = " | ".join(provas)
        novas += 1

    return scr, incluidos, novas, mantidas, sem_resumo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args()

    scr, incluidos, novas, mantidas, sem_resumo = classificar()
    inc = scr[incluidos]

    print("=" * 74)
    print("CLASSIFICAÇÃO DOS INCLUÍDOS  →  docs/slr/screening.csv")
    print("=" * 74)
    print("  %d incluídos: %d classificados por regra, %d já eram manuais"
          % (len(inc), novas, mantidas))
    if sem_resumo:
        print("  ⚠️ %d sem resumo nos exports — classificados só pelo título, "
              "e a coluna da evidência di-lo" % sem_resumo)
    print()
    print("  paradigma:")
    for k, v in inc["paradigma"].value_counts().items():
        print("    %-8s %d" % (k, v))
    print("  escalabilidade: %d sim, %d não"
          % (int((inc["escalabilidade"] == "sim").sum()),
             int((inc["escalabilidade"] == "nao").sum())))
    print()
    print("  ⚠️ Isto é a classificação DERIVADA dos resumos, e a coluna")
    print("     `classificacao_fonte` di-lo em cada linha. Uma linha lida à")
    print("     mão põe-se a `manual` e este script deixa de lhe tocar.")

    if a.escrever:
        scr.to_csv(SCREENING, index=False, encoding="utf-8")
        print("\n  ESCRITO: %s" % os.path.relpath(SCREENING, RAIZ))
        print("  A seguir: python scripts/verificar_slr_corpo.py")
    else:
        print("\n  (nada foi escrito — repetir com --escrever)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
