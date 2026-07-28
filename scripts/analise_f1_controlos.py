"""
analise_f1_controlos.py — F1 do mapa grande: as 4 condições, lidas em conjunto
==============================================================================
Junta a condição **natural** (corrida na torre a 27 jul) com as três condições de
**controlo** (corridas no servidor a 28 jul, uma por diretório) e aplica a leitura
que o `docs/PRE_REGISTO_MAPA_GRANDE.md` §3 fixou **antes** de haver dados:

  · se um controlo der **o mesmo** que a natural, essa causa está excluída e
    reporta-se só a natural (o controlo vai para apêndice);
  · se **divergir**, o zero-shot de topologia está confundido com essa causa e é
    isso que se reporta.

E, textualmente: *"um controlo que ressuscite os campeões NÃO salva a leitura 'a
topologia é dura': desmente-a."* Por isso o veredicto que este script imprime
nunca escolhe a condição com o número melhor — reporta o que diverge.

O teste é **emparelhado por célula** (as 21 combinações origem × algoritmo), com
Wilcoxon dos postos com sinal e δ de Cliff, sobre as médias de recolhas/ep. É o
emparelhamento que os dados permitem: as seeds são as mesmas em todas as
condições (`--seed-base 1000`), logo cada célula tem o seu par em cada condição.

Uso:
    python scripts/analise_f1_controlos.py                       # lê o que houver
    python scripts/analise_f1_controlos.py --csv a.csv b.csv     # ficheiros à mão
    python scripts/analise_f1_controlos.py --sem-figura

Saídas (em results/mapa_grande/f1_zeroshot/):
    f1_grelha_por_condicao.csv   — a grelha 7×3 de cada condição, para a tese
    f1_veredicto.txt             — o que este script imprimiu, datado
    f1_condicoes.png             — 4 painéis, um por condição
"""
import argparse
import glob
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import THESIS_SCENARIOS, SCENARIO_LABELS_SHORT  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

DEST = os.path.join(PROJECT_ROOT, "results", "mapa_grande", "f1_zeroshot")
ALGOS = ("GNN", "PPO", "SAC")

# (NormObs, Controlo) -> nome legível. A ordem é a do pré-registo.
CONDICOES = [
    (("mapa", "base"), "natural"),
    (("treino", "base"), "escala"),
    (("mapa", "sem_obstaculos"), "sem obstáculos"),
    (("mapa", "sem_porta_obs"), "sem features da porta"),
]
NATURAL = ("mapa", "base")

# Um zero-shot com 20 episódios por célula: abaixo disto a célula está incompleta
# e entra no relatório como buraco, não como zero.
EP_POR_CELULA = 20


def carregar(caminhos):
    """Concatena os CSV e remove duplicados (a mesma célula em dois ficheiros)."""
    if not caminhos:
        caminhos = sorted(glob.glob(os.path.join(DEST, "*.csv")))
        caminhos = [c for c in caminhos
                    if os.path.basename(c).startswith("zeroshot_")]
    if not caminhos:
        raise SystemExit(
            "[X] Não encontrei CSV nenhum em %s.\n"
            "    Traz os dos controlos do servidor primeiro (ver o LEIA-ME)."
            % os.path.relpath(DEST, PROJECT_ROOT))

    partes = []
    for c in caminhos:
        d = pd.read_csv(c)
        d["_ficheiro"] = os.path.basename(c)
        partes.append(d)
        print("[i] %-46s %5d episódios" % (os.path.basename(c), len(d)))
    todo = pd.concat(partes, ignore_index=True)

    # A mesma condição pode vir em dois ficheiros (retoma). O par
    # (condição, célula, seed) identifica um episódio univocamente.
    chave = ["NormObs", "Controlo", "Algorithm", "Origem"]
    antes = len(todo)
    if "episode" in todo.columns:
        todo = todo.drop_duplicates(chave + ["episode"])
    else:
        todo = todo.drop_duplicates()
    if len(todo) != antes:
        print("[i] %d episódios duplicados removidos" % (antes - len(todo)))
    return todo


