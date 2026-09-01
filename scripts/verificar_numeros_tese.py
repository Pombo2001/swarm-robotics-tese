"""Confere os números impressos na tese e no artigo contra os CSV que os produziram.

O que compara:
  - tab:res_eval, contra `final_7d/eval_by_run_7d.csv`;
  - tab:res_scale_all, contra `estatisticas/escalabilidade_*.csv`;
  - tab:res_signif, contra `testes_significancia_food_collected.csv`;
  - as afirmações que só existem em prosa (robustez, novidade, mega-treino,
    Resumo/Abstract), que ninguém regenera com um script e por isso sobrevivem
    caladas a dados novos;
  - `Artigo/artigo.tex`, cujas tabelas são cópias reformatadas das da tese.

A tabela de significância é comparada com o CSV que o `statistical_tests.py`
produziu, não recalculada: uma segunda implementação do Mann-Whitney daria duas
respostas possíveis para a mesma pergunta, e a pergunta aqui é se a tabela
impressa é a que o teste produziu.

A unidade é a média por run: cada célula é a média das médias por execução, não
a média dos episódios todos.

Uso:
    python scripts/verificar_numeros_tese.py [--tolerancia 0.05]

Devolve 0 se tudo bate e 1 se houver divergências (serve para hook ou CI).
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys

import numpy as np
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

# Rótulo na tabela da tese -> chave do cenário no CSV: a tese escreve os nomes
# em português, o CSV usa as chaves do simulador.
ROTULO_PARA_CENARIO = {
    "Sandbox": "none",
    "Muro U": "u_wall",
    "Muro em U": "u_wall",
    "Gargalo": "bottleneck",
    "Quatro Salas": "four_rooms",
    "Porta Cooperativa": "cooperative_door",
    "Perceção Coop.": "cooperative_perception",
    "Porta c/ Alternativa": "cooperative_door_bypass",
    # O mesmo cenário aparece com rótulos diferentes conforme a tabela (e o CSV
    # do statistical_tests usa outros ainda); a chave de comparação é sempre o
    # nome do cenário, nunca o rótulo literal.
    "Perceção Cooperativa": "cooperative_perception",
    "Beco Sem Saída (U)": "u_wall",
    "Porta Coop. c/ Alternativa": "cooperative_door_bypass",
    "Porta Cooperativa com Alternativa": "cooperative_door_bypass",
    # Como a prosa os escreve (§Discussão Global), que não é como as tabelas os
    # escrevem.
    "Porta com Alternativa": "cooperative_door_bypass",
    "Muro em U": "u_wall",
    "Muro U": "u_wall",
    "Muro em U": "u_wall",
}
ALGOS = ("GNN", "PPO", "SAC")
DIR_ESCALA = os.path.join(PROJECT_ROOT, "results", "estatisticas")


def numero(s):
    """'85{,}7' ou '85,7' ou '100' -> float. None se não for número.

    O separador decimal PT-PT vem como `{,}` e tem de ser resolvido ANTES de
    limpar chavetas: senão `85{,}7` fica `85{,7` e não converte.
    """
    s = s.strip().replace("{,}", ".")
    s = s.replace("\\%", "").replace("%", "")
    s = re.sub(r"\\mathbf|\\textbf|[{}$]", "", s)
    s = s.replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def corpo_tabela(tex, label):
    """O corpo de uma tabela, do `\\label` ao `\\end{tabular}`.

    Serve as tabelas que não são indexadas por cenário (a `ler_tabela` só
    devolve essas) e que por isso se leem à mão: a tab:res_scale, indexada por
    algoritmo, e as três de configuração, indexadas pelo hiperparâmetro. Está
    numa função à parte porque o `cobertura_verificador.py` embrulha estas
    funções para medir que trechos do `.tex` foram lidos; quem parta a tabela
    com `find()` no meio de outra função escapa à medição.
    """
    i = tex.find("\\label{%s}" % label)
    if i < 0:
        return None
    fim = tex.find("\\end{tabular}", i)
    return tex[i:fim if fim > i else i + 4000]


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
        # ddof=1 (amostral): é o que o pandas faz por omissão e, portanto, o que
        # o `gerar_figuras_7d.py` produziu para a tabela da tese. Com n=7 a
        # diferença não é cosmética: sqrt(7/6) = 1,08.
        saida[(cen, algo)] = (sucesso, por_run.mean(), por_run.std(ddof=1))
    return saida, len(d)


def verificar_escalabilidade(tolerancia):
    """tab:res_scale_all — eficiência per capita do GNN por N, e a retenção.

    A tabela é só do GNN: as políticas MLP do PPO/SAC têm entrada de dimensão
    fixa e são incompatíveis com N!=20 (é o ponto da QI2, não uma omissão).

    Retenção = food_per_agent(N=100) / food_per_agent(N=20). O denominador é a
    dimensão de TREINO, não o menor N da bateria: é a leitura certa para
    zero-shot, mede quanto se perde ao afastar-se do ponto onde a política foi
    aprendida.
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
            # A tese escreve a retenção ao inteiro, por isso a folga é a do
            # próprio arredondamento (0,5 pp).
            elif abs(tese_ret - csv_ret) > 0.5:
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


# §Escalabilidade: a prosa e a tab:res_scale, que a `verificar_escalabilidade`
# não cobre. O que se acrescenta são as afirmações ORDINAIS — a tese não diz só
# «Gargalo 58%», diz que é «a retenção mais baixa dos cenários com paredes». Um
# valor pode estar certo e a ordenação falsa, e é a ordenação que sustenta o
# argumento.

def _escala_por_cenario():
    """{cenário: DataFrame do GNN indexado por N} — a bateria de zero-shot."""
    dados = {}
    for cen in set(ROTULO_PARA_CENARIO.values()):
        fp = os.path.join(DIR_ESCALA, "escalabilidade_%s.csv" % cen)
        if os.path.exists(fp):
            d = pd.read_csv(fp)
            dados[cen] = d
    return dados


def verificar_escalabilidade_prosa(tolerancia):
    """§Escalabilidade: prosa, tab:res_scale, ordinais e o simulador."""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Escalabilidade (prosa + tab:res_scale + simulador)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())
    i = tex.find("\\label{sec:res_scale}")
    j = tex.find("\\section", i + 10)
    sec = tex[i:j]

    dados = _escala_por_cenario()
    problemas, conferidos = [], 0

    def gnn(cen, n, coluna):
        d = dados[cen]
        linha = d[(d["Algorithm"] == "GNN") & (d["N"] == n)]
        return float(linha[coluna].iloc[0])

    def confere(rot, tese, csv_, tol=None):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler o valor na tese" % rot)
        elif abs(tese - csv_) > (tolerancia if tol is None else tol):
            problemas.append("%-46s tese=%8.2f  dados=%8.2f  (Δ=%+.2f)"
                             % (rot, tese, csv_, tese - csv_))

    def achar(rot, padrao):
        m = re.search(padrao, sec, re.DOTALL)
        if m is None:
            problemas.append("%s: não encontrei a frase (o texto mudou?)" % rot)
        return m

    # 1. as 28 combinações a 100%
    celulas = [(cen, n) for cen in dados for n in (10, 20, 50, 100)]
    cem = [(cen, n) for cen, n in celulas if gnn(cen, n, "success_rate") == 1.0]
    m = re.search(r"\\textbf\{100\\% de sucesso nas (\d+) combina", sec)
    if m:
        conferidos += 1
        tese_n = int(m.group(1))
        if tese_n != len(celulas):
            problemas.append("a tese diz %d combinações, a bateria tem %d "
                             "(%d cenários × 4 dimensões)"
                             % (tese_n, len(celulas), len(dados)))
        elif len(cem) != len(celulas):
            faltam = [c for c in celulas if c not in cem]
            problemas.append("a tese diz 100%% nas %d combinações, mas %d não "
                             "estão a 100%%: %s" % (tese_n, len(faltam), faltam))
        else:
            print("   [%2d] 28 combinações a 100%%                    "
                  "%d cenários × 4 dimensões, todas a 1,0" % (1, len(dados)))
    else:
        problemas.append("28 combinações: não encontrei a frase")

    # 2. o ponto de comparação no tamanho de treino
    m = achar("Sandbox N=20 (três algoritmos)",
              r"Sandbox, \$N=20\$: GNN \$([\d{},]+)\$, PPO \$([\d{},]+)\$, "
              r"SAC \$([\d{},]+)\$ recolhas/ep")
    if m:
        d = dados["none"]
        for k, algo in enumerate(ALGOS):
            linha = d[(d["Algorithm"] == algo) & (d["N"] == 20)]
            confere("Sandbox N=20 %s" % algo, numero(m.group(k + 1)),
                    float(linha["mean_food"].iloc[0]))
        print("   [ 3] Sandbox N=20: os três algoritmos batem")

    # 3. a gama de dimensões, dita em palavras
    m = achar("gama de dimensões", r"\$N \\in \\\{10, 50, 100\\\}\$")
    m2 = achar("de metade a cinco vezes", r"de metade a cinco vezes o enxame "
                                          r"de treino")
    if m and m2:
        conferidos += 2
        ns = sorted(int(x) for x in dados["none"]["N"].unique())
        if ns != [10, 20, 50, 100]:
            problemas.append("a tese promete N ∈ {10,20,50,100}; o CSV tem %s"
                             % ns)
        elif not (min(ns) / 20.0 == 0.5 and max(ns) / 20.0 == 5.0):
            problemas.append("«de metade a cinco vezes»: %s/20 não dá 0,5–5×"
                             % ns)
        else:
            print("   [ 2] «de metade a cinco vezes o enxame de treino»  "
                  "N=%s ⇒ 0,5× a 5,0×" % ns)

    # 4. as retenções citadas na prosa (e a ordem que sustenta o argumento)
    retencao = {cen: 100.0 * gnn(cen, 100, "food_per_agent")
                / gnn(cen, 20, "food_per_agent") for cen in dados}
    prosa_ret = [
        ("Porta com Alternativa", "cooperative_door_bypass",
         r"Porta com Alternativa \$(\d+)\\%\$"),
        ("Porta Cooperativa", "cooperative_door",
         r"Porta Cooperativa \$(\d+)\\%\$"),
        ("Muro em U", "u_wall", r"Muro em U \$(\d+)\\%\$"),
        ("Sandbox", "none", r"Sandbox \$(\d+)\\%\$"),
        ("Perceção Cooperativa", "cooperative_perception",
         r"Perceção Cooperativa \$(\d+)\\%\$"),
        ("Quatro Salas", "four_rooms", r"Quatro Salas retém \$(\d+)\\%\$"),
        ("Gargalo", "bottleneck", r"\\textbf\{Gargalo\} \$(\d+)\\%\$"),
    ]
    for rot, cen, padrao in prosa_ret:
        m = achar("retenção %s (prosa)" % rot, padrao)
        if m:
            # A tolerância sai das casas decimais que a tese escreveu: um valor
            # escrito ao inteiro julga-se ao inteiro (0,5 pp), não a 1 pp.
            confere("retenção %s (prosa)" % rot, numero(m.group(1)),
                    retencao[cen], tol=0.5)
    print("   [ 7] as 7 retenções citadas na prosa batem com os CSV")

    # Afirmação ordinal: as duas piores retenções são as dos cenários ABERTOS e
    # a melhor é a de um cenário com paredes. Os valores podem continuar certos
    # e o argumento cair na mesma.
    conferidos += 3
    ordem = sorted(retencao, key=retencao.get)
    abertos = {"none", "cooperative_perception"}
    if set(ordem[:2]) != abertos:
        problemas.append("«a retenção mais baixa aos cenários abertos» é falsa: "
                         "as duas mais baixas são %s" % ordem[:2])
    elif ordem[-1] != "cooperative_door_bypass":
        problemas.append("«a retenção mais alta … Porta com Alternativa» é "
                         "falsa: a mais alta é %s" % ordem[-1])
    else:
        print("   [ 3] ordenação: as 2 mais baixas são os abertos, a mais alta "
              "é a Porta c/ Alternativa")

    # E o Gargalo como pior dos cenários COM PAREDES.
    conferidos += 1
    com_paredes = [c for c in retencao if c not in abertos]
    pior = min(com_paredes, key=retencao.get)
    if pior != "bottleneck":
        problemas.append("«a retenção mais baixa de todos os cenários com "
                         "paredes» é falsa: é %s (%.0f%%), não o Gargalo (%.0f%%)"
                         % (pior, retencao[pior], retencao["bottleneck"]))
    else:
        print("   [ 1] o Gargalo é mesmo a retenção mais baixa entre os que têm "
              "paredes")

    # 5. o Gargalo cresce em termos absolutos
    m = achar("Gargalo, recolhas totais",
              r"\(\$([\d{},]+)\$ em \$N=20\$ para \$([\d{},]+)\$ em \$N=100\$\)")
    if m:
        confere("Gargalo total N=20", numero(m.group(1)),
                gnn("bottleneck", 20, "mean_food"))
        confere("Gargalo total N=100", numero(m.group(2)),
                gnn("bottleneck", 100, "mean_food"))

    # 6. tab:res_scale — o contraste arquitetural no Sandbox
    d = dados["none"]
    # A `ler_tabela` só devolve linhas cujo rótulo seja um cenário; esta tabela
    # é indexada por algoritmo, por isso lê-se aqui. O rótulo perde o que vem
    # entre parênteses («GNN (Evolutivo)» -> «GNN»).
    corpo = corpo_tabela(sec, "tab:res_scale") or ""
    linhas_tab = {}
    for bruta in corpo.split("\\\\"):
        bruta = bruta.replace("\\hline", "").strip()
        campos_ = [c.strip() for c in bruta.split("&")]
        rot_ = re.sub(r"\(.*?\)|\\[a-zA-Z]+\{|[{}$]", "", campos_[0]).strip()
        if rot_ in ALGOS:
            linhas_tab[rot_] = campos_[1:]

    for algo in ALGOS:
        campos = linhas_tab.get(algo)
        if campos is None:
            problemas.append("tab:res_scale: não encontrei a linha do %s" % algo)
            continue
        for k, n in enumerate((10, 20, 50, 100)):
            linha = d[(d["Algorithm"] == algo) & (d["N"] == n)]
            compativel = bool(linha["compatible"].iloc[0])
            celula = campos[k] if k < len(campos) else ""
            conferidos += 1
            if not compativel:
                # O CSV diz incompatível: a tese TEM de dizer N/A, e vice-versa.
                if "N/A" not in celula:
                    problemas.append("tab:res_scale %s N=%d: a tese diz %r mas o "
                                     "CSV marca incompatível" % (algo, n, celula))
                continue
            if "N/A" in celula:
                problemas.append("tab:res_scale %s N=%d: a tese diz N/A mas o "
                                 "CSV tem dados" % (algo, n))
                continue
            # A célula é «taxa / recolhas» — `$100\%$ / $37{,}4$`. Parte-se na
            # barra e deixa-se o `numero()` limpar os $ e o \%.
            partes = celula.split("/")
            if len(partes) != 2:
                problemas.append("tab:res_scale %s N=%d: não li a célula %r"
                                 % (algo, n, celula))
                continue
            confere("tab:res_scale %s N=%d sucesso" % (algo, n),
                    numero(partes[0]),
                    100.0 * float(linha["success_rate"].iloc[0]))
            confere("tab:res_scale %s N=%d recolhas" % (algo, n),
                    numero(partes[1]), float(linha["mean_food"].iloc[0]))
    print("   [12] tab:res_scale: as células do GNN, e os N/A do PPO/SAC onde o "
          "CSV marca incompatível")

    # A legenda repete os extremos do GNN e afirma crescimento monotónico.
    m = achar("legenda: 37,4 → 127,3",
              r"crescem monotonicamente com \$N\$ \(\$([\d{},]+) \\rightarrow "
              r"([\d{},]+)\$\)")
    if m:
        totais = [gnn("none", n, "mean_food") for n in (10, 20, 50, 100)]
        confere("legenda tab:res_scale N=10", numero(m.group(1)), totais[0])
        confere("legenda tab:res_scale N=100", numero(m.group(2)), totais[-1])
        conferidos += 1
        if totais != sorted(totais):
            problemas.append("a legenda diz «monotonicamente» mas as recolhas "
                             "do GNN no Sandbox são %s" % totais)

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores da secção da escalabilidade batem." % conferidos)
    print("NOTA: além dos valores, confere ORDINAIS («a retenção mais baixa é a")
    print("      dos cenários abertos»), que é o que sustenta o argumento —")
    print("      os valores podem estar certos e a ordenação cair na mesma.")
    return problemas


# O mundo que a tese descreve vs o que o simulador constrói. Os cenários do
# Capítulo 4 são dados em metros — «passagem de 2,5 m», «parede de 14 m», «800
# passos» — e nenhum desses números está num CSV: saem da geometria de
# `swarm_env_3d.py` e do `configs/foraging.yaml`, que já mudaram (as aberturas
# passaram de 1,5 m a 2,5 m, a altura das paredes mudou).
#
# Não se lê o código como texto: instancia-se o ambiente e mede-se. A chave do
# cenário no config é `classic_scenario` — um `scenario` escrito por engano é
# ignorado em silêncio e devolve o cenário por omissão.

def _env(cen, n=20):
    import yaml
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    cfg = yaml.safe_load(open(os.path.join(PROJECT_ROOT, "configs",
                                           "foraging.yaml"), encoding="utf-8"))
    cfg["environment"]["num_agents"] = n
    cfg["environment"]["classic_scenario"] = cen
    e = SwarmForagingEnv3D(config=cfg)
    e.reset(seed=0)
    return e


