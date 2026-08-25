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
# ⚠️ AVISA ANTES DE SOBRESCREVER. A 28 jul trouxe-se o CSV de um controlo do F1
# e, como o ficheiro remoto se chama `zeroshot_mapa_grande.csv` — o mesmo nome
# que a condição natural já tinha no destino —, o pscp escreveu-lhe por cima sem
# uma palavra. A condição natural (420 episódios, 6 h de servidor) só se salvou
# por estar versionada no git. Cada corrida guarda o resultado com o MESMO nome
# no SEU diretório, por isso este caso repete-se sempre que se traz mais do que
# uma; o remédio é trazer para nomes distintos, e este aviso é o que obriga a
# pensar nisso.
#
# Requisitos: VPN do ISCTE ligada + PuTTY instalado (pscp).
set -euo pipefail

# Dados de ligação: fora do repositório (configs/servidor.local.env, não
# versionado). Estiveram escritos aqui — endereço, utilizador e host key —, e
# num repositório público seriam um alvo confirmado à espera de quem tente a
# password. Modelo em configs/servidor.exemplo.env.
_CFG="$(dirname "${BASH_SOURCE[0]}")/../configs/servidor.local.env"
if [ -f "$_CFG" ]; then . "$_CFG"; fi
HOST="${SWARM_HOST:?falta SWARM_HOST — copia configs/servidor.exemplo.env para configs/servidor.local.env}"
USER="${SWARM_USER:?falta SWARM_USER em configs/servidor.local.env}"
HOSTKEY="${SWARM_HOSTKEY:?falta SWARM_HOSTKEY em configs/servidor.local.env}"
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

# O destino pode ser uma PASTA (o caso comum) ou um FICHEIRO com nome próprio —
# que é como se cumpre a regra da armadilha nº7: ao trazer várias corridas da
# mesma campanha, nomes distintos, porque o ficheiro remoto chama-se igual em
# todas. Sem esta distinção o `mkdir -p` criava uma PASTA chamada
# `zeroshot_c1_escala.csv` com o CSV lá dentro (aconteceu a 31 jul).
# Heurística: se o destino não existe e o seu nome tem extensão, é ficheiro.
if [[ ! -d "$LOCAL" && "$(basename "$LOCAL")" == *.* ]]; then
    DESTINO_E_FICHEIRO=1
    mkdir -p "$(dirname "$LOCAL")"
    ALVO="$LOCAL"
else
    DESTINO_E_FICHEIRO=0
    mkdir -p "$LOCAL"
    # O que chega chama-se como o último elemento do caminho remoto.
    ALVO="$LOCAL/$(basename "$REMOTO")"
fi
NOME="$(basename "$REMOTO")"
if [[ -e "$ALVO" && "$NOME" != *"*"* ]]; then
    echo "[trazer] ⚠️  JÁ EXISTE: $ALVO"
    echo "[trazer]     ($(du -h "$ALVO" 2>/dev/null | cut -f1), modificado $(date -r "$ALVO" '+%d %b %H:%M' 2>/dev/null))"
    echo "[trazer]     Trazer por cima APAGA-O. Se for um resultado de horas de"
    echo "[trazer]     servidor, traz para outro nome ou renomeia este primeiro."
    if [[ "${TRAZER_FORCAR:-}" != "1" ]]; then
        echo "[trazer] abortado. Para forçar: TRAZER_FORCAR=1 $0 ..." >&2
        exit 3
    fi
    echo "[trazer]     TRAZER_FORCAR=1 — a sobrescrever a pedido."
fi

echo "[trazer] $USER@$HOST:$REMOTO  ->  $ALVO"
# `-r` só quando o destino é pasta: com destino-ficheiro, o -r do pscp também
# funciona, mas manter a simetria torna o comando legível no log.
if [[ "$DESTINO_E_FICHEIRO" == "1" ]]; then
    exec "$PSCP" -p -batch -hostkey "$HOSTKEY" -pw "$PASS" \
         "$USER@$HOST:$REMOTO" "$ALVO"
fi
exec "$PSCP" -r -p -batch -hostkey "$HOSTKEY" -pw "$PASS" \
     "$USER@$HOST:$REMOTO" "$LOCAL"
