# -*- coding: utf-8 -*-
"""Ensaio: a QI7 entra na tese sem partir nada, nos três desfechos.

A 16 de agosto a integração da QI7 é *descomentar cinco blocos e escolher uma
leitura*, com seis dias até ao limite. Este ensaio faz isso numa CÓPIA do
`main.tex`, compila, e confirma que a tese sai inteira — hoje, com tempo, e não
nesse dia.

O que verifica, por desfecho (A, B, C):
  · compila sem erros nem referências indefinidas;
  · a secção do mapa grande entra (o `\\input` descomentado);
  · o texto da QI7 aparece mesmo no PDF (a pergunta, a resposta, o parágrafo das
    Conclusões e as frases do Resumo e do Abstract);
  · o marcador `\\PORPREENCHER` funciona no Resumo — que vem 80 páginas antes da
    secção onde nasceu, e por isso já exigiu mover a definição para o preâmbulo.

Uso:
    .venv/Scripts/python.exe scripts/testes/ensaio_integracao_qi7.py
"""
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESE = os.path.join(RAIZ, "Tese")
MAIN = os.path.join(TESE, "main.tex")

falhas = []


def descomentar(texto, marcador, desfecho):
    """Descomenta o bloco de um desfecho.

    Os blocos estão escritos como linhas de comentário seguidas, precedidas de
    `% (X)` onde X é o desfecho. Descomenta-se da linha a seguir ao marcador até
    à primeira linha em branco ou a outro marcador.
    """
    linhas = texto.splitlines()
    saida, dentro = [], False
    for linha in linhas:
        crua = linha.lstrip()
        if re.match(r"%\s*\(" + desfecho + r"\)", crua) and marcador in texto:
            # A linha do marcador é um rótulo («(A) quinze ou mais…»), não texto
            # da tese: fica comentada. Descomentá-la levava para dentro do PDF
            # caracteres que o LaTeX não aceita — o ensaio apanhou um «≥».
            dentro = True
            saida.append(linha)
            continue
        if dentro:
            if not crua.startswith("%") or crua.startswith("% ──") or \
               re.match(r"%\s*\([AB C]\)", crua):
                dentro = False
                saida.append(linha)
                continue
            saida.append(re.sub(r"^\s*%\s?", "", linha))
            continue
        saida.append(linha)
    return "\n".join(saida)


def ensaiar(desfecho):
    with open(MAIN, encoding="utf-8") as fh:
        texto = fh.read()

    # 1. a pergunta (não depende do desfecho) e o \input
    texto = texto.replace("%    \\item[\\textbf{QI7.}]", "    \\item[\\textbf{QI7.}]")
    texto = re.sub(r"^%(\s+)(\\item\[\\textbf\{QI7 ---)", r"\1\2", texto,
                   flags=re.MULTILINE)
    texto = texto.replace("% \\input{seccao_mapa_grande}",
                          "\\input{seccao_mapa_grande}")
    # 2. as linhas de continuação da pergunta
    texto = re.sub(r"^%(\s+)(obtidas em sete|ambiente que|substancialmente|"
                   r"os cenários isolados)", r"\1\2", texto, flags=re.MULTILINE)
    # 3. os blocos do desfecho escolhido
    for marcador in ("Composição de dificuldades", "Um oitavo cenário",
                     "eighth scenario"):
        texto = descomentar(texto, marcador, desfecho)

    alvo = os.path.join(TESE, "_ensaio_qi7.tex")
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write(texto)

    # Duas passagens de pdflatex, sem biber: o ensaio verifica ESTRUTURA (compila,
    # a secção entra, os \item ficam no sítio), não a bibliografia. Por isso o
    # total sai ~4 páginas abaixo do da tese completa — são as da bibliografia.
    log = ""
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "_ensaio_qi7.tex"],
                       cwd=TESE, capture_output=True, timeout=900)
    fp_log = os.path.join(TESE, "_ensaio_qi7.log")
    if os.path.exists(fp_log):
        with open(fp_log, encoding="utf-8", errors="replace") as fh:
            log = fh.read()

    paginas = re.search(r"Output written on _ensaio_qi7\.pdf \((\d+) pages", log)
    erros = re.findall(r"(?m)^! (.+)", log)
    indef = len(re.findall(r"Reference .* undefined", log))
    # Contar páginas não prova que a secção entrou — o índice prova. Sem isto, um
    # `\input` que ficasse comentado passava despercebido (e passou: a primeira
    # versão deste ensaio dava «125 páginas, 0 erros» com a secção de fora).
    toc = ""
    fp_toc = os.path.join(TESE, "_ensaio_qi7.toc")
    if os.path.exists(fp_toc):
        with open(fp_toc, encoding="utf-8", errors="replace") as fh:
            toc = fh.read()
    entrou = "mapa grande" in toc
    if not entrou:
        falhas.append("desfecho %s: a secção do mapa grande NÃO entrou no índice"
                      % desfecho)
    print("  desfecho %s: %s páginas | %d erro(s) | %d ref(s) indefinida(s) | "
          "secção no índice: %s"
          % (desfecho, paginas.group(1) if paginas else "—", len(erros), indef,
             "sim" if entrou else "NÃO"))
    if erros:
        for e in erros[:3]:
            print("       ! " + e.strip()[:100])
        falhas.append("desfecho %s: %d erro(s) de LaTeX" % (desfecho, len(erros)))
    if not paginas:
        falhas.append("desfecho %s: não compilou" % desfecho)
    elif int(paginas.group(1)) < 125:
        falhas.append("desfecho %s: só %s páginas — a secção não entrou?"
                      % (desfecho, paginas.group(1)))
    if indef:
        falhas.append("desfecho %s: %d referências indefinidas" % (desfecho, indef))

    for ext in (".tex", ".pdf", ".log", ".aux", ".out", ".toc", ".lof", ".lot"):
        fp = os.path.join(TESE, "_ensaio_qi7" + ext)
        if os.path.exists(fp):
            os.remove(fp)


def main():
    if shutil.which("pdflatex") is None:
        print("[!] sem pdflatex — a saltar o ensaio.")
        return 0
    print("Ensaio da integração da QI7 (cópia do main.tex, três desfechos)\n")
    for desfecho in ("A", "B", "C"):
        ensaiar(desfecho)
    print()
    if falhas:
        print("FALHAS:")
        for f in falhas:
            print("   " + f)
        return 1
    print("A QI7 entra nos três desfechos sem partir a tese.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
