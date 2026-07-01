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
"""

# JS: contador animado (count-up) para os KPIs da Overview.
COUNTUP_JS = r"""
window.monoCountUp = function (el, target, decimals, duration) {
  decimals = decimals || 0; duration = duration || 1200;
  const t0 = performance.now();
  function tick(t) {
    const p = Math.min((t - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);            // ease-out cúbico
    el.textContent = (target * eased).toFixed(decimals);
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
};
"""


def apply():
    """Aplica o tema global (chamar uma vez por página)."""
    ui.dark_mode().enable()
    ui.colors(primary="#fafafa", secondary="#a3a3a3", accent="#f5f5f5", dark="#050505")
    ui.add_head_html(f"<style>{CSS}</style>")
    ui.add_head_html(f"<script>{COUNTUP_JS}</script>")


def section_title(icon: str, text: str, sub: str = ""):
    """Título de secção partilhado (ícone branco + título; subtítulo opcional)."""
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(icon).classes("text-sky-400 text-xl")
        ui.label(text).classes("text-lg font-bold mono-title")
        if sub:
            ui.label(sub).classes("text-xs").style(f"color:{INK_MUTED}")


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
