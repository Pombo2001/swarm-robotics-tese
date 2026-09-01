# -*- coding: utf-8 -*-
"""Ensaia a análise do F2 com dados SINTÉTICOS, antes de os reais existirem.

Porque existe
O F2 do GNN fecha ~16 ago e o hard stop da tese é 22. São seis dias. Se a
`analise_mapa_grande.py` rebentar — ou pior, se produzir um número errado — com
os dados na mão, não há janela para uma segunda campanha. A análise tem de correr
à primeira.

Isto gera `eval_by_run.csv` na forma EXATA que o pipeline produz (incluindo a
coluna `door_opened`, que só passou a ser escrita a 5 ago) em três cenários de
resultado, e verifica que a análise responde o que devia em cada um:

  A. ninguém converge  — o modo de falha nº1 do pré-registo
  B. o GNN converge, os gradientes não — a leitura A da secção da tese
  C. todos convergem, com a porta usada de formas diferentes — exercita a M3

Não valida a ciência (não há ciência em dados inventados): valida que o código
lê as colunas certas, aplica o limiar ⌈5/7 × n⌉ ao n que encontra, e reporta as
três métricas sem rebentar.

Uso:
    .venv/Scripts/python.exe scripts/testes/ensaio_analise_f2.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

# A consola do Windows é cp1252 e este ficheiro imprime ⌈⌉ e acentos: sem isto,
# o ensaio rebenta no print em vez de na análise, que é o pior sítio para falhar.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANALISE = os.path.join(RAIZ, "scripts", "analise_mapa_grande.py")
DESTINO = os.path.join(RAIZ, "results", "mapa_grande", "f2_ENSAIO", "evaluation")

N_RUNS = 21
N_EP = 20
falhas = []


def gerar_com_convergentes(n_conv, rng):
    """CSV onde o GNN converge em EXATAMENTE `n_conv` dos 21 runs.

    Serve a fronteira da regra de decisão: o pré-registo (emenda 21) fixa o
    limiar em ⌈5/7 × n⌉, que para n=21 dá 15. Um erro de um nesta conta troca o
    veredicto da QI7 — e é o tipo de erro que ninguém vê a ler o código.
    """
    linhas = []
    for algo in ("GNN", "PPO", "SAC"):
        for run in range(1, N_RUNS + 1):
            converge = (algo == "GNN" and run <= n_conv)
            base = 45.0 if converge else 0.0
            for _ in range(N_EP):
                comida = max(0.0, rng.normal(base, 4.0)) if base else 0.0
                # `success` é o que a M2 conta; sem recolha não há sucesso
                linhas.append({
                    "Scenario": "mapa_grande", "ScenarioLabel": "Mapa grande",
                    "Algorithm": algo, "Run": run,
                    "food_collected": float(round(comida)),
                    "success": bool(comida > 0),
                    "total_reward": float(rng.normal(20000, 3000)),
                    "door_opened": bool(converge),
                })
    return pd.DataFrame(linhas)


def gerar(cenario, rng):
    """CSV na forma que o `eval_by_run.py` grava — colunas e tipos incluídos."""
    linhas = []
    for algo in ("GNN", "PPO", "SAC"):
        for run in range(1, N_RUNS + 1):
            if cenario == "ninguem_converge":
                base, p_porta = 0.0, 0.0
            elif cenario == "so_gnn":
                base = 45.0 if algo == "GNN" else 0.0
                p_porta = 0.7 if algo == "GNN" else 0.0
            else:                                  # todos convergem
                base = {"GNN": 52.0, "PPO": 38.0, "SAC": 30.0}[algo]
                p_porta = {"GNN": 0.9, "PPO": 0.3, "SAC": 0.1}[algo]
            # um terço dos runs degenera quando há convergência — é o padrão
            # tudo-ou-nada que a tese descreve, e exercita o "≥1 recolha"
            if base > 0 and run % 3 == 0:
                base = 0.0
            for _ in range(N_EP):
                comida = max(0.0, rng.normal(base, 6.0)) if base else 0.0
                linhas.append({
                    "Scenario": "mapa_grande", "ScenarioLabel": "Mapa grande",
                    "Algorithm": algo, "Run": run,
                    "food_collected": float(round(comida)),
                    "success": bool(comida > 0),
                    "total_reward": float(rng.normal(20000, 3000)),
                    "door_opened": bool(rng.random() < p_porta),
                })
    return pd.DataFrame(linhas)


def correr_analise():
    r = subprocess.run([sys.executable, ANALISE], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def verificar(nome, saida, codigo, esperados):
    if codigo != 0:
        falhas.append(f"{nome}: a análise saiu com código {codigo}")
    for texto in esperados:
        if texto not in saida:
            falhas.append(f"{nome}: falta '{texto}' na saída")
    print(f"  {'[v]' if not falhas else '[?]'} {nome}")


def main():
    rng = np.random.default_rng(7)
    os.makedirs(DESTINO, exist_ok=True)
    alvo = os.path.join(DESTINO, "eval_by_run.csv")
    print("Ensaio da análise do F2 com dados sintéticos "
          f"({N_RUNS} runs × {N_EP} ep × 3 algoritmos)\n")
    try:
        for nome, esperados in (
            ("ninguem_converge", ["M2", "M1", "0.0", "M3"]),
            ("so_gnn", ["M2", "M1", "GNN", "M3"]),
            ("todos", ["M2", "M1", "M3", "porta"]),
        ):
            gerar(nome, rng).to_csv(alvo, index=False)
            codigo, saida = correr_analise()
            verificar(nome, saida, codigo, esperados)
            if nome == "todos":
                # A M3 tem de sair com os três algoritmos, e com valores
                # distintos: uma M3 que devolva o mesmo para todos estaria a ler
                # a coluna errada (ou a média global).
                linhas = [l for l in saida.splitlines() if "porta aberta" in l]
                if len(linhas) < 3:
                    falhas.append("todos: a M3 não reportou os três algoritmos")
                else:
                    print("      M3 reportada:")
                    for l in linhas:
                        print("       ", l.strip())
                    valores = set(l.split()[-1] for l in linhas)
                    if len(valores) < 3:
                        falhas.append("todos: a M3 deu o mesmo valor a algoritmos "
                                      "com fração de porta diferente")
                # E o limiar tem de vir do n do CSV: 21 runs ⇒ 15.
                if "15" not in saida:
                    falhas.append("todos: o limiar ⌈5/7×21⌉ = 15 não aparece na saída")

        # A fronteira da regra de decisão
        # 15 convergentes tem de SUBIR a resultado; 14 tem de dar NEGATIVO.
        # É a conta que decide a conclusão da QI7, e um erro de um não se vê.
        print("\n  fronteira do limiar (⌈5/7×21⌉ = 15):")
        for n_conv, esperado, proibido in ((15, "SOBE A RESULTADO", "NEGATIVO"),
                                           (14, "NEGATIVO", "SOBE A RESULTADO")):
            gerar_com_convergentes(n_conv, rng).to_csv(alvo, index=False)
            codigo, saida = correr_analise()
            ok = esperado in saida and proibido not in saida
            marca = "[v]" if ok else "[X]"
            print(f"    {marca} {n_conv}/21 convergentes → {esperado}")
            if not ok:
                falhas.append(f"limiar: com {n_conv}/21 esperava «{esperado}»")
            if f"{n_conv}/21" not in saida and f"{n_conv}/%d" % N_RUNS not in saida:
                falhas.append(f"limiar: a saída não diz quantos runs convergiram "
                              f"({n_conv})")
    finally:
        shutil.rmtree(os.path.dirname(DESTINO), ignore_errors=True)

    print()
    if falhas:
        for f in falhas:
            print(f"  FALHA  {f}")
        print(f"\n{len(falhas)} problema(s) — a análise do F2 não está pronta")
        return 1
    print("  A análise do F2 corre nos três cenários de resultado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
