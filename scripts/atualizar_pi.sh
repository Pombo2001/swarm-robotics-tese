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
    # A data que conta é a dos FICHEIROS, não a das pastas: regenerar figuras
    # por cima das antigas não mexe no mtime da pasta (só criar ou apagar o faz),
    # e por isso o critério antigo via 2 campanhas alteradas onde havia 15 — as
    # outras 13 ficavam no Pi com as figuras da véspera, sem sinal nenhum.
    mapfile -t FIGS < <(find results/graficos_tese -mindepth 2 -type f \
                        -newermt '-1 day' -printf '%h\n' 2>/dev/null \
                        | sed 's|\(results/graficos_tese/[^/]*\).*|\1|' | sort -u)
    # Duas pastas de RESULTADOS que não são figuras e o delta não levava:
    #   · episodios_3d — a vista «Episódio 3D» lê-os do disco. Ficaram 13 no Pi
    #     quando cá já havia 21: os oito do PPO e do SAC não chegavam lá.
    #   · mapa_grande  — os CSV do F1 que a vista «Mapa grande» lê. Sem isto, o
    #     Pi mostrava a corrida ANULADA (ou nada), que é pior do que não mostrar.
    # São ~2 MB as duas; não é por elas que o delta engorda.
    CAMINHOS=(dashboard scripts src configs
              results/episodios_3d results/mapa_grande "${FIGS[@]}")
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
