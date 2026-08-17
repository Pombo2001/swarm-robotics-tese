# -*- coding: utf-8 -*-
r"""O que as vistas leem  vs  o que o `atualizar_pi.sh` envia.

Porque existe
-------------
A cópia publicada no Raspberry Pi é atualizada por um **delta**: uma lista de
caminhos escrita à mão no `scripts/atualizar_pi.sh`, mais as figuras tocadas
numa janela de tempo. Sempre que uma vista passa a ler um ficheiro novo e
ninguém acrescenta esse caminho ao script, o Pi fica sem ele — e o modo como
falha é o pior possível: a vista **não rebenta**, devolve `None` e cala-se. Foi
assim que o cartão do mega-treino desapareceu do Pi sem um erro, e que a Galeria
lá ficou sem um único selo.

Este verificador corre as 16 vistas com as leituras de ficheiro instrumentadas,
recolhe **todos os caminhos do repositório que elas de facto abrem**, e confronta
cada um com a cobertura do `atualizar_pi.sh`. Falha quando aparece uma leitura
que o delta não leva.

O que **não** faz: falar com o Pi. Não precisa — a pergunta é sobre o script de
publicação, não sobre o estado da máquina, e a publicação é em lote e a pedido.

Uso:
    .venv/Scripts/python.exe scripts/verificar_paridade_pi.py
    .venv/Scripts/python.exe scripts/verificar_paridade_pi.py --listar
"""
import builtins
import glob as glob_mod
import importlib
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

SCRIPT_PI = os.path.join(RAIZ, "scripts", "atualizar_pi.sh")

# Pastas de código: o script envia-as inteiras, e ninguém precisa de as auditar
# ficheiro a ficheiro.
CODIGO = ("dashboard", "scripts", "src", "configs")

# Leituras que NÃO têm de ir para o Pi, com a razão. Uma isenção sem razão é uma
# forma educada de não corrigir.
ISENTOS = {
    # `results/models`, `models_7d`, `models_ppo`, `models_f2_gnn`… — as vistas
    # só lhes testam a EXISTÊNCIA (para dizer que há modelo), e no Pi essa
    # verificação dá negativa sem mentir: o Pi não treina nem avalia.
    "results/models": "modelos (centenas de MB); o Pi não treina nem avalia",
    "results/logs": "logs de treino em bruto; as vistas leem os CSV agregados",
    "out": "artefactos de trabalho local, nunca publicados",
    ".venv": "ambiente virtual",
    ".git": "repositório",
    "graphify-out": "índice de trabalho, não é conteúdo do dashboard",
}


