# -*- coding: utf-8 -*-
"""Projeção: o limiar de 15/21 execuções convergentes ainda é alcançável?

O que isto é, e sobretudo o que NÃO é
Não altera nada do pré-registo. A regra de decisão da QI7 continua a ser a
fixada antes dos dados (⌈5/7 × n⌉ = 15 de 21 execuções convergentes em pelo
menos um algoritmo, emendas 19 e 21). Isto responde a outra pergunta, de gestão:
*com o que já fechou, quanto falta para a resposta estar selada, e em que data?*
Saber isso a 6 de agosto vale mais do que descobri-lo a 16, com seis dias até ao
limite de integração.

Três ressalvas que a saída repete, para não serem esquecidas por quem lê:

1. A contagem vem das curvas de TREINO, não da avaliação. A M2 do
   pré-registo é a fração de execuções que atingem ≥1 recolha na avaliação
   determinística (20 episódios, sementes emparelhadas), que só corre no fim da
   campanha. Aqui usa-se o `best_task_food` da curva de treino, que é o melhor
   genoma da população contra as suas sementes de treino. São grandezas
   diferentes; a do treino é um majorante otimista.
2. O limiar é sobre "pelo menos um algoritmo". O PPO e o SAC podem cruzá-lo
   sem o GNN. Os seus logs não registam recolhas (só `ep_rew_mean`), pelo que
   não entram nesta projeção — o que a torna, também por aqui, otimista quanto
   ao veredicto final e pessimista quanto a esta linha específica.
3. O modelo assume execuções independentes e equiprováveis. É a hipótese
   mais simples e a mais transparente; se houver deriva (por exemplo, sementes
   mais difíceis nas últimas execuções), não se aplica.

Uso:
    python scripts/projetar_limiar_f2.py
    python scripts/projetar_limiar_f2.py --horas-por-run 13
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from math import comb

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTADO = os.path.join(RAIZ, "results", "estado_f2.json")


def prob_pelo_menos(k, n, p):
    """P(Binomial(n, p) >= k)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def posterior_beta(sucessos, tentativas, a=0.5, b=0.5, passos=2001):
    """Posterior de p com prior de Jeffreys, em grelha (chega e é auditável)."""
    grelha = [i / (passos - 1) for i in range(passos)]
    pesos = [(p ** (sucessos + a - 1)) * ((1 - p) ** (tentativas - sucessos + b - 1))
             for p in grelha]
    total = sum(pesos) or 1.0
    return grelha, [w / total for w in pesos]


def _gradientes():
    """A ressalva 2 do cabeçalho deixou de ser hipotética — mostra o que se mediu.

    A 6 de agosto esta projeção só via o braço do GNN e tinha de avisar que o
    limiar vale para QUALQUER algoritmo, pelo que o PPO ou o SAC ainda o podiam
    cruzar sozinhos. A 10 de agosto os dois fecharam, e a avaliação está no
    disco: 0 de 21 cada. Continuar a imprimir a ressalva como possibilidade
    aberta seria envelhecer no sítio — que é o defeito que o
    `estado_f2.sh` existe para não repetir.
    """
    import glob
    padrao = os.path.join(RAIZ, "results", "mapa_grande", "f2*", "**",
                          "eval_by_run.csv")
    csvs = sorted(glob.glob(padrao, recursive=True))
    if not csvs:
        print("  Gradientes: ainda sem eval_by_run.csv — a ressalva 2 mantém-se "
              "aberta (o PPO ou o SAC podem cruzar o limiar sozinhos).")
        return
    try:
        import pandas as pd
    except ImportError:
        return
    print("  Os outros dois braços, MEDIDOS (o limiar vale para qualquer um):")
    for c in csvs:
        d = pd.read_csv(c)
        for algo, g in d.groupby("Algorithm"):
            conv = int((g.groupby("Run").food_collected.mean() > 0).sum())
            n = g.Run.nunique()
            print("    %-4s %2d/%2d execuções convergentes na avaliação"
                  % (algo, conv, n))


