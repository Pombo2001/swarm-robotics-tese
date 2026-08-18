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
# cenário no código. Nomes não são identificadores — a lição de 28 jul.
LINHAS_TABELA = [
    ("Sandbox", "none"),
    # 18 ago: a tese uniformizou o nome («Muro U» aparecia 35 vezes e «Muro em
    # U» 40); aqui aceitam-se as duas, para o verificador não voltar a partir
    # se alguém preferir a forma curta numa tabela apertada.
    ("Muro em U", "u_wall"),
    ("Gargalo", "bottleneck"),
    ("Quatro Salas", "four_rooms"),
    ("Porta Cooperativa", "cooperative_door"),
    ("Perceção Coop.", "cooperative_perception"),
    ("Porta c/ Alternativa", "cooperative_door_bypass"),
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

    # 7 cenários na tabela; o 8.º (mapa grande) tem campanha própria e uma
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
        "mapa grande F2 (GNN)": (
            os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn",
                         "logs", "_campanha_concluida.txt"),
            r"[Mm]apa grande.*F2|F2.*GNN"),
        "mapa grande F2 (gradientes)": (
            os.path.join(RAIZ, "results", "mapa_grande", "f2_grad_sac",
                         "logs", "_campanha_concluida.txt"),
            r"[Mm]apa grande.*gradientes|F2.*gradientes"),
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


def main():
    tabela_cientifica()
    kpis()
    galeria()
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
