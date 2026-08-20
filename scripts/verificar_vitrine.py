# -*- coding: utf-8 -*-
"""As legendas da Vitrine batem com os dados que a figura ao lado mostra.

A Vitrine é o ecrã que se projeta na sala, e as suas notas são escritas à mão
em `configs/vitrine.yaml` — «Vitória limpa do GNN — 69,8 ± 0,9», «28/28 a
100%». Nada as ligava aos CSV: bastava reprocessar uma campanha para a nota
passar a dizer um número que a figura já não mostra.

Verifica, por item:

* a figura existe na campanha indicada;
* a campanha é das que o dashboard mostra (`data.campanhas_visiveis`) — uma
  vitrine que aponte para uma campanha escondida é uma imagem morta;
* cada `NN,N rec/ep` da nota bate com a média por execução do CSV;
* cada `N/N` bate com as execuções que resolvem o cenário por completo;
* os pares `A vs B` / `A contra B` batem com os dois algoritmos citados.

O cenário sai do nome da figura (`dotplot_eval_<cenário>.png`) e o algoritmo
do texto da nota — que é precisamente o que se quer verificar: se a nota diz
GNN, é o GNN que tem de dar aquele número.
"""
from __future__ import annotations

import os
import re
import sys

import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import data  # noqa: E402

RAIZ = os.path.join("results", "graficos_tese")
YAML = os.path.join("configs", "vitrine.yaml")
TOL_MEDIA = 0.15          # rec/ep — as notas vêm arredondadas a uma decimal
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
    """{algoritmo: (média de recolhas por execução, nº a 100%, nº execuções)}."""
    sub = df[df["Scenario"] == cenario]
    out = {}
    for algo, g in sub.groupby("Algorithm"):
        por_run = g.groupby("Run")
        medias = por_run["food_collected"].mean()
        # «a 100%» é a execução em que todos os episódios resolvem o cenário.
        cheias = por_run["success"].apply(lambda s: bool(s.astype(bool).all()))
        out[str(algo).upper()] = (float(medias.mean()), int(cheias.sum()),
                                  int(medias.size))
    return out


def _num(txt: str) -> float:
    return float(txt.replace(",", "."))


def _cenario_da_figura(figura: str) -> str | None:
    m = re.match(r"(?:dotplot|boxplot)_eval_(.+)\.png$", figura)
    if m:
        return m.group(1)
    m = re.match(r"heatmap_(?:ocupacao_\w+?|geodesico)_(.+)\.png$", figura)
    return m.group(1) if m else None


def _algos_citados(nota: str) -> list[str]:
    return [a for a in ALGOS if re.search(r"\b%s\b" % a, nota)]


def verificar_item(campanha: str, figura: str, nota: str) -> None:
    global vistos
    rot = "%s · %s" % (campanha, figura)

    if not os.path.exists(os.path.join(RAIZ, campanha, figura)):
        X(rot, "a figura não existe")
        return
    if campanha not in data.campanhas_visiveis():
        X(rot, "a campanha não é das que o dashboard mostra")

    cenario = _cenario_da_figura(figura)
    if cenario is None:
        return                       # figura agregada (barras gerais): sem cenário
    df = _eval_csv(campanha)
    if df is None:
        X(rot, "sem eval_by_run para conferir a nota")
        return
    stats = _por_algo(df, cenario)
    if not stats:
        X(rot, "o CSV não tem o cenário %s" % cenario)
        return
    citados = _algos_citados(nota)
    for a in citados:
        if a not in stats:
            X(rot, "a nota fala do %s, mas no %s esta campanha só tem %s"
              % (a, cenario, "/".join(sorted(stats))))
    citados = [a for a in citados if a in stats]

    # ── «NN,N rec/ep» ────────────────────────────────────────────────────────
    for m in re.finditer(r"(\d+,\d)\s*(?:rec/ep|±)", nota):
        esperado = _num(m.group(1))
        alvo = citados[0] if citados else None
        if alvo is None or alvo not in stats:
            X(rot, "a nota diz %s rec/ep mas não nomeia um algoritmo do CSV"
              % m.group(1))
            continue
        real = stats[alvo][0]
        vistos += 1
        if abs(real - esperado) > TOL_MEDIA:
            X(rot, "%s: a nota diz %s rec/ep, o CSV dá %.1f"
              % (alvo, m.group(1), real))

    # ── «N/N a 100%» ─────────────────────────────────────────────────────────
    for m in re.finditer(r"(\d+)/(\d+)", nota):
        cheias, total = int(m.group(1)), int(m.group(2))
        alvo = citados[0] if citados else None
        if alvo is None or alvo not in stats:
            continue
        real_cheias, real_total = stats[alvo][1], stats[alvo][2]
        vistos += 1
        if (cheias, total) != (real_cheias, real_total):
            X(rot, "%s: a nota diz %d/%d, o CSV dá %d/%d"
              % (alvo, cheias, total, real_cheias, real_total))

    # ── «A contra B (PPO) e C (SAC)» / «A vs B» ──────────────────────────────
    pares = re.findall(r"(\d+,\d)\s*(?:contra|vs)\s*(\d+,\d)", nota)
    for a, b in pares:
        if len(citados) < 2:
            continue
        for valor, algo in ((a, citados[0]), (b, citados[1])):
            if algo not in stats:
                continue
            vistos += 1
            if abs(stats[algo][0] - _num(valor)) > TOL_MEDIA:
                X(rot, "%s: a nota diz %s, o CSV dá %.1f"
                  % (algo, valor, stats[algo][0]))
    # o terceiro valor de «X contra Y (PPO) e Z (SAC)»
    for m in re.finditer(r"e\s+(\d+,\d)\s*\((SAC|PPO|GNN)\)", nota):
        algo = m.group(2)
        if algo in stats:
            vistos += 1
            if abs(stats[algo][0] - _num(m.group(1))) > TOL_MEDIA:
                X(rot, "%s: a nota diz %s, o CSV dá %.1f"
                  % (algo, m.group(1), stats[algo][0]))


def main() -> int:
    with open(YAML, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    n_itens = 0
    for bloco in cfg.get("blocos", []):
        campanha_bloco = bloco.get("campanha")
        for item in bloco.get("itens", []):
            campanha = item.get("campanha") or campanha_bloco
            if not campanha:
                X(str(item.get("figura")), "item sem campanha")
                continue
            n_itens += 1
            verificar_item(campanha, item["figura"], item.get("nota", ""))

    print("vitrine: %d itens, %d valores conferidos contra os CSV"
          % (n_itens, vistos))
    for e in erros:
        print("  ERRO  %s" % e)
    if erros:
        print("%d divergência(s) na vitrine" % len(erros))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
