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
_METRICS = {"Score (fitness / recompensa)": "score", "Tarefa (recolhas)": "task"}


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
    fig = make_subplots(rows=len(algos), cols=1, subplot_titles=titles, vertical_spacing=0.14)
    for i, a in enumerate(algos, start=1):
        c = curves[a]
        y = c.get(metric, [])
        fig.add_trace(
            go.Scatter(x=c["x"], y=y, mode="lines+markers", name=a,
                       line=dict(color=config.ALGO_META[a]["color"], width=2)),
            row=i, col=1)
        fig.update_yaxes(title_text=metric, row=i, col=1)
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
