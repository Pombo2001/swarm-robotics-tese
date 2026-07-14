"""Vista «Ao vivo (3D)» — o enxame a mexer, no browser.

Substitui o único uso que restava ao launcher antigo (launcher_dashboard.py): abrir os
visualizadores Ursina para ver um modelo treinado a agir. Aqui é a mesma simulação
(dashboard/simlive.py: env real + modelo real, um forward por passo), desenhada com
ui.scene (three.js) — arrasta para rodar, roda da frente para zoom.

Convenções visuais herdadas do visualizador Ursina (para não desorientar):
  laranja = robô · dourado e maior = a sinalizar comida · verde = ninho ·
  cinza = obstáculos/paredes · vermelho = porta cooperativa (desaparece ao abrir).
"""
from nicegui import run, ui

from .. import config, data, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title

_ALGOS = {"gnn": "GNN (Evolutivo)", "ppo": "PPO", "sac": "SAC"}
_COR_ROBOT = "#E65100"
_COR_SINAL = "#FFD54F"


def build():
    st = {"runner": None, "scene": None, "robots": [], "obst": [], "walls": [],
          "nest": None, "sinal_prev": [], "tick": 0}

    with ui.column().classes("w-full gap-4 p-4 max-w-[1400px] mx-auto"):
        with ui.card().classes(CARD):
            with ui.row().classes("w-full items-center justify-between no-wrap gap-4"):
                _section_title("view_in_ar", "Ao vivo (3D)",
                               "O modelo treinado a agir — mesma simulação do visualizador clássico, agora no browser.")
            with ui.row().classes("items-center gap-4 mt-1"):
                algo_sel = ui.select(_ALGOS, value="gnn", label="Algoritmo") \
                    .props("outlined dense").classes("w-44")
                scen_sel = ui.select(
                    {k: config.SCENARIO_LABEL_SHORT.get(k, k) for k in config.SCENARIO_KEYS},
                    value=config.SCENARIO_KEYS[0], label="Cenário") \
                    .props("outlined dense").classes("w-56")
                vel = ui.slider(min=1, max=8, value=3).props("label") \
                    .classes("w-40").tooltip("passos de simulação por frame")
                play = ui.switch("Simular", value=False)
                ui.button("Reiniciar", icon="restart_alt",
                          on_click=lambda: carregar()).props("outline dense")
            estado = ui.label("Escolhe algoritmo e cenário, e liga «Simular».") \
                .classes("text-xs text-gray-500")
            fonte_lbl = theme.fonte("nenhum modelo carregado")

        with ui.card().classes(CARD):
            scene = ui.scene(grid=False, background_color="#0b0b0d") \
                .classes("w-full h-[560px] rounded")
            st["scene"] = scene

    # ── construção da cena para o runner atual ───────────────────────────────
    def montar_cena():
        r = st["runner"]
        scene.clear()
        with scene:
            R = r.arena_radius
            scene.cylinder(R, R, 0.05, 48).material("#17171a").move(z=-0.05)
            snap = r.snapshot()
            st["nest"] = scene.sphere(r.nest_radius).material("#2E7D32", opacity=0.55)
            st["nest"].move(*snap["nest"])
            st["obst"] = []
            for p in snap["obstacles"]:
                o = scene.sphere(r.obstacle_radius).material("#555")
                o.move(*p)
                st["obst"].append(o)
            st["walls"] = []
            porta = r.door_wall_index
            for i, (pos, size) in enumerate(snap["walls"]):
                w = scene.box(*size).material("#b71c1c" if i == porta else "#3a3a40")
                w.move(*pos)
                st["walls"].append(w)
            st["robots"] = []
            for p in snap["agents"]:
                b = scene.sphere(r.robot_radius).material(_COR_ROBOT)
                b.move(*p)
                st["robots"].append(b)
            st["sinal_prev"] = [False] * len(st["robots"])
            scene.move_camera(x=0, y=-R * 1.35, z=R * 0.95,
                              look_at_x=0, look_at_y=0, look_at_z=0, duration=0.0)

    # ── (re)carregar modelo + env ────────────────────────────────────────────
    async def carregar():
        from ..simlive import SimRunner, model_path_for
        play.value = False
        estado.text = f"A carregar {_ALGOS[algo_sel.value]} / {scen_sel.value}…"
        try:
            st["runner"] = await run.io_bound(SimRunner, algo_sel.value, scen_sel.value)
        except FileNotFoundError as e:
            estado.text = str(e)
            fonte_lbl.text = "⚠ sem modelo para esta combinação"
            return
        montar_cena()
        r = st["runner"]
        rel = r.model_path.replace(str(config.BASE_DIR), "").lstrip("\\/")
        # proveniência: QUAL modelo está em cena. O fallback tem de ser gritante —
        # um modelo do Sandbox num labirinto parece "treino mau" e é só modelo trocado.
        if r.fallback:
            fonte_lbl.text = (f"⚠ {rel} — o cenário {scen_sel.value} não tem modelo "
                              f"próprio; isto é o modelo genérico fora do seu cenário")
        else:
            fonte_lbl.text = f"fonte: {rel}"
        estado.text = "Pronto. Liga «Simular» (arrasta a cena para rodar; roda = zoom)."
        play.value = True

    # ── um frame ─────────────────────────────────────────────────────────────
    def frame():
        r = st["runner"]
        if r is None or not play.value:
            return
        snap = r.step(int(vel.value))
        for b, p in zip(st["robots"], snap["agents"]):
            b.move(*p)
        sinais = snap["signaling"] >= 1.0
        for i, (b, s) in enumerate(zip(st["robots"], sinais)):
            if s != st["sinal_prev"][i]:          # só mudar material quando muda
                b.material(_COR_SINAL if s else _COR_ROBOT)
                st["sinal_prev"][i] = bool(s)
        st["nest"].move(*snap["nest"])
        st["tick"] += 1
        if st["tick"] % 2 == 0:                   # obstáculos/paredes a metade do ritmo
            for o, p in zip(st["obst"], snap["obstacles"]):
                o.move(*p)
            for w, (pos, _s) in zip(st["walls"], snap["walls"]):
                w.move(*pos)
        estado.text = (f"passo {snap['steps']} · episódios {snap['episodes']} · "
                       f"recolhas {snap['food']}")

    ui.timer(0.12, frame)
    algo_sel.on_value_change(carregar)
    scen_sel.on_value_change(carregar)
