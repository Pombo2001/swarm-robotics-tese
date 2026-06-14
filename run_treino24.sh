#!/usr/bin/env bash
cd ~/swarm-robotics-tese
source .venv/bin/activate
ulimit -n 65536
python scripts/run_experiments.py --runs 1 --time 60 --time-ppo 85 --time-gnn 85 --eval-episodes 20 2>&1 | tee treino_24h.log
