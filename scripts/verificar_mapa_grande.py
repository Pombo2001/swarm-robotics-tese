# -*- coding: utf-8 -*-
"""Verifica os números da secção do mapa grande (`Tese/seccao_mapa_grande.tex`).

Porque existe, e porque existe AGORA
A secção entra na dissertação a ~16 de agosto, com seis dias até ao limite de
integração. Nesse dia haverá cinco buracos para preencher, uma leitura para
escolher e um `\\input` para descomentar — e nenhuma vontade de escrever um
verificador. Escrito antes de existirem os números, este verificador faz duas
coisas: valida hoje tudo o que a secção já afirma (a geometria e o F1 inteiro), e
está pronto para validar o F2 no dia em que o `eval_by_run.csv` aparecer.

Os valores esperados são LIDOS DO `.tex`, nunca fixados aqui. Um verificador
com os números copiados para dentro de si concorda com a tese por construção e
deixa de ser verificação — passa a ser uma segunda cópia, que é o defeito que
este projeto já apanhou três vezes (a régua do percurso, as figuras do artigo, a
espessura das paredes).

Uso:
    .venv/Scripts/python.exe scripts/verificar_mapa_grande.py
"""
import glob
import math
import os
import re
import sys

import numpy as np
import pandas as pd
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

SECCAO = os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex")
F1_DIR = os.path.join(RAIZ, "results", "mapa_grande", "f1_zeroshot_v2")
F2_GLOB = os.path.join(RAIZ, "results", "mapa_grande", "f2*", "**",
                       "eval_by_run.csv")
CFG = os.path.join(RAIZ, "configs", "foraging.yaml")

falhas = []
conferidos = 0


def _tex():
    with open(SECCAO, encoding="utf-8") as fh:
        texto = fh.read()
    # Fora as linhas comentadas: as leituras alternativas da Discussão vivem em
    # comentário e os seus números são deliberadamente provisórios.
    return "\n".join(l for l in texto.splitlines()
                     if not l.lstrip().startswith("%"))


def le(padrao, texto, nome):
    """Um número que a secção afirma. Devolve None e regista falha se faltar."""
    m = re.search(padrao, texto)
    if not m:
        falhas.append("não encontrei na secção: %s (a redação mudou?)" % nome)
        return None
    return float(m.group(1).replace("{,}", ".").replace(",", "."))



def _n(s):
    r"""'1{,}7', '+0{,}19' ou '17\%' -> float. None se não for número.

    A ordem importa: o separador decimal PT-PT é `{,}` e tem de ser
    resolvido ANTES de se limparem as chavetas, senão `1{,}7` fica `1{,7` e não
    converte. É a mesma armadilha que o `numero()` do verificar_numeros_tese
    documenta — e que aqui se voltou a cair, por o helper ter sido escrito à
    pressa dentro de um heredoc que comeu as barras invertidas.
    """
    if s is None:
        return None
    s = str(s).replace("{,}", ".")
    s = re.sub(r"\\%|\\textbf|\\emph|[{}$%]", "", s)
    s = s.replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None

def compara(nome, medido, na_tese, tol=0.05):
    global conferidos
    if na_tese is None:
        return
    conferidos += 1
    ok = abs(medido - na_tese) <= tol
    print("  %s %-46s medido %9.2f   secção %9.2f"
          % ("[v]" if ok else "[X]", nome, medido, na_tese))
    if not ok:
        falhas.append("%s: medido %.2f, a secção diz %.2f" % (nome, medido, na_tese))