def verificar(d):
    """Integridade antes de qualquer leitura. Devolve a lista de avisos."""
    avisos = []

    # 1. A impressão digital do ambiente tem de ser ÚNICA por condição — se a
    #    mesma condição aparece com dois hashes, há dados de dois mapas no mesmo
    #    ficheiro e a comparação entre origens deixa de ser emparelhada.
    for (n, c), g in d.groupby(["NormObs", "Controlo"]):
        hashes = sorted(g["env_hash"].dropna().unique())
        if len(hashes) > 1:
            avisos.append("condição (%s, %s) tem %d impressões digitais "
                          "diferentes: %s — são dois mapas, não um."
                          % (n, c, len(hashes), ", ".join(hashes)))

    # 2. A natural e a 'escala' têm de partilhar a digital (a escala muda a
    #    LEITURA do mundo, não o mundo); 'sem_obstaculos' tem de diferir.
    dig = {k: g["env_hash"].dropna().iloc[0]
           for k, g in d.groupby(["NormObs", "Controlo"]) if len(g)}
    if NATURAL in dig:
        base = dig[NATURAL]
        if ("treino", "base") in dig and dig[("treino", "base")] != base:
            avisos.append("a condição 'escala' devia ter a MESMA digital da "
                          "natural (só muda o normalizador da observação) e tem "
                          "%s vs %s." % (dig[("treino", "base")], base))
        alvo = ("mapa", "sem_obstaculos")
        if alvo in dig and dig[alvo] == base:
            avisos.append("a condição 'sem obstáculos' tem a MESMA digital da "
                          "natural (%s) — os obstáculos não foram removidos." % base)
        alvo = ("mapa", "sem_porta_obs")
        if alvo in dig and dig[alvo] != base:
            avisos.append("a condição 'sem features da porta' devia ter a mesma "
                          "digital da natural (só zera 4 entradas da observação) "
                          "e tem %s vs %s." % (dig[alvo], base))

    # 3. Campeões da campanha certa (2-9 jul 2026), como a guarda do eval exige.
    if "ModeloData" in d.columns:
        datas = pd.to_datetime(d["ModeloData"], errors="coerce")
        fora = d[(datas < "2026-07-02") | (datas > "2026-07-10")]
        if len(fora):
            quais = sorted(fora["ModeloPath"].dropna().unique())[:3]
            avisos.append("%d episódios com campeões FORA da campanha de 7 dias "
                          "(%s ...) — foi isto que anulou o F1 de 25 jul."
                          % (len(fora), ", ".join(quais)))

    # 4. Células incompletas
    for (n, c), g in d.groupby(["NormObs", "Controlo"]):
        cont = g.groupby(["Algorithm", "Origem"]).size()
        curtas = cont[cont < EP_POR_CELULA]
        if len(curtas):
            avisos.append("condição (%s, %s): %d célula(s) com menos de %d "
                          "episódios — %s" % (n, c, len(curtas), EP_POR_CELULA,
                                              ", ".join("%s×%s=%d" % (a, o, v)
                                                        for (a, o), v in
                                                        curtas.items())))
    return avisos


def grelha(d, cond):
    """DataFrame origens × algoritmos com 'média (sucesso%)' de uma condição."""
    (n, c) = cond
    g = d[(d["NormObs"] == n) & (d["Controlo"] == c)]
    linhas = []
    for origem in THESIS_SCENARIOS:
        linha = {"Origem": SCENARIO_LABELS_SHORT.get(origem, origem)}
        for a in ALGOS:
            cel = g[(g["Algorithm"] == a) & (g["Origem"] == origem)]
            if len(cel) == 0:
                linha[a] = np.nan
                linha[a + "_sucesso"] = np.nan
            else:
                linha[a] = cel["food_collected"].mean()
                linha[a + "_sucesso"] = 100 * cel["success"].mean()
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("Origem")


def medias_por_celula(d, cond):
    """{(algo, origem): média de recolhas/ep} — a unidade do teste emparelhado."""
    (n, c) = cond
    g = d[(d["NormObs"] == n) & (d["Controlo"] == c)]
    return g.groupby(["Algorithm", "Origem"])["food_collected"].mean().to_dict()


