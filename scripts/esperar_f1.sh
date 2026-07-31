#!/usr/bin/env bash
# Espera que as 4 condicoes do F1 fechem no servidor e sai quando isso acontecer.
#
# Sai com 0 quando as sessoes tmux mapa* desaparecerem TODAS (com o SSH a
# responder — uma falha de rede nao pode ser confundida com "acabou", que era a
# maneira facil de dar o F1 por fechado sem ele estar).
# Sai com 1 se o SSH falhar 12 vezes seguidas (2 h): ai o problema e outro.
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVALO=600      # 10 min
FALHAS_MAX=12
falhas=0

while true; do
    saida=$(bash "$RAIZ/scripts/servidor.sh" "tmux ls 2>/dev/null | grep -c '^mapa'" 2>/dev/null | tail -1 | tr -d '[:space:]')
    if [[ "$saida" =~ ^[0-9]+$ ]]; then
        falhas=0
        echo "$(date '+%H:%M')  sessoes mapa* vivas: $saida"
        if [ "$saida" -eq 0 ]; then
            echo "F1 CONCLUIDO — as 4 condicoes fecharam ($(date '+%d %b %H:%M'))"
            exit 0
        fi
    else
        falhas=$((falhas + 1))
        echo "$(date '+%H:%M')  SSH sem resposta ($falhas/$FALHAS_MAX)"
        [ "$falhas" -ge "$FALHAS_MAX" ] && { echo "SSH em baixo ha 2 h — desisto"; exit 1; }
    fi
    sleep "$INTERVALO"
done
