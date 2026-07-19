#!/bin/bash
# MEGA-TREINO 1 mês — STREAM B (~/swarm-novelty): ablação do anneal + reforços.
# Pré-registo: docs/PRE_REGISTO_MEGATREINO.md. Ablações só por config (as chaves
# novelty_sustain_gens/novelty_decay têm defaults 10/0.98 no evo_trainer_3d.py).
set -u
cd ~/swarm-novelty
source .venv/bin/activate
ulimit -n 65536

CFG=configs/foraging.yaml
LOGDIR=results/logs

config() {  # config <weight> <adaptive> [chave extra p.ex. 'novelty_decay: 0.95']
  sed -i '/novelty_decay:/d; /novelty_sustain_gens:/d' "$CFG"
  sed -i "s/novelty_weight: .*/novelty_weight: $1/; s/novelty_adaptive: .*/novelty_adaptive: $2/" "$CFG"
  if [ $# -ge 3 ]; then sed -i "/novelty_weight:/a\\  $3" "$CFG"; fi
  grep -n 'novelty' "$CFG"
}

correr() {  # correr <log> <args...>  — fase nova + até 2 retries com --resume
  local log=$1; shift
  rm -f "$LOGDIR/_campanha_concluida.txt" "$LOGDIR/_sessao_treino.txt"
  python scripts/run_experiments.py "$@" 2>&1 | tee -a "$log"
  for t in 1 2; do
    [ -f "$LOGDIR/_campanha_concluida.txt" ] && return 0
    echo "[megaB][retry $t] sem sentinela — relançar com --resume ($(date))" | tee -a "$log"
    sleep 60
    python scripts/run_experiments.py "$@" --resume 2>&1 | tee -a "$log"
  done
}

arquivar() {
  mkdir -p ~/"$1"
  cp -r results/evaluation results/models results/logs "$2" ~/"$1"/ 2>/dev/null
}

ABL='--algo GNN --runs 7 --time-gnn 195 --scenarios u_wall,cooperative_door_bypass --eval-episodes 20'

echo "[megaB] FASE 1: ablação sustain=5 ($(date))"
config 0.5 true 'novelty_sustain_gens: 5'
correr mega_B_fase1.log $ABL
arquivar mega_B_fase1 mega_B_fase1.log

echo "[megaB] FASE 2: ablação sustain=20 ($(date))"
config 0.5 true 'novelty_sustain_gens: 20'
correr mega_B_fase2.log $ABL
arquivar mega_B_fase2 mega_B_fase2.log

echo "[megaB] FASE 3: ablação decay=0.95 ($(date))"
config 0.5 true 'novelty_decay: 0.95'
correr mega_B_fase3.log $ABL
arquivar mega_B_fase3 mega_B_fase3.log

echo "[megaB] FASE 4: ablação decay=0.995 ($(date))"
config 0.5 true 'novelty_decay: 0.995'
correr mega_B_fase4.log $ABL
arquivar mega_B_fase4 mega_B_fase4.log

echo "[megaB] FASE 5: adaptativo DEFAULT bypass @195x21 (reforço T4) ($(date))"
config 0.5 true
correr mega_B_fase5.log --algo GNN --runs 21 --time-gnn 195 --scenarios cooperative_door_bypass --eval-episodes 20
arquivar mega_B_fase5 mega_B_fase5.log

echo "[megaB] FASE 6: SAC bottleneck @48x21 ($(date))"
config 0.0 false
correr mega_B_fase6.log --algo SAC --runs 21 --time 48 --scenarios bottleneck --eval-episodes 20
arquivar mega_B_fase6 mega_B_fase6.log

echo "[megaB] FASE 7: GNN ADAPTATIVO perception @195x21 ($(date))"
config 0.5 true
correr mega_B_fase7.log --algo GNN --runs 21 --time-gnn 195 --scenarios cooperative_perception --eval-episodes 20
arquivar mega_B_fase7 mega_B_fase7.log

config 0.0 false
echo "[megaB] CONCLUÍDO — config reposto a 0.0/false ($(date))"