def cliff_delta(a, b):
    """δ de Cliff: P(a>b) − P(a<b). Sem dependências além do numpy."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    maior = sum((x > b).sum() for x in a)
    menor = sum((x < b).sum() for x in a)
    return (maior - menor) / (len(a) * len(b))


def comparar(d, cond, nome):
    """Compara uma condição de controlo com a natural, emparelhado por célula."""
    nat = medias_por_celula(d, NATURAL)
    ctl = medias_por_celula(d, cond)
    comuns = sorted(set(nat) & set(ctl))
    if not comuns:
        return None

    x = np.array([nat[k] for k in comuns])
    y = np.array([ctl[k] for k in comuns])
    dif = y - x

    p = np.nan
    if np.any(dif != 0):
        try:
            from scipy.stats import wilcoxon
            p = wilcoxon(x, y, zero_method="wilcox").pvalue
        except Exception:
            p = np.nan

    return {
        "nome": nome,
        "n_celulas": len(comuns),
        "media_natural": x.mean(),
        "media_controlo": y.mean(),
        "p": p,
        "delta": cliff_delta(y, x),
        # O que interessa mesmo à QI7: células mortas que voltam à vida
        "ressuscitadas": int(np.sum((x == 0) & (y > 0))),
        "mortas": int(np.sum((x > 0) & (y == 0))),
        "zeros_natural": int(np.sum(x == 0)),
        "ambos_zero": int(np.sum((x == 0) & (y == 0))),
        "detalhe": [(k, nat[k], ctl[k]) for k in comuns
                    if (nat[k] == 0) != (ctl[k] == 0)],
    }


def veredicto(r):
    """A leitura pré-comprometida no pré-registo §3. Não escolhe o número melhor."""
    if r is None:
        return "sem dados para comparar."
    if r["ressuscitadas"] > 0:
        return ("DIVERGE — %d célula(s) a zero na condição natural passam a "
                "recolher. O zero-shot de topologia está CONFUNDIDO com esta "
                "causa, e é isto que se reporta: o controlo não salva a leitura "
                "'a topologia é dura', desmente-a." % r["ressuscitadas"])
    if not np.isnan(r["p"]) and r["p"] < 0.05:
        return ("DIVERGE em magnitude (p=%.4f, δ=%+.2f) sem ressuscitar células. "
                "A causa afeta o quanto se recolhe, não o se recolhe — reportar "
                "as duas condições." % (r["p"], r["delta"]))
    return ("MESMO resultado (p=%s, δ=%+.2f, 0 células ressuscitadas) ⇒ causa "
            "EXCLUÍDA. Reporta-se só a condição natural; esta vai para apêndice."
            % ("n/d" if np.isnan(r["p"]) else "%.3f" % r["p"], r["delta"]))


def figura(d, presentes, caminho):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.pyplot as plt

    n = len(presentes)
    fig, eixos = plt.subplots(1, n, figsize=(4.1 * n, 5.4), sharey=True)
    if n == 1:
        eixos = [eixos]

    # Escala comum: os painéis só são comparáveis se partilharem o máximo.
    vmax = max(1.0, max(np.nanmax(grelha(d, c)[list(ALGOS)].values)
                        for c, _ in presentes))

    for ax, (cond, nome) in zip(eixos, presentes):
        g = grelha(d, cond)[list(ALGOS)]
        im = ax.imshow(g.values, cmap="YlGnBu", vmin=0, vmax=vmax, aspect="auto")
        ax.set_xticks(range(len(ALGOS)), ALGOS)
        ax.set_yticks(range(len(g.index)), g.index, fontsize=9)
        ax.set_title(nome, fontsize=12, fontweight="bold", pad=10)
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                v = g.values[i, j]
                if np.isnan(v):
                    ax.text(j, i, "—", ha="center", va="center", color="#94A3B8")
                else:
                    ax.text(j, i, ("%.1f" % v) if v else "0",
                            ha="center", va="center", fontsize=9,
                            color="white" if v > 0.6 * vmax else "#0F172A")
        ax.set_xlabel("algoritmo do campeão")

    eixos[0].set_ylabel("cenário onde o campeão foi treinado")
    fig.colorbar(im, ax=eixos, shrink=0.75, label="recolhas/ep no mapa grande")
    fig.suptitle("F1 — zero-shot de topologia no mapa grande, por condição",
                 fontsize=14, fontweight="bold")
    fig.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", nargs="*", default=None,
                    help="CSV a juntar (por omissão: todos os zeroshot_*.csv "
                         "de results/mapa_grande/f1_zeroshot/)")
    ap.add_argument("--sem-figura", action="store_true")
    ap.add_argument("--saida", default=None,
                    help="onde escrever a grelha, o veredicto e a figura. "
                         "Obrigatório se algum CSV vier de fora da pasta "
                         "canónica — ver a guarda abaixo")
    a = ap.parse_args()

    # GUARDA: correr isto com um CSV de teste escrevia um veredicto FALSO por
    # cima do real, na pasta que a tese cita. Aconteceu a 28 jul, ao validar o
    # próprio script com dados sintéticos. Um ficheiro de fora da pasta canónica
    # obriga a dizer para onde vai a saída.
    dest = os.path.abspath(a.saida) if a.saida else DEST
    if a.csv:
        de_fora = [c for c in a.csv
                   if os.path.dirname(os.path.abspath(c)) != DEST]
        if de_fora and not a.saida:
            raise SystemExit(
                "[X] %d CSV vêm de fora de %s:\n    %s\n"
                "    Passa --saida <pasta> para não escrever por cima dos\n"
                "    resultados reais. (Se são mesmo os bons, move-os para lá\n"
                "    primeiro.)"
                % (len(de_fora), os.path.relpath(DEST, PROJECT_ROOT),
                   "\n    ".join(de_fora)))

    d = carregar(a.csv)
    linhas = []

    def diz(s=""):
        print(s)
        linhas.append(s)

    diz("=" * 74)
    diz("F1 — ZERO-SHOT DE TOPOLOGIA: as 4 condições  (%s)"
        % datetime.now().strftime("%Y-%m-%d %H:%M"))
    diz("=" * 74)

    avisos = verificar(d)
    if avisos:
        diz()
        diz("⚠️  INTEGRIDADE — ler isto ANTES dos números:")
        for x in avisos:
            diz("    · " + x)

    presentes = [(c, n) for c, n in CONDICOES
                 if len(d[(d["NormObs"] == c[0]) & (d["Controlo"] == c[1])])]
    faltam = [n for c, n in CONDICOES if (c, n) not in presentes]

    diz()
    diz("CONDIÇÕES PRESENTES: " + ", ".join(n for _, n in presentes))
    if faltam:
        diz("CONDIÇÕES EM FALTA:  " + ", ".join(faltam))
        diz("⚠️  Sem as quatro, o F1 NÃO responde à QI7 — o pré-registo é")
        diz("    explícito nisto. O que segue é parcial.")

    for cond, nome in presentes:
        g = d[(d["NormObs"] == cond[0]) & (d["Controlo"] == cond[1])]
        diz()
        diz("-" * 74)
        diz("%s  (%d episódios, %d células)"
            % (nome.upper(), len(g), g.groupby(["Algorithm", "Origem"]).ngroups))
        diz("-" * 74)
        tab = grelha(d, cond)
        diz("%-26s %14s %14s %14s" % ("campeão treinado em", *ALGOS))
        for origem, linha in tab.iterrows():
            campos = []
            for al in ALGOS:
                v, s = linha[al], linha[al + "_sucesso"]
                campos.append("—" if np.isnan(v) else "%5.1f (%3.0f%%)" % (v, s))
            diz("%-26s %14s %14s %14s" % (origem, *campos))
        med = [tab[al].mean() for al in ALGOS]
        diz("%-26s %14s %14s %14s"
            % ("MÉDIA", *["%5.2f" % m for m in med]))
        diz("%-26s %14d %14d %14d"
            % ("células a zero", *[int((tab[al] == 0).sum()) for al in ALGOS]))

    # Comparação com a natural
    if NATURAL in [c for c, _ in presentes]:
        diz()
        diz("=" * 74)
        diz("LEITURA PRÉ-COMPROMETIDA (pré-registo §3) — controlo vs natural")
        diz("=" * 74)
        for cond, nome in presentes:
            if cond == NATURAL:
                continue
            r = comparar(d, cond, nome)
            diz()
            diz("%s:" % nome.upper())
            if r:
                diz("   natural %.2f  →  controlo %.2f recolhas/ep "
                    "(%d células emparelhadas)"
                    % (r["media_natural"], r["media_controlo"], r["n_celulas"]))
                diz("   Wilcoxon p=%s | δ de Cliff %+.2f | %d ressuscitadas | "
                    "%d mortas"
                    % ("n/d" if np.isnan(r["p"]) else "%.4f" % r["p"],
                       r["delta"], r["ressuscitadas"], r["mortas"]))
                # Com a maioria das células a zero nas DUAS condições, o δ é
                # dominado por empates e encolhe: um δ pequeno ao lado de um p
                # pequeno não é contradição, é isto. Dizê-lo aqui evita que a
                # tabela seja lida como "efeito desprezável".
                if r["ambos_zero"] >= 0.5 * r["n_celulas"]:
                    diz("   (%d das %d células estão a zero nas DUAS condições: "
                        "o δ fica limitado por empates e lê-se com o nº de "
                        "ressuscitadas, não sozinho)"
                        % (r["ambos_zero"], r["n_celulas"]))
                for (al, orig), vn, vc in r["detalhe"][:6]:
                    diz("      %-4s × %-24s %5.1f → %5.1f"
                        % (al, SCENARIO_LABELS_SHORT.get(orig, orig), vn, vc))
            diz("   ⇒ " + veredicto(r))
    else:
        diz()
        diz("⚠️  Sem a condição NATURAL não há com que comparar os controlos.")

    os.makedirs(dest, exist_ok=True)
    tabelas = []
    for cond, nome in presentes:
        t = grelha(d, cond).reset_index()
        t.insert(0, "Condicao", nome)
        tabelas.append(t)
    if tabelas:
        fp = os.path.join(dest, "f1_grelha_por_condicao.csv")
        pd.concat(tabelas, ignore_index=True).to_csv(fp, index=False)
        diz()
        diz("[OK] grelhas -> %s" % os.path.relpath(fp, PROJECT_ROOT))

    fp = os.path.join(dest, "f1_veredicto.txt")
    with open(fp, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print("[OK] veredicto -> %s" % os.path.relpath(fp, PROJECT_ROOT))

    if not a.sem_figura and presentes:
        try:
            fp = os.path.join(dest, "f1_condicoes.png")
            figura(d, presentes, fp)
            print("[OK] figura -> %s" % os.path.relpath(fp, PROJECT_ROOT))
        except Exception as e:
            print("[!] figura não gerada: %s" % e)


if __name__ == "__main__":
    main()
