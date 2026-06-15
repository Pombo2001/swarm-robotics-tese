"""Vista 'Resultados' (F3): galeria de gráficos com filtros, comparação A/B e
exportação direta para a tese.

As imagens são servidas pela rota estática '/graficos' (registada em app.py).
"""
from nicegui import ui

from .. import data

CARD = "bg-slate-800/70 rounded-xl shadow-lg p-4 w-full"
NONE = "— (sem comparação)"


def _section_title(icon: str, text: str):
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(icon).classes("text-sky-400 text-xl")
        ui.label(text).classes("text-lg font-bold")


def _url(session: str, filename: str) -> str:
    return f"/graficos/{session}/{filename}"


def build():
    sessions = data.list_sessions()

    def open_zoom(session: str, filename: str):
        with ui.dialog() as dlg, ui.card().classes("max-w-[90vw]"):
            ui.label(filename).classes("text-sm font-mono text-gray-300")
            ui.image(_url(session, filename)).classes("max-h-[75vh] object-contain")
            with ui.row().classes("w-full justify-end gap-2"):
                def enviar():
                    ok, msg = data.send_to_thesis(session, filename)
                    ui.notify(f"Enviado para a tese: {msg}" if ok else f"Falhou: {msg}",
                              type="positive" if ok else "negative")
                ui.button("Enviar para a Tese", icon="upload_file", on_click=enviar) \
                    .props("color=secondary")
                ui.button("Fechar", on_click=dlg.close).props("flat")
        dlg.open()

    if not sessions:
        with ui.column().classes("w-full items-center py-10 gap-2"):
            ui.icon("image_not_supported").classes("text-5xl text-gray-600")
            ui.label("Sem sessões em results/graficos_tese/.").classes("text-gray-500")
        return

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.card().classes(CARD):
            _section_title("photo_library", "Galeria de resultados")
            with ui.row().classes("w-full gap-2 no-wrap items-center mt-1"):
                sess_a = ui.select(sessions, value=sessions[0], label="Sessão A") \
                    .props("outlined dense").classes("flex-1")
                sess_b = ui.select([NONE] + sessions, value=NONE, label="Sessão B (A/B)") \
                    .props("outlined dense").classes("flex-1")
                tipos = ["Todos"] + sorted({data.graph_type(f) for f in data.list_pngs(sessions[0])})
                tipo = ui.select(tipos, value="Todos", label="Tipo") \
                    .props("outlined dense").classes("flex-1")

        @ui.refreshable
        def galeria():
            pngs = [f for f in data.list_pngs(sess_a.value)
                    if tipo.value == "Todos" or data.graph_type(f) == tipo.value]
            if not pngs:
                ui.label("Nenhum gráfico para este filtro.").classes("text-gray-500")
                return
            comparar = sess_b.value != NONE
            pngs_b = set(data.list_pngs(sess_b.value)) if comparar else set()
            with ui.grid().classes("w-full gap-3").style(
                    f"grid-template-columns: repeat({'1' if comparar else '3'}, minmax(0, 1fr))"):
                for f in pngs:
                    with ui.card().classes("bg-slate-900/50 rounded-lg p-2"):
                        ui.label(f).classes("text-xs font-mono text-gray-400 truncate")
                        if comparar:
                            with ui.row().classes("w-full gap-2 no-wrap"):
                                for s, tag in ((sess_a.value, "A"), (sess_b.value, "B")):
                                    with ui.column().classes("flex-1 gap-0 items-center"):
                                        ui.badge(f"{tag} · {s}", color="primary").props("rounded").classes("text-[10px]")
                                        # o ficheiro pode não existir na sessão B
                                        if tag == "B" and f not in pngs_b:
                                            ui.label("(não existe nesta sessão)") \
                                                .classes("text-xs text-gray-600 italic py-4")
                                        else:
                                            ui.image(_url(s, f)).classes("w-full cursor-pointer") \
                                                .on("click", lambda _, s=s, f=f: open_zoom(s, f))
                        else:
                            ui.image(_url(sess_a.value, f)).classes("w-full cursor-pointer") \
                                .on("click", lambda _, f=f: open_zoom(sess_a.value, f))

        # refrescar a galeria quando muda qualquer filtro
        for el in (sess_a, sess_b, tipo):
            el.on_value_change(lambda: galeria.refresh())
        galeria()
