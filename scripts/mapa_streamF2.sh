#!/bin/bash
# F2 do MAPA GRANDE — treino NATIVO no 8.º cenário. Corre no servidor, em ~/swarm-mapa.
# Pré-registo: docs/PRE_REGISTO_MAPA_GRANDE.md (secções 2 e 3). Padrão mega_stream*:
# retry com --resume, arquivo por fase, config reposto no fim.
#
# ⚠️ SÓ DEPOIS DO MEGA-TREINO FECHAR (~3 ago). Enquanto megaA/megaB estiverem vivos
#    isto seria uma 3.ª stream pesada e atrasava duas campanhas de um mês.
#    Verificar antes:  scripts/servidor.sh   (sem sessões megaA/megaB = via livre)
#
# ⚠️ UM DIRETÓRIO POR STREAM — não é detalhe de arrumação. Dois streams no mesmo
#    diretório escrevem os MESMOS CSV (`results/logs/gnn_3d_training_*.csv`) e as
#    mesmas sentinelas (`_campanha_concluida.txt`, que a função `correr` apaga à
#    entrada): o segundo a arrancar corrompe o primeiro, ou o retry dispara em
#    falso e o `arquivar` leva ficheiros do vizinho. É a mesma razão pela qual os
#    três controlos do F1 correram em ~/swarm-mapa-c{1,2,3} (30 jul).
#
#     ~/swarm-mapa/scripts/mapa_streamF2.sh preparar    # cria ~/swarm-mapa-f2{g,r,l}
#     tmux new-session -d -s mapaF2g '~/swarm-mapa-f2g/scripts/mapa_streamF2.sh gnn'
#     tmux new-session -d -s mapaF2r '~/swarm-mapa-f2r/scripts/mapa_streamF2.sh grad'
#
# e um TERCEIRO só quando o `grad` fechar (~8 ago) — nunca em paralelo com os dois:
#     tmux new-session -d -s mapaF2l '~/swarm-mapa-f2l/scripts/mapa_streamF2.sh longo'
#
#   gnn   : GNN  21 runs x 780 min  = 273 h  (~11,4 dias)  <- o gargalo
#   grad  : PPO  21 runs x 192 min + SAC 21 runs x 192 min = 134 h  (~5,6 dias)
#   longo : GNN   3 runs x 2340 min = 117 h  (~4,9 dias)   EXPLORATÓRIO
#
# Orçamento PRÉ-REGISTADO, não negociável a meio: 780 min/run para o GNN e 192 para
# PPO/SAC (a proporção 4:1 de todas as campanhas anteriores). O que o justifica está
# na secção 2 do pré-registo: a 195 min o GNN faria 3,4 gerações no mapa grande, e
# "o evolutivo falha no mapa composto" seria artefacto do orçamento — o mesmo erro
# que a tese já apanhou uma vez com a fitness.
#
# 21 runs (era 7): emenda 19, de 2 ago, escrita com ZERO dados de F2. O acréscimo
# de máquina — 15 dias livres entre o fim do megaB e o hard stop de 22 ago — vai
# todo para RUNS e nenhum para minutos por run, porque são os minutos que igualam
# as gerações às campanhas fechadas. M1-M3 e a regra de decisão ficam como estavam;
# M2 continua DESCRITIVO (subir o n e converter um descritivo em teste seria
# escolher o teste com o n na mão).
#
# O modo `longo` é a emenda 20: 3× as gerações, n=3, para responder de antemão a
# "faltou treino" se o F2 der zero. É EXPLORATÓRIO — não entra em M1-M3 e não se
# compara com os braços principais (orçamentos diferentes não são comparáveis).
#
# Seeds 1..N: o run_experiments passa --seed <nº do run>, por isso 21 runs = seeds 1-21.
# O cenário é posto no config pelo próprio run_experiments (set_scenario), não por sed.
#
# Se falhar até 22 ago, a resposta já está pré-decidida (secção 5 do pré-registo):
# cortar para 2 algoritmos e DECLARÁ-LO. Nunca menos de 7 runs.
set -u

