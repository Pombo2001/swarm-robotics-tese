"""Tema visual do dashboard — monocromático noturno ("preto e branco, modo escuro").

Fonte única de estilo: CSS global + helpers partilhados pelas vistas. Filosofia:
a "casca" (fundos, cartões, tipografia, navegação) é estritamente preto/branco/cinza;
a COR só aparece onde tem significado científico — as séries GNN/PPO/SAC nos
gráficos e os semáforos de estado (verde/âmbar/vermelho).

Tipografia: Space Grotesk (títulos) · Inter (texto) · JetBrains Mono (números/consolas).
"""
from nicegui import core, ui

# ── Paleta monocromática ──────────────────────────────────────────────────────
BG        = "#050505"   # fundo (quase preto)
SURFACE   = "#0e0e0e"   # cartões
BORDER    = "#1f1f1f"   # linhas finas
INK       = "#f5f5f5"   # títulos / destaque
INK_SOFT  = "#a3a3a3"   # texto corrente          — 8,0:1 sobre o fundo (AAA)
# Legendas/secundário. Estava #636363, que dá 3,5:1 sobre #050505 e reprova o
# mínimo de 4,5:1 do WCAG AA para texto pequeno — e é precisamente aqui que vivem
# os rótulos dos indicadores ("SESSÕES DE TREINO"), as datas da linha do tempo e
# as legendas dos cartões, todos a 11-12 px em maiúsculas. #7d7d7d dá 4,9:1 e
# mantém a distância para o texto corrente (4,9 vs 8,0), que é o que sustenta a
# hierarquia visual. O modo defesa continua a subi-lo mais (projetores achatam
# os pretos) — ver a secção body.defesa.
INK_MUTED = "#7d7d7d"   # legendas / secundário   — 4,9:1 sobre o fundo (AA)

# Classe padrão dos cartões (usar em todas as vistas)
CARD = "mono-card w-full"

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:#050505; --surface:#0e0e0e; --surface2:#141414; --border:#1f1f1f;
  --border-hi:#333; --ink:#f5f5f5; --ink-soft:#a3a3a3; --ink-muted:#7d7d7d;
}

html, body, .q-page, .nicegui-content {
  font-family:'Inter',-apple-system,'Segoe UI',sans-serif !important;
  letter-spacing:.1px;
}
body {
  background:
    radial-gradient(1200px 600px at 50% -20%, rgba(255,255,255,.045), transparent 60%),
    var(--bg) !important;
  background-attachment:fixed !important;
  color:var(--ink-soft);
}
h1,h2,h3,.font-extrabold,.font-bold,.q-tab__label,.mono-title {
  font-family:'Space Grotesk','Inter',sans-serif !important;
}
.mono-num, .q-badge, code, pre, .mono-console {
  font-family:'JetBrains Mono',monospace !important;
  font-variant-numeric:tabular-nums;
}

/* ── Cartões ──────────────────────────────────────────────────────────────── */
.mono-card, .q-card {
  background:var(--surface) !important;
  border:1px solid var(--border) !important;
  border-radius:14px !important;
  box-shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 12px 32px rgba(0,0,0,.45) !important;
  transition:border-color .25s ease, transform .25s ease;
}
.q-card:hover { border-color:var(--border-hi) !important; }
.mono-card-hover:hover { transform:translateY(-3px); }

/* Neutralizar os fundos "slate" antigos das vistas (rede de segurança) */
[class*="bg-slate-800"], [class*="bg-slate-900"], [class*="bg-slate-700"] {
  background:var(--surface) !important;
  border:1px solid var(--border);
}
.text-sky-400 { color:var(--ink) !important; }   /* ícones de secção → branco */

/* ── Casca: header e navegação ───────────────────────────────────────────── */
.q-header {
  background:rgba(5,5,5,.75) !important;
  border-bottom:1px solid var(--border) !important;
  backdrop-filter:blur(12px);
}
.q-drawer {
  background:rgba(8,8,8,.92) !important;
  border-right:1px solid var(--border) !important;
}
.q-tab { text-transform:none !important; font-weight:600; letter-spacing:.2px;
  justify-content:flex-start; border-radius:10px; min-height:44px;
  color:var(--ink-muted); transition:color .2s ease, background .2s ease; }
.q-tab__content { align-items:flex-start; }
.q-tab--active { color:var(--ink) !important; background:rgba(255,255,255,.06); }
.q-tab:hover { background:rgba(255,255,255,.04); color:var(--ink-soft); }
.q-tab__indicator { background:var(--ink) !important; width:2px !important; }

