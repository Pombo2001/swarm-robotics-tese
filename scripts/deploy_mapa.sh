#!/usr/bin/env bash
# Envia o código do MAPA GRANDE para um diretório ISOLADO no servidor do ISCTE.
#
# Porquê um diretório novo (~/swarm-mapa/) e não o ~/swarm-robotics-tese/:
# esse está a ser usado pelo megaA, que reescreve o configs/foraging.yaml por
# `sed` a cada fase e recarrega o src/ a cada run novo. Substituir ficheiros lá
# a meio de uma campanha faz os runs seguintes correrem com um simulador
# diferente dos anteriores — dentro da mesma campanha. É o padrão que o
# ~/swarm-novelty já seguiu.
#
# NÃO cria um .venv novo: reutiliza o de ~/swarm-robotics-tese (só leitura, as
# dependências são as mesmas). Os scripts resolvem os caminhos a partir do
# próprio ficheiro, por isso correr de ~/swarm-mapa usa o código de ~/swarm-mapa.
#
# Uso:
#     scripts/deploy_mapa.sh            # envia e verifica
#     scripts/deploy_mapa.sh --verificar-so   # só verifica o que já lá está
#
# Requisitos: VPN do ISCTE ligada + PuTTY (plink e pscp).
set -euo pipefail

HOST=SERVIDOR_DE_TREINO
USER=goncalo
HOSTKEY=SHA256:HOSTKEY_REMOVIDA
PLINK="/c/Program Files/PuTTY/plink.exe"
PSCP="/c/Program Files/PuTTY/pscp.exe"
FICHEIRO_PASS="$HOME/.swarm_ssh_pass"
DEST=swarm-mapa

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PASS="${SWARM_SSH_PASS:-}"
[[ -z "$PASS" && -f "$FICHEIRO_PASS" ]] && PASS=$(<"$FICHEIRO_PASS")
if [[ -z "$PASS" ]]; then
    echo "Sem password (ver ~/.swarm_ssh_pass)." >&2
    exit 2
fi

remoto() { "$PLINK" -ssh -batch -hostkey "$HOSTKEY" -pw "$PASS" "$USER@$HOST" "$1"; }
enviar() { "$PSCP" -p -q -batch -hostkey "$HOSTKEY" -pw "$PASS" "$1" "$USER@$HOST:$2"; }

# Os ficheiros que o mapa precisa. Deliberadamente MÍNIMO: não se envia o
# repositório inteiro para o servidor não ficar com duas cópias divergentes de
# tudo. Se um treino reclamar de um import em falta, acrescenta-se aqui.
FICHEIROS=(
    "src/scenarios.py                  src"
    "src/environment/swarm_env_3d.py   src/environment"
    "src/agents/gnn_agent_3d.py        src/agents"
    "src/training/evo_trainer_3d.py    src/training"
    "src/training/train_ppo_3d.py      src/training"
    "src/training/train_sac_3d.py      src/training"
    "scripts/run_experiments.py        scripts"
    "scripts/eval_by_run.py            scripts"
    "scripts/eval_suite.py             scripts"
    "scripts/pos_campanha.py           scripts"
    "configs/foraging.yaml             configs"
    "tests/test_mapa_grande.py         tests"
    "requirements.txt                  ."
)

if [[ "${1:-}" != "--verificar-so" ]]; then
    echo "[1/3] a criar a estrutura em ~/$DEST/"
    remoto "mkdir -p ~/$DEST/{src/environment,src/agents,src/training,scripts,configs,tests,results,logs}"
    # __init__.py: o src/ do projeto tem pacotes; sem eles os imports falham.
    remoto "cd ~/$DEST && touch src/__init__.py src/environment/__init__.py src/agents/__init__.py src/training/__init__.py scripts/__init__.py"

    echo "[2/3] a enviar ${#FICHEIROS[@]} ficheiros"
    for par in "${FICHEIROS[@]}"; do
        read -r origem destino <<<"$par"
        printf '      %-38s -> %s\n' "$origem" "$destino"
        # caminho ABSOLUTO: o pscp não expande o ~ do lado remoto
        enviar "$origem" "/home/$USER/$DEST/$destino/"
    done
fi

echo "[3/3] verificação no servidor"
remoto "cd ~/$DEST && \
  echo '--- o mapa existe no codigo de la? ---' && \
  grep -c mapa_grande src/scenarios.py src/environment/swarm_env_3d.py configs/foraging.yaml && \
  echo '--- datas (tem de ser de hoje) ---' && \
  ls -l --time-style=+%d-%b-%H:%M src/scenarios.py configs/foraging.yaml | awk '{print \$6, \$7}' && \
  echo '--- o config esta no cenario certo? ---' && \
  grep -E '^  classic_scenario' configs/foraging.yaml && \
  echo '--- nao mexeu no dir do megaA? ---' && \
  ls -l --time-style=+%d-%b ~/swarm-robotics-tese/src/scenarios.py | awk '{print \$6, \$7}'"
