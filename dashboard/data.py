"""Leitura e agregação dos resultados (CSVs de avaliação) para a vista Ciência.

Fonte de verdade = results/evaluation/eval_summary.csv (1 linha por episódio).
Não treina nem avalia — só lê o que os scripts já produziram.
"""
import os
import glob

import pandas as pd

from . import config

EVAL_SUMMARY = os.path.join(config.BASE_DIR, "results", "evaluation", "eval_summary.csv")
SIGNIF = os.path.join(config.BASE_DIR, "results", "estatisticas",
                      "testes_significancia_food_collected.csv")
MODEL_DIRS = ("models", "models_ppo", "models_sac")


def _mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


def science_table():
    """Agrega o eval_summary por (cenário, algoritmo).

    Devolve {scenario: {algo: {"ptask": %, "recolhas": média, "n": episódios}}} ou None.
    """
    if not os.path.exists(EVAL_SUMMARY):
        return None
    df = pd.read_csv(EVAL_SUMMARY)
    agg = df.groupby(["Scenario", "Algorithm"]).agg(
        ptask=("success", lambda s: 100.0 * s.mean()),
        recolhas=("food_collected", "mean"),
        n=("success", "size"),
    ).reset_index()
    out = {}
    for _, r in agg.iterrows():
        out.setdefault(r["Scenario"], {})[r["Algorithm"]] = {
            "ptask": float(r["ptask"]), "recolhas": float(r["recolhas"]), "n": int(r["n"]),
        }
    return out


def eval_freshness():
    """Compara a data do eval_summary com a dos modelos treinados.

    Devolve (eval_mtime, model_mtime, stale: bool). stale=True => há modelos mais
    recentes que a avaliação (armadilha conhecida nº3: eval desfasado dos modelos).
    """
    eval_t = _mtime(EVAL_SUMMARY)
    files = []
    for d in MODEL_DIRS:
        files += glob.glob(os.path.join(config.BASE_DIR, "results", d, "*"))
    model_t = max((_mtime(f) for f in files), default=0.0)
    return eval_t, model_t, (model_t > eval_t + 60)


def significance():
    """Tabela de significância (p-values, vencedor por par algo/cenário) ou None."""
    if not os.path.exists(SIGNIF):
        return None
    return pd.read_csv(SIGNIF)
