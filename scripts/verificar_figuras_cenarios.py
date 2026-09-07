# -*- coding: utf-8 -*-
r"""Nenhuma figura por cenário esconde um cenário que os dados têm.

Porque existe
As figuras 6.1 e 6.2 da dissertação — taxa de sucesso e recolhas por cenário —
mostraram durante semanas **cinco** dos sete cenários. Faltavam o Muro em U e a
Porta com Alternativa, que são o cenário de toda a linha da novidade e aquele
onde está o melhor resultado do trabalho. O eixo continuava a desenhar os sete
rótulos, por isso a figura parecia completa: só faltavam as barras.

A causa: a coluna `ScenarioLabel` gravada no `eval_by_run*.csv` fica congelada
com os nomes da data da avaliação. Quando dois cenários foram renomeados
(`Beco Sem Saída (U)` -> `Muro em U`, `Porta Coop. c/ Alternativa` -> `Porta com
Alternativa`), o `plot_evaluation` passou a agrupar por essa coluna e a ordenar o
eixo pelo mapa de hoje: os cinco nomes que não mudaram sobreviveram, os dois
renomeados caíram fora, sem aviso nenhum.

Nenhum verificador via isto. O `verificar_numeros_tese` lê o `.tex` e os CSV — e
ambos estavam certos. O `verificar_figuras_tese` compara a cópia da tese com a
de `results/` — e as duas estavam igualmente erradas. O que faltava era comparar
a figura com os DADOS.

O que faz
1. Todos os cenários da campanha canónica estão no CSV (rede contra um CSV
   truncado).
2. Refaz as duas figuras a partir desse CSV e compara-as, pixel a pixel, com as
   que estão em `Tese/images/`. Uma figura da tese que já não seja o que os
   dados produzem falha aqui.
3. A rede de dentro do `plot_evaluation` — que recusa desenhar quando o eixo e
   os dados não coincidem — continua a disparar: injeta-se um rótulo obsoleto e
   exige-se o erro. Uma rede que ninguém ensaia é uma rede que se desfaz.
4. As famílias de figuras com um ficheiro por cenário (`boxplot_eval_*`,
   `curvas_*`) têm um ficheiro para cada cenário, e não menos.

Uso:
    .venv/Scripts/python.exe scripts/verificar_figuras_cenarios.py
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import pandas as pd
from PIL import Image, ImageChops

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:                                            # pragma: no cover
    pass

from src.scenarios import SCENARIOS, SCENARIO_LABELS_SHORT   # noqa: E402

CSV = os.path.join(RAIZ, "results", "graficos_tese", "final_7d",
                   "eval_by_run_7d.csv")
IMAGENS = os.path.join(RAIZ, "Tese", "images", "resultados")
PARES = ("taxa_sucesso_por_cenario.png", "recolhas_por_cenario.png")
_FINAL = os.path.join(RAIZ, "results", "graficos_tese", "final_7d")
FAMILIAS = {"boxplot_eval_{}.png": _FINAL,      # fiabilidade entre execuções
            "comparacao_mapa_{}.png": _FINAL}   # curvas de aprendizagem

erros: list[str] = []


def X(msg: str) -> None:
    erros.append(msg)


def _iguais(a: str, b: str, tol: int = 2) -> bool:
    """Duas imagens são a mesma? Tolerância de `tol` níveis por canal.

    O md5 não serve: o matplotlib grava metadados que mudam a cada corrida, e a
    compressão do PNG não é bit-a-bit reprodutível entre versões.
    """
    with Image.open(a) as ia, Image.open(b) as ib:
        ia, ib = ia.convert("RGB"), ib.convert("RGB")
        if ia.size != ib.size:
            return False
        return np.asarray(ImageChops.difference(ia, ib)).max() <= tol


def main() -> int:
    print("=" * 74)
    print("VERIFICAÇÃO: as figuras por cenário mostram todos os cenários")
    print("=" * 74)

    if not os.path.exists(CSV):
        print("   [i] sem %s — nada a conferir" % os.path.relpath(CSV, RAIZ))
        return 0
    ev = pd.read_csv(CSV)
    ev["success"] = ev["success"].astype(bool)

    # 1. o CSV tem os sete cenários
    nos_dados = set(ev["Scenario"])
    faltam = [s for s in SCENARIOS if s not in nos_dados and s != "mapa_grande"]
    if faltam:
        X("o CSV da campanha final não tem os cenários: %s" % ", ".join(faltam))
    else:
        print("   [v] os %d cenários da campanha estão no CSV"
              % len(nos_dados))

    # 2. as figuras da tese são o que estes dados produzem hoje
    from scripts.eval_suite import plot_evaluation
    with tempfile.TemporaryDirectory() as tmp:
        try:
            feitas = plot_evaluation(summary=ev, out_dir=tmp)
        except Exception as e:                               # pragma: no cover
            X("plot_evaluation falhou sobre o CSV canónico: %s" % e)
            feitas = []
        for nome in PARES:
            novo = os.path.join(tmp, nome)
            tese = os.path.join(IMAGENS, nome)
            if not os.path.exists(novo):
                X("%s: o gerador não a produziu" % nome)
            elif not os.path.exists(tese):
                X("%s: não está em Tese/images/resultados/" % nome)
            elif not _iguais(novo, tese):
                X("%s: a figura da tese não é a que os dados produzem hoje "
                  "(refaz com o Defesa/… ou copia de results/)" % nome)
            else:
                print("   [v] %-30s é o que os dados produzem" % nome)
        del feitas

    # 3. as duas redes do plot_evaluation disparam mesmo
    #
    # (a) Um rótulo obsoleto no CSV já NÃO faz mal: o `_rotular` reconstrói-o a
    #     partir do slug. É esta a correção de fundo, e ensaia-se pelo efeito —
    #     com o nome antigo lá dentro, a figura tem de sair igual à boa.
    velho = ev.copy()
    velho["ScenarioLabel"] = "lixo de outra época"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            plot_evaluation(summary=velho, out_dir=tmp)
            iguais = all(_iguais(os.path.join(tmp, n), os.path.join(IMAGENS, n))
                         for n in PARES)
        except Exception as e:                               # pragma: no cover
            X("ensaio (a): plot_evaluation falhou com rótulos obsoletos (%r)" % e)
        else:
            if iguais:
                print("   [v] um rótulo obsoleto no CSV já não muda a figura")
            else:
                X("ensaio (a): com rótulos obsoletos a figura saiu diferente — "
                  "o rótulo voltou a depender da coluna gravada")

    # (b) Um cenário que os dados tenham e o eixo não — o modo de falha que
    #     deixou as figuras com cinco de sete — tem de parar o desenho.
    intruso = ev.copy()
    intruso.loc[intruso.index[:20], "Scenario"] = "cenario_que_o_eixo_nao_conhece"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            plot_evaluation(summary=intruso, out_dir=tmp)
        except ValueError:
            print("   [v] a rede recusa desenhar um cenário fora do eixo")
        except Exception as e:                               # pragma: no cover
            X("ensaio (b): erro inesperado (%r)" % e)
        else:
            X("ensaio (b): o plot_evaluation DESENHOU deixando um cenário de "
              "fora — a proteção deixou de funcionar")

    # 4. as famílias com um ficheiro por cenário estão completas
    for padrao, pasta in FAMILIAS.items():
        if not os.path.isdir(pasta):
            continue
        em_falta = [s for s in SCENARIOS
                    if s in nos_dados
                    and not os.path.exists(os.path.join(pasta, padrao.format(s)))]
        if em_falta:
            X("%s: sem ficheiro para %s" % (padrao, ", ".join(em_falta)))
        else:
            print("   [v] %-30s um ficheiro por cenário" % padrao.format("*"))

    print()
    if erros:
        print("DIVERGÊNCIAS (%d):" % len(erros))
        for e in erros:
            print("   " + e)
        return 1
    print("Nenhuma figura por cenário esconde um cenário ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
