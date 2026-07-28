"""
verificar_numeros_tese.py — a regra 6(b) do PLANO_MESTRE, automatizada
======================================================================
*"Antes de dar qualquer sessão por concluída: os números citados batem com o CSV
fonte (dizer qual)?"*

Essa verificação foi feita **à mão** a 18, 25 e 27 de julho de 2026. É a mesma
comparação de cada vez, e vai ser precisa outra vez em agosto (mega-treino e
mapa grande) e em setembro (versão composta, 15 set). Isto fá-la em segundos.

O que compara — **203 valores** e **4 afirmações em prosa**:

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
    a regenera com um script, e sobrevive a dados novos sem dar sinal.

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

    print()
    print("=" * 72)
    print("TOTAL: %s" % ("%d divergência(s) — ver acima" % len(problemas)
                         if problemas else "tudo bate ✓"))
    print("=" * 72)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
