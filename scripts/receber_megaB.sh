#!/usr/bin/env bash
# Receção do megaB — a última stream do mega-treino de 1 mês.
#
# Existe para que a chegada de uma campanha de duas semanas não dependa de
# alguém se lembrar de cinco coisas. Todas elas já correram mal uma vez:
#
#   1. dar a campanha por fechada porque o SSH não respondeu (armadilha nº7 —
#      aqui exige-se a sentinela CONCLUÍDO no master log, não a ausência do tmux);
#   2. deixar o config do `~/swarm-novelty` em `true/0.5` (a armadilha do stream
#      B: os scripts repõem no fim, mas isso é para verificar, não para confiar);
#   3. trazer por cima de dados que já cá estavam (o `trazer_do_servidor.sh`
#      aborta, mas mais vale não chegar lá);
#   4. não reparar que os 21 runs partilham UM modelo (armadilha nº8: o
#      evo_trainer sobrescrevia o `.pth` a cada run — corrigido, e é isto que o
#      confirma nos dados que chegam);
#   5. instalar sem gerar figuras, e a campanha ficar invisível no dashboard.
#
# NÃO toca nos modelos ativos (`results/models*`) — precedente de 19 jul.
#
# Uso (torre, VPN do ISCTE ligada):
#     bash scripts/receber_megaB.sh --verificar    # só diz se está pronta
#     bash scripts/receber_megaB.sh                # verifica, traz e instala
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV="$RAIZ/scripts/servidor.sh"
TRAZER="$RAIZ/scripts/trazer_do_servidor.sh"
DESTINO="$RAIZ/results/mega_1mes"
FASES=(6 7)                       # as que faltam; 1-5 já cá estão

SO_VERIFICAR=0
[ "${1:-}" = "--verificar" ] && SO_VERIFICAR=1

falhas=0
ok()  { echo "  [v] $*"; }
mal() { echo "  [X] $*"; falhas=$((falhas + 1)); }
remoto() { bash "$SRV" "$*" 2>/dev/null; }

echo "=============================================================================="
echo "RECEÇÃO DO megaB   ($(date '+%d %b %Y %H:%M'))"
echo "=============================================================================="

remoto "echo vivo" | grep -q vivo || {
    echo "  [X] servidor sem resposta — VPN do ISCTE ligada?"; exit 2; }
ok "servidor a responder"

# 1. FECHADA de verdade: a sentinela, não a ausência de tmux
fim=$(remoto "grep -c 'CONCLUÍDO' ~/mega_B_master.log 2>/dev/null" | tail -1 | tr -dc '0-9')
viva=$(remoto "tmux ls 2>/dev/null | grep -c '^megaB:'" | tail -1 | tr -dc '0-9')
if [ "${fim:-0}" -ge 1 ]; then
    ok "megaB CONCLUÍDO (sentinela no master log)"
    [ "${viva:-0}" != "0" ] && mal "…mas a sessão tmux megaB ainda existe — ver antes de trazer"
else
    mal "megaB ainda NÃO concluiu"
    remoto "tail -1 ~/mega_B_master.log"
    echo "      fase atual e progresso: bash scripts/servidor.sh"
fi

# 2. o config reposto (a armadilha do stream B)
cfg=$(remoto "grep -E 'novelty_(weight|adaptive)' ~/swarm-novelty/configs/foraging.yaml | tr -d ' \n'")
case "$cfg" in
    *novelty_adaptive:false*novelty_weight:0.0*|*novelty_weight:0.0*novelty_adaptive:false*)
        ok "config de ~/swarm-novelty reposto (0.0 / false)" ;;
    "") mal "não consegui ler o config de ~/swarm-novelty" ;;
    *)  mal "config de ~/swarm-novelty AINDA com novidade: $cfg"
        echo "      (normal enquanto corre; o mega_streamB.sh repõe no fim)" ;;
esac