def _vaos(paredes, eixo=0, excluir=()):
    """Vãos entre paredes consecutivas ao longo de um eixo.

    A largura de uma passagem não está escrita em lado nenhum como constante:
    é a consequência de onde acabam as paredes. Mede-se, portanto, como a tese
    a descreve — o espaço livre entre elas.
    """
    segs = sorted((w["pos"][eixo] - w["size"][eixo] / 2.0,
                   w["pos"][eixo] + w["size"][eixo] / 2.0)
                  for k, w in enumerate(paredes) if k not in excluir)
    return [round(b[0] - a[1], 6) for a, b in zip(segs, segs[1:])
            if b[0] - a[1] > 1e-6]


def _factos_do_simulador():
    """O que o simulador afirma, medido nele. {rótulo: valor}"""
    from src.environment.swarm_env_3d import DOOR_PUSHERS_REQUIRED

    f = {}
    e20 = _env("bottleneck", 20)
    f["dim_obs"] = float(e20.observation_space_val.shape[0])
    f["ego_feats"] = float(e20.ego_feats_dim)
    # A fórmula 16 + (N-1)×5 verifica-se medindo, não lendo: instanciar com
    # outro N e ver se a dimensão anda de 5 em 5 por vizinho.
    e10 = _env("bottleneck", 10)
    f["por_vizinho"] = (f["dim_obs"] - e10.observation_space_val.shape[0]) / 10.0
    f["lidar"] = float(e20.lidar_range)
    f["arena"] = float(e20.arena_radius)
    f["gargalo_passagem"] = _vaos(e20.walls)[0]
    f["max_steps"] = float(e20.max_steps)

    u = _env("u_wall")
    barra = max(u.walls, key=lambda w: w["size"][0])
    perna = min(u.walls, key=lambda w: w["size"][0])
    f["u_barra"] = float(barra["size"][0])
    f["u_perna"] = float(perna["size"][1])
    # A «abertura de 7 m» é o espaço livre entre a perna e a fronteira da arena.
    # O módulo trata a perna da esquerda (x=-7), cuja folga é a mesma.
    f["u_lateral"] = float(u.arena_radius
                           - (abs(perna["pos"][0]) + perna["size"][0] / 2.0))

    q = _env("four_rooms")
    horizontais = [w for w in q.walls if w["size"][0] > w["size"][1]]
    f["salas_abertura"] = max(_vaos(horizontais))

    p = _env("cooperative_door")
    f["porta_largura"] = float(p.door_size[0])
    f["porta_agentes"] = float(DOOR_PUSHERS_REQUIRED)
    f["porta_passos"] = float(p.max_steps)

    b = _env("cooperative_door_bypass")
    f["bypass_porta"] = float(b.door_size[0])
    # A alternativa é o que sobra entre o fim do segmento direito e a arena.
    barreira = [w for w in b.walls if abs(w["pos"][1]) < 1e-6
                and w is not b.walls[b.door_wall_index]]
    fim_direito = max(w["pos"][0] + w["size"][0] / 2.0 for w in barreira)
    f["bypass_alternativa"] = float(b.arena_radius - fim_direito)
    f["bypass_passos"] = float(b.max_steps)

    c = _env("cooperative_perception")
    f["alvo_velocidade"] = float(np.linalg.norm(c.nest_velocity))
    f["captura_agentes"] = float(c.required_to_eat)
    return f


# Cada afirmação: rótulo, padrão (procurado em TODA a tese, todas as
# ocorrências), o facto medido e a tolerância. Um padrão que deixe de encontrar
# seja o que for é problema: a frase pode ter sido reescrita e ficado sem quem a
# confira.
#
# Os padrões são ANCORADOS no cenário (`\item \textbf{Nome:}`) porque as
# descrições partilham a forma da frase: «aberturas de $X$\,m» aparece no Muro
# em U (7 m) e no Quatro Salas (2,5 m), e «passagem de $X$\,m de largura» no
# Gargalo (2,5 m) e na Porta Cooperativa (3 m). Sem âncora comparam-se cenários
# trocados.
AFIRMACOES_SIMULADOR = [
    ("dimensão da observação", r"\\mathbb\{R\}\^\{(\d+)\}", "dim_obs", 0.0),
    ("ego-features na fórmula",
     r"\(\$?(\d+) \+ \(N-1\)\\times 5\$?\)", "ego_feats", 0.0),
    ("Muro em U: parede superior",
     r"Muro em U\):\}.{0,400}?A parede superior tem \$([\d{},]+)\$\\,m",
     "u_barra", 0.01),
    ("Muro em U: pernas",
     r"Muro em U\):\}.{0,400}?as pernas laterais têm \$([\d{},]+)\$\\,m",
     "u_perna", 0.01),
    ("Muro em U: aberturas laterais",
     r"Muro em U\):\}.{0,600}?aberturas de \$([\d{},]+)\$\\,m",
     "u_lateral", 0.01),
    ("Gargalo: passagem (Cap. 4)",
     r"Gargalo \(Porta Estreita\):\}.{0,400}?passagem de \$([\d{},]+)\$\\,m",
     "gargalo_passagem", 0.01),
    ("Gargalo: passagem (§escalabilidade)",
     r"\\emph\{única\} passagem de \$([\d{},]+)\$\\,m",
     "gargalo_passagem", 0.01),
    ("Quatro Salas: aberturas",
     r"Quatro Salas \(Labirinto\):\}.{0,400}?aberturas de \$([\d{},]+)\$\\,m",
     "salas_abertura", 0.01),
    ("Porta Cooperativa: largura",
     r"a passagem de \$([\d{},]+)\$\\,m de largura encontra-se bloqueada",
     "porta_largura", 0.01),
    ("Porta Cooperativa: agentes na zona de pressão",
     r"quando no mínimo (\d+) agentes ocupam a zona de pressão",
     "porta_agentes", 0.0),
    ("Porta Cooperativa: horizonte",
     r"horizonte temporal alargado de \$(\d+)\$ passos", "porta_passos", 0.0),
    ("horizonte dos restantes cenários",
     r"face aos \$(\d+)\$ dos restantes", "max_steps", 0.0),
    ("Perceção: velocidade do alvo",
     r"ao dobro da velocidade normal \(\$([\d{},]+)\$\\,m/s\)",
     "alvo_velocidade", 0.001),
    ("Perceção: agentes para capturar",
     r"quando \$(\d+)\$ agentes se aproximam", "captura_agentes", 0.0),
    ("Bypass: porta central",
     r"mantém a porta central de \$([\d{},]+)\$\\,m", "bypass_porta", 0.01),
    ("Bypass: abertura alternativa",
     r"abertura permanentemente livre de \$([\d{},]+)\$\\,m",
     "bypass_alternativa", 0.01),
    ("Bypass: horizonte",
     r"limite temporal é alargado para \$(\d+)\$ passos", "bypass_passos", 0.0),
    ("alcance do LiDAR",
     r"LiDAR.{0,400}?alcance (?:máximo )?de \$?([\d{},]+)\$?\\,?m",
     "lidar", 0.01),
    ("raio da arena", r"raio \$r_\{arena\} = ([\d{},]+)\$\\,m", "arena", 0.01),
    ("raio da arena (legenda das renderizações)",
     r"uma \\textbf\{esfera\} de raio \$([\d{},]+)\$\\,m", "arena", 0.01),
]


def verificar_simulador():
    """As descrições do mundo, confrontadas com o mundo a correr."""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: o mundo descrito na tese  vs  o simulador instanciado")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    try:
        factos = _factos_do_simulador()
    except Exception as e:
        print("   [X] não consegui instanciar o ambiente: %s: %s"
              % (type(e).__name__, e))
        return ["simulador: não consegui instanciar o ambiente (%s)"
                % type(e).__name__]

    # A fórmula da observação é ela própria uma afirmação: 16 + (N-1)×5.
    problemas, conferidos = [], 0
    conferidos += 1
    esperado = factos["ego_feats"] + 19 * factos["por_vizinho"]
    if factos["dim_obs"] != esperado or factos["por_vizinho"] != 5.0:
        problemas.append("a fórmula 16+(N-1)×5 não descreve o ambiente: "
                         "ego=%g, por vizinho=%g, dim(N=20)=%g"
                         % (factos["ego_feats"], factos["por_vizinho"],
                            factos["dim_obs"]))
    else:
        print("   [ 1] a dimensão medida anda de %g em %g por vizinho: "
              "%g + 19×%g = %g"
              % (factos["por_vizinho"], factos["por_vizinho"],
                 factos["ego_feats"], factos["por_vizinho"], factos["dim_obs"]))

    for rot, padrao, chave, tol in AFIRMACOES_SIMULADOR:
        valor = factos[chave]
        ocorrencias = list(re.finditer(padrao, tex, re.DOTALL))
        if not ocorrencias:
            problemas.append("%s: não encontrei a afirmação na tese (foi "
                             "reescrita? deixou de ser verificada)" % rot)
            continue
        divergiu = 0
        for mm in ocorrencias:
            conferidos += 1
            tese = numero(mm.group(1))
            if tese is None or abs(tese - valor) > tol:
                divergiu += 1
                problemas.append("%-42s linha %-5d tese=%s  simulador=%g"
                                 % (rot, tex.count("\n", 0, mm.start()) + 1,
                                    mm.group(1), valor))
        if not divergiu:
            print("   [%2d] %-44s %g" % (len(ocorrencias), rot[:44], valor))

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores batem com o ambiente instanciado." % conferidos)
    print("NÃO cobre: a distância de captura de 4 m da Perceção Cooperativa, que")
    print("      é uma constante local dentro do passo de simulação e só se")
    print("      verificaria por experiência — fica por fazer, e está dito.")
    return problemas


# tab:hyperparameters contra o `configs/foraging.yaml`: é a tabela que alguém
# consulta para reproduzir o trabalho, e o config já mudou várias vezes. Cada
# linha declara o caminho no config e os números que a célula deve conter, por
# ordem; como a célula é prosa livre, extraem-se dela todos os números.

def _numeros_da_celula(celula):
    """Todos os números de uma célula da tabela, por ordem de aparição.

    Trata as quatro notações que as tabelas usam: `10^{-4}`, os dois
    separadores de milhares que aparecem misturados (`500,000` no Capítulo 4 e
    `500\\,000` no apêndice) e o decimal PT-PT `0{,}015`.
    """
    celula = re.sub(r"(\d)\\,(\d{3})", r"\1\2", celula)
    vals = []
    # O sinal faz parte do número: sem ele, `$-0{,}05$` do custo energético lia-se
    # como 0,05 e batia com um config que diz -0,05. (`--` é o travessão, não um
    # sinal, e por isso é excluído.)
    sinal = r"(?<!-)([-+]?)"
    for m in re.finditer(r"10\^\{(-?\d+)\}|" + sinal + r"(\d{1,3}(?:,\d{3})+)|"
                         + sinal + r"(\d+\{,\}\d+|\d+(?:\.\d+)?)", celula):
        if m.group(1) is not None:
            vals.append(10.0 ** int(m.group(1)))
        elif m.group(3) is not None:
            vals.append(float(m.group(2) + m.group(3).replace(",", "")))
        else:
            vals.append(float(m.group(4) + m.group(5).replace("{,}", ".")))
    return vals


def verificar_hiperparametros():
    """tab:hyperparameters (e o apêndice) vs configs/foraging.yaml."""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: tab:hyperparameters  vs  configs/foraging.yaml")
    print("=" * 72)

    import yaml
    cfg = yaml.safe_load(open(os.path.join(PROJECT_ROOT, "configs",
                                           "foraging.yaml"), encoding="utf-8"))
    amb, ppo, sac, evo = (cfg["environment"], cfg["ppo"], cfg["sac"],
                          cfg["evolution"])

    # (categoria, pedaço do nome do hiperparâmetro, valores esperados)
    esperado = [
        ("Ambiente", "Raio da Arena", [amb["arena_radius"]]),
        ("Ambiente", "Número de Agentes", [amb["num_agents"]]),
        ("Ambiente", "Número de Obstáculos", [amb["num_obstacles"]]),
        ("Ambiente", "Raio dos Obstáculos", [amb["obstacle_radius"]]),
        ("Ambiente", "Velocidade dos Obstáculos", [amb["obstacle_velocity"]]),
        ("Ambiente", "Raio do Ninho", [amb["nest_radius"]]),
        ("Ambiente", "Velocidade do Ninho", [amb["nest_velocity"]]),
        ("Ambiente", "Temporizador de Fome", [amb["hunger_timer_max"]]),
        # O «(1 nos labirintos)» não está no config: é uma regra do ambiente.
        # Mede-se instanciando um labirinto.
        ("Ambiente", "Cooperação Mínima",
         [amb["required_to_eat"], _env("u_wall").required_to_eat]),
        ("Ambiente", "Alcance do LiDAR", [amb["lidar_range"]]),
        ("Ambiente", "Fator de Progresso", [amb["progress_reward_factor"]]),
        ("Ambiente", "Resolução do Campo Geodésico", [amb["geodesic_cell_size"]]),
        ("PPO", "Taxa de Aprendizagem", [ppo["learning_rate"]]),
        ("PPO", "Passos por Rollout", [ppo["n_steps"]]),
        ("PPO", "Batch Size", [ppo["batch_size"]]),
        ("PPO", "Número de Épocas", [ppo["n_epochs"]]),
        ("PPO", "Arquitetura da Rede", [float(x) for x in ppo["net_arch"]]),
        ("PPO", "Número de CPUs", [ppo["num_cpu"]]),
        ("SAC", "Buffer de Replay", [sac["buffer_size"]]),
        ("SAC", "Coeficiente de Entropia", [sac["ent_coef"]]),
        ("SAC", "Taxa de Aprendizagem", [sac["learning_rate"]]),
        ("SAC", "Arquitetura da Rede", [float(x) for x in sac["net_arch"]]),
        ("Evolutivo", "Tamanho da População", [evo["pop_size"]]),
        ("Evolutivo", "Taxa de Mutação", [evo["mutation_rate"]]),
        ("Evolutivo", "Desvio Padrão Inicial",
         [evo["sigma"], evo["sigma_decay"], evo["sigma_min"]]),
        ("Evolutivo", "Episódios de Avaliação", [evo["eval_episodes"]]),
        # O «≈8k pesos» conta-se: instancia-se o agente e somam-se os parâmetros.
        ("Evolutivo", "Dimensão Oculta",
         [cfg["gnn_agent"]["hidden_dim"], _pesos_do_gnn()]),
    ]

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())
    corpo = corpo_tabela(tex, "tab:hyperparameters") or ""

    lidas, categoria = [], None
    for bruta in corpo.split("\\\\"):
        bruta = bruta.replace("\\hline", "").strip()
        campos = [c.strip() for c in bruta.split("&")]
        if len(campos) != 3:
            continue
        if campos[0]:
            cat = re.sub(r"\\textbf\{|\}|\(.*?\)", "", campos[0]).strip()
            if cat and cat != "Categoria":
                categoria = cat
        if campos[1] in ("\\textbf{Hiperparâmetro}", "Hiperparâmetro"):
            continue
        lidas.append((categoria, campos[1], campos[2]))

    problemas, conferidos = [], 0
    for cat, pedaco, valores in esperado:
        alvo = [l for l in lidas if l[0] == cat and pedaco in l[1]]
        if not alvo:
            problemas.append("%s / %s: não encontrei a linha na tabela"
                             % (cat, pedaco))
            continue
        if len(alvo) > 1:
            problemas.append("%s / %s: %d linhas correspondem — o padrão não "
                             "distingue" % (cat, pedaco, len(alvo)))
            continue
        na_tese = _numeros_da_celula(alvo[0][2])
        conferidos += len(valores)
        esp = [float(v) for v in valores]
        if len(na_tese) != len(esp) or any(
                abs(a - b) > max(1e-9, abs(b) * 1e-6)
                for a, b in zip(na_tese, esp)):
            problemas.append("%-10s %-32s tese=%s  config=%s"
                             % (cat, pedaco[:32], na_tese, esp))

    if problemas:
        print("DIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("Os %d valores de tab:hyperparameters batem com o config "
              "(%d linhas)." % (conferidos, len(esperado)))
    print("NOTA: o «$\\approx 8$k pesos» não é lido de lado nenhum — é contado,")
    print("      instanciando o GNNAgent3D e somando os parâmetros (%d)."
          % _pesos_do_gnn())

    # As duas tabelas do apêndice listam as próprias chaves do YAML: lê-se a
    # chave da tabela e procura-se no config, sem mapa escrito à mão. Uma chave
    # nova no apêndice passa a ser verificada sozinha.
    for label in ("tab:apx_env", "tab:apx_train"):
        problemas += _verificar_tabela_apendice(tex, label, cfg)

    # As duas linhas da novidade não existem no foraging.yaml: os seus valores
    # são os defaults do treinador, dados no `evo_config.get(...)`, e são
    # precisamente os parâmetros da QI6. Leem-se do código-fonte, que é a fonte
    # real deles.
    fonte = open(os.path.join(PROJECT_ROOT, "src", "training",
                              "evo_trainer_3d.py"), encoding="utf-8").read()

    def default(nome):
        m = re.search(r"evo_config\.get\('%s',\s*([-\d.]+)\)" % nome, fonte)
        return float(m.group(1)) if m else None

    for chave, esperados, rot in (
            ("novelty_weight", [default("novelty_weight")], "peso base"),
            ("novelty_k", [default("novelty_k"),
                           default("novelty_archive_max"),
                           default("novelty_add_per_gen")],
             "k / arquivo / novos por geração")):
        m = re.search(r"\\texttt\{%s\}[^&]*&([^\\\n]*(?:\\[^\\\n]*)*?)\\\\"
                      % chave.replace("_", r"\\_"), tex)
        if m is None:
            problemas.append("apêndice: não encontrei a linha do %s" % chave)
            continue
        if None in esperados:
            problemas.append("não consegui ler o default de %s no "
                             "evo_trainer_3d.py (mudou a forma da chamada?)"
                             % chave)
            continue
        na_tese = _numeros_da_celula(m.group(1))[:len(esperados)]
        conferidos += len(esperados)
        if na_tese != esperados:
            problemas.append("apêndice %-20s (%s) tese=%s  evo_trainer=%s"
                             % (chave, rot, na_tese, esperados))
        else:
            print("   %-22s %-32s %s" % (chave, rot, esperados))
    print("      (o \\texttt{novelty\\_weight} de 0,5 das campanhas de Novelty")
    print("      vem da linha de comando, não de config nenhum — não verificado.)")
    return problemas


