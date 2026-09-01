#!/bin/bash
# F2 do MAPA GRANDE — treino NATIVO no 8.º cenário. Corre no servidor, em
# ~/swarm-mapa, com o padrão dos mega_stream*: retry com --resume, arquivo por
# fase, config reposto no fim. Pré-registo: docs/PRE_REGISTO_MAPA_GRANDE.md
# (secções 2 e 3).
#
# UM DIRETÓRIO POR STREAM, e não por arrumação: dois streams no mesmo diretório
# escrevem os MESMOS CSV (`results/logs/gnn_3d_training_*.csv`) e as mesmas
# sentinelas (`_campanha_concluida.txt`, que a função `correr` apaga à entrada).
# O segundo a arrancar corrompe o primeiro, ou o retry dispara em falso e o
# `arquivar` leva ficheiros do vizinho.
#
#     ~/swarm-mapa/scripts/mapa_streamF2.sh preparar    # cria ~/swarm-mapa-f2{g,r,l}
#     tmux new-session -d -s mapaF2g '~/swarm-mapa-f2g/scripts/mapa_streamF2.sh gnn'
#     tmux new-session -d -s mapaF2r '~/swarm-mapa-f2r/scripts/mapa_streamF2.sh grad'
#     tmux new-session -d -s mapaF2l '~/swarm-mapa-f2l/scripts/mapa_streamF2.sh longo'
#
#   gnn   : GNN  21 runs x 780 min  = 273 h  (~11,4 dias)  <- o gargalo
#   grad  : PPO  21 runs x 192 min + SAC 21 runs x 192 min = 134 h  (~5,6 dias)
#   longo : GNN   3 runs x 2340 min = 117 h  (~4,9 dias)   EXPLORATÓRIO
#
# O `longo` só arranca quando o `grad` largar a máquina: três streams pesados
# saturam os 64 vCPU e atrasam os que contam.
#
# Orçamento PRÉ-REGISTADO, não negociável a meio: 780 min/run para o GNN e 192
# para PPO/SAC (a proporção 4:1 de todas as campanhas anteriores). A 195 min o
# GNN faria 3,4 gerações no mapa grande, e «o evolutivo falha no mapa composto»
# seria artefacto do orçamento. O acréscimo de máquina foi todo para RUNS e
# nenhum para minutos por run, porque são os minutos que igualam as gerações às
# campanhas fechadas.
#
# O modo `longo` dá 3x as gerações com n=3, para responder de antemão a «faltou
# treino» se o F2 der zero. É EXPLORATÓRIO: não entra em M1-M3 e não se compara
# com os braços principais, porque orçamentos diferentes não são comparáveis.
#
# Seeds 1..N: o run_experiments passa --seed <nº do run>, por isso 21 runs =
# seeds 1-21. O cenário é posto no config pelo próprio run_experiments
# (set_scenario), não por sed.
set -u

BASE=~/swarm-mapa
PY=~/run7d_mlp/.venv/bin/python    # ~/swarm-mapa não tem venv própria; o
                                   # run_experiments propaga o sys.executable aos treinos
CFG=configs/foraging.yaml
LOGDIR=results/logs

MODO="${1:-}"

# preparar: um diretório de trabalho por stream
# Mesma mecânica dos controlos do F1, incluindo a guarda do simulador: um
# diretório que já exista com OUTRO `swarm_env_3d.py` não se reutiliza —
# reutilizá-lo repetiria a campanha com a física antiga.
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

# 21 runs nos braços principais; RUNS_LONGO=3 é o exploratório — n pequeno de
# propósito, não é uma célula da comparação.
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

