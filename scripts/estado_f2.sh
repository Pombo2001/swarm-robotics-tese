#!/usr/bin/env bash
# Instantâneo do F2 (mapa grande) TAL COMO ESTÁ NO SERVIDOR, gravado em ficheiro.
#
# Existe porque o dashboard afirmava o estado das campanhas em texto escrito à mão
# — «arranca 3 ago», «4,75 recolhas à geração 140» — e essas frases envelhecem
# sozinhas: a 6 ago o F2 já corria há três dias, o run que dava 4,75 tinha fechado
# com 6,0 e o run seguinte estava a 0,0. Quem lê o dashboard no Pi não tem VPN nem
# forma de saber que a frase é de anteontem.
#
# A saída (results/estado_f2.json) leva SEMPRE a hora da medição, e é isso que o
# dashboard mostra ao lado dos números: não afirma o presente, afirma o que foi
# medido e quando. Correr sempre que se espreitar o servidor:
#
#     bash scripts/estado_f2.sh
#
# Requisitos: os mesmos do scripts/servidor.sh (VPN do ISCTE + PuTTY + password
# em ~/.swarm_ssh_pass).
set -euo pipefail

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SAIDA="$RAIZ/results/estado_f2.json"

# Tudo numa ligação só: cada plink custa alguns segundos e a VPN nem sempre é
# rápida. O formato é `chave<TAB>valor`, uma linha por facto — mais fácil de ler
# do que tentar produzir JSON do lado do servidor.
REMOTO='
  echo -e "hora_servidor\t$(date -u +%Y-%m-%dT%H:%MZ)"
  echo -e "carga\t$(cut -d" " -f1-3 /proc/loadavg)"
  for s in mapaF2r mapaF2g mapaF2l f2lwatch; do
    tmux has-session -t "$s" 2>/dev/null && echo -e "tmux\t$s"
  done
  # --- braço dos gradientes: um .zip por run de PPO concluído -----------------
  echo -e "grad_ppo_runs\t$(ls ~/swarm-mapa-f2r/results/models_ppo/*run*.zip 2>/dev/null | wc -l)"
  echo -e "grad_sac_runs\t$(ls ~/swarm-mapa-f2r/results/models_sac/*run*.zip 2>/dev/null | wc -l)"
  echo -e "grad_fase\t$(grep -o "FASE [0-9]*/[0-9]*: [A-Z]*" ~/mapa_F2grad_master.log 2>/dev/null | tail -1)"
  echo -e "grad_runs_previstos\t$(grep -o "@192x[0-9]*" ~/mapa_F2grad_master.log 2>/dev/null | tail -1 | tr -d "@" | cut -dx -f2)"
  # --- braço do GNN: um CSV por run, e o melhor best_task_food de cada --------
  echo -e "gnn_runs_previstos\t$(grep -o "@780x[0-9]*" ~/mapa_F2gnn_master.log 2>/dev/null | tail -1 | tr -d "@" | cut -dx -f2)"
  for f in ~/swarm-mapa-f2g/results/logs/gnn_3d_training_mapa_grande_run*.csv; do
    [ -e "$f" ] || continue
    n=$(basename "$f" | sed "s/.*run//;s/\.csv//")
    # 4ª coluna = best_task_food (o cabeçalho está lá: timestep,best_fitness,
    # avg_fitness,best_task_food,time). A última linha diz a geração.
    comida=$(awk -F, "NR>1{if(\$4>m)m=\$4}END{printf \"%.2f\", m+0}" "$f")
    geracoes=$(($(wc -l < "$f") - 1))
    echo -e "gnn_run\t$n|$comida|$geracoes"
  done
'

# O bruto vai por FICHEIRO, não por heredoc: com dois heredocs no mesmo comando
# (`<<'PY'` para o script e `<<<"$bruto"` para os dados) o segundo ganha o stdin e
# o Python recebe os dados como se fossem o programa.
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
bash "$RAIZ/scripts/servidor.sh" "$REMOTO" > "$TMP"

# `python3` não existe no Git Bash do Windows, onde este script corre.
PY_BIN=$(command -v python3 || command -v python)

"$PY_BIN" - "$SAIDA" "$TMP" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone

destino, origem = sys.argv[1], sys.argv[2]
factos, tmux, runs_gnn = {}, [], []
with open(origem, encoding="utf-8", errors="replace") as fh_in:
    bruto = fh_in.read()
for linha in bruto.splitlines():
    if "\t" not in linha:
        continue
    chave, _, valor = linha.partition("\t")
    valor = valor.strip()
    if chave == "tmux":
        tmux.append(valor)
    elif chave == "gnn_run":
        n, comida, gers = valor.split("|")
        runs_gnn.append({"run": int(n), "recolhas": float(comida),
                         "geracoes": int(gers)})
    else:
        factos[chave] = valor

runs_gnn.sort(key=lambda r: r["run"])
# O run com o índice mais alto é o que está a correr (os anteriores fecharam).
for r in runs_gnn:
    r["a_correr"] = (r["run"] == runs_gnn[-1]["run"]) if runs_gnn else False

def inteiro(chave):
    m = re.search(r"\d+", factos.get(chave, ""))
    return int(m.group()) if m else None

estado = {
    "medido_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "hora_servidor": factos.get("hora_servidor"),
    "carga": factos.get("carga"),
    "tmux_vivos": tmux,
    "grad": {
        "fase": factos.get("grad_fase"),
        "runs_previstos": inteiro("grad_runs_previstos"),
        "ppo_runs_concluidos": inteiro("grad_ppo_runs"),
        "sac_runs_concluidos": inteiro("grad_sac_runs"),
    },
    "gnn": {
        "runs_previstos": inteiro("gnn_runs_previstos"),
        "runs": runs_gnn,
        "runs_fechados": [r for r in runs_gnn if not r["a_correr"]],
    },
    "exploratorio_armado": "f2lwatch" in tmux,
}
estado["gnn"]["fechados_com_recolha"] = sum(
    1 for r in estado["gnn"]["runs_fechados"] if r["recolhas"] > 0)
estado["gnn"]["fechados"] = len(estado["gnn"]["runs_fechados"])

with open(destino, "w", encoding="utf-8") as fh:
    json.dump(estado, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"[OK] {destino}")
print(f"  medido {estado['medido_utc']} · tmux: {', '.join(tmux) or 'nenhum'}")
print(f"  grad: PPO {estado['grad']['ppo_runs_concluidos']}"
      f"/{estado['grad']['runs_previstos']} runs, SAC "
      f"{estado['grad']['sac_runs_concluidos']}")
print(f"  GNN: {estado['gnn']['fechados']} runs fechados, "
      f"{estado['gnn']['fechados_com_recolha']} com recolha")
PY