def _procurar_no_config(cfg, chave):
    """Valor de uma chave, procurada em todas as secções do YAML."""
    achados = []
    if chave in cfg and not isinstance(cfg[chave], dict):
        achados.append(cfg[chave])
    for seccao, conteudo in cfg.items():
        if isinstance(conteudo, dict) and chave in conteudo:
            achados.append(conteudo[chave])
    # A mesma chave em duas secções com valores diferentes é uma ambiguidade
    # real (qual delas é a que a tese reporta?): dá erro, não se escolhe a
    # primeira.
    if len({str(v) for v in achados}) > 1:
        return "AMBÍGUA", achados
    return ("OK", achados[0]) if achados else ("AUSENTE", None)


def _verificar_tabela_apendice(tex, label, cfg):
    """As tabelas do apêndice que listam as chaves do YAML uma a uma."""
    corpo = corpo_tabela(tex, label)
    if corpo is None:
        return ["%s: não encontrei a tabela" % label]

    problemas, conferidos, sem_config = [], 0, []
    for bruta in corpo.split("\\\\"):
        bruta = bruta.replace("\\hline", "").strip()
        campos = [c.strip() for c in bruta.split("&")]
        idx = next((k for k, c in enumerate(campos)
                    if c.startswith("\\texttt{")), None)
        if idx is None or idx + 1 >= len(campos):
            continue
        chave = re.match(r"\\texttt\{(.+?)\}", campos[idx]).group(1)
        chave = chave.replace("\\_", "_")
        estado, valor = _procurar_no_config(cfg, chave)
        if estado == "AUSENTE":
            sem_config.append(chave)
            continue
        if estado == "AMBÍGUA":
            problemas.append("%s: a chave %s aparece com valores diferentes em "
                             "secções diferentes do config: %s"
                             % (label, chave, valor))
            continue
        na_tese = _numeros_da_celula(campos[idx + 1])
        esp = ([float(v) for v in valor] if isinstance(valor, list)
               else [float(valor)])
        # Fora das listas, compara-se o PRIMEIRO número da célula: os restantes
        # são anotações («$\times 0{,}999$/geração», «$\sigma_{\min}=0{,}03$»)
        # e essas já são conferidas na tab:hyperparameters.
        na_tese = na_tese[:len(esp)]
        conferidos += len(esp)
        if len(na_tese) != len(esp) or any(
                abs(a - b) > max(1e-9, abs(b) * 1e-6)
                for a, b in zip(na_tese, esp)):
            problemas.append("%s %-38s tese=%s  config=%s"
                             % (label, chave, na_tese, esp))

    if problemas:
        print("\n%s — DIVERGÊNCIAS (%d de %d):"
              % (label, len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("%s: %d valores lidos diretamente das chaves do YAML — batem."
              % (label, conferidos))
    if sem_config:
        print("   (fora do foraging.yaml — verificados a seguir contra os "
              "defaults do treinador: %s)" % ", ".join(sem_config))
    return problemas


_PESOS = []


def _pesos_do_gnn():
    """Milhares de pesos do controlador evolutivo, contados no modelo."""
    if not _PESOS:
        import gymnasium as gym
        from src.agents.gnn_agent_3d import GNNAgent3D
        agente = GNNAgent3D("robot_0",
                            gym.spaces.Box(-1, 1, (3,), dtype=np.float32),
                            config_path=os.path.join(PROJECT_ROOT, "configs",
                                                     "foraging.yaml"))
        _PESOS.append(round(sum(p.numel() for p in agente.parameters()) / 1000.0))
    return _PESOS[0]


# §Discussão Global: as afirmações DERIVADAS. A secção quase não tem números
# próprios — tem conclusões tiradas de números de outras secções: «superior a
# ambos em três cenários», «retém 58--90% nos cenários com paredes», «~8x menos
# núcleos-hora». As tabelas de origem já eram conferidas uma a uma; a contagem,
# o intervalo e a razão que a prosa tira delas não. Uma célula que passe de
# significativa a não significativa não parte tabela nenhuma, parte a frase.

def _convergencia_por_run(csv=None):
    """{(cenário, algo): nº de runs com 100% de sucesso em todos os episódios}"""
    d = pd.read_csv(csv or CSV_7D)
    por_run = d.groupby(["Scenario", "Algorithm", "Run"])["success"].mean()
    return {k: int((v == 1.0).sum())
            for k, v in por_run.groupby(level=[0, 1])}


def _cenarios_da_frase(txt):
    """«Quatro Salas, Porta Cooperativa e Perceção Cooperativa» -> {chaves}.

    Devolve None se algum nome não for reconhecido — é melhor dizer «não
    percebi» do que comparar um conjunto incompleto e dar por bom.
    """
    nomes = re.split(r",| e ", re.sub(r"\\textit\{|\\textbf\{|\}", "", txt))
    chaves = set()
    for nome in nomes:
        nome = nome.strip().rstrip(".")
        if not nome:
            continue
        cen = ROTULO_PARA_CENARIO.get(nome)
        if cen is None:
            return None
        chaves.add(cen)
    return chaves


def verificar_discussao_global(tolerancia):
    """§res_discussao — as contagens, intervalos e razões que a prosa deriva."""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Discussão Global (afirmações derivadas das tabelas)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())
    i = tex.find("\\label{sec:res_discussao}")
    sec = tex[i:tex.find("\\chapter", i)]

    fp = os.path.join(DIR_ESCALA, "testes_significancia_food_collected.csv")
    if not os.path.exists(fp):
        print("[!] sem %s — a saltar." % os.path.basename(fp))
        return []
    csv = pd.read_csv(fp, encoding="utf-8", encoding_errors="replace")

    problemas, conferidos = [], 0

    def achar(rot, padrao):
        m = re.search(padrao, sec, re.DOTALL)
        if m is None:
            problemas.append("%s: não encontrei a frase (o texto mudou?)" % rot)
        return m

    def confere(rot, tese, calc, tol=0.0):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler o valor" % rot)
        elif abs(tese - calc) > tol:
            problemas.append("%-46s tese=%s  calculado=%s" % (rot, tese, calc))

    # quem é superior a quem, e em quantos cenários
    def venceu(cen, adversario):
        """O GNN é significativamente superior a este adversário neste cenário?"""
        linha = csv[(csv["Scenario"] == cen) & (csv["A"] == "GNN")
                    & (csv["B"] == adversario)]
        if linha.empty:
            return None
        r = linha.iloc[0]
        return bool(r["significant"]) and float(r["cliffs_delta"]) > 0

    cenarios = sorted(set(csv["Scenario"]))
    ambos = [c for c in cenarios if venceu(c, "PPO") and venceu(c, "SAC")]
    so_sac = [c for c in cenarios if venceu(c, "SAC") and not venceu(c, "PPO")]

    m = achar("superior a ambos em três cenários",
              r"superior a ambos os métodos de gradiente\}? em três cenários "
              r"\(([^)]+), com \$\\delta \\geq \+([\d{},]+)\$\)")
    if m:
        conferidos += 1
        # Os cenários vêm da PRÓPRIA frase, não de uma lista escrita aqui: se a
        # tese trocar um nome, o verificador tem de dar por isso.
        na_frase = _cenarios_da_frase(m.group(1))
        if na_frase is None:
            problemas.append("«superior a ambos em três cenários»: não "
                             "reconheci os cenários listados (%r)" % m.group(1))
        elif set(ambos) != na_frase:
            problemas.append("«superior a ambos em três cenários»: a tese lista "
                             "%s, os testes dizem %s"
                             % (sorted(na_frase), sorted(ambos)))
        else:
            deltas = [min(float(csv[(csv["Scenario"] == c) & (csv["A"] == "GNN")
                                    & (csv["B"] == adv)]["cliffs_delta"].iloc[0])
                          for adv in ("PPO", "SAC")) for c in ambos]
            confere("δ mínimo dos três cenários", numero(m.group(2)),
                    min(deltas), tol=0.005)
            print("   [ 2] superior a ambos em %d cenários, δ ≥ %.2f"
                  % (len(ambos), min(deltas)))

    m = achar("superior ao SAC em mais dois",
              r"superior ao SAC em mais dois \(([^)]+), \$\\delta = "
              r"\+([\d{},]+)\$\), empatando com o PPO")
    if m:
        conferidos += 1
        na_frase = _cenarios_da_frase(m.group(1))
        if na_frase is None:
            problemas.append("«superior ao SAC em mais dois»: não reconheci os "
                             "cenários listados (%r)" % m.group(1))
        elif set(so_sac) != na_frase:
            problemas.append("«superior ao SAC em mais dois»: a tese lista %s, "
                             "os testes dizem %s"
                             % (sorted(na_frase), sorted(so_sac)))
        else:
            d_sac = [float(csv[(csv["Scenario"] == c) & (csv["A"] == "GNN")
                               & (csv["B"] == "SAC")]["cliffs_delta"].iloc[0])
                     for c in so_sac]
            confere("δ dos dois cenários vs SAC", numero(m.group(2)),
                    min(d_sac), tol=0.005)
            print("   [ 2] superior só ao SAC em %d cenários, δ = %.2f"
                  % (len(so_sac), min(d_sac)))

    # o Muro em U: nenhuma comparação significativa
    if achar("Muro U sem significância",
             r"No \\textbf\{Muro (?:em )?U\}, nenhuma comparação atinge significância"):
        conferidos += 1
        sig = csv[(csv["Scenario"] == "u_wall") & (csv["significant"])]
        if len(sig):
            problemas.append("«nenhuma comparação atinge significância» no Muro "
                             "em U, mas o CSV marca %d como significativa(s): %s"
                             % (len(sig), list(zip(sig["A"], sig["B"]))))
        else:
            print("   [ 1] Muro em U: nenhuma das 3 comparações é significativa")

    convergencia = _convergencia_por_run()
    m = achar("taxas de convergência no Muro U",
              r"distinguir taxas de convergência de \$(\d)/7\$ a \$(\d)/7\$")
    if m:
        u = [convergencia[("u_wall", a)] for a in ALGOS]
        confere("Muro em U: menor taxa de convergência",
                numero(m.group(1)), float(min(u)))
        confere("Muro em U: maior taxa de convergência",
                numero(m.group(2)), float(max(u)))
        print("   [ 2] Muro em U: convergência de %d/7 a %d/7 (GNN %d, PPO %d, "
              "SAC %d)" % (min(u), max(u), u[0], u[1], u[2]))

    # as 28 execuções dos quatro cenários de gargalo
    m = achar("28 execuções nos cenários de gargalo",
              r"convergem as (\d+) execuções que perfazem os quatro cenários de "
              r"gargalo \(sete por cenário\)")
    if m:
        gargalos = ("bottleneck", "four_rooms", "cooperative_door",
                    "cooperative_door_bypass")
        total = sum(convergencia[(c, "GNN")] for c in gargalos)
        confere("execuções do GNN a convergir nos 4 cenários com paredes",
                numero(m.group(1)), float(total))
        conferidos += 1
        if total != 4 * 7:
            problemas.append("a tese diz que convergem TODAS as %s execuções, "
                             "mas só %d dos 28 runs do GNN chegam a 100%%"
                             % (m.group(1), total))
        else:
            print("   [ 2] os 4 cenários com paredes: 28/28 execuções do GNN a "
                  "100%")

    # a variância entre execuções
    d7 = pd.read_csv(CSV_7D)
    med = d7.groupby(["Scenario", "Algorithm", "Run"])["food_collected"].mean()
    for rot, padrao, cen, algo in (
            ("Sandbox bimodal (GNN)", r"cenários abertos \(Sandbox (\d)/7\)",
             "none", "GNN"),
            ("Gargalo, lotaria do SAC",
             r"\(Gargalo \$41\{,\}4 \\pm 36\{,\}8\$, (\d)/7\)", "bottleneck",
             "SAC"),
            ("PPO: único cenário bimodal",
             r"um único cenário bimodal \(Muro (?:em )?U, (\d)/7\)", "u_wall", "PPO")):
        m = achar(rot, padrao)
        if m:
            confere(rot, numero(m.group(1)),
                    float(convergencia[(cen, algo)]))
    # «um único cenário bimodal» é uma afirmação ordinal: se outro cenário do
    # PPO deixar de convergir a 7/7, o valor 4/7 continua certo e a frase fica
    # falsa.
    conferidos += 1
    ppo_incompletos = [c for (c, a), n in convergencia.items()
                       if a == "PPO" and n < 7]
    if ppo_incompletos != ["u_wall"]:
        problemas.append("«o PPO tem um único cenário bimodal»: os cenários do "
                         "PPO abaixo de 7/7 são %s" % sorted(ppo_incompletos))
    else:
        print("   [ 4] bimodalidade: Sandbox/GNN, Gargalo/SAC e o Muro em U "
              "como único caso do PPO")

    m = achar("desvios de 1--2 recolhas/ep",
              r"desvios de (\d)--(\d) recolhas/ep na Porta Cooperativa e na "
              r"Porta com Alternativa")
    if m:
        conferidos += 2
        lo, hi = float(m.group(1)), float(m.group(2))
        # O intervalo está escrito em números inteiros, por isso julga-se com a
        # folga do arredondamento (0,5): o desvio de 0,95 da Porta Cooperativa
        # arredonda a 1 e cabe em «1--2». (A tab:res_eval imprime esse mesmo
        # desvio como 0,9; é a mesma medida com outro arredondamento.)
        for cen in ("cooperative_door", "cooperative_door_bypass"):
            dp = med.loc[cen, "GNN"].std(ddof=1)
            if not (lo - 0.5 <= dp <= hi + 0.5):
                problemas.append("«desvios de %g--%g recolhas/ep»: o GNN em %s "
                                 "tem %.2f" % (lo, hi, cen, dp))
        print("   [ 2] desvios do GNN nas duas portas dentro de %g--%g "
              "(%.2f e %.2f)" % (lo, hi,
                                 med.loc["cooperative_door", "GNN"].std(ddof=1),
                                 med.loc["cooperative_door_bypass",
                                         "GNN"].std(ddof=1)))

    # o custo computacional e a razão de núcleos-hora
    m = achar("núcleos-hora",
              r"consumiu (\d+) minutos com \$\\approx (\d+)\$ núcleos.{0,80}?"
              r"contra (\d+) minutos com (\d+) núcleos.{0,60}?razão de "
              r"\$\\approx (\d+)\\times\$")
    if m:
        import yaml
        cfg = yaml.safe_load(open(os.path.join(PROJECT_ROOT, "configs",
                                               "foraging.yaml"),
                                  encoding="utf-8"))
        # Os dois «números de núcleos» não são estimativas: são a população do
        # evolutivo e o num_cpu do PPO/SAC, que estão no config.
        confere("núcleos do evolutivo (= pop_size)", numero(m.group(2)),
                float(cfg["evolution"]["pop_size"]))
        confere("núcleos do PPO/SAC (= num_cpu)", numero(m.group(4)),
                float(cfg["ppo"]["num_cpu"]))
        razao = (numero(m.group(1)) * numero(m.group(2))) / (
            numero(m.group(3)) * numero(m.group(4)))
        confere("razão em núcleos-hora (≈8×)", numero(m.group(5)),
                round(razao), tol=0.0)
        print("   [ 3] núcleos-hora: %g×%g / (%g×%g) = %.1f ⇒ ≈%d×"
              % (numero(m.group(1)), numero(m.group(2)), numero(m.group(3)),
                 numero(m.group(4)), razao, round(razao)))

    # os intervalos de retenção que a secção repete
    m = achar("retenção 58--90 vs 39--45",
              r"reter \$(\d+)\$--\$(\d+)\\%\$ nos cenários com paredes \(contra "
              r"\$(\d+)\$--\$(\d+)\\%\$ nos abertos\)")
    if m:
        dados = _escala_por_cenario()
        ret = {}
        for cen, d in dados.items():
            g = d[d["Algorithm"] == "GNN"].set_index("N")
            ret[cen] = 100.0 * (g.loc[100, "food_per_agent"]
                                / g.loc[20, "food_per_agent"])
        abertos = {"none", "cooperative_perception"}
        com_paredes = [v for c, v in ret.items() if c not in abertos]
        so_abertos = [v for c, v in ret.items() if c in abertos]
        for k, (rot, calc) in enumerate((
                ("mínimo com paredes", min(com_paredes)),
                ("máximo com paredes", max(com_paredes)),
                ("mínimo nos abertos", min(so_abertos)),
                ("máximo nos abertos", max(so_abertos)))):
            confere("retenção: %s" % rot, numero(m.group(k + 1)), calc, tol=0.5)
        print("   [ 4] retenção %.0f--%.0f%% com paredes, %.0f--%.0f%% nos "
              "abertos" % (min(com_paredes), max(com_paredes),
                           min(so_abertos), max(so_abertos)))

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nAs %d afirmações derivadas batem com os testes e os CSV."
              % conferidos)
    print("NOTA: aqui não se conferem células — conferem-se as CONCLUSÕES tiradas")
    print("      delas. Uma célula que passe de significativa a não significativa")
    print("      não parte tabela nenhuma; parte a frase «em três cenários».")
    return problemas


