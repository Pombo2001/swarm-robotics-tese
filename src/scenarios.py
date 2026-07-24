"""
src/scenarios.py — Fonte única dos cenários e rótulos do projeto
================================================================
Centraliza a lista canónica de cenários, os rótulos (longo/curto), os metadados
dos algoritmos e a convenção de sufixo dos modelos.

Antes, isto estava duplicado e DIVERGENTE em ~8 ficheiros (uns com 6 cenários,
outros com 7), o que fazia o 7º cenário (cooperative_door_bypass) ser treinado
mas NUNCA avaliado nem aparecer em heatmaps/robustez. Importar SEMPRE daqui.
"""

# Ordem canónica (treino + avaliação). Inclui TODOS os cenários ativos.
SCENARIOS = [
    "none", "u_wall", "bottleneck", "four_rooms",
    "cooperative_door", "cooperative_perception", "cooperative_door_bypass",
    "mapa_grande",
]

# Os 7 cenários das campanhas fechadas da tese. Deliberadamente separado de
# SCENARIOS: o mapa_grande é o 8.º e ainda NÃO tem campanha avaliada, por isso
# não deve entrar em tabelas de resultados nem em baterias de avaliação até ter
# dados — apareceria como célula vazia (ou, pior, calada).
THESIS_SCENARIOS = [
    "none", "u_wall", "bottleneck", "four_rooms",
    "cooperative_door", "cooperative_perception", "cooperative_door_bypass",
]

# Cenários com paredes / campo geodésico (usados p.ex. no heatmap geodésico).
MAZE_SCENARIOS = [
    "u_wall", "bottleneck", "four_rooms", "cooperative_door", "cooperative_door_bypass",
    "mapa_grande",
]

# Rótulos descritivos — para títulos de figuras e tabelas.
SCENARIO_LABELS = {
    "none": "Sandbox (Arena Aberta)",
    "u_wall": "Beco Sem Saída (Muro U)",
    "bottleneck": "Gargalo (Porta Estreita)",
    "four_rooms": "Quatro Salas (Labirinto)",
    "cooperative_door": "Porta Cooperativa (3 Robôs)",
    "cooperative_perception": "Perceção Cooperativa (Alvo Móvel)",
    "cooperative_door_bypass": "Porta Cooperativa c/ Alternativa",
    "mapa_grande": "Mapa Grande (Labirinto Composto)",
}

# Rótulos curtos — para eixos/legendas apertadas.
SCENARIO_LABELS_SHORT = {
    "none": "Sandbox",
    "u_wall": "Beco Sem Saída (U)",
    "bottleneck": "Gargalo",
    "four_rooms": "Quatro Salas",
    "cooperative_door": "Porta Cooperativa",
    "cooperative_perception": "Perceção Cooperativa",
    "cooperative_door_bypass": "Porta Coop. c/ Alternativa",
    "mapa_grande": "Mapa Grande",
}

ALGO_LABELS = {"gnn": "GNN (Evolutivo)", "ppo": "PPO", "sac": "SAC"}
ALGO_COLORS = {"GNN": "#2E7D32", "PPO": "#E65100", "SAC": "#0277BD"}


def scenario_suffix(scenario):
    """Sufixo do ficheiro de modelo: '' para o Sandbox ('none'); '_<cenario>' caso contrário."""
    return f"_{scenario}" if scenario and scenario != "none" else ""


def label(scenario, short=False):
    """Rótulo legível de um cenário (curto/longo); devolve a própria chave se desconhecido."""
    d = SCENARIO_LABELS_SHORT if short else SCENARIO_LABELS
    return d.get(scenario, scenario)
