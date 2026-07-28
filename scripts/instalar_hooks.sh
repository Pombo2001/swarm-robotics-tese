#!/usr/bin/env bash
# Instala os hooks de git deste repositório.
#
# O `.git/hooks/` não é versionado, por isso os hooks vivem em `scripts/hooks/`
# e copiam-se para lá. Correr uma vez por clone (e outra vez se o hook mudar).
#
#     scripts/instalar_hooks.sh            # instala
#     scripts/instalar_hooks.sh --remover  # desinstala
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORIGEM="$RAIZ/scripts/hooks"
DESTINO="$(git -C "$RAIZ" rev-parse --git-path hooks)"

if [[ "${1:-}" == "--remover" ]]; then
    for h in "$ORIGEM"/*; do
        alvo="$DESTINO/$(basename "$h")"
        [ -f "$alvo" ] && rm -f "$alvo" && echo "removido: $(basename "$h")"
    done
    exit 0
fi

mkdir -p "$DESTINO"
for h in "$ORIGEM"/*; do
    nome="$(basename "$h")"
    cp "$h" "$DESTINO/$nome"
    chmod +x "$DESTINO/$nome"
    echo "instalado: $nome"
done

echo
echo "O pre-commit corre o verificar_numeros_tese.py quando o commit toca em"
echo "Tese/main.tex ou nos CSV canónicos. Escape: git commit --no-verify"
