"""Vista «Prontidão» — *isto está em condições de ser entregue?*

Responde num ecrã a uma pergunta que hoje exige quatro comandos e algum cuidado:
os números da tese batem com os dados? os testes passam? o PDF que está no disco
foi compilado depois da última alteração ao `.tex`? há trabalho por enviar?

Não é um painel de estatísticas — é uma **lista de verificação antes de entregar**,
e cada linha corresponde a uma alínea da regra 6 do `PLANO_MESTRE.md`. As datas
que interessam são as de **15 set** (versão composta) e **30 set** (entrega).

Três decisões de desenho, para não ser um botão que mente:

  · o **verificador dos números da tese** corre de verdade (leva ~2 s) e o resultado é
    o do momento — nunca um valor guardado de uma corrida anterior;
  · os **testes** levam ~3 min, por isso não correm sozinhos: mostram o último
    resultado com a hora a que foi obtido, e só correm quando se pede;
  · a **compilação** não é refeita — lê-se o `main.log`. Mas compara-se a data do
    `.tex` com a do `.pdf`, que é o que apanha o caso perigoso: o PDF no disco ser
    anterior à última edição, e alguém enviá-lo a pensar que é o de agora.
"""
import os
import re
import subprocess
import sys
from datetime import datetime

from nicegui import ui

from .. import theme

CARD = theme.CARD + " p-4"
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

OK, MAU, AVISO, NEUTRO = "#4ade80", "#ff6b6b", "#ffb020", theme.INK_MUTED

# Último resultado dos testes nesta sessão do dashboard (não persiste: um
# resultado de ontem guardado em ficheiro seria pior do que não ter nenhum).
_testes = {"estado": None, "texto": "ainda não corridos nesta sessão", "quando": None}