def caminhos_do_script():
    r"""Os caminhos que o `atualizar_pi.sh` envia, lidos do próprio script.

    ⚠️ Duas armadilhas, ambas apanhadas a construir isto:

    1. **Os comentários não são caminhos.** A primeira versão apanhava o bloco
       inteiro entre `CAMINHOS=(` e `)` com um regex e partia-o por espaços — e
       o bloco tem trinta linhas de comentário, onde se citam caminhos a
       explicar porque é que lá estão. Resultado: 766 «caminhos», e qualquer
       leitura mencionada num comentário passava a contar como enviada. Um
       verificador que se deixa convencer por um comentário não verifica nada.
    2. **Os globs têm de ser expandidos.** O bash expande `results/*/evaluation`
       ao construir o array; quem lê o ficheiro em Python tem de o fazer também,
       senão dá por não enviado o que é enviado.
    """
    with open(SCRIPT_PI, encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    inicio = next((i for i, l in enumerate(linhas)
                   if l.strip().startswith("CAMINHOS=(")
                   and '"$@"' not in l), None)
    if inicio is None:
        raise SystemExit("não encontrei o array CAMINHOS= no atualizar_pi.sh")
    bruto = []
    for linha in linhas[inicio:]:
        limpa = linha.split("#", 1)[0]           # comentário não é caminho
        bruto.append(limpa)
        if ")" in limpa:
            break
    texto = " ".join(bruto)
    texto = texto[texto.index("(") + 1:texto.rindex(")")]
    texto = texto.replace('"${FIGS[@]}"', "")
    caminhos = []
    for token in texto.split():
        token = token.strip().strip('"')
        if not token:
            continue
        if any(c in token for c in "*?["):
            caminhos += [_rel(h) for h in glob_mod.glob(os.path.join(RAIZ, token))
                         if _rel(h)]
        else:
            caminhos.append(token)
    # As figuras vão por `find results/graficos_tese -newermt`: cobertura por
    # janela de tempo, não por caminho. Trata-se como coberta, mas assinala-se —
    # a janela já falhou uma vez (nove dias sem publicar, delta de um dia).
    caminhos.append("results/graficos_tese")
    return caminhos


def _rel(caminho):
    try:
        rel = os.path.relpath(os.path.abspath(caminho), RAIZ)
    except ValueError:
        return None
    if rel.startswith(".."):
        return None
    return rel.replace("\\", "/")


def recolher_leituras():
    """Os caminhos do repositório que as 16 vistas abrem ao construir-se."""
    lidos = set()
    open_real, exists_real, glob_real = builtins.open, os.path.exists, glob_mod.glob

    def _reg(caminho):
        rel = _rel(caminho)
        if rel and os.path.isfile(caminho):
            lidos.add(rel)

    def open_espia(ficheiro, *a, **kw):
        if isinstance(ficheiro, (str, bytes, os.PathLike)):
            try:
                _reg(os.fspath(ficheiro))
            except Exception:  # noqa: BLE001
                pass
        return open_real(ficheiro, *a, **kw)

    def exists_espia(caminho):
        ok = exists_real(caminho)
        if ok:
            try:
                _reg(caminho)
            except Exception:  # noqa: BLE001
                pass
        return ok

    def glob_espia(padrao, *a, **kw):
        hits = glob_real(padrao, *a, **kw)
        for h in hits:
            try:
                _reg(h)
            except Exception:  # noqa: BLE001
                pass
        return hits

    from nicegui import ui

    from dashboard.jobs import JobQueue
    from scripts.auditar_dashboard import VISTAS

    builtins.open = open_espia
    os.path.exists = exists_espia
    glob_mod.glob = glob_espia
    silencio = io.StringIO()
    real_stdout = sys.stdout
    try:
        fila = JobQueue()
        for nome in VISTAS:
            mod = importlib.import_module("dashboard.views." + nome)
            try:
                sys.stdout = silencio
                with ui.element("div"):
                    try:
                        mod.build(fila)
                    except TypeError as erro:
                        if "positional argument" not in str(erro):
                            raise
                        mod.build()
            except Exception as erro:  # noqa: BLE001
                sys.stdout = real_stdout
                print("  [!] a vista «%s» rebentou (%s) — as leituras dela ficam "
                      "por auditar" % (nome, type(erro).__name__))
            finally:
                sys.stdout = real_stdout
    finally:
        builtins.open, os.path.exists, glob_mod.glob = open_real, exists_real, glob_real
    return lidos


def coberto(rel, caminhos):
    for c in caminhos:
        c = c.rstrip("/")
        if rel == c or rel.startswith(c + "/"):
            return c
    return None


def isento(rel):
    for prefixo, razao in ISENTOS.items():
        p = prefixo.rstrip("/")
        # `results/models` isenta também `results/models_7d`, `models_ppo`,
        # `models_f2_gnn` — são a mesma coisa com sufixo de campanha, e listá-los
        # um a um garantia que o próximo ficasse de fora.
        if rel == p or rel.startswith(p + "/") or rel.startswith(p + "_"):
            return razao
    return None


def main():
    print("=" * 78)
    print("PARIDADE Pi ↔ local: o que as vistas leem vs o que o delta envia")
    print("=" * 78)
    caminhos = caminhos_do_script()
    lidos = sorted(recolher_leituras())
    print("  %d caminhos no atualizar_pi.sh · %d ficheiros lidos pelas vistas"
          % (len(caminhos), len(lidos)))

    # Guarda contra o modo de falha mais perigoso deste verificador: a
    # instrumentação deixar de ver as leituras (uma vista que passe a usar
    # `pathlib`, um `pd.read_csv` com handle já aberto) e ele anunciar «tudo
    # coberto» sobre um conjunto vazio. Um verificador que não encontra o que
    # procura tem de dar erro, não silêncio.
    if len(lidos) < 100:
        print("  [X] só %d leituras recolhidas — a instrumentação partiu-se "
              "(esperam-se ~300)" % len(lidos))
        return 1

    if "--listar" in sys.argv:
        for rel in lidos:
            print("    %-64s %s" % (rel, coberto(rel, caminhos) or "—"))

    falhas, isentados = [], 0
    for rel in lidos:
        if any(rel.startswith(c + "/") or rel == c for c in CODIGO):
            continue
        if coberto(rel, caminhos):
            continue
        razao = isento(rel)
        if razao:
            isentados += 1
            continue
        falhas.append(rel)

    print()
    if falhas:
        print("  %d leitura(s) que o Pi NÃO recebe:" % len(falhas))
        for rel in falhas:
            print("    [X] %s" % rel)
        print()
        print("  Corrigir acrescentando o caminho ao array CAMINHOS= do")
        print("  scripts/atualizar_pi.sh — com o comentário a dizer que vista o lê.")
    else:
        print("  [v] todas as leituras das vistas estão cobertas pelo delta "
              "(%d isentas por razão declarada)" % isentados)

    print()
    print("  [i] `results/graficos_tese` vai por janela de tempo (`DESDE`, por "
          "omissão 1 dia):")
    print("      ficheiros mais antigos que a janela NÃO vão, mesmo estando "
          "cobertos pelo caminho.")
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
