"""Curvas de aprendizagem ao vivo (vista Monitorizar, F2).

Lê os CSVs de treino LOCAIS e redesenha em Plotly, atualizando periodicamente.
Um subplot por algoritmo (eixos próprios): a fitness do GNN e a recompensa do
PPO/SAC têm escalas distintas e NÃO devem partilhar eixo (aviso do orientador).
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from nicegui import ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title
# Ordem = predefinição: a métrica de TAREFA primeiro. O "score" mistura duas
# grandezas — fitness evolutiva (~10^5, porque é comida×10000 + shaping) e
# recompensa episódica (~10^2) — e ao ficar por omissão dava a impressão de que
# o GNN é "gigante" ao lado do PPO/SAC quando o que difere é a unidade. Os
# painéis já são separados; a predefinição faltava.
_METRICS = {"Tarefa (recolhas) — comparável": "task",
            "Score (fitness / recompensa) — escalas diferentes": "score"}


def _build_fig(curves: dict, metric: str) -> go.Figure:
    algos = [a for a in config.ALGOS if a in curves]
    if not algos:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", height=200,
                          annotations=[dict(text="Sem CSVs de treino locais ainda.",
                                            showarrow=False, font=dict(color="gray"))])
        return fig
    titles = [f"{a} — {'fitness' if a == 'GNN' and metric == 'score' else ('recompensa' if metric == 'score' else 'recolhas')}"
              for a in algos]
    # Com a métrica de TAREFA os três medem a mesma coisa na mesma unidade, por
    # isso partilham o eixo Y: é a comparação que se quer ver, e com eixos
    # próprios um algoritmo que recolhe 5 desenha-se tão alto como um que recolhe
    # 120. Com o "score" NUNCA se partilha — a fitness (~10^5) esmagaria as
    # curvas do PPO/SAC (~10^2) contra o eixo, que é o efeito de "o GNN é
    # gigante" que não é resultado nenhum, é a unidade.
    partilhar = (metric == "task")
    fig = make_subplots(rows=len(algos), cols=1, subplot_titles=titles,
                        vertical_spacing=0.14, shared_yaxes=partilhar)
    rotulo_y = "recolhas / episódio" if metric == "task" else "fitness / recompensa"
    for i, a in enumerate(algos, start=1):
        c = curves[a]
        y = c.get(metric, [])
        fig.add_trace(
            go.Scatter(x=c["x"], y=y, mode="lines+markers", name=a,
                       line=dict(color=config.ALGO_META[a]["color"], width=2)),
            row=i, col=1)
        fig.update_yaxes(title_text=rotulo_y, row=i, col=1)
        # Uma linha colada ao zero e um painel sem dados desenham-se igual, e
        # ambos se leem como "o grafico nao carregou". Dizer qual dos dois e:
        # "0 recolhas em 20 registos" é um RESULTADO (treino que ainda não come);
        # "sem coluna no CSV" é uma limitação do log, não do algoritmo.
        if not y:
            nota = ("sem coluna de tarefa neste CSV"
                    if metric == "task" else "sem dados neste CSV")
        elif max(y) == 0:
            nota = f"{len(y)} registos, todos a zero — ainda não recolhe"
        else:
            nota = None
        if nota:
            fig.add_annotation(text=nota, row=i, col=1, xref="x domain", yref="y domain",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(color="#9aa5ad", size=12))
    if partilhar:
        topo = max((max(curves[a].get(metric, [0]) or [0]) for a in algos), default=0)
        for i in range(1, len(algos) + 1):
            fig.update_yaxes(range=[0, topo * 1.08 if topo else 1], row=i, col=1)
    fig.update_xaxes(title_text="timesteps", row=len(algos), col=1)
    fig.update_layout(template="plotly_dark", showlegend=False,
                      height=240 * len(algos), margin=dict(l=50, r=20, t=30, b=40),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def build():
    state = {"sig": None}  # assinatura (mtimes + métrica) para evitar redesenhos inúteis

    with ui.card().classes(CARD):
        with ui.row().classes("w-full items-center justify-between"):
            _section_title("show_chart", "Treino local — curvas ao vivo")
            metric_sel = ui.select(list(_METRICS), value=list(_METRICS)[0]) \
                .props("outlined dense").classes("w-72")
        ui.label("Lê os CSVs em results/logs*; cada algoritmo no seu eixo (escalas diferentes).") \
            .classes("text-xs text-gray-500")
        # Estes CSVs são LOCAIS. Quando o treino corre no servidor — o caso normal
        # neste projeto — ficam parados no último treino local, e a vista desenhava
        # curvas antigas sem avisar, dando a impressão de que "algo está mal".
        aviso = ui.label("").classes("text-xs")
        plot = ui.plotly(_build_fig({}, "score")).classes("w-full")

    def refresh(force=False):
        curves = data.training_curves()
        vivo, msg = data.estado_curvas_locais()
        aviso.text = ("" if vivo else "⚠ " + msg)
        aviso.classes(replace="text-xs " + ("text-gray-500" if vivo else "text-amber-600"))
        metric = _METRICS[metric_sel.value]
        sig = (tuple(sorted((a, c["mtime"], len(c["x"])) for a, c in curves.items())), metric)
        if not force and sig == state["sig"]:
            return
        state["sig"] = sig
        plot.update_figure(_build_fig(curves, metric))

    metric_sel.on_value_change(lambda: refresh(force=True))

    # Quando o browser fecha, os elementos morrem mas o timer continua a disparar
    # do lado do servidor — e cada disparo levanta "The parent slot of the element
    # has been deleted", enchendo o log de tracebacks que não são avarias. O
    # app.py já protege o seu timer assim; estes ficaram de fora.
    def _tick():
        try:
            refresh()
        except Exception:  # noqa: BLE001 — o browser desligou; não há nada a salvar
            timer.cancel()

    timer = ui.timer(2.0, _tick)
    refresh(force=True)
