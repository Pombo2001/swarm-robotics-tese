"""Vista «Ao vivo (3D)» — lança os visualizadores Ursina que já existem.

NÃO reimplementa nada. Abre exatamente `visualization/visualize_{gnn,ppo,sac}.py` —
os mesmos mapas, as mesmas cores, a mesma câmara livre e o mesmo slider de velocidade
de sempre. É o que o launcher antigo (`launcher_dashboard.py`) fazia, e a única razão
por que ele ainda era preciso.

Três diferenças face ao launcher antigo, todas para melhor:
  - o mapa vai por `--scenario`, em vez de o launcher REESCREVER o
    configs/foraging.yaml antes de lançar (o ficheiro do repositório ficava alterado
    no disco — já aconteceu, e perdeu os comentários todos);
  - dá para escolher o TREINO: os modelos ativos (results/models*) ou os arquivados de
    qualquer campanha (results/graficos_tese/<sessão>/modelos), sem restaurar nada por
    cima — antes, espreitar um treino antigo obrigava a sobrescrever os modelos ativos;
  - diz que modelo vai carregar e desativa o botão quando não existe. Nem todas as
    campanhas treinaram os três algoritmos (a de 06-07 só tem PPO/SAC, a de 04-07 só
    PPO) — sem isto, o botão abriria uma janela que morre sozinha.
"""
import os
import subprocess
import sys

from nicegui import ui

from .. import config, data, theme

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

_ATIVOS = "★ Modelos ativos (results/models)"


def _treinos():
    """Origens de modelos: os ativos + as campanhas que arquivaram modelos."""
    ops = {_ATIVOS: os.path.join(config.BASE_DIR, "results")}
    for s in data.list_sessions():
        raiz = os.path.join(data.GRAFICOS_DIR, s, "modelos")
        if os.path.isdir(raiz) and os.listdir(raiz):
            ops[s] = raiz
    return ops


def _modelo_de(algo: str, scenario: str, raiz: str):
    """(caminho_relativo, existe, é_fallback) do modelo que o visualizador vai abrir."""
    sub, stem, ext = _MODELO[algo]
    suf = f"_{scenario}" if scenario and scenario != "none" else ""
    proprio = os.path.join(raiz, sub, f"{stem}{suf}{ext}")
    generico = os.path.join(raiz, sub, f"{stem}{ext}")
    rel = lambda p: os.path.relpath(p, config.BASE_DIR).replace("\\", "/")
    if os.path.exists(proprio):
        return rel(proprio), True, False
    if os.path.exists(generico):
        return rel(generico), True, True
    return rel(proprio), False, False


