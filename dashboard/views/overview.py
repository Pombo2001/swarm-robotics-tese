"""Vista 'Overview' — página de entrada, com ar de site científico.

Hero com um enxame de boids (canvas, pontos brancos sobre preto — o tema da tese
a nadar no ecrã), KPIs animados (count-up), cartões de estado (treino local,
frescura da avaliação, última sessão, servidor) e a linha do tempo do projeto.
Só LÊ dados (data.py / JobQueue); não lança nada.
"""
from datetime import datetime

from nicegui import ui

from .. import config, data, theme
from ..jobs import JobQueue

# ── Boids (canvas) ────────────────────────────────────────────────────────────
# Enxame minimalista: pontos brancos com ligações ténues entre vizinhos —
# separação/alinhamento/coesão simplificados, suave e barato (1 canvas, rAF).
_BOIDS_JS = r"""
(function () {
  const cv = document.getElementById('boids');
  if (!cv || cv.dataset.running) return;
  cv.dataset.running = '1';
  const ctx = cv.getContext('2d');
  let W, H;
  function resize() {
    const r = cv.getBoundingClientRect();   // o canvas cobre o hero (absolute inset:0)
    W = cv.width = r.width; H = cv.height = r.height;
  }
  resize(); window.addEventListener('resize', resize);

  const N = 70, VIEW = 70, SPEED = 1.05;
  const boids = Array.from({length: N}, () => ({
    x: Math.random() * 1200, y: Math.random() * 400,
    vx: (Math.random() - .5) * 2, vy: (Math.random() - .5) * 2,
  }));

  function step() {
    for (const b of boids) {
      let cx = 0, cy = 0, ax = 0, ay = 0, sx = 0, sy = 0, n = 0;
      for (const o of boids) {
        if (o === b) continue;
        const dx = o.x - b.x, dy = o.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 < VIEW * VIEW) {
          cx += o.x; cy += o.y; ax += o.vx; ay += o.vy; n++;
          if (d2 < 500) { sx -= dx; sy -= dy; }
        }
      }
      if (n) {
        b.vx += ((cx / n - b.x) * .0016) + ((ax / n - b.vx) * .045) + sx * .0035;
        b.vy += ((cy / n - b.y) * .0016) + ((ay / n - b.vy) * .045) + sy * .0035;
      }
      const v = Math.hypot(b.vx, b.vy) || 1;
      b.vx = b.vx / v * SPEED; b.vy = b.vy / v * SPEED;
      b.x += b.vx; b.y += b.vy;
      if (b.x < -10) b.x = W + 10;  if (b.x > W + 10) b.x = -10;
      if (b.y < -10) b.y = H + 10;  if (b.y > H + 10) b.y = -10;
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(255,255,255,.07)';
    for (let i = 0; i < boids.length; i++)
      for (let j = i + 1; j < boids.length; j++) {
        const a = boids[i], b = boids[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        if (dx * dx + dy * dy < 3600) {
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    ctx.fillStyle = 'rgba(255,255,255,.75)';
    for (const b of boids) { ctx.beginPath(); ctx.arc(b.x, b.y, 1.6, 0, 7); ctx.fill(); }
  }

  (function loop() {
    if (document.getElementById('boids')) { step(); draw(); requestAnimationFrame(loop); }
  })();
})();
"""


def _kpi(label: str, value: float, decimals: int = 0, suffix: str = ""):
    """Cartão KPI com número animado (count-up via JS do tema)."""
    el_id = f"kpi_{label.lower().replace(' ', '_').replace('.', '')}"
    with ui.card().classes(theme.CARD + " mono-card-hover items-start gap-0 p-4"):
        with ui.row().classes("items-baseline gap-1 no-wrap"):
            ui.html(f'<span id="{el_id}" class="mono-num mono-num-hero" '
                    f'style="font-size:2rem;font-weight:600">0</span>')
            if suffix:
                ui.label(suffix).classes("text-sm").style(f"color:{theme.INK_MUTED}")
        ui.label(label).classes("text-xs uppercase tracking-widest") \
            .style(f"color:{theme.INK_MUTED}")
    ui.timer(0.3, lambda: ui.run_javascript(
        f"var e=document.getElementById('{el_id}');"
        f"if(e) monoCountUp(e, {value}, {decimals});"), once=True)


