"""Vista 'Arquivo' — o registo cronológico das campanhas de treino do projeto.

Mostra TODAS as campanhas datadas (results/graficos_tese/<data>/), da primeira
exploratória à mais recente, com o contexto do que eram. Fica SEPARADA da vista
Resultados de propósito: a maioria destas campanhas é exploratória — só tem gráficos
de treino, e várias chegaram a conclusões que o trabalho posterior refutou (o
"colapso do evolutivo" era artefacto da aptidão, etc.). Guardá-las é transparência
sobre o percurso, não são fonte de números para a tese. Só de leitura: não exporta
para a tese nem lança nada.
"""
import os

from nicegui import ui

from .. import config, data, theme
from .resultados import _pretty_title, _url, TYPE_ORDER, TYPE_ICON

CARD = theme.CARD + " p-4"
_section_title = theme.section_title

_MESES = ["", "jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez"]


def _data_legivel(session: str) -> str:
    dt = data.session_datetime(session)
    if dt is None:
        return session
    return f"{dt.day:02d} {_MESES[dt.month]} {dt.year} · {dt.hour:02d}h{dt.minute:02d}"


def _rotulo(session: str) -> str:
    """Rótulo do seletor: data legível + natureza + nº de gráficos."""
    n = len(data.list_pngs(session))
    natureza = "avaliada" if data.session_is_evaluated(session) else "exploratória"
    return f"{_data_legivel(session)} — {natureza} ({n} gráficos)"


def _zoom(session: str, filename: str):
    with ui.dialog() as dlg, ui.card().classes("max-w-[90vw]"):
        ui.label(f"{_data_legivel(session)}  ·  {filename}") \
            .classes("text-sm font-mono text-gray-300")
        ui.image(_url(session, filename)).classes("max-h-[75vh] object-contain")
        with ui.row().classes("w-full justify-end"):
            ui.button("Fechar", on_click=dlg.close).props("flat")
    dlg.open()


# ── Campanhas CANÓNICAS ──────────────────────────────────────────────────────
# As que sustentam números da dissertação vivem FORA de results/graficos_tese/,
# cada uma na sua pasta, porque nenhuma podia sobrescrever os modelos campeões
# 7d (que continuam a ser os ativos, de propósito — ver a armadilha nº9). O
# resultado colateral era esta vista mostrar 31 campanhas exploratórias e
# nenhuma das quatro que a tese cita. Aqui estão, com o que cada uma produziu.
CANONICAS = [
    ("Campanha final — 7 dias", "graficos_tese/final_7d",
     "3 algoritmos × 7 cenários × 7 execuções × 20 episódios = 2940 episódios",
     "tab:res_eval, tab:res_signif, e a base de tudo o resto"),
    ("Novelty · peso fixo w=0,5", "novelty_final",
     "2 cenários (Muro U, bypass) × 7 execuções, orçamento igualado",
     "QI6 — os 7/7 no Muro U e o custo simétrico no bypass"),
    ("Novelty · dosagem adaptativa", "novelty_adaptativo",
     "5 fases pré-registadas (T1-T4 + controlo de orçamento)",
     "QI6 — a campanha que fechou a tensão do peso fixo"),
    ("Mega-treino de 1 mês", "mega_1mes",
     "12 fases (u_wall a n=28 nos 4 braços + ablações)",
     "replicação da QI6 com 4× o n — A CORRER no servidor"),
    ("Mapa grande — F1", "mapa_grande",
     "zero-shot de topologia: 21 células × 20 episódios por condição",
     "QI7 — por fechar (faltam condições de controlo)"),
]


def _conta(rel):
    """(nº de CSV, nº de PNG) de uma campanha canónica; (0,0) se não existir."""
    raiz = os.path.join(config.BASE_DIR, "results", rel)
    if not os.path.isdir(raiz):
        return 0, 0
    csv = png = 0
    for _, _, fs in os.walk(raiz):
        for f in fs:
            if f.endswith(".csv"):
                csv += 1
            elif f.endswith(".png"):
                png += 1
    return csv, png


def _canonicas():
    """A secção que faltava: o que produziu os números da tese."""
    with ui.card().classes(CARD):
        _section_title("verified", "Campanhas canónicas",
                       "as que sustentam números da dissertação")
        ui.label(
            "Vivem fora de results/graficos_tese/ — cada uma na sua pasta, para "
            "nenhuma sobrescrever os campeões da campanha de 7 dias, que "
            "continuam a ser os modelos ativos. É por isso que não aparecem no "
            "registo cronológico em baixo."
        ).classes("text-xs mb-3").style(f"color:{theme.INK_MUTED}")

        for nome, rel, desenho, produziu in CANONICAS:
            csv, png = _conta(rel)
            existe = csv or png
            with ui.row().classes("w-full gap-3 no-wrap items-start py-2 "
                                  "border-t border-white/5"):
                ui.element("div").style(
                    "width:8px;height:8px;border-radius:50%%;margin-top:6px;"
                    "flex:none;background:%s"
                    % ("#4ade80" if existe else theme.INK_MUTED))
                with ui.column().classes("gap-0 grow"):
                    ui.label(nome).classes("text-sm font-bold")
                    ui.label(desenho).classes("text-xs") \
                        .style(f"color:{theme.INK_MUTED}")
                    ui.label("→ " + produziu).classes("text-xs mt-1")
                with ui.column().classes("gap-0 items-end shrink-0"):
                    ui.label("results/" + rel).classes("text-[11px] mono-num") \
                        .style(f"color:{theme.INK_MUTED}")
                    ui.label(("%d CSV · %d gráficos" % (csv, png)) if existe
                             else "não está neste disco") \
                        .classes("text-[11px] mono-num") \
                        .style(f"color:{theme.INK_MUTED}")