# 3. as fases estão arquivadas lá
for f in "${FASES[@]}"; do
    n=$(remoto "ls ~/mega_B_fase$f/evaluation/eval_by_run.csv 2>/dev/null | wc -l" | tail -1 | tr -dc '0-9')
    if [ "${n:-0}" = "1" ]; then
        ok "~/mega_B_fase$f arquivada, com eval_by_run.csv"
    else
        mal "~/mega_B_fase$f sem eval_by_run.csv (a fase não fechou ou não arquivou)"
    fi
done

# 4. nada por cima do que já cá está
for f in "${FASES[@]}"; do
    [ -d "$DESTINO/mega_B_fase$f" ] && \
        mal "$DESTINO/mega_B_fase$f JÁ EXISTE — apaga ou renomeia antes de trazer"
done

echo "------------------------------------------------------------------------------"
if [ "$falhas" -ne 0 ]; then
    echo "$falhas verificação(ões) falharam — não trago nada."
    exit 1
fi
echo "pronta a receber."
[ "$SO_VERIFICAR" = "1" ] && { echo "(--verificar: não trouxe nada)"; exit 0; }

# ── trazer ───────────────────────────────────────────────────────────────────
echo
for f in "${FASES[@]}"; do
    echo "== fase $f =="
    mkdir -p "$DESTINO/mega_B_fase$f"
    for sub in evaluation logs models; do
        bash "$TRAZER" "/home/goncalo/mega_B_fase$f/$sub" \
                       "$DESTINO/mega_B_fase$f" >/dev/null 2>&1 \
            && echo "   $sub trazido" || echo "   $sub NÃO veio (pode não existir)"
    done
    bash "$TRAZER" "/home/goncalo/mega_B_fase$f/mega_B_fase$f.log" \
                   "$DESTINO/mega_B_fase$f/mega_B_fase$f.log" >/dev/null 2>&1 \
        && echo "   log trazido" || true
done

# ── armadilha nº8: os runs têm modelos DISTINTOS? ────────────────────────────
echo
echo "== verificação dos modelos por run (armadilha nº8) =="
python - "$DESTINO" "${FASES[@]}" <<'PY'
import hashlib
import os
import re
import sys

destino, fases = sys.argv[1], sys.argv[2:]
for f in fases:
    pasta = os.path.join(destino, "mega_B_fase%s" % f, "models")
    if not os.path.isdir(pasta):
        print("   fase %s: sem pasta de modelos (nada a verificar)" % f)
        continue
    por_run = {}
    for nome in os.listdir(pasta):
        m = re.search(r"_run(\d+)\.pth$", nome)
        if m:
            por_run[int(m.group(1))] = os.path.join(pasta, nome)
    if not por_run:
        print("   fase %s: NENHUM ficheiro *_run{n}.pth — é o sintoma da "
              "armadilha nº8 (um modelo só, do último run)" % f)
        continue
    digests = {}
    for run, fp in sorted(por_run.items()):
        with open(fp, "rb") as fh:
            digests.setdefault(hashlib.sha256(fh.read()).hexdigest(), []).append(run)
    repetidos = {d: rs for d, rs in digests.items() if len(rs) > 1}
    print("   fase %s: %d runs com modelo próprio, %d distintos"
          % (f, len(por_run), len(digests)))
    if repetidos:
        for d, rs in repetidos.items():
            print("      ⚠ runs %s partilham o MESMO ficheiro (%s…)"
                  % (rs, d[:12]))
PY

# ── figuras, para a campanha aparecer no dashboard ───────────────────────────
echo
echo "== figuras =="
for f in "${FASES[@]}"; do
    python "$RAIZ/scripts/figuras_campanha.py" --campanha "mega_B$f" 2>&1 \
        | grep -E "^\s+\[v\]|^\s+\[i\]|^\s+\[!\]|figuras em" || true
done

echo
echo "FEITO. A seguir:"
echo "  1. análise do pré-registo v2:  python scripts/analise_megatreino.py"
echo "  2. o F2 do mapa grande já pode arrancar: bash scripts/lancar_f2.sh"
echo "  3. publicar no Pi:             bash scripts/atualizar_pi.sh"