def build():
    procs = {}

    with ui.column().classes("w-full gap-4 p-4 max-w-[1100px] mx-auto"):
        with ui.card().classes(CARD):
            _section_title("view_in_ar", "Ao vivo (3D)",
                           "Abre o visualizador Ursina — câmara livre, velocidade ajustável.")

            treinos = _treinos()
            with ui.row().classes("items-center gap-4 mt-2 no-wrap"):
                treino_sel = ui.select(list(treinos), value=_ATIVOS, label="Treino") \
                    .props("outlined dense").classes("w-72") \
                    .tooltip("Modelos ativos, ou os arquivados de uma campanha "
                             "(não sobrescreve nada)")
                scen_sel = ui.select(
                    {k: config.SCENARIO_LABEL_SHORT.get(k, k) for k in config.SCENARIO_KEYS},
                    value=config.SCENARIO_KEYS[0], label="Mapa") \
                    .props("outlined dense").classes("w-60")
                agents = ui.number(label="Agentes", value=20, min=2, max=200, step=1) \
                    .props("outlined dense").classes("w-28") \
                    .tooltip("O GNN aceita qualquer N (atenção sobre grafo); "
                             "o PPO/SAC só o N de treino")

            ui.label("A janela abre no computador onde o dashboard está a correr. "
                     "Dentro dela: rato para orbitar e zoom, barra no canto para a "
                     "velocidade.").classes("text-xs text-gray-500 mt-1")

        cartoes = ui.row().classes("w-full gap-4 no-wrap")

        def render():
            cartoes.clear()
            raiz = _treinos().get(treino_sel.value, os.path.join(config.BASE_DIR, "results"))
            with cartoes:
                for algo, nome in _ALGOS.items():
                    rel, existe, fb = _modelo_de(algo, scen_sel.value, raiz)
                    with ui.card().classes(CARD + " flex-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("smart_toy").style(
                                f"color:{config.ALGO_META[algo.upper()]['color']}")
                            ui.label(nome).classes("text-base font-bold mono-title")

                        if not existe:
                            ui.label(f"⚠ este treino não tem modelo de {algo.upper()}") \
                                .classes("text-xs mt-1").style("color:#d97706")
                            ui.label(rel).classes("text-xs").style(
                                f"color:{theme.INK_MUTED}")
                            ui.button("Abrir visualizador", icon="play_arrow") \
                                .props("unelevated").classes("w-full mt-2").disable()
                            continue

                        if fb:
                            ui.label("⚠ sem modelo próprio deste mapa — abre o genérico, "
                                     "fora do seu cenário").classes("text-xs mt-1") \
                                .style("color:#d97706")
                        ui.label(f"modelo: {rel}").classes("text-xs mt-1") \
                            .style(f"color:{theme.INK_MUTED}")

                        def abrir(algo=algo, raiz=raiz):
                            # -u: sem buffer, senão o "[OK] modelo carregado" (ou o erro)
                            # fica preso no buffer enquanto a janela está aberta.
                            cmd = [sys.executable, "-u", _SCRIPT[algo],
                                   "--scenario", scen_sel.value]
                            if agents.value and int(agents.value) != 20:
                                cmd += ["--agents", str(int(agents.value))]
                            if treino_sel.value != _ATIVOS:
                                cmd += ["--models-root", raiz]

                            # CREATE_NO_WINDOW: só a janela 3D, sem a consola preta atrás.
                            # O stdout vai para ficheiro — sem ele, um arranque falhado
                            # seria invisível.
                            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                            os.makedirs(_LOG_DIR, exist_ok=True)
                            log = os.path.join(_LOG_DIR, f"viz_{algo}.log")
                            with open(log, "w", encoding="utf-8") as fh:
                                procs[algo] = subprocess.Popen(
                                    cmd, cwd=config.BASE_DIR, creationflags=flags,
                                    stdout=fh, stderr=subprocess.STDOUT)
                            ui.notify(f"{_ALGOS[algo]} · {scen_sel.value} — a abrir a "
                                      f"janela 3D (demora uns segundos)…", type="positive")

                            def _verificar(algo=algo, log=log):
                                p = procs.get(algo)
                                if p is None or p.poll() is None:
                                    return              # ainda vivo: tudo bem
                                try:
                                    txt = open(log, encoding="utf-8", errors="replace").read()
                                except OSError:
                                    txt = ""
                                cauda = [l for l in txt.strip().splitlines()
                                         if l.strip()][-1:] or ["(sem detalhe)"]
                                ui.notify(f"{_ALGOS[algo]} fechou ao arrancar: {cauda[0]}",
                                          type="negative", timeout=10000)

                            ui.timer(8.0, _verificar, once=True)

                        ui.button("Abrir visualizador", icon="play_arrow",
                                  on_click=abrir).props("unelevated").classes("w-full mt-2")

        with ui.card().classes(CARD):
            ui.label("Podes abrir os três ao mesmo tempo: cada um corre na sua janela, "
                     "com o mesmo mapa e o mesmo treino. Fecha a janela para terminar.") \
                .classes("text-xs text-gray-500")

        treino_sel.on_value_change(render)
        scen_sel.on_value_change(render)
        render()
