# -*- coding: utf-8 -*-
"""A dissertação está em português de Portugal?

Porque existe
-------------
A tese e o artigo são escritos em PT-PT por decisão declarada (22 jun 2026), e
uma parte do texto passou por ferramentas que produzem PT-BR por omissão. A
diferença não é de estilo: um júri português lê «usuário» ou «treinamento» como
texto que não foi escrito por quem assina.

Procura marcadores LEXICAIS inequívocos (palavras que só existem numa das
variantes) e a opção de língua do `babel`. Não tenta adivinhar por gramática:
o que aqui aparece é para ser lido, não corrigido às cegas.

Uso:
    python scripts/verificar_ptpt.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                            # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = [os.path.join(RAIZ, "Tese", "main.tex"),
        os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex"),
        os.path.join(RAIZ, "Tese", "apendice_slr.tex"),
        os.path.join(RAIZ, "Artigo", "artigo.tex")]

# (marcador PT-BR, o que se usa em PT-PT). Só palavras inequívocas: fora
# ficam as que as duas variantes partilham depois do Acordo de 1990
# («otimização», «ação», «objetivo», «projeto» são iguais nas duas).
BRASILEIRISMOS = [
    (r"\busuári[oa]s?\b", "utilizador(es)"),
    (r"\btreinamentos?\b", "treino(s)"),
    (r"\baprendizados?\b", "aprendizagem"),
    (r"\bgerenciamentos?\b", "gestão"),
    (r"\bgerenciar\b", "gerir"),
    (r"\bequipes?\b", "equipa(s)"),
    (r"\btelas?\b", "ecrã(s)"),
    (r"\bcontatos?\b", "contacto(s)"),
    (r"\bfatos?\b", "facto(s)"),
    (r"\bregistros?\b", "registo(s)"),
    (r"\bacurácia\b", "exatidão"),
    (r"\bplanejamentos?\b", "planeamento"),
    (r"\bplanejar\b", "planear"),
    (r"\brodar\b", "correr / executar"),
    (r"\bcaix[ao] de ferramentas\b", "conjunto de ferramentas"),
    (r"\bcelulares?\b", "telemóvel(eis)"),
    (r"\bmidia\b", "suporte / meios"),
    (r"\bônibus\b", "autocarro"),
    (r"\bxícara\b", "chávena"),
    (r"\bbanheir[oa]s?\b", "casa de banho"),
    (r"\bgeladeiras?\b", "frigorífico"),
    (r"\btime\b(?![ -]?step)", "equipa"),
    (r"\bestoques?\b", "existências"),
    (r"\bsuco\b", "sumo"),
    (r"\bônus\b", "bónus"),
    (r"\banônim[oa]s?\b", "anónimo(a)"),
    (r"\bgênero\b", "género"),
    (r"\bcenári[oa] de teste do usuário\b", "—"),
    # acentuação divergente (PT-BR usa ô/ê onde PT-PT usa ó/é)
    (r"\bconsensos? econômic", "económic"),
    (r"\beconômic[oa]s?\b", "económico(a)"),
    (r"\bacadêmic[oa]s?\b", "académico(a)"),
    (r"\bautônom[oa]s?\b", "autónomo(a)"),
    (r"\beletrônic[oa]s?\b", "eletrónico(a)"),
    (r"\bfenômen[oa]s?\b", "fenómeno(s)"),
    (r"\bparâmetros? dinâmic", "—"),
    (r"\btônic[oa]s?\b", "tónico(a)"),
    (r"\bcotidian[oa]s?\b", "quotidiano(a)"),
]


# «run» era masculino; «execução» é feminino — e a migração de terminologia
# trocou a palavra sem acertar o que a rodeava. Ficaram frases como «GNN com
# dois execuções degeneradas», «em todos as execuções» e «execuções resolvidas
# e falhados»: oito, todas no Capítulo 6, nenhuma visível a um verificador de
# números, porque nenhum número mudou.
#
# Duas famílias de regra, ambas conservadoras — só apanham o que é
# inequivocamente masculino junto de «execução/execuções»:
DETERMINANTES_MASC = (r"um|dois|todos|esse|este|desse|deste|nesse|neste|"
                      r"aquele|aqueles|outros|muitos|poucos|vários|alguns|"
                      r"quantos|ambos|mesmos|próprios|os|dos|aos|nos|pelos")
PARTICIPIOS_MASC = (r"agrupados|falhados|resolvidos|degenerados|fechados|"
                    r"convergidos|realizados|analisados|reportados|"
                    r"guardados|excluídos|incluídos|contados|afastados|"
                    r"agrupados|espalhados|repartidos|distribuídos|"
                    # Adjetivos, não particípios — mas concordam do mesmo modo,
                    # e foi um deles que escapou: a cronologia do dashboard
                    # dizia «duas execuções completos do objetivo puro».
                    r"completos|incompletos|válidos|inválidos|novos|antigos|"
                    r"lançados|perdidos|descartados|cancelados|usados|"
                    r"escondidos|listados|mostrados|feitos|corridos")

# Cada exceção é uma dívida declarada: a frase está certa e a regra é que não
# a sabe ler. Vazio hoje — e é assim que se vê quando deixa de estar.
CONCORDANCIA_ACEITE = ()

# O que ESTE verificador não apanha, medido e não suposto: das oito frases
# corrigidas, sete voltam a ser acusadas se alguém as desfizer;
# a oitava não. Era «quatro das sete execuções convergem …, dois degeneram por
# completo» — o sujeito de «dois» está elidido, e apanhá-lo exigiria decidir a
# que substantivo se refere. Uma regra que o tentasse acusaria «os dois métodos
# de gradiente» na frase anterior, que está certa.


def concordancia_execucao(tex, nome):
    """Frases em que «execução/execuções» aparece com companhia masculina."""
    achados = []

    # 1. determinante masculino antes, com um `\emph{...}` ou `\textbf{...}`
    #    opcional pelo meio: «em \emph{todos} as execuções». Entre o
    #    determinante e a palavra só se admite o que não muda o género da
    #    frase — «um **ou mais** execuções», «todos **as 28** execuções».
    #    Qualquer outra coisa costuma ser outro substantivo, e aí o masculino
    #    está certo: «todos os cenários … execuções» não pode cair aqui.
    d1 = re.compile(r"\b(?:" + DETERMINANTES_MASC + r")\}?\s+"
                    r"(?:(?:ou\s+mais|as|umas|\d+)\s+)*"
                    r"(?:\\\w+\{)?(?:\d+\s+)?execuç(?:ão|ões)", re.IGNORECASE)
    # 2. particípio masculino logo a seguir, na mesma oração (janela curta, e
    #    sem vírgula pelo meio — a vírgula costuma introduzir outro sujeito).
    d2 = re.compile(r"execuç(?:ão|ões)[^,;.]{0,35}?\b(?:" + PARTICIPIOS_MASC
                    + r")\b", re.IGNORECASE)

    for regra, padrao in (("determinante", d1), ("particípio", d2)):
        for m in padrao.finditer(tex):
            trecho = " ".join(m.group(0).split())
            # «os execuções» é erro; «dos execuções» também — mas «dos três
            # algoritmos … execuções» não, e é por isso que a regra 1 exige
            # que a palavra seguinte SEJA execução (ou um número antes dela).
            if any(re.search(exc, trecho, re.IGNORECASE)
                   for exc in CONCORDANCIA_ACEITE):
                continue
            linha = tex.count("\n", 0, m.start()) + 1
            ctx = " ".join(tex[max(0, m.start() - 55):m.end() + 45].split())
            achados.append("%s:%d  concordância (%s): «%s»\n        …%s…"
                           % (nome, linha, regra, trecho, ctx))
    return achados


def sem_comentarios(t):
    return re.sub(r"(?<!\\)%[^\n]*", "", t)


# ── o texto que o dashboard escreve no ecrã ──────────────────────────────────
# A dissertação e o artigo passavam por aqui; o dashboard nunca passou. E é
# prosa portuguesa como a outra: a cronologia do Overview dizia «duas execuções
# completos do objetivo puro» — a mesma concordância que a dissertação já não
# tinha. Como o dashboard é Python, não se pode ler o ficheiro inteiro (o código
# à volta produziria ruído sem fim); lê-se só o que vai para o ecrã.
DASH = os.path.join(RAIZ, "dashboard")

# Frases do ecrã em que um marcador aparece com o sentido bom. «Rodar» é
# brasileirismo quando quer dizer *executar*; em «arrasta para rodar» quer
# dizer *girar a câmara*, que é português corrente. Declaradas uma a uma —
# a lista curta é o que mantém a regra a valer.
ACEITE_NO_ECRA = (
    "arrasta para rodar",
)


def texto_de_ecra(path):
    """O ficheiro reduzido aos seus literais de string, linha a linha.

    Devolve um texto com o mesmo número de linhas do original e, em cada uma,
    os literais que ali estão — para que as linhas comunicadas sejam as linhas
    reais do ficheiro. Docstrings ficam de fora: são notas para quem lê o
    código, não frases que alguém veja no ecrã.
    """
    import ast
    fonte = open(path, encoding="utf-8").read()
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return ""
    docs = set()
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None)
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and corpo:
            p = corpo[0]
            if isinstance(p, ast.Expr) and isinstance(p.value, ast.Constant) \
                    and isinstance(p.value.value, str):
                docs.add(id(p.value))
    linhas = [[] for _ in range(fonte.count("\n") + 2)]
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) \
                and id(no) not in docs and " " in no.value:
            linhas[no.lineno].append(no.value.replace("\n", " "))
    return "\n".join(" ".join(l) for l in linhas)


def ficheiros_do_dashboard():
    saida = []
    for pasta in (DASH, os.path.join(DASH, "views")):
        if not os.path.isdir(pasta):
            continue
        saida += [os.path.join(pasta, f) for f in sorted(os.listdir(pasta))
                  if f.endswith(".py") and f != "__init__.py"]
    return saida


def main():
    print("=" * 74)
    print("PT-PT: marcadores lexicais brasileiros e opção do babel")
    print("=" * 74)
    problemas = []

    for f in DOCS:
        if not os.path.exists(f):
            continue
        tex = sem_comentarios(open(f, encoding="utf-8").read())
        nome = os.path.relpath(f, RAIZ)

        for padrao, alternativa in BRASILEIRISMOS:
            for m in re.finditer(padrao, tex, re.IGNORECASE):
                linha = tex.count("\n", 0, m.start()) + 1
                ctx = " ".join(tex[max(0, m.start() - 45):m.end() + 45].split())
                problemas.append("%s:%d  «%s» → %s\n        …%s…"
                                 % (nome, linha, m.group(0), alternativa, ctx))

        problemas += concordancia_execucao(tex, nome)

        # o babel: `brazilian` mudaria hifenização, datas e nomes de secções
        for m in re.finditer(r"\\usepackage\[([^\]]*)\]\{babel\}", tex):
            opcoes = m.group(1).lower()
            if "brazil" in opcoes:
                problemas.append("%s: babel com opção `brazilian` — deve ser "
                                 "`portuguese`" % nome)
            elif "portug" not in opcoes:
                problemas.append("%s: babel sem `portuguese` (opções: %s)"
                                 % (nome, opcoes))
            else:
                print("   [v] %-34s babel: %s" % (nome, opcoes))

    # ── e o texto que o dashboard mostra ─────────────────────────────────────
    ficheiros = ficheiros_do_dashboard()
    for f in ficheiros:
        ecra = texto_de_ecra(f)
        if not ecra.strip():
            continue
        nome = os.path.relpath(f, RAIZ)
        for padrao, alternativa in BRASILEIRISMOS:
            for m in re.finditer(padrao, ecra, re.IGNORECASE):
                ctx = " ".join(ecra[max(0, m.start() - 45):m.end() + 45].split())
                if any(a in ctx for a in ACEITE_NO_ECRA):
                    continue
                linha = ecra.count("\n", 0, m.start()) + 1
                problemas.append("%s:%d  «%s» → %s\n        …%s…"
                                 % (nome, linha, m.group(0), alternativa, ctx))
        problemas += concordancia_execucao(ecra, nome)
    print("   [v] %-34s %d ficheiros de ecrã"
          % ("dashboard/", len(ficheiros)))

    if problemas:
        print("\n%d ocorrência(s) para ler:" % len(problemas))
        for p in problemas:
            print("   " + p)
        print("=" * 74)
        return 1
    print("\nSem marcadores brasileiros nos %d documentos nem nos %d ficheiros "
          "de ecrã ✓" % (len(DOCS), len(ficheiros)))
    print("NOTA: procura LÉXICO inequívoco. Palavras que as duas variantes")
    print("      partilham desde o Acordo de 1990 («otimização», «ação»,")
    print("      «projeto», «objetivo») não são sinal de nada.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