# 1. Geometria: a secção descreve o mapa, o simulador constrói-o
def geometria(texto):
    print()
    print("=" * 74)
    print("GEOMETRIA DO MAPA  vs  o que o simulador constrói")
    print("=" * 74)
    from src.environment.swarm_env_3d import SwarmForagingEnv3D

    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    cfg["environment"]["classic_scenario"] = "mapa_grande"
    env = SwarmForagingEnv3D(config=cfg)
    env.render_mode = None
    env.reset(seed=7)

    compara("raio da arena (m)", float(env.arena_radius),
            le(r"inscrito numa arena de raio \$(\d+)\$\\,m", texto, "raio"))
    compara("raio dos sete cenários (m)", 15.0,
            le(r"contra os \$(\d+)\$\\,m de\nraio dos sete", texto,
               "raio dos sete"))
    compara("nº de obstáculos", float(len(env.obstacles)),
            le(r"cinco zonas de oeste para este, \$(\d+)\$ obstáculos", texto,
               "obstáculos"))
    compara("nº de agentes", float(env.num_agents),
            le(r"\\textbf\{\$N = (\d+)\$ agentes\}", texto, "N"))
    compara("max_steps", float(env.max_steps),
            le(r"max\\_steps\} = (\d+)\$", texto, "max_steps"))
    compara("required_to_eat", float(env.required_to_eat),
            le(r"required\\_to\\_eat\} = (\d+)\$", texto, "required_to_eat"))

    # As distâncias: percurso geodésico do spawn ao ninho, na régua do ambiente.
    campo = env.geo_field
    def geo(p):
        i, j = env._to_cell(p)
        return float(campo[i, j])

    # Os extremos são propriedades da CAIXA de spawn, não de uma amostra de
    # 20 agentes (com a semente 7 o máximo amostrado é 137,2 m contra os 139 m
    # que a caixa permite). E também não se medem só nos cantos: o campo
    # geodésico não é monótono dentro da caixa — a saída da sala não está num
    # canto —, pelo que o mínimo cai no meio de um lado. Varre-se a caixa.
    c, hx, hy = env._mapa_grande_spawn_box()
    grelha = [np.array([x, y, 0.0])
              for x in np.linspace(c[0] - hx, c[0] + hx, 41)
              for y in np.linspace(c[1] - hy, c[1] + hy, 41)]
    dists = [geo(p) for p in grelha]
    compara("percurso do centro do spawn ao ninho (m)",
            geo(np.array([c[0], c[1], 0.0])),
            le(r"Do centro da zona de partida ao ninho vão \$(\d+\{,\}\d+)\$\\,m",
               texto, "percurso do centro"), tol=0.6)
    compara("percurso mais curto entre agentes (m)", min(dists),
            le(r"varia entre \$\\approx (\d+)\$\\,m", texto, "percurso mínimo"),
            tol=1.5)
    compara("percurso mais longo entre agentes (m)", max(dists),
            le(r"e \$\\approx (\d+)\$\\,m para o mais afastado", texto,
               "percurso máximo"), tol=1.5)
    finito = campo[np.isfinite(campo)]
    compara("ponto mais distante do ninho (m)", float(finito.max()),
            le(r"fica a \$(\d+\{,\}\d+)\$\\,m", texto, "ponto mais distante"),
            tol=0.6)

    # Folga do orçamento: quantas vezes o episódio dá para o percurso de ida.
    # O passo é 0,2 m POR EIXO (o texto di-lo), que é o que a secção usa.
    passo = 0.2
    compara("passos de ida do pior ponto do mapa",
            float(finito.max()) / passo,
            le(r"mapa fica a \$(\d+)\$ passos apenas de ida", texto,
               "passos de ida"), tol=2.0)
    compara("folga do orçamento sobre a ida (×)",
            env.max_steps / (float(finito.max()) / passo),
            le(r"deixam uma folga\s+de \$(\d+\{,\}\d+)\\times\$ sobre essa ida",
               texto, "folga sobre a ida"), tol=0.05)
    compara("folga a partir do pior spawn (×)",
            env.max_steps / (max(dists) / passo),
            le(r"\(\$(\d+\{,\}\d+)\\times\$ a partir do pior", texto,
               "folga do pior spawn"), tol=0.05)
    return env


