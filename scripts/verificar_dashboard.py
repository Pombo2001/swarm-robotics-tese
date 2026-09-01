# -*- coding: utf-8 -*-
r"""Os números do dashboard contra os da dissertação.

Porque existe
O dashboard não é entregável, mas é o que se projeta na defesa — e um número
que apareça nos dois sítios tem de ser o mesmo número. A 4 de agosto dois KPIs
mentiam; a 31 de julho um rótulo anunciava uma proveniência que o ficheiro não
tinha. Nos dois casos o defeito não era o cálculo: era não haver nada que
comparasse as duas superfícies.

Este verificador compara, célula a célula:

* a tabela científica do dashboard (`data.science_table()`, que alimenta as
  vistas Ciência, Resultados e Defesa) com a `tab:res_eval` da dissertação, lida
  do `.tex` — sucesso e recolhas, nos 7 cenários × 3 algoritmos;
* os KPIs do Overview que têm fonte verificável: episódios avaliados,
  cenários, cobertura ≥80%, e o inventário de horas de treino;
* o inventário `_CAMPANHAS` contra as campanhas que existem em `results/` —
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


# 1. a tabela que as vistas mostram vs a que a tese imprime
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


# 2. KPIs do Overview
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

    # inventário de horas: as campanhas que existem estão todas somadas?
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


# 3. imagens que vêm do campeão e não da campanha
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


# 4. o vocabulário do ecrã é o da dissertação
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


def titulos_da_galeria():
    """Os títulos que a Galeria GERA, e não os que estão escritos no código.

    A verificação acima lê os literais de string dos ficheiros do dashboard. Os
    títulos dos cartões da Galeria não são literais: são derivados do nome do
    ficheiro pelo `_pretty_title`, e por isso passaram-lhe ao lado durante toda
    a segunda passagem — que foi a passagem que inventou a família nº9.

    O que escapou: as quatro figuras do mega-treino, que são as que sustentam a
    QI6. Liam-se «Megatreino U Wall 4Bracos» e «Megatreino Ablacao Anneal
    Bypass» — a chave do código à vista, e português sem acentos.

    Aqui gera-se o título de cada PNG das campanhas visíveis e exige-se dele o
    mesmo que dos literais: nada de chaves internas, nada de formas
    abandonadas. Verifica-se ainda que o dicionário escrito à mão não apodrece
    — uma entrada para uma figura que já não existe é uma correção que deixou
    de se aplicar sem ninguém dar por isso.
    """
    global conferidos
    from dashboard import config, data
    from dashboard.views import resultados

    # Os títulos à mão vão buscar o nome do cenário ao vocabulário único, com
    # um `{...}`. Um placeholder que não seja chave de cenário rebenta no
    # `.format` — e rebentava aqui dentro, com um traceback em vez de uma
    # frase. Conferido primeiro, para a régua dizer o que está mal.
    maus = []
    for f, modelo in sorted(resultados._TITULOS_A_MAO.items()):
        conferidos += 1
        for chave in re.findall(r"\{(\w+)\}", modelo):
            if chave not in config.SCENARIO_LABEL_SHORT:
                maus.append("o título à mão de %s usa {%s}, que não é chave "
                            "de cenário nenhuma" % (f, chave))
    if maus:
        # Só desta verificação: gerar os títulos a seguir rebentaria no
        # `.format`, e um traceback diz menos do que a frase acima.
        falhas.extend(maus)
        return

    a_mao = set(resultados._TITULOS_A_MAO)
    chaves = sorted(config.SCENARIO_KEYS, key=len, reverse=True)
    vistos, n = set(), 0
    for s in data.campanhas_visiveis():
        d = os.path.join(RAIZ, "results", "graficos_tese", s)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".png"):
                continue
            a_mao.discard(f)
            titulo = resultados._pretty_title(f)
            n += 1
            if titulo in vistos:
                continue
            vistos.add(titulo)
            conferidos += 1
            for padrao, certo in FORMAS_ABANDONADAS:
                if re.search(padrao, titulo):
                    falhas.append("a Galeria titula %r (forma abandonada; "
                                  "usar %r) — de %s" % (titulo, certo, f))
            for chave in chaves:
                # Sem `\b`: a chave chega ao título já passada pelo `.title()`
                # e com os `_` virados espaço («u_wall» vira «U Wall»), e é
                # nessa forma que tem de ser apanhada.
                solta = re.escape(chave).replace("_", r"[ _]")
                if re.search(solta, titulo, re.I):
                    falhas.append(
                        "a Galeria titula %r com a chave interna %r em vez de "
                        "%r — de %s"
                        % (titulo, chave,
                           config.SCENARIO_LABEL_SHORT.get(chave, chave), f))
                    break
    if a_mao:
        falhas.append("títulos escritos à mão para figuras que já não existem "
                      "em campanha visível nenhuma: %s" % sorted(a_mao))
    print("[i] galeria      %d títulos distintos gerados de %d figuras"
          % (len(vistos), n))


def rotulos_do_episodio_3d():
    """Os rótulos do seletor do Episódio 3D, que vêm dos JSON gravados.

    Mesmo mecanismo dos títulos da Galeria, outra fonte: o texto não está no
    código do dashboard, está dentro dos ficheiros exportados. Estes foram
    escritos com o `SCENARIO_LABELS` do `src/`, que é anterior à uniformização
    dos nomes, e o seletor oferecia «Beco Sem Saída (Muro U)», «Mapa Grande
    (Labirinto Composto)» e «Porta Cooperativa c/ Alternativa» — três formas
    abandonadas, num seletor que se usa a projetar.

    Um verificador que só lê o código nunca veria isto: o código estava certo,
    era a origem dos dados que era velha.
    """
    global conferidos
    from dashboard import config
    from dashboard.views import viz3d

    rotulos = viz3d._episodios()
    if not rotulos:
        print("[i] episódio 3D  sem episódios exportados nesta máquina")
        return
    chaves = sorted(config.SCENARIO_KEYS, key=len, reverse=True)
    for rot in sorted(rotulos):
        conferidos += 1
        for padrao, certo in FORMAS_ABANDONADAS:
            if re.search(padrao, rot):
                falhas.append("o seletor do Episódio 3D oferece %r (forma "
                              "abandonada; usar %r)" % (rot, certo))
        for chave in chaves:
            solta = re.escape(chave).replace("_", r"[ _]")
            if re.search(solta, rot, re.I):
                falhas.append("o seletor do Episódio 3D oferece %r com a chave "
                              "interna %r" % (rot, chave))
                break
    print("[i] episódio 3D  %d rótulos do seletor" % len(rotulos))


def concordancia_de_numero():
    """Nenhuma frase do ecrã diz «1 vídeos».

    O plural em duro é barato de escrever e passa despercebido a quem testa com
    os dados grandes — 21 execuções, 1680 episódios. Só aparece na campanha
    pequena: 14 das 30 campanhas exibidas gravaram UM episódio, e a vista
    Vídeos lia-se «sessão ... · 1 vídeos ·» em quase metade dos casos, a
    começar pela que abre por omissão.

    Aqui não se lê código: geram-se as frases com as contagens que o disco tem,
    e mais a contagem 1, que é a que parte. O `theme.plural` é o sítio único
    onde a regra vive.
    """
    global conferidos
    from dashboard import data, theme

    # As contagens por campanha que aparecem em texto, e o substantivo que as
    # acompanha. Se alguma valer 1 nesta máquina, a frase tem de concordar.
    contagens = {
        "vídeo": [len(data.list_videos(s)) for s in data.campanhas_visiveis()],
        "gráfico": [len(data.list_pngs(s)) for s in data.campanhas_visiveis()],
        "heatmap": [len([p for p in data.list_pngs(s) if "heatmap" in p])
                    for s in data.campanhas_visiveis()],
    }
    for substantivo, valores in sorted(contagens.items()):
        # O 1 entra sempre, mesmo que hoje nenhuma campanha o tenha: é
        # precisamente o valor que ninguém testa.
        for v in sorted(set(valores) | {0, 1}):
            conferidos += 1
            frase = theme.plural(v, substantivo)
            esperado = "%d %s" % (v, substantivo if v == 1
                                  else substantivo + "s")
            if frase != esperado:
                falhas.append("theme.plural(%d, %r) devolve %r, esperava %r"
                              % (v, substantivo, frase, esperado))
        um = sum(1 for v in valores if v == 1)
        if um:
            print("[i] plural       %d das %d campanhas têm 1 %s"
                  % (um, len(valores), substantivo))


def main():
    tabela_cientifica()
    kpis()
    galeria()
    vocabulario()
    titulos_da_galeria()
    rotulos_do_episodio_3d()
    concordancia_de_numero()
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
