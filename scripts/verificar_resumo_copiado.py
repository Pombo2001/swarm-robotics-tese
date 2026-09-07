# -*- coding: utf-8 -*-
r"""O Resumo copiado para a cábula e para os slides é, palavra por palavra, o da tese.

Porque existe
O Resumo da dissertação está em três sítios: no `Tese/main.tex`, que é a fonte,
e em duas cópias feitas para estudar — a secção «Em trinta segundos» da cábula
(`Defesa/cabula.modelo.html`, de onde sai o `cabula.html`) e as notas do orador
da capa dos slides (`Defesa/gerar_slides.py`, de onde sai o `.pptx`). Uma cópia
sem régua diverge: a 7 de setembro de 2026 a cábula e os slides ainda citavam
páginas do PDF de 141 páginas de 3 de setembro, e o Resumo tinha entretanto
encolhido de 408 para 245 palavras. Nada acusou nem uma coisa nem outra.

O modo de falha é o pior possível para uma defesa: decorar uma frase que a tese
já não diz, e dizê-la ao júri que tem a versão entregue à frente.

O que confere
1. As duas cópias trazem o MESMO texto que o `\chapter*{Resumo}` do `main.tex`,
   palavra a palavra, depois de normalizar o que é notação e não conteúdo — o
   `\emph{}` do LaTeX, as etiquetas do HTML, o `$...$` da matemática, o `{,}` da
   vírgula decimal e o `\times` que na cópia se escreve `x` ou `×`.
2. O Resumo e o Abstract cabem nas 250 palavras de §1.v e §1.vi das normas
   gráficas do Iscte. Conta-se como um processador de texto contaria, sobre o
   texto COMPOSTO e não sobre a fonte: o `$103 \times 62$\,m` são três palavras
   («103», «x», «62») mais o «m», e não uma só.

O que NÃO faz: olhar para dados. Os valores do Resumo já têm régua própria — o
`verificar_numeros_tese.py` confere-os contra os CSV e exige que o Abstract
traga a mesma sequência. Aqui a pergunta é outra: as cópias são a fonte?

Uso:
    .venv/Scripts/python.exe scripts/verificar_resumo_copiado.py
    .venv/Scripts/python.exe scripts/verificar_resumo_copiado.py --mostrar
"""
from __future__ import annotations

import difflib
import html
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:                                            # pragma: no cover
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESE = os.path.join(RAIZ, "Tese", "main.tex")
CABULA = os.path.join(RAIZ, "Defesa", "cabula.html")
SLIDES = os.path.join(RAIZ, "Defesa", "slides_defesa.pptx")

LIMITE_NORMA = 250        # §1.v e §1.vi das normas gráficas do Iscte
ABRE_COPIA = "Para comparar a Aprendizagem"   # a primeira frase do Resumo

erros: list[str] = []


def X(msg: str) -> None:
    erros.append(msg)


# --------------------------------------------------------------------------
# Normalização: tirar a notação, deixar as palavras
# --------------------------------------------------------------------------
def _sem_notacao(t: str) -> str:
    """LaTeX e HTML reduzidos ao texto que uma pessoa lê em voz alta."""
    t = html.unescape(t)
    # \emph{x}, \textit{x}, \textbf{x} -> x  (só um nível; o Resumo não aninha)
    t = re.sub(r"\\(?:emph|textit|textbf)\{([^{}]*)\}", r"\1", t)
    t = t.replace(r"\times", "x").replace(r"\,", " ").replace(r"\%", "%")
    t = t.replace("{,}", ",").replace("$", " ").replace("---", " ")
    t = re.sub(r"<[^>]+>", " ", t)              # etiquetas HTML
    return t.replace("\u00a0", " ").replace("×", "x").replace("—", " ")


def palavras(t: str) -> list[str]:
    """As palavras, para comparar duas escritas do mesmo texto."""
    return re.findall(r"[\wÀ-ÿ]+(?:[,./][\wÀ-ÿ]+)*%?", _sem_notacao(t).lower())


def palavras_compostas(t: str) -> int:
    """Quantas palavras conta um processador de texto no texto COMPOSTO.

    Difere da `palavras` num ponto que decide a conformidade: o `\\times` fica
    como uma palavra sua («103 x 62» são três) e o `\\,m` é a quarta. Contar
    sobre a fonte, onde isso é uma só sequência entre cifrões, dava 250 quando
    o documento composto mostra 253.
    """
    return len(re.findall(r"[\wÀ-ÿ%/,.-]*[\wÀ-ÿ%][\wÀ-ÿ%/,.-]*", _sem_notacao(t)))


