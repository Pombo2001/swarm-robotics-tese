"""
verificar_numeros_tese.py — a regra 6(b) do PLANO_MESTRE, automatizada
======================================================================
*"Antes de dar qualquer sessão por concluída: os números citados batem com o CSV
fonte (dizer qual)?"*

Essa verificação foi feita **à mão** a 18, 25 e 27 de julho de 2026. É a mesma
comparação de cada vez, e vai ser precisa outra vez em agosto (mega-treino e
mapa grande) e em setembro (versão composta, 15 set). Isto fá-la em segundos.

O que compara, hoje:

  · `tab:res_eval` — a tabela principal do Capítulo de Resultados: 21 células
    (7 cenários × 3 algoritmos) × (taxa de sucesso, média ± desvio-padrão das
    recolhas/ep) = **63 valores** contra `final_7d/eval_by_run_7d.csv`;
  · a contagem de episódios que sustenta a tabela (2940 = 3 × 7 × 7 × 20).

O que NÃO compara (e porquê): as tabelas de significância saem do
`statistical_tests.py` e reproduzi-las aqui seria escrever o teste duas vezes —
a verificação delas é correr esse script. A §res_novelty e a campanha adaptativa
vivem noutros CSV, com protocolos próprios; entram aqui quando alguém precisar
de as verificar duas vezes.

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
    # A tabela da escalabilidade escreve dois destes por extenso
    "Perceção Cooperativa": "cooperative_perception",
    "Beco Sem Saída (U)": "u_wall",
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

    print()
    print("=" * 72)
    print("TOTAL: %s" % ("%d divergência(s) — ver acima" % len(problemas)
                         if problemas else "tudo bate ✓"))
    print("=" * 72)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
