# -*- coding: utf-8 -*-
"""Que afirmações numéricas da tese NÃO têm verificador?

O problema
----------
O `verificar_numeros_tese.py` confere 352 valores e diz «tudo bate ✓». O que
essa linha não diz é *de quantos*: o corpo do `main.tex` tem 2170 tokens
numéricos. A fração por cobrir nunca foi medida, e um número que ninguém
verifica é indistinguível de um número verificado — até alguém o ler na defesa.

Como se mede, sem adivinhar
---------------------------
Não se extraem os padrões do código dos verificadores: seriam dezenas, alguns
construídos em tempo de execução, e uma lista escrita à mão envelheceria no
sítio. Em vez disso **instrumenta-se o `re`**: corre-se cada verificador com
`re.search`/`findall`/`finditer`/`match` embrulhados, guardando o texto de cada
match feito sobre o conteúdo de um `.tex`. Um número que caia dentro de um
desses trechos foi lido por alguém; um que não caia, não foi.

Isto mede o que os verificadores **leem**, que é um majorante do que eles
**verificam** — um padrão pode apanhar uma frase e usar só metade dos números
dela. O relatório declara-o, e é por isso que a coluna certa se chama
«lido por um verificador» e não «verificado».

Uso:
    python scripts/cobertura_verificador.py            # imprime o resumo
    python scripts/cobertura_verificador.py --escrever # + docs/COBERTURA_VERIFICADOR.md
"""
import argparse
import io
import os
import re
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(RAIZ, "Tese", "main.tex")
SAIDA = os.path.join(RAIZ, "docs", "COBERTURA_VERIFICADOR.md")

# Os verificadores que leem o `.tex`. O `verificar_slr_corpo` também o lê, mas só
# para tirar três números do capítulo da revisão; entra na mesma.
VERIFICADORES = ["verificar_numeros_tese", "verificar_contagens_prosa",
                 "verificar_parte1", "verificar_mapa_grande",
                 "verificar_slr_corpo", "verificar_planalto"]


# ── instrumentação do `re` ───────────────────────────────────────────────────

def _instrumentar(marcas):
    """Embrulha o `re` para guardar o texto de cada match feito sobre um `.tex`.

    A heurística de «isto é o tex» é o tamanho e o conteúdo: os verificadores
    leem o ficheiro inteiro para uma string. Uma string com dezenas de milhar de
    caracteres e `\\section` lá dentro é o `.tex` e não um nome de ficheiro.
    """
    orig = {n: getattr(re, n) for n in ("search", "findall", "finditer", "match")}

    # O corpo do `.tex`, para reconhecer também os PEDAÇOS. O limiar antigo era
    # «mais de 20 000 caracteres e tem \section», e por isso não via um
    # verificador que recorta uma secção (14 636 caracteres) e faz as buscas só
    # nela — que é exatamente o que a verificação do Novelty passou a fazer. Uma
    # medição que não vê o instrumento novo dá a ilusão de que nada mudou.
    corpo_tex = open(MAIN, encoding="utf-8").read()

    def e_tex(s):
        if not isinstance(s, str) or len(s) < 2000:
            return False
        return s in corpo_tex or (len(s) > 20000 and "\\section" in s)

    def guardar(m):
        if m and m.group(0):
            marcas.append(m.group(0))

    def search(padrao, texto, *a, **k):
        m = orig["search"](padrao, texto, *a, **k)
        if e_tex(texto):
            guardar(m)
        return m

    def match(padrao, texto, *a, **k):
        m = orig["match"](padrao, texto, *a, **k)
        if e_tex(texto):
            guardar(m)
        return m

    def finditer(padrao, texto, *a, **k):
        it = list(orig["finditer"](padrao, texto, *a, **k))
        if e_tex(texto):
            for m in it:
                guardar(m)
        return iter(it)

    def findall(padrao, texto, *a, **k):
        r = orig["findall"](padrao, texto, *a, **k)
        if e_tex(texto):
            for m in orig["finditer"](padrao, texto, *a, **k):
                guardar(m)
        return r

    re.search, re.match, re.finditer, re.findall = search, match, finditer, findall
    return orig


