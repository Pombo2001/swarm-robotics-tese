"""Teste do mecanismo do dashboard F1: JobQueue + captura de stdout (PIPE).

Usa um processo DUMMY (em vez de run_experiments.py) para validar a infraestrutura
sem treinar nada nem tocar nos modelos. Verifica:
  1. o stdout do processo é capturado no buffer em tempo real;
  2. a fila corre o job e marca-o "concluído" (exit 0);
  3. stop() mata um job em curso e marca-o "parado".

Corre das DUAS maneiras — `pytest tests/` e
`.venv/Scripts/python.exe tests/test_dashboard_jobs.py`.

Até 27 jul 2026 corria só como script: o trabalho estava no corpo do módulo e
acabava em `sys.exit(0)`, o que durante a *coleção* do pytest subia como
INTERNALERROR e abortava a corrida inteira. A solução da altura foi excluí-lo
(`collect_ignore` no conftest) — o que devolveu o `pytest tests/` a funcionar mas
deixou o mecanismo do dashboard fora da rede de segurança: uma regressão no
JobQueue não aparecia em nenhuma corrida da suite. Agora o trabalho está em
funções `test_*` e o `sys.exit` vive só no bloco `__main__`, onde é inofensivo.
"""
import os
import sys
import time
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import config
from dashboard.jobs import Job, JobQueue


def _dummy(codigo):
    """Escreve um .py temporário e devolve o caminho (o chamador apaga)."""
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    f.write(codigo)
    f.close()
    return f.name


DUMMY_OK_SRC = (
    "import sys, time\n"
    "for i in range(5):\n"
    "    print('linha de treino', i, flush=True)\n"
    "    time.sleep(0.1)\n"
    "sys.exit(0)\n"
)

DUMMY_LONG_SRC = (
    "import time\n"
    "while True:\n"
    "    print('a treinar...', flush=True)\n"
    "    time.sleep(0.2)\n"
)


def _wait(cond, timeout=15.0, step=0.1):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(step)
    return False


def test_job_conclui_e_captura_stdout():
    """O job corre até ao fim e o stdout aparece no buffer em tempo real."""
    caminho = _dummy(DUMMY_OK_SRC)
    original = config.RUN_EXPERIMENTS
    try:
        config.RUN_EXPERIMENTS = caminho      # redireciona o backend para o dummy
        q = JobQueue()
        job = Job(algo="PPO", scenarios=["none"], minutes=1, runs=1, eval_episodes=0)
        q.add(job)
        q.start()

        captured = []
        ok = _wait(lambda: (captured.extend(q.drain_log()),
                            job.status in ("concluído", "falhou"))[-1])
        captured.extend(q.drain_log())        # drena o resto
        texto = "\n".join(captured)

        assert ok, "o job não terminou a tempo"
        assert job.status == "concluído", (
            f"estado esperado 'concluído', obtido '{job.status}' (código {job.exit_code})")
        assert "linha de treino 0" in texto and "linha de treino 4" in texto, (
            f"stdout do processo não foi capturado: {texto[:200]!r}")
        print("  [OK] job concluído (exit 0) e as 5 linhas capturadas em tempo real")
    finally:
        config.RUN_EXPERIMENTS = original
        try:
            os.remove(caminho)
        except OSError:
            pass


def test_stop_mata_job_em_curso():
    """stop() mata o processo e deixa o job em 'parado' (não 'concluído')."""
    caminho = _dummy(DUMMY_LONG_SRC)
    original = config.RUN_EXPERIMENTS
    try:
        config.RUN_EXPERIMENTS = caminho
        q = JobQueue()
        job = Job(algo="GNN", scenarios=["none"], minutes=99, runs=1, eval_episodes=0)
        q.add(job)
        q.start()

        started = _wait(lambda: job.status == "a correr", timeout=10)
        time.sleep(0.5)                       # deixa produzir algumas linhas
        q.stop()
        stopped = _wait(lambda: not q.is_running, timeout=10)

        assert started, "o job não chegou a 'a correr'"
        assert stopped, "a fila não parou após stop()"
        assert job.status == "parado", f"estado esperado 'parado', obtido '{job.status}'"
        print("  [OK] stop() matou o processo e marcou o job 'parado'")
    finally:
        config.RUN_EXPERIMENTS = original
        try:
            os.remove(caminho)
        except OSError:
            pass


if __name__ == "__main__":
    testes = [test_job_conclui_e_captura_stdout, test_stop_mata_job_em_curso]
    falhas = 0
    for t in testes:
        print(f"=== {t.__name__} ===")
        try:
            t()
        except AssertionError as e:
            falhas += 1
            print(f"  [FALHA] {e}")

    print("\n" + "=" * 40)
    if falhas == 0:
        print(f">>> MECANISMO DO DASHBOARD OK ({len(testes)}/{len(testes)})")
        sys.exit(0)
    else:
        print(f">>> {falhas} FALHA(S)")
        sys.exit(1)
