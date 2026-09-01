# -*- coding: utf-8 -*-
"""Cada «Figura~\\ref{...}» aponta mesmo para uma figura?

Porque existe
O LaTeX não se queixa quando se escreve `Tabela~\\ref{fig:...}`: a referência
resolve, imprime um número, e o PDF fica com uma frase que manda o leitor à
tabela 6.2 quando queria a figura 6.2. É dos poucos erros que sobrevivem a
«0 referências indefinidas» — e a única forma de o apanhar é comparar a PALAVRA
que antecede a remissão com o PREFIXO do rótulo.

Verifica também o inverso: rótulos definidos com um prefixo que não corresponde
ao ambiente onde vivem (um `\\label{fig:...}` dentro de um `table`).

Uso:
    python scripts/verificar_remissoes.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                            # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHEIROS = [os.path.join(RAIZ, "Tese", "main.tex"),
             os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex"),
             os.path.join(RAIZ, "Tese", "apendice_slr.tex"),
             os.path.join(RAIZ, "Artigo", "artigo.tex")]

# palavra que antecede -> prefixos de rótulo que ela admite
ESPERADO = {
    "figura": ("fig",),
    "figuras": ("fig",),
    "tabela": ("tab",),
    "tabelas": ("tab",),
    "secção": ("sec", "apx", "ch"),
    "secções": ("sec", "apx", "ch"),
    "capítulo": ("ch",),
    "capítulos": ("ch",),
    "apêndice": ("apx", "ch"),
    "equação": ("eq",),
    "equações": ("eq",),
    # o artigo escreve em português mas com os mesmos prefixos
    "fig": ("fig",),
    "table": ("tab",),
    "section": ("sec", "apx", "ch"),
}


def sem_comentarios(t):
    return re.sub(r"(?<!\\)%[^\n]*", "", t)


def main():
    print("=" * 74)
    print("REMISSÕES: a palavra que antecede vs o prefixo do rótulo")
    print("=" * 74)
    problemas, conferidas = [], 0

    for f in FICHEIROS:
        if not os.path.exists(f):
            continue
        tex = sem_comentarios(open(f, encoding="utf-8").read())
        nome = os.path.relpath(f, RAIZ)

        # «Figura~\ref{fig:x}», «Tabelas~\ref{a}--\ref{b}», «(Secção~\ref{s})»
        for m in re.finditer(r"(\w+)[~ ]*\\ref\{([^}]+)\}", tex):
            palavra, rotulo = m.group(1).lower(), m.group(2)
            admitidos = ESPERADO.get(palavra)
            if not admitidos:
                continue                      # «ver \ref{}», «e~\ref{}», etc.
            conferidas += 1
            prefixo = rotulo.split(":")[0] if ":" in rotulo else ""
            if prefixo not in admitidos:
                linha = tex.count("\n", 0, m.start()) + 1
                problemas.append(
                    "%s:%d  «%s~\\ref{%s}» — um rótulo `%s:` não é %s"
                    % (nome, linha, m.group(1), rotulo, prefixo, palavra))

        # rótulos com prefixo trocado face ao ambiente onde vivem
        for amb, prefixos in (("figure", ("fig",)), ("table", ("tab",))):
            for m in re.finditer(r"\\begin\{%s\*?\}(.{0,2500}?)\\end\{%s\*?\}"
                                 % (amb, amb), tex, re.DOTALL):
                for lab in re.findall(r"\\label\{([^}]+)\}", m.group(1)):
                    conferidas += 1
                    pre = lab.split(":")[0] if ":" in lab else ""
                    if pre not in prefixos:
                        linha = tex.count("\n", 0, m.start()) + 1
                        problemas.append(
                            "%s:%d  \\label{%s} dentro de um `%s` — o prefixo "
                            "devia ser `%s:`" % (nome, linha, lab, amb,
                                                 prefixos[0]))

    # figuras e tabelas que o texto nunca chama
    #
    # Uma tabela de resultados que nenhuma frase refere é uma tabela a que o
    # leitor nunca é levado — e aconteceu com a `tab:f2_mapa_grande`, que é a
    # do treino nativo no mapa composto (o 4/21 contra 0/21).
    #
    # Os INTERVALOS contam: «Figuras~\ref{a}--\ref{b}» refere também tudo o
    # que está entre as duas. Sem isto, a primeira versão desta verificação
    # acusou quatro figuras que o texto chama por intervalo.
    tese = "\n".join(sem_comentarios(open(f, encoding="utf-8").read())
                     for f in FICHEIROS if os.path.exists(f)
                     and "Artigo" not in f)
    ordem = [m.group(1) for m in re.finditer(r"\\label\{([^}]+)\}", tese)]
    posicao = {lab: i for i, lab in enumerate(ordem)}
    referidos = set(re.findall(r"\\(?:auto)?ref\{([^}]+)\}", tese))
    for m in re.finditer(r"\\ref\{([^}]+)\}\s*(?:--|---|\\textendash)\s*"
                         r"\\ref\{([^}]+)\}", tese):
        a, b = m.group(1), m.group(2)
        if a in posicao and b in posicao:
            i, j = sorted((posicao[a], posicao[b]))
            tipo = a.split(":")[0]
            referidos.update(l for l in ordem[i:j + 1]
                             if l.split(":")[0] == tipo)
    orfaos = sorted(l for l in set(ordem) - referidos
                    if l.split(":")[0] in ("fig", "tab"))
    conferidas += len([l for l in set(ordem)
                       if l.split(":")[0] in ("fig", "tab")])
    for o in orfaos:
        problemas.append("%s nunca é referido no texto — o leitor não é levado "
                         "até lá" % o)

    if problemas:
        print("%d problema(s), em %d remissões/rótulos conferidos:"
              % (len(problemas), conferidas))
        for p in problemas:
            print("   " + p)
        print("=" * 74)
        return 1
    print("As %d remissões apontam para o tipo certo ✓" % conferidas)
    print("NOTA: o LaTeX não acusa isto — «Tabela~\\ref{fig:x}» resolve e")
    print("      imprime um número, e a frase manda o leitor ao sítio errado.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
