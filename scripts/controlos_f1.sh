#!/usr/bin/env bash
# CONTROLOS DO F1 (zero-shot de topologia) — corre NO SERVIDOR.
#
# A condição natural ("base") já está feita: 420 episódios, 21 células, corrida na
# torre a 27 jul e versionada em results/mapa_grande/f1_zeroshot/. Faltam as três
# condições de CONTROLO do pré-registo, e sem elas um zero do F1 não distingue a
# pergunta da tese das outras três causas possíveis (ver o cabeçalho do
# eval_zeroshot_mapa.py, causas 2/3/4):
#
#   1. --norm-obs treino         : desliga a mudança de ESCALA da observação (÷30
#                                  como no treino, em vez do ÷120 imposto por r=60)
#   2. --controlo sem_obstaculos : desliga os 106 obstáculos que os campeões dos
#                                  labirintos nunca viram
#   3. --controlo sem_porta_obs  : desliga as 4 features da porta, mortas no treino
#                                  de quem não tem porta e vivas no mapa
#
# UMA CONDIÇÃO POR CHAMADA, e cada uma no SEU diretório de trabalho. Medido no
# servidor a 28 jul: 1 episódio = 1m34s num core ⇒ 21 células x 20 ep = ~11 h por
# condição. Em sequência seriam 33 h. As três não podem partilhar diretório —
# convivem no mesmo CSV e o script tem lock por ficheiro destino (_CorridaUnica),
# por isso a segunda abortaria. Com um diretório cada, correm ao mesmo tempo e os
# três CSV juntam-se no fim (as colunas NormObs/Controlo dizem qual é qual).
#
# nice 10 + 1 thread: isto corre AO LADO do megaA/megaB. A avaliação é
# single-process, mas o torch abre uma thread por core se o deixarem, e o custo
# não é aqui — é atrasar duas campanhas de um mês que estão a fechar.
#
# Uso (no servidor), depois de `preparar`:
#     ~/swarm-mapa/scripts/controlos_f1.sh preparar     # cria ~/swarm-mapa-c{1,2,3}
#     tmux new-session -d -s mapaC1 '~/swarm-mapa-c1/scripts/controlos_f1.sh 1'
#     tmux new-session -d -s mapaC2 '~/swarm-mapa-c2/scripts/controlos_f1.sh 2'
#     tmux new-session -d -s mapaC3 '~/swarm-mapa-c3/scripts/controlos_f1.sh 3'
#
# Estado: scripts/servidor.sh (lê ~/mapa_C{1,2,3}_master.log) ou o diário do
# próprio eval em results/evaluation/zeroshot_mapa_grande_progresso.log.
set -uo pipefail

BASE="$HOME/swarm-mapa"
PY="$HOME/run7d_mlp/.venv/bin/python"     # campanha fechada — venv estável, ninguém lá mexe
MODELOS=results/models_7d
EPISODIOS=20

# (etiqueta, argumentos) — a ordem é a do pré-registo, com a escala à cabeça por
# ser a explicação alternativa mais provável dos zeros.
CONDICOES=(
    ""                                            # 0: não usado (índices a partir de 1)
    "escala da observacao|--norm-obs treino"
    "sem obstaculos|--controlo sem_obstaculos"
    "sem features da porta|--controlo sem_porta_obs"
)

