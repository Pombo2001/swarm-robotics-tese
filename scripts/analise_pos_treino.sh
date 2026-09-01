#!/usr/bin/env bash
# analise_pos_treino.sh — Pipeline de análise final (pós-train3d)
# Corre toda a análise que NÃO é gerada automaticamente pelo run_experiments.py
# no fim do treino. O train3d já produz eval_suite (20 ep) + plot_results +
# vídeos; este script ACRESCENTA:
#   1. Re-avaliação determinística com 30 episódios (amostra robusta p/ estatística)
#   2. Testes de significância (food_collected + success) -> CSV + tabela .tex
#   3. Escalabilidade Zero-Shot do GNN (N in {10,20,50,100})
#
# Portável: deteta a venv no Linux (.venv/bin/python) ou Windows/Git Bash
# (.venv/Scripts/python.exe). Idempotente — pode correr-se mais que uma vez.
#
# Uso (no servidor, logo após o train3d, ou no PC depois de trazer results/):
#   bash scripts/analise_pos_treino.sh
#   EP=30 SCALE_SCENARIO=none bash scripts/analise_pos_treino.sh   # configurável
#
# Pré-requisito: results/models/ com os 3 algoritmos treinados (GNN novo do
# train3d; PPO/SAC do treino_fds). Ver docs/AVANCO_GNN_HOMING.md §4.
set -uo pipefail

# localizar a raiz do projeto (este script está em scripts/)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

# localizar o interpretador da venv (Linux ou Windows)
if   [ -x ".venv/bin/python" ];          then PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ];  then PY=".venv/Scripts/python.exe"
elif command -v python >/dev/null 2>&1;  then PY="python"
else echo "[ERRO] Sem interpretador Python (.venv não encontrada)."; exit 1
fi
echo "[*] Python: $PY"
echo "[*] Raiz:   $ROOT"

EP="${EP:-30}"                          # episódios de avaliação (>=30 p/ estatística)
SCALE_SCENARIO="${SCALE_SCENARIO:-none}"  # cenário da escalabilidade zero-shot
LOG="results/logs/analise_pos_treino.log"
mkdir -p results/logs
echo "[*] A registar em $LOG"

run() {  # run "descrição" cmd...
  echo ""; echo "=================================================================="
  echo ">>> $1"; echo "=================================================================="
  shift
  "$@" 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  if [ "$rc" -ne 0 ]; then echo "[!] FALHOU (rc=$rc): $* — continua na mesma" | tee -a "$LOG"; fi
}

date | tee "$LOG"

# 1) Re-avaliação determinística (3 algos × 7 cenários, emparelhada) com mais episódios.
#    O train3d já avaliou com 20 ep; 30 dá amostra mais robusta p/ os testes seguintes.
run "1/4 Avaliação determinística ($EP ep, 7 cenários)" \
    "$PY" scripts/eval_suite.py --episodes "$EP"

# 2) Testes de significância — geram CSV + tabela LaTeX em results/estatisticas/.
run "2/4 Testes de significância — food_collected" \
    "$PY" scripts/statistical_tests.py --metric food_collected
run "3/4 Testes de significância — success" \
    "$PY" scripts/statistical_tests.py --metric success

# 3) Escalabilidade Zero-Shot do GNN (invariante a N; PPO/SAC marcados N/A).
run "4/4 Escalabilidade Zero-Shot (cenário=$SCALE_SCENARIO)" \
    "$PY" scripts/eval_scalability.py --scenario "$SCALE_SCENARIO" --episodes "$EP"

echo ""; echo "=================================================================="
echo "[OK] Análise concluída. Artefactos:"
echo "  results/evaluation/        eval_*.csv + gráficos de tarefa (taxa sucesso, recolhas)"
echo "  results/estatisticas/      testes_significancia_{food_collected,success}.{csv,tex}"
echo "  results/evaluation/ (scale) eval_scalability_*.{csv,png}"
echo "Próximo: executar o plano de reescrita da tese (docs/AVANCO_GNN_HOMING.md §3)."
echo "=================================================================="
