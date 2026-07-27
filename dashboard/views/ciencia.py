"""Vista 'Ciência' (F3): o estado científico da tese num só ecrã.

Lê o eval_summary.csv (fonte de verdade) e mostra a matriz algoritmo × cenário com
Ptask (% sucesso) e recolhas/ep, com semáforos. Avisa quando a avaliação está
desfasada dos modelos (armadilha nº3) e mostra a significância estatística.
"""
from datetime import datetime

from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _ptask_fundo(p: float, algo: str) -> str:
    """Fundo da célula: HUE do algoritmo, INTENSIDADE = taxa de sucesso.

    Antes eram três degraus fixos do Tailwind — `bg-emerald-700` (≥80%),
    `bg-amber-700` (40-80%) e `bg-red-800` (<40%). Três problemas:

    1. **Verde/vermelho é o pior par possível** para daltonismo (protanopia e
       deuteranopia atingem ~8% dos homens): as duas pontas da escala, que são
       precisamente o que se quer distinguir, colapsam na mesma cor.
    2. **Três degraus numa métrica contínua** achatam 86% e 100% no mesmo verde,
       e é entre esses dois que está a diferença que interessa ler.
    3. Nenhuma das três cores pertence à paleta validada do projeto, ao
       contrário das cores das séries (ver `config.ALGO_META`).

    Agora a célula usa a cor do **próprio algoritmo** (identidade, coluna a
    coluna) e a **opacidade** codifica a magnitude — o eixo que sobrevive a
    qualquer daltonismo e à impressão a preto e branco. As células fracas
    recuam para o fundo; as fortes destacam-se. O caso crítico (<40%) leva
    ainda um ícone, porque estado nunca deve depender só de cor.
    """
    r, g, b = _hex_rgb(config.ALGO_META.get(algo, {}).get("color", "#7d7d7d"))
    alfa = 0.10 + 0.52 * max(0.0, min(1.0, p / 100.0))
    return f"background: rgba({r},{g},{b},{alfa:.3f})"


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
            "data": [{"yAxis": 100,
                      "label": {"formatter": "100% · imune",
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


def _escala_option(tbl: dict) -> dict:
    """Linhas de eficiência (recolhas/agente) vs N, uma série por algoritmo.

    Pontos incompatíveis (MLP do PPO/SAC com N!=20) ficam a None → a linha
    interrompe-se, mostrando que só a GNN transfere para outro N (zero-shot).
    """
    all_n = sorted({p["N"] for pts in tbl.values() for p in pts})
    series = []
    for a in config.ALGOS:
        if a not in tbl:
            continue
        by_n = {p["N"]: p for p in tbl[a]}
        pts = []
        for n in all_n:
            p = by_n.get(n)
            ok = p and p["compatible"] and p["food_per_agent"] is not None
            pts.append(round(p["food_per_agent"], 3) if ok else None)
        s = {"name": a, "type": "line", "connectNulls": False,
             "symbolSize": 10, "lineStyle": {"width": 3},
             # Anel da cor do fundo à volta de cada marcador: o PPO e o SAC têm
             # um único ponto, ambos em N=20 e a alturas quase iguais (3,59 vs
             # 3,57) — sem o anel lê-se um ponto só.
             "itemStyle": {"color": config.ALGO_META[a]["color"],
                           "borderColor": theme.SURFACE, "borderWidth": 2},
             "data": pts}
        # Rótulo direto só nas séries com LINHA (≥2 pontos): assim a identidade
        # não depende só da cor. Nas de ponto único os rótulos escreviam-se uns
        # por cima dos outros no mesmo x — lia-se "BRO" em vez de PPO/SAC — e aí
        # quem identifica são a legenda e o tooltip.
        if sum(1 for p in pts if p is not None) >= 2:
            s["endLabel"] = {"show": True, "formatter": a, "fontSize": 13,
                             "color": config.ALGO_META[a]["color"],
                             "fontWeight": "bold", "distance": 8}
        series.append(s)
    base = theme.echart_chrome(y_nome="Recolhas / agente")
    base["xAxis"].update({
        "data": [str(n) for n in all_n],
        "name": "Nº de agentes (N)", "nameLocation": "middle", "nameGap": 30,
        "nameTextStyle": {"color": theme.INK_MUTED, "fontSize": 12},
    })
    base["grid"] = {"left": 56, "right": 64, "top": 40, "bottom": 52}
    return {**base, "series": series}


_cell_seq = 0


def _cell(info: dict, algo: str = ""):
    global _cell_seq
    if info is None:
        with ui.element("div").classes("rounded-lg p-2 text-center") \
                .style("background: rgba(255,255,255,.03)"):
            ui.label("—").style(f"color:{theme.INK_MUTED}")
        return
    _cell_seq += 1
    el_id = f"sci_cell_{_cell_seq}"
    p = info["ptask"]
    with ui.element("div").classes("rounded-lg p-2 text-center") \
            .style(_ptask_fundo(p, algo)):
        # Ptask com count-up (o efeito dos KPIs da Overview, agora na matriz).
        ui.html(f'<span id="{el_id}" class="text-lg font-bold leading-tight mono-num">'
                f'{p:.0f}%</span>')
        # Estado crítico marcado por FORMA, não por cor: quem não distingue as
        # cores continua a ver que esta célula é diferente.
        if p < 40:
            ui.html('<span class="text-[11px] leading-tight" title="abaixo de 40% '
                    'de sucesso">▲ crítico</span>')
        ui.label(f"{info['recolhas']:.1f} rec/ep").classes("text-xs opacity-80 leading-tight")
        ui.label(f"n={info['n']}").classes("text-[10px] opacity-50 leading-tight")
    delay = 0.15 + (_cell_seq % 24) * 0.04          # cascata pela grelha
    ui.timer(delay, lambda i=el_id, v=info['ptask']: ui.run_javascript(
        f"var e=document.getElementById('{i}');"
        f"if(e&&window.monoCountUp) monoCountUp(e,{v:.0f},0,900,'%');"), once=True)


def build():
    def render():
        body.clear()
        with body:
            # ── Frescura da avaliação ────────────────────────────────────────
            eval_t, model_t, stale = data.eval_freshness()
            with ui.card().classes(CARD):
                if eval_t == 0:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("help").classes("text-gray-400")
                        ui.label("Sem eval_summary.csv — corre uma avaliação primeiro.") \
                            .classes("text-gray-400")
                    return
                fmt = lambda t: datetime.fromtimestamp(t).strftime("%d/%m %H:%M") if t else "—"
                if stale:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("warning").classes("text-amber-400 text-2xl")
                        ui.label("Avaliação DESATUALIZADA face aos modelos").classes("text-lg font-bold text-amber-300")
                    ui.label(f"eval_summary: {fmt(eval_t)}  ·  modelo mais recente: {fmt(model_t)} "
                             "→ re-avalia antes de tirar conclusões (armadilha nº3).") \
                        .classes("text-sm text-amber-200")
                else:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("verified").classes("text-emerald-400 text-2xl")
                        ui.label(f"Avaliação coerente com os modelos (eval: {fmt(eval_t)})") \
                            .classes("text-sm text-emerald-300")

            # ── Matriz Ptask × cenário ───────────────────────────────────────
            table = data.science_table()
            with ui.card().classes(CARD):
                _section_title("grid_on", "Desempenho por cenário (Ptask · recolhas/ep)")
                if not table:
                    ui.label("Sem dados de avaliação.").classes("text-gray-500")
                else:
                    cols = len(config.ALGOS) + 1
                    with ui.grid(columns=cols).classes("w-full gap-1 mt-2"):
                        ui.label("Cenário").classes("font-bold text-sm self-center")
                        for a in config.ALGOS:
                            ui.label(a).classes("font-bold text-sm text-center") \
                                .style(f"color: {config.ALGO_META[a]['color']}")
                        for key in config.SCENARIO_KEYS:
                            if key not in table:
                                continue
                            ui.label(config.SCENARIO_LABEL_BY_KEY[key]) \
                                .classes("text-sm self-center")
                            for a in config.ALGOS:
                                _cell(table[key].get(a), a)
                    # Legenda: a cor diz QUEM (coluna), a intensidade diz QUANTO.
                    with ui.row().classes("gap-4 mt-3 items-center text-xs") \
                            .style(f"color:{theme.INK_MUTED}"):
                        ui.label("intensidade = taxa de sucesso")
                        with ui.row().classes("items-center gap-1"):
                            for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
                                ui.html('<span class="inline-block w-5 h-3 rounded-sm" '
                                        f'style="{_ptask_fundo(frac * 100, config.ALGOS[0])}">'
                                        '</span>')
                            ui.label("0 → 100%").classes("ml-1")
                        ui.label("▲ crítico = abaixo de 40%")

            # ── Significância estatística ────────────────────────────────────
            sig = data.significance()
            if sig is not None and len(sig):
                with ui.card().classes(CARD):
                    with ui.expansion("Significância estatística (recolhas)", icon="functions") \
                            .classes("w-full"):
                        rows = [{
                            "Cenário": r["Label"], "Par": f"{r['A']} vs {r['B']}",
                            "p": f"{r['p_value']:.3g}", "δ Cliff": f"{r['cliffs_delta']:.2f}",
                            "Sig.": "✓" if r["significant"] else "—", "Vencedor": r["winner"],
                        } for _, r in sig.iterrows()]
                        ui.table(rows=rows, columns=[
                            {"name": k, "label": k, "field": k, "align": "left"}
                            for k in rows[0]]).classes("w-full").props("dense")

            # ── Robustez a falhas (Rrobust) ──────────────────────────────────
            rob = data.robustness_table()
            with ui.card().classes(CARD):
                _section_title("health_and_safety",
                               "Robustez a falhas de agentes (Rrobust)")
                ui.label("Recolhas retidas quando 10% dos agentes falham a meio do "
                         "episódio (avaliação emparelhada, mesmas seeds). 100% = imune.") \
                    .classes("text-xs text-gray-400")
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
                                    "Base": f"{info['base']:.1f}",
                                    "10% falhas": f"{info['fail']:.1f}",
                                    "Retenção": (f"{info['retencao']:.0f}%"
                                                 if info["retencao"] is not None else "—"),
                                    "n": info["n"],
                                })
                        if rrows:
                            ui.table(rows=rrows, columns=[
                                {"name": c, "label": c, "field": c, "align": "left"}
                                for c in rrows[0]]).classes("w-full").props("dense")

            # ── Escalabilidade Zero-Shot (Sscale) ────────────────────────────
            scen_scale = data.scalability_scenarios()
            with ui.card().classes(CARD):
                _section_title("open_in_full", "Escalabilidade Zero-Shot (Sscale)")
                ui.label("Eficiência (recolhas/agente) ao transferir, sem retreino, a "
                         "política de N=20 para outros tamanhos de enxame. A linha do "
                         "PPO/SAC interrompe-se em N≠20 (MLP de entrada fixa); só a GNN "
                         "(atenção sobre vizinhos) é invariante a N.") \
                    .classes("text-xs text-gray-400")
                # Cada cenário só aparece aqui se tiver sido AVALIADO. Um cenário em
                # falta não significa "não escala" — significa "ainda não foi corrido";
                # a distinção tem de ser visível, senão o silêncio parece resultado.
                em_falta = [s for s in config.SCENARIO_KEYS if s not in scen_scale]
                if em_falta:
                    rot = ", ".join(config.SCENARIO_LABEL_SHORT.get(s, s) for s in em_falta)
                    theme.fonte(f"Sem dados de escalabilidade em: {rot}. "
                                f"Correr:  python scripts/eval_scalability.py "
                                f"--scenario <cenário> --sizes 10,20,50,100 --episodes 20",
                                aviso=True)
                if not scen_scale:
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("info").classes("text-sky-400")
                        ui.label("Ainda sem dados de escalabilidade.").classes("text-gray-400")
                    ui.label("Gera com:  python scripts/eval_scalability.py --scenario none "
                             "--sizes 10,20,50,100 --episodes 30") \
                        .classes("text-xs font-mono text-gray-500")
                else:
                    sel = ui.select({k: config.SCENARIO_LABEL_SHORT[k] for k in scen_scale},
                                    value=scen_scale[0], label="Cenário") \
                        .props("outlined dense").classes("w-60 mt-1")
                    holder = ui.column().classes("w-full")

                    def draw_scale():
                        holder.clear()
                        tbl = data.scalability_table(sel.value)
                        with holder:
                            if not tbl:
                                ui.label("Sem dados para este cenário.").classes("text-gray-500")
                            else:
                                ui.echart(_escala_option(tbl)).classes("w-full") \
                                    .style("height:340px")

                    sel.on_value_change(draw_scale)
                    draw_scale()

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            _section_title("science", "Estado científico da tese")
            ui.button("Recarregar", icon="refresh", on_click=lambda: render()).props("outline size=sm")
        body = ui.column().classes("w-full gap-4")
    render()