def verificar_significancia(tolerancia):
    """tab:res_signif — as 21 comparações emparelhadas contra o CSV do teste.

    Não repete os testes: compara a tabela da tese com o CSV que o
    `statistical_tests.py` produziu. Reproduzir aqui o Mann-Whitney seria ter
    duas implementações a poder discordar, e a pergunta é se a tabela impressa é
    a que o teste produziu — que é onde entram as gralhas de transcrição.

    Verifica ainda a coerência interna da tabela: a coluna "Signif." e o p têm
    de concordar em torno de 0,05.
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

    A robustez não tem tabela: tem uma figura e duas afirmações em prosa
    ("entre 92% e 106% em todas as 21 combinações", "o controlador evolutivo
    retém 92--97%").

    Retenção = recolhas/ep com 10% de falhas / recolhas/ep de base, por célula.
    Células com base a zero ficam de fora, porque a divisão não tem significado
    — é o que o texto quer dizer com "com desempenho de base".
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
    # A legenda declara que a base é o campeão e não a média das sete execuções,
    # e cita o par do Muro em U para o mostrar: são dois números de FONTES
    # DIFERENTES na mesma frase, por isso cada um confirma-se contra o seu CSV.
    m = re.search(r"no Muro em U, \$(\d+)\$ contra \$([\d{},]+)\$ recolhas/ep",
                  tex)
    if m:
        base_uw = pd.read_csv(os.path.join(d_eval, "eval_gnn_u_wall.csv"))
        campeao = float(base_uw["food_collected"].mean())
        d7 = pd.read_csv(CSV_7D)
        g = d7[(d7["Scenario"] == "u_wall") & (d7["Algorithm"] == "GNN")]
        media7 = float(g.groupby("Run")["food_collected"].mean().mean())
        for rot, na_tese, medido, tol in (
                ("campeão do GNN no Muro em U", numero(m.group(1)), campeao, 0.5),
                ("média das 7 execuções", numero(m.group(2)), media7, 0.05)):
            if na_tese is None or abs(na_tese - medido) > tol:
                problemas.append("%s: legenda diz %s, medido %.2f"
                                 % (rot, m.group(1), medido))
        print("legenda: campeão %.1f  vs  média das 7 execuções %.1f"
              % (campeao, media7))
    else:
        problemas.append("não encontrei na legenda da robustez o par «campeão "
                         "vs média das sete execuções» (mudou a redação?)")

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

    A §res_complexos afirma, dentro das legendas, quantas recolhas teve o
    episódio de cada figura ("contorno do obstáculo em U (esq., 78 recolhas)").
    Não estão em tabela nem em prosa corrida, e regenerar as figuras com outros
    episódios não os atualizaria. A fonte é o JSON do episódio gravado, o mesmo
    de onde a figura sai (`scripts/captura_episodio.py`).
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

    As tabelas do artigo são cópias reformatadas das da tese e sobrevivem a
    correções dela sem darem sinal.

    Cada célula é `média ± dp (sucesso%) [runs a 100%]`. O `[n/7]` não existe na
    tese: é o número de execuções cuja taxa de sucesso é 100%, e não a taxa de
    sucesso média — no Muro U o PPO tem 71% de sucesso mas só 4 execuções em 7
    chegam aos 100%.
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

    # As mesmas afirmações que a tese faz em prosa, agora do lado do artigo: ele
    # repete-as por palavras suas («Quinze das vinte e uma») e uma correção na
    # tese não lhes toca.
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

    O `verificar_artigo` cobre a tab:task; no artigo o mega-treino não vive em
    tabela nenhuma, vive num parágrafo. A redação é a da tese comprimida
    (`\\pm` sem espaços à volta), pelo que os padrões são próprios: se a redação
    mudar, o regex deixa de casar e o verificador diz que não conseguiu ler —
    não passa em silêncio.
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

    São os números de maior peso do capítulo: o $28/28$ contra $15/28$ é o que
    sustenta a resposta final à QI6, e não têm tabela — vivem em prosa e em duas
    legendas.

    As contagens de convergência verificam-se exatamente (são inteiros); as
    médias e desvios com a mesma tolerância do resto do verificador.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §res_novelty (mega-treino, n=28)  vs  mega_1mes/*/eval_by_run.csv")
    print("=" * 72)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from analise_megatreino import FIXO_BYPASS, carregar, compara
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

    # M1: as duas médias vêm na MESMA frase, e as contagens na seguinte
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

    # A legenda da figura distingue os dois padrões de falha: o GNN objetivo e o
    # PPO repartem-se entre execuções que resolvem e execuções a zero, enquanto
    # no SAC nenhuma das 28 chega a metade da magnitude dos outros braços e a
    # distribuição é contínua. O que se confere são os números que descrevem a
    # FORMA da distribuição, não a média — que pode manter-se enquanto a forma
    # muda por completo.
    v = procura(r"o PPO com \$(\d+)\$ das \$(\d+)\$ acima de \$(\d+)\$ "
                r"recolhas/ep")
    if v:
        g_ppo = carregar("mega_A_fase3", "u_wall")
        limiar = v[2]
        confere("legenda: PPO acima do limiar", v[0],
                int((g_ppo["food"] > limiar).sum()), exato=True)
        confere("legenda: n do PPO", v[1], len(g_ppo), exato=True)
    else:
        problemas.append("legenda do mega-treino: não encontrei a contagem do "
                         "PPO acima do limiar")

    v = procura(r"nenhuma das suas \$(\d+)\$ execuções passa de \$" + N +
                r"\$ recolhas/ep")
    if v:
        g_sac = carregar("mega_A_fase4", "u_wall")
        confere("legenda: n do SAC", v[0], len(g_sac), exato=True)
        confere("legenda: máximo do SAC", v[1], float(g_sac["food"].max()))
        conferidos += 1
        # «nenhuma passa de X» tem de ser verdade, não só o máximo bater.
        if int((g_sac["food"] > v[1] + 0.05).sum()):
            problemas.append("legenda: o SAC tem execuções acima de %s" % v[1])
    else:
        problemas.append("legenda do mega-treino: não encontrei o máximo do SAC")

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

    # M3: adaptativo desta campanha vs peso fixo da de julho, na mesma frase
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

    # Os testes de M1, M2 e M3: os p e os δ, que são a metade que decide — o
    # «28/28 contra 15/28» só responde à QI6 acompanhado do Fisher exato, e uma
    # média pode continuar a bater com o CSV enquanto o p ao lado dela ficou de
    # uma versão anterior dos dados. Os testes não são reimplementados: importa-se
    # o `compara` do `analise_megatreino`, que os produziu, incluindo a escolha
    # entre método exato e assintótico.
    def teste(a, b, alternativa="two-sided"):
        if a is None or b is None:
            return None, None
        with contextlib.redirect_stdout(io.StringIO()):
            r = compara("", a, b, alternativa)
        return (r["p"], r["delta"]) if r else (None, None)

    def _tol_escrita(txt):
        """A tolerância sai das casas que a tese ESCREVEU, não de um número meu.

        «$p = 0{,}14$» é uma afirmação a duas casas: exigir-lhe 0,1403 seria
        acusar de erro um arredondamento correto.
        """
        casas = len((str(txt).replace("{,}", ".").split(".") + [""])[1])
        return 0.5 * 10 ** (-casas) if casas else 0.5

    def confere_p(rotulo, sinal, txt, calc):
        """«$p < 0{,}0001$» é uma desigualdade — e verifica-se como tal."""
        nonlocal conferidos
        conferidos += 1
        tese = numero(str(txt)) if txt is not None else None
        if tese is None or calc is None:
            problemas.append("%s: não consegui ler o p no main.tex ou "
                             "recalculá-lo (mudou a redação?)" % rotulo)
        elif sinal == "<":
            if not calc < tese:
                problemas.append("%-28s tese=p<%g  csv=p=%.6f  (a desigualdade "
                                 "é falsa)" % (rotulo, tese, calc))
        elif abs(tese - calc) > _tol_escrita(txt):
            problemas.append("%-28s tese=%s  csv=%.6f" % (rotulo, txt, calc))

    def confere_delta(rotulo, txt, calc):
        nonlocal conferidos
        conferidos += 1
        tese = numero(str(txt)) if txt is not None else None
        if tese is None or calc is None:
            problemas.append("%s: não consegui ler o δ no main.tex ou "
                             "recalculá-lo (mudou a redação?)" % rotulo)
        elif abs(abs(tese) - abs(calc)) > _tol_escrita(txt):
            problemas.append("%-28s tese=%s  csv=%+.4f" % (rotulo, txt, calc))
        elif (tese >= 0) != (calc >= 0):
            problemas.append("%-28s o SINAL do δ está trocado (tese=%s, "
                             "csv=%+.4f)" % (rotulo, txt, calc))

    def grupos(padrao):
        """Como o `procura`, mas devolve os grupos em bruto: o sinal de «$p <
        0{,}0001$» não é um número e o `numero()` deitá-lo-ia fora."""
        m = re.search(padrao, tex)
        return list(m.groups()) if m else None

    def num(g, i):
        """O i-ésimo grupo de um `grupos()`, já convertido — o `confere` espera
        um número, e um grupo em bruto rebentaria lá dentro."""
        return numero(str(g[i])) if g else None

    serie = {rot: carregar(fase, cen) for rot, (fase, cen) in (
        ("adaptativo", ("mega_A_fase1", "u_wall")),
        ("objetivo", ("mega_A_fase2", "u_wall")),
        ("PPO", ("mega_A_fase3", "u_wall")),
        ("SAC", ("mega_A_fase4", "u_wall")),
        ("bypass adaptativo", ("mega_B_fase5", "cooperative_door_bypass")))}
    if os.path.exists(FIXO_BYPASS):
        df = pd.read_csv(FIXO_BYPASS)
        col = "Run" if "Run" in df.columns else df.columns[0]
        serie["bypass fixo"] = df.groupby(col).agg(
            food=("food_collected", "mean"), suc=("success", "mean"))

    # M1 — magnitude (unilateral) e convergência (Fisher exato)
    g = grupos(r"do objetivo puro \(\$p (<|=) " + N +
               r"\$ unilateral, \$\\delta = \+" + N + r"\$\)")
    p_m1, d_m1 = teste(serie["adaptativo"], serie["objetivo"], "greater")
    confere_p("M1 p (unilateral)", g[0] if g else None,
              g[1] if g else None, p_m1)
    confere_delta("M1 δ", g[2] if g else None, d_m1)

    g = grupos(r"\(Fisher exato, \$p (<|=) " + N + r"\$\)")
    p_fisher = None
    if serie["adaptativo"] is not None and serie["objetivo"] is not None:
        from scipy.stats import fisher_exact
        ca = int((serie["adaptativo"]["suc"] >= 1.0).sum())
        cb = int((serie["objetivo"]["suc"] >= 1.0).sum())
        p_fisher = float(fisher_exact([[ca, len(serie["adaptativo"]) - ca],
                                       [cb, len(serie["objetivo"]) - cb]])[1])
    confere_p("M1 Fisher exato", g[0] if g else None,
              g[1] if g else None, p_fisher)

    # M2 — os três pares que a tese cita dos seis que corre (p BRUTOS: o
    # pré-registo manda assinalar a multiplicidade, não corrigi-la)
    for algo, padrao in (
            ("PPO", r"PPO \$[^$]+\$ \(\$\d+/\d+\$; \$p (<|=) " + N +
                    r"\$, \$\\delta = \+" + N + r"\$\)"),
            ("SAC", r"SAC \$[^$]+\$ \(\$\d+/\d+\$; \$p (<|=) " + N +
                    r"\$, \$\\delta = \+" + N + r"\$\)")):
        g = grupos(padrao)
        p, d = teste(serie["adaptativo"], serie[algo])
        confere_p("M2 adaptativo vs %s (p)" % algo, g[0] if g else None,
                  g[1] if g else None, p)
        confere_delta("M2 adaptativo vs %s (δ)" % algo, g[2] if g else None, d)

    g = grupos(r"permanecem indistinguíveis \(\$p (<|=) " + N + r"\$\)")
    p, _ = teste(serie["objetivo"], serie["PPO"])
    confere_p("M2 objetivo vs PPO (p)", g[0] if g else None,
              g[1] if g else None, p)

    # M3 — entre campanhas, como a tese declara
    g = grupos(r"do peso fixo \(\$p (<|=) " + N + r"\$, \$\\delta = \+" + N +
               r"\$\)")
    p, d = teste(serie.get("bypass adaptativo"), serie.get("bypass fixo"))
    confere_p("M3 p", g[0] if g else None, g[1] if g else None, p)
    confere_delta("M3 δ", g[2] if g else None, d)

    # O Resumo e o Abstract repetem as contagens dos quatro braços: são os
    # primeiros números que o leitor vê e vivem a cem páginas do capítulo que os
    # produz. Verificam-se os DOIS idiomas — uma tradução que fica para trás não
    # é um erro de número, e por isso nada a apanharia.
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

    # Células EXPLORATÓRIAS (A5 Sandbox, B7 Perceção, B6 SAC no Gargalo), em
    # cumprimento do compromisso do pré-registo de reportar todas as fases. Como
    # as confirmatórias, vivem só em prosa.
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

    # As exploratórias: a OUTRA metade de cada frase. O bloco acima confere a
    # célula nova (a $n=21$) e deixava por conferir aquilo contra o que ela é
    # lida: o braço da campanha final que lhe serve de referência, os p e os δ da
    # comparação, e as percentagens de convergência — que estavam FIXAS dentro
    # dos padrões. Uma percentagem fixa no regex não é verificada, é exigida: se
    # a contagem mudar, o padrão deixa de casar e o verificador diz «não
    # encontrei a frase» em vez de «o número está errado».
    #
    # A régua dos testes é a do resto do mega-treino (o `compara` do
    # `analise_megatreino`) e é bilateral: são comparações descritivas entre uma
    # célula exploratória e o braço de julho, sem hipótese direcional
    # pré-registada.
    def serie_final(algo, cen):
        """Médias por execução da campanha final ($n=7$), no formato do `compara`."""
        fp = os.path.join(PROJECT_ROOT, "results", "graficos_tese", "final_7d",
                          "eval_by_run_7d.csv")
        if not os.path.exists(fp):
            return None
        d = pd.read_csv(fp)
        d = d[(d["Algorithm"].astype(str).str.upper() == algo) &
              (d["Scenario"] == cen)]
        if d.empty:
            return None
        return d.groupby("Run").agg(food=("food_collected", "mean"),
                                    suc=("success", "mean")).sort_index()

    def confere_pct(rotulo, txt, conv, n):
        """A percentagem que a tese escreve ao lado de «$k/n$»."""
        nonlocal conferidos
        conferidos += 1
        tese = numero(str(txt)) if txt is not None else None
        if tese is None or not n:
            problemas.append("%s: não consegui ler a percentagem" % rotulo)
        elif abs(tese - 100.0 * conv / n) > 0.5:
            problemas.append("%-28s tese=%s%%  csv=%.1f%% (%d/%d)"
                             % (rotulo, txt, 100.0 * conv / n, conv, n))

    def descritivo(g):
        return (float(g["food"].mean()), float(g["food"].std()),
                int((g["suc"] >= 1.0).sum()), len(g))

    # A5 Sandbox — a célula a n=21 contra o GNN objetivo da campanha final
    g = grupos(r"eleva a convergência de \$(\d+)/(\d+)\$ \(\$(\d+)\\%\$\) do "
               r"objetivo puro para \$\\mathbf\{(\d+)/(\d+)\}\$ \(\$(\d+)\\%\$\), "
               r"com \$" + N + r" \\pm " + N + r"\$ contra \$" + N + r" \\pm " +
               N + r"\$ recolhas/ep \(\$p (<|=) " + N + r"\$, \$\\delta = \+" +
               N + r"\$\)")
    ref = serie_final("GNN", "none")
    cel = carregar("mega_A_fase5", "none")
    if ref is None:
        problemas.append("A5 Sandbox: falta o braço objetivo da campanha final")
    else:
        med_r, dp_r, conv_r, n_r = descritivo(ref)
        confere("A5 ref objetivo convergentes", num(g, 0), conv_r, exato=True)
        confere("A5 ref objetivo n", num(g, 1), n_r, exato=True)
        confere_pct("A5 ref objetivo %", g[2] if g else None, conv_r, n_r)
        if cel is not None:
            _, _, conv_c, n_c = descritivo(cel)
            confere_pct("A5 Sandbox %", g[5] if g else None, conv_c, n_c)
        confere("A5 ref objetivo média", num(g, 8), med_r)
        confere("A5 ref objetivo desvio", num(g, 9), dp_r)
        p, d = teste(cel, ref)
        confere_p("A5 Sandbox p", g[10] if g else None, g[11] if g else None, p)
        confere_delta("A5 Sandbox δ", g[12] if g else None, d)

    # B7 Perceção Cooperativa — idem, contra o mesmo braço no cenário dela
    g = grupos(r"\$(\d+)/(\d+)\$ \(\$(\d+)\\%\$\) e \$" + N + r" \\pm " + N +
               r"\$ contra \$(\d+)/(\d+)\$ \(\$(\d+)\\%\$\) e \$" + N +
               r" \\pm " + N + r"\$ do objetivo \(\$p (<|=) " + N +
               r"\$, \$\\delta = \+" + N + r"\$\)")
    ref = serie_final("GNN", "cooperative_perception")
    cel = carregar("mega_B_fase7", "cooperative_perception")
    if ref is None:
        problemas.append("B7 Perceção: falta o braço objetivo da campanha final")
    else:
        med_r, dp_r, conv_r, n_r = descritivo(ref)
        if cel is not None:
            _, _, conv_c, n_c = descritivo(cel)
            confere_pct("B7 Perceção %", g[2] if g else None, conv_c, n_c)
        confere("B7 ref objetivo convergentes", num(g, 5), conv_r, exato=True)
        confere("B7 ref objetivo n", num(g, 6), n_r, exato=True)
        confere_pct("B7 ref objetivo %", g[7] if g else None, conv_r, n_r)
        confere("B7 ref objetivo média", num(g, 8), med_r)
        confere("B7 ref objetivo desvio", num(g, 9), dp_r)
        p, d = teste(cel, ref)
        confere_p("B7 Perceção p", g[10] if g else None, g[11] if g else None, p)
        confere_delta("B7 Perceção δ", g[12] if g else None, d)

    # B6 SAC no Gargalo — aqui a tese diz explicitamente que os dois valores
    # NÃO são comparáveis (orçamentos diferentes); o que se verifica é que
    # ambos são o que o texto diz que são.
    ref = serie_final("SAC", "bottleneck")
    cel = carregar("mega_B_fase6", "bottleneck")
    if ref is None:
        problemas.append("B6 SAC Gargalo: falta o braço da campanha final")
    else:
        med_r, dp_r, conv_r, n_r = descritivo(ref)
        g = grupos(r"resolvera em apenas \$(\d+)/(\d+)\$")
        confere("B6 ref SAC convergentes", num(g, 0), conv_r, exato=True)
        confere("B6 ref SAC n", num(g, 1), n_r, exato=True)
        g = grupos(r"comparável com os \$" + N + r" \\pm " + N +
                   r"\$ da campanha final")
        confere("B6 ref SAC média", num(g, 0), med_r)
        confere("B6 ref SAC desvio", num(g, 1), dp_r)
        if cel is not None:
            _, _, conv_c, n_c = descritivo(cel)
            g = grupos(r"converge em \$\d+/\d+\$ \(\$(\d+)\\%\$\)")
            confere_pct("B6 SAC Gargalo %", g[0] if g else None, conv_c, n_c)

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do mega-treino batem com os CSV." % conferidos)
    return problemas


# Novelty Search (QI6). A secção não tem tabela — os números vivem em prosa — e
# é aqui que os p e os δ são RECALCULADOS, ao contrário do resto do ficheiro:
# para o Novelty não existe CSV de testes, e recalcular é a única verificação
# possível. O `cliffs_delta` vem importado do `statistical_tests`, para não haver
# uma segunda implementação dele.

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


def _runs_a_100(chave, cen):
    r"""Execuções com $100\%$ de sucesso — a «convergência» desta secção.

    Não quer dizer o mesmo que no mapa composto: lá conta-se «pelo menos uma
    recolha», porque quase tudo dá zero; aqui o `[6/7]` do pré-registo são as
    execuções que resolvem o cenário em TODOS os episódios. Contar recolhas > 0
    no Sandbox daria 7/7.
    """
    fp = os.path.join(RAIZ_NOV, *FONTES_NOV[chave])
    if not os.path.exists(fp):
        return None
    d = pd.read_csv(fp)
    d = d[d["Algorithm"].astype(str).str.upper() == "GNN"]
    if "Scenario" in d.columns:
        d = d[d["Scenario"] == cen]
    if d.empty or "success" not in d.columns:
        return None
    por_run = d.groupby("Run")["success"].mean()
    return float((por_run >= 1.0).sum())


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
        "re": r"\$(?P<conv>\d+)/7\$ (?:\\\\textit\\{runs?\\}|execuç(?:ão|ões)), \$(?P<m>[\d{},]+) \\pm "
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
    # Os que têm CSV por trás: o Sandbox de T1 (o único cenário onde o adaptativo
    # SOBE, e por isso o mais citado de volta) e as duas metades de T4, o teste
    # que compara os dois mecanismos de novidade entre si.
    {
        "rot": "T1 — Sandbox (o adaptativo sobe descritivamente)",
        "re": r"no Sandbox o adaptativo até sobe descritivamente "
              r"\(\$(?P<m>[\d{},]+) \\pm (?P<s>[\d{},]+)\$, (?P<conv>\d+)/7, "
              r"vs\.\\ \$(?P<mo>[\d{},]+) \\pm (?P<so>[\d{},]+)\$, "
              r"(?P<convb>\d+)/7\)",
        "A": ("adapt_A1", "none"), "B": ("objetivo", "none"),
        "unilateral": False, "conv_a_100": True,
    },
    {
        # O `5/7` da Perceção Cooperativa: um número da campanha de 19 de julho
        # citado a meio de uma frase sobre outra campanha — o tipo de valor que
        # ninguém regenera e que sobrevive a qualquer recálculo.
        "rot": "Perceção Cooperativa — o 5/7 de 19 de julho",
        "re": r"se o \$(?P<conv>\d+)/7\$ observado a 19 de julho",
        "A": ("adapt_B1", "cooperative_perception"), "B": None,
        "unilateral": False, "conv_a_100": True,
    },
    {
        "rot": "T4 — adaptativo vs peso fixo no Muro em U",
        "re": r"indistinguível no Muro em U \(\$p=(?P<p>[\d{},]+)\$\)",
        "A": ("adapt_A1", "u_wall"), "B": ("fixo_uwall", "u_wall"),
        "unilateral": False,
    },
    {
        "rot": "T4 — adaptativo vs peso fixo no bypass",
        "re": r"superior em magnitude n[ao] (?:bypass|Porta com Alternativa) "
              r"\(\$(?P<m>[\d{},]+)\$ vs\.\\ "
              r"\$(?P<mo>[\d{},]+)\$; \$p=(?P<p>[\d{},]+)\$, "
              r"\$\\delta=\+(?P<d>[\d{},]+)\$",
        "A": ("adapt_B1", "cooperative_door_bypass"),
        "B": ("fixo_bypass", "cooperative_door_bypass"),
        "unilateral": False,
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
        # `conv100`: a frase conta execuções a 100% de sucesso (o `[6/7]` do
        # pré-registo); `conv`: execuções com pelo menos uma recolha.
        cem = af.get("conv_a_100")
        if g.get("conv") is not None:
            alvos.append(("convergentes",
                          g["conv"],
                          _runs_a_100(*af["A"]) if cem
                          else float((a_serie > 0).sum())))
        if g.get("convb") is not None and b_serie is not None:
            alvos.append(("convergentes (B)",
                          g["convb"],
                          _runs_a_100(*af["B"]) if cem
                          else float((b_serie > 0).sum())))
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
            # A tolerância sai das casas decimais que a tese ESCREVEU: «$p=0{,}32$»
            # é uma afirmação a duas casas, e exigir-lhe 0,3176 seria acusar de
            # erro um arredondamento correto. Para as médias fica o maior entre
            # essa regra e a tolerância da linha de comandos, que absorve a ordem
            # das agregações.
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

    # T1: «o menor dos cinco é $p = 0{,}21$». Uma afirmação sobre CINCO testes de
    # uma vez: se um dos cinco descer, a frase passa a ser falsa sem que nenhum
    # número escrito na tese mude.
    #
    # A frase dizia «todos $p \geq 0{,}21$», e o menor dos cinco é $0{,}2086$ —
    # verdadeiro a duas casas, falso a quatro. O padrão aceita as duas formas,
    # para a régua não falhar a ler uma tese antiga.
    m = re.search(r"nenhuma diferença é significativa \((?:todos \$p \\geq|"
                  r"o menor dos cinco é \$p =) (?P<p>[\d{},]+)\$\)", sec)
    if m:
        cinco = [("adapt_A1", "none"), ("adapt_A1", "bottleneck"),
                 ("adapt_A1", "four_rooms"), ("adapt_B1", "cooperative_door"),
                 ("adapt_B1", "cooperative_perception")]
        ps = []
        for chave, cen in cinco:
            a, b = _por_run(chave, cen), _por_run("objetivo", cen)
            if a is None or b is None:
                continue
            valor = _mw(a, b, False)
            if valor is not None:
                ps.append((cen, valor))
        if len(ps) == 5:
            conferidos += 1
            menor_cen, menor = min(ps, key=lambda x: x[1])
            tese = numero(str(m.group("p")))
            # Exige-se que o valor citado SEJA o menor dos cinco p, arredondado
            # às duas casas com que a tese o escreve.
            if abs(round(menor, 2) - tese) > 0.005:
                problemas.append(
                    "T1 — a tese cita %s e o menor dos cinco é %.4f (%s)"
                    % (m.group("p"), menor, menor_cen))
            else:
                print("   [5] T1 — o menor dos cinco p é %.4f (%s), e a tese "
                      "cita %s" % (menor, menor_cen, m.group("p")))
        else:
            problemas.append("T1 — «todos p ≥ …»: só consegui recalcular %d "
                             "dos 5 testes" % len(ps))

    # A ablação do anilamento (as quatro variantes): «não é sensível à afinação»
    # é uma conclusão sobre 8 células de uma vez, e nenhuma delas tem tabela. Os
    # limites citados são o mínimo e o máximo das médias das quatro variantes —
    # se uma variante entrar ou sair, os limites mudam e mais nada no texto muda
    # com eles.
    m = re.search(r"as quatro variantes convergem em \$7/7\$ execuções nos dois "
                  r"cenários, com médias entre \$(?P<u0>[\d{},]+)\$ e "
                  r"\$(?P<u1>[\d{},]+)\$ recolhas/ep no Muro em U e entre "
                  r"\$(?P<b0>[\d{},]+)\$ e \$(?P<b1>[\d{},]+)\$", sec)
    if m:
        fases = ["mega_B_fase%d" % i for i in (1, 2, 3, 4)]
        for cen, g0, g1 in (("u_wall", "u0", "u1"),
                            ("cooperative_door_bypass", "b0", "b1")):
            medias, cem_a_cem = [], True
            for fase in fases:
                fp = os.path.join(PROJECT_ROOT, "results", "mega_1mes", fase,
                                  "evaluation", "eval_by_run.csv")
                if not os.path.exists(fp):
                    continue
                d = pd.read_csv(fp)
                d = d[(d["Algorithm"].astype(str).str.upper() == "GNN") &
                      (d["Scenario"] == cen)]
                if d.empty:
                    continue
                medias.append(d.groupby("Run")["food_collected"].mean().mean())
                if (d.groupby("Run")["success"].mean() >= 1.0).sum() != 7:
                    cem_a_cem = False
            if len(medias) != 4:
                problemas.append("Ablação (%s): encontrei %d das 4 variantes"
                                 % (cen, len(medias)))
                continue
            conferidos += 3
            if not cem_a_cem:
                problemas.append("Ablação (%s): a tese diz 7/7 em todas as "
                                 "variantes, e alguma não o é" % cen)
            bateu = True
            for grupo, esperado in ((g0, min(medias)), (g1, max(medias))):
                tese = numero(str(m.group(grupo)))
                if tese is None or abs(tese - esperado) > max(0.05, tolerancia):
                    bateu = False
                    problemas.append("Ablação (%s) %s: tese=%s dados=%.2f"
                                     % (cen, grupo, m.group(grupo), esperado))
            if bateu and cem_a_cem:
                print("   [4] Ablação do anilamento (%s): médias de %.1f a %.1f, "
                      "7/7 nas quatro" % (cen, min(medias), max(medias)))

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


# Coerência interna: o mesmo facto, contado duas vezes. A «Resposta às Questões
# de Investigação» é o Capítulo 5 recontado, e confrontá-la outra vez com os CSV
# deixaria passar o defeito que ela pode mesmo ter — um resultado corrigido num
# capítulo e esquecido no eco do outro. Aqui não se compara com dados: procura-se
# cada facto em toda a tese e exige-se que as ocorrências concordem entre si.

# Cada facto declara os SÍTIOS onde é dito, um padrão por sítio. Um padrão só, à
# solta sobre a tese toda, apanha factos diferentes escritos na mesma forma de
# frase (o mega-treino com $n=28$ e a campanha final com $n=7$, o adaptativo a
# 390 minutos e o de 195) e acusa contradições que não existem — daí cada sítio
# ter a sua âncora.
#
# `ordem` diz por que ordem os grupos daquele sítio correspondem aos do
# primeiro: a mesma comparação aparece escrita nas duas direções («A contra B» e
# «B vs. A»), e isso não é uma divergência.
FACTOS_REPETIDOS = [
    {"rot": "Muro em U — novidade fixa vs objetivo",
     "sitios": [
         {"re": r"hibridiza[çc][ãa]o elevou a taxa.{0,120}?com \$([\d{},]+) "
                r"\\pm ([\d{},]+)\$ recolhas/ep contra \$([\d{},]+) \\pm "
                r"([\d{},]+)\$ do objetivo puro"},
         {"re": r"7/7 (?:\\\\textit\\{runs?\\}|execuç(?:ão|ões)) a 100\\% de sucesso e \$([\d{},]+) \\pm "
                r"([\d{},]+)\$ recolhas/ep, contra 3/7 e \$([\d{},]+) \\pm "
                r"([\d{},]+)\$"},
     ]},
    {"rot": "Porta c/ Alternativa — objetivo vs novidade fixa",
     "sitios": [
         {"re": r"\$([\d{},]+) \\pm ([\d{},]+)\$ contra \$([\d{},]+) \\pm "
                r"([\d{},]+)\$ recolhas/ep com novidade"},
         {"re": r"degradou a magnitude \(\$([\d{},]+) \\pm ([\d{},]+)\$ vs\.\\ "
                r"\$([\d{},]+) \\pm ([\d{},]+)\$", "ordem": (2, 3, 0, 1)},
     ]},
    {"rot": "Adaptativo no Muro em U (T2, 195 min)",
     "sitios": [
         {"re": r"\(T2\).{0,80}?\$7/7\$ (?:\\\\textit\\{runs?\\}|execuç(?:ão|ões)) a 100\\% e "
                r"\$([\d{},]+) \\pm ([\d{},]+)\$"},
         {"re": r"manteve os \$7/7\$ (?:\\\\textit\\{runs?\\}|execuç(?:ão|ões)) no Muro em U "
                r"\(\$([\d{},]+) \\pm ([\d{},]+)\$"},
     ]},
    {"rot": "Melhor bypass da dissertação (adaptativo, 390 min)",
     "sitios": [
         {"re": r"melhor resultado desta disserta[çc][ãa]o\}? \(\$([\d{},]+) "
                r"\\pm ([\d{},]+)\$"},
         {"re": r"melhor resultado da disserta[çc][ãa]o na Porta com "
                r"Alternativa \(\$([\d{},]+) \\pm ([\d{},]+)\$\)"},
         # e uma terceira vez, no parágrafo de abertura das Conclusões
         {"re": r"melhor resultado da disserta[çc][ãa]o \(\$([\d{},]+) \\pm "
                r"([\d{},]+)\$ recolhas/ep\)"},
     ]},
    {"rot": "Mega-treino — adaptativo vs objetivo puro no Muro em U",
     "sitios": [
         {"re": r"\\textbf\{\$?(\d+)/28\$? execu[çc][õo]es a 100\\% de sucesso "
                r"contra \$?(\d+)/28\$?\}"},
         {"re": r"resolve o Muro em U em \$(\d+)/28\$ execu[çc][õo]es contra "
                r"\$(\d+)/28\$"},
         {"re": r"\$(\d+)/28\$ execuções resolvidas contra \$(\d+)/28\$ do "
                r"objetivo puro"},
     ]},
    # Os ecos do parágrafo de abertura das Conclusões, que reconta oito
    # resultados de uma vez.
    {"rot": "Núcleos-hora — a razão dita em três sítios",
     "sitios": [
         {"re": r"uma razão de \$\\approx (\d+)\\times\$ em núcleos-hora"},
         {"re": r"eficiência computacional\}? \(\$\\approx (\d+)\\times\$ menos "
                r"núcleos-hora"},
         {"re": r"vantagem de \$\\approx (\d+)\\times\$ em núcleos-hora"},
     ]},
    {"rot": "Escalabilidade — a janela de N e o sucesso mantido",
     "sitios": [
         # a Discussão Global escreve o sucesso primeiro e a janela depois; as
         # Conclusões ao contrário. É a mesma afirmação, não uma divergência.
         {"re": r"mantendo (\d+)\\% de sucesso de \$N=(\d+)\$ a \$N=(\d+)\$ sem "
                r"retreino", "ordem": (1, 2, 0)},
         {"re": r"escala de \$N=(\d+)\$ a \$N=(\d+)\$ sem retreino, mantendo "
                r"(\d+)\\% de sucesso"},
     ]},
    {"rot": "T2 — o p do adaptativo no Muro em U, em três sítios",
     "sitios": [
         {"re": r"do objetivo \(\$p=([\d{},]+)\$ unilateral"},
         {"re": r"\$p=([\d{},]+)\$, \$\\delta=\+[\d{},]+\$ vs\.\\ objetivo"},
         {"re": r"manteve os 7/7 no Muro (?:em )?U \(\$p=([\d{},]+)\$ face ao objetivo\)"},
     ]},
    {"rot": "Mega-treino — o 14/28 dos gradientes nas Conclusões",
     # a frase das Conclusões diz «de cada método de gradiente»; o SAC ter a
     # mesma contagem é conferido contra o CSV pelo `verificar_megatreino`, e
     # aqui só se garante que o número recontado não ficou para trás.
     "sitios": [
         {"re": r"PPO \$[^$]+\$ \(\$(\d+)/(\d+)\$;"},
         {"re": r"\$(\d+)/(\d+)\$ de cada método de gradiente"},
     ]},
    {"rot": "Escalabilidade — as 28 combinações a 100%",
     "sitios": [
         {"re": r"O resultado é inequívoco.{0,120}?100\\% de sucesso nas (\d+) "
                r"combina[çc][õo]es"},
         # `\.?` — o rótulo pode não ter ponto final (a classe `amsbook`
         # já lhe acrescenta dois pontos, e saía «Escalabilidade.:»).
         {"re": r"QI2 --- Escalabilidade\.?\].{0,260}?100\\% de sucesso nas "
                r"(\d+) combina[çc][õo]es"},
         # e uma terceira vez na Discussão do mapa composto, onde o
         # número serve para dizer o que o resultado negativo NÃO derruba
         {"re": r"\$100\\%\$ de sucesso nas \$(\d+)\$\s*\n?\s*combinações cenário"},
     ]},
    # Os ecos do Capítulo 6. A «Resposta às Questões de Investigação» e as
    # «Conclusões» são o Capítulo 5 recontado: o risco não é o número estar
    # errado à nascença, é ficar para trás quando o resultado é corrigido lá
    # atrás.
    {"rot": "QI7 — o mapa composto resolvido em k de n execuções",
     "sitios": [
         {"re": r"GNN, mas só em (\d+) das \$(\d+)\$\s*\n?\s*execuções"},
         {"re": r"resolve o mapa em (\d+) das \$(\d+)\$\s*\n?\s*execuções"},
         # o item dos Contributos diz o mesmo pela terceira vez
         {"re": r"resolve o mapa, em \$(\d+)\$ de \$(\d+)\$ execuções"},
     ]},
    {"rot": "QI2 — retenção per capita em N=100 (paredes e abertos)",
     "sitios": [
         # Contributos: «a reter 58--90% … (contra 39--45% nos abertos)»
         {"re": r"per capita em \$N=100\$ a reter \$(\d+)\$--\$(\d+)\\%\$ nos "
                r"cenários com paredes \(contra \$(\d+)\$--\$(\d+)\\%\$"},
         # QI2: a mesma janela, com os dois cenários abertos nomeados um a um.
         {"re": r"per capita em \$N=100\$ retém \$(\d+)\$--\$(\d+)\\%\$ nos "
                r"cenários com paredes.{0,180}?\$(\d+)\\%\$ no Sandbox, "
                r"\$(\d+)\\%\$ na Perceção"},
     ]},
    # A mesma janela dita uma quarta vez, nos Contributos, e escrita de outra
    # maneira («entre 58% e 90%» em vez de «58--90%»). Compara-se só a janela: o
    # parágrafo dos Contributos não repete os cenários abertos, e um facto com
    # mais valores de um lado acusaria uma divergência que não existe.
    {"rot": "Contributos — a janela de retenção per capita (58--90%)",
     "sitios": [
         {"re": r"retendo entre \$(\d+)\\%\$ e \$(\d+)\\%\$ da eficiência per "
                r"capita"},
         {"re": r"per capita em \$N=100\$ a reter \$(\d+)\$--\$(\d+)\\%\$"},
         {"re": r"per capita em \$N=100\$ retém \$(\d+)\$--\$(\d+)\\%\$"},
     ]},
    # O δ do Sandbox exploratório é dito nos Resultados e outra vez nos Trabalhos
    # Futuros, onde sustenta a proposta de alargar o braço de controlo.
    {"rot": "Sandbox exploratório — o δ que os Trabalhos Futuros citam",
     "sitios": [
         {"re": r"\$p = 0\{,\}14\$, \$\\delta = \+([\d{},]+)\$\): a assimetria"},
         {"re": r"mantém o \$\\delta = \+([\d{},]+)\$ do Sandbox longe do "
                r"limiar convencional"},
     ]},
    {"rot": "Robustez — a janela de retenção com 10% de falhas",
     "sitios": [
         # Só a JANELA (92--106) é o mesmo facto nos dois sítios: o Cap. 5
         # acrescenta as 21 combinações e o Cap. 6 a fração de falha, e juntar
         # tudo acusaria uma contradição onde há duas frases complementares.
         {"re": r"retenção de recolhas situa-se entre \\textbf\{(\d+)\\% e "
                r"(\d+)\\%\}"},
         {"re": r"falhas de 10\\% dos agentes.{0,90}?retenção de "
                r"(\d+)--(\d+)\\%"},
     ]},
    # Os ecos dos TESTES da QI6: a resposta à QI6 reconta oito comparações do
    # Capítulo 5, cada uma com o seu p e o seu δ. Os factos acima cruzam as
    # médias; estes cruzam os testes, que são o que muda quando os dados mudam —
    # uma média pode sobreviver a um recálculo e o p não.
    {"rot": "QI6 — o teste do Muro em U com peso fixo",
     "sitios": [
         {"re": r"do objetivo puro \(\$p = ([\d{},]+)\$, \$\\delta = \+"
                r"([\d{},]+)\$\)\. A pressão"},
         {"re": r"\(Mann--Whitney \$p=([\d{},]+)\$, \$\\delta=\+([\d{},]+)\$\)"},
     ]},
    {"rot": "QI6 — o teste da Porta com Alternativa com peso fixo",
     "sitios": [
         {"re": r"recolhas/ep com novidade \(\$p = ([\d{},]+)\$, \$\\delta = -"
                r"([\d{},]+)\$"},
         {"re": r"\$p=([\d{},]+)\$, \$\\delta=-([\d{},]+)\$\), desmascarando"},
     ]},
    {"rot": "QI6 — T2, o teste do adaptativo no Muro em U",
     "sitios": [
         {"re": r"do objetivo \(\$p=([\d{},]+)\$ unilateral, \$\\delta=\+"
                r"([\d{},]+)\$\)"},
         {"re": r"\$p=([\d{},]+)\$, \$\\delta=\+([\d{},]+)\$ vs\.\\ objetivo"},
     ]},
    {"rot": "QI6 — T4, o adaptativo contra o peso fixo no bypass",
     "sitios": [
         {"re": r"superior em magnitude n[ao] (?:bypass|Porta com Alternativa) "
                r"\(\$([\d{},]+)\$ vs\.\\ \$"
                r"([\d{},]+)\$; \$p=[\d{},]+\$, \$\\delta=\+([\d{},]+)\$"},
         {"re": r"superou o peso fixo em magnitude n[ao] (?:bypass|Porta com Alternativa) \(\$([\d{},]+)\$ "
                r"vs\.\\ \$([\d{},]+)\$; \$\\delta=\+([\d{},]+)\$\)"},
     ]},
    {"rot": "QI6 — o controlo de orçamento continua bimodal",
     "sitios": [
         {"re": r"\(390 min/(?:\\\\textit\\{runs?\\}|execuç(?:ão|ões))\) continua bimodal --- \$(\d+)/(\d+)\$"},
         {"re": r"continua bimodal no Muro em U \(\$(\d+)/(\d+)\$\)"},
         {"re": r"continuou bimodal no Muro (?:em )?U \((\d+)/(\d+)\)"},
     ]},
    {"rot": "Mega-treino — o p do Fisher exato",
     "sitios": [
         {"re": r"\(Fisher exato, \$p < ([\d{},]+)\$\)"},
         {"re": r"\(Fisher exato, \$p<([\d{},]+)\$\)"},
     ]},
    {"rot": "Mega-treino — as contagens do PPO e do SAC (três sítios)",
     "sitios": [
         {"re": r"PPO \$[^$]+\$ \(\$(\d+)/(\d+)\$;.{0,90}?SAC \$[^$]+\$ "
                r"\(\$(\d+)/(\d+)\$"},
         {"re": r"\$(\d+)/(\d+)\$ do PPO e \$(\d+)/(\d+)\$ do SAC\)"},
         {"re": r"\$(\d+)/(\d+)\$ do PPO e \$(\d+)/(\d+)\$ do SAC, sendo a única"},
     ]},
    {"rot": "Mega-treino — M3 (adaptativo vs peso fixo no bypass)",
     "sitios": [
         {"re": r"o adaptativo faz \$([\d{},]+) \\pm [\d{},]+\$ recolhas/ep em "
                r"\$\d+/\d+\$ execuções contra \$([\d{},]+) \\pm [\d{},]+\$ do "
                r"peso fixo \(\$p = ([\d{},]+)\$, \$\\delta = \+([\d{},]+)\$\)"},
         {"re": r"com significância \(\$([\d{},]+)\$ vs\.\\ \$([\d{},]+)\$; \$p="
                r"([\d{},]+)\$, \$\\delta=\+([\d{},]+)\$\)"},
     ]},
    # O mapa composto, recontado fora da sua secção: ela entra por `\input` e
    # vive noutro ficheiro, mas os seus resultados são recontados na Discussão
    # Global, na resposta à QI7 e nas Conclusões.
    {"rot": "Mapa composto — o zero da transferência (F1)",
     "sitios": [
         {"re": r"o que perfaz\s*\n?\s*\$(\d+)\$ células a zero em \$(\d+)\$ "
                r"episódios"},
         {"re": r"as \$(\d+)\$ células do estudo de transferência ficam todas a "
                r"\$0\{,\}00\$ recolhas por episódio, em \$(\d+)\$ episódios"},
     ]},
    {"rot": "Mapa composto — quem resolve o mapa com treino nativo",
     "sitios": [
         {"re": r"GNN em (\d+)/(\d+), das quais \d+ a \$100\\%\$ de sucesso; PPO "
                r"em (\d+)/(\d+),.{0,60}?SAC em (\d+)/(\d+),"},
         {"re": r"em \$(\d+)\$ das \$(\d+)\$ execuções, contra \$(\d+)\$ de \$(\d+)"
                r"\$ do PPO e \$(\d+)\$ de \$(\d+)\$ do SAC"},
     ]},
    {"rot": "Mapa composto — o limiar fixado antes dos dados (três sítios)",
     "sitios": [
         {"re": r"abaixo do limiar de \$(\d+)\$ que\s*\n?\s*o pré-registo fixou"},
         {"re": r"abaixo do limiar de \$(\d+)\$ execuções convergentes que o "
                r"pré-registo fixou"},
         {"re": r"abaixo do limiar de \$(\d+)\$ fixado antes dos dados"},
     ]},
    {"rot": "Mapa composto — o orçamento que não chegou ao planalto",
     "sitios": [
         {"re": r"Em \$(\d+)\$ das \$(\d+)\$ execuções o melhor \\textit\{fitness\}"},
         {"re": r"em \$(\d+)\$ das \$(\d+)\$ execuções o melhor\s*\n?\s*"
                r"\\textit\{fitness\} ainda subia"},
     ]},
    {"rot": "Mapa composto — M1, o teste entre paradigmas",
     "sitios": [
         {"re": r"GNN \\emph\{vs\.\}\\ PPO: \$p = ([\d{},]+)\$, \$\\delta = \+"
                r"([\d{},]+)\$"},
         {"re": r"\(\$p = ([\d{},]+)\$ e \$\\delta = \+([\d{},]+)\$ entre o "
                r"evolutivo"},
     ]},
    # Os números da QI6 ditos três e quatro vezes. A secção do Novelty conta a
    # mesma história em camadas — comparação preliminar, campanhas com orçamento
    # igualado, campanha adaptativa, mega-treino — e alguns números atravessam-nas
    # todas: são os que ficam para trás quando uma camada é recalculada.
    {"rot": "QI6 — o +26% da comparação preliminar (três sítios)",
     "sitios": [
         {"re": r"do objetivo puro --- \$\+(\d+)\\%\$, Wilcoxon"},
         {"re": r"O ganho de \$\+(\d+)\\%\$ da comparação preliminar"},
         {"re": r"desmascarando o \$\+(\d+)\\%\$ da comparação preliminar"},
     ]},
    {"rot": "QI6 — o objetivo puro na Porta com Alternativa (três sítios)",
     "sitios": [
         {"re": r"em magnitude --- \$([\d{},]+) \\pm ([\d{},]+)\$ contra"},
         {"re": r"vs\.\\ \$([\d{},]+) \\pm ([\d{},]+)\$ \(\$p=0\{,\}32\$"},
         {"re": r"superando o próprio objetivo puro \(\$([\d{},]+) \\pm "
                r"([\d{},]+)\$\)"},
     ]},
    {"rot": "QI6 — o δ de T4 no bypass (quatro sítios)",
     "sitios": [
         {"re": r"\$\\delta=\+([\d{},]+)\$ --- com \$n=7\$"},
         {"re": r"o \$\\delta = \+([\d{},]+)\$ de \(T4\) ficou à espera"},
         {"re": r"pelo que o \$\\delta = \+([\d{},]+)\$ de \(T4\) --- que a \$n=7\$"},
         {"re": r"n[ao] (?:bypass|Porta com Alternativa) \(\$77\{,\}2\$ vs\.\\ "
                r"\$63\{,\}0\$; \$\\delta=\+([\d{},]+)\$\)"},
     ]},
    {"rot": "QI6 — o δ do peso fixo no bypass",
     "sitios": [
         {"re": r"\$\\delta = -([\d{},]+)\$: todas as execuções objetivas"},
         {"re": r"em contraste direto com o \$\\delta=-([\d{},]+)\$ do peso fixo"},
     ]},
    {"rot": "Planalto — células ainda a subir no fim do orçamento",
     "sitios": [
         {"re": r"\\textbf\{(\d+) das (\d+) combina[çc][õo]es ainda subiam de "
                r"forma significativa no fim\}.{0,140}?Gargalo \(\$\+(\d+)"
                r"\\%\$\) e na Porta com Alternativa \(\$\+(\d+)\\%\$\)"},
         {"re": r"em \$(\d+)\$ das \$(\d+)\$ combina[çc][õo]es a curva ainda "
                r"subia.{0,160}?Gargalo \(\$\+(\d+)\\%\$\) e na Porta com "
                r"Alternativa \(\$\+(\d+)\\%\$\)"},
     ]},
]


def verificar_sandbox(tolerancia):
    """§Sandbox — a tabela própria do cenário e a FORMA da distribuição.

    O argumento do cenário («o mais simples é o menos fiável para o evolutivo»)
    não está na média: está na decomposição das sete execuções — quatro
    competitivas, duas degeneradas e uma intermédia. A `tab:res_sandbox` é a
    única tabela de resultados da tese com rótulos de algoritmo em vez de
    cenário, e por isso escapava ao leitor de tabelas genérico.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Sandbox (tab:res_sandbox + a forma da distribuição)")
    print("=" * 72)

    fp = os.path.join(PROJECT_ROOT, "results", "graficos_tese", "final_7d",
                      "eval_by_run_7d.csv")
    if not os.path.exists(fp):
        print("[!] falta o %s — a saltar." % os.path.relpath(fp, PROJECT_ROOT))
        return []
    d = pd.read_csv(fp)
    d = d[d["Scenario"] == "none"]

    por_algo = {}
    for algo in ("GNN", "PPO", "SAC"):
        s = d[d["Algorithm"].astype(str).str.upper() == algo]
        if s.empty:
            continue
        por_algo[algo] = s.groupby("Run").agg(food=("food_collected", "mean"),
                                              suc=("success", "mean"))

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas, conferidos = [], 0

    def confere(rot, tese, calc, exato=False, tol=None):
        nonlocal conferidos
        conferidos += 1
        if tese is None or calc is None:
            problemas.append("%s: não consegui ler no main.tex "
                             "(mudou a redação?)" % rot)
        elif exato and int(tese) != int(calc):
            problemas.append("%-38s tese=%d  csv=%d" % (rot, tese, calc))
        elif not exato and abs(tese - calc) > (tol if tol else tolerancia):
            problemas.append("%-38s tese=%.3f  csv=%.3f" % (rot, tese, calc))

    # a tabela
    for rotulo, algo in (("GNN \\(Evolutivo\\)", "GNN"), ("PPO", "PPO"),
                         ("SAC", "SAC")):
        m = re.search(rotulo + r" & \$([\d{},]+) \\pm ([\d{},]+)\$ & \$([\d{},]+)"
                      r"\\?%?\$ & \$(\d+)/(\d+)\$", tex)
        g = por_algo.get(algo)
        if g is None:
            problemas.append("tab:res_sandbox (%s): sem dados no CSV" % algo)
            continue
        vals = [numero(x) for x in m.groups()] if m else [None] * 5
        confere("tab %s: média" % algo, vals[0], float(g["food"].mean()))
        confere("tab %s: desvio" % algo, vals[1], float(g["food"].std()))
        # P_task da tabela é a taxa de sucesso média entre execuções, em %
        confere("tab %s: P_task" % algo, vals[2],
                100.0 * float(g["suc"].mean()), tol=0.05)
        confere("tab %s: runs funcionais" % algo, vals[3],
                int((g["suc"] >= 1.0).sum()), exato=True)
        confere("tab %s: n" % algo, vals[4], len(g), exato=True)
        print("  %-4s n=%d  %6.2f ± %5.2f   P_task %5.1f%%   funcionais %d/%d"
              % (algo, len(g), g["food"].mean(), g["food"].std(),
                 100 * g["suc"].mean(), int((g["suc"] >= 1.0).sum()), len(g)))

    # a prosa: as duas médias dos gradientes e a do evolutivo
    m = re.search(r"\(PPO \$([\d{},]+) \\pm ([\d{},]+)\$ recolhas/ep; SAC "
                  r"\$([\d{},]+) \\pm ([\d{},]+)\$\)", tex)
    if m and "PPO" in por_algo and "SAC" in por_algo:
        for i, (rot, algo, campo) in enumerate((
                ("prosa PPO: média", "PPO", "mean"),
                ("prosa PPO: desvio", "PPO", "std"),
                ("prosa SAC: média", "SAC", "mean"),
                ("prosa SAC: desvio", "SAC", "std"))):
            serie = por_algo[algo]["food"]
            confere(rot, numero(m.group(i + 1)),
                    float(getattr(serie, campo)()), tol=max(0.05, tolerancia))
    else:
        problemas.append("prosa do Sandbox: não encontrei as médias do PPO/SAC")

    # A FORMA: quatro competitivas, duas degeneradas, uma intermédia. É a frase
    # que sustenta o argumento do capítulo e a que sobrevive a uma mudança de
    # dados sem que nenhuma média mude o suficiente para dar sinal. Verifica-se
    # por construção: contam-se as execuções em cada regime e exige-se que os
    # limites citados sejam o mínimo e o máximo do grupo competitivo.
    m = re.search(r"quatro d[oa]s sete (?:\\textit\{runs?\}|execuç(?:ão|ões)) "
                  r"convergem para políticas "
                  # o padrão aceita «dois … um» e «duas … uma» (o género mudou
                  # com «execuções»); o que se confere são os números
                  r"competitivas \(([\d,]+) a ([\d,]+) recolhas/ep\), (?:dois|duas) "
                  r"degeneram por completo \(\$<(\d+)\$ recolha/ep\) e (?:um|uma) fica "
                  r"num regime intermédio \(([\d,]+) recolhas/ep, com sucesso "
                  r"em todos os episódios", tex)
    g = por_algo.get("GNN")
    if m is None:
        problemas.append("forma da distribuição do GNN: não encontrei a frase")
    elif g is not None:
        lo, hi = numero(m.group(1)), numero(m.group(2))
        limiar_zero, intermedio = numero(m.group(3)), numero(m.group(4))
        food = g["food"].sort_values()
        # a folga é a do arredondamento a uma casa (0,05), com um epsilon por
        # cima: 61,55 escreve-se 61,6, e sem o epsilon o próprio valor citado
        # caía fora do grupo por erro de vírgula flutuante
        folga = 0.05 + 1e-9
        competitivas = food[food >= lo - folga]
        degeneradas = food[food < limiar_zero]
        meio = food[(food >= limiar_zero) & (food < lo - folga)]
        conferidos += 5
        if len(competitivas) != 4:
            problemas.append("a tese diz quatro execuções competitivas; são %d"
                             % len(competitivas))
        if len(degeneradas) != 2:
            problemas.append("a tese diz duas execuções degeneradas (<%g); são "
                             "%d" % (limiar_zero, len(degeneradas)))
        if len(meio) != 1:
            problemas.append("a tese diz uma execução intermédia; são %d"
                             % len(meio))
        if len(competitivas):
            confere("limite inferior das competitivas", lo,
                    float(competitivas.min()), tol=folga)
            confere("limite superior das competitivas", hi,
                    float(competitivas.max()), tol=folga)
        if len(meio) == 1:
            confere("execução intermédia", intermedio, float(meio.iloc[0]),
                    tol=folga)
            # «com sucesso em todos os episódios» — a metade da frase que não
            # é um número, e que distingue esta execução das degeneradas.
            conferidos += 1
            run_meio = g[g["food"] == meio.iloc[0]]
            if float(run_meio["suc"].iloc[0]) < 1.0:
                problemas.append("a execução intermédia não tem sucesso em "
                                 "todos os episódios (%.2f)"
                                 % run_meio["suc"].iloc[0])
            else:
                print("  [4] a forma: %d competitivas (%.1f a %.1f), %d a zero "
                      "(<%g) e 1 intermédia (%.1f, sucesso pleno)"
                      % (len(competitivas), competitivas.min(),
                         competitivas.max(), len(degeneradas), limiar_zero,
                         meio.iloc[0]))

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do Sandbox batem com o CSV." % conferidos)
    return problemas


