"""
verificar_numeros_tese.py — a regra 6(b) do PLANO_MESTRE, automatizada
======================================================================
*"Antes de dar qualquer sessão por concluída: os números citados batem com o CSV
fonte (dizer qual)?"*

Essa verificação foi feita **à mão** a 18, 25 e 27 de julho de 2026. É a mesma
comparação de cada vez, e vai ser precisa outra vez em agosto (mega-treino e
mapa grande) e em setembro (versão composta, 15 set). Isto fá-la em segundos.

O que compara — **308 valores** e **4 afirmações em prosa**, na tese
e no artigo:

  · `tab:res_eval` (63) — a tabela principal: 21 células (7 cenários × 3
    algoritmos) × (sucesso, média, desvio) contra `final_7d/eval_by_run_7d.csv`,
    mais a contagem de episódios que a sustenta (2940 = 3 × 7 × 7 × 20);
  · `tab:res_scale_all` (35) — eficiência per capita do GNN a N∈{10,20,50,100} e
    a retenção, contra `estatisticas/escalabilidade_*.csv`;
  · `tab:res_signif` (105) — as 21 comparações emparelhadas (médias, p, δ e a
    coluna "Signif.") contra `testes_significancia_food_collected.csv`;
  · `§res_robustez` — os INTERVALOS afirmados em prosa ("entre 92% e 106% nas 21
    combinações", "o evolutivo retém 92--97%") contra os `eval_*_fail10.csv`.
    Uma afirmação de intervalo em texto é mais frágil do que uma tabela: ninguém
    a regenera com um script, e sobrevive a dados novos sem dar sinal;
  · `Artigo/artigo.tex`, `tab:task` (105) — o artigo é o que vai ser submetido e
    as suas tabelas são cópias reformatadas das da tese, que sobrevivem a
    correções da tese sem darem sinal (foi assim que 8 figuras dele ficaram
    desatualizadas até 21 jul).

⚠️ A tabela de significância é comparada com o **CSV que o `statistical_tests.py`
produziu**, não recalculada. Ter aqui uma segunda implementação do Mann-Whitney
seria ter duas respostas possíveis para a mesma pergunta; e a pergunta que
interessa não é "o teste está bem feito?" mas "a tabela impressa é a que o teste
produziu?" — que é onde entram as gralhas de transcrição.

O que fica de fora: a §res_novelty e a campanha adaptativa, que vivem noutros CSV
com protocolos próprios. Entram quando alguém precisar de as verificar duas vezes.

⚠️ A unidade da tese é a **média por run**: cada célula é a média das 7 médias
por execução, não a média dos 140 episódios. Com runs desequilibrados dariam
valores diferentes, e é a armadilha nº3 noutra roupagem. Aqui reproduz-se a
regra da tese, não a mais cómoda.

Uso:
    python scripts/verificar_numeros_tese.py
    python scripts/verificar_numeros_tese.py --tolerancia 0.05

Devolve 0 se tudo bate; 1 se houver divergências (serve para um hook ou CI).
"""
import argparse
import json
import os
import re
import sys

import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

MAIN_TEX = os.path.join(PROJECT_ROOT, "Tese", "main.tex")
CSV_7D = os.path.join(PROJECT_ROOT, "results", "graficos_tese", "final_7d",
                      "eval_by_run_7d.csv")

# Rótulo na tabela da tese -> nome do cenário no CSV. A tese escreve os nomes em
# português; o CSV usa as chaves do simulador.
ROTULO_PARA_CENARIO = {
    "Sandbox": "none",
    "Muro U": "u_wall",
    "Gargalo": "bottleneck",
    "Quatro Salas": "four_rooms",
    "Porta Cooperativa": "cooperative_door",
    "Perceção Coop.": "cooperative_perception",
    "Porta c/ Alternativa": "cooperative_door_bypass",
    # O mesmo cenário aparece com rótulos diferentes conforme a tabela (e o CSV
    # do statistical_tests usa outros ainda). Comparar por rótulo literal dava
    # falsas divergências; a chave de comparação é sempre o nome do cenário.
    "Perceção Cooperativa": "cooperative_perception",
    "Beco Sem Saída (U)": "u_wall",
    "Porta Coop. c/ Alternativa": "cooperative_door_bypass",
    "Porta Cooperativa com Alternativa": "cooperative_door_bypass",
}
ALGOS = ("GNN", "PPO", "SAC")
DIR_ESCALA = os.path.join(PROJECT_ROOT, "results", "estatisticas")


def numero(s):
    """'85{,}7' ou '85,7' ou '100' -> float. None se não for número.

    O separador decimal PT-PT vem como `{,}` (commit 982f1a2, que passou 68
    números da tese a vírgula). Tem de ser resolvido ANTES de limpar chavetas,
    senão `85{,}7` fica `85{,7` e não converte — foi o que este parser fez à
    primeira, e deu 48 falsas divergências em 63 valores.
    """
    s = s.strip().replace("{,}", ".")
    s = s.replace("\\%", "").replace("%", "")
    s = re.sub(r"\\mathbf|\\textbf|[{}$]", "", s)
    s = s.replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def ler_tabela(caminho, label):
    """Extrai as linhas de dados de uma tabela LaTeX identificada pelo \\label."""
    with open(caminho, encoding="utf-8") as f:
        tex = f.read()
    i = tex.find("\\label{%s}" % label)
    if i < 0:
        raise SystemExit("[X] não encontrei \\label{%s} em %s" % (label, caminho))
    fim = tex.find("\\end{tabular}", i)
    corpo = tex[i:fim]

    linhas = {}
    for bruta in corpo.split("\\\\"):
        bruta = bruta.replace("\\hline", "").strip()
        if not bruta or bruta.startswith("%"):
            continue
        campos = [c.strip() for c in bruta.split("&")]
        rotulo = re.sub(r"\\[a-zA-Z]+\{|\}|\$", "", campos[0]).strip()
        if rotulo in ROTULO_PARA_CENARIO:
            linhas[rotulo] = campos[1:]
    return linhas


def esperado_do_csv(csv):
    """{(cenário, algo): (sucesso%, média, dp)} — pela regra da tese."""
    d = pd.read_csv(csv)
    saida = {}
    for (cen, algo), g in d.groupby(["Scenario", "Algorithm"]):
        # média por RUN primeiro; a célula é a média/dp dessas médias
        por_run = g.groupby("Run")["food_collected"].mean()
        sucesso = 100.0 * g["success"].mean()
        # ddof=1 (amostral) — é o que o pandas faz por omissão e, portanto, o que
        # o `gerar_figuras_7d.py` produziu para a tabela da tese. Com n=7 a
        # diferença não é cosmética: sqrt(7/6) = 1,08, e a primeira versão deste
        # script (ddof=0) acusou os 18 desvios da tabela de estarem errados
        # quando o errado era ele. Um verificador que dá falsos positivos é pior
        # do que não ter verificador nenhum.
        saida[(cen, algo)] = (sucesso, por_run.mean(), por_run.std(ddof=1))
    return saida, len(d)


