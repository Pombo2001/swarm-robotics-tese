# -*- coding: utf-8 -*-
r"""Os números do dashboard contra os da dissertação.

Porque existe
-------------
O dashboard não é entregável, mas é o que se projeta na defesa — e **um número
que apareça nos dois sítios tem de ser o mesmo número**. A 4 de agosto dois KPIs
mentiam; a 31 de julho um rótulo anunciava uma proveniência que o ficheiro não
tinha. Nos dois casos o defeito não era o cálculo: era não haver nada que
comparasse as duas superfícies.

Este verificador compara, célula a célula:

* a **tabela científica** do dashboard (`data.science_table()`, que alimenta as
  vistas Ciência, Resultados e Defesa) com a `tab:res_eval` da dissertação, lida
  do `.tex` — sucesso e recolhas, nos 7 cenários × 3 algoritmos;
* os **KPIs do Overview** que têm fonte verificável: episódios avaliados,
  cenários, cobertura ≥80%, e o inventário de horas de treino;
* o inventário `_CAMPANHAS` contra as campanhas que **existem em `results/`** —
  é o que apanha uma campanha fechada que ninguém somou às horas.

Uso:
    .venv/Scripts/python.exe scripts/verificar_dashboard.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

MAIN = os.path.join(RAIZ, "Tese", "main.tex")

falhas = []
conferidos = 0

# Os rótulos da tabela da tese, na ordem em que lá aparecem, e a chave do
# cenário no código: nomes não são identificadores.
LINHAS_TABELA = [
    ("Sandbox", "none"),
    # A tese uniformizou o nome («Muro U» aparecia 35 vezes e «Muro em
    # U» 40); aqui aceitam-se as duas, para o verificador não voltar a partir
    # se alguém preferir a forma curta numa tabela apertada.
    ("Muro em U", "u_wall"),
    ("Gargalo", "bottleneck"),
    ("Quatro Salas", "four_rooms"),
    ("Porta Cooperativa", "cooperative_door"),
    ("Perceção Cooperativa", "cooperative_perception"),
    ("Porta com Alternativa", "cooperative_door_bypass"),
]


def _n(s):
    r"""'38{,}3' ou '85{,}7\%' -> float."""
    s = str(s).replace("{,}", ".")
    s = re.sub(r"\\%|\\mathbf|\\textbf|[{}$%\\]", "", s)
    return float(s.replace(",", ".").strip())


def compara(nome, dashboard, tese, tol=0.05):
    global conferidos
    conferidos += 1
    ok = abs(dashboard - tese) <= tol
    print("  %s %-46s dashboard %8.2f   tese %8.2f"
          % ("[v]" if ok else "[X]", nome, dashboard, tese))
    if not ok:
        falhas.append("%s: dashboard %.2f, tese %.2f" % (nome, dashboard, tese))


def tabela_da_tese():
    """{cenário: {algo: (sucesso, recolhas)}} lido da `tab:res_eval`."""
    with open(MAIN, encoding="utf-8") as fh:
        tex = fh.read()
    bloco = re.search(r"\\label\{tab:res_eval\}(.*?)\\end\{table\}", tex, re.S)
    if not bloco:
        falhas.append("não encontrei a tab:res_eval no main.tex")
        return {}
    out = {}
    for rotulo, chave in LINHAS_TABELA:
        m = re.search(re.escape(rotulo) + r"\s*&(.*?)\\\\", bloco.group(1), re.S)
        if not m:
            falhas.append("a linha «%s» não está na tab:res_eval" % rotulo)
            continue
        campos = [c.strip() for c in m.group(1).split("&")]
        if len(campos) != 6:
            falhas.append("a linha «%s» tem %d campos, esperava 6"
                          % (rotulo, len(campos)))
            continue
        out[chave] = {}
        for i, algo in enumerate(("GNN", "PPO", "SAC")):
            sucesso = _n(campos[2 * i])
            recolhas = _n(campos[2 * i + 1].split("\\pm")[0])
            out[chave][algo] = (sucesso, recolhas)
    return out


# ── 1. a tabela que as vistas mostram vs a que a tese imprime ────────────────
def tabela_cientifica():
    print()
    print("=" * 78)
    print("TABELA CIENTÍFICA do dashboard  vs  tab:res_eval da dissertação")
    print("=" * 78)
    from dashboard import data

    dash = data.science_table()
    tese = tabela_da_tese()
    if not dash:
        falhas.append("o dashboard não consegue construir a science_table()")
        print("  [X] sem eval_summary.csv — a vista Ciência ficaria vazia")
        return
    for _, chave in LINHAS_TABELA:
        if chave not in tese:
            continue
        if chave not in dash:
            falhas.append("cenário «%s» na tese e não no dashboard" % chave)
            print("  [X] %s: a tese reporta-o, o dashboard não o tem" % chave)
            continue
        for algo in ("GNN", "PPO", "SAC"):
            if algo not in dash[chave]:
                falhas.append("%s/%s falta no dashboard" % (chave, algo))
                continue
            suc_t, rec_t = tese[chave][algo]
            compara("%s · %s: sucesso (%%)" % (chave, algo),
                    dash[chave][algo]["ptask"], suc_t, tol=0.06)
            compara("%s · %s: recolhas/ep" % (chave, algo),
                    dash[chave][algo]["recolhas"], rec_t, tol=0.06)


# ── 2. KPIs do Overview ─────────────────────────────────────────────────────
def kpis():
    print()
    print("=" * 78)
    print("KPIs do Overview  vs  as fontes")
    print("=" * 78)
    import pandas as pd

    from dashboard import config, data
    from dashboard.views import overview

    dash = data.science_table() or {}
    n_epis = sum(i["n"] for algos in dash.values() for i in algos.values())
    df = pd.read_csv(data.EVAL_SUMMARY)
    compara("episódios avaliados (KPI)", n_epis, float(len(df)), tol=0.5)

    # 7 cenários na tabela; o 8.º (mapa composto) tem campanha própria e uma
    # secção própria — não entra no denominador da cobertura (compromisso 3 do
    # pré-registo, e a razão pela qual o KPI dizia 6/8 em vez de 6/7).
    compara("cenários na tabela de avaliação", float(len(dash)), 7.0, tol=0.5)
    print("  [i] cenários no simulador (SCENARIO_KEYS): %d — o 8.º é o mapa "
          "grande e tem secção própria" % len(config.SCENARIO_KEYS))

    # Cobertura ≥80% por algoritmo, recalculada da mesma fonte
    for algo in config.ALGOS:
        n = sum(1 for s in dash.values()
                if algo in s and s[algo]["ptask"] >= 80.0)
        print("  [i] %s: %d de %d cenários com sucesso ≥80%%"
              % (algo, n, len(dash)))

    # ── inventário de horas: as campanhas que existem estão todas somadas? ──
    horas = dict(overview._CAMPANHAS)
    print("  [i] %d campanhas no inventário, %d h no total"
          % (len(horas), sum(horas.values())))
    esperadas = {
        "mapa composto F2 (GNN)": (
            os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn",
                         "logs", "_campanha_concluida.txt"),
            r"[Mm]apa composto.*F2|F2.*GNN"),
        "mapa composto F2 (gradientes)": (
            os.path.join(RAIZ, "results", "mapa_grande", "f2_grad_sac",
                         "logs", "_campanha_concluida.txt"),
            r"[Mm]apa composto.*gradientes|F2.*gradientes"),
    }
    for nome, (marcador, padrao) in esperadas.items():
        if not os.path.exists(marcador):
            continue
        esta = any(re.search(padrao, k) for k in horas)
        print("  %s inventário de horas inclui «%s»"
              % ("[v]" if esta else "[X]", nome))
        if not esta:
            falhas.append("a campanha «%s» fechou e não está no inventário de "
                          "horas do Overview" % nome)


# ── 3. imagens que vêm do campeão e não da campanha ─────────────────────────
def galeria():
    print()
    print("=" * 78)
    print("GALERIA: as imagens de uma campanha têm de vir da campanha")
    print("=" * 78)
    import pandas as pd

    csv = os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn",
                       "evaluation", "eval_summary.csv")
    by_run = os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn",
                          "evaluation", "eval_by_run.csv")
    if not (os.path.exists(csv) and os.path.exists(by_run)):
        print("  [i] sem dados do F2 — nada a comparar")
        return
    campeao = pd.read_csv(csv)
    campanha = pd.read_csv(by_run)
    m_camp = campeao["food_collected"].mean()
    m_todos = campanha.groupby("Run")["food_collected"].mean().mean()
    print("  [i] eval_summary.csv (modelo campeão): %.2f recolhas/ep, "
          "%d episódios" % (m_camp, len(campeao)))
    print("  [i] eval_by_run.csv (as 21 execuções): %.2f recolhas/ep, "
          "%d episódios" % (m_todos, len(campanha)))
    if abs(m_camp - m_todos) > 0.5:
        print("  [!] as duas fontes divergem — qualquer figura desta campanha "
              "gerada do eval_summary mostra o MELHOR CASO, não a campanha")
    conferir = os.path.join(RAIZ, "results", "graficos_tese")
    print("  [i] figuras da tese ficam em results/graficos_tese; as do PDF são "
          "verificadas por scripts/verificar_figuras_tese.py")


# ── 4. o vocabulário do ecrã é o da dissertação ─────────────────────────────
# As formas que a dissertação abandonou, e que o dashboard continuou a mostrar.
# Os padrões são exatos de propósito: «Perceção Coop\.» não pode apanhar
# «Perceção Cooperativa», que é a forma boa.
FORMAS_ABANDONADAS = [
    (r"Muro U\b", "Muro em U"),
    (r"Beco Sem Sa", "Muro em U"),
    (r"Perceção [Cc]oop\.", "Perceção Cooperativa"),
    (r"Porta c/ [Aa]lt", "Porta com Alternativa"),
    (r"Porta [Cc]oop\.", "Porta Cooperativa"),
    (r"\b4 Salas\b", "Quatro Salas"),
    (r"Mapa [Gg]rande", "mapa composto"),
    # Com as duas caixas: um ensaio mostrou que «Runs/cenário» passava incólume
    # por o padrão ser minúsculo, que é a forma que uma etiqueta de campo tem.
    (r"\b[Rr]uns?\b", "execução/execuções"),
]

# Strings que contêm as palavras acima sem serem texto de ecrã: nomes de
# ficheiro, chaves e padrões de leitura. Declaradas uma a uma — a lista curta é
# o sinal de que a regra está a valer.
VOCABULARIO_ACEITE = (
    "Runs por algoritmo:",     # rótulo do ficheiro de metadados que se LÊ
)


def _literais_de_ecra(path):
    """(linha, texto) dos literais de string que não são docstrings.

    Ao contrário de um grep, isto não vê comentários — e os comentários deste
    projeto citam as formas velhas para explicar porque foram abandonadas. Um
    verificador que se queixasse da própria explicação seria ruído.
    """
    import ast
    with open(path, encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    docs = set()
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None)
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and corpo:
            p = corpo[0]
            if isinstance(p, ast.Expr) and isinstance(p.value, ast.Constant) \
                    and isinstance(p.value.value, str):
                docs.add(id(p.value))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) \
                and id(no) not in docs:
            yield no.lineno, no.value


def vocabulario():
    """O ecrã e a dissertação chamam o mesmo nome à mesma coisa.

    Chegaram a existir CINCO vocabulários para os sete cenários: os de
    `src/scenarios.py`, os do `dashboard/config.py`, e cópias próprias em duas
    vistas — e o Overview dizia «Muro U» na primeira linha da cronologia.
    Verifica duas coisas:

    * os nomes que o dashboard publica são os que a dissertação imprime na
      `tab:res_eval` (a lista `LINHAS_TABELA` é a mesma que serve para comparar
      os números — nomes e valores lidos da mesma fonte);
    * nenhuma string de ecrã usa uma forma abandonada.
    """
    global conferidos
    from dashboard import config

    for rotulo, chave in LINHAS_TABELA:
        conferidos += 1
        dado = config.SCENARIO_LABEL_SHORT.get(chave)
        if dado != rotulo:
            falhas.append("o dashboard chama %r ao %s; a dissertação imprime %r"
                          % (dado, chave, rotulo))

    base = os.path.join(RAIZ, "dashboard")
    ficheiros = []
    for pasta in (base, os.path.join(base, "views")):
        ficheiros += [os.path.join(pasta, f) for f in sorted(os.listdir(pasta))
                      if f.endswith(".py") and f != "__init__.py"]

    # As chaves internas dos cenários são identificadores, não nomes: dentro de
    # um caminho ou de um comando estão no sítio certo, numa frase não. O
    # Arquivo dizia «12 fases (u_wall a n=28)» e um seletor oferecia «u_wall
    # objetivo puro @390» a quem não sabe o que é um u_wall.
    chaves = sorted(config.SCENARIO_KEYS, key=len, reverse=True)
    tecnico = re.compile(r"[/\\]|\.(?:py|png|csv|gif|json|yaml|sh|md)\b|--|%s"
                         r"|\{|;\s*[\w-]+:")   # o último ramo é CSS embutido

    for path in ficheiros:
        rel = os.path.relpath(path, RAIZ).replace(os.sep, "/")
        for linha, texto in _literais_de_ecra(path):
            if any(a in texto for a in VOCABULARIO_ACEITE):
                continue
            # Frases, não identificadores: uma chave («runs») ou um argumento
            # de linha de comando («--runs») não é texto que alguém leia.
            if " " not in texto:
                continue
            for padrao, certo in FORMAS_ABANDONADAS:
                if re.search(padrao, texto):
                    falhas.append("%s:%d mostra uma forma abandonada (usar %r): %s"
                                  % (rel, linha, certo,
                                     texto.strip()[:70].replace("\n", " ")))
            if tecnico.search(texto):
                continue
            for chave in chaves:
                if re.search(r"\b%s\b" % re.escape(chave), texto):
                    falhas.append(
                        "%s:%d mostra a chave interna %r em vez de %r: %s"
                        % (rel, linha, chave,
                           config.SCENARIO_LABEL_SHORT.get(chave, chave),
                           texto.strip()[:60].replace("\n", " ")))
                    break
    print("[i] vocabulário  %d nomes de cenário e %d ficheiros do dashboard"
          % (len(LINHAS_TABELA), len(ficheiros)))


def main():
    tabela_cientifica()
    kpis()
    galeria()
    vocabulario()
    print()
    print("=" * 78)
    if falhas:
        print("%d valor(es) conferido(s), %d problema(s):" % (conferidos, len(falhas)))
        for f in falhas:
            print("  [X] %s" % f)
    else:
        print("Os %d valores do dashboard batem com as fontes da tese ✓" % conferidos)
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