def verificar_ptask_prosa(tolerancia):
    """§P_task — as afirmações do parágrafo que lê a `tab:res_eval`.

    A tabela tem verificador; o parágrafo que a lê, não — e é ele que o leitor
    retém: «o PPO é o mais consistente», «o GNN iguala o PPO no Gargalo», «cerca
    de 1,8x o melhor método de gradiente». São afirmações derivadas: sobrevivem
    a uma mudança de dados que mexa nas células sem mexer na conclusão.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §P_task (o parágrafo que LÊ a tabela)  vs  eval_by_run_7d")
    print("=" * 72)

    fp = os.path.join(PROJECT_ROOT, "results", "graficos_tese", "final_7d",
                      "eval_by_run_7d.csv")
    if not os.path.exists(fp):
        print("[!] falta o eval_by_run_7d.csv — a saltar.")
        return []
    # os SETE, da fonte única — nunca uma lista escrita aqui
    sys.path.insert(0, PROJECT_ROOT)
    from src.scenarios import THESIS_SCENARIOS
    d = pd.read_csv(fp)
    d["Algorithm"] = d["Algorithm"].astype(str).str.upper()
    por = {}
    for (cen, algo), g in d.groupby(["Scenario", "Algorithm"]):
        r = g.groupby("Run").agg(food=("food_collected", "mean"),
                                 suc=("success", "mean"))
        por[(cen, algo)] = r

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas, conferidos = [], 0

    def confere(rot, tese, calc, tol=None, exato=False):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler no main.tex (mudou a "
                             "redação?)" % rot)
        elif exato and int(tese) != int(calc):
            problemas.append("%-42s tese=%d  csv=%d" % (rot, tese, calc))
        elif not exato and abs(tese - calc) > (tol or tolerancia):
            problemas.append("%-42s tese=%.4g  csv=%.4g" % (rot, tese, calc))
        else:
            print("   [v] %-44s %8.4g" % (rot, calc))

    def media(cen, algo):
        r = por.get((cen, algo))
        return None if r is None else float(r["food"].mean())

    # o PPO é o mais consistente
    m = re.search(r"100\\% de sucesso em (\w+) dos sete cenários, com a menor "
                  r"variância entre (?:\\\\textit\\{runs?\\}|execuç(?:ão|ões)) \(desvios padrão de "
                  r"([\d,]+) a ([\d,]+) recolhas/ep fora do Muro (?:em )?U\)", tex)
    if m is None:
        problemas.append("PPO consistente: não encontrei a frase")
    else:
        POR_EXTENSO = {"um": 1, "dois": 2, "três": 3, "quatro": 4, "cinco": 5,
                       "seis": 6, "sete": 7}
        cheios = sum(1 for (cen, algo), r in por.items()
                     if algo == "PPO" and cen in THESIS_SCENARIOS
                     and float(r["suc"].mean()) >= 1.0)
        confere("PPO: cenários a 100% de sucesso",
                POR_EXTENSO.get(m.group(1).lower()), cheios, exato=True)
        dps = [float(r["food"].std()) for (cen, algo), r in por.items()
               if algo == "PPO" and cen in THESIS_SCENARIOS and cen != "u_wall"]
        confere("PPO: menor desvio fora do Muro em U",
                numero(m.group(2).replace(",", ".")), min(dps), tol=0.05)
        confere("PPO: maior desvio fora do Muro em U",
                numero(m.group(3).replace(",", ".")), max(dps), tol=0.05)

    # as três médias do GNN citadas em prosa, e o rácio do Quatro Salas
    m = re.search(r"igualando o PPO no Gargalo \(([\d,]+) recolhas/ep em média.{0,60}?"
                  r"destacando-se no Quatro Salas \(([\d,]+), cerca de "
                  r"\$([\d{},]+)\\times\$ o melhor método de gradiente\).{0,80}?"
                  r"com Alternativa \(([\d,]+)\)", tex, re.DOTALL)
    if m is None:
        problemas.append("médias do GNN em prosa: não encontrei a frase")
    else:
        confere("GNN no Gargalo (prosa)", numero(m.group(1).replace(",", ".")),
                media("bottleneck", "GNN"), tol=0.05)
        confere("GNN no Quatro Salas (prosa)",
                numero(m.group(2).replace(",", ".")),
                media("four_rooms", "GNN"), tol=0.05)
        melhor_grad = max(media("four_rooms", "PPO"), media("four_rooms", "SAC"))
        confere("Quatro Salas: rácio face ao melhor gradiente",
                numero(m.group(3)), media("four_rooms", "GNN") / melhor_grad,
                tol=0.05)
        confere("GNN na Porta c/ Alternativa (prosa)",
                numero(m.group(4).replace(",", ".")),
                media("cooperative_door_bypass", "GNN"), tol=0.05)

    # o SAC: onde mantém 100% e onde é frágil
    m = re.search(r"O \\textbf\{SAC\} mantém 100\\% nos cenários cooperativos e "
                  r"no Quatro Salas", tex)
    if m is None:
        problemas.append("SAC a 100%: não encontrei a frase")
    else:
        conferidos += 1
        falham = [cen for cen in ("cooperative_door", "cooperative_perception",
                                  "cooperative_door_bypass", "four_rooms")
                  if por.get((cen, "SAC")) is not None
                  and float(por[(cen, "SAC")]["suc"].mean()) < 1.0]
        if falham:
            problemas.append("a tese diz SAC a 100%% nos cooperativos e no "
                             "Quatro Salas, e falha em: %s" % ", ".join(falham))
        else:
            print("   [4] SAC a 100% nos três cooperativos e no Quatro Salas")

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do parágrafo do P_task batem com o CSV."
              % conferidos)
    return problemas


def verificar_computacional():
    """§Desempenho Computacional — a aritmética que liga os seis números.

    É a única secção de resultados cujos valores não saem de um CSV: são
    medições de máquina (`scripts/benchmark_sim.py`), e re-medi-las noutro
    computador daria outro número sem que nada estivesse errado. O que tem de
    bater é a aritmética que as liga entre si:

        agente-passos/s = passos/s x N          (N = 20, dito na mesma frase)
        segundos/episódio = passos do episódio / passos/s
        ganho = passos/s (depois) / passos/s (antes)

    E a tabela repete os mesmos valores da prosa.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Desempenho Computacional (a aritmética entre os valores)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas, conferidos = [], 0

    def confere(rot, tese, calc, tol):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não consegui ler no main.tex (mudou a "
                             "redação?)" % rot)
        elif abs(tese - calc) > tol:
            problemas.append("%-40s tese=%.4g  aritmética=%.4g" % (rot, tese, calc))
        else:
            print("   [v] %-44s %8.4g  (tese %.4g)" % (rot, calc, tese))

    m = re.search(
        r"\$N=(?P<n>\d+)\$ agentes, (?P<bench>[\d\\,]+) passos com ações "
        r"aleatórias.{0,200}?\\textbf\{(?P<antes>[\d\\,]+) passos de simulação "
        r"por segundo\} \(\$\\approx\$(?P<ag_antes>[\d\\,]+) atualizações de "
        r"agente por segundo; \$\\approx\$(?P<s_antes>[\d,]+)\\,s por episódio "
        r"de (?P<passos_ep>\d+) passos\).{0,120}?\\textbf\{(?P<depois>[\d\\,]+) "
        r"passos/s\} \(\$\\approx\$(?P<ag_depois>[\d\\,]+) agente-passos/s; "
        r"\$\\approx\$(?P<s_depois>[\d,]+)\\,s por episódio\) --- um ganho de "
        r"\$\\approx (?P<ganho>[\d{},]+)\\times\$", tex, re.DOTALL)

    def n_(s):
        """'2\\,770' e '3,6' -> float (o `\\,` é o separador de milhares)."""
        return numero(str(s).replace("\\,", "").replace(",", ".")) if s else None

    if m is None:
        problemas.append("não encontrei a frase do throughput (mudou a redação?)")
    else:
        g = m.groupdict()
        n_ag = n_(g["n"])
        antes, depois = n_(g["antes"]), n_(g["depois"])
        passos_ep = n_(g["passos_ep"])
        # o separador decimal PT-PT: «3,6\,s» é 3,6 segundos, não 36.
        s_antes = numero(g["s_antes"].replace(",", "."))
        s_depois = numero(g["s_depois"].replace(",", "."))
        confere("agente-passos/s antes da vetorização", n_(g["ag_antes"]),
                antes * n_ag, tol=15)
        confere("agente-passos/s depois", n_(g["ag_depois"]),
                depois * n_ag, tol=15)
        confere("segundos por episódio antes", s_antes, passos_ep / antes,
                tol=0.05)
        confere("segundos por episódio depois", s_depois, passos_ep / depois,
                tol=0.05)
        confere("ganho da vetorização (×)", n_(g["ganho"]), depois / antes,
                tol=0.05)

        # A tabela diz os mesmos números — e é aqui que um deles fica para trás.
        t = re.search(
            r"pré-vetorização \(1 arena\) & \$\\approx (?P<a>\d+)\$ passos/s "
            r"\(\$\\approx (?P<aa>[\d\\,]+)\$ ag\.-passo/s\).{0,220}?"
            r"pós-vetorização\}? \(1 arena\) & \$\\approx (?P<d>\d+)\$ passos/s "
            r"\(\$\\approx (?P<dd>[\d\\,]+)\$ ag\.-passo/s\).{0,200}?"
            r"\((?P<pe>\d+) passos\), pós-vetorização & \$\\approx "
            r"(?P<sd>[\d{},]+)\$", tex, re.DOTALL)
        if t is None:
            problemas.append("tab:res_computacional: não encontrei as células")
        else:
            for rot, na_tabela, na_prosa in (
                    ("tabela: passos/s antes", n_(t.group("a")), antes),
                    ("tabela: ag.-passos/s antes", n_(t.group("aa")), n_(g["ag_antes"])),
                    ("tabela: passos/s depois", n_(t.group("d")), depois),
                    ("tabela: ag.-passos/s depois", n_(t.group("dd")), n_(g["ag_depois"])),
                    ("tabela: passos do episódio", n_(t.group("pe")), passos_ep),
                    ("tabela: segundos por episódio", n_(t.group("sd")), s_depois)):
                confere(rot, na_tabela, na_prosa, tol=0.05)

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do desempenho computacional são coerentes entre si."
              % conferidos)
    print("NOTA: não se re-mede o hardware — mede-se a ARITMÉTICA que liga os")
    print("      números, e a igualdade entre a prosa e a tabela.")
    return problemas


