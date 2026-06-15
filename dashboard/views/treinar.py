"""Vista 'Treinar': fila de trabalhos + consola integrada.

Funde Treino Rápido + Tour + Rotina Noturna numa só vista com uma fila de jobs.
Cada job corre o pipeline completo (treina → avalia → gráficos) via run_experiments.py,
com o stdout a aparecer na consola integrada (sem consolas Windows soltas).
"""
from nicegui import ui

from .. import config
from ..jobs import Job, JobQueue

# Presets: (algo, cenários, minutos, runs, eval_episodes)
PRESETS = {
    "Rápido":  ("PPO",   ["none"],                   5,  1, 10),
    "Tour":    ("GNN",   list(config.SCENARIO_KEYS), 15, 3, 20),
    "Noturna": ("Todos", list(config.SCENARIO_KEYS), 60, 5, 20),
}


def build(queue: JobQueue):
    """Constrói a vista Treinar. `queue` é a JobQueue partilhada da app."""
    w = {}  # referências aos widgets do formulário (preenchido abaixo)

    def apply_preset(name):
        algo, cens, mins, runs, ev = PRESETS[name]
        w["algo"].value = algo
        w["cen"].value = list(cens)
        w["min"].value = mins
        w["runs"].value = runs
        w["eval"].value = ev
        ui.notify(f"Preset '{name}' aplicado", type="info")

    with ui.row().classes("w-full gap-4 no-wrap"):
        # ── Coluna esquerda: formulário + fila ───────────────────────────────
        with ui.column().classes("w-1/2 gap-3"):
            with ui.card().classes("w-full"):
                ui.label("Novo trabalho de treino").classes("text-lg font-bold")

                with ui.row().classes("w-full gap-2"):
                    for name in PRESETS:
                        ui.button(name, on_click=lambda _, n=name: apply_preset(n)) \
                            .props("outline size=sm")

                w["algo"] = ui.select(["Todos"] + config.ALGOS, value="Todos",
                                      label="Algoritmo").classes("w-full")
                w["cen"] = ui.select(
                    options={k: config.SCENARIO_LABEL_BY_KEY[k] for k in config.SCENARIO_KEYS},
                    value=list(config.SCENARIO_KEYS), multiple=True, label="Cenários",
                ).props("use-chips").classes("w-full")

                with ui.row().classes("w-full gap-2 no-wrap"):
                    w["min"]  = ui.number("Minutos/run", value=15, min=1, format="%d").classes("flex-1")
                    w["runs"] = ui.number("Runs/cenário", value=1, min=1, format="%d").classes("flex-1")
                    w["eval"] = ui.number("Eval ep. (0=não)", value=20, min=0, format="%d").classes("flex-1")

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

                ui.button("➕  Adicionar à fila", on_click=add_job) \
                    .classes("w-full").props("color=primary")

            # Fila de trabalhos
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Fila de trabalhos").classes("text-lg font-bold")
                    with ui.row().classes("gap-2"):
                        ui.button("▶ Iniciar", on_click=lambda: (queue.start(), fila.refresh())) \
                            .props("color=positive size=sm")
                        ui.button("⏹ Parar", on_click=lambda: (queue.stop(), fila.refresh())) \
                            .props("color=negative size=sm outline")
                        ui.button("🧹 Limpar concluídos",
                                  on_click=lambda: (queue.clear_finished(), fila.refresh())) \
                            .props("size=sm outline")

                @ui.refreshable
                def fila():
                    if not queue.jobs:
                        ui.label("Fila vazia — adiciona um trabalho acima.").classes("text-gray-500")
                        return
                    for job in queue.jobs:
                        color = {"em fila": "grey", "a correr": "blue", "concluído": "green",
                                 "falhou": "red", "parado": "orange"}.get(job.status, "grey")
                        with ui.row().classes("w-full items-center justify-between no-wrap"):
                            ui.label(job.label()).classes("text-sm")
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                ui.badge(job.status, color=color)
                                if job.status == "em fila":
                                    ui.button(icon="delete",
                                              on_click=lambda _, j=job.id: (queue.remove(j), fila.refresh())) \
                                        .props("flat round size=sm color=negative")
                fila()

        # ── Coluna direita: consola integrada ────────────────────────────────
        with ui.column().classes("w-1/2 gap-3"):
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Consola de treino").classes("text-lg font-bold")
                    status_lbl = ui.label("● inativo").classes("text-sm text-gray-500")
                log = ui.log(max_lines=2000).classes("w-full h-[70vh] bg-black text-green-400 text-xs")

    # Timer: drena o buffer de log e atualiza estados (poll evita problemas cross-thread)
    def tick():
        for line in queue.drain_log():
            log.push(line)
        running = queue.is_running
        status_lbl.text = "● a treinar…" if running else "● inativo"
        status_lbl.classes(replace="text-sm " + ("text-blue-400" if running else "text-gray-500"))
        fila.refresh()

    ui.timer(0.5, tick)
