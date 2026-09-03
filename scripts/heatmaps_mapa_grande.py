# -*- coding: utf-8 -*-
"""Regenera os três heatmaps de ocupação do mapa composto (F2), com o raio certo.

Os heatmaps arquivados em `results/graficos_tese/mapa_grande_f2/` foram gerados
com o histograma limitado a ±15 m — o raio dos sete cenários, lido antes do
reset que muda o mapa composto para 60 m — e mostravam um quadrado de 30 m no
meio de um labirinto de 103 (ver `heatmaps.run_occupancy`). Este script chama
a mesma função, já corrigida, com os modelos do F2 de cada algoritmo, e grava
nas pastas que o dashboard lê: a agregada e a do stream de origem.

Uso: .venv/Scripts/python.exe scripts/heatmaps_mapa_grande.py [--algo gnn|ppo|sac] [--episodes 6]
"""
import argparse
import os
import shutil
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from scripts.heatmaps import run_occupancy  # noqa: E402

CONFIG = os.path.join(RAIZ, "configs", "foraging.yaml")
GT = os.path.join(RAIZ, "results", "graficos_tese")
# (algo, pasta com models*/, pasta datada do stream de onde o F2 copiou o heatmap)
FONTES = {
    "gnn": (os.path.join(GT, "16-08-2026_16h14m", "modelos"), "16-08-2026_16h14m"),
    "ppo": (os.path.join(RAIZ, "results", "models_f2_ppo"), "07-08-2026_05h27m"),
    "sac": (os.path.join(RAIZ, "results", "models_f2_sac"), "10-08-2026_16h34m"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=list(FONTES), nargs="*", default=list(FONTES))
    ap.add_argument("--episodes", type=int, default=6)
    a = ap.parse_args()
    destino = os.path.join(GT, "mapa_grande_f2")
    for algo in a.algo:
        raiz, stream = FONTES[algo]
        out = run_occupancy(algo, "mapa_grande", a.episodes, 120, CONFIG,
                            out_dir=destino, models_root=raiz)
        if out and os.path.isdir(os.path.join(GT, stream)):
            shutil.copy2(out, os.path.join(GT, stream, os.path.basename(out)))
            print("[v] copiado para %s" % stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