# 2. F1: 84 células a zero, e as três causas excluídas
def f1(texto):
    print()
    print("=" * 74)
    print("F1 (zero-shot)  vs  results/mapa_grande/f1_zeroshot_v2/")
    print("=" * 74)
    csvs = sorted(glob.glob(os.path.join(F1_DIR, "zeroshot_*.csv")))
    if not csvs:
        print("  [!] sem CSV do F1 — a saltar.")
        return
    dfs = {os.path.basename(c): pd.read_csv(c) for c in csvs}
    natural = next((d for n, d in dfs.items() if "natural" in n), None)
    if natural is None:
        falhas.append("F1: falta o zeroshot_natural.csv")
        return

    # A célula do F1 é (cenário de ORIGEM do campeão) × algoritmo — o mapa é
    # sempre o mesmo, por isso a coluna que varia é `Origem`.
    col_cen = "Origem" if "Origem" in natural else "Scenario"
    col_alg = "Algorithm" if "Algorithm" in natural else "algorithm"
    celulas = natural.groupby([col_cen, col_alg]).ngroups
    compara("células da condição natural", float(celulas),
            le(r"das \$?(\d+)\$? células da condição natural", texto,
               "células naturais"), tol=0.01)
    compara("episódios da condição natural", float(len(natural)),
            le(r"\$(\d+)\$ episódios\n---", texto, "episódios naturais"),
            tol=0.01)

    total_cel = sum(d.groupby([col_cen, col_alg]).ngroups for d in dfs.values())
    total_ep = sum(len(d) for d in dfs.values())
    compara("células nas 4 condições", float(total_cel),
            le(r"que perfaz\n?\$?(\d+)\$? células a zero", texto,
               "células totais"), tol=0.01)
    compara("episódios nas 4 condições", float(total_ep),
            le(r"células a zero em \$?(\d+)\$? episódios", texto,
               "episódios totais"), tol=0.01)

    col_food = "food_collected" if "food_collected" in natural else "recolhas"
    piores = {n: float(d[col_food].max()) for n, d in dfs.items()}
    print("  recolha máxima por condição: %s"
          % ", ".join("%s=%.2f" % (n.replace("zeroshot_", "").replace(".csv", ""), v)
                      for n, v in piores.items()))
    if max(piores.values()) > 0:
        falhas.append("F1: a secção afirma 0,00 em todas as células, mas há "
                      "recolhas > 0 nos CSV (%s)"
                      % ", ".join("%s=%.2f" % kv for kv in piores.items()
                                  if kv[1] > 0))
    else:
        global conferidos
        conferidos += 1
        print("  [v] todas as condições a 0,00 recolhas, como a secção afirma")


# 3. Orçamento do F2
def orcamento(texto):
    print()
    print("=" * 74)
    print("ORÇAMENTO DO F2  vs  o que o servidor está a correr")
    print("=" * 74)
    estado = os.path.join(RAIZ, "results", "estado_f2.json")
    minutos_gnn = le(r"fixado em \$(\d+)\$ minutos por execução", texto,
                     "minutos do GNN")
    minutos_grad = le(r"e \$(\d+)\$ minutos por execução de\ncada método",
                      texto, "minutos dos gradientes")
    runs = le(r"\$(\d+)\$ execuções independentes com sementes", texto,
              "nº de execuções")
    print("  a secção afirma: %s min (GNN), %s min (gradientes), %s execuções"
          % (minutos_gnn, minutos_grad, runs))
    if os.path.exists(estado):
        import json
        with open(estado, encoding="utf-8") as fh:
            e = json.load(fh)
        for chave, nome in (("gnn", "GNN"), ("grad", "gradientes")):
            prev = e.get(chave, {}).get("runs_previstos")
            if prev is not None:
                compara("execuções previstas no servidor (%s)" % nome,
                        float(prev), runs, tol=0.01)
    else:
        print("  [!] sem results/estado_f2.json — correr scripts/estado_f2.sh "
              "para confrontar com o servidor")