def _status_card(icon: str, title: str, goto=None, view: str = ""):
    """Cartão de estado; devolve a coluna onde o chamador escreve o conteúdo."""
    card = ui.card().classes(theme.CARD + " mono-card-hover p-4 gap-2 cursor-pointer"
                             if goto else theme.CARD + " p-4 gap-2")
    with card:
        with ui.row().classes("items-center gap-2 no-wrap w-full"):
            ui.icon(icon).classes("text-sky-400")
            ui.label(title).classes("text-sm font-bold mono-title")
            ui.space()
            if goto:
                ui.icon("north_east").classes("text-xs").style(f"color:{theme.INK_MUTED}")
        body = ui.column().classes("gap-1 w-full")
    if goto:
        card.on("click", lambda: goto(view))
    return body


# Campanhas de treino (nome, horas de parede) — curado à mão, como a _TIMELINE:
# as sessões arquivadas não guardam a duração do treino. Inclui o servidor ISCTE
# e os treinos locais deste PC (rotina noturna + testes, mai–jun; estimativa).
#
# ⚠️ Esta lista tinha ficado em junho: dizia 433 h quando só o mega-treino são
# mais de 600. O cartaz é a primeira coisa que se vê, e subestimava o trabalho
# por um fator de quatro. As horas de julho em diante vêm das datas de arranque e
# fecho registadas nos logs das campanhas (`mega_{A,B}_master.log`) e no
# PLANO_MESTRE — são horas de PAREDE, e as que correram em paralelo somam-se na
# mesma, porque o que se conta é tempo de máquina, não tempo de calendário.
_CAMPANHAS = [
    ("Treinos locais no PC (rotina noturna, mai–jun)", 65),
    ("Treino 24h", 24), ("Treino 48h", 48), ("Treino 24h v2", 24),
    ("Fase B (3 runs)", 45), ("GNN-48h", 48),
    ("Fim-de-semana (recompensa simplificada)", 90),
    ("Validações homing", 4), ("Treino 3 dias (GNN homing)", 68),
    ("Novelty Search (bypass)", 10), ("Re-runs seed 2", 7),
    # julho em diante — as campanhas que sustentam a tese
    ("Campanha final de 7 dias", 168),
    ("Novelty de peso fixo", 30),
    ("Novelty adaptativo (stream A)", 144),
    ("Novelty adaptativo (stream B)", 168),
    ("Mega-treino de 1 mês (stream A)", 317),
    ("Mega-treino de 1 mês (stream B)", 341),
    ("Mapa grande (F0 e F1)", 70),
]

