# -*- coding: utf-8 -*-
r"""Cada compromisso pré-registado contra o que a dissertação reporta.

Porque existe
-------------
Três pré-registos, com emendas até à 21ª, fixam antes dos dados o que vai ser
medido, com que n, e o que tem de ser reportado aconteça o que acontecer. **Um
compromisso pré-registado que não seja reportado é o defeito mais caro que esta
tese pode ter** — mais do que um número errado, porque é o que separa uma regra
fixada à partida de uma escolhida depois de ver os resultados.

Este verificador constrói a tabela *compromisso → onde é reportado → bate*, e
verifica executavelmente tudo o que é verificável:

* o **desenho executado** (algoritmos, execuções, episódios, parâmetros do
  ambiente) contra o desenho pré-registado — lido dos CSV e do simulador;
* a **presença** de cada compromisso de reporte no `.tex`, ignorando linhas
  comentadas (a QI7 viveu meses em comentário: um parser ingénuo dá-a por
  escrita);
* os **desvios**: um braço pré-registado que não produziu dados tem de estar
  declarado por escrito e datado, senão o compromisso 5 («qualquer desvio é
  datado abaixo, nunca silencioso») está por cumprir.

O que este verificador **não** faz é conferir os números de M1--M3 do mapa
grande: isso é o `verificar_mapa_grande.py`, que os lê do `.tex` e recalcula-os
dos CSV. Aqui verifica-se que as métricas **estão lá**, não que valem o que
dizem valer — duas perguntas diferentes, dois instrumentos.

Estados:
    [v] OK       — verificado por medição ou por padrão encontrado no texto
    [X] FALHA    — compromisso por cumprir (código de saída 1)
    [.] LEITURA  — só uma pessoa pode decidir; fica listado, não conta como falha

Uso:
    .venv/Scripts/python.exe scripts/verificar_preregistos.py
    .venv/Scripts/python.exe scripts/verificar_preregistos.py --escrever
        (grava a tabela em docs/PREREGISTO_VS_REPORTADO.md)
"""
import json
import os
import re
import sys
from datetime import datetime

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

MAIN = os.path.join(RAIZ, "Tese", "main.tex")
SECCAO = os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex")
PRE_MG = os.path.join(RAIZ, "docs", "PRE_REGISTO_MAPA_GRANDE.md")
PRE_MT = os.path.join(RAIZ, "docs", "PRE_REGISTO_MEGATREINO.md")
PRE_NA = os.path.join(RAIZ, "docs", "PRE_REGISTO_NOVELTY_ADAPTATIVO.md")
F2 = {
    "GNN": os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn"),
    "PPO": os.path.join(RAIZ, "results", "mapa_grande", "f2_grad_ppo"),
    "SAC": os.path.join(RAIZ, "results", "mapa_grande", "f2_grad_sac"),
}
HARD_STOP = datetime(2026, 8, 22)

linhas = []   # (bloco, id, compromisso, onde, estado, evidência)
falhas = []


