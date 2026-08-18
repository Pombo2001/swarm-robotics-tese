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

# Vieram com a comparação de treinos, que estava na Galeria. Da fonte única
# (config), como lá estavam — não são cópias de listas escritas à mão.
SCEN_ORDER = config.MAIN_SCENARIO_KEYS
SCEN_LABEL = config.SCENARIO_LABEL_SHORT


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


def _comparison_html(metrics_a: dict, metrics_b: dict) -> str:
    """Tabela HTML A vs B com Ptask% e recolhas/ep e delta colorido (maior=melhor)."""
    # Cores de ESTADO (bom/mau), não de série: são as da paleta de status e ficam
    # deliberadamente distintas das dos algoritmos, para um delta nunca se fazer
    # passar por uma série. O sinal (+/−) leva a informação sozinho — a cor só
    # reforça, que é o que a torna segura para daltonismo.
    def delta(va, vb, unit=""):
        if va is None or vb is None:
            return f"<span style='color:{theme.INK_MUTED}'>—</span>"
        d = vb - va
        if abs(d) < 1e-9:
            return f"<span style='color:{theme.INK_MUTED}'>0</span>"
        col = "#0ca30c" if d > 0 else "#d03b3b"
        sign = "+" if d > 0 else "−"
        return (f"<span style='color:{col};font-weight:600'>{sign}"
                f"{theme.num(abs(d))}{unit}</span>")

    def cell(m, key, casas=1):
        if m is None:
            return f"<span style='color:{theme.INK_MUTED}'>n/d</span>"
        return theme.num(m[key], casas)

    th = (f"padding:6px 12px;text-align:center;border-bottom:1px solid {theme.BORDER};"
          f"font-weight:600;color:{theme.INK_SOFT};font-size:13px")
    td = f"padding:5px 12px;text-align:center;border-bottom:1px solid #161616"
    rows = []
    algos = ["GNN", "PPO", "SAC"]
    for s in SCEN_ORDER:
        a_s = metrics_a.get(s, {}) if metrics_a else {}
        b_s = metrics_b.get(s, {}) if metrics_b else {}
        for i, alg in enumerate(algos):
            ma, mb = a_s.get(alg), b_s.get(alg)
            scen_cell = (f"<td style='{td};text-align:left;font-weight:600;color:#93c5fd' "
                         f"rowspan='3'>{SCEN_LABEL.get(s, s)}</td>") if i == 0 else ""
            rows.append(
                f"<tr>{scen_cell}"
                f"<td style='{td};text-align:left;color:#e2e8f0'>{alg}</td>"
                f"<td style='{td}'>{cell(ma, 'ptask', 0)}%</td>"
                f"<td style='{td}'>{cell(mb, 'ptask', 0)}%</td>"
                f"<td style='{td}'>{delta(ma['ptask'] if ma else None, mb['ptask'] if mb else None, '%')}</td>"
                f"<td style='{td}'>{cell(ma, 'recolhas')}</td>"
                f"<td style='{td}'>{cell(mb, 'recolhas')}</td>"
                f"<td style='{td}'>{delta(ma['recolhas'] if ma else None, mb['recolhas'] if mb else None)}</td>"
                f"</tr>")
    return (
        "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        "<thead><tr>"
        f"<th style='{th};text-align:left'>Cenário</th>"
        f"<th style='{th};text-align:left'>Algo</th>"
        f"<th style='{th}' colspan='3'>Ptask (sucesso %)</th>"
        f"<th style='{th}' colspan='3'>Recolhas / ep</th>"
        "</tr><tr>"
        f"<th style='{th}'></th><th style='{th}'></th>"
        f"<th style='{th}'>A</th><th style='{th}'>B</th><th style='{th}'>Δ</th>"
        f"<th style='{th}'>A</th><th style='{th}'>B</th><th style='{th}'>Δ</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


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
        ui.label(f"{theme.num(info['recolhas'])} rec/ep").classes("text-xs opacity-80 leading-tight")
        ui.label(f"n={info['n']}").classes("text-[10px] opacity-50 leading-tight")
    delay = 0.15 + (_cell_seq % 24) * 0.04          # cascata pela grelha
    theme.js_diferido(f"var e=document.getElementById('{el_id}');"
                      f"if(e&&window.monoCountUp) "
                      f"monoCountUp(e,{info['ptask']:.0f},0,900,'%');", delay)


def _p_legivel(p: float) -> str:
    """p<0,0001 em vez de 0,0000 — um zero ali lê-se como 'p igual a zero'."""
    return "p < 0,0001" if p < 0.0001 else ("p = %.4f" % p).replace(".", ",")


def _braco_linha(d: dict, destaque: bool = False):
    """Uma linha 'rótulo · média ± dp · convergentes' do mega-treino."""
    cor = theme.INK if destaque else theme.INK_MUTED
    peso = "font-bold" if destaque else ""
    with ui.row().classes("w-full items-center justify-between gap-2"):
        ui.label(d["rotulo"]).classes(f"text-sm {peso}").style(f"color:{cor}")
        with ui.row().classes("items-center gap-3"):
            ui.label(("%.1f ± %.1f" % (d["media"], d["dp"])).replace(".", ",")) \
                .classes(f"text-sm {peso}").style(f"color:{cor}")
            # A contagem é o que decide a leitura deste cenário: 28/28 vs 15/28
            # separa os braços de forma que a média sozinha não separa.
            conv = "%d/%d" % (d["convergentes"], d["n"])
            completo = d["convergentes"] == d["n"]
            ui.label(conv).classes("text-xs px-2 py-0.5 rounded").style(
                "background:%s; color:%s; font-weight:600"
                % ("rgba(46,125,50,.18)" if completo else "rgba(255,255,255,.06)",
                   "#6ee7a8" if completo else theme.INK_MUTED))


def _megatreino_card():
    """O resultado de maior peso do capítulo, e o mais recente — fica no topo.

    Mostra o que a tese afirma em §res_novelty: as contagens de convergência a
    n=28. Os números vêm do resumo JSON gerado pela análise (fonte única).
    """
    m = data.megatreino()
    if not m:
        return
    m1 = m["testes"].get("M1")
    m3 = m["testes"].get("M3")
    if not m1:
        return

    with ui.card().classes(CARD):
        _section_title("workspace_premium",
                       "Mega-treino de 1 mês — Muro em U a n=28",
                       "a campanha que fecha a QI6")
        ui.label("Quatro braços, 28 execuções cada, no cenário que resistia aos "
                 "três algoritmos base. A dosagem adaptativa da novidade é a "
                 "única condição de toda a tese sem uma execução falhada.") \
            .classes("text-xs mt-1").style(f"color:{theme.INK_MUTED}")

        with ui.column().classes("w-full gap-1 mt-3"):
            _braco_linha(m1["a"], destaque=True)
            _braco_linha(m1["b"])
            for chave in ("M2: GNN adaptativo vs PPO", "M2: GNN adaptativo vs SAC"):
                t = m["testes"].get(chave)
                if t:
                    _braco_linha(t["b"])

        with ui.row().classes("w-full gap-4 mt-3 flex-wrap"):
            for rot, val in (
                    ("magnitude (unilateral)",
                     "%s · δ = %+.2f" % (_p_legivel(m1["p"]), m1["delta"])),
                    ("convergência (Fisher exato)",
                     _p_legivel(m1["fisher_p"]) if "fisher_p" in m1 else "—")):
                with ui.column().classes("gap-0"):
                    ui.label(rot).classes("text-xs").style(f"color:{theme.INK_MUTED}")
                    ui.label(val.replace(".", ",")).classes("text-sm font-bold") \
                        .style(f"color:{theme.INK}")

        ui.image("/figuras_tese/megatreino_u_wall_4bracos.png") \
            .classes("w-full rounded mt-3").style("background:#fff")

        if m3:
            # O δ leva vírgula como tudo o resto desta vista: escrevia-se
            # «δ = +0.77» ao lado de «δ = +0,61» na linha de cima.
            ui.label("Porta com Alternativa (M3): %s vs %s — %s, δ = %s. %s"
                     % (("%.1f" % m3["a"]["media"]).replace(".", ","),
                        ("%.1f" % m3["b"]["media"]).replace(".", ","),
                        _p_legivel(m3["p"]),
                        ("%+.2f" % m3["delta"]).replace(".", ","),
                        m3.get("aviso", ""))) \
                .classes("text-xs mt-2").style(f"color:{theme.INK_MUTED}")


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

            # ── Mega-treino (n=28) ───────────────────────────────────────────
            _megatreino_card()

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
                            "p": f"{r['p_value']:.3g}".replace(".", ","),
                            "δ Cliff": theme.num(r['cliffs_delta'], 2, sinal=True),
                            "Sig.": "✓" if r["significant"] else "—", "Vencedor": r["winner"],
                        } for _, r in sig.iterrows()]
                        ui.table(rows=rows, columns=[
                            {"name": k, "label": k, "field": k, "align": "left"}
                            for k in rows[0]]).classes("w-full").props("dense")

            # ── Comparar treinos ─────────────────────────────────────────────
            # Veio da Galeria. A matriz cenário×algoritmo aparecia em TRÊS vistas
            # (aqui, na Galeria e na Proveniência); a comparação entre campanhas
            # pertence ao pé da matriz oficial, não ao pé das imagens.
            eval_sessions = data.sessions_with_eval()
            if len(eval_sessions) >= 1:
                with ui.card().classes(CARD):
                    _section_title("compare_arrows", "Comparar treinos (métricas de avaliação)")
                    ui.label("Escolhe dois treinos para comparar Ptask e recolhas por cenário. "
                             "Δ verde = B melhor que A.").classes("text-xs text-gray-400")
                    default_a = eval_sessions[0]
                    default_b = eval_sessions[1] if len(eval_sessions) > 1 else eval_sessions[0]
                    with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                        cmp_a = ui.select(eval_sessions, value=default_a, label="Treino A") \
                            .props("outlined dense").classes("flex-1")
                        ui.icon("arrow_forward").classes("text-gray-500")
                        cmp_b = ui.select(eval_sessions, value=default_b, label="Treino B") \
                            .props("outlined dense").classes("flex-1")

                    @ui.refreshable
                    def tabela_cmp():
                        ma = data.session_metrics(cmp_a.value)
                        mb = data.session_metrics(cmp_b.value)
                        if ma is None and mb is None:
                            ui.label("Sem métricas para os treinos escolhidos.") \
                                .classes("text-gray-500")
                            return
                        ui.html(_comparison_html(ma or {}, mb or {})).classes("w-full mt-2")

                    for el in (cmp_a, cmp_b):
                        el.on_value_change(lambda: tabela_cmp.refresh())
                    tabela_cmp()

            # A escalabilidade VIVIA aqui e também na vista Escalabilidade, com os
            # mesmos CSV — duas respostas para a mesma pergunta, que é como se
            # começa a ter duas respostas DIFERENTES. Fica só na vista dedicada,
            # que a mostra melhor (por tamanho de enxame e com a retenção per
            # capita). Aqui deixa-se o ponteiro.
            with ui.card().classes(CARD):
                _section_title("open_in_full", "Escalabilidade e robustez",
                               "estão na sua própria vista")
                ui.label("A transferência sem retreino para N ∈ {10, 50, 100} e a "
                         "retenção sob falha de agentes vivem na vista "
                         "«Escalabilidade e robustez» — as duas são propriedades do "
                         "MESMO modelo já treinado, e lêem-se melhor juntas.")                     .classes("text-xs").style(f"color:{theme.INK_MUTED}")

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            _section_title("science", "Estado científico da tese")
            ui.button("Recarregar", icon="refresh", on_click=lambda: render()).props("outline size=sm")
        body = ui.column().classes("w-full gap-4")
    render()
