"""Ligação ao servidor de treino ISCTE (SSH/SCP via PuTTY).

Usa plink/pscp (já instalados) com a host key conhecida — como no procedimento manual
documentado em docs/PLANO_DE_ATAQUE.md secção 4. Requer a VPN do ISCTE ligada.

SEGURANÇA: a password NUNCA é guardada em disco nem em log — é passada em runtime
e vive só na memória da sessão do browser. (É passada na linha de comando do plink,
visível na lista de processos local; aceitável num launcher de uso pessoal.)
"""
import os
import subprocess
from datetime import datetime

from . import config

USER = "goncalo"
REMOTE_DIR = "/home/goncalo/swarm-robotics-tese"

# Máquinas conhecidas: label -> (ip, host key ed25519). Só a .14 tem fingerprint
# registada (a que usámos); a .26 pode ser adicionada quando tivermos a dela.
SERVERS = {
    "SERVIDOR_DE_TREINO (dellicious)": (
        "SERVIDOR_DE_TREINO", "SHA256:HOSTKEY_REMOVIDA"),
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _tool(name: str) -> str:
    """Caminho do executável PuTTY (instalado) com fallback para o PATH."""
    cand = rf"C:\Program Files\PuTTY\{name}.exe"
    return cand if os.path.isfile(cand) else name


def run_remote(ip: str, hostkey: str, password: str, command: str, timeout: int = 30):
    """Corre um comando no servidor. Devolve (returncode, stdout, stderr)."""
    cmd = [_tool("plink"), "-ssh", "-batch", "-hostkey", hostkey,
           "-pw", password, f"{USER}@{ip}", command]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", creationflags=_NO_WINDOW)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout — a VPN do ISCTE está ligada? A máquina está acessível?"
    except FileNotFoundError:
        return -1, "", "plink (PuTTY) não encontrado."


# Um único comando recolhe todo o estado, separado por marcadores @@SECÇÃO.
_STATUS_CMD = (
    "echo @@HOST; hostname; "
    "echo @@UP; uptime; "
    "echo @@TMUX; tmux ls 2>/dev/null || echo '(sem sessões tmux)'; "
    # NOTA: o truque do bracket ([e]vo...) impede que este próprio comando de
    # monitorização se conte a si mesmo. Com 'pgrep -f' a linha de comando do
    # shell que corre este script contém as palavras 'evo_trainer_3d'/'train_ppo'
    # /etc — sem o bracket, os contadores ficavam sempre >=1 e mostrava
    # "A TREINAR" para sempre, mesmo com o treino já terminado.
    "echo @@PROC; echo evo=$(pgrep -fc '[e]vo_trainer_3d') ppo=$(pgrep -fc '[t]rain_ppo') "
    "sac=$(pgrep -fc '[t]rain_sac') runexp=$(pgrep -fc '[r]un_experiments'); "
    f"cd {REMOTE_DIR} 2>/dev/null; "
    "echo @@GNN; tail -n 2 results/logs/gnn_3d_training.csv 2>/dev/null || echo '(sem csv)'; "
    "echo @@SESS; ls -t results/graficos_tese/ 2>/dev/null | head -1 || echo '(nenhuma)'; "
    # Deteta o log de treino MAIS RECENTE (treino_*.log) em vez de um nome fixo —
    # cada treino é lançado com 'tee treino_<algo>.log' diferente, por isso fixar
    # 'treino_24h.log' mostrava o log do treino anterior já terminado.
    "LOGF=$(ls -t treino_*.log 2>/dev/null | head -1); "
    "echo @@LOGNAME; echo \"${LOGF:-(nenhum)}\"; "
    # Para estimar o fim usamos fontes FIÁVEIS (não o log, que fica block-buffered):
    #  - epoch de início do tmux e hora atual do servidor (sem problemas de fuso);
    #  - _sessao_treino.txt (escrito a cada treino concluído → done/runs/algos);
    #  - nº real de cenários importado do próprio módulo run_experiments.
    "echo @@NOW; date +%s; "
    "echo @@TSTART; tmux ls -F '#{session_created}' 2>/dev/null | head -1; "
    "echo @@NSCEN; .venv/bin/python -c \"import sys;sys.path.insert(0,'scripts');"
    "from run_experiments import SCENARIOS;print(len(SCENARIOS))\" 2>/dev/null; "
    "echo @@SESSAO; cat results/logs/_sessao_treino.txt 2>/dev/null; "
    "echo @@LOG; [ -n \"$LOGF\" ] && tail -n 12 \"$LOGF\" || echo '(sem log de treino)'"
)


def _parse_sessao(sessao: str) -> tuple[int, int, list[str]]:
    """Do _sessao_treino.txt (linhas 'cenário|algo|run') extrai (done, runs, algos)."""
    done, runs, algos = 0, 0, set()
    for line in (sessao or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 3 and parts[2].strip().isdigit():
            done += 1
            runs = max(runs, int(parts[2].strip()))
            algos.add(parts[1].strip())
    return done, runs, sorted(algos)


def estimate_eta(now: str, tstart: str, nscen: str, sessao: str) -> dict | None:
    """Estima o fim do treino pelo RITMO REAL (proporcional), não por tempos teóricos.

    eta = início + tempo_decorrido × (total_treinos / treinos_concluídos).
    Robusto a tempos diferentes por algoritmo e a fusos (usa o relógio do servidor).
    Devolve None se nem o início se conseguir ler.
    """
    try:
        now_ts, start_ts = int((now or "").strip()), int((tstart or "").strip())
    except ValueError:
        return None
    done, runs, algos = _parse_sessao(sessao)
    try:
        nscen = int((nscen or "").strip())
    except ValueError:
        nscen = 0
    base = {
        "start": datetime.fromtimestamp(start_ts), "now": datetime.fromtimestamp(now_ts),
        "done": done or None, "runs": runs or None,
        "cenarios": nscen or None, "algos": algos or None,
        "eta": None, "total_treinos": None,
    }
    if done and runs and algos and nscen:
        total = nscen * runs * len(algos)
        elapsed = max(now_ts - start_ts, 1)
        eta_ts = start_ts + elapsed * total / done
        base["eta"] = datetime.fromtimestamp(eta_ts)
        base["total_treinos"] = total
    return base


def get_status(ip: str, hostkey: str, password: str) -> dict:
    """Recolhe o estado do servidor (tmux, load, processos, progresso GNN, log)."""
    code, out, err = run_remote(ip, hostkey, password, _STATUS_CMD)
    if code != 0:
        return {"ok": False, "error": (err or out).strip() or f"código {code}"}
    sections, cur = {}, None
    for line in out.splitlines():
        if line.startswith("@@"):
            cur = line[2:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    g = lambda k: "\n".join(sections.get(k, [])).strip()
    res = {
        "ok": True,
        "host": g("HOST"), "uptime": g("UP"), "tmux": g("TMUX"),
        "proc": g("PROC"), "gnn": g("GNN"), "sessao": g("SESS"),
        "logname": g("LOGNAME"), "log": g("LOG"),
    }
    res["eta"] = estimate_eta(g("NOW"), g("TSTART"), g("NSCEN"), g("SESSAO"))
    return res


def fetch_results(ip: str, hostkey: str, password: str) -> tuple[bool, str]:
    """Empacota a sessão de gráficos mais recente + avaliação/logs e traz por scp.

    Devolve (ok, texto_de_log). O ficheiro chega a out/res_servidor.tar.gz.
    """
    log = []
    pack = (
        f"cd {REMOTE_DIR} && LATEST=$(ls -t results/graficos_tese/ 2>/dev/null | head -1) && "
        "echo PASTA=$LATEST && "
        "tar czf /tmp/res.tar.gz --ignore-failed-read "
        "results/graficos_tese/$LATEST results/evaluation results/logs "
        "results/logs_ppo results/logs_sac && ls -lh /tmp/res.tar.gz"
    )
    code, out, err = run_remote(ip, hostkey, password, pack, timeout=180)
    log.append(out.strip())
    if code != 0:
        log.append(f"[erro a empacotar] {err.strip()}")
        return False, "\n".join(log)

    dest = os.path.join(config.BASE_DIR, "out", "res_servidor.tar.gz")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    cmd = [_tool("pscp"), "-batch", "-hostkey", hostkey, "-pw", password,
           f"{USER}@{ip}:/tmp/res.tar.gz", dest]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace", creationflags=_NO_WINDOW)
    except subprocess.TimeoutExpired:
        log.append("[erro] scp excedeu o tempo limite")
        return False, "\n".join(log)
    if r.returncode != 0:
        log.append(f"[erro scp] {r.stderr.strip()}")
        return False, "\n".join(log)
    log.append(f"[ok] resultados trazidos para: {dest}")
    return True, "\n".join(log)
