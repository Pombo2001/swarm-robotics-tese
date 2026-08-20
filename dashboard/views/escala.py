"""Vista «Escalabilidade» — a QI2 demonstrada, em vez de explicada.

O contributo distintivo da tese é este: a política de grafo com atenção transfere
de N=20 para N∈{10,50,100} **sem retreino**, e as MLP de entrada fixa do PPO/SAC
nem sequer carregam. Na dissertação isso são dois parágrafos e uma tabela; aqui
mexe-se no N e vê-se acontecer — incluindo o que é o ponto principal, que é o
PPO e o SAC ficarem **indisponíveis** fora do N de treino.

A incompatibilidade não é uma opinião desta vista: vem da coluna `compatible` dos
`results/estatisticas/escalabilidade_*.csv`, escrita pelo `eval_scalability.py`
quando tenta carregar o modelo e a dimensão da observação não bate certo.

Duas leituras que a tese faz e que o gráfico tem de deixar ver:
  · a **taxa de sucesso** mantém-se a 100% em todas as células do GNN — escalar
    não parte a tarefa;
  · a **eficiência per capita** cai, e cai mais nos cenários abertos (Sandbox,
    Perceção) do que nos estruturados (Portas Cooperativas) — o que a tese
    atribui à partilha de um recurso finito, não a falha de coordenação.
"""
import os

import pandas as pd
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title   # veio com o bloco da robustez, da Ciência
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIR_EST = os.path.join(_RAIZ, "results", "estatisticas")

ALGOS = ("GNN", "PPO", "SAC")
DIMENSOES = (10, 20, 50, 100)
N_TREINO = 20

# Os nomes dos cenários vêm do dashboard/config.py — que é onde vivem os nomes
# da dissertação. Havia aqui uma cópia própria, e dizia «Muro U» e «Perceção
# Coop.» onde o texto diz «Muro em U» e «Perceção Cooperativa».
ROTULOS = {k: config.SCENARIO_LABEL_SHORT[k] for k in config.MAIN_SCENARIO_KEYS}


def _dados():
    """{cenário: DataFrame} — um por ficheiro de escalabilidade."""
    saida = {}
    if not os.path.isdir(DIR_EST):
        return saida
    for f in sorted(os.listdir(DIR_EST)):
        if f.startswith("escalabilidade_") and f.endswith(".csv"):
            cen = f[len("escalabilidade_"):-len(".csv")]
            try:
                saida[cen] = pd.read_csv(os.path.join(DIR_EST, f))
            except Exception:  # noqa: BLE001
                pass
    return saida


def _cor(algo):
    return config.ALGO_META.get(algo, {}).get("color", "#7d7d7d")


def _echart_axis_label():
    """Rótulo de eixo com as cores do tema (era o azul 'slate' do tema antigo)."""
    return {"color": theme.INK_MUTED, "fontSize": 12, "fontFamily": "Inter"}


def _robustez_option(table: dict) -> dict:
    """Barras de retenção (%) por cenário, uma série por algoritmo.

    Retenção = recolhas com 10% de falhas / recolhas sem falhas. 100% = imune.
    """
    scen_keys = [k for k in config.SCENARIO_KEYS if k in table]
    labels = [config.SCENARIO_LABEL_SHORT[k] for k in scen_keys]
    series = []
    for a in config.ALGOS:
        pts = []
        for k in scen_keys:
            info = table[k].get(a)
            pts.append(round(info["retencao"], 1)
                       if info and info["retencao"] is not None else None)
        s = {"name": a, "type": "bar", "barMaxWidth": 26,
             "itemStyle": {"color": config.ALGO_META[a]["color"],
                           "borderRadius": [4, 4, 0, 0]},
             "data": pts}
        series.append(s)
    if series:
        series[0]["markLine"] = {
            "silent": True, "symbol": "none",
            "lineStyle": {"color": theme.AXIS_LINE, "type": "dashed"},
            # `insideStartTop`: por omissão o ECharts escreve a etiqueta no FIM
            # da linha, encostada à margem direita da grelha — e ela saía do
            # gráfico, cortada a meio do «100» («10(»). No início, cabe.
            "data": [{"yAxis": 100,
                      "label": {"formatter": "100% · imune",
                                "position": "insideStartTop",
                                "color": theme.INK_MUTED, "fontSize": 12}}]}
    base = theme.echart_chrome(y_nome="Retenção (%)", rotacao_x=18)
    base["xAxis"]["data"] = labels

    # Eixo limitado, com os fora-de-escala rotulados no topo da barra.
    #
    # A retenção é um RÁCIO, por isso um cenário cuja base é quase zero produz
    # valores absurdos (um caso mediu ~570%: com falhas recolheu mais do que sem
    # elas, porque o denominador era ~0). Com escala automática, esses um ou dois
    # outliers levavam o eixo a 600% e esmagavam as outras ~19 barras — que estão
    # todas à volta de 100%, que é exatamente onde a leitura interessa: quem
    # resiste e quem não resiste à perda de 10% dos agentes.
    #
    # O corte não esconde nada: as barras que passam do teto levam o valor real
    # escrito por cima, que é a recomendação para outliers (rótulo direto em vez
    # de deixar a escala mentir).
    TETO = 150
    valores = [v for s in series for v in s["data"] if v is not None]
    if valores and max(valores) > TETO:
        base["yAxis"] = {**base.get("yAxis", {}), "max": TETO}
        for s in series:
            # Rótulo por PONTO (JSON puro, sem funções JS): só os que saem fora
            # do teto o levam. Rotular todas as barras seria ruído.
            s["data"] = [
                v if (v is None or v <= TETO) else
                {"value": v,
                 "label": {"show": True, "position": "top", "fontSize": 11,
                           "color": theme.INK_SOFT, "formatter": f"{v:.0f}%"}}
                for v in s["data"]
            ]
    return {**base, "series": series}


