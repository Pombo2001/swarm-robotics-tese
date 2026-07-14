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
#     scripts/servidor.sh                            # estado: tmux + carga + logs do treino
#     scripts/servidor.sh "tail -40 ~/week_A.log"    # comando à medida
#
# Requisitos: VPN do ISCTE ligada + PuTTY instalado (plink).
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

ESTADO='tmux ls 2>&1; echo; echo "--- carga ---"; uptime; date
echo; echo "--- week_A ---"; tail -3 ~/swarm-robotics-tese/week_A.log 2>/dev/null
echo; echo "--- week_B ---"; tail -3 ~/swarm-robotics-tese/week_B.log 2>/dev/null'

exec "$PLINK" -ssh -batch -hostkey "$HOSTKEY" -pw "$PASS" \
     "$USER@$HOST" "${1:-$ESTADO}"