# --- preparar: um diretório de trabalho por condição -------------------------
# Cópia inteira (cp -rp) e não symlinks: são 49 MB, e -p é OBRIGATÓRIO porque a
# guarda de campanha do eval lê a DATA de cada campeão — sem preservar mtime,
# todos os modelos passariam a ser de hoje e a guarda deixaria passar qualquer
# coisa (foi assim que se perderam as 6 h do F1 de 25 jul).
if [ "${1:-}" = "preparar" ]; then
    for i in 1 2 3; do
        d="$HOME/swarm-mapa-c$i"
        # "já existe" não basta: existir com o código ERRADO é pior que não
        # existir. A 29 jul as três cópias tinham o simulador de 27 jul, em que
        # as paredes deixavam 45 m de céu aberto e os agentes voavam por cima do
        # labirinto — e este `preparar` tê-las-ia reutilizado sem uma palavra,
        # repetindo o F1 anulado. Compara-se o simulador com o do BASE.
        if [ -d "$d" ] && ! cmp -s "$BASE/src/environment/swarm_env_3d.py" \
                                   "$d/src/environment/swarm_env_3d.py"; then
            echo "[preparar] ⚠️  $d tem um SIMULADOR DIFERENTE do de $BASE."
            echo "[preparar]     Uma campanha com dois simuladores não é comparável."
            echo "[preparar]     Arquiva-o (mv $d ~/ANULADO_\$(date +%d%b)_$(basename "$d"))"
            echo "[preparar]     e volta a correr: esta cópia é recriada do BASE."
            exit 3
        fi
        if [ -d "$d" ]; then
            echo "[preparar] $d já existe, com o mesmo simulador — não toco"
        else
            cp -rp "$BASE" "$d"
            rm -f "$d"/results/evaluation/zeroshot_*.csv \
                  "$d"/results/evaluation/zeroshot_*.lock \
                  "$d"/results/evaluation/zeroshot_*_progresso.log
            echo "[preparar] $d criado ($(du -sh "$d" | cut -f1))"
        fi
    done
    echo "[preparar] datas dos campeões (têm de ser 3-9 jul):"
    ls -l --time-style=+%d-%b "$HOME"/swarm-mapa-c1/results/models_7d/models/*.pth \
        | awk '{print $6}' | sort | uniq -c
    exit 0
fi

N="${1:-}"
case "$N" in
    1|2|3) ;;
    *) echo "uso: $0 {preparar|1|2|3}" >&2; exit 2 ;;
esac

# O diretório é o do próprio script — assim `~/swarm-mapa-c2/scripts/...` corre
# em ~/swarm-mapa-c2 e não há hipótese de duas condições irem ao mesmo CSV.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/mapa_C${N}_master.log"

etiqueta="${CONDICOES[$N]%%|*}"
args="${CONDICOES[$N]#*|}"

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

cd "$RAIZ" || { echo "[mapaC$N] sem $RAIZ"; exit 2; }
[ -x "$PY" ] || { echo "[mapaC$N] sem python em $PY"; exit 2; }

registar() { echo "[mapaC$N] $*" | tee -a "$LOG"; }

agora() { date -u '+%a %b %d %H:%M:%S %Z %Y'; }

registar "ARRANQUE $(agora)"
registar "FASE $N/3: $etiqueta ($args)"
registar "dir: $RAIZ | python: $PY | $EPISODIOS episódios/célula | ETA ~11 h"
inicio=$(date +%s)

# shellcheck disable=SC2086
nice -n 10 "$PY" scripts/eval_zeroshot_mapa.py \
    --episodes "$EPISODIOS" --models-dir "$MODELOS" $args \
    >> "$HOME/mapa_C${N}_eval.log" 2>&1
rc=$?
mins=$(( ($(date +%s) - inicio) / 60 ))

CSV="$RAIZ/results/evaluation/zeroshot_mapa_grande.csv"
if [ $rc -ne 0 ]; then
    registar "FASE $N/3 FALHOU (rc=$rc, ${mins} min) — ver ~/mapa_C${N}_eval.log"
    tail -5 "$HOME/mapa_C${N}_eval.log" | sed "s/^/[mapaC$N]     /" | tee -a "$LOG" >/dev/null
    exit $rc
fi

registar "FASE $N/3 OK (${mins} min)"
if [ -f "$CSV" ]; then
    registar "CSV: $(( $(wc -l < "$CSV") - 1 )) episódios em $(basename "$CSV")"
    "$PY" - "$CSV" "$N" <<'FIM' 2>&1 | tee -a "$LOG"
import sys, pandas as pd
d = pd.read_csv(sys.argv[1])
p = "[mapaC%s]  " % sys.argv[2]
for (n, c), g in d.groupby(["NormObs", "Controlo"]):
    print("%s norm=%-7s controlo=%-15s %4d ep, %2d células, %5.2f recolhas/ep"
          % (p, n, c, len(g), g.groupby(["Algorithm", "Origem"]).ngroups,
             g["food_collected"].mean()))
FIM
fi
registar "CONCLUÍDO $(agora)"
