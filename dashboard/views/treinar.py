"""Vista 'Treinar': fila de trabalhos + consola integrada.

Funde Treino Rápido + Tour + Rotina Noturna numa só vista com uma fila de jobs.
Cada job corre o pipeline completo (treina → avalia → gráficos) via run_experiments.py,
com o stdout a aparecer na consola integrada (sem consolas Windows soltas).
"""
from nicegui import ui

from .. import config, theme
from ..jobs import Job, JobQueue

# Presets: nome -> (algo, cenários, minutos, runs, eval_episodes, ícone, cor)
PRESETS = {
    "Rápido":  ("PPO",   ["none"],                   5,  1, 10, "flash_on",   "secondary"),
    "Tour":    ("GNN",   list(config.SCENARIO_KEYS), 15, 3, 20, "tour",       "primary"),
    "Noturna": ("Todos", list(config.SCENARIO_KEYS), 60, 5, 20, "nights_stay", "accent"),
}

_STATUS_COLOR = {"em fila": "grey", "a correr": "blue", "concluído": "green",
                 "falhou": "red", "parado": "orange"}

CARD = theme.CARD + " p-4"
_section_title = theme.section_title


def build(queue: JobQueue):
    """Constrói a vista Treinar. `queue` é a JobQueue partilhada da app."""
    w = {}  # referências aos widgets do formulário (preenchido abaixo)

    def apply_preset(name):
        algo, cens, mins, runs, ev, *_ = PRESETS[name]
        w["algo"].value = algo
        w["cen"].value = list(cens)
        w["min"].value = mins
        w["runs"].value = runs
        w["eval"].value = ev
        ui.notify(f"Preset '{name}' aplicado", type="info")

    with ui.row().classes("w-full gap-4 no-wrap p-4"):
        # ── Coluna esquerda: formulário + fila ───────────────────────────────
        with ui.column().classes("w-1/2 gap-4"):
            with ui.card().classes(CARD):
                _section_title("add_task", "Novo trabalho de treino")

                with ui.row().classes("w-full gap-2 mt-1"):
                    for name, (_, _, _, _, _, icon, color) in PRESETS.items():
                        ui.button(name, icon=icon, on_click=lambda _, n=name: apply_preset(n)) \
                            .props(f"outline size=sm color={color}")

                w["algo"] = ui.select(["Todos"] + config.ALGOS, value="Todos",
                                      label="Algoritmo").props("outlined dense").classes("w-full")
                w["cen"] = ui.select(
                    options={k: config.SCENARIO_LABEL_BY_KEY[k] for k in config.SCENARIO_KEYS},
                    value=list(config.SCENARIO_KEYS), multiple=True, label="Cenários",
                ).props("outlined dense use-chips").classes("w-full")

                with ui.row().classes("w-full gap-2 no-wrap"):
                    w["min"]  = ui.number("Minutos/run", value=15, min=1, format="%d") \
                        .props("outlined dense").classes("flex-1")
                    w["runs"] = ui.number("Runs/cenário", value=1, min=1, format="%d") \
                        .props("outlined dense").classes("flex-1")
                    w["eval"] = ui.number("Eval ep. (0=não)", value=20, min=0, format="%d") \
                        .props("outlined dense").classes("flex-1")

                def add_job():
                    cens = w["cen"].value or []
                    if not cens:
                        ui.notify("Escolhe pelo menos um cenário", type="warning")
                        return
                    queue.add(Job(
                        algo=w["algo"].value,
                        scenarios=list(cens),
                        minutes=int(w["min"].value or 1),
                        runs=int(w["runs"].value or 1),
                        eval_episodes=int(w["eval"].value or 0),
                    ))
                    ui.notify("Job adicionado à fila", type="positive")
                    fila.refresh()

                ui.button("Adicionar à fila", icon="add", on_click=add_job) \
                    .classes("w-full mt-1").props("color=primary unelevated")

            # Fila de trabalhos
            with ui.card().classes(CARD):
                with ui.row().classes("w-full items-center justify-between"):
                    _section_title("playlist_play", "Fila de trabalhos")
                    with ui.row().classes("gap-1"):
                        ui.button(icon="play_arrow", on_click=lambda: (queue.start(), fila.refresh())) \
                            .props("color=positive size=sm round").tooltip("Iniciar fila")
                        ui.button(icon="stop", on_click=lambda: (queue.stop(), fila.refresh())) \
                            .props("color=negative size=sm round outline").tooltip("Parar")
                        ui.button(icon="cleaning_services",
                                  on_click=lambda: (queue.clear_finished(), fila.refresh())) \
                            .props("size=sm round outline").tooltip("Limpar concluídos")

                @ui.refreshable
                def fila():
                    if not queue.jobs:
                        with ui.column().classes("w-full items-center py-6 gap-1"):
                            ui.icon("inbox").classes("text-4xl text-gray-600")
                            ui.label("Fila vazia — adiciona um trabalho acima.") \
                                .classes("text-gray-500 text-sm")
                        return
                    for job in queue.jobs:
                        color = _STATUS_COLOR.get(job.status, "grey")
                        with ui.row().classes(
                                "w-full items-center justify-between no-wrap "
                                "bg-slate-900/50 rounded-lg px-3 py-2"):
                            ui.label(job.label()).classes("text-sm font-mono")
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                if job.status == "a correr":
                                    ui.spinner(size="sm", color="blue")
                                ui.badge(job.status, color=color).props("rounded")
                                if job.status == "em fila":
                                    ui.button(icon="delete",
                                              on_click=lambda _, j=job.id: (queue.remove(j), fila.refresh())) \
                                        .props("flat round size=sm color=negative")
                fila()

        # ── Coluna direita: consola integrada (estilo terminal) ──────────────
        with ui.column().classes("w-1/2 gap-4"):
            with ui.card().classes(CARD + " p-0 overflow-hidden"):
                with ui.row().classes(
                        "w-full items-center justify-between bg-slate-900 px-4 py-2"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        for c in ("bg-red-500", "bg-yellow-500", "bg-green-500"):
                            ui.element("div").classes(f"w-3 h-3 rounded-full {c}")
                        ui.label("consola de treino").classes("text-sm font-mono text-gray-400 ml-2")
                    status_lbl = ui.label("● inativo").classes("text-xs font-mono text-gray-500")
                log = ui.log(max_lines=2000).classes(
                    "w-full h-[72vh] bg-[#0d1117] text-green-400 text-xs font-mono p-3")

    # Timer: drena o buffer de log e atualiza estados (poll evita problemas cross-thread)
    def tick():
        for line in queue.drain_log():
            log.push(line)
        running = queue.is_running
        status_lbl.text = "● a treinar…" if running else "● inativo"
        status_lbl.classes(replace="text-xs font-mono " +
                           ("text-blue-400" if running else "text-gray-500"))
        fila.refresh()

    ui.timer(0.5, tick)