def build():
    dados = _dados()
    if not dados:
        with ui.column().classes("w-full p-4"):
            ui.label("Sem CSV de escalabilidade em results/estatisticas/.") \
                .classes("text-sm font-bold")
        return

    cenarios = [c for c in ROTULOS if c in dados]
    estado = {"n": N_TREINO}

    with ui.column().classes("w-full gap-4 p-4"):
        theme.section_title(
            "groups", "Escalabilidade (Zero-Shot)",
            "QI2 — a mesma política, enxames de dimensão diferente, sem retreino")

        # ── o seletor de N ────────────────────────────────────────────────────
        with ui.card().classes(CARD + " w-full"):
            ui.label("Dimensão do enxame").classes("text-sm font-bold")
            ui.label("Todos os controladores foram treinados com N=20. "
                     "Mover daqui é pedir-lhes uma dimensão que nunca viram.") \
                .classes("text-xs mb-3").style(f"color:{theme.INK_MUTED}")
            with ui.row().classes("items-center gap-2 flex-wrap"):
                botoes = {}
                for n in DIMENSOES:
                    b = ui.button("N = %d" % n,
                                  on_click=lambda x=n: escolher(x)) \
                        .props("flat no-caps").classes("mono-num")
                    botoes[n] = b

        # ── um cartão por algoritmo ───────────────────────────────────────────
        cartoes = ui.row().classes("w-full gap-3 flex-wrap")
        # ── e o gráfico ───────────────────────────────────────────────────────
        grafico = ui.column().classes("w-full")

        def escolher(n):
            estado["n"] = n
            for k, b in botoes.items():
                b.props(remove="outline")
                b.style("background: rgba(255,255,255,%.2f)"
                        % (0.14 if k == n else 0.04))
            desenhar()

        def desenhar():
            n = estado["n"]
            cartoes.clear()
            grafico.clear()

            with cartoes:
                for algo in ALGOS:
                    linhas = [(cen, d[(d["Algorithm"] == algo) & (d["N"] == n)])
                              for cen, d in dados.items() if cen in ROTULOS]
                    compat = [(cen, g) for cen, g in linhas
                              if len(g) and bool(g["compatible"].iloc[0])]
                    with ui.card().classes(CARD).style("min-width:250px;flex:1"):
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.element("div").style(
                                "width:10px;height:10px;border-radius:2px;"
                                "background:%s" % _cor(algo))
                            ui.label(algo).classes("text-sm font-bold mono-title")
                        if not compat:
                            ui.label("indisponível").classes(
                                "text-3xl font-bold mt-2") \
                                .style(f"color:{theme.INK_MUTED}")
                            ui.label(
                                "A política é uma MLP de entrada fixa: a "
                                "observação tem 16+(N−1)×5 valores, logo só "
                                "carrega com N=%d. Não é um resultado fraco — "
                                "é uma incompatibilidade de arquitetura, e é "
                                "essa a resposta à QI2." % N_TREINO
                            ).classes("text-xs mt-2") \
                                .style(f"color:{theme.INK_MUTED}")
                            continue

                        pc = sum(float(g["food_per_agent"].iloc[0])
                                 for _, g in compat) / len(compat)
                        suc = sum(float(g["success_rate"].iloc[0])
                                  for _, g in compat) / len(compat)
                        ui.label(theme.num(pc, 2)).classes(
                            "text-3xl font-bold mono-num mt-2")
                        ui.label("recolhas por agente · média de %d cenários"
                                 % len(compat)).classes("text-xs") \
                            .style(f"color:{theme.INK_MUTED}")
                        ui.label("%.0f%% de sucesso" % (100 * suc)).classes(
                            "text-xs mono-num mt-1") \
                            .style(f"color:{theme.INK_MUTED}")

                        # retenção face ao N de treino
                        if n != N_TREINO:
                            base = []
                            for cen, _ in compat:
                                b = dados[cen][(dados[cen]["Algorithm"] == algo)
                                               & (dados[cen]["N"] == N_TREINO)]
                                if len(b) and pd.notna(b["food_per_agent"].iloc[0]):
                                    base.append(float(b["food_per_agent"].iloc[0]))
                            if base:
                                r = 100.0 * pc / (sum(base) / len(base))
                                ui.label("%.0f%% do que rende a N=%d"
                                         % (r, N_TREINO)).classes(
                                    "text-xs mono-num mt-1") \
                                    .style("color:%s" % (
                                        "#4ade80" if r >= 80 else "#ffb020"))

            # gráfico: per capita por cenário, no N escolhido
            with grafico:
                with ui.card().classes(CARD + " w-full"):
                    ui.label("Eficiência per capita por cenário, com N=%d" % n) \
                        .classes("text-sm font-bold mb-2")
                    series = []
                    for algo in ALGOS:
                        valores = []
                        for cen in cenarios:
                            g = dados[cen][(dados[cen]["Algorithm"] == algo)
                                           & (dados[cen]["N"] == n)]
                            v = (float(g["food_per_agent"].iloc[0])
                                 if len(g) and pd.notna(g["food_per_agent"].iloc[0])
                                 else None)
                            valores.append(v)
                        if any(v is not None for v in valores):
                            series.append({
                                "name": algo, "type": "bar", "data": valores,
                                "itemStyle": {"color": _cor(algo),
                                              "borderRadius": [3, 3, 0, 0]}})
                    if not series:
                        ui.label(
                            "Nenhum controlador é compatível com N=%d além do "
                            "de grafo — e o de grafo não tem dados aqui." % n
                        ).classes("text-xs").style(f"color:{theme.INK_MUTED}")
                    else:
                        base = theme.echart_chrome(
                            y_nome="Recolhas por agente", rotacao_x=18)
                        ui.echart({
                            **base,
                            "xAxis": {**base.get("xAxis", {}), "type": "category",
                                      "data": [ROTULOS[c] for c in cenarios]},
                            "yAxis": {**base.get("yAxis", {}), "type": "value"},
                            "series": series,
                        }).classes("w-full h-72")
                    em_falta = [a for a in ALGOS
                                if not any(s["name"] == a for s in series)]
                    if em_falta:
                        ui.label(
                            "Sem barras para %s: a MLP de entrada fixa não "
                            "carrega com N≠%d." % (" e ".join(em_falta), N_TREINO)
                        ).classes("text-xs mt-2").style(f"color:{theme.INK_MUTED}")

        escolher(N_TREINO)

        # ── Robustez a falhas (Rrobust) ─────────────────────────────────────
        # Veio da vista Ciência. Escalabilidade e robustez sao a mesma pergunta
        # feita de duas maneiras — o que acontece ao modelo JA TREINADO quando o
        # mundo muda: mais agentes (N) ou menos agentes (falhas). Separadas, cada
        # uma parecia um detalhe; juntas, sao o argumento da tese sobre
        # generalizacao.
        rob = data.robustness_table()
        with ui.card().classes(CARD):
            _section_title("health_and_safety",
                           "Robustez a falhas de agentes (Rrobust)",
                           "sempre com N=20 — não segue o seletor acima")
            ui.label("Recolhas retidas quando 10% dos agentes falham a meio do "
                     "episódio (avaliação emparelhada, mesmas seeds). 100% = imune.") \
                .classes("text-xs text-gray-400")
            # O seletor de N governa só a secção da escalabilidade. Esta bateria
            # correu toda a N=20, e as barras do PPO e do SAC aparecem aqui de
            # pleno direito — mas com "N = 50" escolhido lá em cima, e sem esta
            # frase, leem-se como PPO e SAC a N=50, que é precisamente o que a
            # página acabou de dizer ser impossível. Dizer o N aqui custa uma
            # linha; deixar a ambiguidade custava a credibilidade das duas
            # secções ao mesmo tempo.
            ui.label("Todos os valores desta secção são com N=20, o tamanho de "
                     "treino — é a única dimensão em que os três algoritmos "
                     "correm, e por isso a única em que a comparação é possível.") \
                .classes("text-xs").style(f"color:{theme.INK_MUTED}")
            if not rob:
                with ui.row().classes("items-center gap-2 mt-2"):
                    ui.icon("info").classes("text-sky-400")
                    ui.label("Ainda sem avaliações com falhas.").classes("text-gray-400")
                ui.label("Gera com:  python scripts/run_eval.py --algo sac "
                         "--scenario none --episodes 30 --fail-frac 0.1") \
                    .classes("text-xs font-mono text-gray-500")
            else:
                ui.echart(_robustez_option(rob)).classes("w-full").style("height:340px")
                with ui.expansion("Tabela (recolhas: base → com falhas)",
                                  icon="table_view").classes("w-full"):
                    rrows = []
                    for k in config.SCENARIO_KEYS:
                        if k not in rob:
                            continue
                        for a in config.ALGOS:
                            info = rob[k].get(a)
                            if not info:
                                continue
                            rrows.append({
                                "Cenário": config.SCENARIO_LABEL_SHORT[k], "Algo": a,
                                "Base": theme.num(info['base']),
                                "10% falhas": theme.num(info['fail']),
                                "Retenção": (f"{info['retencao']:.0f}%"
                                             if info["retencao"] is not None else "—"),
                                "n": info["n"],
                            })
                    if rrows:
                        ui.table(rows=rrows, columns=[
                            {"name": c, "label": c, "field": c, "align": "left"}
                            for c in rrows[0]]).classes("w-full").props("dense")
