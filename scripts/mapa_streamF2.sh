#!/bin/bash
# F2 do MAPA GRANDE — treino NATIVO no 8.º cenário. Corre no servidor, em ~/swarm-mapa.
# Pré-registo: docs/PRE_REGISTO_MAPA_GRANDE.md (secções 2 e 3). Padrão mega_stream*:
# retry com --resume, arquivo por fase, config reposto no fim.
#
# ⚠️ SÓ DEPOIS DO MEGA-TREINO FECHAR (~3 ago). Enquanto megaA/megaB estiverem vivos
#    isto seria uma 3.ª stream pesada e atrasava duas campanhas de um mês.
#    Verificar antes:  scripts/servidor.sh   (sem sessões megaA/megaB = via livre)
#
# DOIS STREAMS, lançados ao mesmo tempo:
#     tmux new-session -d -s mapaF2g '~/swarm-mapa/scripts/mapa_streamF2.sh gnn'
#     tmux new-session -d -s mapaF2r '~/swarm-mapa/scripts/mapa_streamF2.sh grad'
#
#   gnn  : GNN  7 runs x 780 min = 91 h  (~3,8 dias)  <- o gargalo
#   grad : PPO  7 runs x 192 min + SAC 7 runs x 192 min = 45 h  (~1,9 dias)
#
# Orçamento PRÉ-REGISTADO, não negociável a meio: 780 min/run para o GNN e 192 para
# PPO/SAC (a proporção 4:1 de todas as campanhas anteriores). O que o justifica está
# na secção 2 do pré-registo: a 195 min o GNN faria 3,4 gerações no mapa grande, e
# "o evolutivo falha no mapa composto" seria artefacto do orçamento — o mesmo erro
# que a tese já apanhou uma vez com a fitness.
#
# Seeds 1-7: o run_experiments passa --seed <nº do run>, por isso 7 runs = seeds 1-7.
# O cenário é posto no config pelo próprio run_experiments (set_scenario), não por sed.
#
# Se falhar até 22 ago, a resposta já está pré-decidida (secção 5 do pré-registo):
# cortar para 2 algoritmos e DECLARÁ-LO. Nunca menos de 7 runs.
set -u

RAIZ=~/swarm-mapa
PY=~/run7d_mlp/.venv/bin/python    # ~/swarm-mapa não tem venv própria; o
                                   # run_experiments propaga o sys.executable aos treinos
CFG=configs/foraging.yaml
LOGDIR=results/logs

MODO="${1:-}"
case "$MODO" in
    gnn|grad) ;;
    *) echo "uso: $0 {gnn|grad}" >&2; exit 2 ;;
esac

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
    registar "FASE 1/1: GNN mapa_grande @780x7 ($(date))"
    correr ~/mapa_F2_gnn.log --algo GNN --runs 7 --time-gnn 780 \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_gnn ~/mapa_F2_gnn.log
else
    registar "FASE 1/2: PPO mapa_grande @192x7 ($(date))"
    correr ~/mapa_F2_ppo.log --algo PPO --runs 7 --time-ppo 192 \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_ppo ~/mapa_F2_ppo.log

    registar "FASE 2/2: SAC mapa_grande @192x7 ($(date))"
    correr ~/mapa_F2_sac.log --algo SAC --runs 7 --time 192 \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_sac ~/mapa_F2_sac.log
fi

# Repor o cenário do config: o set_scenario deixa-o em mapa_grande e o próximo a
# entrar aqui (uma avaliação, um smoke) herdava-o em silêncio.
sed -i 's/^  classic_scenario: .*/  classic_scenario: u_wall/' "$CFG"
registar "CONCLUÍDO $(date -u '+%a %b %d %H:%M:%S %Z %Y') — config reposto em u_wall"
registar "A SEGUIR: $PY scripts/pos_campanha.py  (armadilha nº9) e a análise M1-M3"