def _repor(orig):
    for n, f in orig.items():
        setattr(re, n, f)


def _instrumentar_tabelas(mod, marcas):
    """O `ler_tabela()` não passa pelo `re` sobre o `.tex` — e é onde vive a maioria.

    A primeira medição deu 6% de cobertura, o que não batia com os 352 valores
    que o verificador diz conferir. A explicação não era o verificador estar a
    mentir: é que ele lê as tabelas com `find()` e `split('&')`, não com
    expressões regulares, e por isso escapava inteiro à instrumentação do `re`.
    Uma medição que só vê metade dos instrumentos mede o instrumento, não a
    tese. Aqui marca-se a tabela toda, do `\\label` ao `\\end{tabular}`.
    """
    original = getattr(mod, "ler_tabela", None)
    if original is None:
        return

    def embrulhado(caminho, label, *a, **k):
        try:
            tex = open(caminho, encoding="utf-8").read()
            i = tex.find("\\label{%s}" % label)
            if i >= 0:
                fim = tex.find("\\end{tabular}", i)
                marcas.append(tex[i:fim if fim > i else i + 4000])
        except OSError:
            pass
        return original(caminho, label, *a, **k)

    mod.ler_tabela = embrulhado

    # As tabelas indexadas por algoritmo ou por hiperparâmetro não passam pela
    # `ler_tabela` (que só devolve linhas de cenários): passam pelo
    # `corpo_tabela`, que já recebe o `.tex` em memória. Sem este segundo
    # embrulho, as três tabelas de configuração e a tab:res_scale ficavam de
    # fora da medição — 45 valores conferidos que a cobertura não via.
    corpo = getattr(mod, "corpo_tabela", None)
    if corpo is None:
        return

    def corpo_embrulhado(tex, label, *a, **k):
        saida = corpo(tex, label, *a, **k)
        if saida:
            marcas.append(saida)
        return saida

    mod.corpo_tabela = corpo_embrulhado


def correr_verificadores():
    """Corre-os todos, calados, e devolve os trechos que leram do `.tex`."""
    marcas = []
    orig = _instrumentar(marcas)
    falharam = []
    try:
        for nome in VERIFICADORES:
            try:
                mod = __import__(nome)
                _instrumentar_tabelas(mod, marcas)
                alvo = getattr(mod, "main", None)
                if alvo is None:
                    continue
                argv, sys.argv = sys.argv, [nome]
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    try:
                        alvo()
                    except SystemExit:
                        pass
                sys.argv = argv
            except Exception as e:  # noqa: BLE001
                falharam.append("%s: %s" % (nome, e))
    finally:
        _repor(orig)
    return marcas, falharam


# ── classificação do que sobra ───────────────────────────────────────────────

# (iii) não é resultado: não há nada nos dados com que confrontar estes números.
NAO_E_RESULTADO = [
    (r"\\(?:ref|label|cite|eqref|autoref|pageref)\b", "referência interna/citação"),
    (r"\d+(?:\.\d+)?\\(?:textwidth|linewidth|columnwidth|height|baselineskip)",
     "dimensão de figura"),
    (r"\d+(?:\.\d+)?\s*(?:cm|mm|pt|em|ex|in)\b", "medida de composição"),
    (r"(?:19|20)\d{2}", "ano"),
    (r"\\(?:begin|end|item|includegraphics|hspace|vspace|scalebox|resizebox)",
     "comando LaTeX"),
]

# (i) automatizável: o número está ao pé de uma palavra que o liga a um dado.
SINAIS_DE_RESULTADO = [
    (r"recolhas?(?:/ep| por epis)", "recolhas por episódio"),
    (r"\\pm|±", "média ± desvio"),
    (r"\bp\s*(?:=|<|>)|\\delta\s*=|δ\s*=", "estatística (p, δ)"),
    (r"\bruns?\b|execuç", "contagem de execuções"),
    (r"taxa de sucesso|\bsucesso\b", "taxa de sucesso"),
    (r"\bn\s*=\s*\d|\$n = ", "dimensão amostral"),
    (r"epis[óo]dios?\b", "episódios"),
    (r"retenç|robustez", "robustez"),
    (r"\bN\s*=\s*\d|dimensão do enxame", "escalabilidade"),
]