def _b_ou_c(n_conv_treino):
    """Qual das leituras da secção, agora que a (A) está excluída.

    A (A) — «o mapa é aprendível de raiz» — cai com o limiar. As outras duas
    NÃO se distinguem com o que existe hoje:

      (B) «nenhum o resolve, nem por transferência nem com treino nativo»
      (C) «é resolvido em k das 21 execuções, abaixo do limiar»

    A diferença é `k >= 1`, e o `k` da secção conta-se na AVALIAÇÃO
    determinística, não nas curvas de treino. As três execuções que hoje
    aparecem com recolha são `best_task_food` do melhor genoma contra as
    sementes de treino — o majorante otimista da ressalva 1. Se nenhuma delas
    recolher na avaliação, o `k` é zero e a leitura certa é a (B).

    Por isso este script deixou de escolher: escolher entre B e C sem o
    `eval_by_run.csv` do GNN seria decidir pela régua errada, que é exatamente o
    erro que o plano de qualidade cataloga como «uma métrica medida por duas
    réguas diferentes».
    """
    print()
    print("  Qual leitura da secção:")
    print("    (A) excluída — o limiar é inalcançável.")
    print("    (B) ou (C) — decide-se com o eval_by_run.csv do GNN, não aqui:")
    print("         k = 0   → (B) nenhum resolve o mapa")
    print("         k >= 1  → (C) resolve-o em k das 21, abaixo do limiar")
    print("    hoje há %d execuções com recolha nas CURVAS DE TREINO, que são o"
          % n_conv_treino)
    print("    majorante otimista da ressalva 1 — não são o k da secção.")