# --------------------------------------------------------------------------
# As três origens
# --------------------------------------------------------------------------
def _entre(texto: str, inicio: str, fim: str, onde: str) -> str | None:
    i = texto.find(inicio)
    if i < 0:
        X("%s: não encontrei %r" % (onde, inicio))
        return None
    j = texto.find(fim, i + len(inicio))
    if j < 0:
        X("%s: não encontrei %r depois de %r" % (onde, fim, inicio))
        return None
    return texto[i + len(inicio):j]


def da_tese(marca: str) -> str | None:
    with io.open(TESE, encoding="utf-8") as fh:
        tex = fh.read()
    return _entre(tex, marca, r"\vspace{3ex}", "main.tex")


def da_cabula() -> str | None:
    if not os.path.exists(CABULA):
        X("cabula.html não existe — corre o Defesa/gerar_cabula.py")
        return None
    with io.open(CABULA, encoding="utf-8") as fh:
        pag = fh.read()
    return _entre(pag, ABRE_COPIA, "Palavras-chave:", "cabula.html")


def dos_slides() -> str | None:
    if not os.path.exists(SLIDES):
        X("slides_defesa.pptx não existe — corre o Defesa/gerar_slides.py")
        return None
    try:
        from pptx import Presentation
    except ImportError:                                      # pragma: no cover
        print("   [i] python-pptx não instalado — os slides ficam por conferir")
        return None
    capa = Presentation(SLIDES).slides[0]
    if not capa.has_notes_slide:
        X("slides: a capa não tem notas do orador")
        return None
    return _entre(capa.notes_slide.notes_text_frame.text,
                  ABRE_COPIA, "É daqui que saem", "slides (notas da capa)")


# --------------------------------------------------------------------------
def comparar(rot: str, referencia: list[str], copia: list[str] | None) -> None:
    if copia is None:
        return
    sm = difflib.SequenceMatcher(None, referencia, copia, autojunk=False)
    difs = [o for o in sm.get_opcodes() if o[0] != "equal"]
    if not difs:
        print("   [v] %-22s %d palavras, iguais às da tese" % (rot, len(copia)))
        return
    X("%s: %d diferença(s) para o Resumo do main.tex" % (rot, len(difs)))
    for _tag, a1, a2, b1, b2 in difs[:8]:
        erros.append("      tese diz %r  e a cópia %r"
                     % (" ".join(referencia[a1:a2]), " ".join(copia[b1:b2])))


def main() -> int:
    print("=" * 74)
    print("VERIFICAÇÃO: o Resumo copiado para a cábula e para os slides")
    print("=" * 74)

    resumo = da_tese(r"\chapter*{Resumo}")
    abstract = da_tese(r"\chapter*{Abstract}")

    # 1. as duas cópias são a fonte?
    if resumo is not None:
        ref = palavras(ABRE_COPIA + resumo.split(ABRE_COPIA, 1)[-1]
                       if ABRE_COPIA in resumo else resumo)
        comparar("cabula.html", ref, None if (c := da_cabula()) is None
                 else palavras(ABRE_COPIA + c))
        comparar("slides (capa)", ref, None if (s := dos_slides()) is None
                 else palavras(ABRE_COPIA + s))

    # 2. cabem nas 250 palavras da norma?
    for rot, bloco in (("Resumo", resumo), ("Abstract", abstract)):
        if bloco is None:
            continue
        n = palavras_compostas(bloco)
        if n > LIMITE_NORMA:
            X("%s com %d palavras — a norma do Iscte (§1.v/§1.vi) fixa %d"
              % (rot, n, LIMITE_NORMA))
        else:
            print("   [v] %-22s %d palavras (limite %d)" % (rot, n, LIMITE_NORMA))

    if "--mostrar" in sys.argv and resumo:
        print("\n--- o Resumo, como está no main.tex ---")
        print(" ".join(_sem_notacao(resumo).split()))

    print()
    if erros:
        print("DIVERGÊNCIAS (%d):" % len([e for e in erros
                                          if not e.startswith("      ")]))
        for e in erros:
            print(("   " + e) if not e.startswith("      ") else e)
        print("\nAs cópias fazem-se a correr o Defesa/gerar_cabula.py e o")
        print("Defesa/gerar_slides.py depois de editar o modelo/o gerador —")
        print("o texto vive no cabula.modelo.html e no gerar_slides.py, não")
        print("nos ficheiros gerados.")
        return 1
    print("O Resumo da tese, da cábula e dos slides é o mesmo texto ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
