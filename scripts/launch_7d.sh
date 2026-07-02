#!/bin/bash
# launch_7d.sh — watchdog do treino longo (7 dias) no servidor ISCTE
# ===================================================================
# Corre o run_experiments com auto-RESUME: se o processo morrer (OOM, exceção,
# etc.), relança automaticamente com --resume — os treinos já concluídos são
# saltados via _sessao_treino.txt, e as curvas/scores já estão no disco
# (gravação incremental). Sem isto, um crash ao dia 3 matava a semana inteira.
#
# Uso (dentro de um tmux, na raiz do projeto):
#   bash scripts/launch_7d.sh --algo GNN --runs 7 --time-gnn 195 --eval-episodes 20
#   (os argumentos são passados tal-e-qual ao run_experiments.py)
#
# Campanha NOVA: apaga o progresso da sessão anterior antes de arrancar.
# Se quiseres RETOMAR uma campanha interrompida manualmente, corre com
# SWARM_KEEP_SESSION=1 para não apagar o _sessao_treino.txt.

set -o pipefail
cd "$(dirname "$0")/.."

source .venv/bin/activate
ulimit -n 65536

LOG="treino_7d_$(date +%Y%m%d_%H%M).log"

if [ "${SWARM_KEEP_SESSION:-0}" != "1" ]; then
    rm -f results/logs/_sessao_treino.txt
    echo "[WATCHDOG] Campanha nova (progresso anterior limpo)." | tee -a "$LOG"
fi

# O sinal de conclusão é a SENTINELA escrita pelo run_experiments no fim,
# não o exit code: libs nativas (VTK headless) podem abortar o processo
# depois de todo o trabalho feito, e o exit ≠ 0 relançava uma campanha
# já completa em loop (visto no smoke de 2 jul).
DONE=results/logs/_campanha_concluida.txt

MAX_TRIES=10
try=0
while true; do
    python scripts/run_experiments.py "$@" --resume 2>&1 | tee -a "$LOG"
    if [ -f "$DONE" ]; then
        echo "[WATCHDOG] Campanha CONCLUÍDA com sucesso (sentinela presente)." | tee -a "$LOG"
        break
    fi
    try=$((try+1))
    echo "[WATCHDOG] run_experiments morreu sem concluir (tentativa $try/$MAX_TRIES)." | tee -a "$LOG"
    if [ "$try" -ge "$MAX_TRIES" ]; then
        echo "[WATCHDOG] Limite de tentativas atingido — a desistir." | tee -a "$LOG"
        exit 1
    fi
    sleep 120
    echo "[WATCHDOG] A relançar com --resume..." | tee -a "$LOG"
done