def verificar_questoes_investigacao():
    """As QI são sete, aparecem por ordem, e cada pergunta tem resposta.

    A QI7 esteve impressa antes da QI6 na lista do Capítulo 1: o bloco dela viveu
    meses em comentário à espera do resultado do mapa composto e, ao ser
    descomentado, ficou onde estava. Nenhum verificador de números veria isto —
    todos os números estavam certos.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: as questões de investigação (ordem e correspondência)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas = []
    # As perguntas (Cap. 1) e as respostas (Cap. 7) usam formas de rótulo
    # diferentes de propósito — «\textbf{QI1.}» e «QI1 --- …» —, e é por isso
    # que se distinguem sem depender da posição no ficheiro.
    listas = (("perguntas (Secção das Questões de Investigação)",
               r"\\item\[\\textbf\{QI(\d)\.\}\]"),
              ("respostas (Secção da Resposta às Questões)",
               r"\\item\[QI(\d) ---"))
    conjuntos = {}
    for rot, padrao in listas:
        nums = [int(m.group(1)) for m in re.finditer(padrao, tex)]
        conjuntos[rot] = nums
        if not nums:
            problemas.append("%s: não encontrei a lista (mudou a forma dos "
                             "\\item?)" % rot)
            continue
        if nums != sorted(nums):
            problemas.append("%s: estão fora de ordem — %s"
                             % (rot, ", ".join("QI%d" % n for n in nums)))
        if len(set(nums)) != len(nums):
            problemas.append("%s: há uma QI repetida — %s" % (rot, nums))
        print("   [%d] %-46s %s" % (len(nums), rot[:46],
                                    ", ".join("QI%d" % n for n in nums)))

    vals = list(conjuntos.values())
    if len(vals) == 2 and all(vals):
        if set(vals[0]) != set(vals[1]):
            so_pergunta = sorted(set(vals[0]) - set(vals[1]))
            so_resposta = sorted(set(vals[1]) - set(vals[0]))
            problemas.append(
                "perguntadas sem resposta: %s | respondidas sem pergunta: %s"
                % (so_pergunta or "nenhuma", so_resposta or "nenhuma"))
        else:
            print("   [%d] cada questão perguntada tem resposta, e vice-versa"
                  % len(vals[0]))

    if problemas:
        print("\nDIVERGÊNCIAS:")
        for p in problemas:
            print("   " + p)
    else:
        print("\nAs questões de investigação estão em ordem e emparelhadas.")
    return problemas


def verificar_coerencia_interna():
    """O mesmo facto, dito em sítios diferentes, diz o mesmo número?"""
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: coerência interna (o mesmo facto em capítulos diferentes)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    # A secção do mapa composto entra na tese por `\input` e o seu texto não está
    # dentro do `main.tex`, mas os seus factos são recontados na Discussão Global
    # e nas Conclusões. Sem esta junção, os sítios que vivem lá dentro apareciam
    # como «não encontrei a frase». As linhas do ficheiro incluído contam-se a
    # partir do fim do `main.tex`, e é por isso que aparecem com números altos.
    incluido = os.path.join(os.path.dirname(MAIN_TEX), "seccao_mapa_grande.tex")
    if re.search(r"^\s*\\input\{seccao_mapa_grande\}", tex, re.M) and \
            os.path.exists(incluido):
        with open(incluido, encoding="utf-8") as f:
            tex += "\n" + re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas, conferidos, repetidos = [], 0, 0
    for facto in FACTOS_REPETIDOS:
        achados = []
        for sitio in facto["sitios"]:
            m = re.search(sitio["re"], tex, re.DOTALL)
            if m is None:
                problemas.append("%s: não encontrei um dos sítios onde é dito "
                                 "(o texto mudou de forma?)" % facto["rot"])
                continue
            vals = [numero(v) for v in m.groups() if v is not None]
            ordem = sitio.get("ordem")
            if ordem:
                vals = [vals[i] for i in ordem]
            # Dois padrões a caírem no MESMO sítio não são uma verificação
            # cruzada — são a mesma frase lida duas vezes, e passariam sempre.
            if any(p == m.start() for _, _, p in achados):
                problemas.append("%s: dois sítios apanham a mesma ocorrência "
                                 "(linha %d) — a verificação não é cruzada"
                                 % (facto["rot"], tex.count("\n", 0, m.start()) + 1))
                continue
            achados.append((tuple(vals), tex.count("\n", 0, m.start()) + 1,
                            m.start()))
        if len(achados) < 2:
            if achados:
                print("   [1] %-52s só um sítio encontrado (linha %d)"
                      % (facto["rot"][:52], achados[0][1]))
            continue
        conferidos += sum(len(v) for v, _, _ in achados)
        repetidos += 1
        base, linha0, _ = achados[0]
        divergiu = False
        for vals, linha, _ in achados[1:]:
            if vals != base:
                divergiu = True
                problemas.append(
                    "%s: linha %d diz %s, linha %d diz %s — a tese contradiz-se"
                    % (facto["rot"], linha0, base, linha, vals))
        if not divergiu:
            print("   [%d] %-52s coerente (linhas %s)"
                  % (len(achados), facto["rot"][:52],
                     ", ".join(str(l) for _, l, _ in achados)))

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores repetidos concordam entre si (%d factos ditos "
              "mais do que uma vez)." % (conferidos, repetidos))
    print("NOTA: isto não compara com dados — compara a tese consigo própria.")
    print("      Um facto corrigido no Cap. 5 e esquecido no Cap. 6 aparece aqui")
    print("      e em mais lado nenhum.")
    return problemas


def verificar_fiabilidade_prosa(tolerancia):
    """§Fiabilidade e Variância entre Execuções — a prosa que LÊ os dotplots.

    A secção não tem tabela: descreve, cenário a cenário, a FORMA de sete pontos
    («as sete execuções ficam agrupadas e afastadas do zero», «o SAC espalha-se
    de 0 a 88 recolhas/ep»). Uma média pode manter-se enquanto a forma que estas
    frases descrevem muda por completo.

    A régua é a média por execução do `eval_by_run_7d.csv`, a mesma da tabela
    principal. «Degenerada» é o que a própria frase diz — abaixo de uma recolha
    por episódio; «funcional» é a execução com sucesso em todos os episódios,
    que é como o resto do capítulo conta convergência.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: §Fiabilidade entre Execuções (a forma dos sete pontos)")
    print("=" * 72)

    if not os.path.exists(CSV_7D):
        print("[!] sem eval_by_run_7d.csv — a saltar.")
        return []

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    d = pd.read_csv(CSV_7D)
    por_run = (d.groupby(["Scenario", "Algorithm", "Run"])
                .agg(food=("food_collected", "mean"), suc=("success", "mean"))
                .reset_index())

    def celula(cen, algo):
        return por_run[(por_run["Scenario"] == cen) &
                       (por_run["Algorithm"] == algo)]

    problemas, conferidos = [], 0

    def confere(rot, tese, calc, exato=True):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não encontrei a frase (mudou a redação?)" % rot)
        elif exato and int(tese) != int(calc):
            problemas.append("%-46s tese=%d  dados=%d" % (rot, tese, calc))
        elif not exato and abs(tese - calc) > tolerancia:
            problemas.append("%-46s tese=%.1f  dados=%.1f" % (rot, tese, calc))
        else:
            print("   [v] %-46s %s" % (rot, ("%d" % calc) if exato
                                       else ("%.1f" % calc)))

    def procura(padrao):
        m = re.search(padrao, tex, re.DOTALL)
        return [numero(g) for g in m.groups()] if m else None

    # o protocolo que a secção enuncia
    v = procura(r"média dos (\d+) episódios de avaliação; (\d+) pontos por "
                r"algoritmo")
    if v:
        n_ep = int(d.groupby(["Scenario", "Algorithm", "Run"]).size().min())
        confere("episódios por ponto", v[0], n_ep)
        confere("pontos por algoritmo", v[1],
                int(celula("none", "GNN")["Run"].nunique()))
    else:
        problemas.append("protocolo dos dotplots: não encontrei a frase")

    # Gargalo: PPO e GNN fiáveis, SAC de 0 a 88
    v = procura(r"No \\textbf\{Gargalo\}, PPO e GNN são fiáveis \((\d+)/(\d+) "
                r"execuções\), mas as execuções do SAC espalham-se de (\d+) a "
                r"(\d+) recolhas/ep")
    if v:
        for algo in ("PPO", "GNN"):
            g = celula("bottleneck", algo)
            confere("Gargalo/%s: execuções a 100%%" % algo, v[0],
                    int((g["suc"] >= 1.0).sum()))
        confere("Gargalo: execuções por célula", v[1],
                len(celula("bottleneck", "SAC")))
        sac = celula("bottleneck", "SAC")["food"]
        confere("Gargalo/SAC: mínimo (recolhas/ep)", v[2], float(sac.min()),
                exato=False)
        # A tese escreve «de 0 a 88», um arredondamento à unidade: comparar
        # com a tolerância de uma casa decimal acusaria os 88,2 medidos.
        conferidos += 1
        if abs(v[3] - float(sac.max())) > 0.5:
            problemas.append("Gargalo/SAC: máximo   tese=%.0f  dados=%.1f"
                             % (v[3], sac.max()))
        else:
            print("   [v] %-46s %.1f" % ("Gargalo/SAC: máximo (recolhas/ep)",
                                         sac.max()))
    else:
        problemas.append("Gargalo: não encontrei a frase do SAC «de 0 a 88»")

    # Sandbox: o GNN com execuções degeneradas. «Degeneradas» é um critério e não
    # um adjetivo — a secção chama-lhes as que ficam abaixo de UMA recolha por
    # episódio. O numeral vem por extenso, e o que se confere é o número: trocar
    # «duas» por «três» tem de acusar o valor errado, não um «não encontrei a
    # frase» que se leria como problema do verificador.
    EXTENSO = {"uma": 1, "um": 1, "duas": 2, "dois": 2, "três": 3, "tres": 3,
               "quatro": 4, "cinco": 5, "seis": 6, "sete": 7}
    m = re.search(r"GNN com (\w+) execuç(?:ão|ões) degenerada?s?", tex)
    g = celula("none", "GNN")["food"]
    if m and m.group(1).lower() in EXTENSO:
        confere("Sandbox/GNN: execuções abaixo de 1 recolha/ep",
                EXTENSO[m.group(1).lower()], int((g < 1.0).sum()))
    else:
        problemas.append("Sandbox: não encontrei a frase das execuções "
                         "degeneradas (ou o numeral não é um que eu saiba ler)")

    # Muro em U: os três têm execuções a zero, o PPO tem a maioria
    v = procura(r"só o PPO tem a maioria das execuções funcionais \((\d+)/(\d+)\)")
    if v:
        ppo = celula("u_wall", "PPO")
        confere("Muro em U/PPO: execuções a 100%", v[0],
                int((ppo["suc"] >= 1.0).sum()))
        confere("Muro em U: execuções por célula", v[1], len(ppo))
        conferidos += 1
        # «a zero» é o mesmo critério que a secção do Sandbox usa para
        # «degenerada»: abaixo de UMA recolha por episódio. Exigir zero exato era
        # mais estrito do que a tese — no Muro em U as execuções falhadas do PPO
        # medem 0,10, 0,45 e 0,85 recolhas/ep contra 67 a 72 das que resolvem.
        sem_zero = [a for a in ALGOS
                    if int((celula("u_wall", a)["food"] < 1.0).sum()) == 0]
        if sem_zero:
            problemas.append("Muro em U: a tese diz que os três algoritmos têm "
                             "execuções a zero, mas %s não tem nenhuma"
                             % ", ".join(sem_zero))
        else:
            print("   [3] %-46s os três têm execuções a zero"
                  % "Muro em U: bimodalidade")
    else:
        problemas.append("Muro em U: não encontrei a frase do «4/7» do PPO")

    # Os cenários onde treinar é fiável. «Agrupadas e afastadas do zero» é uma
    # afirmação sobre TODAS as sete execuções dos três algoritmos: basta uma a
    # zero para deixar de ser verdade, e é isso que se testa — não a média, que
    # sobreviveria a ela.
    if re.search(r"as sete execuções dos três algoritmos ficam agrupadas e "
                 r"afastadas do zero", tex):
        for cen, rot in (("cooperative_door", "Porta Cooperativa"),
                         ("cooperative_door_bypass", "Porta c/ Alternativa"),
                         ("four_rooms", "Quatro Salas")):
            conferidos += 1
            minimos = {a: float(celula(cen, a)["food"].min()) for a in ALGOS}
            if min(minimos.values()) < 1.0:
                problemas.append("%s: a tese diz «afastadas do zero», mas há "
                                 "execuções abaixo de 1 recolha/ep (%s)"
                                 % (rot, minimos))
            else:
                print("   [v] %-46s mínimo %.1f recolhas/ep"
                      % ("%s: nenhuma execução perto do zero" % rot,
                         min(minimos.values())))
    else:
        problemas.append("cenários fiáveis: não encontrei a frase «agrupadas e "
                         "afastadas do zero»")

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores da secção da fiabilidade batem com o CSV."
              % conferidos)
    print("NOTA: o que aqui se confere é a FORMA da distribuição — quantas")
    print("      execuções ficam a zero, onde estão os extremos —, e não as")
    print("      médias, que a tabela principal já verifica.")
    return problemas


