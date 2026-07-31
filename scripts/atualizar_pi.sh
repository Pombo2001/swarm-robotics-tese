#!/usr/bin/env bash
# Atualiza a cópia do dashboard no Raspberry Pi — só o que mudou.
#
# O pacote completo tem 305 MB; refazê-lo e reenviá-lo por causa de três pastas
# de figuras é meia hora de espera para 10 MB de conteúdo novo. Este script leva
# só os caminhos indicados, extrai-os por cima e reinicia o serviço.
#
# A torre não tem rsync (Git Bash não o traz) e o Pi tem — mas rsync precisa dos
# dois lados, por isso vai-se de tar sobre ssh, que é o que existe em ambos.
#
# Uso:
#     scripts/atualizar_pi.sh                          # o habitual: código + figuras alteradas hoje
#     scripts/atualizar_pi.sh dashboard scripts        # caminhos à medida
set -euo pipefail

PI=pi5@192.168.68.54
DIR_PI=/home/pi5/TeseRobotics
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

if [ $# -gt 0 ]; then
    CAMINHOS=("$@")
else
    # Por omissão: o código todo (é pequeno) e as pastas de figuras tocadas nas
    # últimas 24 h. `find -newermt` evita reenviar 1 GB de campanhas antigas.
    mapfile -t FIGS < <(find results/graficos_tese -maxdepth 1 -mindepth 1 -type d \
                        -newermt '-1 day' 2>/dev/null)
    CAMINHOS=(dashboard scripts src configs "${FIGS[@]}")
fi

echo "[pi] a enviar:"
printf '     %s\n' "${CAMINHOS[@]}"

TAR=$(mktemp -t delta_pi_XXXX.tar.gz)
tar czf "$TAR" --exclude=__pycache__ --exclude='*.pyc' --exclude='*.log' "${CAMINHOS[@]}"
echo "[pi] pacote: $(du -h "$TAR" | cut -f1)"

scp -o BatchMode=yes "$TAR" "$PI:~/delta_pi.tar.gz"
ssh -o BatchMode=yes "$PI" "cd $DIR_PI && tar xzf ~/delta_pi.tar.gz && rm -f ~/delta_pi.tar.gz \
    && sudo systemctl restart swarm-dash && sleep 8 \
    && systemctl is-active swarm-dash \
    && curl -sf -o /dev/null http://127.0.0.1:8090/ && echo '[pi] no ar'"
rm -f "$TAR"
echo "[pi] http://192.168.68.54:8090/"
