#!/usr/bin/env bash
# Fase B — primeiros 3 runs (variância estatística para os boxplots).
# Config: 6 cenários × 3 algos × 3 runs, ~45h na .14 (cabe nas 48h).
# Tempos por cenário: SAC 40m, PPO 55m, GNN 55m (próximos do 24h v2 que convergiu).
#
# ARRANQUE LIMPO (começa do zero, apaga o estado de sessão anterior):
#   tmux new -s treino48
#   bash scripts/run_treino48.sh
#   (Ctrl+B, D para sair sem matar)
#
# RETOMA APÓS CRASH (mesma sessão, salta o que já ficou feito):
#   acrescentar --resume ao comando abaixo e relançar.
cd ~/swarm-robotics-tese
source .venv/bin/activate
ulimit -n 65536
python scripts/run_experiments.py \
    --runs 3 \
    --time 40 --time-ppo 55 --time-gnn 55 \
    --eval-episodes 20 \
    2>&1 | tee treino_fase_b.log
