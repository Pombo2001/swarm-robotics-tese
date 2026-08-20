# -*- coding: utf-8 -*-
"""O README dos scripts nomeia todos os scripts, e só scripts que existem?

Correr da raiz do repositório: python scripts/testes/conferir_readme_scripts.py
"""
import io
import os
import re

D = 'scripts'
texto = io.open(os.path.join(D, 'README.md'), encoding='utf-8').read()
citados = set(re.findall(r"`([A-Za-z0-9_]+\.(?:py|sh|ps1))`", texto))

# Os do topo da pasta são os que o índice tem de nomear um a um; os das
# subpastas (`hooks/`, `testes/`) contam como existentes, para o índice os poder
# citar na secção que as descreve, mas não são exigidos linha a linha.
existem = {f for f in os.listdir(D)
           if os.path.isfile(os.path.join(D, f))
           and f.endswith(('.py', '.sh', '.ps1'))}
nas_subpastas = {f for sub in ('hooks', 'testes')
                 for f in os.listdir(os.path.join(D, sub))
                 if os.path.isfile(os.path.join(D, sub, f))}

fantasmas = sorted(citados - existem - nas_subpastas)
esquecidos = sorted(existem - citados)

print("%d ficheiros em scripts/, %d citados no README" % (len(existem), len(citados)))
if fantasmas:
    print("\nCITADOS E INEXISTENTES (%d):" % len(fantasmas))
    for f in fantasmas:
        print("   " + f)
if esquecidos:
    print("\nEXISTEM E NÃO ESTÃO NO README (%d):" % len(esquecidos))
    for f in esquecidos:
        print("   " + f)
if not fantasmas and not esquecidos:
    print("\nO índice cobre exatamente o que está na pasta.")
