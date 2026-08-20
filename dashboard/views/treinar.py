"""Vista 'Treinar': fila de trabalhos + consola integrada.

Funde Treino Rápido + Tour + Rotina Noturna numa só vista com uma fila de jobs.
Cada job corre o pipeline completo (treina → avalia → gráficos) via run_experiments.py,
com o stdout a aparecer na consola integrada (sem consolas Windows soltas).

Design (Swarm Observatory): seleção por CHIPS (algoritmo com a cor científica,
cenários em grelha clicável), estimativa de duração ao vivo, presets em cartões
e fila com barra de estado colorida por job.
"""
from nicegui import ui

from .. import config, theme
from ..jobs import Job, JobQueue

# Presets: nome -> (algo, cenários, minutos, runs, eval_episodes, ícone, descrição)
PRESETS = {
    "Rápido":  ("PPO",   ["none"],                   5,  1, 10, "flash_on",
                "1 execução PPO no Sandbox — fumo em ~5 min"),
    "Tour":    ("GNN",   list(config.SCENARIO_KEYS), 15, 3, 20, "tour",
                "GNN em todos os cenários, 3 execuções curtas"),
    "Noturna": ("Todos", list(config.SCENARIO_KEYS), 60, 5, 20, "nights_stay",
                "Pipeline completo — deixar a correr de noite"),
}

_STATUS_COLOR = {"em fila": "#636363", "a correr": "#60a5fa", "concluído": "#34d399",
                 "falhou": "#ef4444", "parado": "#f59e0b"}
_STATUS_BADGE = {"em fila": "grey", "a correr": "blue", "concluído": "green",
                 "falhou": "red", "parado": "orange"}

CARD = theme.CARD + " p-4"
_section_title = theme.section_title


def _fmt_dur(total_min: float) -> str:
    h, m = divmod(int(round(total_min)), 60)
    return f"{h}h {m:02d}m" if h else f"{m} min"


