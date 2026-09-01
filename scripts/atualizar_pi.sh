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

# Janela do delta. O `-1 day` de omissão pressupõe publicação diária; quem
# publica ao fim de uns dias tem de a alargar, senão o script anuncia «a enviar»
# e não leva as figuras que mudaram no entretanto:
#
#     DESDE='-10 days' scripts/atualizar_pi.sh
DESDE="${DESDE:--1 day}"

# Miniaturas da Galeria, ANTES de montar o pacote — senão as geradas agora ficam
# de fora da janela do `find` e o Pi continua a servir os PNG de impressão. É
# idempotente. Se falhar, o envio continua: a Galeria recua para o original
# quando não encontra a miniatura, o que é lento mas correto.
echo "[pi] miniaturas da Galeria:"
python scripts/gerar_miniaturas.py 2>&1 | sed 's/^/     /' \
    || echo "     AVISO: falharam — o Pi vai servir os PNG grandes"

if [ $# -gt 0 ]; then
    CAMINHOS=("$@")
else
    # Por omissão: o código todo (é pequeno) e as figuras tocadas na janela.
    # `find -newermt` evita reenviar 1 GB de campanhas antigas.
    #
    # A data que conta é a dos FICHEIROS, não a das pastas: regenerar figuras por
    # cima das antigas não mexe no mtime da pasta (só criar ou apagar o faz).
    # E enviam-se os FICHEIROS, não as pastas que os contêm — reduzir cada
    # ficheiro à sua campanha fazia um MANIFESTO.md de 2 KB arrastar 118 MB. O
    # tar recria a árvore na mesma.
    mapfile -t FIGS < <(find results/graficos_tese -mindepth 2 -type f \
                        -newermt "$DESDE" 2>/dev/null | sort -u)
    # Além das figuras, o delta leva os caminhos pequenos de que as vistas
    # precisam para produzir NÚMEROS: episódios 3D, CSV do mapa grande, resumo do
    # mega-treino, estado_f2.json, estatísticas, avaliações, curvas dos métodos
    # de gradiente e a dissertação em `Tese/` (a Galeria descobre as figuras que a
    # tese usa lendo os `\includegraphics` do `.tex`, e a Prontidão compara as
    # datas do `main.pdf` e do `main.log`).
    #
    # Todos partilham o mesmo modo de falha: sem eles a vista não rebenta, cala-se
    # — devolve `None` ou uma lista vazia e mostra menos do que existe. A lista é
    # verificada pelo `scripts/verificar_paridade_pi.py`, que corre as vistas com
    # as leituras de ficheiro instrumentadas e as compara com estes caminhos.
    #
    # `Tese/images/` vai inteira (14 MB) porque a comparação da Galeria é por
    # CONTEÚDO (md5) e não por nome. O `main.pdf` (12 MB) é o único caminho pesado:
    # quem quiser um delta leve passa os caminhos à mão.
    CAMINHOS=(dashboard scripts src configs
              results/episodios_3d results/mapa_grande
              results/mega_1mes/resumo_megatreino.json
              results/estado_f2.json results/estatisticas results/evaluation
              results/mega_1mes/*/evaluation
              results/novelty_adaptativo/*/evaluation
              results/logs_ppo results/logs_sac
              Tese/main.tex Tese/main.pdf Tese/main.log
              Tese/images "${FIGS[@]}")
fi

echo "[pi] a enviar:"
printf '     %s\n' "${CAMINHOS[@]}"

TAR=$(mktemp -t delta_pi_XXXX.tar.gz)
# O exclude dos logs é ANCORADO a `results/`: com `--exclude='*.log'` o
# `Tese/main.log` — de onde a vista Prontidão tira as páginas, os overfulls e as
# referências indefinidas — saía do pacote em silêncio. O que se quer excluir são
# os logs de treino em bruto, que vivem todos sob `results/`.
tar czf "$TAR" --exclude=__pycache__ --exclude='*.pyc' \
    --exclude='results/*.log' --exclude='results/*/*.log' \
    --exclude='results/*/*/*.log' "${CAMINHOS[@]}"
echo "[pi] pacote: $(du -h "$TAR" | cut -f1)"

scp -o BatchMode=yes "$TAR" "$PI:~/delta_pi.tar.gz"
ssh -o BatchMode=yes "$PI" "cd $DIR_PI && tar xzf ~/delta_pi.tar.gz && rm -f ~/delta_pi.tar.gz \
    && sudo systemctl restart swarm-dash && sleep 8 \
    && systemctl is-active swarm-dash \
    && curl -sf -o /dev/null http://127.0.0.1:8090/ && echo '[pi] no ar'"
rm -f "$TAR"
echo "[pi] http://192.168.68.54:8090/"
