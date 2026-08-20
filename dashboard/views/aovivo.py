"""Vista «Ao vivo (3D)» — lança os visualizadores Ursina que já existem.

NÃO reimplementa nada. Abre exatamente `visualization/visualize_algo.py --algo <a>` —
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
# Um só visualizador para os três algoritmos, escolhido por `--algo` (6 ago 2026).
# Antes eram três ficheiros: o `ppo` e o `sac` diferiam em 12 linhas, e tinham já
# divergido de facto (convenções de eixos diferentes, a porta que abria na
# simulação mas não no ecrã só em dois deles).
_SCRIPT = os.path.join(config.BASE_DIR, "visualization", "visualize_algo.py")
_LOG_DIR = os.path.join(config.BASE_DIR, "results", "logs")

# (subpasta, prefixo, extensão) por algoritmo — a convenção de nomes do projeto:
# Sandbox ("none") sem sufixo, restantes com "_{cenário}".
_MODELO = {
    "gnn": ("models", "gnn_3d_best", ".pth"),
    "ppo": ("models_ppo", "ppo_3d_final", ".zip"),
    "sac": ("models_sac", "sac_3d_final", ".zip"),
}

_ATIVOS = "★ Modelos ativos (results/models)"

# --- Vista 3D do MAPA GRANDE ------------------------------------------------
# A geometria está no simulador desde 24 jul 2026 (`_spawn_obstacles_mapa_grande`
# em src/environment/swarm_env_3d.py) e o visualizador lê-a de LÁ — o que se vê é
# o que os robôs treinam. O rascunho scripts/preview_mapa_grande.py foi retirado
# precisamente por ter ficado a ser uma segunda cópia da geometria, divergente.
# O visualizador é o MESMO Ursina dos outros mapas.
_VIZ_MAPA = os.path.join(config.BASE_DIR, "visualization", "visualize_mapa_grande.py")


def _treinos():
    """Origens de modelos: os ativos + a campanha adaptativa + campanhas com modelos.

    As fases da campanha adaptativa (results/novelty_adaptativo/) guardam os .pth do
    GNN em models/ na raiz da fase — a mesma convenção de _modelo_de(). Só têm GNN
    (o PPO/SAC do eval eram os campeões 7d reutilizados), por isso os botões desses
    ficam desativados, como já acontece com campanhas que só treinaram um algoritmo.
    """
    ops = {_ATIVOS: os.path.join(config.BASE_DIR, "results")}
    for lbl, sub in data.ADAPT_FASES:
        raiz = os.path.join(data.ADAPT_DIR, sub)
        if os.path.isdir(os.path.join(raiz, "models")):
            ops[lbl] = raiz
    # Mega-treino: os modelos vivem em results/mega_1mes/<fase>/models, fora do
    # graficos_tese — a mesma situação das fases adaptativas, e por isso a mesma
    # solução. Sem isto, a campanha mais recente da tese (e a que responde à QI6)
    # era a única que não se podia ver a mexer.
    #
    # Só entram as fases com modelos PRÓPRIOS: as do PPO e do SAC arquivaram por
    # engano uma cópia dos modelos GNN da fase anterior (mesmo sha256), e foram
    # removidas — ver o LEIA-ME_modelos.md de cada uma. Abrir uma dessas era ver
    # um GNN a fingir de PPO.
    for lbl, sub in data.MEGA_FASES:
        raiz = os.path.join(data.MEGA_DIR, sub)
        if os.path.isdir(os.path.join(raiz, "models")):
            ops[lbl] = raiz
    for s in data.list_sessions():
        raiz = os.path.join(data.GRAFICOS_DIR, s, "modelos")
        if os.path.isdir(raiz) and os.listdir(raiz):
            # `mega_A1` não diz nem o cenário nem QUANDO foi treinado, e o
            # seletor tem dezenas de entradas assim: escolher ali era adivinhar.
            # A data vem dos dados de origem, não dos ficheiros da pasta — as
            # figuras regeneram-se e diriam a data da regeneração.
            desc = data.descricao_sessao(s)
            ops["%s — %s" % (s, desc) if desc else s] = raiz
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
        aviso_mapa = ui.label("").classes("text-xs").style("color:#d97706")

        def cenarios_com_modelo(raiz):
            """Os mapas que ESTE treino chegou a treinar (qualquer algoritmo)."""
            return [c for c in config.SCENARIO_KEYS
                    if any(_modelo_de(a, c, raiz)[1] for a in _ALGOS)]

        def ao_mudar_treino():
            """O Mapa fica no que estava — e a maioria dos treinos não o tem.

            O seletor de mapa arranca sempre no Sandbox e não se mexia ao trocar de
            treino. Mas quase nenhuma campanha treinou os oito cenários: a «B1» só
            fez coop/bypass/perceção, as fases do mega-treino fizeram uma cada. O
            ecrã respondia com três avisos amarelos — que se leem como "esta
            campanha não tem modelos", quando o que falta é o modelo DAQUELE mapa.
            Agora salta para um mapa que o treino tenha, e diz que saltou.
            """
            raiz = _treinos().get(treino_sel.value)
            aviso_mapa.set_text("")
            if raiz:
                tem = cenarios_com_modelo(raiz)
                if tem and scen_sel.value not in tem:
                    antigo = config.SCENARIO_LABEL_SHORT.get(scen_sel.value, scen_sel.value)
                    scen_sel.set_value(tem[0])
                    aviso_mapa.set_text(
                        "Este treino não treinou «%s» — mudei o mapa para «%s». "
                        "Treinou: %s."
                        % (antigo,
                           config.SCENARIO_LABEL_SHORT.get(tem[0], tem[0]),
                           ", ".join(config.SCENARIO_LABEL_SHORT.get(c, c) for c in tem)))
                elif not tem:
                    aviso_mapa.set_text(
                        "Este treino não tem modelos próprios de nenhum mapa.")
            render()

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
                            cmd = [sys.executable, "-u", _SCRIPT,
                                   "--algo", algo,
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

        # ---------------- MAPA GRANDE (rascunho) — 3D no browser -------------
        with ui.card().classes(CARD):
            # O texto dizia "ainda NÃO está no simulador" — verdade quando foi
            # escrito (23 jul), falso desde 24 jul: o mapa_grande é o 8.º cenário
            # do simulador e já correu campanhas. Ficava aqui a desmentir a vista
            # Mapa composto, ao lado.
            _section_title("construction", "Mapa composto — pré-visualização 3D",
                           "O cenário está no simulador desde 24 jul; isto é só a "
                           "planta, para ver tamanho e aspeto. A altura das paredes "
                           "aqui é da PRÉ-VISUALIZAÇÃO — no simulador é 2× o raio da "
                           "arena, para vedarem mesmo.")

            with ui.row().classes("items-center gap-4 mt-2 no-wrap"):
                raio_sel = ui.select(
                    {45.0: "r=45 m — 77×46 m (3,1× o Quatro Salas)",
                     60.0: "r=60 m — 103×62 m (4,2×)",
                     75.0: "r=75 m — 129×77 m (5,2×)"},
                    value=60.0, label="Tamanho da arena") \
                    .props("outlined dense").classes("w-80")
                altura = ui.number(label="Altura das paredes (m)", value=3.0,
                                   min=0.4, max=30.0, step=0.5) \
                    .props("outlined dense").classes("w-48") \
                    .tooltip("Só para veres o mapa: no simulador as paredes têm 30 m "
                             "(intransponíveis). O visualizador Ursina desenha-as a 0,4.")
                robos_chk = ui.checkbox("Robôs à escala real", value=True) \
                    .tooltip("Raio 0,15 m — minúsculos de propósito. Aproxima a câmara "
                             "para os veres e julgares a escala dos corredores.")

            def _abrir_3d():
                # MESMO visualizador Ursina dos outros mapas (visualization/), com
                # --preview-mapa-grande: sem modelo, sem simulação, só a geometria.
                # Um só visualizador = um só sítio onde pode haver bugs.
                cmd = [sys.executable, "-u", _VIZ_MAPA,
                       "--radius", str(float(raio_sel.value)),
                       "--wall-height", str(float(altura.value or 3.0))]
                if not robos_chk.value:
                    cmd += ["--sem-robos"]

                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                os.makedirs(_LOG_DIR, exist_ok=True)
                log = os.path.join(_LOG_DIR, "viz_mapa_grande.log")
                with open(log, "w", encoding="utf-8") as fh:
                    procs["mapa"] = subprocess.Popen(
                        cmd, cwd=config.BASE_DIR, creationflags=flags,
                        stdout=fh, stderr=subprocess.STDOUT)
                ui.notify("Mapa composto — a abrir a janela 3D (demora uns segundos)…",
                          type="positive")

                def _verificar():
                    p = procs.get("mapa")
                    if p is None or p.poll() is None:
                        return
                    try:
                        txt = open(log, encoding="utf-8", errors="replace").read()
                    except OSError:
                        txt = ""
                    cauda = [l for l in txt.strip().splitlines() if l.strip()][-1:] \
                        or ["(sem detalhe)"]
                    ui.notify(f"A janela do mapa fechou ao arrancar: {cauda[0]}",
                              type="negative", timeout=10000)

                ui.timer(8.0, _verificar, once=True)

            with ui.row().classes("items-center gap-3 mt-2"):
                ui.button("Ver o mapa em 3D", icon="view_in_ar", on_click=_abrir_3d) \
                    .props("unelevated")
                ui.label("Abre a janela Ursina — a mesma dos outros mapas, "
                         "com a câmara livre de sempre.") \
                    .classes("text-xs text-gray-500")

        # Mudar de TREINO pode ter de mexer no mapa; mudar de MAPA é escolha
        # explícita de quem está a ver e respeita-se como está.
        treino_sel.on_value_change(ao_mudar_treino)
        scen_sel.on_value_change(render)
        render()
