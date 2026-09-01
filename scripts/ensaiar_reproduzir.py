# -*- coding: utf-8 -*-
r"""O `docs/REPRODUZIR.md` posto à prova: cada promessa dele contra o disco.

Porque existe
O `REPRODUZIR.md` é a resposta à pergunta que um júri faz sempre — *«de onde vem
este número?»*. Ele promete, para cada resultado da dissertação, um ficheiro de
dados e um script. Uma promessa dessas envelhece sozinha: os dados mudam de
pasta, os scripts são renomeados, uma campanha fecha e a linha continua a dizer
«a correr». Quando isso acontece, o documento deixa de ser um mapa e passa a ser
uma lista de coisas que já não estão onde diz.

Este ensaio percorre o documento e verifica, comando a comando e caminho a
caminho:

* cada ficheiro ou pasta citado entre crases existe (globs e `{a,b}`
  expandidos), ou está declarado como fora deste disco;
* cada script citado existe em `scripts/` e compila — um `.py` com erro
  de sintaxe é uma promessa que rebenta na defesa, não antes;
* cada passo do pipeline de reprodução aponta para um script que existe.

O que não faz: correr os treinos. Reproduzir uma campanha de 21 execuções × 780
minutos não é um ensaio, é a campanha outra vez.

Uso:
    .venv/Scripts/python.exe scripts/ensaiar_reproduzir.py
    .venv/Scripts/python.exe scripts/ensaiar_reproduzir.py --listar
"""
import glob
import os
import py_compile
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(RAIZ, "docs", "REPRODUZIR.md")

# Caminhos que o documento declara, ele próprio, como não estando neste disco.
# Uma isenção sem razão escrita é uma forma educada de não corrigir.
FORA_DO_DISCO = {
    "~/swarm-novelty": "diretório do servidor de treino",
    "~/run7d_mlp": "diretório do servidor de treino",
    "~/swarm-robotics-tese": "diretório do servidor de treino",
    "~/swarm-mapa-c{1,2,3}": "diretórios do servidor de treino",
}

falhas = []
notas = []


def _ler():
    with open(DOC, encoding="utf-8") as fh:
        return fh.read()


def expandir_chavetas(token):
    """`a/{x,y}/b` → ['a/x/b', 'a/y/b'] (o shell fá-lo; o `glob` não)."""
    m = re.search(r"\{([^}]*,[^}]*)\}", token)
    if not m:
        return [token]
    saida = []
    for alt in m.group(1).split(","):
        saida += expandir_chavetas(token[:m.start()] + alt.strip() + token[m.end():])
    return saida


def normalizar(token):
    r"""Marcadores de posição do documento → padrões de `glob`.

    O mapa escreve `eval_{algo}_{cenario}.csv` e `eval_{algo}_{cen}[_fail10].csv`:
    as chavetas sem vírgula são marcadores («o algoritmo», «o cenário»), não
    alternativas de shell, e os parênteses retos marcam a parte opcional do nome.
    Tratá-los à letra dava três ficheiros «em falta» que estão no disco 50 e 21
    vezes.
    """
    token = re.sub(r"\{([^},]*)\}", "*", token)     # {algo} → *  (sem vírgula)
    token = re.sub(r"\[[^\]]*\]", "*", token)        # [_fail10] → *
    return token


def parece_caminho(token):
    if token.startswith("~") or token.startswith("http"):
        return False
    if token.startswith(".") or token.startswith("_"):
        return False        # `..._pre7d.csv`, `.tex`: fragmentos de prosa
    if any(token.endswith(ext) for ext in
           (".py", ".csv", ".md", ".tex", ".sh", ".png", ".yaml", ".json", ".zip")):
        return True
    # pastas: têm barra e não são prosa
    return "/" in token and " " not in token and not token.endswith(".")


def caminhos_citados(texto):
    """Tokens entre crases que são caminhos, com a linha onde aparecem."""
    vistos = {}
    for n, linha in enumerate(texto.splitlines(), 1):
        for token in re.findall(r"`([^`]+)`", linha):
            token = token.strip()
            # comandos: fica só o que parece caminho ("python scripts/x.py --f")
            for parte in token.split():
                parte = parte.strip("(),;:")
                if parte.startswith("~"):
                    vistos.setdefault(parte, n)
                elif parece_caminho(parte):
                    vistos.setdefault(parte, n)
    return vistos


def existe(caminho):
    """Existe algures no repositório?

    O documento cita tanto caminhos completos (`results/estatisticas/x.csv`)
    como nomes soltos (`screening.csv`, `eval_by_run_7d.csv`), porque a
    coluna ao lado já diz onde vivem. Procurar só a partir da raiz dava 36
    «ficheiros em falta» que estão todos no disco — o ensaio acusaria o
    documento de um defeito que era do ensaio.
    """
    for alt in expandir_chavetas(normalizar(caminho)):
        alt = alt.strip("/")
        alvo = os.path.join(RAIZ, alt.replace("/", os.sep))
        if glob.glob(alvo) or os.path.exists(alvo):
            return True
        # Caminho PARCIAL (`final_7d/eval_by_run_7d.csv`) ou nome solto: o mapa
        # cita-os assim porque a coluna ao lado já diz onde vivem.
        if glob.glob(os.path.join(RAIZ, "**", *alt.split("/")), recursive=True):
            return True
    return False