def classificar(contexto):
    for padrao, rot in NAO_E_RESULTADO:
        if re.search(padrao, contexto):
            return "iii", rot
    for padrao, rot in SINAIS_DE_RESULTADO:
        if re.search(padrao, contexto, re.IGNORECASE):
            return "i", rot
    return "ii", "sem sinal automático — precisa de leitura"


def analisar():
    bruto = open(MAIN, encoding="utf-8").read()
    corpo = re.sub(r"(?<!\\)%[^\n]*", "", bruto)

    marcas, falharam = correr_verificadores()

    # Onde é que cada trecho lido cai no corpo? Marca-se por texto, não por
    # posição: os verificadores tiram os comentários primeiro, e os offsets
    # deles não são os deste ficheiro.
    coberto = [False] * len(corpo)
    for trecho in marcas:
        if len(trecho) < 4:
            continue
        ini = 0
        while True:
            i = corpo.find(trecho, ini)
            if i < 0:
                break
            for j in range(i, min(i + len(trecho), len(corpo))):
                coberto[j] = True
            ini = i + 1

    itens = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*(?:\{,\}\d+)*", corpo):
        a, b = m.span()
        dentro = any(coberto[a:b])
        ctx = corpo[max(0, a - 90):min(len(corpo), b + 90)]
        ctx = " ".join(ctx.split())
        cls, rot = classificar(ctx)
        itens.append({"valor": m.group(0), "lido": dentro, "classe": cls,
                      "rotulo": rot, "contexto": ctx, "pos": a})
    return itens, marcas, falharam


def linha_do(corpo, pos):
    return corpo.count("\n", 0, pos) + 1


def _seccoes(corpo):
    """(posição, nome) de cada capítulo/secção, para dizer ONDE está o buraco.

    Um número por verificar no meio do Cap. 2 e um número por verificar no
    Resumo não têm o mesmo peso: o Resumo é a página que toda a gente lê, e é
    onde estão os valores que o júri cita de volta. Sem esta divisão, a lista
    de 495 é uma pilha sem ordem de ataque.
    """
    marcos = []
    for m in re.finditer(r"\\(chapter|section|chapter\*|section\*)\*?\{([^}]{0,80})\}",
                         corpo):
        marcos.append((m.start(), m.group(2)))
    return marcos


