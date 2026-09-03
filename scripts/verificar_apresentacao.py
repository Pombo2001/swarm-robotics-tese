# -*- coding: utf-8 -*-
"""As frases da Apresentação batem com os dados do treino que está no ecrã.

A vista «Apresentação» mostra, por cenário, o treino vencedor do ranking e uma
frase escrita à mão em `configs/apresentacao.yaml`. A frase diz números —
«PPO 71,5 rec/ep, 7/7 execuções» — e nada os ligava ao CSV: bastava
reprocessar uma campanha, ou o ranking mudar de vencedor, para a frase passar
a dizer um número que a figura ao lado já não mostra.

Verifica:

* os oito cenários do simulador têm frase, e nenhuma frase é de um cenário
  que não existe;
* cada `ALGO … NN,N rec/ep` da frase bate com a média por execução desse
  algoritmo no CSV do treino vencedor (o mesmo que a vista mostra);
* cada `ALGO … N/N` bate com as execuções a 100 % desse algoritmo;
* um número qualificado com «na campanha final» confere-se contra a `final_7d`;
* o episódio 3D exportado para a Apresentação, quando existe, é do treino
  vencedor — o meta diz a campanha, e a vista recusa-o se não for.

O número pertence ao ÚLTIMO algoritmo nomeado antes dele na frase. É a regra
que faz «GNN 121,4 contra 123,2 do PPO» ler-se como se escreve: o 123,2 vem
depois do «do PPO»? Não — vem antes; por isso «X do PPO» é tratado à parte.
"""
from __future__ import annotations

import json
import os
import re
import sys

import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import config, data  # noqa: E402

RAIZ = os.path.join("results", "graficos_tese")
YAML = os.path.join("configs", "apresentacao.yaml")
DIR_EP = os.path.join("results", "episodios_3d", "apresentacao")
TOL_MEDIA = 0.15
ALGOS = ("GNN", "PPO", "SAC")

erros: list[str] = []
vistos = 0


def X(item: str, msg: str) -> None:
    erros.append("%s: %s" % (item, msg))


def _eval_csv(campanha: str) -> pd.DataFrame | None:
    d = os.path.join(RAIZ, campanha)
    for nome in ("eval_by_run.csv", "eval_by_run_7d.csv"):
        p = os.path.join(d, nome)
        if os.path.exists(p):
            return pd.read_csv(p)
    return None


def _por_algo(df: pd.DataFrame, cenario: str) -> dict:
    """{ALGO: (média por execução, execuções a 100 %, execuções)}."""
    sub = df[df["Scenario"] == cenario]
    out = {}
    for algo, g in sub.groupby("Algorithm"):
        por_run = g.groupby("Run")
        medias = por_run["food_collected"].mean()
        cheias = por_run["success"].apply(lambda s: bool(s.astype(bool).all()))
        out[str(algo).upper()] = (float(medias.mean()), int(cheias.sum()), int(medias.size))
    return out


def _num(txt: str) -> float:
    return float(txt.replace(",", "."))


def _atribuicoes(frase: str):
    """[(algo, tipo, valor, na_campanha_final)] — cada número com o seu algoritmo.

    Percorre a frase da esquerda para a direita e liga cada número ao último
    algoritmo nomeado antes dele; «123,2 do PPO» liga ao que vem a seguir.
    """
    saida = []
    # «X do PPO» / «X (PPO)»: o algoritmo vem depois do número.
    for m in re.finditer(r"(\d+,\d)\s*(?:do|da|\()\s*(GNN|PPO|SAC)", frase):
        saida.append((m.group(2), "media", _num(m.group(1)), m.start()))
    marcados = {s[3] for s in saida}
    ultimo, pos_ultimo = None, -1
    tokens = list(re.finditer(r"\b(GNN|PPO|SAC)\b|(\d+,\d)\s*rec/ep|(\d+)/(\d+)", frase))
    for m in tokens:
        if m.group(1):
            ultimo, pos_ultimo = m.group(1), m.start()
            continue
        if m.start() in marcados:
            continue
        if ultimo is None:
            continue
        if m.group(2):
            saida.append((ultimo, "media", _num(m.group(2)), m.start()))
        else:
            saida.append((ultimo, "cheias", (int(m.group(3)), int(m.group(4))), m.start()))
    final = "campanha final" in frase
    return [(a, t, v, final) for a, t, v, _ in saida]


def verificar_frase(cenario: str, frase: str) -> None:
    global vistos
    linhas = data.ranking_por_cenario().get(cenario, [])
    if not linhas:
        X(cenario, "sem treino vencedor no ranking")
        return
    venc = linhas[0]
    campanha = venc["campanha"]
    stats_venc = {}
    df = _eval_csv(campanha)
    if df is None:
        X(cenario, "o vencedor (%s) não tem eval_by_run para conferir" % campanha)
        return
    stats_venc = _por_algo(df, cenario)
    stats_final = {}
    df_final = _eval_csv("final_7d")
    if df_final is not None:
        stats_final = _por_algo(df_final, cenario)

    for algo, tipo, valor, na_final in _atribuicoes(frase):
        # O algoritmo vencedor confere-se sempre contra a campanha vencedora; os
        # outros, se a campanha vencedora não os treinou, contra a final.
        if algo in stats_venc and (algo == venc["algo"].upper() or not na_final):
            stats, origem = stats_venc, campanha
        elif algo in stats_final:
            stats, origem = stats_final, "final_7d"
        else:
            X(cenario, "a frase fala do %s, que nem o vencedor (%s) nem a final treinaram"
              % (algo, campanha))
            continue
        vistos += 1
        media, cheias, total = stats[algo]
        if tipo == "media" and abs(media - valor) > TOL_MEDIA:
            X(cenario, "%s: a frase diz %.1f rec/ep, o CSV de %s dá %.1f"
              % (algo, valor, origem, media))
        if tipo == "cheias" and (cheias, total) != valor:
            X(cenario, "%s: a frase diz %d/%d, o CSV de %s dá %d/%d"
              % (algo, valor[0], valor[1], origem, cheias, total))

    # O episódio 3D da Apresentação, se existir, é deste treino.
    p = os.path.join(DIR_EP, "%s_%s.json" % (venc["algo"].lower(), cenario))
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            meta = json.load(fh).get("meta", {})
        origem = data._ALIAS.get(meta.get("campanha", ""), meta.get("campanha", ""))
        vistos += 1
        if origem != campanha:
            X(cenario, "o episódio 3D é da campanha «%s», o vencedor é «%s»"
              % (meta.get("campanha", "?"), campanha))


def main() -> int:
    with open(YAML, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    itens = {it["cenario"]: (it.get("frase") or "") for it in cfg.get("cenarios", [])}

    for cen in config.SCENARIO_KEYS:
        if cen not in itens:
            X(cen, "sem frase no apresentacao.yaml")
    for cen in itens:
        if cen not in config.SCENARIO_KEYS:
            X(cen, "cenário que o simulador não conhece")
    for cen, frase in itens.items():
        if cen in config.SCENARIO_KEYS:
            verificar_frase(cen, frase)

    print("apresentação: %d cenários, %d valores conferidos contra os CSV"
          % (len(itens), vistos))
    for e in erros:
        print("  ERRO  %s" % e)
    if erros:
        print("%d divergência(s) na apresentação" % len(erros))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
