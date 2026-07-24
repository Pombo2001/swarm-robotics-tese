"""Constantes e caminhos partilhados do dashboard.

Extraído do antigo launcher_dashboard.py. Os scripts em scripts/ continuam a ser
o backend real — este módulo só descreve cenários, algoritmos e caminhos para o
dashboard os orquestrar.

⚠️ A lista de cenários NÃO se declara aqui: vem de `src/scenarios.py`, que é a
fonte única do projeto. Havia aqui uma cópia própria, e já divergia nos rótulos
("Beco Sem Saída (Muro U)" aqui vs "Beco Sem Saída (U)" em src). O docstring do
`src/scenarios.py` conta o preço dessa duplicação: a lista esteve espalhada por
~8 ficheiros e o 7.º cenário chegou a ser treinado mas NUNCA avaliado. Com um
8.º mapa a caminho, manter cópia era repetir o erro de propósito.
"""
import os
import sys

# Raiz do projeto (dois níveis acima deste ficheiro: dashboard/ -> projeto/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.scenarios import (  # noqa: E402  (precisa do sys.path acima)
    SCENARIOS as _SRC_SCENARIOS,
    SCENARIO_LABELS as _SRC_LABELS,
    SCENARIO_LABELS_SHORT as _SRC_LABELS_SHORT,
)

# Todos os cenários que o simulador conhece, na ordem canónica de src/scenarios.py.
SCENARIO_KEYS = list(_SRC_SCENARIOS)

# (label legível, chave interna) — a forma que as vistas já consumiam.
SCENARIOS = [(_SRC_LABELS.get(k, k), k) for k in SCENARIO_KEYS]
SCENARIO_LABEL_BY_KEY = {k: lbl for lbl, k in SCENARIOS}

# Labels curtos. Partem dos de src/scenarios.py; o dashboard encurta alguns por
# caber em tabelas/gráficos estreitos (só isso — as chaves são as mesmas).
SCENARIO_LABEL_SHORT = dict(_SRC_LABELS_SHORT)
SCENARIO_LABEL_SHORT.update({
    "u_wall": "Muro em U",
    "four_rooms": "4 Salas",
    "cooperative_door": "Porta coop.",
    "cooperative_perception": "Perceção coop.",
    "cooperative_door_bypass": "Porta c/ alt.",
})

# Conjunto canónico de experiências DA TESE — os 7 cenários das campanhas
# fechadas. Deliberadamente NÃO é `SCENARIO_KEYS`: um cenário novo (ex.: o mapa
# grande) aparece nas vistas de operação, mas não deve entrar nas tabelas de
# resultados enquanto não tiver campanha avaliada — apareceria como linha vazia
# ou, pior, calada. Acrescentar aqui só quando os dados existirem.
MAIN_SCENARIO_KEYS = [
    "none", "u_wall", "bottleneck", "four_rooms",
    "cooperative_door", "cooperative_perception", "cooperative_door_bypass",
]

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