# A CONFIGURAÇÃO DO BRAÇO, ESCRITA E VERIFICADA
# O trainer herda o que estiver no config da cópia. Sem esta função, uma cópia
# sem a secção `novelty` cai nos defaults (weight=0, adaptive=false) e treina o
# objetivo puro em vez do braço pré-registado, em silêncio.
#
# Escreve-se e RELÊ-SE: se o que ficou no ficheiro não for o que se pediu,
# aborta. Um `sed` que não encontra a chave não falha — limita-se a não fazer
# nada, e é assim que se lança com os parâmetros errados.
config_novelty() {   # config_novelty <weight> <adaptive>
    local w="$1" adap="$2"
    # As chaves da ablação saem sempre: os defaults do trainer (sustain=10,
    # decay=0,98) são os que o pré-registo declara, e uma sobra de outra
    # campanha mudava o braço sem aparecer em lado nenhum.
    sed -i '/^  novelty_decay:/d; /^  novelty_sustain_gens:/d' "$CFG"
    for chave in novelty_weight novelty_adaptive; do
        local valor; [ "$chave" = novelty_weight ] && valor="$w" || valor="$adap"
        if grep -qE "^  $chave:" "$CFG"; then
            sed -i "s/^  $chave: .*/  $chave: $valor/" "$CFG"
        else
            # A secção pode não ter a chave: acrescenta-se debaixo de
            # `evolution:`, que é onde o evo_trainer a procura.
            sed -i "/^evolution:/a\\  $chave: $valor" "$CFG"
        fi
    done
    local lido_w lido_a
    lido_w=$(grep -E '^  novelty_weight:' "$CFG" | awk '{print $2}')
    lido_a=$(grep -E '^  novelty_adaptive:' "$CFG" | awk '{print $2}')
    registar "braço: novelty_weight=$lido_w novelty_adaptive=$lido_a (pedido: $w/$adap)"
    if [ "$lido_w" != "$w" ] || [ "$lido_a" != "$adap" ]; then
        registar "⛔ o config NÃO ficou com o braço pedido — a abortar sem treinar."
        exit 5
    fi
}

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
    # Secção 2 do pré-registo: o braço GNN é o ADAPTATIVO (w₀=0,5), não o
    # objetivo puro — «a QI6 mostrou que o adaptativo domina o objetivo».
    config_novelty 0.5 true
    registar "FASE 1/1: GNN ADAPTATIVO mapa_grande @${MIN_GNN}x${RUNS} ($(date))"
    correr ~/mapa_F2_gnn.log --algo GNN --runs "$RUNS" --time-gnn "$MIN_GNN" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_gnn ~/mapa_F2_gnn.log
elif [ "$MODO" = "grad" ]; then
    # PPO e SAC não usam novidade: a chave fica explicitamente a zero para o log
    # do arranque dizer qual foi o braço, em vez de o deixar implícito.
    config_novelty 0.0 false
    registar "FASE 1/2: PPO mapa_grande @${MIN_GRAD}x${RUNS} ($(date))"
    correr ~/mapa_F2_ppo.log --algo PPO --runs "$RUNS" --time-ppo "$MIN_GRAD" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_ppo ~/mapa_F2_ppo.log

    registar "FASE 2/2: SAC mapa_grande @${MIN_GRAD}x${RUNS} ($(date))"
    correr ~/mapa_F2_sac.log --algo SAC --runs "$RUNS" --time "$MIN_GRAD" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_sac ~/mapa_F2_sac.log
else
    # EXPLORATÓRIO: não entra em M1-M3 nem se compara com os braços principais
    # (2340 min são 3x as gerações do braço GNN, e orçamentos diferentes não são
    # comparáveis). Só arranca depois de o `grad` largar a máquina.
    if tmux ls 2>/dev/null | grep -qE '^mapaF2r:'; then
        registar "⛔ o stream dos gradientes (mapaF2r) ainda corre — o longo espera."
        registar "   Relança quando ele fechar (~8 ago). A sair sem tocar em nada."
        exit 4
    fi
    # O exploratório é o MESMO braço com mais orçamento — só assim responde a
    # "faltou treino". Com outra configuração responderia a outra pergunta.
    config_novelty 0.5 true
    registar "FASE 1/1 EXPLORATÓRIA: GNN ADAPTATIVO mapa_grande @${MIN_LONGO}x${RUNS_LONGO} ($(date))"
    correr ~/mapa_F2_longo.log --algo GNN --runs "$RUNS_LONGO" --time-gnn "$MIN_LONGO" \
           --scenarios mapa_grande --eval-episodes 20
    arquivar mapa_F2_longo ~/mapa_F2_longo.log
fi

# Repor o cenário do config: o set_scenario deixa-o em mapa_grande e o próximo a
# entrar aqui (uma avaliação, um smoke) herdava-o em silêncio.
sed -i 's/^  classic_scenario: .*/  classic_scenario: u_wall/' "$CFG"
registar "CONCLUÍDO $(date -u '+%a %b %d %H:%M:%S %Z %Y') — config reposto em u_wall"
registar "A SEGUIR: $PY scripts/pos_campanha.py  (armadilha nº9) e a análise M1-M3"