def projetar(e):
    """A aritmética do limiar, sem imprimir nada — para quem a queira mostrar.

    Existe porque o dashboard precisa exatamente destes números e copiá-los
    para lá criaria a mesma conta em dois sítios: o defeito que este projeto
    apanhou a 5 ago com o custo do percurso (13,4% num sítio, 17,0% no outro).
    A conta do limiar vive aqui; quem a mostra, importa-a.

    Devolve `estado` em {'atingido', 'inalcancavel', 'em_aberto'}. Note-se que
    'inalcancavel' NÃO escolhe a leitura da secção: diz que a (A) caiu, e a
    escolha entre (B) e (C) continua a depender do `eval_by_run.csv` do GNN.
    """
    gnn = e["gnn"]
    total = gnn.get("runs_previstos") or 21
    limiar = -(-5 * total // 7)          # ⌈5/7 × n⌉, a mesma conta do pré-registo
    fechados = gnn.get("runs_fechados", [])
    n_fech = len(fechados)
    n_conv = sum(1 for r in fechados if r["recolhas"] > 0)
    restantes = total - n_fech
    faltam = limiar - n_conv             # convergências ainda necessárias
    return {
        "medido_utc": e.get("medido_utc", "?"),
        "total": total, "limiar": limiar,
        "n_fechados": n_fech, "n_convergentes": n_conv,
        "n_falhas": n_fech - n_conv, "restantes": restantes, "faltam": faltam,
        "estado": ("atingido" if faltam <= 0 else
                   "inalcancavel" if faltam > restantes else "em_aberto"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas-por-run", type=float, default=13.0,
                    help="780 min por execução do GNN = 13 h")
    a = ap.parse_args()

    if not os.path.exists(ESTADO):
        raise SystemExit("[X] falta results/estado_f2.json — correr "
                         "scripts/estado_f2.sh (precisa da VPN).")
    with open(ESTADO, encoding="utf-8") as fh:
        e = json.load(fh)

    p = projetar(e)
    total, limiar = p["total"], p["limiar"]
    n_fech, n_conv = p["n_fechados"], p["n_convergentes"]
    n_falhas, restantes, faltam = p["n_falhas"], p["restantes"], p["faltam"]

    print("=" * 74)
    print("PROJEÇÃO DO LIMIAR DO F2  (medido em %s)" % e.get("medido_utc", "?"))
    print("=" * 74)
    print("  limiar pré-registado: ⌈5/7 × %d⌉ = %d execuções convergentes"
          % (total, limiar))
    print("  execuções fechadas:   %d de %d  →  %d convergentes, %d a zero"
          % (n_fech, total, n_conv, n_falhas))
    print("  por correr:           %d" % restantes)
    print()

    if faltam <= 0:
        print("  ✔ O limiar JÁ está atingido.")
        return 0
    if faltam > restantes:
        print("  ✘ O limiar é INALCANÇÁVEL: faltam %d convergências e só restam "
              "%d execuções." % (faltam, restantes))
        print("    Pela emenda 21, reporta-se como negativo com o número "
              "declarado.")
        print()
        _gradientes()
        _b_ou_c(n_conv)
        return 0

    print("  Faltam %d convergências em %d execuções." % (faltam, restantes))
    print()
    print("  Probabilidade de atingir o limiar, por taxa de convergência p:")
    print("  " + "-" * 52)
    for p in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90):
        pr = prob_pelo_menos(faltam, restantes, p)
        barra = "█" * int(round(pr * 30))
        print("    p = %.2f   P(limiar) = %6.2f%%  %s" % (p, 100 * pr, barra))
    print("  " + "-" * 52)

    # Leitura bayesiana: integra a incerteza sobre p em vez de a fixar. Com duas
    # execuções fechadas, é a diferença entre "50%" e "não fazemos ideia".
    grelha, post = posterior_beta(n_conv, n_fech)
    pr_bayes = sum(w * prob_pelo_menos(faltam, restantes, p)
                   for p, w in zip(grelha, post))
    media = sum(p * w for p, w in zip(grelha, post))
    acum, lo, hi = 0.0, None, None
    for p, w in zip(grelha, post):
        acum += w
        if lo is None and acum >= 0.05:
            lo = p
        if hi is None and acum >= 0.95:
            hi = p
    print()
    print("  Integrando a incerteza sobre p (posterior de Jeffreys com %d/%d):"
          % (n_conv, n_fech))
    print("    p estimado = %.2f   (intervalo de 90%%: %.2f a %.2f)"
          % (media, lo or 0.0, hi or 1.0))
    print("    P(atingir o limiar) = %.1f%%" % (100 * pr_bayes))
    print()

    # Quando é que a resposta fica SELADA: basta o nº de falhas passar o que a
    # aritmética permite. É a data que interessa ao calendário, porque a partir
    # daí a secção pode ser escrita sem esperar pelo fim da campanha.
    falhas_toleraveis = total - limiar          # 21 - 15 = 6
    falhas_ate_selar = falhas_toleraveis - n_falhas + 1
    print("  Selagem da resposta:")
    print("    tolerância total de falhas: %d (o limiar deixa passar %d - %d)"
          % (falhas_toleraveis, total, limiar))
    print("    falhas já registadas: %d  →  basta mais %d para o limiar ficar "
          "impossível" % (n_falhas, falhas_ate_selar))
    for p in (0.4, 0.5, 0.6):
        # nº esperado de execuções até acumular `falhas_ate_selar` falhas
        esperado = falhas_ate_selar / (1 - p) if p < 1 else float("inf")
        quando = datetime.now(timezone.utc) + timedelta(
            hours=a.horas_por_run * min(esperado, restantes))
        print("      com p = %.1f, isso acontece por volta da execução %d "
              "(~%s UTC)" % (p, n_fech + min(round(esperado), restantes),
                             quando.strftime("%d %b %H:%M")))
    fim = datetime.now(timezone.utc) + timedelta(hours=a.horas_por_run * restantes)
    print("    fim da campanha (as %d execuções restantes): ~%s UTC"
          % (restantes, fim.strftime("%d %b %H:%M")))

    print()
    print("  ⚠️ Isto conta convergências pelas CURVAS DE TREINO. A M2 conta-as na")
    print("     avaliação determinística, que só corre no fim — e o limiar vale")
    print("     para QUALQUER algoritmo, não só o GNN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
