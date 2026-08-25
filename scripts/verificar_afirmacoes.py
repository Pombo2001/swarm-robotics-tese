#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""As afirmações ABSOLUTAS da dissertação são verdadeiras?

    python scripts/verificar_afirmacoes.py

Porque existe
-------------
Os outros verificadores conferem **números**: onde o `.tex` escreve $67{,}4$, o
CSV tem de dizer 67,4. Esta régua confere as frases onde o número está na
palavra: «o único cenário que nenhum algoritmo resolve», «converge em todas as
execuções de seis cenários», «nenhuma das $28$ execuções passa de $45{,}4$».

São 40 afirmações destas no corpo da tese, e são as mais caras de errar: uma
média mal arredondada é um erro de transcrição, mas «o único» a mais é uma
afirmação sobre tudo o que não foi medido. Nenhum verificador olhava para elas
— o `verificar_numeros_tese.py` lê o `45{,}4` e não lê o «nenhuma».

Método: cada afirmação é reduzida à contagem que a torna verdadeira ou falsa,
essa contagem é feita sobre os CSV, e os valores citados são **lidos do
`.tex`** — nunca escritos aqui. Um número que mude no texto e não nos dados
falha; um número que mude nos dados e não no texto também.

⚠️ A régua não julga a redação: se a frase disser «o único» e a contagem der 1,
passa. O que ela não deixa passar é a frase sobreviver a uma mudança nos dados.
"""
import glob
import os
import re
import sys

import pandas as pd

# A consola do Windows abre em cp1252 e o `✓` desta régua rebentava-a — o guião
# saía com erro sem uma linha de resultado, e para o hook de pré-commit isso é
# indistinguível de uma verificação falhada. É o que os outros verificadores
# deste projeto fazem, e por esta razão.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(RAIZ, "Tese", "main.tex")
FINAL_7D = os.path.join(RAIZ, "results", "graficos_tese", "final_7d", "eval_by_run_7d.csv")
MEGA = os.path.join(RAIZ, "results", "mega_1mes", "*", "evaluation", "eval_by_run.csv")
HORIZONTE = os.path.join(RAIZ, "results", "mapa_grande", "horizonte_gnn.csv")
LOGS_F2 = os.path.join(RAIZ, "results", "mapa_grande", "f2_gnn", "logs",
                       "gnn_3d_training_mapa_grande_run*.csv")
ESCALA = os.path.join(RAIZ, "results", "estatisticas", "escalabilidade_%s.csv")
EVAL = os.path.join(RAIZ, "results", "evaluation")

falhas = []


def corpo():
    """O texto da dissertação como ele é impresso: os `\\input` incluídos e as
    linhas comentadas fora.

    As duas metades desta função são achados. O `%` do LaTeX esconde parágrafos
    inteiros — a QI7 viveu meses em comentário. E a secção do mapa composto (a
    QI7 inteira, com todos os números da última campanha) **não está no
    `main.tex`**: entra por `\\input{seccao_mapa_grande}`. Uma régua que abra só
    o `main.tex` não vê o oitavo cenário e diz que está tudo bem.
    """
    def ler(caminho):
        linhas = open(caminho, encoding="utf-8").read().split("\n")
        return [l for l in linhas if not l.lstrip().startswith("%")]

    saida = []
    for linha in ler(TEX):
        m = re.search(r"\\input\{([^}]+)\}", linha)
        alvo = os.path.join(os.path.dirname(TEX), (m.group(1) if m else "") + ".tex")
        if m and os.path.exists(alvo):
            saida.extend(ler(alvo))
        else:
            saida.append(linha)
    return "\n".join(saida)


def do_tex(padrao, nome, grupos=1):
    """Lê do `.tex` os números de uma frase. Se a frase desaparecer, é achado:
    uma régua que não encontra o que verifica tem de o dizer, não calar-se."""
    m = re.search(padrao, corpo(), re.S)
    if not m:
        falhas.append("a frase de «%s» não está no main.tex — mudou a redação "
                      "ou o padrão desta régua envelheceu" % nome)
        return None
    return tuple(m.group(i + 1) for i in range(grupos))


def num(s):
    return float(str(s).replace("{,}", ".").replace(",", "."))


def confere(nome, esperado, obtido, tol=0.06):
    ok = abs(num(esperado) - float(obtido)) <= tol
    print("  [%s] %-52s tese %-8s dados %s"
          % ("v" if ok else "!", nome, esperado, round(float(obtido), 3)))
    if not ok:
        falhas.append("%s: a tese diz %s, os dados dizem %s"
                      % (nome, esperado, round(float(obtido), 3)))
    return ok


def cabecalho(t):
    print("\n" + "=" * 78 + "\n%s\n" % t + "=" * 78)


# ---------------------------------------------------------------- campanha final
def campanha_final():
    cabecalho("Campanha final (7 cenários × 3 algoritmos × 7 execuções)")
    d = pd.read_csv(FINAL_7D)

    v = do_tex(r"\\textbf\{(\d+) das (\d+) combinações algoritmo--cenário atingem "
               r"100\\% de sucesso em todas as execuções", "células plenas", 2)
    if v:
        cel = d.groupby(["Scenario", "Algorithm"]).success.mean()
        confere("células a 100%% em todos os episódios", v[0], (cel == 1.0).sum(), 0)
        confere("total de células", v[1], len(cel), 0)

    v = do_tex(r"não o aprende de todo \(GNN (\d)/7 execuções, PPO (\d)/7, SAC (\d)/7\)",
               "Muro em U por algoritmo", 3)
    if v:
        u = d[d.Scenario == "u_wall"]
        conv = u.groupby(["Algorithm", "Run"]).success.mean().groupby("Algorithm")
        conv = conv.apply(lambda s: int((s == 1).sum()))
        for i, algo in enumerate(("GNN", "PPO", "SAC")):
            confere("Muro em U, execuções a 100%% (%s)" % algo, v[i], conv[algo], 0)

    # «o único cenário que nenhum algoritmo resolve de forma fiável»
    if re.search(r"\\textbf\{Muro em U\} é o único cenário que nenhum algoritmo "
                 r"resolve de forma fiável", corpo()):
        plenos = d.groupby(["Scenario", "Algorithm"]).success.mean()
        por_cen = plenos.groupby("Scenario").apply(lambda s: (s == 1.0).sum())
        sem_ninguem = sorted(por_cen[por_cen == 0].index)
        ok = sem_ninguem == ["u_wall"]
        print("  [%s] %-52s %s" % ("v" if ok else "!",
                                   "cenários que NENHUM algoritmo resolve", sem_ninguem))
        if not ok:
            falhas.append("«o único cenário que nenhum algoritmo resolve» — sem "
                          "algoritmo pleno: %s" % sem_ninguem)

    # «o PPO converge em todas as execuções de seis cenários»
    v = do_tex(r"generalista fiável\}: converge em todas as execuções de "
               r"(\w+) cenários", "PPO generalista")
    if v:
        palavras = {"quatro": 4, "cinco": 5, "seis": 6, "sete": 7}
        esperado = palavras.get(v[0].lower())
        s = d[d.Algorithm == "PPO"].groupby(["Scenario", "Run"]).success.mean()
        plenos = s.groupby("Scenario").apply(lambda x: int((x == 1).sum()) == len(x))
        confere("PPO: cenários com todas as execuções a 100%%", esperado, plenos.sum(), 0)

    # «o SAC é o único que falha execuções no Gargalo»
    if re.search(r"é o único que falha execuções no Gargalo", corpo()):
        g = d[d.Scenario == "bottleneck"].groupby(["Algorithm", "Run"]).success.mean()
        falham = sorted(a for a in ("GNN", "PPO", "SAC") if (g.loc[a] < 1).any())
        ok = falham == ["SAC"]
        print("  [%s] %-52s %s" % ("v" if ok else "!",
                                   "algoritmos com execuções falhadas no Gargalo", falham))
        if not ok:
            falhas.append("«o SAC é o único que falha no Gargalo» — falham: %s" % falham)


# ------------------------------------------------------------------ mega-treino
def mega_treino():
    cabecalho("Mega-treino no Muro em U (n = 28 por braço)")
    fs = glob.glob(MEGA)
    d = pd.concat([pd.read_csv(f).assign(fonte=f) for f in fs], ignore_index=True)
    u = d[d.Scenario == "u_wall"]

    v = do_tex(r"o PPO com \$(\d+)\$ das \$(\d+)\$ acima de \$(\d+)\$ recolhas/ep",
               "PPO acima do limiar", 3)
    if v:
        s = u[u.Algorithm == "PPO"].groupby(["fonte", "Run"]).food_collected.mean()
        confere("PPO: execuções acima de %s rec/ep" % v[2], v[0], (s > num(v[2])).sum(), 0)
        confere("PPO: execuções no braço", v[1], len(s), 0)

    v = do_tex(r"nenhuma das suas \$(\d+)\$ execuções passa de \$([\d{},]+)\$ recolhas/ep",
               "tecto do SAC", 2)
    if v:
        s = u[u.Algorithm == "SAC"].groupby(["fonte", "Run"]).food_collected.mean()
        confere("SAC: execuções no braço", v[0], len(s), 0)
        confere("SAC: máximo por execução", v[1], s.max(), 0.05)
        if s.max() > num(v[1]) + 0.05:
            falhas.append("«nenhuma passa de %s» — há uma com %.1f" % (v[1], s.max()))


# --------------------------------------------------------------- escalabilidade
def escalabilidade():
    cabecalho("Escalabilidade Zero-Shot (N = 10 a 100, sem retreino)")
    chaves = {"none": "Sandbox", "cooperative_perception": "Perceção Cooperativa",
              "bottleneck": "Gargalo", "four_rooms": "Quatro Salas",
              "u_wall": "Muro em U", "cooperative_door": "Porta Cooperativa",
              "cooperative_door_bypass": "Porta com Alternativa"}
    tudo_100 = True
    for chave, rotulo in chaves.items():
        d = pd.read_csv(ESCALA % chave)
        g = d[d.Algorithm == "GNN"].set_index("N")
        # A linha da tabela: rótulo & 4 valores por agente & retenção.
        v = do_tex(r"%s & \$([\d{},]+)\$ & \$([\d{},]+)\$ & \$([\d{},]+)\$ & "
                   r"\$([\d{},]+)\$ & \$(\d+)\\%%\$" % re.escape(rotulo), rotulo, 5)
        if not v:
            continue
        for i, n in enumerate((10, 20, 50, 100)):
            confere("%s: rec/agente em N=%d" % (rotulo, n), v[i],
                    g.loc[n, "food_per_agent"], 0.006)
        confere("%s: retenção N=100 face a N=20" % rotulo, v[4],
                100 * g.loc[100, "food_per_agent"] / g.loc[20, "food_per_agent"], 0.5)
        if (g.success_rate.dropna() < 1).any():
            tudo_100 = False

    if re.search(r"Taxa de sucesso: \$100\\%\$ em todas as células", corpo()):
        print("  [%s] %-52s %s" % ("v" if tudo_100 else "!",
                                   "sucesso a 100% em todas as células da tabela",
                                   "sim" if tudo_100 else "NÃO"))
        if not tudo_100:
            falhas.append("«100% em todas as células» da escalabilidade não se verifica")

    v = do_tex(r"sobrepostos porque distam \$([\d{},]+)\$ recolhas por agente", "PPO vs SAC")
    if v:
        d = pd.read_csv(ESCALA % "none").set_index(["Algorithm", "N"])
        dist = abs(d.loc[("PPO", 20), "food_per_agent"] - d.loc[("SAC", 20), "food_per_agent"])
        confere("Sandbox: distância PPO–SAC por agente em N=20", v[0], dist, 0.006)


# --------------------------------------------------------------------- robustez
def robustez():
    cabecalho("Robustez à perda súbita de 10% dos agentes")
    v = do_tex(r"retenção de recolhas situa-se entre \\textbf\{(\d+)\\% e (\d+)\\%\} "
               r"em todas as (\d+) combinações", "faixa de retenção", 3)
    if not v:
        return
    rets = []
    for f in sorted(glob.glob(os.path.join(EVAL, "*_fail10.csv"))):
        base = f[:-len("_fail10.csv")] + ".csv"
        if not os.path.exists(base):
            continue
        a = pd.read_csv(base).food_collected.mean()
        if a > 0:
            rets.append(100 * pd.read_csv(f).food_collected.mean() / a)
    confere("células com desempenho de base", v[2], len(rets), 0)
    confere("retenção mínima", v[0], min(rets), 0.5)
    confere("retenção máxima", v[1], max(rets), 0.5)


# ------------------------------------------------------- diagnóstico da QI7
def diagnostico_qi7():
    cabecalho("Diagnóstico da QI7 (orçamento, horizonte e aproximação)")
    logs = sorted(glob.glob(LOGS_F2))
    v = do_tex(r"Em \$(\d+)\$ das \$(\d+)\$ execuções o melhor \\textit\{fitness\} surge "
               r"nos últimos \$(\d+)\\%\$ das gerações, com a geração do máximo a cair, "
               r"em mediana, a \$(\d+)\\%\$", "orçamento por esgotar", 4)
    if v and logs:
        fracs = []
        for f in logs:
            c = pd.read_csv(f)
            fracs.append((c.best_fitness.idxmax() + 1) / len(c))
        cauda = 1 - num(v[2]) / 100
        confere("execuções com o máximo na cauda do treino", v[0],
                sum(1 for x in fracs if x > cauda), 0)
        confere("execuções com log de treino", v[1], len(logs), 0)
        confere("mediana da geração do máximo (%% do orçamento)", v[3],
                100 * pd.Series(fracs).median(), 0.5)

    v = do_tex(r"traduziu-se em \$([\d{},]+)\$ gerações por execução em média "
               r"\(amplitude de \$(\d+)\$ a \$(\d+)\$", "gerações por execução", 3)
    if v and logs:
        tamanhos = [len(pd.read_csv(f)) for f in logs]
        confere("gerações por execução (média)", v[0], sum(tamanhos) / len(tamanhos), 0.05)
        confere("gerações por execução (mínimo)", v[1], min(tamanhos), 0)
        confere("gerações por execução (máximo)", v[2], max(tamanhos), 0)

    v = do_tex(r"de \$(\d+)\$ para \$(\d+)\$ \\emph\{sem qualquer retreino\} faz a "
               r"distância mínima mediana ao ninho cair de \$([\d{},]+)\$ para "
               r"\$([\d{},]+)\$\\,m e quase duplica a magnitude da melhor execução "
               r"\(de \$(\d+)\$ para \$(\d+)\$ recolhas por episódio\), mas leva o número "
               r"de execuções com pelo menos uma recolha apenas de \$(\d+)\$ para \$(\d+)\$ "
               r"em \$(\d+)\$", "horizonte do episódio", 9)
    if v:
        h = pd.read_csv(HORIZONTE)
        for i, passos in ((0, num(v[0])), (1, num(v[1]))):
            if passos not in set(h.horizonte):
                falhas.append("o horizonte de %d passos não está no CSV" % passos)
        curto, longo = h[h.horizonte == num(v[0])], h[h.horizonte == num(v[1])]
        confere("distância mediana ao ninho (%s passos)" % v[0], v[2],
                curto.groupby("Run").d_min.min().median(), 0.05)
        confere("distância mediana ao ninho (%s passos)" % v[1], v[3],
                longo.groupby("Run").d_min.min().median(), 0.05)
        confere("melhor episódio (%s passos)" % v[0], v[4], curto.recolhas.max(), 0)
        confere("melhor episódio (%s passos)" % v[1], v[5], longo.recolhas.max(), 0)
        confere("execuções com recolha (%s passos)" % v[0], v[6],
                (curto.groupby("Run").recolhas.sum() > 0).sum(), 0)
        confere("execuções com recolha (%s passos)" % v[1], v[7],
                (longo.groupby("Run").recolhas.sum() > 0).sum(), 0)
        confere("execuções ao todo", v[8], h.Run.nunique(), 0)

    # A frase dizia «param a 5--13 m» e havia três execuções a parar a 2,3, 4,1
    # e 4,9 m — as que mais sustentam o argumento (o problema é a aproximação
    # final, não o orçamento) ficavam de fora do intervalo citado. Passa a
    # contar-se quantas param abaixo de cada limiar, que é o que se afirma.
    v = do_tex(r"há \$(\d+)\$ execuções que param a menos de \$(\d+)\$\\,m do ninho "
               r"--- \$(\d+)\$ delas a menos de \$(\d+)\$\\,m --- e não entram nele "
               r"mesmo com o dobro do tempo", "as que param à porta", 4)
    if v:
        h = pd.read_csv(HORIZONTE)
        longo = h[h.horizonte == h.horizonte.max()]
        por_run = longo.groupby("Run").agg(dmin=("d_min", "min"), rec=("recolhas", "sum"))
        paradas = por_run[por_run.rec == 0].dmin.sort_values()
        confere("execuções que param a menos de %s m sem entrar" % v[1], v[0],
                (paradas < num(v[1])).sum(), 0)
        confere("dessas, as que param a menos de %s m" % v[3], v[2],
                (paradas < num(v[3])).sum(), 0)
        print("      distâncias: %s"
              % ", ".join("%.1f" % x for x in paradas[paradas < num(v[1])]))


def main():
    campanha_final()
    mega_treino()
    escalabilidade()
    robustez()
    diagnostico_qi7()
    print("\n" + "=" * 78)
    if falhas:
        print("%d afirmação(ões) que os dados não sustentam:" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        print("=" * 78)
        sys.exit(1)
    print("As afirmações absolutas da dissertação batem com os dados ✓")
    print("=" * 78)


if __name__ == "__main__":
    main()
