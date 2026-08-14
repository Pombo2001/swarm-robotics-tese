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

# Janela do delta. O `-1 day` de omissão pressupõe que se publica todos os dias,
# e a 14 de agosto o lote estava parado havia NOVE — com essa janela, o script
# anunciava «a enviar» e não levava uma única figura das que mudaram no
# entretanto. Quem publica ao fim de uns dias tem de a alargar:
#
#     DESDE='-10 days' scripts/atualizar_pi.sh
DESDE="${DESDE:--1 day}"

if [ $# -gt 0 ]; then
    CAMINHOS=("$@")
else
    # Por omissão: o código todo (é pequeno) e as figuras tocadas na janela.
    # `find -newermt` evita reenviar 1 GB de campanhas antigas. A data que conta
    # é a dos FICHEIROS, não a das pastas: regenerar figuras por cima das antigas
    # não mexe no mtime da pasta (só criar ou apagar o faz), e por isso o critério
    # antigo via 2 campanhas alteradas onde havia 15 — as outras 13 ficavam no Pi
    # com as figuras da véspera, sem sinal nenhum.
    #
    # Enviam-se os FICHEIROS, não as pastas que os contêm. A versão anterior
    # reduzia cada ficheiro à sua campanha e mandava a campanha inteira: um
    # MANIFESTO.md de 2 KB alterado arrastava os 118 MB da pasta, e os 34 ficheiros
    # tocados na `final_7d` arrastavam 51 MB. O tar recria a árvore na mesma.
    mapfile -t FIGS < <(find results/graficos_tese -mindepth 2 -type f \
                        -newermt "$DESDE" 2>/dev/null | sort -u)
    # Duas pastas de RESULTADOS que não são figuras e o delta não levava:
    #   · episodios_3d — a vista «Episódio 3D» lê-os do disco. Ficaram 13 no Pi
    #     quando cá já havia 21: os oito do PPO e do SAC não chegavam lá.
    #   · mapa_grande  — os CSV do F1 que a vista «Mapa grande» lê. Sem isto, o
    #     Pi mostrava a corrida ANULADA (ou nada), que é pior do que não mostrar.
    # São ~2 MB as duas; não é por elas que o delta engorda.
    # E o que a vista Ciência passou a ler a 3 ago:
    #   · o resumo do mega-treino — é um JSON de 8 KB, mas sem ele o cartão do
    #     28/28 simplesmente não aparece no Pi (a vista devolve None e cala-se);
    #   · Tese/images/resultados — a rota /figuras_tese serve daqui, e a figura
    #     dos quatro braços é servida por essa rota, não pela pasta da campanha.
    #     Sem isto o cartão aparece com a imagem partida.
    # E três caminhos que as vistas leem para produzir NÚMEROS, e que o delta
    # não levava — todos pequenos, somam ~3 MB:
    #   · estado_f2.json — o instantâneo datado do servidor. É o ficheiro que a
    #     vista «Mapa grande» e a «Defesa» passaram a ler justamente para não
    #     afirmarem o estado da campanha em prosa fixa. Sem ele no delta, o Pi
    #     mostra o estado do dia da última publicação completa — que é o defeito
    #     que essas vistas existem para não ter;
    #   · estatisticas — os testes de significância e a escalabilidade, que a
    #     Ciência e a Defesa leem;
    #   · evaluation — os `*_fail10.csv` da robustez.
    # E, desde 14 ago, a dissertação inteira em `Tese/`:
    #   · main.tex  — a Galeria marca as figuras que a tese usa DE FACTO, e
    #     descobre-as lendo os `\includegraphics` do `.tex`. Sem ele no Pi, a
    #     função devolve `{}` e a galeria fica sem um único selo — sem erro
    #     nenhum, que é a maneira mais cara de falhar;
    #   · images/   — a comparação é por CONTEÚDO (md5 do ficheiro), não por
    #     nome, e por isso precisa das imagens todas e não só das de
    #     `resultados/`. Vão inteiras (14 MB): ao contrário das figuras das
    #     campanhas, estas não passam pela janela do `-newermt`, porque uma
    #     imagem que falte não dá erro — tira um selo em silêncio.
    CAMINHOS=(dashboard scripts src configs
              results/episodios_3d results/mapa_grande
              results/mega_1mes/resumo_megatreino.json
              results/estado_f2.json results/estatisticas results/evaluation
              Tese/main.tex Tese/images "${FIGS[@]}")
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