def verificar_escalabilidade(tolerancia):
    """tab:res_scale_all — eficiência per capita do GNN por N, e a retenção.

    A tabela é só do GNN: as políticas MLP do PPO/SAC têm entrada de dimensão
    fixa e são incompatíveis com N≠20 (é o ponto da QI2, não uma omissão).

    Retenção = food_per_agent(N=100) / food_per_agent(**N=20**) — o denominador é
    a dimensão de **treino**, não o menor N da bateria. É a leitura certa para
    zero-shot: mede quanto se perde ao afastar-se do ponto onde a política foi
    aprendida. (A primeira versão desta função dividiu por N=10 e acusou 6 das 7
    retenções de estarem erradas; estava errada ela. É o segundo caso hoje em que
    este verificador acusou a tese e o enganado era o verificador.)
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: tab:res_scale_all  vs  estatisticas/escalabilidade_*.csv")
    print("=" * 72)

    tabela = ler_tabela(MAIN_TEX, "tab:res_scale_all")
    problemas, conferidos = [], 0

    for rotulo, campos in tabela.items():
        cen = ROTULO_PARA_CENARIO[rotulo]
        fp = os.path.join(DIR_ESCALA, "escalabilidade_%s.csv" % cen)
        if not os.path.exists(fp):
            problemas.append("%s: sem %s" % (rotulo, os.path.basename(fp)))
            continue
        d = pd.read_csv(fp)
        gnn = d[d["Algorithm"] == "GNN"].set_index("N")

        percapita = {}
        for k, n in enumerate((10, 20, 50, 100)):
            conferidos += 1
            tese = numero(campos[k]) if k < len(campos) else None
            if n not in gnn.index:
                problemas.append("%s: o CSV não tem N=%d" % (rotulo, n))
                continue
            csv_ = float(gnn.loc[n, "food_per_agent"])
            percapita[n] = csv_
            if tese is None:
                problemas.append("%s N=%d: não consegui ler a tese (%r)"
                                 % (rotulo, n, campos[k] if k < len(campos) else ""))
            elif abs(tese - csv_) > tolerancia:
                problemas.append("%-22s N=%-4d tese=%7.2f  csv=%7.2f  (Δ=%+.2f)"
                                 % (rotulo, n, tese, csv_, tese - csv_))

        # retenção (a última coluna), em pontos percentuais
        conferidos += 1
        tese_ret = numero(campos[4]) if len(campos) > 4 else None
        if 20 in percapita and 100 in percapita and percapita[20]:
            csv_ret = 100.0 * percapita[100] / percapita[20]
            if tese_ret is None:
                problemas.append("%s retenção: não consegui ler a tese" % rotulo)
            elif abs(tese_ret - csv_ret) > 1.0:   # a tese arredonda ao inteiro
                problemas.append("%-22s retenção tese=%5.1f%%  csv=%5.1f%%  "
                                 "(Δ=%+.1f pp)" % (rotulo, tese_ret, csv_ret,
                                                   tese_ret - csv_ret))

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores de tab:res_scale_all batem com os CSV." % conferidos)
    print("NOTA: a tabela é só do GNN — as MLP do PPO/SAC são incompatíveis com")
    print("      N≠20 por construção, que é o resultado da QI2 e não uma falta.")
    return problemas


def verificar_significancia(tolerancia):
    """tab:res_signif — as 21 comparações emparelhadas contra o CSV do teste.

    ⚠️ Isto **não** repete os testes: compara a tabela da tese com o CSV que o
    `statistical_tests.py` produziu. Reproduzir aqui o Mann-Whitney seria ter
    duas implementações a poder discordar, e a pergunta que interessa não é "o
    teste está bem feito?" mas "a tabela impressa é a que o teste produziu?" —
    que é onde entram as gralhas de transcrição.

    Verifica ainda a coerência interna que uma tabela dessas tem de ter: a coluna
    "Signif." e o p têm de concordar em torno de 0,05.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: tab:res_signif  vs  estatisticas/testes_significancia_*.csv")
    print("=" * 72)

    fp = os.path.join(DIR_ESCALA, "testes_significancia_food_collected.csv")
    if not os.path.exists(fp):
        print("[!] sem %s — a saltar." % os.path.basename(fp))
        return []
    csv = pd.read_csv(fp, encoding="utf-8", encoding_errors="replace")
    # chave: (cenário, "A vs B")
    # chave canónica: (cenário, "A vs B") — nunca o rótulo escrito
    do_csv = {(r["Scenario"], "%s vs %s" % (r["A"], r["B"])): r
              for _, r in csv.iterrows()}

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = f.read()
    i = tex.find("\\label{tab:res_signif}")
    corpo = tex[i:tex.find("\\end{tabular}", i)]

    problemas, conferidos, linhas_lidas = [], 0, 0
    for bruta in corpo.split("\\\\"):
        campos = [c.strip() for c in bruta.replace("\\hline", "").split("&")]
        if len(campos) < 7:
            continue
        rotulo = re.sub(r"\\[a-zA-Z]+\{|\}|\$", "", campos[0]).strip()
        par = re.sub(r"\\[a-zA-Z]+\{|\}|\$", "", campos[1]).strip()
        cen = ROTULO_PARA_CENARIO.get(rotulo)
        if cen is None or (cen, par) not in do_csv:
            if rotulo and "vs" in par:
                problemas.append("%s / %s: não está no CSV do teste (cenário %r)"
                                 % (rotulo, par, cen))
            continue
        linhas_lidas += 1
        r = do_csv[(cen, par)]

        for k, nome, esperado in ((2, "média A", float(r["mean_A"])),
                                  (3, "média B", float(r["mean_B"])),
                                  (4, "p", float(r["p_value"])),
                                  (5, "δ", float(r["cliffs_delta"]))):
            conferidos += 1
            tese = numero(campos[k])
            # o p vem com 4 casas na tese; as médias com 2
            tol = 0.0001 if nome == "p" else tolerancia
            if tese is None:
                problemas.append("%s / %s %s: não consegui ler (%r)"
                                 % (rotulo, par, nome, campos[k]))
            elif abs(tese - esperado) > tol:
                problemas.append("%-22s %-12s %-8s tese=%9.4f  csv=%9.4f"
                                 % (rotulo, par, nome, tese, esperado))

        # coerência entre a coluna "Signif." e o p
        conferidos += 1
        diz_sim = campos[6].strip().lower().startswith("sim")
        if diz_sim != bool(r["significant"]):
            problemas.append("%s / %s: coluna Signif.=%r mas o CSV diz %s "
                             "(p=%.4f)" % (rotulo, par, campos[6],
                                           r["significant"], r["p_value"]))

    if linhas_lidas != 21:
        problemas.append("li %d linhas da tabela, esperava 21 (7 cenários × 3 pares)"
                         % linhas_lidas)

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores de tab:res_signif (21 comparações) batem com o CSV."
              % conferidos)
    print("NOTA: compara a tabela com o CSV do statistical_tests.py; não repete")
    print("      os testes — duas implementações podiam discordar.")
    return problemas


