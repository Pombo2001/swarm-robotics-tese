#!/usr/bin/env bash
# Traz ficheiros do servidor de treino do ISCTE — o par do scripts/servidor.sh.
#
# Existe pela mesma razão: o host, o utilizador e a hostkey certos num sítio só, e
# a password lida de ~/.swarm_ssh_pass (FORA do repositório) em vez de escrita na
# linha de comandos, onde ficaria no histórico da shell.
#
# Uso:
#     scripts/trazer_do_servidor.sh <caminho_remoto> <destino_local>
#
# Exemplo (campeões da campanha 7d, para o F1 do mapa grande):
#     scripts/trazer_do_servidor.sh \
#         '~/swarm-robotics-tese/results/graficos_tese/09-07-2026_12h52m/modelos' \
#         results/models_7d
#
# ⚠️ Preserva as DATAS dos ficheiros (`-p`). Não é cosmético: a guarda de campanha
# do scripts/eval_zeroshot_mapa.py verifica a data de cada campeão contra a janela
# da campanha (2026-07-02..2026-07-10) e ABORTA se for anterior. Sem `-p`, todos
# os modelos chegavam com a data de hoje e a guarda deixava de distinguir a
# campanha 7d de qualquer outra coisa — que é exatamente o que ela existe para
# apanhar (ver a emenda de 25 jul no PRE_REGISTO_MAPA_GRANDE.md).
#
# Requisitos: VPN do ISCTE ligada + PuTTY instalado (pscp).
set -euo pipefail

HOST=SERVIDOR_DE_TREINO           # dellicious
USER=goncalo
HOSTKEY=SHA256:HOSTKEY_REMOVIDA
PSCP="/c/Program Files/PuTTY/pscp.exe"
FICHEIRO_PASS="$HOME/.swarm_ssh_pass"

if [[ $# -lt 2 ]]; then
    echo "uso: $0 <caminho_remoto> <destino_local>" >&2
    exit 2
fi
REMOTO="$1"
LOCAL="$2"

PASS="${SWARM_SSH_PASS:-}"
if [[ -z "$PASS" && -f "$FICHEIRO_PASS" ]]; then
    PASS=$(<"$FICHEIRO_PASS")
fi
if [[ -z "$PASS" ]]; then
    echo "Sem password. Cria o ficheiro uma vez:" >&2
    echo "    printf '%s' 'a-tua-password' > ~/.swarm_ssh_pass" >&2
    exit 2
fi

mkdir -p "$LOCAL"
echo "[trazer] $USER@$HOST:$REMOTO  ->  $LOCAL"
exec "$PSCP" -r -p -batch -hostkey "$HOSTKEY" -pw "$PASS" \
     "$USER@$HOST:$REMOTO" "$LOCAL"