def build():
    campanhas = data.historical_sessions()

    with ui.column().classes("w-full gap-4 p-4"):
        _canonicas()

        # ── Contexto: o que é este arquivo ───────────────────────────────────
        with ui.card().classes(CARD):
            _section_title("history_edu", "Arquivo de campanhas — o percurso do projeto")
            if campanhas:
                primeira = data.session_datetime(campanhas[0])
                ultima = data.session_datetime(campanhas[-1])
                n_expl = sum(1 for s in campanhas if not data.session_is_evaluated(s))
                periodo = (f"{_MESES[primeira.month]} a {_MESES[ultima.month]} de "
                           f"{ultima.year}")
                ui.label(f"{len(campanhas)} campanhas de treino, de {periodo}. "
                         f"As primeiras {n_expl} são exploratórias.") \
                    .classes("text-sm text-gray-300 mt-1")
            ui.markdown(
                "Estas foram **as primeiras campanhas do projeto** — a fase de "
                "exploração em que se afinaram os cenários, as recompensas e o "
                "desenho da aptidão do algoritmo evolutivo. **Não são a fonte dos "
                "números da tese**, e ao lê-las convém saber que:\n\n"
                "- A maioria só guarda **gráficos de treino** (curvas de "
                "recompensa/aptidão), não a avaliação determinística de 20 episódios "
                "que a dissertação usa como veredicto.\n"
                "- Várias chegaram a conclusões que o trabalho posterior **refutou** "
                "— nomeadamente o \"colapso do evolutivo\", que se veio a mostrar ser "
                "um artefacto do desenho da aptidão (curado pela aptidão de homing).\n"
                "- Ficam aqui por **transparência do percurso**. Os resultados "
                "canónicos vivem na vista **Ciência** e na comparação da vista "
                "**Resultados**.\n\n"
                "As campanhas marcadas *avaliada* (a partir de julho) já têm avaliação "
                "determinística ou modelos arquivados; as *exploratórias* não.") \
                .classes("text-sm text-gray-400 mt-1 leading-relaxed")

        if not campanhas:
            with ui.card().classes(CARD):
                ui.label("Sem campanhas datadas em results/graficos_tese/.") \
                    .classes("text-gray-500")
            return

        # ── Seletor da campanha (cronológico, a primeira por defeito) ─────────
        opcoes = {s: _rotulo(s) for s in campanhas}
        with ui.card().classes(CARD):
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                ui.icon("event").classes("text-sky-400")
                sel = ui.select(opcoes, value=campanhas[0], label="Campanha") \
                    .props("outlined dense").classes("flex-1")

        painel = ui.column().classes("w-full gap-4")

        @ui.refreshable
        def mostrar():
            session = sel.value
            avaliada = data.session_is_evaluated(session)
            pngs = data.list_pngs(session)

            with ui.card().classes(CARD):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.label(_data_legivel(session)).classes("text-lg font-bold")
                    cor = "positive" if avaliada else "grey"
                    ui.badge("avaliada" if avaliada else "exploratória", color=cor) \
                        .props("rounded")
                    ui.badge(f"{len(pngs)} gráficos", color="primary").props("rounded")
                    ui.space()
                    ui.label(session).classes("text-xs font-mono text-gray-600")
                manifesto = data.session_manifesto(session)
                if manifesto:
                    with ui.expansion("Manifesto da campanha (artefactos gerados)",
                                      icon="description").classes("w-full mt-1"):
                        ui.markdown(manifesto).classes("text-xs")

            if not pngs:
                with ui.card().classes(CARD):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("image_not_supported").classes("text-gray-600")
                        ui.label("Esta campanha não guardou gráficos.") \
                            .classes("text-gray-500")
                return

            # Galeria só de leitura, agrupada por tipo (mesma taxonomia de Resultados).
            grupos = {}
            for f in pngs:
                grupos.setdefault(data.graph_type(f), []).append(f)
            ordem = [t for t in TYPE_ORDER if t in grupos] + \
                    [t for t in grupos if t not in TYPE_ORDER]
            with ui.card().classes(CARD):
                _section_title("photo_library", "Gráficos da campanha")
                for tname in ordem:
                    files = grupos[tname]
                    with ui.row().classes("items-center gap-2 w-full mt-3 mb-1"):
                        ui.icon(TYPE_ICON.get(tname, "image")).classes("text-sky-400 text-xl")
                        ui.label(tname).classes("text-base font-bold")
                        ui.badge(str(len(files)), color="primary").props("rounded")
                    ui.separator().classes("opacity-30")
                    with ui.grid().classes("w-full gap-3").style(
                            "grid-template-columns: repeat(3, minmax(0, 1fr))"):
                        for f in files:
                            with ui.card().classes("bg-slate-900/50 rounded-lg p-2"):
                                ui.label(_pretty_title(f)) \
                                    .classes("text-sm font-semibold text-sky-200")
                                ui.label(f).classes("text-[10px] font-mono text-gray-500 truncate")
                                ui.image(_url(session, f)) \
                                    .classes("w-full cursor-pointer") \
                                    .on("click", lambda _, s=session, f=f: _zoom(s, f))

        sel.on_value_change(lambda: mostrar.refresh())
        with painel:
            mostrar()