# Linha do tempo do projeto (editar aqui à medida que há marcos novos).
_TIMELINE = [
    ("08 jun", "Acesso aos servidores ISCTE", "Treinos longos passam para a .14 (64 vCPU)."),
    ("09–14 jun", "Treinos 24h e 48h (baseline)", "PPO/SAC convergem; GNN colapsa nos labirintos."),
    ("16–18 jun", "Fase B — 3 runs", "Variância estatística; boxplots reais."),
    ("24–28 jun", "Recompensa simplificada", "Cura o reward hacking do PPO (Muro U 0→100%)."),
    ("28 jun", "Fitness de homing (GNN)", "O GNN come em labirintos pela primeira vez."),
    ("30 jun", "Novelty Search", "Ataque ao ótimo deceptive do bypass."),
    ("01 jul", "Treino de 3 dias fecha", "GNN come nos 7/7 cenários (números de treino)."),
    ("02–09 jul", "Campanha final de 7 dias", "3 algos × 7 cenários × 7 runs = 147 treinos."),
    ("10 jul", "Resultados fechados", "GNN 28/28 runs nos labirintos; Muro U bimodal p/ os 3."),
    ("13 jul", "Revisão sistemática a sério", "883 registos → 58 estudos; só 1 compara os paradigmas."),
    ("18–19 jul", "Novelty adaptativo fecha", "Muro U 7/7 a 100%; bypass @390 = 88,7 — o melhor da tese."),
    ("19 jul", "Mega-treino de 1 mês", "u_wall n=28 nos 4 braços + ablação do anneal (megaA/megaB)."),
    ("24–25 jul", "Mapa grande (8.º cenário)", "Labirinto composto de 103×62 m; pré-registo da QI7."),
    ("27 jul", "Auditoria de física ao mapa", "Enxame amontoado atravessava a porta — corrigido antes de treinar."),
    ("29–30 jul", "Os robôs voavam por cima das paredes",
     "Arena r=60 com paredes de 30 m: 45 m de céu aberto. O F1 é anulado e repetido; "
     "teto de ±2 m tira o incentivo a subir."),
    ("31 jul", "O dashboard sai da torre",
     "Publicado no Raspberry Pi para o orientador; o 3D passa a ser desenhado no browser."),
    ("01–02 ago", "F1 do mapa grande fecha",
     "1680 episódios, 84 de 84 células a 0,00: as três causas alternativas excluídas. "
     "O zero mede transferência (o navegador geodésico faz 53 rec/ep no mesmo mapa)."),
    ("02 ago", "megaA concluído; F2 pronto",
     "5 fases arquivadas. O F2 arranca a 3 ago com 21 runs por algoritmo (emenda 19)."),
    ("03 ago", "Mega-treino fecha — e entra na tese",
     "12 de 12 fases sem falhas. No Muro em U a n=28, a dosagem adaptativa resolve "
     "28/28 execuções contra 15/28 do objetivo puro e 14/28 de cada método de "
     "gradiente (Fisher exato, p<0,0001): a única condição da tese sem uma execução "
     "falhada neste cenário."),
    ("03 ago", "F2 do mapa grande lançado",
     "Os dois streams principais a treinar no 8.º cenário."),
    ("04 ago", "O stream do GNN treinava o braço errado",
     "O script da campanha não escrevia as chaves de novidade no config e o treino "
     "caiu nos defaults — objetivo puro, onde o pré-registo fixa o adaptativo "
     "(w₀=0,5). Pior: o lançador verificava «sem novidade» e certificava o erro. "
     "27 h descartadas; relançado a 4 ago às 22:57 com o braço certo, e o script "
     "passa a escrever, reler e abortar se não bater."),
    ("05 ago", "A primeira recolha que o mapa grande alguma vez deu",
     "Com o braço adaptativo, 4,75 recolhas à geração 140 (era 0,00 em dois runs "
     "completos do objetivo puro, guardados como controlo). O GNN fecha ~16 ago; "
     "o braço exploratório arranca sozinho quando os gradientes largarem a máquina."),
    ("06 ago", "O mapa grande resolve-se num run e não no seguinte",
     "O run que dava 4,75 fechou com 6,00 recolhas; o run 2 fechou a 0,00. É a "
     "bimodalidade do Muro em U outra vez, agora no 8.º cenário — e é por isso "
     "que M1 precisa dos 21 runs: a resposta vai ser uma PROPORÇÃO de execuções "
     "que resolvem, não um «resolve». O estado deixa de ser escrito à mão: "
     "scripts/estado_f2.sh grava um instantâneo datado e as vistas leem-no."),
    ("07–10 ago", "O braço dos gradientes fecha — e fica três dias parado",
     "PPO 21/21 a 7 ago, SAC 21/21 a 10 ago: 840 episódios de avaliação "
     "determinística, 0,00 recolhas em 42 de 42 execuções, a porta cooperativa "
     "nunca aberta. A M3 do pré-registo fica respondida para os gradientes. "
     "Ninguém os trouxe até 13 ago porque o watcher procurava a conclusão no log "
     "do script de shell e não no marcador que o pipeline escreve "
     "(logs/_campanha_concluida.txt): travou por bem, mas a ler o sítio errado."),
    ("13 ago", "A QI7 tem resposta, e é negativa",
     "Com 15 execuções do GNN fechadas e 3 convergentes, faltavam 12 "
     "convergências para as 6 execuções que restavam: o limiar pré-registado de "
     "⌈5/7 × 21⌉ = 15 tornou-se aritmeticamente inalcançável — e como a contagem "
     "do treino é o majorante otimista da avaliação, nem as restantes o salvam. "
     "Reporta-se como negativo, com o número declarado (emenda 21). O braço "
     "exploratório é cancelado: a n=3 não mexe no veredicto e competiria pelo "
     "CPU. Falta o eval_by_run do GNN para saber em quantas execuções, se "
     "alguma, o mapa chega a ser resolvido."),
]


