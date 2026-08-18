# -*- coding: utf-8 -*-
"""As tabelas da tese ficam com os SETE cenários, mesmo com dados do oitavo.

O compromisso 3 do pré-registo do mapa grande: «o mapa NÃO entra nas tabelas dos
7 cenários (`tab:res_eval`, `tab:res_signif`) — os 7 têm campanhas com orçamento
e protocolo próprios, e misturá-los seria comparar coisas diferentes na mesma
linha. Por isso `THESIS_SCENARIOS` está separado de `SCENARIOS` no código.»

Só que o `gerar_figuras_7d.py`, que é quem produz essas tabelas, filtrava por
`SCENARIOS` (os oito). A única coisa que mantinha o mapa grande de fora era não
haver dados dele — e a partir de ~16 ago passa a haver.
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.scenarios import SCENARIOS, THESIS_SCENARIOS  # noqa: E402


def test_as_duas_listas_diferem_pelo_mapa_grande():
    assert set(SCENARIOS) - set(THESIS_SCENARIOS) == {"mapa_grande"}
    assert len(THESIS_SCENARIOS) == 7


def test_o_filtro_das_tabelas_exclui_o_oitavo_cenario():
    """Reproduz a linha do `gerar_figuras_7d.py` com dados dos OITO cenários."""
    ev = pd.DataFrame({"Scenario": SCENARIOS,
                       "Algorithm": ["GNN"] * len(SCENARIOS),
                       "Run": 1, "food_collected": 1.0, "success": True})
    scen_present = [s for s in THESIS_SCENARIOS if s in set(ev["Scenario"])]
    assert "mapa_grande" not in scen_present
    assert len(scen_present) == 7


def test_o_ficheiro_usa_mesmo_thesis_scenarios():
    """Guarda contra uma regressão silenciosa: se alguém voltar a pôr
    `SCENARIOS` no filtro, isto acusa antes de a tabela sair errada."""
    fonte = open(os.path.join(RAIZ, "scripts", "gerar_figuras_7d.py"),
                 encoding="utf-8").read()
    linha = next(l for l in fonte.splitlines() if "scen_present = " in l)
    assert "THESIS_SCENARIOS" in linha, \
        f"o filtro das tabelas voltou a incluir o 8.º cenário: {linha.strip()}"


def test_a_limitacao_vertical_ignora_os_episodios_do_oitavo_cenario():
    """A frase da tese diz «$21$ células (três controladores × sete cenários)».

    A pasta `results/episodios_3d/` passou a ter 24 ficheiros quando o mapa
    grande foi exportado, e o `verificar_vertical.py` lia-os todos: a contagem
    dos cenários onde quem voa mais alto recolhe menos subia de 5 (o que a tese
    escreve) para 6, e o verificador acusava a tese de errar um número certo.
    O mesmo padrão do filtro das tabelas, noutro sítio.
    """
    fonte = open(os.path.join(RAIZ, "scripts", "verificar_vertical.py"),
                 encoding="utf-8").read()
    assert "THESIS_SCENARIOS" in fonte, \
        "o verificador da dimensão vertical voltou a aceitar o 8.º cenário"

    eps = os.path.join(RAIZ, "results", "episodios_3d")
    if not os.path.isdir(eps):
        return
    dos_sete = [f for f in os.listdir(eps) if f.endswith(".json")
                and f[:-5].split("_", 1)[1] in THESIS_SCENARIOS]
    assert len(dos_sete) == 21, \
        f"esperava 21 episódios dos sete cenários, encontrei {len(dos_sete)}"