# 4. F2: ativa-se sozinho quando os dados existirem
def f2(texto):
    print()
    print("=" * 74)
    print("F2 (treino nativo)  vs  eval_by_run.csv")
    print("=" * 74)
    csvs = glob.glob(F2_GLOB, recursive=True)
    if not csvs:
        print("  [i] ainda não há dados do F2 — nada a verificar aqui.")
        print("      Quando houver, esta função compara a tabela e M1-M3 com o")
        print("      CSV, do mesmo modo que o F1 acima.")
        return
    df = pd.concat([pd.read_csv(c) for c in csvs], ignore_index=True)
    col_alg = "Algorithm" if "Algorithm" in df else "algorithm"
    col_run = "Run" if "Run" in df else "run"
    col_food = "food_collected" if "food_collected" in df else "recolhas"
    print("  %d ficheiro(s), %d linhas" % (len(csvs), len(df)))
    for algo, g in df.groupby(col_alg):
        por_run = g.groupby(col_run)[col_food].mean()
        conv = int((por_run > 0).sum())
        print("    %-5s n=%2d runs | média %6.2f ± %5.2f | convergentes %d/%d"
              % (algo, len(por_run), por_run.mean(), por_run.std(ddof=1),
                 conv, len(por_run)))
    # Só compara com o texto se os buracos já tiverem sido preenchidos.
    #
    # Ignoram-se os comentários do `.tex`: depois de a secção ser preenchida, as
    # leituras alternativas que não foram escolhidas ficam comentadas, com os seus
    # `\PORPREENCHER` lá dentro, e o verificador dava por preencher uma secção
    # inteira. E procura-se a UTILIZAÇÃO (`\PORPREENCHER{...}`), não a palavra: a
    # secção define o próprio comando com `\providecommand`, e essa linha fica lá
    # para sempre.
    if re.search(r"\\PORPREENCHER\{", texto):
        print("  [!] a secção ainda tem \\PORPREENCHER — preencher antes de "
              "comparar.")
        return
    _f2_contra_texto(texto)