def build(queue: JobQueue, goto=None):
    """Constrói a Overview. `goto(nome_da_vista)` muda de vista (dado pelo app)."""
    sessions = data.list_sessions()
    table = data.science_table()
    eval_t, model_t, stale = data.eval_freshness()

    n_epis = sum(info["n"] for algos in (table or {}).values() for info in algos.values())
    covered = {a: sum(1 for s in (table or {}).values()
                      if a in s and s[a]["ptask"] >= 80.0) for a in config.ALGOS}

    with ui.column().classes("w-full gap-4 p-4"):

        # ── Hero: boids + título da tese ──────────────────────────────────────
        with ui.element("div").classes("w-full fade-up").style(
                "position:relative; min-height:300px; border-radius:16px; overflow:hidden;"
                f"border:1px solid {theme.BORDER}; background:#000;"):
            ui.html('<canvas id="boids" '
                    'style="position:absolute;inset:0;width:100%;height:100%"></canvas>')
            with ui.column().classes("gap-2").style(
                    "position:relative; z-index:1; padding:44px 40px; pointer-events:none;"):
                ui.label("DISSERTAÇÃO DE MESTRADO · INTELIGÊNCIA ARTIFICIAL · ISCTE 2026") \
                    .classes("text-[11px] tracking-[.25em]").style(f"color:{theme.INK_MUTED}")
                ui.label("Aprendizagem por Reforço para Controlo de Enxames") \
                    .classes("mono-title").style(
                        f"font-size:clamp(1.6rem,3.4vw,2.6rem); font-weight:700; "
                        f"line-height:1.15; color:{theme.INK}; max-width:720px;")
                ui.label("Gonçalo Pombo · Orientação: Prof. Luís Nunes") \
                    .classes("text-sm").style(f"color:{theme.INK_SOFT}")
                with ui.row().classes("gap-2 mt-2"):
                    for a in config.ALGOS:
                        c = config.ALGO_META[a]["color"]
                        with ui.row().classes("items-center gap-1 no-wrap px-3 py-1").style(
                                f"border:1px solid {theme.BORDER}; border-radius:999px; "
                                "background:rgba(255,255,255,.03);"):
                            ui.element("div").style(f"width:7px;height:7px;border-radius:50%;"
                                                    f"background:{c}")
                            ui.label(config.ALGO_META[a]["label"]) \
                                .classes("text-xs").style(f"color:{theme.INK_SOFT}")
        ui.timer(0.4, lambda: ui.run_javascript(_BOIDS_JS), once=True)

        # ── KPIs (count-up) ───────────────────────────────────────────────────
        total_h = sum(h for _, h in _CAMPANHAS)
        longest_name, longest_h = max(_CAMPANHAS, key=lambda c: c[1])
        with ui.grid(columns=3).classes("w-full gap-4 fade-up-1"):
            # Só as sessões DATADAS: as pastas curadas (final_7d, adaptativo_*,
            # mega_*) são vistas das campanhas, não treinos que aconteceram — e
            # contá-las fazia o número saltar de 31 para 46 sem ter corrido nada.
            _kpi("Sessões de treino", len(data.historical_sessions()))
            _kpi("Cenários de estudo", len(config.SCENARIO_KEYS))
            _kpi("Episódios avaliados", n_epis)
            # Empate diz-se. O `max` devolvia o primeiro da lista e o cartão
            # anunciava "melhor algo (GNN)" com o PPO na mesma contagem — uma
            # preferência inventada pela ordem do dicionário, num trabalho cuja
            # tese é precisamente que não há domínio de paradigma.
            topo = max(covered.values()) if table else 0
            best = "/".join(a for a in config.ALGOS
                            if covered.get(a) == topo) if table else "—"
            # O denominador é o nº de cenários NA TABELA de avaliação, não o
            # `SCENARIO_KEYS` — que inclui o mapa grande (8.º cenário), ainda sem
            # campanha avaliada. Com /8, o KPI dizia "6/8" quando o universo
            # possível era 7: um cenário que nunca poderia contar aparecia no
            # denominador e fazia a cobertura parecer pior do que é.
            _kpi(f"Cenários ≥80% · melhor algo ({best})", topo,
                 suffix=f"/{len(table) if table else len(config.MAIN_SCENARIO_KEYS)}")
            _kpi("Horas de treino acumuladas (PC + servidor)", total_h, suffix="h")
            _kpi(f"Treino mais longo · {longest_name.lower()}", longest_h, suffix="h")

        # ── Estado ────────────────────────────────────────────────────────────
        # Em modo leitura ficam dois: os cartões «Treino local» e «Servidor
        # ISCTE» apontam para vistas que a cópia publicada não tem — eram dois
        # retângulos clicáveis que não iam a lado nenhum, um deles a anunciar
        # "VPN necessária" a quem está a ver isto pela internet.
        with ui.grid(columns=2 if config.READONLY else 4) \
                .classes("w-full gap-4 fade-up-2"):
            if not config.READONLY:
                with _status_card("rocket_launch", "Treino local", goto, "treinar"):
                    running = queue.is_running
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("div").classes(
                            "live-dot" + ("" if running else " live-dot--idle"))
                        ui.label("a correr" if running else "parado — fila vazia") \
                            .classes("text-sm").style(f"color:{theme.INK_SOFT}")

            with _status_card("fact_check", "Avaliação vs. modelos", goto, "ciencia"):
                if not eval_t:
                    ui.label("sem avaliação local").classes("text-sm") \
                        .style(f"color:{theme.INK_MUTED}")
                else:
                    # Sem modelos no disco (o caso da cópia de leitura no Pi) não
                    # se comparou nada — e dizer "em dia" seria afirmar uma
                    # verificação que não houve.
                    sem_modelos = model_t == 0
                    ok = not stale
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("div").classes(
                            "live-dot " + ("live-dot--ok" if ok and not sem_modelos else ""))
                        ui.label("sem modelos nesta cópia" if sem_modelos
                                 else ("em dia" if ok else "DESFASADA dos modelos")) \
                            .classes("text-sm").style(f"color:{theme.INK_SOFT}")
                    ui.label("eval: " + datetime.fromtimestamp(eval_t).strftime("%d %b %H:%M")) \
                        .classes("text-xs mono-num").style(f"color:{theme.INK_MUTED}")

            with _status_card("history", "Última sessão", goto, "resultados"):
                ui.label(sessions[0] if sessions else "—") \
                    .classes("text-sm mono-num").style(f"color:{theme.INK_SOFT}")
                ui.label(f"{len(data.list_pngs(sessions[0]))} gráficos" if sessions else "") \
                    .classes("text-xs").style(f"color:{theme.INK_MUTED}")

            if not config.READONLY:
                with _status_card("dns", "Servidor ISCTE", goto, "monitorizar"):
                    ui.label("ver painel de monitorização").classes("text-sm") \
                        .style(f"color:{theme.INK_SOFT}")
                    ui.label("VPN necessária").classes("text-xs") \
                        .style(f"color:{theme.INK_MUTED}")

        # ── Linha do tempo ────────────────────────────────────────────────────
        with ui.card().classes(theme.CARD + " p-5 fade-up-3"):
            theme.section_title("timeline", "Linha do tempo do projeto")
            with ui.column().classes("w-full gap-0 mt-2"):
                for i, (when, title, desc) in enumerate(reversed(_TIMELINE)):
                    last = i == len(_TIMELINE) - 1
                    with ui.row().classes("no-wrap items-stretch gap-4 w-full"):
                        with ui.column().classes("items-center gap-0").style("width:14px"):
                            ui.element("div").style(
                                f"width:9px;height:9px;border-radius:50%;margin-top:4px;"
                                f"background:{theme.INK if i == 0 else theme.INK_MUTED};")
                            if not last:
                                ui.element("div").style(
                                    f"width:1px;flex:1;background:{theme.BORDER};")
                        with ui.column().classes("gap-0 pb-4"):
                            with ui.row().classes("items-baseline gap-2 no-wrap"):
                                ui.label(when).classes("text-xs mono-num") \
                                    .style(f"color:{theme.INK_MUTED}; min-width:64px")
                                ui.label(title).classes("text-sm font-bold mono-title") \
                                    .style(f"color:{theme.INK}")
                            ui.label(desc).classes("text-xs ml-[72px]") \
                                .style(f"color:{theme.INK_SOFT}")
