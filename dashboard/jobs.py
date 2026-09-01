"""Fila de trabalhos de treino + execução de processos com output capturado.

Diferença-chave face ao launcher antigo: os treinos já NÃO abrem consolas Windows
soltas (CREATE_NEW_CONSOLE). Cada job corre com stdout canalizado (PIPE) e as suas
linhas vão para um buffer thread-safe que a UI drena e mostra na consola integrada.

O backend continua a ser scripts/run_experiments.py (treina + avalia + gera gráficos
numa só invocação). Este módulo só constrói os argumentos e orquestra a sequência.
"""
import sys
import subprocess
import threading
import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import config

# No Windows, evita abrir uma janela de consola para o subprocesso.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_id_counter = itertools.count(1)


@dataclass
class Job:
    """Um trabalho de treino = uma invocação de run_experiments.py."""
    algo: str                 # "Todos" | "GNN" | "PPO" | "SAC"
    scenarios: list           # chaves de cenário (config.SCENARIO_KEYS)
    minutes: int              # minutos por run
    runs: int                 # nº de runs por cenário
    eval_episodes: int = 20   # 0 = não avaliar no fim
    id: int = field(default_factory=lambda: next(_id_counter))
    status: str = "em fila"   # "em fila" | "a correr" | "concluído" | "falhou" | "parado"
    exit_code: Optional[int] = None

    def label(self) -> str:
        cen = "todos" if len(self.scenarios) == len(config.SCENARIO_KEYS) else \
              ", ".join(self.scenarios)
        return f"#{self.id}  {self.algo} × [{cen}]  ·  {self.runs}×{self.minutes}min"

    def build_args(self) -> list:
        args = ["--runs", str(self.runs), "--time", str(self.minutes)]
        if self.algo != "Todos":
            args += ["--algo", self.algo]
        args += ["--scenarios", ",".join(self.scenarios)]
        args += ["--eval-episodes", str(self.eval_episodes)]
        return args


class JobQueue:
    """Corre os jobs em fila, um de cada vez, capturando o stdout para um buffer."""

    def __init__(self):
        self.jobs: list[Job] = []
        self._log = deque(maxlen=5000)        # buffer de linhas da consola
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False                 # a fila está ativa?
        self._stop_requested = False
        # callback opcional avisado quando o estado de um job muda (para refrescar a UI)
        self.on_change: Optional[Callable] = None

    # API pública
    def add(self, job: Job):
        self.jobs.append(job)
        self._notify()

    def remove(self, job_id: int):
        # só remove jobs que ainda não correram
        self.jobs = [j for j in self.jobs if not (j.id == job_id and j.status == "em fila")]
        self._notify()

    def clear_finished(self):
        self.jobs = [j for j in self.jobs if j.status in ("em fila", "a correr")]
        self._notify()

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """Arranca a fila (corre os jobs 'em fila' sequencialmente) numa thread."""
        if self._running:
            return
        if not any(j.status == "em fila" for j in self.jobs):
            self._emit("[fila] Nenhum job em fila para correr.")
            return
        self._running = True
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Pára a fila e mata o processo atual."""
        self._stop_requested = True
        p = self._proc
        if p and p.poll() is None:
            self._emit("[fila] A parar o treino atual…")
            try:
                p.terminate()
            except Exception:
                pass

    def drain_log(self) -> list:
        """Devolve e limpa as linhas acumuladas (a UI chama isto periodicamente)."""
        with self._lock:
            lines = list(self._log)
            self._log.clear()
        return lines

    # Interno
    def _run_loop(self):
        # Procura sempre o próximo 'em fila' na lista ATUAL (não num snapshot): assim
        # add/remove/clear durante a corrida são respeitados (a lista é reatribuída).
        while not self._stop_requested:
            job = next((j for j in list(self.jobs) if j.status == "em fila"), None)
            if job is None:
                break
            self._run_job(job)
        self._running = False
        self._proc = None
        self._emit("[fila] Fila terminada.")
        self._notify()

    def _run_job(self, job: Job):
        job.status = "a correr"
        self._notify()
        cmd = [sys.executable, "-u", config.RUN_EXPERIMENTS] + job.build_args()
        self._emit(f"\n[fila] A iniciar {job.label()}")
        self._emit(f"[cmd] {' '.join(cmd)}")
        try:
            self._proc = subprocess.Popen(
                cmd, cwd=config.BASE_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
                creationflags=_NO_WINDOW,
            )
        except Exception as e:
            job.status = "falhou"
            self._emit(f"[erro] Não foi possível lançar: {e}")
            self._notify()
            return

        for line in self._proc.stdout:
            self._emit(line.rstrip("\n"))
        code = self._proc.wait()
        job.exit_code = code
        if self._stop_requested:
            job.status = "parado"
        elif code == 0:
            job.status = "concluído"
        else:
            job.status = "falhou"
        self._emit(f"[fila] {job.label()} → {job.status} (código {code})")
        self._notify()

    def _emit(self, line: str):
        with self._lock:
            self._log.append(line)

    def _notify(self):
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass
