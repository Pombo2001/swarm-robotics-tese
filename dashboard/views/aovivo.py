"""Vista «Ao vivo (3D)» — lança os visualizadores Ursina que já existem.

NÃO reimplementa nada. Abre exatamente `visualization/visualize_{gnn,ppo,sac}.py` —
os mesmos mapas, as mesmas cores, a mesma câmara livre e o mesmo slider de velocidade
que sempre usaste. É o que o launcher antigo (`launcher_dashboard.py`) fazia, e a
única razão por que ele ainda era preciso.

Duas diferenças face ao launcher antigo, ambas para melhor:
  - o cenário vai por `--scenario`, em vez de o launcher REESCREVER o
    configs/foraging.yaml antes de lançar (o ficheiro do repositório ficava alterado
    no disco — já aconteceu, e perdeu os comentários todos);
  - a vista diz que modelo vai ser carregado e avisa quando é fallback: um modelo do
    Sandbox largado num labirinto parece treino mau e é só o modelo errado.

Uma tentativa anterior de desenhar a simulação no browser (ui.scene/three.js) foi
abandonada: não renderizava neste ambiente e, mesmo a renderizar, não teria a câmara
livre do Ursina. O visualizador nativo é melhor — só faltava poder chamá-lo daqui.
"""
import os
import subprocess
import sys

from nicegui import ui

from .. import config, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title

_ALGOS = {"gnn": "GNN (Evolutivo)", "ppo": "PPO", "sac": "SAC"}
_SCRIPT = {a: os.path.join(config.BASE_DIR, "visualization", f"visualize_{a}.py")
           for a in _ALGOS}
_LOG_DIR = os.path.join(config.BASE_DIR, "results", "logs")

# (subpasta, prefixo, extensão) por algoritmo — a convenção de nomes do projeto:
# Sandbox ("none") sem sufixo, restantes com "_{cenário}".
_MODELO = {
    "gnn": ("models", "gnn_3d_best", ".pth"),
    "ppo": ("models_ppo", "ppo_3d_final", ".zip"),
    "sac": ("models_sac", "sac_3d_final", ".zip"),
}


def _modelo_de(algo: str, scenario: str):
    """(caminho_relativo, existe, é_fallback) do modelo que o visualizador vai abrir."""
    sub, stem, ext = _MODELO[algo]
    suf = f"_{scenario}" if scenario and scenario != "none" else ""
    proprio = os.path.join(config.BASE_DIR, "results", sub, f"{stem}{suf}{ext}")
    generico = os.path.join(config.BASE_DIR, "results", sub, f"{stem}{ext}")
    if os.path.exists(proprio):
        return os.path.relpath(proprio, config.BASE_DIR), True, False
    if os.path.exists(generico):
        return os.path.relpath(generico, config.BASE_DIR), True, True
    return os.path.relpath(proprio, config.BASE_DIR), False, False


def build():
    procs = {}   # algo -> Popen (para saber o que está aberto)

    with ui.column().classes("w-full gap-4 p-4 max-w-[1100px] mx-auto"):
        with ui.card().classes(CARD):
            _section_title("view_in_ar", "Ao vivo (3D)",
                           "Abre o visualizador Ursina — câmara livre, velocidade ajustável.")

            with ui.row().classes("items-center gap-4 mt-2"):
                scen_sel = ui.select(
                    {k: config.SCENARIO_LABEL_SHORT.get(k, k) for k in config.SCENARIO_KEYS},
                    value=config.SCENARIO_KEYS[0], label="Mapa") \
                    .props("outlined dense").classes("w-64")
                agents = ui.number(label="Agentes", value=20, min=2, max=200, step=1) \
                    .props("outlined dense").classes("w-32") \
                    .tooltip("Passa --agents ao visualizador (o GNN aceita qualquer N; "
                             "o PPO/SAC só o N de treino)")

            ui.label("A janela abre no computador onde o dashboard está a correr. "
                     "Dentro dela: rato para orbitar e zoom, barra no canto para a "
                     "velocidade.").classes("text-xs text-gray-500 mt-1")

        # ── um cartão por algoritmo ──────────────────────────────────────────
        with ui.row().classes("w-full gap-4 no-wrap"):
            for algo, nome in _ALGOS.items():
                with ui.card().classes(CARD + " flex-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("smart_toy").style(
                            f"color:{config.ALGO_META[algo.upper()]['color']}")
                        ui.label(nome).classes("text-base font-bold mono-title")

                    fonte = ui.label("").classes("text-xs mt-1")
                    botao = ui.button("Abrir visualizador", icon="play_arrow") \
                        .props("unelevated").classes("w-full mt-2")

                    def atualizar(algo=algo, fonte=fonte, botao=botao):
                        rel, existe, fb = _modelo_de(algo, scen_sel.value)
                        if not existe:
                            fonte.text = f"⚠ sem modelo: {rel}"
                            fonte.style("color:#d97706")
                            botao.disable()
                        elif fb:
                            fonte.text = (f"⚠ {rel} — este mapa não tem modelo próprio; "
                                          f"abre o modelo genérico, fora do seu cenário")
                            fonte.style("color:#d97706")
                            botao.enable()
                        else:
                            fonte.text = f"modelo: {rel}"
                            fonte.style(f"color:{theme.INK_MUTED}")
                            botao.enable()

                    def abrir(algo=algo, botao=botao):
                        # -u: sem buffer. Sem isto, o "[OK] Modelo carregado" (ou o erro)
                        # fica preso no buffer do processo enquanto a janela está aberta,
                        # e o log só serviria depois de o visualizador fechar.
                        cmd = [sys.executable, "-u", _SCRIPT[algo],
                               "--scenario", scen_sel.value]
                        if agents.value and int(agents.value) != 20:
                            cmd += ["--agents", str(int(agents.value))]

                        # CREATE_NO_WINDOW: sem a janela preta de consola a saltar
                        # atrás do visualizador (só a janela 3D do Ursina aparece).
                        # Mas o stdout deixaria de existir — e é lá que o script diz
                        # "[OK] modelo carregado" ou porque falhou. Vai para ficheiro,
                        # que a vista mostra se o processo morrer à nascença.
                        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                        os.makedirs(_LOG_DIR, exist_ok=True)
                        log = os.path.join(_LOG_DIR, f"viz_{algo}.log")
                        with open(log, "w", encoding="utf-8") as fh:
                            procs[algo] = subprocess.Popen(
                                cmd, cwd=config.BASE_DIR, creationflags=flags,
                                stdout=fh, stderr=subprocess.STDOUT)
                        ui.notify(f"{_ALGOS[algo]} · {scen_sel.value} — a abrir a janela 3D "
                                  f"(demora uns segundos)…", type="positive")

                        def _verificar(algo=algo, log=log):
                            p = procs.get(algo)
                            if p is None or p.poll() is None:
                                return          # ainda a correr: tudo bem
                            try:
                                erro = open(log, encoding="utf-8", errors="replace").read()
                            except OSError:
                                erro = ""
                            cauda = [l for l in erro.strip().splitlines()
                                     if l.strip()][-1:] or ["(sem detalhe)"]
                            ui.notify(f"{_ALGOS[algo]} fechou logo ao arrancar: {cauda[0]}",
                                      type="negative", timeout=10000)

                        # o Ursina leva alguns segundos a abrir a janela; só se ainda
                        # assim tiver morrido é que houve mesmo um erro
                        ui.timer(8.0, _verificar, once=True)

                    botao.on_click(abrir)
                    scen_sel.on_value_change(lambda _e, f=atualizar: f())
                    atualizar()

        with ui.card().classes(CARD):
            ui.label("Podes abrir os três ao mesmo tempo: cada um corre na sua janela, "
                     "com o mesmo mapa. Fecha a janela para terminar.") \
                .classes("text-xs text-gray-500")
