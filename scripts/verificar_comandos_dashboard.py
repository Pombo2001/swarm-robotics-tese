# -*- coding: utf-8 -*-
"""Os comandos que o dashboard manda copiar existem e aceitam o que lhes passa.

A vista «Proveniência» promete, por cada célula da `tab:res_eval`, «o comando
que as reproduz» — e quem defende a dissertação pode ser convidado a colá-lo no
terminal. Durante meses esse comando foi

    python scripts/eval_by_run.py --algo gnn --scenario u_wall --episodes 20

quando o script declara `--algos` e `--scenarios`. Corria por acaso: o argparse
aceita prefixos não ambíguos. Bastava o script ganhar uma opção começada por
«algo» para o comando do ecrã passar a rebentar, e ninguém daria por isso — o
dashboard constrói-se sem nunca tocar no script que cita.

Verifica, sem executar nada:

* o ficheiro citado existe;
* cada `--opção` do comando é declarada por um `add_argument` desse ficheiro,
  pelo nome exato (prefixos abreviados são recusados de propósito: funcionam
  hoje e partem-se amanhã).

Uso:
    .venv/Scripts/python.exe scripts/verificar_comandos_dashboard.py
"""
from __future__ import annotations

import ast
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(RAIZ, "dashboard")

# Um comando é uma string que invoca um script do projeto. Apanha as duas
# formas que o dashboard usa: com o interpretador à frente e sem ele.
COMANDO = re.compile(r"(?:python\s+|\.venv/Scripts/python\.exe\s+)?"
                     r"((?:scripts|tools)/[\w/]+\.(?:py|sh))((?:\s+[^\s\"']+)*)")
OPCAO = re.compile(r"(?<!\w)--([a-zA-Z][\w-]*)")

# Opções que não são do script citado: pertencem a um comando encadeado ou são
# do próprio interpretador. Declaradas, para a regra não se diluir.
OPCOES_ALHEIAS = frozenset()

problemas: list[str] = []
conferidos = 0


def literais(path):
    """(linha, texto) dos literais de string do ficheiro, docstrings à parte."""
    with open(path, encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    docs = set()
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None)
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and corpo:
            p = corpo[0]
            if isinstance(p, ast.Expr) and isinstance(p.value, ast.Constant) \
                    and isinstance(p.value.value, str):
                docs.add(id(p.value))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) \
                and id(no) not in docs:
            yield no.lineno, no.value


def opcoes_declaradas(script: str) -> set[str] | None:
    """As opções longas que o script declara. None se não for legível."""
    caminho = os.path.join(RAIZ, script)
    if not os.path.exists(caminho):
        return None
    fonte = open(caminho, encoding="utf-8", errors="replace").read()
    if script.endswith(".sh"):
        # Nos guiões de shell não há argparse: aceita-se o que o texto do
        # próprio guião menciona (é o contrato que ele publica).
        return set(re.findall(r"--([a-zA-Z][\w-]*)", fonte))
    achadas = set()
    for m in re.finditer(r"add_argument\(\s*((?:[\"'][^\"']+[\"']\s*,?\s*){1,3})",
                         fonte):
        for nome in re.findall(r"[\"']--([\w-]+)[\"']", m.group(1)):
            achadas.add(nome)
    # Nem todos os scripts usam argparse: o `gerar_figuras_7d.py` decide com
    # `if '--install-oficial' in sys.argv`. Uma opção lida assim é tão real
    # como as outras, e ignorá-la fazia o verificador acusar um comando bom.
    for linha in fonte.splitlines():
        if "sys.argv" not in linha:
            continue
        for nome in re.findall(r"[\"']--([\w-]+)[\"']", linha):
            achadas.add(nome)
    return achadas


def ficheiros():
    saida = []
    for pasta in (DASH, os.path.join(DASH, "views")):
        saida += [os.path.join(pasta, f) for f in sorted(os.listdir(pasta))
                  if f.endswith(".py") and f != "__init__.py"]
    return saida


def main() -> int:
    global conferidos
    vistos = set()
    for path in ficheiros():
        rel = os.path.relpath(path, RAIZ).replace(os.sep, "/")
        for linha, texto in literais(path):
            # Uma string partida em várias («... --algos %s » + «--episodes 20»)
            # chega aqui já concatenada pelo parser, que é o que se quer.
            for m in COMANDO.finditer(texto):
                script, resto = m.group(1), m.group(2) or ""
                declaradas = opcoes_declaradas(script)
                chave = (script, resto.strip())
                if chave in vistos:
                    continue
                vistos.add(chave)
                conferidos += 1
                if declaradas is None:
                    problemas.append("%s:%d cita um ficheiro que não existe: %s"
                                     % (rel, linha, script))
                    continue
                for opcao in OPCAO.findall(resto):
                    if opcao in OPCOES_ALHEIAS or opcao in declaradas:
                        continue
                    perto = sorted(d for d in declaradas
                                   if d.startswith(opcao) or opcao.startswith(d))
                    dica = (" — o script declara %s" % ", ".join("--" + p
                                                                 for p in perto)
                            if perto else "")
                    problemas.append(
                        "%s:%d  %s não tem a opção --%s%s"
                        % (rel, linha, script, opcao, dica))

    print("=" * 74)
    print("Comandos que o dashboard manda copiar")
    print("=" * 74)
    print("  %d comando(s) distinto(s) em %d ficheiros"
          % (conferidos, len(ficheiros())))
    if problemas:
        print("\n%d problema(s):" % len(problemas))
        for p in problemas:
            print("  [X] %s" % p)
        print("=" * 74)
        return 1
    print("\nTodos existem e as opções são as declaradas ✓")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