def seccao_de(marcos, pos):
    nome = "(antes do primeiro capítulo)"
    for p, n in marcos:
        if p <= pos:
            nome = n
        else:
            break
    return nome


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args()

    itens, marcas, falharam = analisar()
    corpo = re.sub(r"(?<!\\)%[^\n]*", "",
                   open(MAIN, encoding="utf-8").read())

    total = len(itens)
    lidos = sum(1 for i in itens if i["lido"])
    porcls = {}
    for i in itens:
        if not i["lido"]:
            porcls.setdefault(i["classe"], []).append(i)

    print("=" * 74)
    print("COBERTURA DOS VERIFICADORES SOBRE O main.tex")
    print("=" * 74)
    if falharam:
        for f in falharam:
            print("  ⚠️ verificador não correu — %s" % f)
    print("  %d tokens numéricos no corpo (sem comentários)" % total)
    print("  %d lidos por algum verificador (%.0f%%)" % (lidos, 100.0 * lidos / total))
    print("  %d por cobrir:" % (total - lidos))
    print("    (i)   %4d automatizáveis — são resultados com dados por trás"
          % len(porcls.get("i", [])))
    print("    (ii)  %4d precisam de leitura" % len(porcls.get("ii", [])))
    print("    (iii) %4d não são resultados (anos, refs, medidas)"
          % len(porcls.get("iii", [])))
    print()
    print("  ⚠️ «lido» é majorante de «verificado»: um padrão pode apanhar uma")
    print("     frase e usar só metade dos números dela.")

    if not a.escrever:
        print("\n  (--escrever gera docs/COBERTURA_VERIFICADOR.md)")
        return 0

    grupos = {}
    for i in porcls.get("i", []):
        grupos.setdefault(i["rotulo"], []).append(i)

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("# Cobertura dos verificadores sobre o `main.tex`\n\n")
        f.write("> GERADO por `scripts/cobertura_verificador.py` — não editar à "
                "mão.\n\n")
        f.write("O `verificar_numeros_tese.py` diz «tudo bate ✓». Este ficheiro "
                "diz **de quantos**.\n\n")
        f.write("| | tokens numéricos |\n|---|---|\n")
        f.write("| no corpo do `main.tex` (sem comentários) | %d |\n" % total)
        f.write("| lidos por algum verificador | **%d** (%.0f%%) |\n"
                % (lidos, 100.0 * lidos / total))
        f.write("| por cobrir | %d |\n\n" % (total - lidos))
        f.write("«Lido» é um **majorante** de «verificado»: a medição regista o "
                "que os padrões dos verificadores apanham do `.tex`, e um padrão "
                "pode apanhar uma frase inteira e usar só metade dos números "
                "dela. Um token *não lido* é, esse sim, certo: ninguém olhou "
                "para ele.\n\n")
        f.write("Método: instrumenta-se o módulo `re` e corre-se cada "
                "verificador, guardando o texto de cada match feito sobre o "
                "`.tex`. Não há lista de padrões escrita à mão para envelhecer.\n\n")

        f.write("## (i) Automatizáveis — %d\n\n" % len(porcls.get("i", [])))
        f.write("Números com um dado por trás e nenhum verificador a olhar para "
                "eles. É aqui que se acrescenta ao `verificar_numeros_tese.py`.\n\n")

        marcos = _seccoes(corpo)
        por_sec = {}
        for i in porcls.get("i", []):
            por_sec.setdefault(seccao_de(marcos, i["pos"]), []).append(i)
        f.write("### Por onde começar — onde estão os %d\n\n"
                % len(porcls.get("i", [])))
        f.write("A ordem de ataque não é o tamanho do grupo, é a visibilidade: "
                "um valor por verificar no Resumo é lido por toda a gente e "
                "citado de volta na defesa; o mesmo valor no meio do Cap. 2 "
                "não.\n\n")
        f.write("| secção | por verificar |\n|---|---|\n")
        for sec, lst in sorted(por_sec.items(), key=lambda x: -len(x[1])):
            f.write("| %s | %d |\n" % (sec, len(lst)))
        f.write("\n")
        for rot in sorted(grupos, key=lambda r: -len(grupos[r])):
            f.write("### %s — %d\n\n" % (rot, len(grupos[rot])))
            for i in grupos[rot][:14]:
                f.write("- `%s` (linha %d) — …%s…\n"
                        % (i["valor"], linha_do(corpo, i["pos"]),
                           i["contexto"][:150]))
            if len(grupos[rot]) > 14:
                f.write("- *(mais %d)*\n" % (len(grupos[rot]) - 14))
            f.write("\n")

        f.write("## (ii) Precisam de leitura — %d\n\n" % len(porcls.get("ii", [])))
        f.write("Sem sinal automático que os ligue a um dado. Podem ser "
                "resultados escritos de outra maneira, números da literatura "
                "citada, ou escolhas de desenho.\n\n")
        for i in porcls.get("ii", [])[:40]:
            f.write("- `%s` (linha %d) — …%s…\n"
                    % (i["valor"], linha_do(corpo, i["pos"]), i["contexto"][:140]))
        if len(porcls.get("ii", [])) > 40:
            f.write("- *(mais %d)*\n" % (len(porcls["ii"]) - 40))
        f.write("\n")

        f.write("## (iii) Não são resultados — %d\n\n" % len(porcls.get("iii", [])))
        f.write("Anos, referências internas, dimensões de figura, medidas de "
                "composição. Não há dado com que os confrontar.\n\n")
        cont = {}
        for i in porcls.get("iii", []):
            cont[i["rotulo"]] = cont.get(i["rotulo"], 0) + 1
        for k, v in sorted(cont.items(), key=lambda x: -x[1]):
            f.write("- %s: %d\n" % (k, v))
    print("\n  ESCRITO: %s" % os.path.relpath(SAIDA, RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
