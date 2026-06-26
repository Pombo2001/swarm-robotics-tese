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

EVAL_DIR = os.path.join(config.BASE_DIR, "results", "evaluation")
EVAL_SUMMARY = os.path.join(EVAL_DIR, "eval_summary.csv")
STATS_DIR = os.path.join(config.BASE_DIR, "results", "estatisticas")
SIGNIF = os.path.join(STATS_DIR, "testes_significancia_food_collected.csv")
MODEL_DIRS = ("models", "models_ppo", "models_sac")


def _mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


def _aggregate_eval(path: str):
    """Agrega um eval_summary.csv por (cenário, algoritmo).

    Devolve {scenario: {algo: {"ptask": %, "recolhas": média, "n": episódios}}} ou None.
    """
    if not path or not os.path.exists(path):
        return None
    df = pd.read_csv(path)
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


def science_table():
    """Métricas do eval oficial (results/evaluation/eval_summary.csv) ou None."""
    return _aggregate_eval(EVAL_SUMMARY)


# ── Comparação de métricas entre treinos (vista Resultados) ───────────────────
OFICIAL_LABEL = "★ Oficial (10 jun · results/evaluation)"


def _session_eval_path(session: str):
    """Caminho do eval_summary de uma sessão (procura em subpastas) ou None.

    A entrada especial OFICIAL_LABEL aponta para o eval oficial em results/evaluation/.
    """
    if session == OFICIAL_LABEL:
        return EVAL_SUMMARY if os.path.exists(EVAL_SUMMARY) else None
    base = os.path.join(GRAFICOS_DIR, session)
    hits = glob.glob(os.path.join(base, "**", "eval_summary.csv"), recursive=True)
    return hits[0] if hits else None


def sessions_with_eval():
    """Treinos que têm métricas de avaliação, prontos a comparar (oficial primeiro)."""
    out = []
    if os.path.exists(EVAL_SUMMARY):
        out.append(OFICIAL_LABEL)
    for s in list_sessions():
        if glob.glob(os.path.join(GRAFICOS_DIR, s, "**", "eval_summary.csv"), recursive=True):
            out.append(s)
    return out


def session_metrics(session: str):
    """Métricas Ptask/recolhas por (cenário, algo) de um treino, ou None."""
    return _aggregate_eval(_session_eval_path(session))


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


# ── Robustez a falhas (Rrobust) ───────────────────────────────────────────────
def robustness_table():
    """Por (cenário, algo): recolhas base vs com 10% de falhas + retenção %.

    Base = eval_summary.csv (avaliação sem falhas, agregada por cenário/algo).
    Falhas = eval_{algo}_{cenário}_fail10.csv (run_eval.py --fail-frac 0.1).
    Devolve {scenario: {algo: {base, fail, base_succ, fail_succ, retencao, n}}}
    só para os pares que têm ambas as avaliações; {} se ainda não há nada.
    """
    if not os.path.exists(EVAL_SUMMARY):
        return {}
    base = pd.read_csv(EVAL_SUMMARY)
    out = {}
    for scen in config.SCENARIO_KEYS:
        for algo in config.ALGOS:
            b = base[(base["Scenario"] == scen) & (base["Algorithm"] == algo)]
            fp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{scen}_fail10.csv")
            if b.empty or not os.path.exists(fp):
                continue
            f = pd.read_csv(fp)
            base_m = float(b["food_collected"].mean())
            fail_m = float(f["food_collected"].mean())
            out.setdefault(scen, {})[algo] = {
                "base": base_m,
                "fail": fail_m,
                "base_succ": 100.0 * float(b["success"].mean()),
                "fail_succ": (100.0 * float(f["success"].mean())
                              if "success" in f.columns else None),
                "retencao": (100.0 * fail_m / base_m) if base_m > 1e-9 else None,
                "n": int(len(f)),
            }
    return out


# ── Escalabilidade Zero-Shot (Sscale) ─────────────────────────────────────────
def scalability_scenarios():
    """Cenários com CSV de escalabilidade (escalabilidade_{cenário}.csv)."""
    if not os.path.isdir(STATS_DIR):
        return []
    return [k for k in config.SCENARIO_KEYS
            if os.path.exists(os.path.join(STATS_DIR, f"escalabilidade_{k}.csv"))]


