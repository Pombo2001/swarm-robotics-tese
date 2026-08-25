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
import hashlib
import os
import re
import subprocess
import sys
from datetime import date, datetime

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


def _tex_igual_ao_compilado(tex):
    """O `.tex` mudou de CONTEÚDO desde a última compilação, ou só de data?

    A data por si mente nos dois sentidos, e mentiu aqui: qualquer coisa que
    reescreva o ficheiro com o mesmo texto — um ensaio de mutação que repõe o
    original, um editor a gravar sem alterar, um `git checkout` — deixa o `.tex`
    mais recente do que o PDF sem uma vírgula diferente. A vista mandava
    recompilar uma tese que estava compilada, e quem mande recompilar sem
    necessidade acaba por ser ignorado quando a necessidade for real.

    O `latexmk` guarda no `main.fdb_latexmk` o md5 de cada ficheiro que leu na
    última corrida. É a única fonte que sabe o que foi mesmo compilado — e é a
    mesma que o `latexmk` usa para decidir se recompila.
    """
    fdb = os.path.join(os.path.dirname(tex), "main.fdb_latexmk")
    if not os.path.exists(fdb):
        return False                     # sem registo, a data é o que há
    nome = os.path.basename(tex)
    m = re.search(r'"%s"\s+[\d.]+\s+\d+\s+([0-9a-f]{32})' % re.escape(nome),
                  open(fdb, encoding="utf-8", errors="replace").read())
    if not m:
        return False
    return hashlib.md5(open(tex, "rb").read()).hexdigest() == m.group(1)


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

    if t_pdf < t_tex and not _tex_igual_ao_compilado(tex):
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


# `strftime("%b")` segue o locale do sistema e escrevia «22 Aug» num painel em
# português. Três letras, sem depender de locale nenhum.
_MESES_PT = ("jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez")


def _data_pt(d):
    return "%02d %s" % (d.day, _MESES_PT[d.month - 1])


def _dias_pt(n):
    return "%d dia%s" % (n, "" if abs(n) == 1 else "s")


def _prazo():
    """(cor, resumo, detalhe) dos marcos que faltam.

    O resumo existe porque o cartão dos prazos era o único mudo: a lista das
    datas ia toda para o «detalhe», fechado por omissão, e o cartão aparecia
    sem cor e sem uma linha — a dois dias do hard stop de integração. Um painel
    de prontidão que se cala precisamente no que está a chegar não serve.
    """
    # Contam-se DIAS DE CALENDÁRIO, não intervalos de 24 h: com `datetime.now()`
    # a meio da tarde, o dia 22 ficava a «1 dia» a 20 de agosto — e quem lê um
    # prazo conta os dias que faltam no calendário, não as horas.
    hoje = datetime.now().date()
    marcos = [("versão composta ao orientador", date(2026, 9, 15)),
              ("entrega", date(2026, 9, 30)),
              ("hard stop de integração (mapa/mega-treino)", date(2026, 8, 22))]
    marcos.sort(key=lambda kv: kv[1])
    linhas = []
    for nome, quando in marcos:
        dias = (quando - hoje).days
        linhas.append("%-44s %s  (%s)"
                      % (nome, _data_pt(quando), _dias_pt(dias)))

    proximos = [(n, q, (q - hoje).days) for n, q in marcos if (q - hoje).days >= 0]
    if not proximos:
        return MAU, "todos os marcos já passaram", "\n".join(linhas)
    nome, quando, dias = proximos[0]
    resumo = "%s — %s, %s" % (nome, _data_pt(quando),
                              "hoje" if dias == 0 else
                              "amanhã" if dias == 1 else
                              "daqui a %d dias" % dias)
    cor = MAU if dias <= 1 else AVISO if dias <= 7 else NEUTRO
    return cor, resumo, "\n".join(linhas)


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

                cor_prazo, resumo_prazo, detalhe_prazo = _prazo()
                linha(cor_prazo, "Prazos", resumo_prazo, detalhe_prazo)

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