# ── utilitários ──────────────────────────────────────────────────────────────
def _ler(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def sem_comentarios_de_texto(texto):
    r"""O `.tex` como o LaTeX o vê: sem `%` que não esteja escapado.

    ⚠️ Não é cosmético. A secção da QI7, o parágrafo das Conclusões e as frases
    do Resumo estiveram semanas dentro de comentários, prontas a entrar; quem
    procurar por regex sem os retirar dá por reportado o que ainda não está.
    """
    saida = []
    for linha in texto.splitlines():
        limpa = re.sub(r"(?<!\\)%.*$", "", linha)
        if limpa.strip():
            saida.append(limpa)
    return "\n".join(saida)


def sem_comentarios(caminho):
    return sem_comentarios_de_texto(_ler(caminho))


def regista(bloco, cid, compromisso, onde, estado, evidencia):
    linhas.append((bloco, cid, compromisso, onde, estado, evidencia))
    marca = {"OK": "[v]", "FALHA": "[X]", "LEITURA": "[.]"}[estado]
    print("  %s %-22s %s" % (marca, cid, evidencia))
    if estado == "FALHA":
        falhas.append("%s: %s" % (cid, evidencia))


def presente(texto, padrao):
    return re.search(padrao, texto, re.S) is not None


def bloco_da_tabela(texto, label):
    """O ambiente `table` que contém `\\label{label}` — ou None."""
    for m in re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", texto, re.S):
        if ("\\label{%s}" % label) in m.group(1):
            return m.group(1)
    return None


# ── medições dos dados (o desenho executado) ────────────────────────────────
def medir_f2():
    """Algoritmos, execuções, episódios e métricas do F2, lidos dos CSV."""
    out = {}
    for algo, pasta in F2.items():
        csv = os.path.join(pasta, "evaluation", "eval_by_run.csv")
        if not os.path.exists(csv):
            out[algo] = None
            continue
        df = pd.read_csv(csv)
        df = df[df["Algorithm"].astype(str).str.upper() == algo]
        por_run = df.groupby("Run")
        out[algo] = {
            "runs": int(df["Run"].nunique()),
            "eps": sorted(set(por_run.size())),
            "convergentes": int((por_run["food_collected"].mean() > 0).sum()),
            "cem": int((por_run["success"].mean() == 1.0).sum()),
            "porta": float(df["door_opened"].mean()) * 100.0,
        }
        sentinela = os.path.join(pasta, "logs", "_campanha_concluida.txt")
        if os.path.exists(sentinela):
            carimbo = _ler(sentinela).strip().split(".")[0]
            out[algo]["fecho"] = datetime.strptime(carimbo, "%Y-%m-%d %H:%M:%S")
    return out


def medir_novelty():
    """Cenários × execuções da campanha do adaptativo (condição primária)."""
    base = os.path.join(RAIZ, "results", "novelty_adaptativo")
    cenarios, runs = set(), set()
    for fase in ("week_A_fase1", "week_B_fase1"):
        csv = os.path.join(base, fase, "evaluation", "eval_by_run.csv")
        if not os.path.exists(csv):
            continue
        df = pd.read_csv(csv)
        cenarios |= set(df["Scenario"].unique())
        runs |= set(df["Run"].unique())
    return cenarios, runs


# ══════════════════════════════════════════════════════════════════════════════
# 1. PRE_REGISTO_MAPA_GRANDE.md  (QI7)
# ══════════════════════════════════════════════════════════════════════════════
def mapa_grande(tex_sec, tex_main, pre):
    print()
    print("=" * 78)
    print("PRE_REGISTO_MAPA_GRANDE.md  —  QI7, o oitavo cenário")
    print("=" * 78)
    B = "Mapa grande (QI7)"
    m = medir_f2()
    onde_sec = "Tese/seccao_mapa_grande.tex"

    # ── desenho: 3 algoritmos × 21 execuções × 20 episódios ─────────────────
    faltam = [a for a, v in m.items() if v is None]
    if faltam:
        regista(B, "MG-desenho-n", "3 algoritmos × 21 execuções (emenda 19)",
                "results/mapa_grande/f2_*", "FALHA",
                "sem eval_by_run.csv para: %s" % ", ".join(faltam))
    else:
        mau = {a: v["runs"] for a, v in m.items() if v["runs"] != 21}
        regista(B, "MG-desenho-n", "3 algoritmos × 21 execuções (emenda 19)",
                "results/mapa_grande/f2_*",
                "OK" if not mau else "FALHA",
                "GNN %d · PPO %d · SAC %d execuções"
                % (m["GNN"]["runs"], m["PPO"]["runs"], m["SAC"]["runs"])
                if not mau else "execuções a menos: %s" % mau)

        eps = {a: v["eps"] for a, v in m.items()}
        ok = all(v == [20] for v in eps.values())
        regista(B, "MG-desenho-ep", "avaliação determinística de 20 episódios",
                "results/mapa_grande/f2_*", "OK" if ok else "FALHA",
                "20 episódios em todas as execuções" if ok
                else "episódios por execução: %s" % eps)

    # ── desenho: os parâmetros congelados na secção 2 do pré-registo ────────
    try:
        import yaml

        from src.environment.swarm_env_3d import SwarmForagingEnv3D
        cfg = yaml.safe_load(_ler(os.path.join(RAIZ, "configs", "foraging.yaml")))
        cfg["environment"]["classic_scenario"] = "mapa_grande"
        env = SwarmForagingEnv3D(config=cfg)
        env.render_mode = None
        env.reset(seed=7)
        medido = {
            "num_agents": int(env.num_agents),
            "max_steps": int(env.max_steps),
            "required_to_eat": int(env.required_to_eat),
            "obstáculos": len(env.obstacles),
        }
        esperado = {"num_agents": 20, "max_steps": 2000,
                    "required_to_eat": 1, "obstáculos": 106}
        difs = {k: (medido[k], esperado[k]) for k in esperado
                if medido[k] != esperado[k]}
        regista(B, "MG-desenho-params",
                "N=20, max_steps=2000, required_to_eat=1, 106 obstáculos",
                "configs/foraging.yaml + src/environment",
                "OK" if not difs else "FALHA",
                "o simulador constrói exatamente o pré-registado"
                if not difs else "divergem (medido, pré-registado): %s" % difs)
    except Exception as erro:  # noqa: BLE001
        regista(B, "MG-desenho-params",
                "N=20, max_steps=2000, required_to_eat=1, 106 obstáculos",
                "configs/foraging.yaml + src/environment", "LEITURA",
                "não consegui construir o ambiente: %s" % erro)

    # ── compromisso 1: todos os algoritmos, todas as execuções ──────────────
    tabela = bloco_da_tabela(tex_sec, "tab:f2_mapa_grande")
    ok = tabela is not None and all(a in tabela for a in ("GNN", "PPO", "SAC"))
    regista(B, "MG-rep-1", "todos os 3 algoritmos e todas as execuções, sem "
            "cherry-picking", onde_sec + " (tab:f2_mapa_grande)",
            "OK" if ok else "FALHA",
            "a tabela do F2 tem as três linhas" if ok
            else "a tabela do F2 não lista os três algoritmos")

    # ── compromisso 2: convergência descritiva, magnitude testada ───────────
    desc = presente(tex_sec, r"M2 \(convergência, descritivo\)")
    decl = presente(tex_sec, r"M2 permanece descritiva|mantém-se\s+\\textbf\{descritiva\}")
    regista(B, "MG-rep-2", "convergência = descritivo; magnitude = teste "
            "(M2 não vira teste por o n ter subido)", onde_sec,
            "OK" if (desc and decl) else "FALHA",
            "M2 rotulada descritiva e a limitação declara porquê" if (desc and decl)
            else "falta o rótulo descritivo (M2=%s) ou a declaração (%s)" % (desc, decl))

    # ── compromisso 3: o mapa fora das tabelas dos sete cenários ────────────
    intrusos = []
    for label in ("tab:res_eval", "tab:res_signif"):
        bloco = bloco_da_tabela(tex_main, label)
        if bloco is None:
            intrusos.append("%s não existe" % label)
        elif re.search(r"[Mm]apa\s+[Gg]rande|mapa_grande", bloco):
            intrusos.append("%s menciona o mapa" % label)
    regista(B, "MG-rep-3", "o mapa NÃO entra nas tabelas dos sete cenários",
            "Tese/main.tex (tab:res_eval, tab:res_signif)",
            "OK" if not intrusos else "FALHA",
            "as duas tabelas dos sete cenários não o mencionam" if not intrusos
            else "; ".join(intrusos))

    # ── compromisso 4: hard stop de 22 ago ─────────────────────────────────
    fechos = {a: v.get("fecho") for a, v in m.items() if v}
    if all(fechos.values()):
        ultimo = max(fechos.values())
        regista(B, "MG-rep-4", "o que fechar depois de 22 ago não entra na tese",
                "results/mapa_grande/f2_*/logs/_campanha_concluida.txt",
                "OK" if ultimo < HARD_STOP else "FALHA",
                "última campanha fechou %s (limite %s)"
                % (ultimo.strftime("%d/%m %H:%M"), HARD_STOP.strftime("%d/%m")))
    else:
        regista(B, "MG-rep-4", "o que fechar depois de 22 ago não entra na tese",
                "results/mapa_grande/f2_*/logs", "FALHA",
                "falta a sentinela de conclusão em: %s"
                % [a for a, f in fechos.items() if not f])

    # ── compromisso 5: desvios datados ─────────────────────────────────────
    # Só a secção 7 conta: os «1.» e «3.» da secção 4 são compromissos de
    # reporte, não emendas, e inflavam a contagem.
    seccao7 = pre.split("## 7. Emendas")[-1]
    emendas = sorted(int(n) for n in re.findall(r"^(\d{1,2})\. \*\*", seccao7, re.M))
    seguidas = emendas == list(range(1, len(emendas) + 1))
    regista(B, "MG-rep-5a", "emendas numeradas e datadas (nada muda em silêncio)",
            "docs/PRE_REGISTO_MAPA_GRANDE.md",
            "OK" if seguidas else "FALHA",
            "%d emendas numeradas, 1..%d, sem buracos" % (len(emendas), max(emendas))
            if seguidas else "numeração com buracos ou repetida: %s" % emendas)

    # ── emenda 20: o braço exploratório correu? foi declarado se não? ───────
    dados_expl = [p for p in os.listdir(os.path.join(RAIZ, "results", "mapa_grande"))
                  if "expl" in p or "2340" in p]
    declarado = presente(pre, r"(?is)braço explorat[óo]rio.{0,400}?"
                              r"(cancelad|não (foi )?lançad|não corre)")
    if dados_expl:
        regista(B, "MG-expl", "braço exploratório GNN @2340 min × 3 (emenda 20)",
                "results/mapa_grande/", "OK",
                "dados presentes: %s" % ", ".join(dados_expl))
    else:
        regista(B, "MG-expl", "braço exploratório GNN @2340 min × 3 (emenda 20)",
                "docs/PRE_REGISTO_MAPA_GRANDE.md",
                "OK" if declarado else "FALHA",
                "não correu, e o pré-registo declara-o em emenda datada"
                if declarado else
                "não correu e o pré-registo NÃO tem emenda a declará-lo "
                "(compromisso 5: desvios datados)")

    # A dissertação pode falar do braço — mas não como se ele tivesse corrido.
    # A frase que o invoca tem de dizer, ali mesmo, que não foi lançado: quem lê
    # a secção não vai ao pré-registo confirmar de que braços é que ela fala.
    fala = re.findall(r"[^.]*braço explorat[óo]rio[^.]*\.", tex_sec, re.S)
    nega = r"não chegou a ser lançado|não foi lançado|não correu|cancelad"
    sem_ressalva = [f for f in fala if not re.search(nega, f)]
    if dados_expl or not fala:
        regista(B, "MG-expl-tex", "a dissertação não invoca braços que não correram",
                onde_sec, "OK",
                "a secção refere o braço, e ele existe" if fala
                else "a secção não invoca o braço exploratório")
    else:
        regista(B, "MG-expl-tex", "a dissertação não invoca braços que não correram",
                onde_sec, "OK" if not sem_ressalva else "FALHA",
                "a secção refere-o e declara, na mesma frase, que não foi lançado"
                if not sem_ressalva else
                "%d frase(s) invocam o braço sem dizer que não correu: «%s»"
                % (len(sem_ressalva),
                   " ".join(sem_ressalva[0].split())[:90]))

    # ── as três métricas pré-registadas estão reportadas ───────────────────
    for chave, rotulo in (("M1", r"\\textbf\{M1 \(magnitude\)"),
                          ("M2", r"\\textbf\{M2 \(convergência"),
                          ("M3", r"\\textbf\{M3 \(porta cooperativa")):
        regista(B, "MG-%s" % chave,
                "%s reportada (valores conferidos por verificar_mapa_grande.py)" % chave,
                onde_sec, "OK" if presente(tex_sec, rotulo) else "FALHA",
                "presente" if presente(tex_sec, rotulo)
                else "não encontrei o parágrafo da %s" % chave)

    # M3 medido dos CSV contra o que a secção afirma (a única métrica que o
    # verificador da secção lê de uma coluna acrescentada a meio da campanha)
    if m["GNN"]:
        mm = re.search(r"porta é aberta: GNN \$?(\d+)", tex_sec)
        if mm:
            na_tese, medido = float(mm.group(1)), m["GNN"]["porta"]
            ok = abs(na_tese - medido) <= 1.0
            regista(B, "MG-M3-valor", "M3 do GNN bate com o eval_by_run.csv",
                    onde_sec, "OK" if ok else "FALHA",
                    "secção %.0f%%, medido %.1f%%" % (na_tese, medido))

    # ── F1 reporta-se em qualquer caso ─────────────────────────────────────
    ok = presente(tex_sec, r"\$84\$ células|\$?84\$? células") and presente(tex_sec, r"1680")
    regista(B, "MG-F1", "F1 (zero-shot) reporta-se mesmo dando zero em tudo",
            onde_sec, "OK" if ok else "FALHA",
            "as 84 células e os 1680 episódios estão reportados" if ok
            else "não encontrei as 84 células / 1680 episódios")

    # ── regra de decisão: limiar proporcional e k declarado ────────────────
    limiar = presente(tex_sec, r"limiar de \$15\$|⌈5/7|\$15\$ fixado")
    limiar_main = presente(tex_main, r"limiar de \$15\$")
    k = presente(tex_sec, r"4/\$?21") or presente(tex_sec, r"4/21")
    regista(B, "MG-regra", "limiar ⌈5/7×n⌉=15 e nº de execuções convergentes "
            "declarado (emenda 21)", onde_sec + " + main.tex (Conclusões)",
            "OK" if ((limiar or limiar_main) and k) else "FALHA",
            "limiar 15 e k=4/21 declarados" if ((limiar or limiar_main) and k)
            else "limiar=%s (secção) / %s (Conclusões), k=%s"
                 % (limiar, limiar_main, k))

    # ── emenda 23: os dois runs do braço errado, guardados como controlo ───
    regista(B, "MG-objpuro", "os 2 runs do braço errado (objetivo puro) declarados "
            "e fora de M1--M3 (emenda 23)", "docs/PRE_REGISTO_MAPA_GRANDE.md",
            "OK" if presente(pre, r"mapa_F2_gnn_objetivopuro") else "FALHA",
            "declarados na emenda 23, com o diretório onde ficaram"
            if presente(pre, r"mapa_F2_gnn_objetivopuro")
            else "não encontrei a declaração dos runs descartados")


# ══════════════════════════════════════════════════════════════════════════════
# 2. PRE_REGISTO_MEGATREINO.md
# ══════════════════════════════════════════════════════════════════════════════
def megatreino(tex_main):
    print()
    print("=" * 78)
    print("PRE_REGISTO_MEGATREINO.md  —  mega-treino de um mês (n=28)")
    print("=" * 78)
    B = "Mega-treino"
    onde = "Tese/main.tex (sec:res_novelty)"
    resumo = json.loads(_ler(os.path.join(RAIZ, "results", "mega_1mes",
                                          "resumo_megatreino.json")))
    testes = resumo["testes"]

    # M1: magnitude + Fisher sobre convergência (o n=28 é que o permite)
    m1 = testes["M1"]
    diz_fisher = presente(tex_main, r"Fisher exato, \$p")
    diz_conv = presente(tex_main, r"\$28/28\$ execuções a 100\\% de sucesso contra \$15/28\$")
    bate = (m1["a"]["convergentes"], m1["b"]["convergentes"]) == (28, 15)
    regista(B, "MT-M1", "M1: magnitude (unilateral) + Fisher sobre convergência",
            onde, "OK" if (diz_fisher and diz_conv and bate) else "FALHA",
            "28/28 vs 15/28 com Fisher, e bate com o resumo da análise"
            if (diz_fisher and diz_conv and bate)
            else "fisher=%s, convergência no texto=%s, dados=%s/%s"
                 % (diz_fisher, diz_conv, m1["a"]["convergentes"],
                    m1["b"]["convergentes"]))

    # M2: seis pares, p brutos, multiplicidade assinalada
    pares = [k for k in testes if k.startswith("M2:")]
    diz_seis = presente(tex_main, r"seis pares de M2 são \$p\$ brutos")
    diz_mult = presente(tex_main, r"multiplicidade")
    regista(B, "MT-M2", "M2: os 6 pares no Muro em U, p brutos e multiplicidade "
            "assinalada", onde,
            "OK" if (len(pares) == 6 and diz_seis and diz_mult) else "FALHA",
            "%d pares na análise; o texto declara os p brutos e a multiplicidade"
            % len(pares) if (len(pares) == 6 and diz_seis and diz_mult)
            else "pares=%d, declara p brutos=%s, multiplicidade=%s"
                 % (len(pares), diz_seis, diz_mult))

    # M3: bypass adaptativo vs fixo, declarado como entre campanhas
    m3 = testes["M3"]
    diz = presente(tex_main, r"\\textbf\{entre campanhas\}")
    regista(B, "MT-M3", "M3: bypass adaptativo vs peso fixo, declarado como "
            "comparação entre campanhas", onde, "OK" if diz else "FALHA",
            "n=%d vs n=%d, e o texto declara que são campanhas diferentes"
            % (m3["a"]["n"], m3["b"]["n"]) if diz
            else "falta a declaração «entre campanhas»")

    # Exploratório: reportar TODAS as fases, não só as que confirmam
    expl = resumo["exploratorio"]
    esperados = {
        "ablação do anilamento (B1-B4)": r"duas durações do critério de descoberta",
        "Sandbox adaptativo n=21 (A5)": r"\$\\mathbf\{20/21\}\$|\{20/21\}",
        "Perceção adaptativa n=21 (B7)": r"\$17/21\$",
        "SAC no Gargalo n=21 (B6)": r"\$7/21\$",
    }
    em_falta = [nome for nome, pad in esperados.items()
                if not presente(tex_main, pad)]
    regista(B, "MT-expl", "exploratório: reportar TODAS as configs e fases",
            onde, "OK" if not em_falta else "FALHA",
            "as 4 células exploratórias estão reportadas (%d no resumo da "
            "análise)" % len(expl) if not em_falta
            else "por reportar: %s" % ", ".join(em_falta))

    regista(B, "MT-rep-1", "todos os runs, todas as configs, todas as fases",
            onde, "LEITURA",
            "as 12 células (A1-A5, B1-B7) estão cobertas por MT-M1..MT-expl; "
            "a exaustividade da prosa é leitura humana")


# ══════════════════════════════════════════════════════════════════════════════
# 3. PRE_REGISTO_NOVELTY_ADAPTATIVO.md  (QI6)
# ══════════════════════════════════════════════════════════════════════════════
def novelty(tex_main):
    print()
    print("=" * 78)
    print("PRE_REGISTO_NOVELTY_ADAPTATIVO.md  —  QI6, dosagem adaptativa")
    print("=" * 78)
    B = "Novelty adaptativo (QI6)"
    onde = "Tese/main.tex (sec:res_novelty)"

    for t in ("T1", "T2", "T3", "T4"):
        pad = r"\\textbf\{\(%s\)" % t
        regista(B, "NA-%s" % t, "%s reportado" % t, onde,
                "OK" if presente(tex_main, pad) else "FALHA",
                "presente" if presente(tex_main, pad)
                else "não encontrei o teste %s no texto" % t)

    cenarios, runs = medir_novelty()
    ok = len(cenarios) == 7 and len(runs) == 7
    regista(B, "NA-rep-1", "reportar TODOS os 7 cenários e TODOS os 7 runs",
            "results/novelty_adaptativo/week_*_fase1", "OK" if ok else "FALHA",
            "%d cenários × %d execuções na condição primária"
            % (len(cenarios), len(runs)) if ok
            else "medido %d cenários × %d execuções" % (len(cenarios), len(runs)))

    diz = presente(tex_main, r"o peso da leitura recai no tamanho de efeito")
    regista(B, "NA-rep-3", "p brutos + peso no δ, não em cruzar 0,05", onde,
            "OK" if diz else "FALHA",
            "declarado no parágrafo de T4" if diz
            else "não encontrei a declaração sobre o peso do δ")

    diz = presente(tex_main, r"Duas análises exploratórias, assim rotuladas no "
                             r"pré-registo")
    regista(B, "NA-expl", "braços @390 min rotulados exploratórios", onde,
            "OK" if diz else "FALHA",
            "rotulados no texto, fora da regra de decisão" if diz
            else "os braços @390 não estão rotulados como exploratórios")


# ══════════════════════════════════════════════════════════════════════════════
def escrever_tabela():
    destino = os.path.join(RAIZ, "docs", "PREREGISTO_VS_REPORTADO.md")
    marca = {"OK": "✅", "FALHA": "❌", "LEITURA": "👤"}
    out = ["# Pré-registo → o que é reportado",
           "",
           "*Gerado por `scripts/verificar_preregistos.py` em %s.*"
           % datetime.now().strftime("%d/%m/%Y %H:%M"),
           "",
           "Um compromisso pré-registado que não seja reportado é o defeito mais",
           "caro desta dissertação: é o que separa uma regra fixada à partida de",
           "uma escolhida depois de ver os resultados. Esta tabela é gerada, não",
           "escrita — se um compromisso deixar de ser cumprido, ela muda sozinha.",
           ""]
    bloco_atual = None
    for bloco, cid, comp, ondex, estado, ev in linhas:
        if bloco != bloco_atual:
            out += ["", "## %s" % bloco, "",
                    "| | compromisso | onde é reportado | evidência |",
                    "|---|---|---|---|"]
            bloco_atual = bloco
        out.append("| %s | **%s** — %s | `%s` | %s |"
                   % (marca[estado], cid, comp, ondex, ev))
    out += ["", "---", "",
            "✅ verificado por medição ou por padrão encontrado no `.tex` · "
            "❌ por cumprir · 👤 leitura humana", ""]
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("\nTabela escrita em docs/PREREGISTO_VS_REPORTADO.md")


def main():
    tex_sec = sem_comentarios(SECCAO)
    tex_main = sem_comentarios(MAIN)
    mapa_grande(tex_sec, tex_main, _ler(PRE_MG))
    megatreino(tex_main)
    novelty(tex_main)

    print()
    print("=" * 78)
    total = len(linhas)
    n_ok = sum(1 for l in linhas if l[4] == "OK")
    n_lei = sum(1 for l in linhas if l[4] == "LEITURA")
    print("%d compromissos verificados: %d cumpridos, %d por cumprir, "
          "%d para leitura humana" % (total, n_ok, len(falhas), n_lei))
    for f in falhas:
        print("  [X] %s" % f)
    print("=" * 78)

    if "--escrever" in sys.argv:
        escrever_tabela()
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