BASE=~/swarm-mapa
PY=~/run7d_mlp/.venv/bin/python    # ~/swarm-mapa não tem venv própria; o
                                   # run_experiments propaga o sys.executable aos treinos
CFG=configs/foraging.yaml
LOGDIR=results/logs

MODO="${1:-}"

# --- preparar: um diretório de trabalho por stream ---------------------------
# Mesma mecânica dos controlos do F1, incluindo a guarda do simulador: um
# diretório que já exista com OUTRO `swarm_env_3d.py` não se reutiliza. Foi essa
# a armadilha de 29 jul — as cópias tinham o simulador em que os agentes voavam
# por cima das paredes, e reutilizá-las teria repetido o F1 anulado.
if [ "$MODO" = "preparar" ]; then
    for m in g r l; do
        d="$HOME/swarm-mapa-f2$m"
        if [ -d "$d" ] && ! cmp -s "$BASE/src/environment/swarm_env_3d.py" \
                                   "$d/src/environment/swarm_env_3d.py"; then
            echo "[preparar] ⚠️  $d tem um SIMULADOR DIFERENTE do de $BASE."
            echo "[preparar]     Arquiva-o (mv $d ~/ANULADO_\$(date +%d%b)_$(basename "$d"))"
            echo "[preparar]     e volta a correr — a cópia é recriada do BASE."
            exit 3
        fi
        if [ -d "$d" ]; then
            echo "[preparar] $d já existe, com o mesmo simulador — não toco"
        else
            cp -rp "$BASE" "$d"
            # O F2 treina de raiz: nada do F1 (nem CSV, nem campeões da 7d) entra
            # aqui. Ficam de fora para o `arquivar` não os apanhar como se fossem
            # desta campanha.
            rm -rf "$d"/results/evaluation "$d"/results/models \
                   "$d"/results/models_ppo "$d"/results/models_sac \
                   "$d"/results/logs "$d"/results/models_7d
            mkdir -p "$d"/results/logs "$d"/results/evaluation
            echo "[preparar] $d criado ($(du -sh "$d" | cut -f1))"
        fi
    done
    exit 0
fi

case "$MODO" in
    gnn|grad|longo) ;;
    *) echo "uso: $0 {preparar|gnn|grad|longo}" >&2; exit 2 ;;
esac

# O diretório é o do PRÓPRIO script — `~/swarm-mapa-f2r/scripts/...` corre em
# ~/swarm-mapa-f2r e não há hipótese de dois streams irem ao mesmo CSV.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_ABS="$(cd "$BASE" 2>/dev/null && pwd || true)"
if [ -n "$BASE_ABS" ] && [ "$RAIZ" = "$BASE_ABS" ]; then
    echo "[F2] ⛔ Estás a correr a partir de $BASE, que é a cópia-mãe." >&2
    echo "[F2]    Corre '$0 preparar' e lança de ~/swarm-mapa-f2{g,r,l}." >&2
    exit 2
fi

# Emenda 19 (2 ago): 21 runs nos braços principais. RUNS_LONGO=3 é o exploratório
# da emenda 20 — n pequeno de propósito, não é uma célula da comparação.
RUNS=${F2_RUNS:-21}
RUNS_LONGO=${F2_RUNS_LONGO:-3}
MIN_GNN=${F2_MIN_GNN:-780}
MIN_GRAD=${F2_MIN_GRAD:-192}
MIN_LONGO=${F2_MIN_LONGO:-2340}

cd "$RAIZ" || { echo "[F2] sem $RAIZ"; exit 2; }
[ -x "$PY" ] || { echo "[F2] sem python em $PY"; exit 2; }
ulimit -n 65536

TAG="mapaF2${MODO}"
MASTER=~/mapa_F2${MODO}_master.log

registar() { echo "[$TAG] $*" | tee -a "$MASTER"; }