def scalability_table(scenario: str):
    """Lê escalabilidade_{scenario}.csv → {algo: [pontos ordenados por N]} ou None.

    Cada ponto: {N, food_per_agent, success_rate, mean_food, compatible}. Os
    pontos incompatíveis (MLP do PPO/SAC com N!=20) vêm com compatible=False e
    métricas a None — é a evidência da vantagem de escala da GNN.
    """
    fp = os.path.join(STATS_DIR, f"escalabilidade_{scenario}.csv")
    if not os.path.exists(fp):
        return None
    df = pd.read_csv(fp)
    num = lambda v: None if pd.isna(v) else float(v)
    out = {}
    for _, r in df.iterrows():
        out.setdefault(r["Algorithm"], []).append({
            "N": int(r["N"]),
            "food_per_agent": num(r["food_per_agent"]),
            "success_rate": num(r["success_rate"]),
            "mean_food": num(r["mean_food"]),
            "compatible": bool(r["compatible"]),
        })
    for a in out:
        out[a].sort(key=lambda d: d["N"])
    return out


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


# ── Curvas de treino ao vivo (vista Monitorizar) ─────────────────────────────
# algo -> (caminho, coluna_x, coluna_score, coluna_tarefa)
TRAIN_LOGS = {
    "GNN": (os.path.join(config.BASE_DIR, "results", "logs", "gnn_3d_training.csv"),
            "timestep", "best_fitness", "best_task_food"),
    "PPO": (os.path.join(config.BASE_DIR, "results", "logs_ppo", "training_history_ppo_3d.csv"),
            "timesteps", "ep_rew_mean", "ep_task_mean"),
    "SAC": (os.path.join(config.BASE_DIR, "results", "logs_sac", "training_history_sac_3d.csv"),
            "timesteps", "ep_rew_mean", "ep_task_mean"),
}


def training_curves():
    """Lê os CSVs de treino locais. Devolve {algo: {x, score, task, mtime}} (só os que existem)."""
    out = {}
    for algo, (path, xcol, scol, tcol) in TRAIN_LOGS.items():
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if xcol not in df.columns or len(df) == 0:
            continue
        out[algo] = {
            "x": df[xcol].tolist(),
            "score": df[scol].tolist() if scol in df.columns else [],
            "task": df[tcol].tolist() if tcol in df.columns else [],
            "mtime": _mtime(path),
        }
    return out


# ── Vídeos dos episódios (vista Vídeos) ───────────────────────────────────────
VIDEO_ALGOS = ("gnn", "ppo", "sac")


def _videos_dir(session: str) -> str:
    return os.path.join(GRAFICOS_DIR, session, "videos")


def video_sessions():
    """Sessões com vídeos (pasta videos/ não vazia), mais recentes primeiro."""
    out = []
    for s in list_sessions():
        d = _videos_dir(s)
        if os.path.isdir(d) and any(f.lower().endswith(".gif") for f in os.listdir(d)):
            out.append(s)
    return out


def list_videos(session: str):
    """Nomes dos GIFs de uma sessão (ordenados)."""
    d = _videos_dir(session)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".gif"))


def parse_video(filename: str):
    """'gnn_u_wall.gif' -> ('gnn', 'u_wall'). Algo = prefixo conhecido."""
    base = filename[:-4] if filename.lower().endswith(".gif") else filename
    for a in VIDEO_ALGOS:
        if base.startswith(a + "_"):
            return a, base[len(a) + 1:]
    return "?", base


def video_for(session: str, algo: str, scenario: str):
    """Nome do GIF de (algo, cenário) nessa sessão, ou None se não existir."""
    fn = f"{algo}_{scenario}.gif"
    return fn if fn in list_videos(session) else None


def scenarios_with_video(session: str):
    """Cenários (chaves) que têm pelo menos um vídeo na sessão, na ordem canónica."""
    present = {parse_video(f)[1] for f in list_videos(session)}
    from . import config
    return [k for k in config.SCENARIO_KEYS if k in present]


def send_to_thesis(session: str, filename: str):
    """Copia um PNG da sessão para Tese/images/resultados/ (nome inalterado)."""
    src = os.path.join(GRAFICOS_DIR, session, filename)
    if not os.path.exists(src):
        return False, "ficheiro não encontrado"
    os.makedirs(TESE_IMG_DIR, exist_ok=True)
    shutil.copy2(src, os.path.join(TESE_IMG_DIR, filename))
    return True, filename
