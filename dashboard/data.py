"""Leitura e agregação dos resultados (CSVs de avaliação) para a vista Ciência.

Fonte de verdade = results/evaluation/eval_summary.csv (1 linha por episódio).
Não treina nem avalia — só lê o que os scripts já produziram.
"""
import os
import glob
import shutil

import pandas as pd

from . import config

GRAFICOS_DIR = os.path.join(config.BASE_DIR, "results", "graficos_tese")
TESE_IMG_DIR = os.path.join(config.BASE_DIR, "Tese", "images", "resultados")

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


# ── Galeria de resultados (vista Resultados) ──────────────────────────────────
def list_sessions():
    """Pastas de sessão em results/graficos_tese/, mais recentes primeiro."""
    if not os.path.isdir(GRAFICOS_DIR):
        return []
    dirs = [d for d in os.listdir(GRAFICOS_DIR)
            if os.path.isdir(os.path.join(GRAFICOS_DIR, d))]
    return sorted(dirs, key=lambda d: os.path.getmtime(os.path.join(GRAFICOS_DIR, d)),
                  reverse=True)


def list_pngs(session: str):
    """PNGs de uma sessão (ordenados)."""
    p = os.path.join(GRAFICOS_DIR, session)
    if not os.path.isdir(p):
        return []
    return sorted(f for f in os.listdir(p) if f.lower().endswith(".png"))


def graph_type(filename: str) -> str:
    """Categoria de um gráfico, derivada do prefixo do nome (para filtrar)."""
    f = filename.lower()
    if f.startswith("comparacao_mapa"):
        return "Curvas por mapa"
    if f.startswith("boxplot"):
        return "Boxplots"
    if f.startswith("desempenho_global"):
        return "Curvas por algoritmo"
    if f.startswith("heatmap_geodesico"):
        return "Heatmaps geodésicos"
    if f.startswith("heatmap_ocupacao"):
        return "Heatmaps de ocupação"
    if f.startswith(("taxa_sucesso", "recolhas", "comparacao_barras")):
        return "Métricas de tarefa"
    return "Outros"


def send_to_thesis(session: str, filename: str):
    """Copia um PNG da sessão para Tese/images/resultados/ (nome inalterado)."""
    src = os.path.join(GRAFICOS_DIR, session, filename)
    if not os.path.exists(src):
        return False, "ficheiro não encontrado"
    os.makedirs(TESE_IMG_DIR, exist_ok=True)
    shutil.copy2(src, os.path.join(TESE_IMG_DIR, filename))
    return True, filename
