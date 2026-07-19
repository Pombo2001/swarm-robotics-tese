"""Tema visual do dashboard — monocromático noturno ("preto e branco, modo escuro").

Fonte única de estilo: CSS global + helpers partilhados pelas vistas. Filosofia:
a "casca" (fundos, cartões, tipografia, navegação) é estritamente preto/branco/cinza;
a COR só aparece onde tem significado científico — as séries GNN/PPO/SAC nos
gráficos e os semáforos de estado (verde/âmbar/vermelho).

Tipografia: Space Grotesk (títulos) · Inter (texto) · JetBrains Mono (números/consolas).
"""
from nicegui import ui

# ── Paleta monocromática ──────────────────────────────────────────────────────
BG        = "#050505"   # fundo (quase preto)
SURFACE   = "#0e0e0e"   # cartões
BORDER    = "#1f1f1f"   # linhas finas
INK       = "#f5f5f5"   # títulos / destaque
INK_SOFT  = "#a3a3a3"   # texto corrente
INK_MUTED = "#636363"   # legendas / secundário

# Classe padrão dos cartões (usar em todas as vistas)
CARD = "mono-card w-full"

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:#050505; --surface:#0e0e0e; --surface2:#141414; --border:#1f1f1f;
  --border-hi:#333; --ink:#f5f5f5; --ink-soft:#a3a3a3; --ink-muted:#636363;
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
"""

# JS: contador animado (count-up) para KPIs e células numéricas.
COUNTUP_JS = r"""
window.monoCountUp = function (el, target, decimals, duration, suffix) {
  decimals = decimals || 0; duration = duration || 1200; suffix = suffix || '';
  const t0 = performance.now();
  function tick(t) {
    const p = Math.min((t - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);            // ease-out cúbico
    el.textContent = (target * eased).toFixed(decimals) + suffix;
    if (p < 1) requestAnimationFrame(tick);
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


def apply():
    """Aplica o tema global (chamar uma vez por página)."""
    ui.dark_mode().enable()
    ui.colors(primary="#fafafa", secondary="#a3a3a3", accent="#f5f5f5", dark="#050505")
    ui.add_head_html(f"<style>{CSS}</style>")
    ui.add_head_html(f"<script>{COUNTUP_JS}</script>")
    # Enxame de fundo (atrás de todas as vistas; .q-layout fica com z-index 1).
    ui.add_body_html(
        '<canvas id="boids-bg" style="position:fixed;inset:0;z-index:0;'
        'pointer-events:none"></canvas>')
    ui.timer(0.5, lambda: ui.run_javascript(BG_SWARM_JS), once=True)


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
