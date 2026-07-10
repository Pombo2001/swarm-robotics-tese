"""Constantes e caminhos partilhados do dashboard (fonte única de verdade).

Extraído do antigo launcher_dashboard.py. Os scripts em scripts/ continuam a ser
o backend real — este módulo só descreve cenários, algoritmos e caminhos para o
dashboard os orquestrar.
"""
import os

# Raiz do projeto (dois níveis acima deste ficheiro: dashboard/ -> projeto/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label legível, chave interna) — inclui o 7º cenário (cooperative_door_bypass)
SCENARIOS = [
    ("Nenhum (Sandbox)",                 "none"),
    ("Beco Sem Saída (Muro U)",          "u_wall"),
    ("Gargalo (Porta Estreita)",         "bottleneck"),
    ("Quatro Salas (Labirinto)",         "four_rooms"),
    ("Porta Cooperativa (3 Robôs)",      "cooperative_door"),
    ("Perceção Cooperativa (Alvo Móvel)", "cooperative_perception"),
    ("Porta Coop. c/ Alternativa",       "cooperative_door_bypass"),
]
SCENARIO_LABEL_BY_KEY = {k: lbl for lbl, k in SCENARIOS}
SCENARIO_KEYS = [k for _, k in SCENARIOS]

# Labels curtos (para tabelas/gráficos onde o nome completo não cabe) — fonte
# única partilhada pelas vistas (evita SCEN_LABEL duplicados por ficheiro).
SCENARIO_LABEL_SHORT = {
    "none": "Sandbox",
    "u_wall": "Muro em U",
    "bottleneck": "Gargalo",
    "four_rooms": "4 Salas",
    "cooperative_door": "Porta coop.",
    "cooperative_perception": "Perceção coop.",
    "cooperative_door_bypass": "Porta c/ alt.",
}
# Conjunto canónico de experiências da tese — os 7 cenários. O bypass deixou de ser
# exploratório na campanha final (é o cenário deceptive, treinado e avaliado nos 7 runs).
MAIN_SCENARIO_KEYS = list(SCENARIO_KEYS)

ALGOS = ["GNN", "PPO", "SAC"]
ALGO_META = {
    "GNN": {"color": "#00C896", "icon": "🧬", "label": "GNN (Evolutivo)"},
    "PPO": {"color": "#3D9EFF", "icon": "🤖", "label": "PPO (Actor-Critic)"},
    "SAC": {"color": "#FF6B6B", "icon": "🔥", "label": "SAC (Soft Actor-Critic)"},
}

# Script de backend que treina + avalia (aceita --runs/--time/--algo/--scenarios/...)
RUN_EXPERIMENTS = os.path.join(BASE_DIR, "scripts", "run_experiments.py")
PLOT_RESULTS    = os.path.join(BASE_DIR, "scripts", "plot_results.py")
CONFIG_PATH     = os.path.join(BASE_DIR, "configs", "foraging.yaml")