/* Botões primários: branco sobre preto (estilo editorial) */
.q-btn.bg-primary, .q-btn.bg-primary .q-icon, .q-btn.bg-primary .q-btn__content {
  color:#0a0a0a !important; font-weight:600; }
.q-btn { text-transform:none !important; border-radius:10px; letter-spacing:.2px; }
.q-field--outlined .q-field__control { border-radius:10px; }

/* ── Animações ───────────────────────────────────────────────────────────── */
@keyframes fadeUp { from { opacity:0; transform:translateY(10px); }
                    to   { opacity:1; transform:none; } }
.fade-up   { animation:fadeUp .5s ease both; }
.fade-up-1 { animation:fadeUp .5s .08s ease both; }
.fade-up-2 { animation:fadeUp .5s .16s ease both; }
.fade-up-3 { animation:fadeUp .5s .24s ease both; }

/* Entrada em cascata ao trocar de vista: os filhos diretos de cada painel
   sobem em sequência (o efeito da Overview, agora em toda a app). */
.q-tab-panel > * { animation:fadeUp .45s ease both; }
.q-tab-panel > *:nth-child(2) { animation-delay:.06s; }
.q-tab-panel > *:nth-child(3) { animation-delay:.12s; }
.q-tab-panel > *:nth-child(4) { animation-delay:.18s; }
.q-tab-panel > *:nth-child(5) { animation-delay:.24s; }
.q-tab-panel > *:nth-child(n+6) { animation-delay:.30s; }

/* Navegação viva: deslize no hover, brilho no separador ativo. */
.q-tab { transition:color .2s ease, background .2s ease, transform .18s ease; }
.q-tab:hover { transform:translateX(3px); }
.q-tab--active .q-icon { filter:drop-shadow(0 0 7px rgba(255,255,255,.45)); }

/* Botões com "pressão" física. */
.q-btn { transition:transform .12s ease, opacity .2s ease; }
.q-btn:active { transform:scale(.96); }

/* Rotação lenta (ícone do header enquanto há treino a correr). */
@keyframes spinSlow { to { transform:rotate(360deg); } }
.spin-slow { animation:spinSlow 9s linear infinite; }

/* O conteúdo da app fica acima do enxame de fundo (canvas fixo, z-index 0). */
.q-layout { position:relative; z-index:1; }

@keyframes pulseDot { 0%,100% { opacity:1; box-shadow:0 0 0 0 rgba(255,255,255,.35); }
                      50% { opacity:.55; box-shadow:0 0 0 5px rgba(255,255,255,0); } }
.live-dot { width:8px; height:8px; border-radius:50%; background:var(--ink);
  animation:pulseDot 1.8s ease-in-out infinite; }
.live-dot--ok    { background:#34d399; }
.live-dot--idle  { background:var(--ink-muted); animation:none; }

.vid-card { transition:transform .18s ease, box-shadow .18s ease; }
.vid-card:hover { transform:translateY(-4px); box-shadow:0 14px 34px rgba(0,0,0,.6); }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#222; border-radius:8px;
  border:2px solid transparent; background-clip:padding-box; }
::-webkit-scrollbar-thumb:hover { background:#3a3a3a; background-clip:padding-box; }

/* Separadores e tabelas discretos */
.q-separator { background:var(--border) !important; }
.q-table, .q-table__container { background:transparent !important; }

/* ── Acabamento fino (passagem de 19 jul) ────────────────────────────────── */

/* Linha de luz no topo de cada cartão — o toque editorial. */
.q-card { position:relative; overflow:hidden; }
.q-card::before {
  content:''; position:absolute; left:0; right:0; top:0; height:1px;
  background:linear-gradient(90deg, transparent 4%, rgba(255,255,255,.16) 50%, transparent 96%);
  pointer-events:none;
}

/* Header com a mesma linha de luz em vez de um risco chapado. */
.q-header::after {
  content:''; position:absolute; left:0; right:0; bottom:-1px; height:1px;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.28), transparent);
  pointer-events:none;
}