def _numeros_do_bloco(texto):
    """Os valores numéricos de um bloco de prosa, pela ordem em que aparecem.

    Normaliza as duas escritas do mesmo número — o `88{,}7` do Resumo e o `88.7`
    do Abstract são o mesmo valor — e deixa cair o que não é grandeza:
    argumentos de comandos LaTeX (`\\vspace{3ex}`, `\\times`) e índices de
    referências.

    A procura corre sobre o texto ORIGINAL e não sobre uma cópia limpa: o
    `cobertura_verificador.py` mede o que os verificadores leem instrumentando o
    módulo `re`, e só reconhece o que é procurado no `.tex` tal como ele está.
    """
    vals = []
    for m in re.finditer(r"(?<![\w.,])(\d+(?:(?:\{,\}|[.,])\d+)?)(?![\w])",
                         texto):
        bruto = m.group(1)
        antes = texto[max(0, m.start() - 14):m.start()]
        # O `3ex` de um `\vspace`, o ano de um `\cite` ou o número de um DOI
        # não são grandezas que alguém leia em voz alta.
        if re.search(r"\\(?:vspace|hspace|label|ref|cite|url|doi)\{[^}]*$",
                     antes):
            continue
        if re.fullmatch(r"(19|20)\d{2}", bruto):
            continue
        vals.append(float(bruto.replace("{,}", ".").replace(",", ".")))
    return vals