def medir_f2_seguro():
    """O `medir_f2()` do analise_mapa_grande, ou None se não houver dados."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from analise_mapa_grande import medir_f2
        return medir_f2()
    except Exception:                                        # noqa: BLE001
        return None


def artigo():
    """A secção do mapa composto no ARTIGO, contra as mesmas fontes da tese.

    O artigo é um documento à parte, com o seu próprio `.tex` e a sua própria
    bibliografia, e já divergiu da tese duas vezes (as figuras, a 21 jul e a
    4 ago). Ganhou a QI7 a 18 ago, em versão destilada: se algum destes números
    for recalculado do lado da dissertação, aqui não muda nada — e é por isso
    que a comparação é com os CSV, e não com o `main.tex`.
    """
    art = os.path.join(RAIZ, "Artigo", "artigo.tex")
    if not os.path.exists(art):
        return
    with open(art, encoding="utf-8") as fh:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", fh.read())
    i = tex.find("Composição de dificuldades: um mapa quatro vezes maior")
    if i < 0:
        print("\n  [i] o artigo não tem a secção do mapa composto — nada a "
              "verificar. (A dissertação tem: são dois documentos a dizer "
              "coisas diferentes sobre o mesmo trabalho.)")
        return
    sec = tex[i:i + 2500]

    print()
    print("=" * 74)
    print("ARTIGO (secção do mapa composto)  vs  os mesmos CSV da tese")
    print("=" * 74)

    # F1: as células e os episódios das quatro condições
    csvs = sorted(glob.glob(os.path.join(F1_DIR, "zeroshot_*.csv")))
    if csvs:
        dfs = {os.path.basename(c): pd.read_csv(c) for c in csvs}
        natural = next((d for n, d in dfs.items() if "natural" in n), None)
        col_cen = "Origem" if natural is not None and "Origem" in natural \
            else "Scenario"
        col_alg = "Algorithm" if natural is not None and "Algorithm" in natural \
            else "algorithm"
        total_cel = sum(d.groupby([col_cen, col_alg]).ngroups
                        for d in dfs.values())
        total_ep = sum(len(d) for d in dfs.values())
        compara("artigo: células a zero", float(total_cel),
                le(r"o mesmo: \$(\d+)\$ células a zero", sec,
                   "células a zero (artigo)"), tol=0.01)
        compara("artigo: episódios do F1", float(total_ep),
                le(r"células a zero em \$(\d+)\$\n?episódios", sec,
                   "episódios do F1 (artigo)"), tol=0.01)
        if natural is not None:
            compara("artigo: campeões que não transferem",
                    float(natural.groupby([col_cen, col_alg]).ngroups),
                    le(r"nenhum dos \$(\d+)\$ campeões", sec,
                       "campeões (artigo)"), tol=0.01)

    # F2: quem resolve o mapa, e o limiar
    m = medir_f2_seguro()
    if m and m.get("por_algo"):
        conv = {a: int(v["convergentes"]) for a, v in m["por_algo"].items()}
        n_exec = {a: int(v["n"]) for a, v in m["por_algo"].items()}
        g = re.search(r"em \$(\d+)\$ das \$(\d+)\$ execuções,\s+contra \$(\d+)\$"
                      r"\s+de \$(\d+)\$ do PPO e \$(\d+)\$ de \$(\d+)\$ do SAC",
                      sec)
        if g is None:
            falhas.append("artigo: não encontrei a frase do F2 (mudou a "
                          "redação?)")
        else:
            alvos = (("GNN", 0, 1), ("PPO", 2, 3), ("SAC", 4, 5))
            for algo, i_c, i_n in alvos:
                if algo.lower() in conv or algo in conv:
                    chave = algo if algo in conv else algo.lower()
                    compara("artigo: %s resolve" % algo, float(conv[chave]),
                            float(g.group(i_c + 1)), tol=0.01)
                    compara("artigo: %s n" % algo, float(n_exec[chave]),
                            float(g.group(i_n + 1)), tol=0.01)
        # o limiar sai do n, não de um número escrito à mão: ⌈5/7 × n⌉
        n_gnn = n_exec.get("GNN", n_exec.get("gnn", 0))
        if n_gnn:
            limiar = math.ceil(5.0 / 7.0 * n_gnn)
            compara("artigo: limiar pré-registado", float(limiar),
                    le(r"abaixo do limiar de \$(\d+)\$ execuções convergentes",
                       sec, "limiar (artigo)"), tol=0.01)


def trabalho_futuro():
    """O item do mapa composto nos Trabalhos Futuros (está no `main.tex`).

    Este item afirma coisas que nenhum outro verificador vê, por viverem
    fora da `seccao_mapa_grande.tex`: quantas execuções tinham o pico do
    `fitness` nos últimos 20% do treino, e o que muda quando se duplica o
    horizonte. São números de diagnóstico, das curvas de treino e do
    `horizonte_gnn.csv` — e o `horizonte_gnn.csv` é um ficheiro que vai crescer
    (mais episódios por célula), pelo que a probabilidade de o texto e os dados
    divergirem é alta. Daí estar aqui.
    """
    main_tex = os.path.join(RAIZ, "Tese", "main.tex")
    if not os.path.exists(main_tex):
        return
    with open(main_tex, encoding="utf-8") as fh:
        tex = re.sub(r"(?<!\\)%[^\n]*", "", fh.read())
    i = tex.find("O mapa composto, com o orçamento separado em três causas")
    if i < 0:
        print("\n  [i] o item do mapa composto não está nos Trabalhos Futuros "
              "— nada a verificar.")
        return
    item = tex[i:i + 3000]

    print()
    print("=" * 74)
    print("TRABALHOS FUTUROS (item do mapa composto)  vs  as medições")
    print("=" * 74)

    # as curvas de treino: quantas ainda subiam, e onde caiu o pico
    curvas = sorted(glob.glob(os.path.join(
        RAIZ, "results", "mapa_grande", "f2_gnn", "logs",
        "gnn_3d_training_mapa_grande_run*.csv")))
    if curvas:
        picos, n_ultimos = [], 0
        for f in curvas:
            d = pd.read_csv(f)
            if "best_fitness" not in d or len(d) < 2:
                continue
            fracao = d.best_fitness.idxmax() / (len(d) - 1)
            picos.append(fracao)
            n_ultimos += fracao > 0.8
        compara("execuções com o pico nos últimos 20%", float(n_ultimos),
                le(r"Em \$(\d+)\$ das \$21\$ execuções o melhor", item,
                   "execuções com o pico no fim"), tol=0.0)
        compara("geração do pico (mediana, % do orçamento)",
                100.0 * float(np.median(picos)),
                le(r"em mediana, a \$(\d+)\\%\$ do orçamento", item,
                   "mediana do pico"), tol=1.0)

    # o teste do horizonte
    fp = os.path.join(RAIZ, "results", "mapa_grande", "horizonte_gnn.csv")
    if os.path.exists(fp):
        h = pd.read_csv(fp)
        por = {k: g.groupby("Run").recolhas.max()
               for k, g in h.groupby("horizonte")}
        if 2000 in por and 4000 in por:
            compara("execuções com recolha a 2000 passos",
                    float((por[2000] > 0).sum()),
                    le(r"execuções com pelo menos uma recolha apenas de "
                       r"\$(\d+)\$ para \$\d+\$", item, "recolhas a 2000"),
                    tol=0.0)
            compara("execuções com recolha a 4000 passos",
                    float((por[4000] > 0).sum()),
                    le(r"execuções com pelo menos uma recolha apenas de "
                       r"\$\d+\$ para \$(\d+)\$", item, "recolhas a 4000"),
                    tol=0.0)
            compara("melhor execução a 2000 passos (recolhas)",
                    float(por[2000].max()),
                    le(r"\(de \$(\d+)\$ para \$\d+\$ recolhas por episódio\)",
                       item, "melhor a 2000"), tol=0.0)
            compara("melhor execução a 4000 passos (recolhas)",
                    float(por[4000].max()),
                    le(r"\(de \$\d+\$ para \$(\d+)\$ recolhas por episódio\)",
                       item, "melhor a 4000"), tol=0.0)
            # A distância mediana ao ninho, nos dois horizontes. É o par que
            # sustenta a distinção do item («mais percurso feito, não mais
            # execuções a fechar») e o que mais mexeu quando os episódios por
            # célula passaram de 1 para 3 — daí estar sob verificação.
            dm = {k: g.groupby("Run").d_min.min().median()
                  for k, g in h.groupby("horizonte")}
            compara("distância mediana ao ninho a 2000 passos (m)", dm[2000],
                    le(r"mediana ao ninho cair de \$([\d{},]+)\$ para", item,
                       "d_min mediana a 2000"), tol=0.1)
            compara("distância mediana ao ninho a 4000 passos (m)", dm[4000],
                    le(r"cair de \$[\d{},]+\$ para \$([\d{},]+)\$\\,m", item,
                       "d_min mediana a 4000"), tol=0.1)
            # E a coerência com a avaliação oficial: ao horizonte pré-registado,
            # este diagnóstico tem de reproduzir o k que a secção reporta.
            m_ofic = medir_f2_seguro()
            if m_ofic:
                compara("k a 2000 passos vs o k da avaliação oficial",
                        float(m_ofic["max_convergentes"]),
                        float((por[2000] > 0).sum()), tol=0.0)
            # «há 5 execuções que param a menos de 13 m do ninho --- 3 delas a
            # menos de 5 m --- e não entram nele mesmo com o dobro do tempo».
            #
            # São DUAS contagens, e é isso que se confere: escrita como intervalo
            # («param a 5--13 m»), a frase deixava de fora as execuções que param
            # a 2,3, 4,1 e 4,9 m, que são as que mais sustentam o argumento — o
            # que falta é a aproximação final, não o orçamento.
            m_int = re.search(r"há \$(\d+)\$ execuções que param a menos de "
                              r"\$(\d+)\$\\,m do ninho --- \$(\d+)\$ delas a menos "
                              r"de \$(\d+)\$\\,m --- e não entram", item)
            if m_int is None:
                falhas.append("Trabalhos Futuros: não encontrei a frase das "
                              "execuções presas perto do ninho")
            else:
                n_perto, lim, n_muito, lim2 = (float(m_int.group(i)) for i in (1, 2, 3, 4))
                d4 = h[h.horizonte == 4000].groupby("Run").agg(
                    dmin=("d_min", "min"), rec=("recolhas", "max"))
                paradas = d4[d4.rec == 0].dmin
                compara("execuções que param a menos de %g m sem entrar" % lim,
                        float((paradas < lim).sum()), n_perto, tol=0.0)
                compara("dessas, as que param a menos de %g m" % lim2,
                        float((paradas < lim2).sum()), n_muito, tol=0.0)


def _f2_contra_texto(texto):
    """A tabela, o M1--M3 e a Discussão do F2 contra o `medir_f2()`.

    Enquanto a secção teve `\\PORPREENCHER`, esta comparação não existia — só o
    aviso acima. No dia em que ela foi preenchida (17 ago) isso deixou os
    números acabados de escrever sem ninguém a conferi-los, e o primeiro
    defeito apareceu de imediato: a Discussão dizia «4 chegam aos 100% de
    sucesso» onde a M2, duas linhas acima, dizia 2. Não foi erro de dados — foi
    o `fechar_qi7.py` a resolver a chave `k100` pelo prefixo `k`.

    Isto compara com a MESMA função que escreve (`medir_f2`), e por isso não
    prova que a regra esteja certa. Prova outra coisa, que é o que falha na
    prática: que o texto continua a dizer o que os CSV dizem hoje — depois de
    uma edição à mão, de um CSV regenerado, ou de um bug de preenchimento como
    aquele.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from analise_mapa_grande import medir_f2
    m = medir_f2()
    if not m:
        return
    print()
    print("  a secção  vs  medir_f2()")

    def confere(rot, na_tese, medido, tol=0.05):
        if na_tese is None:
            falhas.append("%s: não consegui ler o valor na secção" % rot)
            print("  [X] %-46s não consegui ler na secção" % rot)
            return
        compara(rot, medido, na_tese, tol)

    # a tabela: uma linha por algoritmo
    # As linhas da tabela leem-se por LINHA de ficheiro, não por regex sobre o
    # texto todo: as células trazem `\%` e a linha acaba em `\\`, e um padrão
    # que exclua barras invertidas (para não saltar linhas) não apanha nenhuma
    # das três.
    linhas_tab = {}
    for bruta in texto.splitlines():
        campos_ = [c.strip() for c in bruta.replace("\\\\", "").split("&")]
        if campos_ and campos_[0] in m["por_algo"]:
            linhas_tab[campos_[0]] = campos_[1:]

    for algo, v in m["por_algo"].items():
        campos = linhas_tab.get(algo)
        if campos is None:
            print("  [X] tab:f2_mapa_grande: não encontrei a linha do %s" % algo)
            falhas.append("tab:f2_mapa_grande: sem linha do %s" % algo)
            continue
        vals = [_n(c) for c in campos]
        confere("%s: recolhas/ep" % algo, vals[0], v["media"], 0.05)
        confere("%s: desvio-padrão" % algo, vals[1], v["dp"], 0.05)
        confere("%s: sucesso (%%)" % algo, vals[2], 100.0 * v["sucesso"], 0.5)
        conv = re.search(r"(\d+)/(\d+)", campos[3]) if len(campos) > 3 else None
        confere("%s: convergentes" % algo,
                float(conv.group(1)) if conv else None, v["convergentes"], 0.0)

    # M1: os três pares
    for t in m["m1"]:
        pad = (r"%s \\emph\{vs\.\}\\ %s: \$p = ([\d{},]+)\$, "
               r"\$\\delta = ([+-][\d{},]+)\$" % (t["a"], t["b"]))
        mm = re.search(pad, texto)
        if not mm:
            print("  [X] M1 %s vs %s: não encontrei a frase" % (t["a"], t["b"]))
            continue
        confere("M1 %s vs %s: p" % (t["a"], t["b"]), _n(mm.group(1)),
                t["p"], 0.0005)
        confere("M1 %s vs %s: δ" % (t["a"], t["b"]), _n(mm.group(2)),
                t["delta"], 0.005)

    # M2 e M3
    for algo, v in m["por_algo"].items():
        mm = re.search(r"%s em (\d+)/(\d+), das quais (\d+) a \$100" % algo,
                       texto)
        if not mm:
            print("  [X] M2 %s: não encontrei a frase" % algo)
            continue
        confere("M2 %s: convergentes" % algo, _n(mm.group(1)),
                v["convergentes"], 0.0)
        confere("M2 %s: a 100%% de sucesso" % algo, _n(mm.group(3)),
                v["cem_por_cento"], 0.0)
    mm = re.search(r"porta é aberta: GNN \$(\d+)\\%\$, PPO \$(\d+)\\%\$, "
                   r"SAC \$(\d+)\\%\$", texto)
    if mm:
        for k, algo in enumerate(("GNN", "PPO", "SAC")):
            if algo in m["por_algo"]:
                confere("M3 %s: porta aberta (%%)" % algo, _n(mm.group(k + 1)),
                        100.0 * (m["por_algo"][algo]["porta"] or 0.0), 0.5)
    else:
        print("  [X] M3: não encontrei a frase da porta")

    # a legenda da figura dos rastos cita a instrumentação geodésica
    #
    # Estes três números não vêm do `eval_by_run`: vêm dos
    # `onde_param_{gnn,ppo,sac}.csv`, e a fronteira de 39,1 m é a distância
    # geodésica da passagem B->C ao ninho. Sem esta verificação, a legenda de uma
    # figura seria o único sítio da dissertação com números que ninguém confere.
    mm = re.search(r"zona da porta é de \$(\d+)\\%\$ \(GNN\), \$(\d+)\\%\$ "
                   r"\(PPO\)\s*\n?\s*e \$(\d+)\\%\$ \(SAC\)", texto)
    if mm:
        for k, algo in enumerate(("gnn", "ppo", "sac")):
            fp = os.path.join(RAIZ, "results", "mapa_grande",
                              "onde_param_%s.csv" % algo)
            if not os.path.exists(fp):
                falhas.append("legenda dos rastos: falta o %s"
                              % os.path.basename(fp))
                continue
            d = pd.read_csv(fp)
            confere("rastos: %s chega à passagem B→C (%%)" % algo.upper(),
                    _n(mm.group(k + 1)), 100.0 * (d.d_min < 39.1).mean(), 0.5)
    else:
        print("  [X] legenda dos rastos: não encontrei os 3 valores")
        falhas.append("legenda da figura dos rastos: não encontrei os valores")

    # a Discussão repete o k e o k100: têm de bater com a M2
    campeao = m["algo_campeao"]
    v = m["por_algo"][campeao]
    mm = re.search(r"fiável: (\d+) das \$21\$ execuções atingem pelo menos uma "
                   r"recolha e\s+(\d+) chegam aos \$100", texto)
    if mm:
        confere("Discussão: k (convergentes)", _n(mm.group(1)),
                v["convergentes"], 0.0)
        confere("Discussão: k a 100% de sucesso", _n(mm.group(2)),
                v["cem_por_cento"], 0.0)
    else:
        print("  [X] Discussão: não encontrei a frase do k/k100")


def main():
    if not os.path.exists(SECCAO):
        raise SystemExit("[X] falta %s" % SECCAO)
    texto = _tex()

    print("=" * 74)
    print("VERIFICAÇÃO DA SECÇÃO DO MAPA GRANDE")
    print("=" * 74)
    buracos = re.findall(r"\\PORPREENCHER\{([^}]{0,60})", texto)
    print("  %d \\PORPREENCHER por preencher:" % len(buracos))
    for b in buracos:
        print("     · %s…" % b.strip().replace("\n", " ")[:64])

    geometria(texto)
    f1(texto)
    orcamento(texto)
    f2(texto)
    artigo()
    trabalho_futuro()

    print()
    print("=" * 74)
    if falhas:
        print("%d DIVERGÊNCIA(S) em %d valores conferidos:"
              % (len(falhas), conferidos))
        for f in falhas:
            print("   " + f)
    else:
        print("Os %d valores da secção batem com as fontes ✓" % conferidos)
    print("=" * 74)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
