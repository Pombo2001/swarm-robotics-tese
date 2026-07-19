#!/bin/bash
# MEGA-TREINO 1 mês — STREAM A (~/swarm-robotics-tese): u_wall a n=28 + Sandbox.
# Pré-registo: docs/PRE_REGISTO_MEGATREINO.md. Padrão week_*: config por sed em cada
# fase, retry com --resume, arquivo por fase, config reposto no fim.
set -u
cd ~/swarm-robotics-tese
source .venv/bin/activate
ulimit -n 65536

CFG=configs/foraging.yaml
LOGDIR=results/logs

config() {  # config <weight> <adaptive>  (limpa chaves de ablação; normaliza)
  sed -i '/novelty_decay:/d; /novelty_sustain_gens:/d' "$CFG"
  sed -i "s/novelty_weight: .*/novelty_weight: $1/; s/novelty_adaptive: .*/novelty_adaptive: $2/" "$CFG"
  grep -n 'novelty' "$CFG"
}

correr() {  # correr <log> <args...>  — fase nova + até 3 retries com --resume
  local log=$1; shift
  rm -f "$LOGDIR/_campanha_concluida.txt" "$LOGDIR/_sessao_treino.txt"
  python scripts/run_experiments.py "$@" 2>&1 | tee -a "$log"
  for t in 1 2; do
    [ -f "$LOGDIR/_campanha_concluida.txt" ] && return 0
    echo "[megaA][retry $t] sem sentinela — relançar com --resume ($(date))" | tee -a "$log"
    sleep 60
    python scripts/run_experiments.py "$@" --resume 2>&1 | tee -a "$log"
  done
}

arquivar() {  # arquivar <pasta> <log>
  mkdir -p ~/"$1"
  cp -r results/evaluation results/models results/logs "$2" ~/"$1"/ 2>/dev/null
}

echo "[megaA] FASE 1: GNN ADAPTATIVO u_wall @195x28 ($(date))"
config 0.5 true
correr mega_A_fase1.log --algo GNN --runs 28 --time-gnn 195 --scenarios u_wall --eval-episodes 20
arquivar mega_A_fase1 mega_A_fase1.log

echo "[megaA] FASE 2: GNN OBJETIVO u_wall @195x28 ($(date))"
config 0.0 false
correr mega_A_fase2.log --algo GNN --runs 28 --time-gnn 195 --scenarios u_wall --eval-episodes 20
arquivar mega_A_fase2 mega_A_fase2.log

echo "[megaA] FASE 3: PPO u_wall @48x28 ($(date))"
correr mega_A_fase3.log --algo PPO --runs 28 --time-ppo 48 --scenarios u_wall --eval-episodes 20
arquivar mega_A_fase3 mega_A_fase3.log

echo "[megaA] FASE 4: SAC u_wall @48x28 ($(date))"
correr mega_A_fase4.log --algo SAC --runs 28 --time 48 --scenarios u_wall --eval-episodes 20
arquivar mega_A_fase4 mega_A_fase4.log

echo "[megaA] FASE 5: GNN ADAPTATIVO Sandbox (none) @195x21 ($(date))"
config 0.5 true
correr mega_A_fase5.log --algo GNN --runs 21 --time-gnn 195 --scenarios none --eval-episodes 20
arquivar mega_A_fase5 mega_A_fase5.log

config 0.0 false
echo "[megaA] CONCLUÍDO — config reposto a 0.0/false ($(date))"
