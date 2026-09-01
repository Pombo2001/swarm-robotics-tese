"""
progress.py — Progresso partilhado entre os scripts de geração e o dashboard
Os scripts (plot_results, heatmaps) escrevem o progresso num ficheiro simples;
o dashboard lê-o no seu tick e atualiza a barra de progresso + label de estado.
Formato do ficheiro: uma linha "FRACAO|MENSAGEM" (ex: "0.4200|A gerar heatmap SAC/u_wall").
"""
import os

PROGRESS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "results", "logs", "_report_progress.txt")


def set_progress(frac, msg):
    """Escreve a fração [0,1] e a mensagem atual. Silencioso em caso de erro."""
    try:
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        frac = max(0.0, min(1.0, float(frac)))
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            f.write(f"{frac:.4f}|{msg}")
    except Exception:
        pass


def clear_progress():
    """Remove o ficheiro de progresso (sinaliza 'sem tarefa a decorrer')."""
    try:
        os.remove(PROGRESS_FILE)
    except Exception:
        pass


def read_progress(max_age_s=15):
    """Lê (frac, msg) se o ficheiro for recente; senão None (idle).
    Usado pelo dashboard. max_age_s evita mostrar progresso de uma tarefa morta."""
    try:
        import time
        if not os.path.exists(PROGRESS_FILE):
            return None
        if time.time() - os.path.getmtime(PROGRESS_FILE) > max_age_s:
            return None
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        frac_s, _, msg = raw.partition("|")
        return float(frac_s), msg
    except Exception:
        return None
