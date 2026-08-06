# -*- coding: utf-8 -*-
"""Verifica os números da secção do mapa grande (`Tese/seccao_mapa_grande.tex`).

Porque existe, e porque existe AGORA
------------------------------------
A secção entra na dissertação a ~16 de agosto, com seis dias até ao limite de
integração. Nesse dia haverá cinco buracos para preencher, uma leitura para
escolher e um `\\input` para descomentar — e nenhuma vontade de escrever um
verificador. Escrito antes de existirem os números, este verificador faz duas
coisas: valida hoje tudo o que a secção já afirma (a geometria e o F1 inteiro), e
está pronto para validar o F2 no dia em que o `eval_by_run.csv` aparecer.

⚠️ Os valores esperados são LIDOS DO `.tex`, nunca fixados aqui. Um verificador
com os números copiados para dentro de si concorda com a tese por construção e
deixa de ser verificação — passa a ser uma segunda cópia, que é o defeito que
este projeto já apanhou três vezes (a régua do percurso, as figuras do artigo, a
espessura das paredes).

Uso:
    .venv/Scripts/python.exe scripts/verificar_mapa_grande.py
"""
import glob
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


# ── 1. Geometria: a secção descreve o mapa, o simulador constrói-o ───────────
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

    # ⚠️ Os extremos são propriedades da CAIXA de spawn, não de uma amostra de
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


# ── 2. F1: 84 células a zero, e as três causas excluídas ────────────────────
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


# ── 3. Orçamento do F2 ──────────────────────────────────────────────────────
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


# ── 4. F2: ativa-se sozinho quando os dados existirem ───────────────────────
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
    if "PORPREENCHER" in open(SECCAO, encoding="utf-8").read():
        print("  [!] a secção ainda tem \\PORPREENCHER — preencher antes de "
              "comparar.")


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