# 1. Os caminhos que o mapa promete
def caminhos(texto):
    print()
    print("=" * 78)
    print("CAMINHOS citados pelo REPRODUZIR.md")
    print("=" * 78)
    citados = caminhos_citados(texto)
    ok = fora = 0
    for caminho, linha in sorted(citados.items()):
        if caminho.startswith("~"):
            razao = next((r for p, r in FORA_DO_DISCO.items()
                          if caminho.startswith(p.split("{")[0])), None)
            if razao:
                fora += 1
                continue
            notas.append("linha %d: `%s` é do servidor e não está declarado"
                         % (linha, caminho))
            continue
        if existe(caminho):
            ok += 1
            if "--listar" in sys.argv:
                print("  [v] %s" % caminho)
        else:
            falhas.append("linha %d: `%s` não existe neste disco" % (linha, caminho))
            print("  [X] linha %-4d %s" % (linha, caminho))
    print("  %d caminhos existem · %d declarados como do servidor · %d em falta"
          % (ok, fora, len(falhas)))


# 2. Os scripts que o mapa manda correr
def scripts(texto):
    print()
    print("=" * 78)
    print("SCRIPTS citados: existem e compilam?")
    print("=" * 78)
    # `[a-z_]{3,}` e não `[a-z0-9_]+`: o `~/swarm-mapa-c{1,2,3}` produzia um
    # «script» chamado `2.sh` — o ensaio a inventar um achado a partir de uma
    # expansão de chavetas.
    nomes = sorted(set(re.findall(r"`?([a-z][a-z0-9_]{2,}\.(?:py|sh))`?", texto)))
    ok = 0
    tmp = os.path.join(RAIZ, ".pytest_cache", "_ensaio_compile.pyc")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    for nome in nomes:
        hits = glob.glob(os.path.join(RAIZ, "scripts", nome)) or \
            glob.glob(os.path.join(RAIZ, "**", nome), recursive=True)
        if not hits:
            falhas.append("o script `%s` é citado e não existe" % nome)
            print("  [X] %-34s não existe" % nome)
            continue
        if nome.endswith(".py"):
            try:
                py_compile.compile(hits[0], doraise=True, cfile=tmp)
            except py_compile.PyCompileError as erro:
                falhas.append("o script `%s` não compila: %s" % (nome, erro))
                print("  [X] %-34s NÃO COMPILA" % nome)
                continue
        ok += 1
        if "--listar" in sys.argv:
            print("  [v] %-34s %s" % (nome, os.path.relpath(hits[0], RAIZ)))
    print("  %d de %d scripts citados existem e compilam" % (ok, len(nomes)))


# 3. O pipeline numerado, passo a passo
def pipeline(texto):
    print()
    print("=" * 78)
    print("PIPELINE de reprodução (o bloco numerado)")
    print("=" * 78)
    bloco = re.search(r"## Pipeline de reprodução.*?```\n(.*?)```", texto, re.S)
    if not bloco:
        falhas.append("não encontrei o bloco do pipeline de reprodução")
        return
    passos = re.findall(r"^\s*(\d)\. (python|bash)? ?(\S+)", bloco.group(1), re.M)
    for n, _, alvo in passos:
        caminho = os.path.join(RAIZ, alvo.replace("/", os.sep))
        existe_ = os.path.exists(caminho)
        print("  %s passo %s: %s" % ("[v]" if existe_ else "[X]", n, alvo))
        if not existe_:
            falhas.append("passo %s do pipeline aponta para `%s`, que não existe"
                          % (n, alvo))
    if len(passos) < 4:
        notas.append("só %d passos lidos do pipeline — a formatação mudou?"
                     % len(passos))


# 4. O estado que o documento afirma
def estado(texto):
    """Afirmações datadas que o disco pode desmentir.

    O modo de falha deste documento não é dizer algo falso: é continuar a dizer
    o que era verdade. Uma campanha que fechou e uma linha que continua a dizer
    «a correr» é o que faz um mapa envelhecer sem que ninguém repare.
    """
    print()
    print("=" * 78)
    print("ESTADO afirmado  vs  o que está no disco")
    print("=" * 78)
    marcas = [
        (r"a correr desde 3 ago",
         os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn", "logs",
                      "_campanha_concluida.txt"),
         "o F2 do mapa grande", "dá-o como a correr, e a campanha tem sentinela "
         "de conclusão no disco"),
        (r"6 fases trazidas a 28 jul, 6 por fechar",
         os.path.join(RAIZ, "results", "mega_1mes", "mega_B_fase7"),
         "o mega-treino", "dá-o por meio-fechado, e as 12 fases estão no disco"),
        (r"controlos no servidor",
         os.path.join(RAIZ, "results", "mapa_grande", "f1_zeroshot_v2",
                      "zeroshot_c3_sem_porta_obs.csv"),
         "os controlos do F1", "dá-os como remotos, e estão no disco"),
    ]
    for padrao, prova, assunto, erro in marcas:
        if re.search(padrao, texto) and os.path.exists(prova):
            falhas.append("desatualizado — %s: o documento %s" % (assunto, erro))
            print("  [X] %-24s o documento %s" % (assunto, erro))
        else:
            print("  [v] %-24s o documento acompanha o disco" % assunto)


def main():
    texto = _ler()
    caminhos(texto)
    scripts(texto)
    pipeline(texto)
    estado(texto)

    print()
    print("=" * 78)
    if falhas:
        print("%d achado(s):" % len(falhas))
        for f in falhas:
            print("  [X] %s" % f)
    else:
        print("O REPRODUZIR.md bate com o disco ✓")
    for n in notas:
        print("  [i] %s" % n)
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