def verificar_resumo_abstract():
    """O Resumo e o Abstract dizem o mesmo, e o que dizem bate com os dados.

    Duas perguntas:

    1. O Abstract é a tradução do Resumo? Não em prosa — em números: os dois
       blocos têm de trazer a MESMA sequência de valores. Uma correção feita num
       deles e esquecida no outro passa despercebida às restantes réguas, porque
       cada valor, isoladamente, continua a bater com o seu CSV.
    2. Os números do Resumo são os medidos? As afirmações que ele arrisca são
       reconferidas contra as mesmas fontes que sustentam o corpo.
    """
    print()
    print("=" * 72)
    print("VERIFICAÇÃO: Resumo e Abstract (paridade PT↔EN + valores)")
    print("=" * 72)

    with open(MAIN_TEX, encoding="utf-8") as f:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", f.read())

    problemas, conferidos = [], 0

    def bloco(inicio, fim):
        i = tex.find(inicio)
        if i < 0:
            return None
        j = tex.find(fim, i)
        return tex[i + len(inicio):j if j > 0 else len(tex)]

    pt = bloco(r"\chapter*{Resumo}", r"\textsc{Palavras Chave:}")
    en = bloco(r"\chapter*{Abstract}", r"\textsc{Keywords:}")
    if pt is None or en is None:
        problemas.append("não encontrei o Resumo ou o Abstract (mudaram de "
                         "forma? este verificador procura os \\chapter*)")
        print("   [X] blocos não encontrados")
        return problemas

    v_pt, v_en = _numeros_do_bloco(pt), _numeros_do_bloco(en)
    conferidos += len(v_pt)
    if v_pt == v_en:
        print("   [%d] Resumo e Abstract trazem a mesma sequência de valores"
              % len(v_pt))
    else:
        # Mostrar ONDE divergem, não só que divergem: com quinze números, «são
        # diferentes» manda procurar à mão.
        for k, (a, b) in enumerate(zip(v_pt, v_en), 1):
            if a != b:
                problemas.append("Resumo vs Abstract, valor #%d: %s vs %s"
                                 % (k, a, b))
        if len(v_pt) != len(v_en):
            problemas.append("Resumo tem %d valores e o Abstract %d — um deles "
                             "ganhou ou perdeu uma afirmação" % (len(v_pt), len(v_en)))

    def confere(rot, tese, calc, exato=True, tol=0.05):
        nonlocal conferidos
        conferidos += 1
        if tese is None:
            problemas.append("%s: não encontrei a frase no Resumo "
                             "(mudou a redação?)" % rot)
        elif exato and int(tese) != int(calc):
            problemas.append("%-42s resumo=%d  dados=%d" % (rot, tese, calc))
        elif not exato and abs(tese - calc) > tol:
            problemas.append("%-42s resumo=%.2f  dados=%.2f" % (rot, tese, calc))
        else:
            print("   [v] %-42s %s" % (rot, ("%d" % calc) if exato
                                       else ("%.1f" % calc)))

    def le(padrao, texto=pt):
        m = re.search(padrao, texto, re.DOTALL)
        return [numero(g) for g in m.groups()] if m else None

    # 1. sete execuções independentes por combinação
    v = le(r"\((\d+) execuções independentes por combinação\)")
    if os.path.exists(CSV_7D):
        d = pd.read_csv(CSV_7D)
        por_celula = d.groupby(["Scenario", "Algorithm"])["Run"].nunique()
        confere("execuções por combinação", v[0] if v else None,
                int(por_celula.min()))
        if v and int(por_celula.min()) != int(por_celula.max()):
            problemas.append("as células não têm todas o mesmo n (%d a %d) — o "
                             "Resumo afirma um número só"
                             % (por_celula.min(), por_celula.max()))

    # 2. Zero-Shot: de N=10 a N=100, a 100% de sucesso
    v = le(r"\$N\$ de \$(\d+)\$ a \$(\d+)\$, com (\d+)\\% de sucesso")
    csv_esc = os.path.join(PROJECT_ROOT, "results", "estatisticas",
                           "escalabilidade_none.csv")
    if os.path.exists(csv_esc):
        e = pd.read_csv(csv_esc)
        g = e[(e["Algorithm"] == "GNN") & (e["compatible"])]
        confere("Zero-Shot: N mínimo", v[0] if v else None, int(g["N"].min()))
        confere("Zero-Shot: N máximo", v[1] if v else None, int(g["N"].max()))
        confere("Zero-Shot: sucesso (%)", v[2] if v else None,
                int(round(100 * g["success_rate"].min())))

    # 3. os 7/7 do Muro em U com dosagem adaptativa
    v = le(r"preserva os \$(\d+)/(\d+)\$ execuções no Muro em U")
    r = _runs_a_100("adapt_B2", "u_wall")
    n = _por_run("adapt_B2", "u_wall")
    if r is not None and n is not None:
        confere("Muro em U: execuções a 100%", v[0] if v else None, int(r))
        confere("Muro em U: execuções na campanha", v[1] if v else None, len(n))

    # 4. o melhor resultado da dissertação
    v = le(r"melhor resultado de toda a dissertação \(\$([\d.,{}\\]+)\$ "
           r"recolhas/ep\)")
    b3 = _por_run("adapt_B3", "cooperative_door_bypass")
    if b3 is not None:
        confere("Porta c/ Alternativa: recolhas/ep", v[0] if v else None,
                float(b3.mean()), exato=False)

    # 5. a replicação a n=28
    v = le(r"\$(\d+)/(\d+)\$, contra \$(\d+)/28\$ do objetivo puro, "
           r"\$(\d+)/28\$ do PPO e \$(\d+)/28\$ do SAC")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from analise_megatreino import carregar as _carregar_mega
    except Exception:                                        # pragma: no cover
        _carregar_mega = None
    if _carregar_mega is not None:
        for k, (fase, rot) in enumerate((("mega_A_fase1", "adaptativo"),
                                         ("mega_A_fase2", "objetivo puro"),
                                         ("mega_A_fase3", "PPO"),
                                         ("mega_A_fase4", "SAC"))):
            g = _carregar_mega(fase, "u_wall")
            if g is None:
                problemas.append("mega-treino %s: sem dados" % rot)
                continue
            idx = 0 if k == 0 else k + 1        # o segundo valor lido é o n=28
            confere("n=28, %s: execuções a 100%%" % rot,
                    v[idx] if v else None, int((g["suc"] >= 1.0).sum()))
            if k == 0:
                confere("n=28: execuções por braço", v[1] if v else None, len(g))

    # 6. o oitavo cenário
    v = le(r"resolvido em (\d+) das\s+\$(\d+)\$ execuções independentes")
    try:
        from analise_mapa_grande import medir_f2
        m = medir_f2()
    except Exception:                                        # pragma: no cover
        m = None
    if m:
        confere("mapa composto: execuções que resolvem", v[0] if v else None,
                int(m["max_convergentes"]))
        confere("mapa composto: execuções por braço", v[1] if v else None,
                int(m["n_runs"]))

    if problemas:
        print("\nDIVERGÊNCIAS (%d de %d valores):" % (len(problemas), conferidos))
        for p in problemas:
            print("   " + p)
    else:
        print("\nOs %d valores do Resumo batem com os dados, e o Abstract diz "
              "o mesmo." % conferidos)
    print("NOTA: a paridade PT↔EN é a única verificação deste ficheiro que não")
    print("      olha para dados nenhuns — compara as duas primeiras páginas")
    print("      uma com a outra, que é onde uma correção esquecida se instala.")
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
    problemas += verificar_escalabilidade_prosa(a.tolerancia)
    problemas += verificar_simulador()
    problemas += verificar_hiperparametros()
    problemas += verificar_discussao_global(a.tolerancia)
    problemas += verificar_sandbox(a.tolerancia)
    problemas += verificar_ptask_prosa(a.tolerancia)
    problemas += verificar_computacional()
    problemas += verificar_questoes_investigacao()
    problemas += verificar_resumo_abstract()
    problemas += verificar_fiabilidade_prosa(a.tolerancia)
    problemas += verificar_coerencia_interna()
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
