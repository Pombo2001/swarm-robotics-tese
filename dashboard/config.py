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
# ── MODO LEITURA ─────────────────────────────────────────────────────────────
# Ligado com SWARM_DASH_READONLY=1. Serve a cópia que corre no Raspberry Pi, à
# qual o orientador acede pela internet: ali o dashboard é para VER, e as vistas
# de OPERAÇÃO não podem sequer existir —
#   · Treinar    lança processos na máquina;
#   · Servidor   pede a password SSH do servidor do ISCTE (não a expor num site);
#   · Ao vivo    abre o visualizador Ursina no ecrã de quem CORRE o servidor, o
#                que num Pi remoto não faz sentido nenhum.
# Não é uma questão de arrumação: é a diferença entre publicar resultados e
# publicar um controlo remoto da máquina de treino.
READONLY = os.environ.get("SWARM_DASH_READONLY", "") == "1"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.scenarios import (  # noqa: E402  (precisa do sys.path acima)
    SCENARIOS as _SRC_SCENARIOS,
    THESIS_SCENARIOS as _SRC_THESIS,
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
# ou, pior, calada.
# Vem de `THESIS_SCENARIOS` (src/scenarios.py) e NÃO se escreve aqui: era uma
# cópia à mão da mesma lista, exatamente o que o docstring deste ficheiro diz
# para não fazer. Quando o mapa composto tiver campanha, promove-se num sítio só.
MAIN_SCENARIO_KEYS = list(_SRC_THESIS)

ALGOS = ["GNN", "PPO", "SAC"]

# ── Cores das séries (25 jul 2026) — MEDIDAS, não escolhidas a olho ──────────
# Duas razões para as anteriores (#00C896 / #3D9EFF / #FF6B6B) terem saído:
#
# 1. CONTRADIZIAM AS FIGURAS DA TESE. Lá o PPO é LARANJA e o SAC é AZUL
#    (src/scenarios.py: ALGO_COLORS); aqui o azul era o PPO e o SAC era vermelho.
#    Numa defesa mostram-se as duas coisas seguidas, e a mesma cor a significar
#    algoritmos diferentes em slides e ecrã é pior do que feio.
# 2. NÃO ERAM SEGURAS PARA DALTONISMO: verde-água vs vermelho dava ΔE 6,2 em
#    deuteranopia (~8% dos homens) — as duas séries colapsam numa só.
#
# Estas mantêm as FAMÍLIAS da tese (GNN verde · PPO laranja · SAC azul) e são os
# degraus certos para fundo escuro. Verificadas com o validador de paletas
# (surface #0e0e0e, modo escuro, todos os pares): banda de luminosidade PASSA,
# croma PASSA, separação CVD **9,4** (alvo ≥8) PASSA, visão normal 20,9 PASSA,
# contraste ≥3:1 PASSA. Se mexeres nestes hex, volta a correr o validador —
# o verde "verdadeiro" (#22a34a) parece melhor e FALHA (ΔE 4,4 vs o laranja).
ALGO_META = {
    "GNN": {"color": "#199e70", "icon": "🧬", "label": "GNN (Evolutivo)"},
    "PPO": {"color": "#d95926", "icon": "🤖", "label": "PPO (Actor-Critic)"},
    "SAC": {"color": "#3987e5", "icon": "🔥", "label": "SAC (Soft Actor-Critic)"},
}

# Script de backend que treina + avalia (aceita --runs/--time/--algo/--scenarios/...)
RUN_EXPERIMENTS = os.path.join(BASE_DIR, "scripts", "run_experiments.py")
PLOT_RESULTS    = os.path.join(BASE_DIR, "scripts", "plot_results.py")
CONFIG_PATH     = os.path.join(BASE_DIR, "configs", "foraging.yaml")
