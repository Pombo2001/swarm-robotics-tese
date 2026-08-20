# -*- coding: utf-8 -*-
"""Fecha a QI7 na dissertação: lê o F2, aplica a regra pré-registada, escreve.

Porque existe
-------------
A secção do mapa grande está escrita e ensaiada, mas entra na tese com cinco
`\\PORPREENCHER` por preencher e **três leituras alternativas** (A/B/C) à espera
de escolha, em seis sítios diferentes do `.tex` — secção, pergunta, parágrafo
das Conclusões, resposta às QI, Resumo e Abstract. Feito à mão no dia em que o
GNN fechar, isso é meia hora de edição com o relógio a correr até 22 ago, e
cada número copiado à mão é um número que o verificador dos 352 valores pode
vir a apanhar. Aqui é um comando.

O que este script NÃO faz
-------------------------
Não escolhe a leitura por gosto nem por conveniência: aplica a regra de decisão
fixada **antes** dos dados (⌈5/7 × n⌉ = 15 de 21 execuções convergentes em pelo
menos um algoritmo; emendas 19 e 21), e a contagem vem da **avaliação
determinística** — o `eval_by_run.csv` —, nunca das curvas de treino. É a
distinção que o `projetar_limiar_f2.py` teve de aprender à força a 13 ago: as
execuções que aparecem com recolha no treino são o `best_task_food` do melhor
genoma contra as suas sementes, um majorante otimista, e decidir entre (B) e
(C) por aí seria medir uma métrica com duas réguas.

Também não inventa números: tudo o que escreve sai do `medir_f2()` do
`analise_mapa_grande.py` (a conta vive lá) e do `estado_f2.json`.

Uso
---
    python scripts/fechar_qi7.py                 # só diz o que faria
    python scripts/fechar_qi7.py --escrever      # aplica ao .tex
    python scripts/fechar_qi7.py --simular C     # ensaio, com dados inventados
    python scripts/fechar_qi7.py --escrever --forcar   # com o GNN incompleto
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from analise_mapa_grande import medir_f2  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESE = os.path.join(RAIZ, "Tese")
MAIN = os.path.join(TESE, "main.tex")
SECCAO = os.path.join(TESE, "seccao_mapa_grande.tex")
ESTADO = os.path.join(RAIZ, "results", "estado_f2.json")


# ── números → português ──────────────────────────────────────────────────────

def num(v, casas=1):
    """`67.4` → `$67{,}4$`. A tese usa vírgula decimal em modo matemático."""
    if v is None:
        return "---"
    s = ("%%.%df" % casas) % v
    return "$" + s.replace(".", "{,}") + "$"


def pct(v, casas=0):
    """`0.0` → `$0\\%$`. O `%` fica DENTRO do modo matemático, como na tese."""
    if v is None:
        return "---"
    s = ("%%.%df" % casas) % (100.0 * v)
    return "$" + s.replace(".", "{,}") + "\\%$"


def p_legivel(p):
    """`p<0,0001` em vez de `0,0000` — um zero ali lê-se como «p igual a zero»."""
    if p < 0.0001:
        return "$p < 0{,}0001$"
    return "$p = %s$" % ("%.4f" % p).replace(".", "{,}")


# ── as cinco entradas da secção ──────────────────────────────────────────────

def texto_geracoes(estado):
    """As gerações que cada execução perfez, medidas (não as orçamentadas)."""
    runs = (estado or {}).get("gnn", {}).get("runs_fechados") or []
    g = [r["geracoes"] for r in runs if r.get("geracoes")]
    if not g:
        return ("\\PORPREENCHER{gerações efetivamente alcançadas por execução, "
                "média e amplitude}")
    media = sum(g) / len(g)
    return ("Em execução, o orçamento de $780$ minutos traduziu-se em "
            "%s gerações por execução em média (amplitude de $%d$ a $%d$, "
            "sobre as %d execuções fechadas), contra as $13{,}7$ gerações que "
            "as campanhas dos sete cenários perfazem."
            % (num(media), min(g), max(g), len(g)))


def texto_tabela(m):
    """A tabela dos 3 algoritmos × n execuções."""
    linhas = []
    for algo, v in m["por_algo"].items():
        linhas.append("%s & %s & %s & %s & %d/%d \\\\"
                      % (algo, num(v["media"]), num(v["dp"]),
                         pct(v["sucesso"] or 0.0), v["convergentes"], v["n"]))
    return "\n".join([
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\caption{Treino nativo no mapa composto (F2): %d execuções "
        "independentes por algoritmo, avaliação determinística de $20$ "
        "episódios com sementes emparelhadas.}" % m["n_runs"],
        "\\label{tab:f2_mapa_grande}",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "\\textbf{Algoritmo} & \\textbf{Recolhas/ep} & "
        "\\textbf{Desvio-padrão} & \\textbf{Sucesso} & "
        "\\textbf{Convergentes} \\\\",
        "\\hline",
        "\n".join(linhas),
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
    ])


def texto_m1(m):
    """M1 — magnitude. Com tudo a zero, o teste não tem conteúdo: dizê-lo."""
    tudo_zero = all(v["max"] == 0.0 for v in m["por_algo"].values())
    if tudo_zero:
        return ("\\textbf{M1 (magnitude).} Com as %d execuções de cada "
                "algoritmo a $0{,}00$ recolhas por episódio, o teste de "
                "Mann-Whitney sobre médias por execução não tem conteúdo --- "
                "não há um único par discordante ---, e o $\\delta$ de Cliff é "
                "identicamente nulo. O que sustenta a leitura é a contagem de "
                "execuções convergentes (M2), não a comparação de magnitudes."
                % m["n_runs"])
    partes = []
    for t in m["m1"]:
        partes.append("%s \\emph{vs.}\\ %s: %s, $\\delta = %s$"
                      % (t["a"], t["b"], p_legivel(t["p"]),
                         ("%+.2f" % t["delta"]).replace(".", "{,}")))
    return ("\\textbf{M1 (magnitude).} Mann-Whitney $U$ bilateral sobre as "
            "médias por execução ($n = %d$): %s. O peso da evidência está no "
            "tamanho de efeito, como a limitação desta campanha declara."
            % (m["n_runs"], "; ".join(partes)))


def texto_m2(m):
    partes = []
    for algo, v in m["por_algo"].items():
        partes.append("%s em %d/%d, das quais %d a $100\\%%$ de sucesso"
                      % (algo, v["convergentes"], v["n"], v["cem_por_cento"]))
    return ("\\textbf{M2 (convergência, descritivo).} Execuções que atingem "
            "pelo menos uma recolha na avaliação determinística: %s. Pelo "
            "compromisso pré-registado (emenda 19), não se infere sobre "
            "proporções: a contagem é reportada como descritivo."
            % "; ".join(partes))


def texto_m3(m):
    if not m["tem_porta"]:
        return ("\\textbf{M3 (porta cooperativa).} A coluna do estado da porta "
                "não foi registada nesta campanha, pelo que a M3 fica por "
                "reportar --- e declara-se aqui a ausência, em vez de se "
                "omitir a métrica.")
    partes = ["%s %s" % (algo, pct(v["porta"]))
              for algo, v in m["por_algo"].items()]
    todas_zero = all(v["porta"] == 0.0 for v in m["por_algo"].values())
    extra = (" A porta cooperativa nunca chega a ser aberta, o que situa a "
             "falha antes da última das quatro dificuldades compostas."
             if todas_zero else "")
    return ("\\textbf{M3 (porta cooperativa).} Fração de episódios em que a "
            "porta é aberta: %s.%s" % (", ".join(partes), extra))


# ── edição do LaTeX ──────────────────────────────────────────────────────────

def _substituir_porpreencher(texto, inicio_do_conteudo, novo):
    """Troca o `\\PORPREENCHER{...}` cujo conteúdo começa por `inicio_do_conteudo`.

    Conta chavetas em vez de usar regex gulosa: o conteúdo tem `$\\times$`,
    `$\\pm$` e afins, e uma expressão que pare na primeira `}` cortaria a meio.
    """
    marca = "\\PORPREENCHER{"
    proc = 0
    while True:
        i = texto.find(marca, proc)
        if i < 0:
            return texto, False
        j, nivel = i + len(marca), 1
        while j < len(texto) and nivel:
            nivel += (texto[j] == "{") - (texto[j] == "}")
            j += 1
        conteudo = " ".join(texto[i + len(marca):j - 1].split())
        if conteudo.startswith(inicio_do_conteudo):
            return texto[:i] + novo + texto[j:], True
        proc = j


def _distribuicao(v):
    """A forma da distribuição, que é o que a leitura (C) pede em vez da média.

    «A distribuição entre execuções é o resultado, e não a média» — a frase
    está escrita na secção, e a única maneira de a honrar é dizer se as
    execuções que resolvem o fazem por inteiro ou por pouco.
    """
    ativas = [x for x in v["medias_por_run"] if x > 0]
    if not ativas:
        return "todas as execuções a $0{,}00$"
    corpo = ("média de %s recolhas por episódio entre as que recolhem "
             "(amplitude de %s a %s), contra $0{,}00$ nas restantes"
             % (num(sum(ativas) / len(ativas)), num(min(ativas)),
                num(max(ativas))))
    if min(ativas) > 0.5 * max(ativas):
        corpo += (" --- a distribuição é de tudo-ou-nada: as execuções que "
                  "resolvem o mapa resolvem-no com magnitude comparável entre si")
    return corpo


def preencher_restantes(texto, m):
    """Preenche os `\\PORPREENCHER` NUMÉRICOS que vivem dentro das leituras.

    As leituras (A) e (C) trazem `\\PORPREENCHER{k}`, `{algoritmo}`, `{k100}` e
    afins lá dentro. Descomentar a leitura sem os preencher punha caixas
    vermelhas «[POR PREENCHER]» no PDF entregue — o defeito que este script
    existe para evitar, cometido pelo próprio script.

    Os que **não** são números ficam como estão, de propósito: escolhas de
    redação como «não impede / degrada mas não impede» ou «ler contra a Secção
    \\ref{sec:res_scale}» são leitura do autor, e um script que as adivinhasse
    estaria a escrever a tese. Devolve-os para serem declarados em voz alta.
    """
    campeao = m["algo_campeao"]
    v = m["por_algo"][campeao]
    numericos = {
        "algoritmo": campeao,
        "k": str(m["max_convergentes"]),
        "k100": str(v["cem_por_cento"]),
        "n": str(m["max_convergentes"]),
        "valor": num(v["media"]),
        "média e amplitude": _distribuicao(v),
    }
    ficaram, proc = [], 0
    marca = "\\PORPREENCHER{"
    while True:
        i = texto.find(marca, proc)
        if i < 0:
            break
        j, nivel = i + len(marca), 1
        while j < len(texto) and nivel:
            nivel += (texto[j] == "{") - (texto[j] == "}")
            j += 1
        conteudo = " ".join(texto[i + len(marca):j - 1].split())
        # não tocar no que está comentado: são as leituras não escolhidas
        linha = texto.rfind("\n", 0, i) + 1
        comentado = texto[linha:i].lstrip().startswith("%")
        # A chave MAIS LONGA que corresponda, não a primeira: `k100` começa por
        # `k`, e como `k` vinha antes no dicionário o buraco «quantas chegam aos
        # 100% de sucesso» ficava com o número de execuções convergentes. Na
        # primeira escrita isso pôs «4 chegam aos 100%» numa secção
        # onde a M2, duas linhas acima, dizia 2 — a tese a contradizer-se a si
        # própria por um prefixo.
        chave = max((k for k in numericos if conteudo.startswith(k)),
                    key=len, default=None)
        if comentado or chave is None:
            if not comentado:
                ficaram.append(conteudo[:60])
            proc = j
            continue
        texto = texto[:i] + numericos[chave] + texto[j:]
        proc = i + len(numericos[chave])
    return texto, ficaram


def _descomentar(bloco):
    """Tira o `%` inicial de cada linha (e o espaço a seguir, se houver)."""
    out = []
    for linha in bloco.split("\n"):
        s = linha.lstrip()
        if s.startswith("%"):
            s = s[1:]
            out.append(s[1:] if s.startswith(" ") else s)
        else:
            out.append(linha)
    return "\n".join(out)


def _bloco_variante(texto, cabecalho, letra):
    """Devolve (inicio, fim, corpo) do bloco de comentário da variante `letra`.

    Os blocos têm todos a mesma forma: uma linha de cabeçalho distintiva, e
    depois as variantes marcadas `% (A)`, `% (B)`, `% (C)`, cada uma até à
    seguinte ou até à primeira linha que já não é comentário.
    """
    i = texto.find(cabecalho)
    if i < 0:
        return None
    linhas = texto[i:].split("\n")
    fim_rel, dentro, corpo, achou = 0, False, [], False
    for n, linha in enumerate(linhas):
        s = linha.strip()
        if n and not s.startswith("%"):
            fim_rel = n
            break
        marca = re.match(r"%\s*\((A|B|C)\)\s*(.*)$", s)
        if marca:
            dentro = (marca.group(1) == letra)
            achou = achou or dentro
            if dentro:
                resto = marca.group(2).strip()
                # Dois formatos convivem nestes blocos. No Resumo e no Abstract
                # o "(A)" é seguido do próprio texto; nas Conclusões e na
                # Resposta é seguido de um RÓTULO da condição («≥15/21 num
                # algoritmo:»), e o texto começa na linha a seguir. Levar o
                # rótulo para o PDF metia lá «≥15/21 num algoritmo:» a meio de
                # um parágrafo — e o «≥» nem sequer compila (Unicode fora do
                # mapa do pdfLaTeX). Distingue-se pelos dois pontos finais.
                if resto.endswith(":"):
                    continue
                corpo.append(re.sub(r"^(\s*)%\s*\([ABC]\)\s*", r"\1% ", linha))
                continue
        if dentro:
            corpo.append(linha)
    else:
        fim_rel = len(linhas)
    if not achou:
        return None
    fim = i + sum(len(l) + 1 for l in linhas[:fim_rel])
    return i, fim, _descomentar("\n".join(corpo)).strip()


# ── o trabalho ───────────────────────────────────────────────────────────────

CABECALHOS = {
    "resumo": "% ── Frase da QI7 no Resumo",
    "abstract": "% ── QI7 sentence for the Abstract",
    "conclusoes": "% ── Parágrafo da QI7 nas Conclusões",
    "resposta": "% ── RESPOSTA À QI7",
}


def aplicar(m, estado, leitura, escrever):
    """Escreve (ou simula) as seis alterações. Devolve a lista do que fez."""
    feito, falhou = [], []

    # ── 1. a secção: os cinco \PORPREENCHER ──────────────────────────────────
    sec = open(SECCAO, encoding="utf-8").read()
    entradas = [
        ("gerações efetivamente alcançadas", texto_geracoes(estado)),
        ("tabela dos $3$ algoritmos", texto_tabela(m)),
        ("M1 ---", texto_m1(m)),
        ("M2 ---", texto_m2(m)),
        ("M3 ---", texto_m3(m)),
    ]
    for chave, novo in entradas:
        sec, ok = _substituir_porpreencher(sec, chave, novo)
        (feito if ok else falhou).append("secção: %s" % chave)

    # ── 2. a secção: a leitura escolhida na Discussão ────────────────────────
    # As três leituras da secção não usam o formato "% (A)" dos blocos do
    # main.tex: são três blocos seguidos, cada um com o seu cabeçalho.
    cab_leitura = "%s ── LEITURA %s:" % ("%", leitura)
    i = sec.find(cab_leitura)
    if i < 0:
        falhou.append("secção: leitura (%s)" % leitura)
    else:
        linhas = sec[i:].split("\n")
        corpo = []
        for n, linha in enumerate(linhas):
            s = linha.strip()
            if n and (not s.startswith("%") or s.startswith("%s ── LEITURA" % "%")):
                break
            corpo.append(linha)
        sec = sec.replace("\n".join(corpo),
                          _descomentar("\n".join(corpo[1:])).strip())
        feito.append("secção: leitura (%s) descomentada" % leitura)

    sec, sobram_sec = preencher_restantes(sec, m)

    if escrever:
        shutil.copy2(SECCAO, SECCAO + ".bak")
        open(SECCAO, "w", encoding="utf-8").write(sec)

    # ── 3. o main.tex: os cinco blocos + o \input ───────────────────────────
    txt = open(MAIN, encoding="utf-8").read()

    for nome, cab in CABECALHOS.items():
        b = _bloco_variante(txt, cab, leitura)
        if b is None:
            falhou.append("main: %s (%s)" % (nome, leitura))
            continue
        ini, fim, corpo = b
        txt = txt[:ini] + corpo + "\n\n" + txt[fim:]
        feito.append("main: %s → variante (%s)" % (nome, leitura))

    # a PERGUNTA não tem variantes: é a mesma nos três desfechos
    alvo = "%    \\item[\\textbf{QI7.}] \\textbf{Composição de dificuldades:}"
    i = txt.find(alvo)
    if i < 0:
        falhou.append("main: pergunta da QI7")
    else:
        linhas = txt[i:].split("\n")
        corpo = []
        for linha in linhas:
            if not linha.strip().startswith("%"):
                break
            corpo.append(linha)
        txt = txt.replace("\n".join(corpo), _descomentar("\n".join(corpo)))
        feito.append("main: pergunta da QI7 descomentada")

    # o \input da secção
    if "\n% \\input{seccao_mapa_grande}" in txt:
        txt = txt.replace("\n% \\input{seccao_mapa_grande}",
                          "\n\\input{seccao_mapa_grande}")
        feito.append("main: \\input{seccao_mapa_grande} descomentado")
    elif "\n\\input{seccao_mapa_grande}" in txt:
        feito.append("main: \\input já estava descomentado")
    else:
        falhou.append("main: \\input{seccao_mapa_grande}")

    txt, sobram_main = preencher_restantes(txt, m)

    if escrever:
        shutil.copy2(MAIN, MAIN + ".bak")
        open(MAIN, "w", encoding="utf-8").write(txt)

    return feito, falhou, sobram_sec + sobram_main


def _simular(letra):
    """Dados inventados para ensaiar o script antes de o GNN fechar.

    Ensaiar a troca no dia em que os dados chegam é ensaiá-la tarde demais.
    """
    def arm(conv, valor):
        medias = [valor] * conv + [0.0] * (21 - conv)
        return {"n": 21, "media": sum(medias) / 21,
                "dp": 1.0 if conv else 0.0,
                "sucesso": conv / 21.0, "convergentes": conv,
                "cem_por_cento": max(0, conv - 1), "medias_por_run": medias,
                "porta": 0.3 if conv else 0.0,
                "min": 0.0, "max": max(medias)}
    conv = {"A": 17, "B": 0, "C": 4}[letra]
    return {
        "fontes": ["(SIMULADO — nenhum ficheiro foi lido)"],
        "n_runs": 21, "limiar": 15,
        "por_algo": {"GNN": arm(conv, 12.5), "PPO": arm(0, 0.0),
                     "SAC": arm(0, 0.0)},
        "m1": [{"a": "GNN", "b": "PPO", "p": 0.002, "delta": 0.61},
               {"a": "GNN", "b": "SAC", "p": 0.002, "delta": 0.61}],
        "algo_campeao": "GNN", "max_convergentes": conv, "tem_porta": True,
        "leitura": letra,
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--escrever", action="store_true",
                    help="aplica ao .tex (por omissão só diz o que faria)")
    ap.add_argument("--simular", choices=["A", "B", "C"],
                    help="ensaio com dados inventados, sem tocar nos CSV")
    ap.add_argument("--forcar", action="store_true",
                    help="escreve mesmo com o GNN incompleto")
    ap.add_argument("--escrever-ensaio", action="store_true",
                    help="com --simular, escreve MESMO os números inventados "
                         "no .tex (para compilar o desfecho e ver como fica); "
                         "repor com: git checkout Tese/")
    a = ap.parse_args()

    estado = None
    if os.path.exists(ESTADO):
        estado = json.load(open(ESTADO, encoding="utf-8"))

    if a.escrever_ensaio and not a.simular:
        raise SystemExit("[X] --escrever-ensaio só faz sentido com --simular.")

    if a.simular:
        m = _simular(a.simular)
        print("⚠️  MODO DE ENSAIO: os números abaixo são INVENTADOS, para "
              "verificar a mecânica da troca.")
        if a.escrever_ensaio:
            print("⚠️  E VÃO SER ESCRITOS NO .tex. Repor com: git checkout Tese/")
        print()
    else:
        m = medir_f2()
        if m is None:
            raise SystemExit("[X] sem eval_by_run.csv em results/mapa_grande/"
                             "f2*/ — nada a fazer.")

    print("=" * 74)
    print("FECHO DA QI7  —  regra pré-registada: ⌈5/7 × %d⌉ = %d execuções "
          "convergentes" % (m["n_runs"], m["limiar"]))
    print("=" * 74)
    print("  fonte: %s" % ", ".join(m["fontes"]))
    for algo, v in m["por_algo"].items():
        print("    %-4s %6.1f ± %5.1f rec/ep   ≥1 recolha: %2d/%d   100%%: %d"
              % (algo, v["media"], v["dp"], v["convergentes"], v["n"],
                 v["cem_por_cento"]))
    print()

    tem_gnn = "GNN" in m["por_algo"]
    completo = tem_gnn and m["por_algo"]["GNN"]["n"] >= 21
    if not tem_gnn:
        print("  ⚠️  O braço do GNN AINDA NÃO ESTÁ NA AVALIAÇÃO.")
        print("      A escolha entre (B) e (C) depende dele: é o k da secção.")
    elif not completo:
        print("  ⚠️  O GNN tem só %d das 21 execuções avaliadas."
              % m["por_algo"]["GNN"]["n"])

    print("  → leitura (%s): %s" % (m["leitura"], {
        "A": "a QI7 SOBE a resposta afirmativa",
        "B": "negativo — nenhum algoritmo resolve o mapa",
        "C": "negativo pela regra proporcional, com o k declarado",
    }[m["leitura"]]))
    print()

    if a.escrever and not (a.simular or completo or a.forcar):
        raise SystemExit(
            "[X] não escrevo com o GNN incompleto: a leitura ainda pode mudar.\n"
            "    Usar --forcar se for mesmo essa a intenção.")

    escrever = (a.escrever_ensaio if a.simular
                else a.escrever)
    feito, falhou, sobram = aplicar(m, estado, m["leitura"], escrever)

    print("  %s:" % ("ESCRITO" if escrever else "FARIA"))
    for f in feito:
        print("    ✔ %s" % f)
    for f in falhou:
        print("    ✘ NÃO ENCONTRADO — %s" % f)

    if sobram:
        print()
        print("  ⚠️  FICAM %d \\PORPREENCHER POR ESCREVER — são escolhas de "
              "redação, não números," % len(sobram))
        print("      e apareceriam a VERMELHO no PDF. Escrever à mão antes de "
              "entregar:")
        for s in sobram:
            print("        · %s…" % s)

    if falhou:
        print("\n  ⚠️  %d bloco(s) por tratar: o .tex mudou de forma desde que "
              "este script foi escrito. Tratar à mão e corrigir o script."
              % len(falhou))
    if a.escrever and not a.simular:
        print("\n  Cópias de segurança: main.tex.bak, seccao_mapa_grande.tex.bak")
        print("  A seguir:")
        print("    python scripts/verificar_numeros_tese.py")
        print("    cd Tese && pdflatex main.tex")
    else:
        print("\n  (nada foi escrito — repetir com --escrever)")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