def _correr(args, timeout):
    """(codigo, saida). Nunca levanta — uma verificação que rebenta não informa."""
    try:
        p = subprocess.run(args, cwd=_RAIZ, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "excedeu %d s" % timeout
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def _numeros_da_tese():
    rc, saida = _correr([sys.executable, "scripts/verificar_numeros_tese.py"], 180)
    total = sum(int(m) for m in re.findall(r"Os (\d+) valores", saida))
    if rc == 0:
        return OK, "%d valores conferem com os CSV" % total, saida
    divergencias = re.findall(r"DIVERG\w+ \((\d+) de", saida)
    n = sum(int(x) for x in divergencias) if divergencias else "?"
    return MAU, "%s divergência(s) — ver detalhe" % n, saida


def _pdf_em_dia():
    tex = os.path.join(_RAIZ, "Tese", "main.tex")
    pdf = os.path.join(_RAIZ, "Tese", "main.pdf")
    log = os.path.join(_RAIZ, "Tese", "main.log")
    if not (os.path.exists(tex) and os.path.exists(pdf)):
        return NEUTRO, "sem main.tex ou main.pdf", ""

    t_tex = datetime.fromtimestamp(os.path.getmtime(tex))
    t_pdf = datetime.fromtimestamp(os.path.getmtime(pdf))
    detalhe = "tex: %s · pdf: %s" % (t_tex.strftime("%d %b %H:%M"),
                                     t_pdf.strftime("%d %b %H:%M"))

    paginas = overfulls = refs = None
    if os.path.exists(log):
        txt = open(log, encoding="utf-8", errors="replace").read()
        m = re.search(r"Output written on main\.pdf \((\d+) pages", txt)
        paginas = m.group(1) if m else None
        overfulls = txt.count("Overfull")
        refs = txt.count("LaTeX Warning: Reference")

    if t_pdf < t_tex:
        return MAU, "o PDF é ANTERIOR à última edição do .tex — recompilar", detalhe
    corpo = "%s págs · %s overfulls · %s refs indefinidas" % (
        paginas or "?", overfulls if overfulls is not None else "?",
        refs if refs is not None else "?")
    cor = OK if (overfulls == 0 and refs == 0) else AVISO
    return cor, corpo, detalhe


def _git():
    rc, saida = _correr(["git", "status", "--porcelain"], 30)
    sujo = [l for l in saida.splitlines() if l.strip()]
    rc2, ahead = _correr(["git", "log", "--oneline", "origin/main..HEAD"], 30)
    por_enviar = len([l for l in ahead.splitlines() if l.strip()]) if rc2 == 0 else None

    if sujo:
        return AVISO, "%d ficheiro(s) por commitar" % len(sujo), "\n".join(sujo[:10])
    if por_enviar:
        return AVISO, "%d commit(s) por enviar (push)" % por_enviar, ahead
    return OK, "árvore limpa e sincronizada com o origin", ""


def _hook():
    caminho = os.path.join(_RAIZ, ".git", "hooks", "pre-commit")
    if os.path.exists(caminho):
        return OK, "pre-commit instalado", caminho
    return AVISO, "não instalado — scripts/instalar_hooks.sh", ""


def _prazo():
    hoje = datetime.now()
    marcos = [("versão composta ao orientador", datetime(2026, 9, 15)),
              ("entrega", datetime(2026, 9, 30)),
              ("hard stop de integração (mapa/mega-treino)", datetime(2026, 8, 22))]
    marcos.sort(key=lambda kv: kv[1])
    linhas = []
    for nome, quando in marcos:
        dias = (quando - hoje).days
        linhas.append("%-44s %s  (%d dias)"
                      % (nome, quando.strftime("%d %b"), dias))
    return "\n".join(linhas)


def build():
    with ui.column().classes("w-full gap-4 p-4"):
        theme.section_title(
            "checklist", "Prontidão",
            "as alíneas da regra 6 do plano, verificadas de facto")

        cartoes = ui.column().classes("w-full gap-3")

        def linha(cor, titulo, corpo, detalhe=""):
            with ui.card().classes(CARD + " w-full"):
                with ui.row().classes("items-center gap-3 no-wrap w-full"):
                    ui.element("div").style(
                        "width:10px;height:10px;border-radius:50%%;"
                        "background:%s;flex:none" % cor)
                    with ui.column().classes("gap-0 grow"):
                        ui.label(titulo).classes("text-sm font-bold")
                        ui.label(corpo).classes("text-xs mono-num") \
                            .style(f"color:{theme.INK_MUTED}")
                if detalhe:
                    with ui.expansion("detalhe").classes("w-full text-xs"):
                        ui.label(detalhe).classes(
                            "text-[11px] mono-num whitespace-pre-wrap break-all")

        def recarregar():
            cartoes.clear()
            with cartoes:
                cor, corpo, det = _numeros_da_tese()
                linha(cor, "Os números da tese e do artigo batem com os CSV?",
                      corpo, det)

                cor, corpo, det = _pdf_em_dia()
                linha(cor, "O PDF no disco é o do .tex atual?", corpo, det)

                linha(_testes["estado"] or NEUTRO, "A suite de testes passa?",
                      _testes["texto"] +
                      (" · %s" % _testes["quando"].strftime("%H:%M")
                       if _testes["quando"] else ""))

                cor, corpo, det = _git()
                linha(cor, "O trabalho está guardado e enviado?", corpo, det)

                cor, corpo, det = _hook()
                linha(cor, "O hook que trava números dessincronizados?", corpo, det)

                linha(NEUTRO, "Prazos", "", _prazo())

        async def correr_testes():
            _testes.update(estado=AVISO, texto="a correr (~3 min)…",
                           quando=datetime.now())
            recarregar()
            rc, saida = await ui.run.io_bound(
                _correr, [sys.executable, "-m", "pytest", "tests/", "-q"], 900)
            m = re.search(r"(\d+) passed", saida)
            if rc == 0 and m:
                _testes.update(estado=OK, texto="%s testes passam" % m.group(1),
                               quando=datetime.now())
            else:
                falhas = re.search(r"(\d+) failed", saida)
                _testes.update(
                    estado=MAU,
                    texto="%s teste(s) a falhar" % (falhas.group(1) if falhas
                                                    else "erro a correr"),
                    quando=datetime.now())
            recarregar()

        with ui.row().classes("items-center gap-2"):
            ui.button("Reverificar", icon="refresh", on_click=recarregar) \
                .props("flat dense no-caps")
            ui.button("Correr os testes (~3 min)", icon="science",
                      on_click=correr_testes).props("flat dense no-caps")

        recarregar()