correr() {  # correr <log> <args...> — fase nova + até 2 retries com --resume
  local log=$1; shift
  rm -f "$LOGDIR/_campanha_concluida.txt" "$LOGDIR/_sessao_treino.txt"
  "$PY" scripts/run_experiments.py "$@" 2>&1 | tee -a "$log"
  for t in 1 2; do
    [ -f "$LOGDIR/_campanha_concluida.txt" ] && return 0
    registar "retry $t — sem sentinela, relançar com --resume ($(date))"
    sleep 60
    "$PY" scripts/run_experiments.py "$@" --resume 2>&1 | tee -a "$log"
  done
  [ -f "$LOGDIR/_campanha_concluida.txt" ]
}

arquivar() {  # arquivar <pasta> <log>
  mkdir -p ~/"$1"
  cp -r results/evaluation results/models results/models_ppo results/models_sac \
        results/logs "$2" ~/"$1"/ 2>/dev/null
  registar "arquivado em ~/$1"
}

# Aviso ruidoso, não bloqueio: se o mega-treino ainda estiver vivo, o utilizador
# tem de o ver no log. Bloquear seria pior — obrigaria a editar o script para
# relançar depois, e é assim que se lança com os parâmetros errados.
if tmux ls 2>/dev/null | grep -qE '^mega[AB]:'; then
    registar "⚠️  ATENÇÃO: megaA/megaB AINDA A CORRER. O pré-registo manda esperar."
    registar "⚠️  Vou arrancar na mesma daqui a 120 s — Ctrl+C (ou tmux kill-session) para abortar."
    sleep 120
fi

registar "ARRANQUE $(date -u '+%a %b %d %H:%M:%S %Z %Y') — modo $MODO"

if [ "$MODO" = "gnn" ]; then
    registar "FASE 1/1: GNN mapa_grande @${MIN_GNN}x${RUNS} ($(date))"
    correr ~/mapa_F2_gnn.log --algo GNN --runs "$RUNS" --time-gnn "$MIN_GNN" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_gnn ~/mapa_F2_gnn.log
elif [ "$MODO" = "grad" ]; then
    registar "FASE 1/2: PPO mapa_grande @${MIN_GRAD}x${RUNS} ($(date))"
    correr ~/mapa_F2_ppo.log --algo PPO --runs "$RUNS" --time-ppo "$MIN_GRAD" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_ppo ~/mapa_F2_ppo.log

    registar "FASE 2/2: SAC mapa_grande @${MIN_GRAD}x${RUNS} ($(date))"
    correr ~/mapa_F2_sac.log --algo SAC --runs "$RUNS" --time "$MIN_GRAD" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_sac ~/mapa_F2_sac.log
else
    # EXPLORATÓRIO (emenda 20). Não entra em M1-M3 e não se compara com os braços
    # principais: 2340 min são 3× as gerações do braço GNN, e orçamentos
    # diferentes não são comparáveis. Só arranca depois do `grad` largar a
    # máquina — três streams pesados saturam os 64 vCPU e atrasam os que contam.
    if tmux ls 2>/dev/null | grep -qE '^mapaF2r:'; then
        registar "⛔ o stream dos gradientes (mapaF2r) ainda corre — o longo espera."
        registar "   Relança quando ele fechar (~8 ago). A sair sem tocar em nada."
        exit 4
    fi
    registar "FASE 1/1 EXPLORATÓRIA: GNN mapa_grande @${MIN_LONGO}x${RUNS_LONGO} ($(date))"
    correr ~/mapa_F2_longo.log --algo GNN --runs "$RUNS_LONGO" --time-gnn "$MIN_LONGO" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_longo ~/mapa_F2_longo.log
fi

# Repor o cenário do config: o set_scenario deixa-o em mapa_grande e o próximo a
# entrar aqui (uma avaliação, um smoke) herdava-o em silêncio.
sed -i 's/^  classic_scenario: .*/  classic_scenario: u_wall/' "$CFG"
registar "CONCLUÍDO $(date -u '+%a %b %d %H:%M:%S %Z %Y') — config reposto em u_wall"
registar "A SEGUIR: $PY scripts/pos_campanha.py  (armadilha nº9) e a análise M1-M3"