def build(queue: JobQueue):
    """Constrói a vista Treinar. `queue` é a JobQueue partilhada da app."""
    state = {"algo": "Todos", "cens": set(config.SCENARIO_KEYS),
             "min": 15, "runs": 1, "eval": 20}
    w = {}  # widgets numéricos

    # ── helpers de estado ─────────────────────────────────────────────────────
    def _n_algos() -> int:
        return len(config.ALGOS) if state["algo"] == "Todos" else 1

    def _update_est():
        n = _n_algos() * len(state["cens"]) * int(w["runs"].value or 1)
        total = n * int(w["min"].value or 1)
        est_num.set_content(
            f'<span class="mono-num" style="font-size:1.7rem;font-weight:600;'
            f'color:{theme.INK}">{_fmt_dur(total)}</span>')
        est_sub.text = (f"{n} treino(s) = {_n_algos()} algo(s) × "
                        f"{len(state['cens'])} cenário(s) × {int(w['runs'].value or 1)} execução(ões)")

    def apply_preset(name):
        algo, cens, mins, runs, ev, *_ = PRESETS[name]
        state["algo"] = algo
        state["cens"] = set(cens)
        w["min"].value = mins
        w["runs"].value = runs
        w["eval"].value = ev
        algo_chips.refresh()
        cen_chips.refresh()
        _update_est()
        ui.notify(f"Preset '{name}' aplicado", type="info")

    # ── chips de algoritmo (cores científicas) ────────────────────────────────
    @ui.refreshable
    def algo_chips():
        with ui.row().classes("w-full gap-2 no-wrap"):
            for a in ["Todos"] + config.ALGOS:
                on = state["algo"] == a
                color = "#f5f5f5" if a == "Todos" else config.ALGO_META[a]["color"]
                label = "Todos" if a == "Todos" else config.ALGO_META[a]["label"]

                def _pick(_, a=a):
                    state["algo"] = a
                    algo_chips.refresh()
                    _update_est()

                chip = ui.row().classes(
                    "items-center gap-2 no-wrap px-3 py-2 cursor-pointer flex-1 "
                    "justify-center").style(
                    f"border-radius:10px; transition:all .18s ease; "
                    + (f"border:1px solid {color}; background:rgba(255,255,255,.07);"
                       if on else
                       f"border:1px solid {theme.BORDER}; background:transparent; opacity:.65;"))
                with chip:
                    ui.element("div").style(
                        f"width:8px;height:8px;border-radius:50%;background:{color};"
                        + ("" if on else "opacity:.5;"))
                    ui.label(label).classes("text-xs font-bold mono-title").style(
                        f"color:{theme.INK if on else theme.INK_MUTED}")
                chip.on("click", _pick)

    # ── chips de cenário (grelha clicável) ────────────────────────────────────
    @ui.refreshable
    def cen_chips():
        with ui.row().classes("w-full items-center justify-between no-wrap"):
            ui.label("CENÁRIOS").classes("text-[10px] tracking-[.2em] font-bold") \
                .style(f"color:{theme.INK_MUTED}")
            def _all(_):
                state["cens"] = set(config.SCENARIO_KEYS) \
                    if state["cens"] != set(config.SCENARIO_KEYS) else set()
                cen_chips.refresh(); _update_est()
            lbl = ("limpar" if state["cens"] == set(config.SCENARIO_KEYS) else "todos")
            b = ui.label(lbl).classes("text-[11px] cursor-pointer") \
                .style(f"color:{theme.INK_SOFT}; text-decoration:underline dotted")
            b.on("click", _all)
        with ui.grid(columns=2).classes("w-full gap-1 mt-1"):
            for k in config.SCENARIO_KEYS:
                on = k in state["cens"]

                def _tog(_, k=k):
                    (state["cens"].discard if k in state["cens"]
                     else state["cens"].add)(k)
                    cen_chips.refresh()
                    _update_est()

                chip = ui.row().classes(
                    "items-center gap-2 no-wrap px-2 py-1 cursor-pointer").style(
                    f"border-radius:8px; transition:all .15s ease; "
                    + ("border:1px solid #3a3a3a; background:rgba(255,255,255,.06);"
                       if on else
                       f"border:1px solid {theme.BORDER}; opacity:.55;"))
                with chip:
                    ui.icon("check_circle" if on else "radio_button_unchecked") \
                        .classes("text-xs").style(
                        f"color:{theme.INK if on else theme.INK_MUTED}")
                    ui.label(config.SCENARIO_LABEL_BY_KEY[k]).classes("text-xs") \
                        .style(f"color:{theme.INK_SOFT if on else theme.INK_MUTED}")
                chip.on("click", _tog)

    with ui.row().classes("w-full gap-4 no-wrap p-4"):
        # ── Coluna esquerda: formulário + fila ───────────────────────────────
        with ui.column().classes("w-1/2 gap-4"):
            with ui.card().classes(CARD + " gap-3"):
                _section_title("add_task", "Novo trabalho de treino")
                # A regra do projeto (docs/PLANO_MESTRE.md §7) é explícita: nada
                # de treinos nem avaliações longas no PC — só no servidor. Esta
                # vista continua a existir para *smoke tests* de minutos, que é
                # para o que serve; sem o aviso, um botão convidativo contradiz
                # em silêncio a regra que o próprio projeto escreveu.
                ui.label("⚠ A regra do projeto é treinar NO SERVIDOR (PLANO_MESTRE §7). "
                         "Isto aqui é para testes curtos — um treino a sério ocupa "
                         "a máquina durante dias e não se compara com os do servidor.") \
                    .classes("text-xs").style("color:#f0a04b")

                # Presets em cartões
                with ui.row().classes("w-full gap-2 no-wrap"):
                    for name, (_, _, _, _, _, icon, desc) in PRESETS.items():
                        with ui.column().classes(
                                "flex-1 gap-0 px-3 py-2 cursor-pointer mono-card-hover").style(
                                f"border:1px solid {theme.BORDER}; border-radius:10px; "
                                "background:rgba(255,255,255,.02); transition:all .18s ease;") \
                                as card:
                            with ui.row().classes("items-center gap-1 no-wrap"):
                                ui.icon(icon).classes("text-sm").style(f"color:{theme.INK}")
                                ui.label(name).classes("text-xs font-bold mono-title") \
                                    .style(f"color:{theme.INK}")
                            ui.label(desc).classes("text-[10px] leading-tight mt-1") \
                                .style(f"color:{theme.INK_MUTED}")
                        card.on("click", lambda _, n=name: apply_preset(n))

                ui.label("ALGORITMO").classes("text-[10px] tracking-[.2em] font-bold") \
                    .style(f"color:{theme.INK_MUTED}")
                algo_chips()
                cen_chips()

                with ui.row().classes("w-full gap-2 no-wrap"):
                    w["min"]  = ui.number("Minutos/execução", value=15, min=1, format="%d",
                                          on_change=lambda _: _update_est()) \
                        .props("outlined dense").classes("flex-1")
                    w["runs"] = ui.number("Execuções/cenário", value=1, min=1, format="%d",
                                          on_change=lambda _: _update_est()) \
                        .props("outlined dense").classes("flex-1")
                    w["eval"] = ui.number("Eval ep. (0=não)", value=20, min=0, format="%d") \
                        .props("outlined dense").classes("flex-1")

                # Estimativa de duração ao vivo
                with ui.row().classes("w-full items-center gap-3 no-wrap px-3 py-2").style(
                        f"border:1px dashed {theme.BORDER}; border-radius:10px;"):
                    ui.icon("schedule").style(f"color:{theme.INK_MUTED}")
                    with ui.column().classes("gap-0"):
                        est_num = ui.html("")
                        est_sub = ui.label("").classes("text-[11px]") \
                            .style(f"color:{theme.INK_MUTED}")

                def add_job():
                    if not state["cens"]:
                        ui.notify("Escolhe pelo menos um cenário", type="warning")
                        return
                    queue.add(Job(
                        algo=state["algo"],
                        scenarios=[k for k in config.SCENARIO_KEYS if k in state["cens"]],
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
                            ui.icon("inbox").classes("text-4xl").style(f"color:{theme.INK_MUTED}")
                            ui.label("Fila vazia — adiciona um trabalho acima.") \
                                .classes("text-sm").style(f"color:{theme.INK_MUTED}")
                        return
                    for job in queue.jobs:
                        c = _STATUS_COLOR.get(job.status, "#636363")
                        with ui.row().classes(
                                "w-full items-center justify-between no-wrap "
                                "rounded-lg px-3 py-2").style(
                                f"background:var(--surface2); "
                                f"border-left:3px solid {c}; transition:border-color .3s ease;"):
                            ui.label(job.label()).classes("text-sm mono-num") \
                                .style(f"color:{theme.INK_SOFT}")
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                if job.status == "a correr":
                                    ui.spinner("dots", size="sm", color="blue")
                                ui.badge(job.status,
                                         color=_STATUS_BADGE.get(job.status, "grey")) \
                                    .props("rounded outline")
                                if job.status == "em fila":
                                    ui.button(icon="delete",
                                              on_click=lambda _, j=job.id: (queue.remove(j), fila.refresh())) \
                                        .props("flat round size=sm color=negative")
                fila()

        # ── Coluna direita: consola integrada (estilo terminal) ──────────────
        with ui.column().classes("w-1/2 gap-4"):
            with ui.card().classes(CARD + " p-0 overflow-hidden"):
                with ui.row().classes(
                        "w-full items-center justify-between px-4 py-2").style(
                        f"background:var(--surface2); border-bottom:1px solid {theme.BORDER}"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        for c in ("bg-red-500", "bg-yellow-500", "bg-green-500"):
                            ui.element("div").classes(f"w-3 h-3 rounded-full {c} opacity-70")
                        ui.label("consola de treino").classes("text-sm mono-num ml-2") \
                            .style(f"color:{theme.INK_MUTED}")
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        status_dot = ui.element("div").classes("live-dot live-dot--idle")
                        status_lbl = ui.label("inativo").classes("text-xs mono-num") \
                            .style(f"color:{theme.INK_MUTED}")
                log = ui.log(max_lines=2000).classes(
                    "w-full h-[72vh] text-xs mono-console p-3").style(
                    "background:#070707; color:#4ade80;")

    _update_est()

    # Timer: drena o buffer de log e atualiza estados (poll evita problemas cross-thread)
    def tick():
        # O browser pode ter fechado: os elementos morrem, o timer não. Sem isto,
        # cada disparo levanta "The parent slot of the element has been deleted"
        # e o log enche-se de tracebacks que não são avarias — o treino em si
        # corre noutro processo e não é afetado. Mesmo padrão do app.py.
        try:
            for line in queue.drain_log():
                log.push(line)
            running = queue.is_running
            status_lbl.text = "a treinar…" if running else "inativo"
            status_dot.classes(remove="live-dot--idle",
                               add="" if running else "live-dot--idle")
            fila.refresh()
        except Exception:  # noqa: BLE001
            timer.cancel()

    timer = ui.timer(0.5, tick)
