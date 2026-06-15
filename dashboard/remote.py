"""Ligação ao servidor de treino ISCTE (SSH/SCP via PuTTY).

Usa plink/pscp (já instalados) com a host key conhecida — como no procedimento manual
documentado em PLANO_DE_ATAQUE.md secção 4. Requer a VPN do ISCTE ligada.

SEGURANÇA: a password NUNCA é guardada em disco nem em log — é passada em runtime
e vive só na memória da sessão do browser. (É passada na linha de comando do plink,
visível na lista de processos local; aceitável num launcher de uso pessoal.)
"""
import os
import subprocess

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
    "echo @@PROC; echo evo=$(pgrep -fc evo_trainer_3d) ppo=$(pgrep -fc train_ppo) "
    "sac=$(pgrep -fc train_sac) runexp=$(pgrep -fc run_experiments); "
    f"cd {REMOTE_DIR} 2>/dev/null; "
    "echo @@GNN; tail -n 2 results/logs/gnn_3d_training.csv 2>/dev/null || echo '(sem csv)'; "
    "echo @@SESS; ls -t results/graficos_tese/ 2>/dev/null | head -1 || echo '(nenhuma)'; "
    "echo @@LOG; tail -n 12 treino_24h.log 2>/dev/null || echo '(sem treino_24h.log)'"
)


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
    return {
        "ok": True,
        "host": g("HOST"), "uptime": g("UP"), "tmux": g("TMUX"),
        "proc": g("PROC"), "gnn": g("GNN"), "sessao": g("SESS"), "log": g("LOG"),
    }


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