def verificar_robustez():
    """§res_robustez — os INTERVALOS afirmados no texto, não uma tabela.

    A robustez não tem tabela: tem uma figura e duas afirmações em prosa —
    *"entre 92% e 106% em todas as 21 combinações"* e *"o controlador evolutivo
    (…) retém 92--97%"*. Uma afirmação de intervalo em prosa é **mais** fácil de
    ficar para trás do que uma tabela: ninguém a regenera com um script, e
    sobrevive a mudanças de dados sem dar sinal.

    Retenção = recolhas/ep com 10% de falhas ÷ recolhas/ep de base, por célula.
    Células com base a zero ficam de fora (a divisão não tem significado) — é o
    que o texto quer dizer com *"com desempenho de base"*.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §res_robustez (afirmações em prosa)  vs  eval_*_fail10.csv")
    print("=" * 72)

    d_eval = os.path.join(PROJECT_ROOT, "results", "evaluation")
    retencoes = {}
    for algo in ("gnn", "ppo", "sac"):
        for cen in ROTULO_PARA_CENARIO.values():
            base = os.path.join(d_eval, "eval_%s_%s.csv" % (algo, cen))
            fail = os.path.join(d_eval, "eval_%s_%s_fail10.csv" % (algo, cen))
            if not (os.path.exists(base) and os.path.exists(fail)):
                continue
            b = pd.read_csv(base)["food_collected"].mean()
            f = pd.read_csv(fail)["food_collected"].mean()
            if b > 0:
                retencoes[(algo.upper(), cen)] = 100.0 * f / b

    if not retencoes:
        print("[!] sem CSV de robustez — a saltar.")
        return []

    problemas = []
    lo, hi = min(retencoes.values()), max(retencoes.values())
    print("%d células com base > 0 | retenção de %.1f%% a %.1f%%"
          % (len(retencoes), lo, hi))

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = f.read()

    # "entre \textbf{92\% e 106\%} em todas as 21 combinações"
    m = re.search(r"retenção de recolhas situa-se entre\s*\\textbf\{(\d+)\\%\s*"
                  r"e\s*(\d+)\\%\}", tex)
    if not m:
        problemas.append("não encontrei a frase do intervalo global no main.tex "
                         "(mudou a redação? actualizar este verificador)")
    else:
        t_lo, t_hi = float(m.group(1)), float(m.group(2))
        # o texto arredonda para fora: 92 tem de ser <= mínimo real < 93, etc.
        if not (t_lo <= lo < t_lo + 1):
            problemas.append("mínimo: texto diz %.0f%%, medido %.1f%%"
                             % (t_lo, lo))
        if not (t_hi - 1 < hi <= t_hi):
            problemas.append("máximo: texto diz %.0f%%, medido %.1f%%"
                             % (t_hi, hi))

    m = re.search(r"n.º de combinações|em todas as (\d+) combinações", tex)
    if m and int(m.group(1)) != len(retencoes):
        problemas.append("o texto diz %s combinações, contei %d com base > 0"
                         % (m.group(1), len(retencoes)))

    # "O controlador evolutivo (…) retém 92--97\%"
    m = re.search(r"controlador evolutivo[^.]*?retém\s*(\d+)--(\d+)\\%", tex)
    gnn = [v for (a, _), v in retencoes.items() if a == "GNN"]
    if m and gnn:
        t_lo, t_hi = float(m.group(1)), float(m.group(2))
        g_lo, g_hi = min(gnn), max(gnn)
        print("GNN (%d células): %.1f%% a %.1f%%  | texto: %.0f--%.0f%%"
              % (len(gnn), g_lo, g_hi, t_lo, t_hi))
        if not (t_lo <= g_lo < t_lo + 1) or not (t_hi - 1 < g_hi <= t_hi):
            problemas.append("intervalo do GNN: texto %.0f--%.0f%%, medido "
                             "%.1f--%.1f%%" % (t_lo, t_hi, g_lo, g_hi))
    elif not m:
        problemas.append("não encontrei a frase do intervalo do GNN")

    if problemas:
        print("DIVERGÊNCIAS:")
        for p in problemas:
            print("   " + p)
    else:
        print("As afirmações de §res_robustez batem com os CSV.")
    return problemas


def verificar_legendas_trajetorias():
    """As recolhas citadas nas LEGENDAS das figuras de trajetórias.

    §res_complexos afirma, dentro das legendas, quantas recolhas teve o episódio
    de cada figura: *"contorno do obstáculo em U (esq., 78 recolhas)"*. São
    números como quaisquer outros — só que vivem numa legenda, e por isso
    escapavam a tudo: não estão em tabela nem em prosa corrida, e regenerar as
    figuras com outros episódios não os atualizaria. A fonte é o JSON do episódio
    gravado, o mesmo que o painel «Ao vivo (3D)» reproduz e de onde a figura sai
    (`scripts/captura_episodio.py`).
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: legendas de §res_complexos  vs  results/episodios_3d/*.json")
    print("=" * 72)

    d_ep = os.path.join(PROJECT_ROOT, "results", "episodios_3d")
    if not os.path.isdir(d_ep):
        print("[!] sem results/episodios_3d — a saltar.")
        return []

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = f.read()

    # (cenário, o que a legenda diz antes do número) — a ordem é a das figuras
    alvos = [
        ("u_wall", r"contorno do obstáculo em U \(esq\., (\d+) recolhas\)"),
        ("four_rooms", r"labirinto de Quatro Salas \(dir\., (\d+) recolhas\)"),
        ("cooperative_door", r"Porta Cooperativa e a atravessa até ao ninho "
                             r"\(esq\., (\d+) recolhas\)"),
        ("cooperative_perception", r"tracejado verde \(dir\., (\d+) recolhas\)"),
    ]

    problemas = []
    for cen, padrao in alvos:
        caminho = os.path.join(d_ep, "gnn_%s.json" % cen)
        if not os.path.exists(caminho):
            problemas.append("%s: falta o JSON do episódio (%s)"
                             % (cen, os.path.basename(caminho)))
            continue
        with open(caminho, encoding="utf-8") as f:
            real = json.load(f).get("meta", {}).get("recolhas")
        m = re.search(padrao, tex)
        if not m:
            problemas.append("%s: não encontrei o número na legenda (a redação "
                             "mudou? atualizar este verificador)" % cen)
            continue
        na_tese = int(m.group(1))
        estado = "[v]" if na_tese == real else "[X]"
        print("  %s %-24s legenda %3d   episódio %s"
              % (estado, cen, na_tese, real))
        if na_tese != real:
            problemas.append("%s: a legenda diz %d recolhas, o episódio tem %s"
                             % (cen, na_tese, real))

    if problemas:
        print("DIVERGÊNCIAS:")
        for p in problemas:
            print("   " + p)
    else:
        print("As legendas das trajetórias batem com os episódios gravados.")
    return problemas


def verificar_artigo(tolerancia):
    """Artigo/artigo.tex, tab:task — a mesma campanha, outra apresentação.

    O artigo é o que vai ser submetido, e as suas tabelas são **cópias
    reformatadas** das da tese: sobrevivem a correções da tese sem darem sinal.
    Foi assim que 8 figuras do artigo ficaram desatualizadas até 21 jul.

    Cada célula é `média ± dp (sucesso%) [runs a 100%]`. O `[n/7]` **não existe na
    tese** — é o número de execuções cuja taxa de sucesso é 100%, e não a taxa de
    sucesso média. São coisas diferentes: no Muro U o PPO tem 71% de sucesso mas
    só 4 execuções em 7 chegam aos 100%.
    """
    fp_tex = os.path.join(PROJECT_ROOT, "Artigo", "artigo.tex")
    if not os.path.exists(fp_tex) or not os.path.exists(CSV_7D):
        return []

    print()
    print("=" * 72)
    print("VERIFICAÇÃO: Artigo tab:task  vs  final_7d/eval_by_run_7d.csv")
    print("=" * 72)

    d = pd.read_csv(CSV_7D)
    esperado = {}
    for (cen, algo), g in d.groupby(["Scenario", "Algorithm"]):
        por_run = g.groupby("Run")["food_collected"].mean()
        cheios = g.groupby("Run")["success"].mean()
        esperado[(cen, algo)] = (por_run.mean(), por_run.std(ddof=1),
                                 100.0 * g["success"].mean(),
                                 int((cheios == 1.0).sum()), len(por_run))

    with open(fp_tex, encoding="utf-8") as f:
        tex = f.read()
    i = tex.find("\\label{tab:task}")
    corpo = tex[i:tex.find("\\bottomrule", i)]

    problemas, conferidos, celulas = [], 0, 0
    for bruta in corpo.split("\\\\"):
        campos = [c.strip() for c in bruta.replace("\\midrule", "").split("&")]
        if len(campos) < 4:
            continue
        rotulo = re.sub(r"\\[a-zA-Z]+\{|\}|\$", "", campos[0]).strip()
        cen = ROTULO_PARA_CENARIO.get(rotulo)
        if cen is None:
            continue
        for k, algo in enumerate(ALGOS):
            txt = campos[k + 1]
            m = re.search(r"([\d{},.\\]+)\s*\\pm\s*([\d{},.\\]+).*?\((\d+)\\%\)"
                          r".*?\[(\d+)/(\d+)\]", txt)
            if not m:
                problemas.append("%s/%s: não consegui ler a célula (%r)"
                                 % (rotulo, algo, txt[:60]))
                continue
            celulas += 1
            e_med, e_dp, e_suc, e_cheios, e_runs = esperado[(cen, algo)]
            for nome, tese, csv_, tol in (
                    ("média", numero(m.group(1)), e_med, tolerancia),
                    ("desvio", numero(m.group(2)), e_dp, tolerancia),
                    # o artigo arredonda a taxa ao inteiro
                    ("sucesso", float(m.group(3)), e_suc, 0.5),
                    ("runs a 100%", float(m.group(4)), float(e_cheios), 0.01),
                    ("nº de runs", float(m.group(5)), float(e_runs), 0.01)):
                conferidos += 1
                if tese is None:
                    problemas.append("%s/%s %s: ilegível" % (rotulo, algo, nome))
                elif abs(tese - csv_) > tol:
                    problemas.append("%-22s %-4s %-12s artigo=%7.2f  csv=%7.2f"
                                     % (rotulo, algo, nome, tese, csv_))

    if celulas != 21:
        problemas.append("li %d células, esperava 21" % celulas)

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores de tab:task (21 células) batem com o CSV da tese."
              % conferidos)
    print("NOTA: o [n/7] do artigo é 'execuções com 100%% de sucesso', que NÃO é")
    print("      a taxa de sucesso média — a tese não reporta esta métrica.")

    # ── as mesmas afirmações que a tese faz em prosa, agora do lado do artigo ──
    # O artigo repete-as por palavras suas ("Quinze das vinte e uma"), e uma
    # correção na tese não lhes toca. É a divergência de sempre, a um nível a que
    # o verificador ainda não chegava: as tabelas batiam, as frases não eram
    # olhadas por ninguém.
    cheios = d.groupby(["Scenario", "Algorithm", "Run"])["success"].mean()
    combinacoes = d.groupby(["Scenario", "Algorithm"]).ngroups
    a_100 = sum(1 for (_, _), g in cheios.groupby(level=[0, 1])
                if (g == 1.0).all())

    # O artigo escreve os números por extenso; o texto tem quebras de linha no
    # meio das frases, por isso os padrões toleram qualquer espaço em branco.
    frases = [
        (r"Quinze\s+das\s+vinte\s+e\s+uma\s+combinações", float(a_100), 15.0,
         "combinações com 100% em todas as execuções"),
        (r"as\s+seis\s+restantes\s+escondem", float(combinacoes - a_100), 6.0,
         "combinações restantes"),
    ]
    for padrao, medido, no_artigo, nome in frases:
        conferidos += 1
        if not re.search(padrao, tex):
            problemas.append("artigo: não encontrei a frase de %s (a redação "
                             "mudou?)" % nome)
        elif abs(medido - no_artigo) > 0.01:
            problemas.append("artigo: %s — texto diz %.0f, dados dão %.0f"
                             % (nome, no_artigo, medido))
        else:
            print("  [v] %-42s dados %2.0f   artigo %2.0f"
                  % (nome, medido, no_artigo))
    return problemas


def verificar_megatreino_artigo(tolerancia):
    """Artigo, §5 — os números do mega-treino em PROSA, contra os mesmos CSV.

    O `verificar_artigo` cobre a tab:task; o mega-treino, no artigo, não vive
    em tabela nenhuma — vive num parágrafo, e nada o verificava. É a mesma
    situação que a tese tinha no Abstract até hoje: um número copiado para um
    segundo sítio, que sobrevive a uma correção do primeiro sem dar sinal. No
    artigo o risco é maior, porque é o que vai ser submetido e as suas figuras
    já derivaram uma vez em silêncio (8 delas, até 21 jul).

    A redação do artigo é a da tese comprimida (`\\pm` sem espaços à volta),
    pelo que os padrões são próprios. Se a redação mudar, o regex deixa de
    casar e o verificador diz que não conseguiu ler — não passa em silêncio.
    """
    fp_tex = os.path.join(PROJECT_ROOT, "Artigo", "artigo.tex")
    if not os.path.exists(fp_tex):
        return []

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from analise_megatreino import carregar
    except Exception as e:                                   # pragma: no cover
        print("[!] não importei o analise_megatreino (%s) — a saltar." % e)
        return []

    print()
    print("=" * 72)
    print("VERIFICAÇÃO: Artigo §5 (mega-treino, prosa)  vs  mega_1mes/*/eval_by_run.csv")
    print("=" * 72)

    with open(fp_tex, encoding="utf-8") as f:
        tex = f.read()

    N = r"([\d.,{}\\]+)"
    problemas, conferidos = [], 0

    def do_csv(fase, cen):
        g = carregar(fase, cen)
        if g is None:
            return None
        return (float(g["food"].mean()), float(g["food"].std()),
                int((g["suc"] >= 1.0).sum()), len(g))

    def confere(rotulo, tese, calc, exato=False):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler o valor no artigo.tex "
                             "(mudou a redação? actualizar este verificador)"
                             % rotulo)
        elif exato and int(tese) != int(calc):
            problemas.append("%-30s artigo=%d  csv=%d" % (rotulo, tese, calc))
        elif not exato and abs(tese - calc) > tolerancia:
            problemas.append("%-30s artigo=%6.1f  csv=%6.1f  (Δ=%+.2f)"
                             % (rotulo, tese, calc, tese - calc))

    def procura(padrao):
        m = re.search(padrao, tex)
        return [numero(g) for g in m.groups()] if m else None

    dados = {f: do_csv(f, c) for f, c in
             (("mega_A_fase1", "u_wall"), ("mega_A_fase2", "u_wall"),
              ("mega_A_fase3", "u_wall"), ("mega_A_fase4", "u_wall"),
              ("mega_B_fase5", "cooperative_door_bypass"))}
    if any(v is None for v in dados.values()):
        print("[!] faltam dados do mega-treino — a saltar.")
        return []
    med_a, dp_a, conv_a, n_a = dados["mega_A_fase1"]
    med_o, dp_o, conv_o, n_o = dados["mega_A_fase2"]
    med_p, dp_p, conv_p, n_p = dados["mega_A_fase3"]
    med_s, dp_s, conv_s, n_s = dados["mega_A_fase4"]
    med_b, dp_b, conv_b, n_b = dados["mega_B_fase5"]

    for rot, padrao, alvos in (
            ("M1 médias",
             r"adaptativo faz\s*\$" + N + r"\\pm" + N +
             r"\$ recolhas/ep contra \$" + N + r"\\pm" + N +
             r"\$ do objetivo puro",
             ((("M1 adaptativo média"), med_a, False),
              (("M1 adaptativo desvio"), dp_a, False),
              (("M1 objetivo média"), med_o, False),
              (("M1 objetivo desvio"), dp_o, False))),
            ("M1 contagens",
             r"\\textbf\{\$(\d+)/(\d+)\$ execuções\s*a \$100\\%\$ de sucesso "
             r"contra \$(\d+)/(\d+)\$\}",
             ((("M1 adaptativo convergentes"), conv_a, True),
              (("M1 adaptativo n"), n_a, True),
              (("M1 objetivo convergentes"), conv_o, True),
              (("M1 objetivo n"), n_o, True))),
            ("M2 PPO",
             r"PPO\s*\$" + N + r"\\pm" + N + r"\$ \(\$(\d+)/(\d+)\$;",
             ((("M2 PPO média"), med_p, False), (("M2 PPO desvio"), dp_p, False),
              (("M2 PPO convergentes"), conv_p, True), (("M2 PPO n"), n_p, True))),
            ("M2 SAC",
             r"SAC\s*\$" + N + r"\\pm" + N + r"\$ \(\$(\d+)/(\d+)\$;",
             ((("M2 SAC média"), med_s, False), (("M2 SAC desvio"), dp_s, False),
              (("M2 SAC convergentes"), conv_s, True), (("M2 SAC n"), n_s, True))),
            ("M3 bypass",
             r"\(\$" + N + r"\\pm" + N + r"\$, \$(\d+)/(\d+)\$ a \$100\\%\$, "
             r"contra \$" + N + r"\\pm" + N + r"\$",
             ((("M3 adaptativo média"), med_b, False),
              (("M3 adaptativo desvio"), dp_b, False),
              (("M3 adaptativo convergentes"), conv_b, True),
              (("M3 adaptativo n"), n_b, True))),
    ):
        v = procura(padrao)
        for i, (r, calc, ex) in enumerate(alvos):
            confere(r, v[i] if v else None, calc, exato=ex)

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("  " + p)
    else:
        print("Os %d valores do mega-treino no artigo batem com os CSV." % conferidos)
    return problemas


def verificar_megatreino(tolerancia):
    """§res_novelty, parágrafo do mega-treino — prosa, como a robustez.

    Estes números entraram na tese a 3 ago e são os de maior peso do capítulo:
    o $28/28$ contra $15/28$ é o que sustenta a resposta final à QI6. Não têm
    tabela, vivem em prosa e em duas legendas — exatamente a situação que o
    `verificar_robustez` existe para cobrir: ninguém os regenera com um script,
    e sobreviveriam a uma mudança de dados sem dar sinal.

    As contagens de convergência verificam-se **exatamente** (são inteiros); as
    médias e desvios com a mesma tolerância do resto do verificador.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §res_novelty (mega-treino, n=28)  vs  mega_1mes/*/eval_by_run.csv")
    print("=" * 72)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from analise_megatreino import FIXO_BYPASS, carregar
    except Exception as e:                                   # pragma: no cover
        print("[!] não importei o analise_megatreino (%s) — a saltar." % e)
        return []

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = f.read()

    N = r"([\d.,{}\\]+)"          # "67{,}4" tal como sai do LaTeX
    problemas, conferidos = [], 0

    def do_csv(fase, cen):
        g = carregar(fase, cen)
        if g is None:
            return None
        return (float(g["food"].mean()), float(g["food"].std()),
                int((g["suc"] >= 1.0).sum()), len(g))

    def confere(rotulo, tese, calc, exato=False):
        """`tese` lido do .tex, `calc` recalculado do CSV."""
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler o valor no main.tex "
                             "(mudou a redação? actualizar este verificador)" % rotulo)
        elif exato and int(tese) != int(calc):
            problemas.append("%-28s tese=%d  csv=%d" % (rotulo, tese, calc))
        elif not exato and abs(tese - calc) > tolerancia:
            problemas.append("%-28s tese=%6.1f  csv=%6.1f  (Δ=%+.2f)"
                             % (rotulo, tese, calc, tese - calc))

    def procura(padrao):
        m = re.search(padrao, tex)
        return [numero(g) for g in m.groups()] if m else None

    # --- M1: as duas médias vêm na MESMA frase, e as contagens na seguinte ---
    dados = {f: do_csv(f, c) for f, c in
             (("mega_A_fase1", "u_wall"), ("mega_A_fase2", "u_wall"),
              ("mega_A_fase3", "u_wall"), ("mega_A_fase4", "u_wall"),
              ("mega_B_fase5", "cooperative_door_bypass"))}
    for fase, v in dados.items():
        if v is None:
            problemas.append("%s: sem dados (a tese cita números que não consigo "
                             "reproduzir)" % fase)
    if any(v is None for v in dados.values()):
        print("[!] faltam dados do mega-treino — a saltar o resto.")
        return problemas

    for fase, rot in (("mega_A_fase1", "GNN adaptativo"),
                      ("mega_A_fase2", "GNN objetivo"),
                      ("mega_A_fase3", "PPO"), ("mega_A_fase4", "SAC"),
                      ("mega_B_fase5", "adaptativo bypass")):
        med, dp, conv, n = dados[fase]
        print("  %-18s n=%-3d %6.1f ± %5.1f   convergentes: %d/%d"
              % (rot, n, med, dp, conv, n))

    v = procura(r"o adaptativo faz \$" + N + r" \\pm " + N +
                r"\$ recolhas/ep contra \$" + N + r" \\pm " + N +
                r"\$ do objetivo puro")
    med_a, dp_a, conv_a, n_a = dados["mega_A_fase1"]
    med_o, dp_o, conv_o, n_o = dados["mega_A_fase2"]
    for i, (rot, calc) in enumerate((("M1 adaptativo média", med_a),
                                     ("M1 adaptativo desvio", dp_a),
                                     ("M1 objetivo média", med_o),
                                     ("M1 objetivo desvio", dp_o))):
        confere(rot, v[i] if v else None, calc)

    v = procura(r"\$(\d+)/(\d+)\$ execuções a 100\\% de sucesso contra \$(\d+)/(\d+)\$")
    for i, (rot, calc) in enumerate((("M1 adaptativo convergentes", conv_a),
                                     ("M1 adaptativo n", n_a),
                                     ("M1 objetivo convergentes", conv_o),
                                     ("M1 objetivo n", n_o))):
        confere(rot, v[i] if v else None, calc, exato=True)

    for algo, fase in (("PPO", "mega_A_fase3"), ("SAC", "mega_A_fase4")):
        med, dp, conv, n = dados[fase]
        v = procura(algo + r" \$" + N + r" \\pm " + N + r"\$ \(\$(\d+)/(\d+)\$")
        for i, (rot, calc, ex) in enumerate(
                ((("M2 %s média" % algo), med, False),
                 (("M2 %s desvio" % algo), dp, False),
                 (("M2 %s convergentes" % algo), conv, True),
                 (("M2 %s n" % algo), n, True))):
            confere(rot, v[i] if v else None, calc, exato=ex)

    # --- M3: adaptativo desta campanha vs peso fixo da de julho, na mesma frase ---
    med_b, dp_b, conv_b, n_b = dados["mega_B_fase5"]
    v = procura(r"o adaptativo faz \$" + N + r" \\pm " + N +
                r"\$ recolhas/ep em \$(\d+)/(\d+)\$ execuções contra \$" +
                N + r" \\pm " + N + r"\$ do peso fixo")
    if os.path.exists(FIXO_BYPASS):
        df = pd.read_csv(FIXO_BYPASS)
        col = "Run" if "Run" in df.columns else df.columns[0]
        g = df.groupby(col).agg(food=("food_collected", "mean"))
        med_f, dp_f = float(g["food"].mean()), float(g["food"].std())
        print("  %-18s n=%-3d %6.1f ± %5.1f   (campanha de 12 jul, declarada)"
              % ("peso fixo w=0,5", len(g), med_f, dp_f))
        alvos = ((("M3 adaptativo média"), med_b, False),
                 (("M3 adaptativo desvio"), dp_b, False),
                 (("M3 adaptativo convergentes"), conv_b, True),
                 (("M3 adaptativo n"), n_b, True),
                 (("M3 peso fixo média"), med_f, False),
                 (("M3 peso fixo desvio"), dp_f, False))
        for i, (rot, calc, ex) in enumerate(alvos):
            confere(rot, v[i] if v else None, calc, exato=ex)
    else:
        problemas.append("falta o CSV do peso fixo (%s) que a tese cita em M3"
                         % os.path.relpath(FIXO_BYPASS, PROJECT_ROOT))

    # O Resumo e o Abstract repetem as contagens dos quatro braços: são os
    # primeiros números que o leitor (e o júri) vê, e vivem a cem páginas do
    # capítulo que os produz. Verificam-se os DOIS idiomas porque a versão
    # anterior só cobria o Resumo — e a 14 de agosto encontrou-se o Abstract
    # sem sequer a frase, que o Resumo tinha desde 3 de agosto. Uma tradução
    # que fica para trás não é um erro de número, e por isso nada a apanhava.
    med_p, dp_p, conv_p, n_p = dados["mega_A_fase3"]
    med_s, dp_s, conv_s, n_s = dados["mega_A_fase4"]
    quatro_bracos = (("adaptativo convergentes", conv_a), ("adaptativo n", n_a),
                     ("objetivo convergentes", conv_o), ("objetivo n", n_o),
                     ("PPO convergentes", conv_p), ("PPO n", n_p),
                     ("SAC convergentes", conv_s), ("SAC n", n_s))
    for idioma, padrao in (
            ("resumo",
             r"\$(\d+)/(\d+)\$, contra \$(\d+)/(\d+)\$ do objetivo puro, "
             r"\$(\d+)/(\d+)\$ do PPO e \$(\d+)/(\d+)\$ do SAC"),
            ("abstract",
             r"\$(\d+)/(\d+)\$, against \$(\d+)/(\d+)\$ for the pure objective, "
             r"\$(\d+)/(\d+)\$ for PPO and \$(\d+)/(\d+)\$ for SAC")):
        v = procura(padrao)
        for i, (rot, calc) in enumerate(quatro_bracos):
            confere("%s %s" % (idioma, rot), v[i] if v else None, calc, exato=True)

    # --- Células EXPLORATÓRIAS (A5 Sandbox, B7 Perceção, B6 SAC no Gargalo) ---
    # Entraram na tese a 4 ago, em cumprimento do compromisso do pré-registo de
    # reportar todas as fases. Como as confirmatórias, vivem só em prosa.
    for fase, cen, rot, padrao in (
            ("mega_A_fase5", "none", "A5 Sandbox",
             r"para \$\\mathbf\{(\d+)/(\d+)\}\$ \(\$95\\%\$\), com \$" + N +
             r" \\pm " + N + r"\$ contra"),
            ("mega_B_fase7", "cooperative_perception", "B7 Perceção",
             r"\$(\d+)/(\d+)\$ \(\$81\\%\$\) e \$" + N + r" \\pm " + N + r"\$ contra"),
            ("mega_B_fase6", "bottleneck", "B6 SAC Gargalo",
             r"converge em \$(\d+)/(\d+)\$ \(\$33\\%\$\), com \$" + N +
             r" \\pm " + N + r"\$ recolhas/ep")):
        d = do_csv(fase, cen)
        if d is None:
            problemas.append("%s: sem dados para a célula exploratória" % rot)
            continue
        med, dp, conv, n = d
        print("  %-18s n=%-3d %6.1f ± %5.1f   convergentes: %d/%d  (exploratória)"
              % (rot, n, med, dp, conv, n))
        v = procura(padrao)
        for i, (r, calc, ex) in enumerate(((rot + " convergentes", conv, True),
                                           (rot + " n", n, True),
                                           (rot + " média", med, False),
                                           (rot + " desvio", dp, False))):
            confere(r, v[i] if v else None, calc, exato=ex)

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do mega-treino batem com os CSV." % conferidos)
    return problemas


# ── Novelty Search (QI6) ─────────────────────────────────────────────────────
#
# A secção do Novelty é a que carrega a QI6 — o resultado central da tese — e a
# medição de cobertura de 14 ago encontrou lá **164 valores que nenhum
# verificador olhava**, o maior buraco da dissertação. Não tem tabela: os
# números vivem em prosa, e por isso não há `ler_tabela()` que os apanhe.
#
# Diferença face às outras verificações deste ficheiro: os p e os δ **são
# recalculados** aqui. Nas tabelas comparo a tese com o CSV que o
# `statistical_tests.py` produziu, e digo que não repito os testes — porque
# repetir seria ter duas implementações a poder discordar. Para o Novelty não
# existe esse CSV: os testes correram nos scripts de análise e o resultado só
# ficou na prosa. Recalcular é, portanto, a única verificação possível — e o
# `cliffs_delta` vem importado do `statistical_tests`, para não haver uma
# segunda implementação dele por aqui.

RAIZ_NOV = os.path.join(PROJECT_ROOT, "results")
FONTES_NOV = {
    "fixo_uwall": ("novelty_final", "uwall", "results", "evaluation",
                   "eval_by_run.csv"),
    "fixo_bypass": ("novelty_final", "bypass", "results", "evaluation",
                    "eval_by_run.csv"),
    "adapt_A1": ("novelty_adaptativo", "week_A_fase1", "evaluation",
                 "eval_by_run.csv"),
    "adapt_A2": ("novelty_adaptativo", "week_A_fase2", "evaluation",
                 "eval_by_run.csv"),
    "adapt_B1": ("novelty_adaptativo", "week_B_fase1", "evaluation",
                 "eval_by_run.csv"),
    "adapt_B2": ("novelty_adaptativo", "week_B_fase2", "evaluation",
                 "eval_by_run.csv"),
    "adapt_B3": ("novelty_adaptativo", "week_B_fase3", "evaluation",
                 "eval_by_run.csv"),
    "objetivo": ("graficos_tese", "final_7d", "eval_by_run_7d.csv"),
}


def _por_run(chave, cen):
    """Médias por execução — a unidade da tese, nunca o episódio."""
    fp = os.path.join(RAIZ_NOV, *FONTES_NOV[chave])
    if not os.path.exists(fp):
        return None
    d = pd.read_csv(fp)
    d = d[d["Algorithm"].astype(str).str.upper() == "GNN"]
    if "Scenario" in d.columns:
        d = d[d["Scenario"] == cen]
    if d.empty:
        return None
    return d.groupby("Run")["food_collected"].mean().sort_index()


def _mw(a, b, unilateral):
    from scipy.stats import mannwhitneyu
    alt = "greater" if unilateral else "two-sided"
    try:
        return float(mannwhitneyu(list(a), list(b), alternative=alt,
                                  method="exact")[1])
    except ValueError:
        return None


def _delta(a, b):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from statistical_tests import cliffs_delta
    return cliffs_delta(list(a), list(b))


# Cada afirmação: o padrão lê os valores DO .tex (nunca fixos aqui), e cada
# grupo diz de que série sai o valor esperado.
AFIRMACOES_NOV = [
    {
        "rot": "Muro em U — novidade fixa vs objetivo",
        "re": r"com \$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ recolhas/ep contra "
              r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ do objetivo puro "
              r"\(\$p = (?P<p>[\d{},]+)\$, \$\\delta = \+(?P<d>[\d{},]+)\$\)",
        "A": ("fixo_uwall", "u_wall"), "B": ("objetivo", "u_wall"),
        "unilateral": False,
    },
    {
        "rot": "Porta c/ Alternativa — objetivo vs novidade fixa",
        "re": r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ contra "
              r"\$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ recolhas/ep com novidade "
              r"\(\$p = (?P<p>[\d{},]+)\$, \$\\delta = -(?P<d>[\d{},]+)\$",
        # A frase escreve o objetivo primeiro e a novidade depois, mas o grupo
        # `m` é sempre a série A: aqui A é a NOVIDADE (o segundo par), e o
        # δ=-1,00 do texto é δ(novidade, objetivo).
        "A": ("fixo_bypass", "cooperative_door_bypass"),
        "B": ("objetivo", "cooperative_door_bypass"),
        "unilateral": False, "delta_negativo": True,
    },
    {
        "rot": "T2 — adaptativo no Muro em U",
        "re": r"\$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ recolhas/ep contra "
              r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ do objetivo "
              r"\(\$p=(?P<p>[\d{},]+)\$ unilateral, \$\\delta=\+(?P<d>[\d{},]+)\$\)",
        "A": ("adapt_A1", "u_wall"), "B": ("objetivo", "u_wall"),
        "unilateral": True,
    },
    {
        "rot": "T3 — adaptativo no bypass",
        "re": r"\$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ vs\.\\ "
              r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ "
              r"\(\$p=(?P<p>[\d{},]+)\$, \$\\delta=-(?P<d>[\d{},]+)\$",
        "A": ("adapt_B1", "cooperative_door_bypass"),
        "B": ("objetivo", "cooperative_door_bypass"),
        "unilateral": False, "delta_negativo": True,
    },
    {
        "rot": "Controlo de orçamento — objetivo puro a 390 min",
        "re": r"\$(?P<conv>\d+)/7\$ \\textit\{runs\}, \$(?P<m>[\d{},]+) \\pm "
              r"(?P<s>[\d{},]+)\$",
        "A": ("adapt_A2", "u_wall"), "B": None, "unilateral": False,
    },
    {
        "rot": "Adaptativo a 390 min — Muro em U",
        "re": r"mant[ée]m \$7/7\$ no Muro em U \(\$(?P<m>[\d{},]+) \\pm "
              r"(?P<s>[\d{},]+)\$\)",
        "A": ("adapt_B2", "u_wall"), "B": None, "unilateral": False,
    },
    {
        "rot": "Adaptativo a 390 min — bypass (melhor da dissertação)",
        "re": r"\(\$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$, \$7/7\$\)",
        "A": ("adapt_B3", "cooperative_door_bypass"), "B": None,
        "unilateral": False,
    },
    {
        "rot": "T1 — Porta Cooperativa (não-degradação)",
        "re": r"Porta Cooperativa \$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ vs\.\\ "
              r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ "
              r"\(\$\\delta=-(?P<d>[\d{},]+)\$\)",
        "A": ("adapt_B1", "cooperative_door"), "B": ("objetivo", "cooperative_door"),
        "unilateral": False, "delta_negativo": True,
    },
    {
        "rot": "T1 — Perceção Cooperativa (não-degradação)",
        "re": r"Perce[çc][ãa]o \$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$ vs\.\\ "
              r"\$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$ "
              r"\(\$\\delta=-(?P<d>[\d{},]+)\$\)",
        "A": ("adapt_B1", "cooperative_perception"),
        "B": ("objetivo", "cooperative_perception"),
        "unilateral": False, "delta_negativo": True,
    },
]


def verificar_novelty(tolerancia):
    """§res_novelty — os valores em prosa da QI6, contra os eval_by_run."""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Novelty (QI6, em prosa)  vs  eval_by_run das campanhas")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())
    i = tex.find("Deceção e Procura por Novidade")
    if i < 0:
        print("[!] não encontrei a secção do Novelty — a saltar.")
        return []
    sec = tex[i:tex.find("\\section", i + 10)]

    problemas, conferidos = [], 0
    for af in AFIRMACOES_NOV:
        m = re.search(af["re"], sec)
        if m is None:
            problemas.append("%s: não encontrei a frase no main.tex "
                             "(o texto mudou de forma?)" % af["rot"])
            continue
        g = m.groupdict()
        a_serie = _por_run(*af["A"])
        b_serie = _por_run(*af["B"]) if af["B"] else None
        if a_serie is None or (af["B"] and b_serie is None):
            problemas.append("%s: falta o CSV de origem" % af["rot"])
            continue

        alvos = [("média", g.get("m"), a_serie.mean()),
                 ("desvio", g.get("s"), a_serie.std())]
        if b_serie is not None:
            alvos += [("média (B)", g.get("mo"), b_serie.mean()),
                      ("desvio (B)", g.get("so"), b_serie.std())]
        if g.get("conv") is not None:
            alvos.append(("convergentes", g["conv"], float((a_serie > 0).sum())))
        if g.get("p") is not None and b_serie is not None:
            alvos.append(("p", g["p"], _mw(a_serie, b_serie, af["unilateral"])))
        if g.get("d") is not None and b_serie is not None:
            d = _delta(a_serie, b_serie)
            alvos.append(("δ", g["d"], abs(d) if af.get("delta_negativo") else d))

        for nome, txt, esperado in alvos:
            if txt is None or esperado is None:
                continue
            conferidos += 1
            tese = numero(str(txt))
            # A tolerância sai das casas decimais que a tese ESCREVEU, não de um
            # número escolhido por mim: «$p=0{,}32$» é uma afirmação a duas
            # casas, e exigir-lhe 0,3176 é acusar de erro um arredondamento
            # correto — foi o que este verificador fez à primeira. Para as
            # médias fica o maior entre essa regra e a tolerância da linha de
            # comandos, que existe para absorver a ordem das agregações.
            casas = len((str(txt).replace("{,}", ".").split(".") + [""])[1])
            tol = 0.5 * 10 ** (-casas) if casas else 0.5
            if nome.startswith(("média", "desvio")):
                tol = max(tol, tolerancia)
            if tese is None:
                problemas.append("%s %s: não consegui ler (%r)"
                                 % (af["rot"], nome, txt))
            elif abs(tese - esperado) > tol:
                problemas.append("%-44s %-13s tese=%8.4f  dados=%8.4f  (Δ=%+.4f)"
                                 % (af["rot"], nome, tese, esperado,
                                    tese - esperado))

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores em prosa da secção do Novelty batem com os CSV."
              % conferidos)
    print("NOTA: aqui os p e os δ são RECALCULADOS, ao contrário das tabelas —")
    print("      esta secção nunca teve um CSV de testes, só prosa. O δ vem do")
    print("      `statistical_tests.cliffs_delta`, não de uma cópia local.")
    return problemas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerancia", type=float, default=0.05,
                    help="diferença absoluta aceite (o texto arredonda a 1 dp)")
    a = ap.parse_args()

    if not os.path.exists(CSV_7D):
        raise SystemExit(
            "[X] sem %s.\n    Este CSV vive na torre — ver docs/REPRODUZIR.md."
            % os.path.relpath(CSV_7D, PROJECT_ROOT))

    print("=" * 72)
    print("VERIFICAÇÃO: tab:res_eval  vs  final_7d/eval_by_run_7d.csv")
    print("=" * 72)

    tabela = ler_tabela(MAIN_TEX, "tab:res_eval")
    esperado, n_episodios = esperado_do_csv(CSV_7D)

    n_esperado = 3 * 7 * 7 * 20
    if n_episodios == n_esperado:
        print("episódios no CSV: %d = 3 algos × 7 cenários × 7 runs × 20 ep ✓"
              % n_episodios)
    else:
        print("⚠️  episódios no CSV: %d, esperados %d (3×7×7×20)"
              % (n_episodios, n_esperado))

    if len(tabela) != 7:
        print("⚠️  li %d linhas da tabela, esperava 7: %s"
              % (len(tabela), sorted(tabela)))

    print()
    problemas = []
    conferidos = 0
    for rotulo, campos in tabela.items():
        cen = ROTULO_PARA_CENARIO[rotulo]
        # A tabela é: Cenário & GNN-sucesso & GNN-recolhas & PPO-... & SAC-...
        for k, algo in enumerate(ALGOS):
            try:
                txt_suc, txt_rec = campos[2 * k], campos[2 * k + 1]
            except IndexError:
                problemas.append("%s/%s: a linha não tem colunas para este algoritmo"
                                 % (rotulo, algo))
                continue

            suc_tese = numero(txt_suc)
            m = re.search(r"([\d.,{}\\]+)\s*\\pm\s*([\d.,{}\\]+)", txt_rec)
            med_tese = numero(m.group(1)) if m else None
            dp_tese = numero(m.group(2)) if m else None

            suc_csv, med_csv, dp_csv = esperado[(cen, algo)]

            for nome, tese, csv_ in (("sucesso", suc_tese, suc_csv),
                                     ("média", med_tese, med_csv),
                                     ("desvio", dp_tese, dp_csv)):
                conferidos += 1
                if tese is None:
                    bruto = txt_suc if nome == "sucesso" else txt_rec
                    problemas.append("%s/%s %s: não consegui ler o valor da tese "
                                     "(%r)" % (rotulo, algo, nome, bruto))
                elif abs(tese - csv_) > a.tolerancia:
                    problemas.append(
                        "%-22s %-4s %-8s tese=%7.2f  csv=%7.2f  (Δ=%+.2f)"
                        % (rotulo, algo, nome, tese, csv_, tese - csv_))

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores de tab:res_eval batem com o CSV "
              "(tolerância %.2f)." % (conferidos, a.tolerancia))

    print()
    print("NOTA: a unidade é a MÉDIA POR RUN (7 por célula), não o episódio.")
    print("      As tabelas de significância verificam-se correndo o")
    print("      statistical_tests.py — reproduzir os testes aqui era escrevê-los")
    print("      duas vezes e arriscar duas respostas.")

    problemas += verificar_escalabilidade(a.tolerancia)
    problemas += verificar_significancia(a.tolerancia)
    problemas += verificar_robustez()
    problemas += verificar_legendas_trajetorias()
    problemas += verificar_megatreino(a.tolerancia)
    problemas += verificar_novelty(a.tolerancia)
    problemas += verificar_artigo(a.tolerancia)
    problemas += verificar_megatreino_artigo(a.tolerancia)

    print()
    print("=" * 72)
    print("TOTAL: %s" % ("%d divergência(s) — ver acima" % len(problemas)
                         if problemas else "tudo bate ✓"))
    print("=" * 72)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
