#!/usr/bin/env bash
# Espera que a condição NATURAL do F1 feche no servidor e traz o CSV nesse momento.
#
# A repetição do F1 (depois de tapar o céu por cima das paredes) tem 4 condições.
# As três de controlo já fecharam e já cá estão; falta a natural, que é a
# principal. Este script vigia-a e traz o resultado assim que a sessão `mapaNat`
# desaparecer — com o SSH a responder, para não confundir uma falha de rede com
# "acabou" (foi a maneira fácil de dar o F1 por fechado sem ele estar).
#
# Traz para um nome PRÓPRIO (`zeroshot_natural.csv`) e não para o nome remoto:
# cada corrida grava em `zeroshot_mapa_grande.csv` no seu diretório, e trazer
# duas para a mesma pasta apagou 420 episódios a 28 jul (armadilha nº7).
#
# Uso:  bash scripts/trazer_f1_ao_fechar.sh
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="$RAIZ/results/mapa_grande/f1_zeroshot_v2/zeroshot_natural.csv"
REMOTO="/home/goncalo/swarm-mapa/results/evaluation/zeroshot_mapa_grande.csv"
INTERVALO=600                        # 10 min
# 3 h por omissão; mais quando se sabe que a VPN vai estar em baixo um bocado
# (a 31 jul desligou-se o GlobalProtect para chegar ao Pi — o Pi e o servidor do
# ISCTE não se alcançam ao mesmo tempo — e o esperador desistiu a meio da tarde,
# com o F1 ainda por fechar).
FALHAS_MAX=${F1_FALHAS_MAX:-18}

falhas=0
echo "[f1] a vigiar a condição natural (sessão tmux mapaNat) — $(date '+%d %b %H:%M')"

while true; do
    vivas=$(bash "$RAIZ/scripts/servidor.sh" "tmux ls 2>/dev/null | grep -c '^mapaNat'" 2>/dev/null \
            | tail -1 | tr -d '[:space:]')
    feitos=$(bash "$RAIZ/scripts/servidor.sh" "grep -c '^    ep' ~/mapa_natural_eval.log 2>/dev/null" 2>/dev/null \
             | tail -1 | tr -d '[:space:]')

    if [[ "$vivas" =~ ^[0-9]+$ ]]; then
        falhas=0
        echo "[f1] $(date '+%H:%M')  mapaNat viva=$vivas  episódios=${feitos:-?}/420"
        if [ "$vivas" -eq 0 ]; then
            echo "[f1] CONDIÇÃO NATURAL FECHADA — a trazer ($(date '+%d %b %H:%M'))"
            if bash "$RAIZ/scripts/trazer_do_servidor.sh" "$REMOTO" "$DESTINO"; then
                linhas=$(wc -l < "$DESTINO" 2>/dev/null || echo 0)
                echo "[f1] trazido: $DESTINO ($linhas linhas; esperadas 421 = 420 ep + cabeçalho)"
                # As 4 condições ficam juntas e com nomes distintos.
                ls -1 "$(dirname "$DESTINO")"
                exit 0
            fi
            echo "[f1] o pscp falhou — o CSV continua no servidor, nada se perdeu" >&2
            exit 2
        fi
    else
        falhas=$((falhas + 1))
        echo "[f1] $(date '+%H:%M')  SSH sem resposta ($falhas/$FALHAS_MAX) — VPN?"
        if [ "$falhas" -ge "$FALHAS_MAX" ]; then
            echo "[f1] SSH mudo há 3 h. NÃO quer dizer que o F1 acabou — desisto de vigiar." >&2
            exit 1
        fi
    fi
    sleep "$INTERVALO"
done