/* Tabelas: cabeçalho tipográfico, linhas quase invisíveis, hover suave. */
.q-table thead th {
  color:var(--ink-muted) !important; text-transform:uppercase; font-size:11px;
  letter-spacing:.8px; font-weight:600; border-color:var(--border) !important;
}
.q-table tbody td { border-color:#161616 !important; }
.q-table tbody tr { transition:background .15s ease; }
.q-table tbody tr:hover { background:rgba(255,255,255,.035); }

/* Tooltips e menus a condizer com a casca (por defeito vinham claros). */
.q-tooltip {
  background:#111 !important; color:var(--ink) !important;
  border:1px solid #2a2a2a; border-radius:8px; font-size:12px; letter-spacing:.2px;
}
.q-menu {
  background:var(--surface2) !important; border:1px solid var(--border-hi) !important;
  border-radius:12px !important; box-shadow:0 18px 44px rgba(0,0,0,.6) !important;
}

/* Badges, barras de progresso e campos: cantos e pesos coerentes. */
.q-badge { border-radius:6px; font-weight:600; letter-spacing:.3px; }
/* Badges de fundo claro (primary/accent são quase-brancos): texto escuro, senão
   ficava branco sobre branco e ilegível (ex.: o "16 gráficos" do Arquivo). */
.q-badge.bg-primary, .q-badge.bg-accent { color:#0a0a0a !important; }
.q-linear-progress { border-radius:6px; overflow:hidden; }
.q-field--outlined .q-field__control:hover:before { border-color:var(--border-hi) !important; }

/* Números-herói (opt-in): gradiente branco→cinza, para KPIs grandes. */
.mono-num-hero {
  background:linear-gradient(180deg,#ffffff 20%,#8f8f8f);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}

/* Micro-detalhes: seleção, foco acessível, scroll suave. */
::selection { background:rgba(255,255,255,.22); color:#fff; }
:focus-visible { outline:1px solid rgba(255,255,255,.45); outline-offset:2px; border-radius:4px; }
html { scroll-behavior:smooth; }

/* ══ MODO DEFESA ═══════════════════════════════════════════════════════════
   Um ecrã bonito ao pé do nariz não é um ecrã legível projetado numa sala.
   Este modo trata das três coisas que um videoprojetor estraga:

   1. TAMANHO — o texto de 10-12px (rodapés de fonte, rótulos de eixo, chips de
      estado) é ilegível a partir da terceira fila. Sobe tudo com um piso.
   2. CONTRASTE — os projetores achatam os pretos: #636363 sobre #050505 lê-se
      no portátil e desaparece na parede. O cinza sobe, as bordas dos cartões
      passam a ver-se, e o fundo fica preto CHAPADO (o gradiente de topo vira
      uma mancha suja quando a lâmpada está gasta).
   3. MOVIMENTO — o enxame de fundo e as entradas em cascata distraem quem está
      a ouvir e comem CPU enquanto se fala. Ficam parados.

   Não é um tema novo: é o mesmo, com os parâmetros corrigidos para a sala.
   Liga-se no botão do cabeçalho e fica gravado no browser (localStorage), para
   sobreviver a um F5 a meio da defesa.                                        */
body.defesa {
  --ink-soft:#e2e2e2; --ink-muted:#9a9a9a; --border:#2e2e2e; --border-hi:#4a4a4a;
  background:#000 !important;             /* sem gradiente: projetor não o rende */
  font-size:118%;
}
body.defesa .text-xs,
body.defesa .text-\[11px\],
body.defesa .text-\[10px\] { font-size:14px !important; line-height:1.45 !important; }
body.defesa .text-sm  { font-size:15.5px !important; }
body.defesa .text-lg  { font-size:22px !important; }
body.defesa .text-xl  { font-size:26px !important; }
body.defesa .text-2xl { font-size:32px !important; }
body.defesa .text-3xl { font-size:42px !important; }
body.defesa .text-4xl { font-size:54px !important; }
/* Maiúsculas espaçadas (rótulos de secção) tornam-se ilegíveis em pequeno. */
body.defesa .tracking-\[\.2em\] { font-size:13px !important; letter-spacing:.16em !important; }
/* Cartões com aresta visível: na parede, 1px a #1f1f1f não existe. */
body.defesa .mono-card, body.defesa .q-card { border-color:#2e2e2e !important; }
/* Tabelas: cabeçalhos e células maiores, para ler de longe. */
body.defesa .q-table thead th { font-size:13px !important; letter-spacing:.6px; }
body.defesa .q-table tbody td { font-size:15px !important; }
/* Sossego: sem enxame de fundo, sem entradas em cascata, sem brilhos. */
body.defesa #boids-bg { display:none !important; }
body.defesa .fade-up, body.defesa .fade-up-1, body.defesa .fade-up-2,
body.defesa .fade-up-3, body.defesa .q-tab-panel > * { animation:none !important; }
body.defesa .spin-slow { animation:none !important; }
body.defesa .q-tab:hover { transform:none; }
body.defesa .live-dot { animation:none !important; }
/* O botão do modo assinala-se a si próprio quando está ligado. */
body.defesa .defesa-btn { background:rgba(255,255,255,.14) !important; }
/* Fora o ruído de operação: numa defesa ninguém quer saber do porto local. */
body.defesa .op-footer { display:none !important; }

/* Quem tiver "reduzir movimento" no sistema recebe o mesmo sossego, sempre. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; animation-iteration-count:1 !important;
                           transition-duration:.01ms !important; scroll-behavior:auto !important; }
  #boids-bg { display:none !important; }
}
"""

# JS: contador animado (count-up) para KPIs e células numéricas.
COUNTUP_JS = r"""
window.monoCountUp = function (el, target, decimals, duration, suffix) {
  decimals = decimals || 0; duration = duration || 1200; suffix = suffix || '';
  const fim = function () { el.textContent = target.toFixed(decimals) + suffix; };
  // ⚠️ O requestAnimationFrame NÃO corre em separadores em segundo plano: quem
  // abrisse o dashboard num separador que não está à frente (ou o deixasse a
  // carregar enquanto trabalha noutro) via os seis KPIs a **zero** até voltar —
  // e um número parado em zero lê-se como resultado, não como animação por
  // começar. Com a página oculta escreve-se já o valor final; a animação fica
  // para quando (e se) o separador aparecer.
  if (document.hidden) {
    fim();
    document.addEventListener('visibilitychange', function uma() {
      document.removeEventListener('visibilitychange', uma);
      if (!document.hidden) window.monoCountUp(el, target, decimals, duration, suffix);
    });
    return;
  }
  const t0 = performance.now();
  function tick(t) {
    const p = Math.min((t - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);            // ease-out cúbico
    el.textContent = (target * eased).toFixed(decimals) + suffix;
    if (p < 1) requestAnimationFrame(tick); else fim();
  }
  requestAnimationFrame(tick);
};
"""

# JS: enxame de fundo — a assinatura visual da Overview espalhada pela app.
# Versão MUITO subtil dos boids do hero (menos pontos, opacidade baixa, canvas
# fixo atrás de todo o conteúdo); pausa quando o separador do browser está oculto.
BG_SWARM_JS = r"""
(function () {
  const cv = document.getElementById('boids-bg');
  if (!cv || cv.dataset.running) return;
  cv.dataset.running = '1';
  const ctx = cv.getContext('2d');
  let W, H;
  function resize() { W = cv.width = innerWidth; H = cv.height = innerHeight; }
  resize(); window.addEventListener('resize', resize);

  const N = 44, VIEW = 80, SPEED = .55;
  const boids = Array.from({length: N}, () => ({
    x: Math.random() * innerWidth, y: Math.random() * innerHeight,
    vx: (Math.random() - .5), vy: (Math.random() - .5),
  }));

  function frame() {
    if (!document.getElementById('boids-bg')) return;   // página morreu
    if (document.hidden) { setTimeout(frame, 400); return; }
    for (const b of boids) {
      let cx = 0, cy = 0, ax = 0, ay = 0, sx = 0, sy = 0, n = 0;
      for (const o of boids) {
        if (o === b) continue;
        const dx = o.x - b.x, dy = o.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 < VIEW * VIEW) {
          cx += o.x; cy += o.y; ax += o.vx; ay += o.vy; n++;
          if (d2 < 600) { sx -= dx; sy -= dy; }
        }
      }
      if (n) {
        b.vx += ((cx / n - b.x) * .0012) + ((ax / n - b.vx) * .04) + sx * .003;
        b.vy += ((cy / n - b.y) * .0012) + ((ay / n - b.vy) * .04) + sy * .003;
      }
      const v = Math.hypot(b.vx, b.vy) || 1;
      b.vx = b.vx / v * SPEED; b.vy = b.vy / v * SPEED;
      b.x += b.vx; b.y += b.vy;
      if (b.x < -10) b.x = W + 10;  if (b.x > W + 10) b.x = -10;
      if (b.y < -10) b.y = H + 10;  if (b.y > H + 10) b.y = -10;
    }
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(255,255,255,.035)';
    for (let i = 0; i < boids.length; i++)
      for (let j = i + 1; j < boids.length; j++) {
        const a = boids[i], b = boids[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        if (dx * dx + dy * dy < 4900) {
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    ctx.fillStyle = 'rgba(255,255,255,.28)';
    for (const b of boids) { ctx.beginPath(); ctx.arc(b.x, b.y, 1.3, 0, 7); ctx.fill(); }
    requestAnimationFrame(frame);
  }
  frame();
})();
"""


def js_diferido(js: str, atraso_s: float = 0.3):
    """Corre `js` no browser daqui a `atraso_s`, SEM timer do lado do servidor.

    Estas esperas são todas cosméticas: dar tempo a que o elemento exista no DOM
    e a que o JS do tema esteja carregado. Feitas com `ui.timer(..., once=True)`
    ficavam a dormir no servidor, e fechar o separador a meio da espera fazia o
    `_cleanup()` do NiceGUI ir buscar um `parent_slot` já apagado — cerca de
    trinta tracebacks «The parent slot of the element has been deleted» na
    consola de cada vez que se fechava a página. Não é evitável do lado do
    callback (rebenta ao SAIR do `with`, depois de o callback ser saltado).
    A espera passa para o `setTimeout` do browser, onde não há slot nenhum para
    apagar; o `run_javascript` fica em fila até o cliente ligar.

    Sem servidor a correr — a auditoria `auditar_dashboard.py` e os testes
    constroem as vistas sem levantar o NiceGUI — não há sequer ciclo de eventos,
    e o `ui.run_javascript` rebenta numa `assert core.loop is not None`. O
    `ui.timer` que aqui estava adiava-se sozinho nesse caso; isto tem de o
    dizer à mão, senão «arranjar o log» partia a construção de duas vistas.
    """
    if core.loop is None:
        return
    ui.run_javascript("setTimeout(function(){%s}, %d);"
                      % (js, int(atraso_s * 1000)))


def apply():
    """Aplica o tema global (chamar uma vez por página)."""
    ui.dark_mode().enable()
    ui.colors(primary="#fafafa", secondary="#a3a3a3", accent="#f5f5f5", dark="#050505")
    ui.add_head_html(f"<style>{CSS}</style>")
    ui.add_head_html(f"<script>{COUNTUP_JS}</script>")
    # No <body>, não no <head>: o script repõe o Modo Defesa gravado e precisa
    # que document.body já exista quando corre.
    ui.add_body_html(f"<script>{DEFESA_JS}</script>")
    # Enxame de fundo (atrás de todas as vistas; .q-layout fica com z-index 1).
    ui.add_body_html(
        '<canvas id="boids-bg" style="position:fixed;inset:0;z-index:0;'
        'pointer-events:none"></canvas>')
    js_diferido(BG_SWARM_JS, 0.5)


def section_title(icon: str, text: str, sub: str = ""):
    """Título de secção partilhado (ícone branco + título; subtítulo opcional)."""
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(icon).classes("text-sky-400 text-xl")
        ui.label(text).classes("text-lg font-bold mono-title")
        if sub:
            ui.label(sub).classes("text-xs").style(f"color:{INK_MUTED}")


def fonte(texto: str, aviso: bool = False):
    """Rodapé de proveniência: DE ONDE vêm os dados desta vista e DE QUANDO são.

    Toda a vista que mostre números ou imagens deve declarar a sua fonte. Sem isto o
    dashboard não distingue "não existe" de "não está aqui" — e foi assim que uma
    sessão antiga passou por recente, e curvas de há semanas passaram por "ao vivo".
    Devolve o ui.label para poder ser atualizado dinamicamente.
    """
    lbl = ui.label(("⚠ " if aviso else "fonte: ") + texto).classes("text-xs mt-1")
    lbl.style(f"color:{'#d97706' if aviso else INK_MUTED}")
    return lbl


# Base ECharts monocromática (eixos/grelha/tooltip) — as séries mantêm as cores
# por algoritmo (significado científico).
ECHART_BASE = {
    "textStyle": {"fontFamily": "Inter"},
    "axisLabelColor": INK_MUTED,
    "splitLineColor": "#191919",
    "tooltip": {
        "backgroundColor": "#111",
        "borderColor": "#2a2a2a",
        "textStyle": {"color": INK},
    },
}

# ── Cromo dos gráficos (eixos, grelha, legenda, tooltip) ─────────────────────
# Os ECharts das vistas tinham as cores do tema ANTIGO cravadas à mão (o azul
# "slate" #94a3b8/#cbd5e1, de antes da passagem monocromática): o dashboard era
# preto e branco e os gráficos continuavam azulados, e mudar o tema não lhes
# tocava. Passa tudo por aqui.
#
# Os tamanhos de letra são deliberadamente generosos (12-13px, não os 10-11px
# por omissão do ECharts): o mesmo gráfico tem de servir o portátil e a parede,
# e o Modo Defesa não consegue reescalar texto desenhado dentro de um <canvas>.
GRID_LINE = "rgba(255,255,255,.08)"
AXIS_LINE = "rgba(255,255,255,.18)"


def echart_chrome(*, y_nome: str = "", rotacao_x: int = 0) -> dict:
    """Eixos/grelha/legenda/tooltip coerentes com o tema, para juntar à opção.

    Uso: `{**theme.echart_chrome(y_nome="Retenção (%)"), "series": [...]}`.
    """
    rotulo = {"color": INK_MUTED, "fontSize": 12, "fontFamily": "Inter"}
    return {
        "textStyle": {"fontFamily": "Inter", "fontSize": 12},
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(12,12,12,.96)",
            "borderColor": "#2a2a2a",
            "textStyle": {"color": INK, "fontSize": 13},
            "axisPointer": {"lineStyle": {"color": AXIS_LINE}},
        },
        "legend": {
            "top": 0, "itemGap": 18, "icon": "roundRect",
            "itemWidth": 14, "itemHeight": 10,
            # A legenda está SEMPRE presente com ≥2 séries: a identidade da série
            # nunca pode depender só da cor (regra de acessibilidade).
            "textStyle": {"color": INK_SOFT, "fontSize": 13, "fontFamily": "Inter"},
        },
        "grid": {"left": 56, "right": 20, "top": 40, "bottom": 68},
        "xAxis": {
            "type": "category",
            "axisLabel": {**rotulo, "rotate": rotacao_x},
            "axisLine": {"lineStyle": {"color": AXIS_LINE}},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "name": y_nome,
            "nameTextStyle": {"color": INK_MUTED, "fontSize": 12, "padding": [0, 0, 0, 6]},
            "axisLabel": rotulo,
            "axisLine": {"show": False},
            "splitLine": {"lineStyle": {"color": GRID_LINE}},
        },
    }


# JS do Modo Defesa: alterna a classe no <body> e grava a escolha no browser,
# para um F5 a meio da apresentação não desligar o modo.
DEFESA_JS = r"""
window.monoDefesa = function (ligar) {
  const b = document.body;
  if (ligar === undefined) ligar = !b.classList.contains('defesa');
  b.classList.toggle('defesa', ligar);
  try { localStorage.setItem('swarm-defesa', ligar ? '1' : '0'); } catch (e) {}
  window.dispatchEvent(new Event('resize'));   // ECharts re-mede o contentor
  return ligar;
};
(function () {
  try {
    if (localStorage.getItem('swarm-defesa') === '1') document.body.classList.add('defesa');
  } catch (e) {}
})();
"""


def num(valor, casas: int = 1, sinal: bool = False) -> str:
    """Um número como o resto do projeto o escreve: com **vírgula**.

    A dissertação é PT-PT e escreve `38,3`; o dashboard escrevia `38.3` em
    quinze sítios e `38,3` noutros tantos — às vezes na mesma linha («δ = +0.77»
    debaixo de «δ = +0,61»). Não é um erro de valor, é um ecrã que se lê a duas
    velocidades, e num que vai ser projetado numa defesa isso conta.

    Devolve «—» para `None`/`NaN`, que é o que as tabelas já mostravam nos
    buracos.
    """
    if valor is None:
        return "—"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    if v != v:                                   # NaN
        return "—"
    fmt = "%+." + str(casas) + "f" if sinal else "%." + str(casas) + "f"
    return (fmt % v).replace(".", ",")


def defesa_button():
    """Botão do Modo Defesa (usar no header). Devolve o ui.button."""
    b = ui.button(icon="present_to_all",
                  on_click=lambda: ui.run_javascript("window.monoDefesa()")) \
        .props("flat round dense color=white").classes("defesa-btn")
    b.tooltip("Modo Defesa — texto maior, mais contraste e sem animações, "
              "para projetar numa sala")
    return b
