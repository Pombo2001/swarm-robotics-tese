"""Painel do Servidor ISCTE (vista Monitorizar, F2).

Mostra o estado do servidor de treino (tmux, load, processos, progresso do GNN, log)
e permite trazer os resultados por scp — sem sair do dashboard. Requer VPN ligada.
"""
from datetime import datetime

from nicegui import ui, run

from .. import remote, theme

CARD = theme.CARD + " p-4"
_section_title = theme.section_title


def _is_training(proc: str) -> bool:
    """proc = 'evo=N ppo=N sac=N runexp=N' → True se algum contador > 0."""
    try:
        return any(int(tok.split("=")[1]) > 0 for tok in proc.split() if "=" in tok)
    except (ValueError, IndexError):
        return False


def build():
    st = {"pw": "", "status": None, "busy": False}

    def _set_busy(v: bool):
        st["busy"] = v
        painel.refresh()

    async def atualizar():
        if not pw_in.value:
            ui.notify("Introduz a password SSH", type="warning")
            return
        st["pw"] = pw_in.value
        ip, hk = remote.SERVERS[server_sel.value]
        _set_busy(True)
        res = await run.io_bound(remote.get_status, ip, hk, st["pw"])
        st["status"] = res
        _set_busy(False)
        ui.notify("Estado atualizado" if res.get("ok") else "Falha na ligação",
                  type="positive" if res.get("ok") else "negative")

    async def trazer():
        if not st["pw"]:
            ui.notify("Atualiza o estado primeiro (precisa da password)", type="warning")
            return
        ip, hk = remote.SERVERS[server_sel.value]
        n = ui.notification("A empacotar e trazer resultados (scp)…", spinner=True, timeout=None)
        ok, txt = await run.io_bound(remote.fetch_results, ip, hk, st["pw"])
        n.dismiss()
        fetch_log.clear()
        with fetch_log:
            ui.label(txt).classes("text-xs font-mono whitespace-pre-wrap")
        ui.notify("Resultados trazidos e desempacotados — vê na vista Resultados" if ok
                  else "Falha a trazer resultados", type="positive" if ok else "negative")

    with ui.column().classes("w-full gap-4 p-4"):
        # Ligação
        with ui.card().classes(CARD):
            _section_title("dns", "Servidor de treino ISCTE")
            ui.label("Requer a VPN do ISCTE ligada. A password não é guardada.") \
                .classes("text-xs text-gray-500")
            if not remote.SERVERS:
                # Sem `configs/servidor.local.env` não há máquina nenhuma: o
                # endereço deixou de estar escrito no código para o repositório
                # poder ser público. Dizer o que falta é melhor do que um
                # seletor vazio — ou do que o IndexError que isto dava antes.
                ui.label("Sem máquina configurada. Copia "
                         "`configs/servidor.exemplo.env` para "
                         "`configs/servidor.local.env` e preenche o endereço, o "
                         "utilizador e a host key — o ficheiro não é versionado.") \
                    .classes("text-xs mt-2").style("color:#ffb020")
                return
            with ui.row().classes("w-full items-center gap-2 no-wrap mt-1"):
                server_sel = ui.select(list(remote.SERVERS), value=list(remote.SERVERS)[0],
                                       label="Máquina").props("outlined dense").classes("flex-1")
                pw_in = ui.input("Password SSH", password=True, password_toggle_button=True) \
                    .props("outlined dense").classes("flex-1")
                ui.button("Atualizar", icon="sync", on_click=atualizar).props("color=primary unelevated")

        # Estado
        @ui.refreshable
        def painel():
            if st["busy"]:
                with ui.row().classes("items-center gap-2 py-6 justify-center w-full"):
                    ui.spinner(size="lg", color="primary")
                    ui.label("A contactar o servidor…").classes("text-gray-400")
                return
            res = st["status"]
            if res is None:
                with ui.column().classes("w-full items-center py-8 gap-1"):
                    ui.icon("cloud_off").classes("text-5xl text-gray-600")
                    ui.label("Sem ligação ainda — introduz a password e clica em Atualizar.") \
                        .classes("text-gray-500 text-sm")
                return
            if not res.get("ok"):
                with ui.card().classes("bg-red-900/40 rounded-xl p-4 w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("error").classes("text-red-400 text-2xl")
                        ui.label("Não foi possível ligar").classes("text-lg font-bold")
                    ui.label(res.get("error", "")).classes("text-sm font-mono text-red-200")
                return

            training = _is_training(res.get("proc", ""))
            with ui.card().classes(CARD):
                with ui.row().classes("w-full items-center justify-between"):
                    _section_title("monitor_heart", res.get("host", "servidor"))
                    if training:
                        with ui.row().classes("items-center gap-2"):
                            ui.spinner(size="sm", color="green")
                            ui.badge("A TREINAR", color="green").props("rounded")
                    else:
                        ui.badge("LIVRE", color="grey").props("rounded")

                with ui.grid(columns=2).classes("w-full gap-2 mt-2"):
                    _info("speed", "Load / uptime", res.get("uptime", "—"))
                    _info("dashboard", "Processos", res.get("proc", "—"))
                    _info("terminal", "Sessões tmux", res.get("tmux", "—"))
                    _info("folder", "Sessão mais recente", res.get("sessao", "—"))

                _eta_block(res.get("eta"), training)

                ui.separator().classes("my-1")
                ui.label("Progresso GNN (últimas linhas do CSV)").classes("text-sm font-semibold text-sky-300")
                ui.label(res.get("gnn", "—")).classes("text-xs font-mono whitespace-pre-wrap text-gray-300")
                logname = res.get("logname") or "—"
                ui.label(f"Log de treino ({logname})").classes("text-sm font-semibold text-sky-300 mt-2")
                with ui.element("div").classes("bg-[#0d1117] rounded-lg p-2 w-full max-h-48 overflow-auto"):
                    ui.label(res.get("log", "—")).classes("text-xs font-mono whitespace-pre-wrap text-green-400")
        painel()

        # Ações
        with ui.card().classes(CARD):
            with ui.row().classes("w-full items-center justify-between"):
                _section_title("download", "Trazer resultados")
                ui.button("Trazer resultados (scp)", icon="cloud_download", on_click=trazer) \
                    .props("color=secondary outline")
            ui.label("Empacota a sessão de gráficos mais recente + avaliação/logs, descarrega "
                     "para out/res_servidor.tar.gz e desempacota em results/ (aparece logo na "
                     "vista Resultados).").classes("text-xs text-gray-500")
            fetch_log = ui.column().classes("w-full mt-1")


_DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def _fmt_dt(dt: datetime) -> str:
    return f"{_DIAS[dt.weekday()]} {dt.strftime('%d/%m %H:%M')}"


def _eta_block(eta: dict | None, training: bool):
    """Mostra início, fim estimado e progresso do treino (se houver dados)."""
    if not eta:
        return
    done, total = eta.get("done"), eta.get("total_treinos")
    pct = int(round(100 * done / total)) if (done and total) else None

    with ui.card().classes("bg-slate-900/60 rounded-xl p-3 w-full mt-2 border border-sky-900"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("schedule").classes("text-sky-400")
            ui.label("Estimativa de fim do treino").classes("text-sm font-semibold text-sky-300")
        with ui.grid(columns=2).classes("w-full gap-2 mt-1"):
            _info("play_arrow", "Início", _fmt_dt(eta["start"]) + " (servidor)")
            if eta.get("now") and eta.get("start"):
                horas_dec = (eta["now"] - eta["start"]).total_seconds() / 3600
                dec = (theme.num(horas_dec) + "h" if horas_dec >= 1
                       else f"{int(horas_dec * 60)} min")
                _info("timelapse", "Decorrido", dec)
            if eta.get("eta"):
                _info("flag", "Fim estimado", _fmt_dt(eta["eta"]) + " (servidor)")
            if eta.get("runs") and eta.get("cenarios") and eta.get("algos"):
                cfg = (f"{eta['runs']} execuções × {eta['cenarios']} cenários × "
                       f"{len(eta['algos'])} algos ({'/'.join(eta['algos'])})")
                _info("tune", "Plano", cfg)
            if pct is not None:
                _info("checklist", "Treinos concluídos", f"{done}/{total}  (~{pct}%)")
            elif done:
                _info("checklist", "Treinos concluídos", str(done))

        # "Faltam" calculado com o relógio do SERVIDOR (sem problemas de fuso).
        if training and eta.get("eta") and eta.get("now"):
            horas = (eta["eta"] - eta["now"]).total_seconds() / 3600
            if horas > 0:
                txt = f"Faltam ~{horas:.0f}h" if horas >= 1 else f"Faltam ~{int(horas * 60)} min"
                ui.label(f"⏳ {txt} — estimativa pelo ritmo real (a avaliação final acrescenta algum tempo).") \
                    .classes("text-xs text-amber-200 mt-1")
        elif training and not eta.get("eta"):
            # Warm-up da campanha: a ETA usa o ritmo REAL (treinos concluídos ÷
            # tempo decorrido) — antes do 1º treino fechar não há ritmo.
            ui.label("⏳ 1º treino da campanha ainda a decorrer — a estimativa de fim "
                     "aparece quando ele fechar (é calculada pelo ritmo real, não por "
                     "tempos teóricos). Com execuções de 195 min, conta ~3h15 até à 1ª estimativa.") \
                .classes("text-xs text-amber-200 mt-1")
        elif not training:
            ui.label("Sem treino ativo — a estimativa refere o último plano registado.") \
                .classes("text-xs text-gray-500 mt-1")


def _info(icon: str, titulo: str, valor: str):
    with ui.element("div").classes("bg-slate-900/50 rounded-lg p-2"):
        with ui.row().classes("items-center gap-1 no-wrap"):
            ui.icon(icon).classes("text-sky-400 text-sm")
            ui.label(titulo).classes("text-xs text-gray-400")
        ui.label(valor or "—").classes("text-sm font-mono whitespace-pre-wrap text-gray-200")
