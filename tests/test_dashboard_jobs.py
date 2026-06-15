"""Teste do mecanismo do dashboard F1: JobQueue + captura de stdout (PIPE).

Usa um processo DUMMY (em vez de run_experiments.py) para validar a infraestrutura
sem treinar nada nem tocar nos modelos. Verifica:
  1. o stdout do processo é capturado no buffer em tempo real;
  2. a fila corre o job e marca-o "concluído" (exit 0);
  3. stop() mata um job em curso e marca-o "parado".
"""
import os
import sys
import time
import tempfile
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import config
from dashboard.jobs import Job, JobQueue

falhas = 0

# Dummy 1: imprime 5 linhas (com flush) e sai 0.
DUMMY_OK = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
DUMMY_OK.write(
    "import sys, time\n"
    "for i in range(5):\n"
    "    print('linha de treino', i, flush=True)\n"
    "    time.sleep(0.1)\n"
    "sys.exit(0)\n"
)
DUMMY_OK.close()

# Dummy 2: corre 'para sempre' (até ser morto).
DUMMY_LONG = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
DUMMY_LONG.write(
    "import time\n"
    "while True:\n"
    "    print('a treinar...', flush=True)\n"
    "    time.sleep(0.2)\n"
)
DUMMY_LONG.close()


def _wait(cond, timeout=15.0, step=0.1):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(step)
    return False


# ── Teste 1+2: captura de stdout + fila conclui ───────────────────────────────
print("=== Teste 1/2: job corre e stdout é capturado ===")
config.RUN_EXPERIMENTS = DUMMY_OK.name   # redireciona o backend para o dummy
q = JobQueue()
job = Job(algo="PPO", scenarios=["none"], minutes=1, runs=1, eval_episodes=0)
q.add(job)
q.start()

captured = []
ok = _wait(lambda: (captured.extend(q.drain_log()), job.status in ("concluído", "falhou"))[-1])
captured.extend(q.drain_log())  # drena o resto

texto = "\n".join(captured)
if not ok:
    falhas += 1; print("  [FALHA] o job não terminou a tempo")
elif job.status != "concluído":
    falhas += 1; print(f"  [FALHA] estado esperado 'concluído', obtido '{job.status}' (código {job.exit_code})")
elif "linha de treino 0" not in texto or "linha de treino 4" not in texto:
    falhas += 1; print("  [FALHA] stdout do processo não foi capturado")
    print("  capturado:", repr(texto[:200]))
else:
    print("  [OK] job concluído (exit 0) e as 5 linhas foram capturadas em tempo real")

# ── Teste 3: stop() mata o job em curso ───────────────────────────────────────
print("=== Teste 3: stop() pára um job em curso ===")
config.RUN_EXPERIMENTS = DUMMY_LONG.name
q2 = JobQueue()
job2 = Job(algo="GNN", scenarios=["none"], minutes=99, runs=1, eval_episodes=0)
q2.add(job2)
q2.start()

started = _wait(lambda: job2.status == "a correr", timeout=10)
time.sleep(0.5)  # deixa produzir algumas linhas
q2.stop()
stopped = _wait(lambda: not q2.is_running, timeout=10)

if not started:
    falhas += 1; print("  [FALHA] o job não chegou a 'a correr'")
elif not stopped:
    falhas += 1; print("  [FALHA] a fila não parou após stop()")
elif job2.status != "parado":
    falhas += 1; print(f"  [FALHA] estado esperado 'parado', obtido '{job2.status}'")
else:
    print("  [OK] stop() matou o processo e marcou o job 'parado'")

# limpeza
for f in (DUMMY_OK.name, DUMMY_LONG.name):
    try: os.remove(f)
    except OSError: pass

print("\n" + "=" * 40)
if falhas == 0:
    print(">>> MECANISMO DO DASHBOARD OK (3/3)")
    sys.exit(0)
else:
    print(f">>> {falhas} FALHA(S)")
    sys.exit(1)
