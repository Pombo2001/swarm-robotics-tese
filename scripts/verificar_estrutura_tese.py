# -*- coding: utf-8 -*-
"""A tese está bem montada? (acrónimos, flutuantes órfãos, páginas órfãs)

Porque existe
-------------
Os outros dezassete verificadores respondem à pergunta «os números estão
certos?». Este responde a duas que ninguém fazia, e cujas respostas erradas se
veem a olho num PDF impresso:

1. **A Lista de Acrónimos serve para alguma coisa?** Um acrónimo declarado e
   nunca usado é ruído; uma sigla usada trinta vezes e nunca declarada é o
   leitor a procurar na lista e a não encontrar. Foi este segundo caso o que
   se mediu a 20 de agosto: o `QI` — a espinha da dissertação, QI1 a QI7 —
   não estava na lista, e o `AI` e o `ML`, que estavam, não aparecem uma
   única vez no corpo.

2. **Alguma figura ou tabela ficou órfã?** Um flutuante que nunca é citado
   aparece no meio do texto sem que nada o anuncie, e a Lista de Figuras
   promete-o na mesma. O caso que interessa é o da figura acrescentada à
   pressa; o que NÃO é caso são as citações por intervalo
   (`Figuras~\\ref{a}--\\ref{d}`), que esta verificação resolve — sem isso
   acusaria três figuras certas e ninguém voltaria a olhar para ela.

3. **Alguma página ficou com uma linha e o resto em branco?** As folhas em
   branco do `twoside` dizem que o são; a que interessa é a outra — o Índice
   transbordava uma ÚNICA linha («Apêndice D. Recursos Adicionais 115») para
   uma terceira página, e essa linha tinha a folha toda por baixo.

As duas primeiras leem o `.tex` e o `.aux` (que traz os números com que o LaTeX
numerou cada flutuante); a terceira lê o PDF impresso, que é a única forma de
ver o que sai na folha.

Uso:
    python scripts/verificar_estrutura_tese.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                            # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_TEX = os.path.join(RAIZ, "Tese", "main.tex")
SECCAO = os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex")
AUX = os.path.join(RAIZ, "Tese", "main.aux")

# Siglas que não são acrónimos da tese: formatos de ficheiro, instituições,
# unidades e o ruído dos comandos do preâmbulo (`pdftitle`, `ABS`, `KEY`).
NAO_SAO_ACRONIMOS = {
    "PDF", "CSV", "JSON", "YAML", "GPU", "CPU", "RAM", "API", "ISCTE", "FCT",
    "UID", "DOI", "URL", "IEEE", "ACM", "HTML", "SSH", "VPN", "TITLE", "ABS",
    "KEY", "RS", "III", "II", "IV", "AND", "OR", "NOT", "PT", "EN", "BR",
    "LATEX", "TEX", "PNG", "OK",
}
MINIMO_PARA_EXIGIR_DECLARACAO = 3

# Páginas curtas por desenho, não por acidente. A dedicatória é uma linha no
# meio de uma folha — é suposto sê-lo. Cada entrada é um padrão declarado, e
# uma página curta que não case com nenhum é acusada.
PAGINAS_CURTAS_ACEITES = (
    r"Aos meus pais",              # dedicatória
)


def _sem_comentarios(t):
    return re.sub(r"(?<!\\)%[^\n]*", "", t)


def _tex():
    t = _sem_comentarios(open(MAIN_TEX, encoding="utf-8").read())
    if os.path.exists(SECCAO):
        t += "\n" + _sem_comentarios(open(SECCAO, encoding="utf-8").read())
    return t


def acronimos(tex):
    """Declarados sem uso, e usados sem declaração."""
    print("=" * 74)
    print("ACRÓNIMOS: a lista descreve o que a tese usa?")
    print("=" * 74)
    problemas = []

    i, j = tex.find(r"\begin{acronym}"), tex.find(r"\end{acronym}")
    if i < 0 or j < 0:
        print("   [X] não encontrei o bloco `acronym`")
        return ["lista de acrónimos: bloco não encontrado"]
    bloco, corpo = tex[i:j], tex[j:]
    decl = re.findall(r"\\acro\{([^}]+)\}(?:\[([^\]]*)\])?\{([^}]+)\}", bloco)
    print("   [i] %d acrónimos declarados" % len(decl))
    if not decl:
        return ["lista de acrónimos vazia — já aconteceu (18 jul)"]

    usados_cmd = set(re.findall(r"\\ac[a-z]*\{([^}]+)\}", corpo))
    nunca = []
    for chave, curto, _longo in decl:
        sigla = curto or chave
        n = len(re.findall(r"(?<![A-Za-z])" + re.escape(sigla) + r"(?![A-Za-z])",
                           corpo))
        if chave in usados_cmd:
            n += 1
        if n == 0:
            nunca.append(sigla)
    if nunca:
        problemas.append("declarados e nunca usados no corpo: %s"
                         % ", ".join(sorted(nunca)))
    else:
        print("   [v] todos os declarados aparecem no corpo")

    declarados = {c or k for k, c, _ in decl} | {k for k, _, _ in decl}
    contagem = {}
    for m in re.finditer(r"(?<![A-Za-z\\])([A-Z]{2,6})(?![A-Za-z])", corpo):
        contagem[m.group(1)] = contagem.get(m.group(1), 0) + 1
    faltam = {s: n for s, n in contagem.items()
              if s not in declarados and s not in NAO_SAO_ACRONIMOS
              and n >= MINIMO_PARA_EXIGIR_DECLARACAO}
    if faltam:
        problemas.append("siglas usadas %d+ vezes e não declaradas: %s"
                         % (MINIMO_PARA_EXIGIR_DECLARACAO,
                            ", ".join("%s (%d)" % (s, n)
                                      for s, n in sorted(faltam.items(),
                                                         key=lambda kv: -kv[1]))))
    else:
        print("   [v] nenhuma sigla frequente fica de fora da lista")
    return problemas


def _numeros_do_aux():
    """{rótulo: número impresso} para figuras e tabelas."""
    if not os.path.exists(AUX):
        return {}
    saida = {}
    for m in re.finditer(r"\\newlabel\{((?:fig|tab):[^}]+)\}\{\{([^}]*)\}\{",
                         open(AUX, encoding="utf-8").read()):
        if not m.group(1).endswith("@cref"):
            saida[m.group(1)] = m.group(2)
    return saida


def _chave_ordenacao(num):
    try:
        return tuple(int(p) for p in re.findall(r"\d+", num))
    except ValueError:                                       # pragma: no cover
        return ()


def flutuantes(tex):
    """Toda a figura e toda a tabela com rótulo são citadas no texto?"""
    print()
    print("=" * 74)
    print("FLUTUANTES: alguma figura ou tabela nunca é citada?")
    print("=" * 74)
    problemas = []

    numeros = _numeros_do_aux()
    rotulos = [r for r in numeros if r.startswith(("fig:", "tab:"))]
    if not rotulos:
        print("   [!] sem main.aux — compilar a tese primeiro; a saltar.")
        return []

    citados = set(re.findall(r"\\ref\{([^}]+)\}", tex))

    # Citações por INTERVALO: «Figuras~\ref{a}--\ref{d}» cita também tudo o que
    # estiver numerado pelo meio. Sem isto, as quatro figuras de fiabilidade e
    # as três da visão global apareciam como órfãs — e estão citadas.
    intervalos = 0
    for m in re.finditer(r"\\ref\{([^}]+)\}\s*-{2,3}\s*\\ref\{([^}]+)\}", tex):
        a, b = numeros.get(m.group(1)), numeros.get(m.group(2))
        if not a or not b:
            continue
        intervalos += 1
        lo, hi = sorted((_chave_ordenacao(a), _chave_ordenacao(b)))
        prefixo = m.group(1).split(":")[0]
        for rot, num in numeros.items():
            if rot.startswith(prefixo + ":") and lo <= _chave_ordenacao(num) <= hi:
                citados.add(rot)
    print("   [i] %d flutuantes com rótulo, %d citações por intervalo"
          % (len(rotulos), intervalos))

    orfaos = sorted(r for r in rotulos if r not in citados)
    if orfaos:
        for r in orfaos:
            problemas.append("nunca citada no texto: %s (%s %s)"
                             % (r, "Figura" if r.startswith("fig:") else "Tabela",
                                numeros[r]))
    else:
        print("   [v] todas as figuras e tabelas são citadas")

    # E o inverso: um `\ref` para um rótulo que não existe imprime «??».
    inexistentes = sorted(r for r in re.findall(r"\\ref\{((?:fig|tab):[^}]+)\}", tex)
                          if r not in numeros)
    if inexistentes:
        problemas.append("citam rótulos que não existem: %s"
                         % ", ".join(sorted(set(inexistentes))))
    return problemas


def paginas_orfas():
    """Páginas do PDF com uma linha e o resto em branco.

    O `\\cleardoublepage` do `twoside` produz páginas em branco de propósito, e
    essas dizem-no: «[ Página intencionalmente deixada em branco. ]». O que
    esta verificação procura é a OUTRA — a que ficou quase vazia por acidente,
    porque uma última linha transbordou. Foi assim que o Índice ficou com
    «Apêndice D. Recursos Adicionais 115» sozinho na página xi, com folha
    inteira por baixo, durante quem sabe quantas versões.

    Lê o PDF impresso: é a única forma de ver isto. Se o `pypdf` não estiver
    instalado, a verificação salta-se e diz-se que se saltou.
    """
    print()
    print("=" * 74)
    print("PÁGINAS: alguma ficou com uma linha órfã?")
    print("=" * 74)
    pdf = os.path.join(RAIZ, "Tese", "main.pdf")
    if not os.path.exists(pdf):
        print("   [!] sem main.pdf — compilar a tese primeiro; a saltar.")
        return []
    try:
        import pypdf
    except ImportError:                                      # pragma: no cover
        print("   [!] sem pypdf — a saltar (pip install pypdf).")
        return []

    problemas = []
    leitor = pypdf.PdfReader(pdf)
    orfas = []
    for i, pagina in enumerate(leitor.pages, 1):
        try:
            texto = " ".join(pagina.extract_text().split())
        except Exception:                                    # noqa: BLE001
            continue
        if "intencionalmente deixada em branco" in texto:
            continue
        sem_numero = re.sub(r"\b[\divxlc]+\b\s*$", "", texto,
                            flags=re.IGNORECASE).strip()
        if not sem_numero:
            continue
        # Uma página com imagem é uma página de figura, não uma órfã.
        try:
            xobj = pagina.get("/Resources", {}).get("/XObject")
            if xobj and len(xobj.get_object()):
                continue
        except Exception:                                    # noqa: BLE001
            pass
        if len(sem_numero) < 60 and not any(
                re.search(pad, sem_numero) for pad in PAGINAS_CURTAS_ACEITES):
            orfas.append((i, sem_numero[:70]))
    print("   [i] %d páginas no PDF" % len(leitor.pages))
    if orfas:
        for i, amostra in orfas:
            problemas.append("página física %d tem uma linha só: «%s»"
                             % (i, amostra))
    else:
        print("   [v] nenhuma página com uma linha órfã")
    return problemas


def main():
    tex = _tex()
    problemas = acronimos(tex) + flutuantes(tex) + paginas_orfas()
    print()
    print("=" * 74)
    if problemas:
        print("%d problema(s):" % len(problemas))
        for p in problemas:
            print("   [X] " + p)
        print("=" * 74)
        return 1
    print("Estrutura da tese: acrónimos e flutuantes coerentes ✓")
    print("NOTA: as citações por intervalo contam — «Figuras 6.12--6.15» cita")
    print("      as quatro, e é assim que a tese as cita.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
