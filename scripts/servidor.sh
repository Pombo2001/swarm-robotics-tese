#!/usr/bin/env bash
# Ligação ao servidor de treino do ISCTE — o host e o utilizador CERTOS, num sítio só.
#
# Existe porque já se perdeu tempo a tentar IPs de memória (e o errado dá "connection
# timed out", que se confunde com a VPN em baixo ou com o servidor ocupado).
#
# A password NÃO está aqui, nem deve alguma vez ser escrita na linha de comandos (ficaria
# no histórico da shell e nos logs). Vem de ~/.swarm_ssh_pass — um ficheiro FORA do
# repositório, criado uma única vez:
#     printf '%s' 'a-password' > ~/.swarm_ssh_pass
# Em alternativa, da variável de ambiente SWARM_SSH_PASS, se preferires.
#
# Uso:
#     scripts/servidor.sh                                  # estado: tmux + carga + campanha viva
#     scripts/servidor.sh "tail -40 ~/mega_A_master.log"   # comando à medida
#
# O estado DESCOBRE a campanha a correr (não tem nomes de campanha lá dentro). Antes
# estavam os `week_*` em duro e, quando o mega-treino arrancou, o script continuava a
# dizer "CONCLUÍDO" da campanha anterior — parecia que não corria nada.
#
# Requisitos: VPN do ISCTE ligada + PuTTY instalado (plink).
# Nota: o servidor não responde a ping (ICMP bloqueado). Timeout aqui = VPN em baixo.
set -euo pipefail

HOST=SERVIDOR_DE_TREINO           # dellicious
USER=goncalo
HOSTKEY=SHA256:HOSTKEY_REMOVIDA
PLINK="/c/Program Files/PuTTY/plink.exe"
FICHEIRO_PASS="$HOME/.swarm_ssh_pass"

PASS="${SWARM_SSH_PASS:-}"
if [[ -z "$PASS" && -f "$FICHEIRO_PASS" ]]; then
    PASS=$(<"$FICHEIRO_PASS")
fi
if [[ -z "$PASS" ]]; then
    echo "Sem password. Cria o ficheiro uma vez:" >&2
    echo "    printf '%s' 'a-tua-password' > ~/.swarm_ssh_pass" >&2
    exit 2
fi

# Comando de estado. Heredoc com aspas ('REMOTO') para o shell LOCAL não expandir nada:
# tudo aqui dentro corre no servidor. `read -d ''` devolve !=0 no fim → `|| true`.
read -r -d '' ESTADO <<'REMOTO' || true
tmux ls 2>&1
echo
echo "--- carga ---"
uptime
date

SESSOES=$(tmux ls -F '#{session_name}' 2>/dev/null)

if [ -z "$SESSOES" ]; then
    echo
    echo "--- SEM TREINOS A CORRER — últimas campanhas ---"
    for log in $(ls -t ~/*_master.log 2>/dev/null | head -2); do
        echo "== $(basename "$log") (fim: $(date -r "$log" '+%d %b %H:%M')) =="
        grep -E '^\[[A-Za-z_]+\] (FASE|CONCLU)' "$log" 2>/dev/null | tail -2
    done
    exit 0
fi

for s in $SESSOES; do
    # tmux "week_A" -> week_A_master.log ; tmux "megaA" -> mega_A_master.log
    log="$HOME/${s}_master.log"
    [ -f "$log" ] || log="$HOME/$(echo "$s" | sed 's/\([a-z]\)\([A-Z]\)/\1_\2/g')_master.log"

    echo
    echo "--- $s ---"
    if [ -f "$log" ]; then
        # Só os marcadores do arranque de fase — não as linhas [INFO] do treino.
        echo "fase:  $(grep -E '^\[[A-Za-z_]+\] (FASE|CONCLU)' "$log" | tail -1)"
        echo "log:   $(basename "$log")  (escrito há $(( ($(date +%s) - $(date -r "$log" +%s)) / 60 )) min)"
        # Do LOG, não do capture-pane: o pane parte as linhas à largura do terminal.
        tail -2 "$log"
    else
        echo "(sem *_master.log correspondente — leitura direta do pane)"
        tmux capture-pane -pt "$s" -S -3 2>/dev/null | tail -3
    fi
done
REMOTO

exec "$PLINK" -ssh -batch -hostkey "$HOSTKEY" -pw "$PASS" \
     "$USER@$HOST" "${1:-$ESTADO}"
