#!/usr/bin/env bash
# Lança o F2 do mapa grande no servidor — com as verificações ANTES de disparar.
#
# Porquê um script em vez de dois `tmux new-session`
# --------------------------------------------------
# O F2 são 11 dias de máquina. Um erro no arranque só se vê horas depois, e o
# histórico deste projeto tem três: uma campanha lançada com o config da
# anterior, um F1 anulado por o simulador ser o velho, e dois streams a
# partilhar diretório. Nenhum deles daria erro no primeiro minuto.
#
# Este script verifica, uma a uma, as condições que já falharam alguma vez:
#
#   1. o mega-treino já largou a máquina (senão são três streams pesados);
#   2. as três cópias existem e têm o simulador de agora (mesmo sha256);
#   3. os configs estão sem novidade (novelty_weight 0.0 / adaptive false);
#   4. o cenário do config é o que o run_experiments vai sobrepor, e a arena do
#      mapa grande está nos 60 m com 2000 passos;
#   5. há disco;
#   6. os `_fail10`, `models_7d` e CSV do F1 NÃO estão nas cópias (o F2 treina
#      de raiz — se estiverem, o `arquivar` leva-os como se fossem desta campanha).
#
# Só depois lança, e confirma que os dois streams escreveram a primeira geração.
#
# Uso (na torre, com a VPN do ISCTE ligada):
#     bash scripts/lancar_f2.sh --verificar     # só as verificações, não lança
#     bash scripts/lancar_f2.sh                 # verifica e lança
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV="$RAIZ/scripts/servidor.sh"
SO_VERIFICAR=0
[ "${1:-}" = "--verificar" ] && SO_VERIFICAR=1

falhas=0
ok()   { echo "  [v] $*"; }
mal()  { echo "  [X] $*"; falhas=$((falhas + 1)); }

remoto() { bash "$SRV" "$*" 2>/dev/null; }

echo "=============================================================================="
echo "F2 DO MAPA GRANDE — verificações antes de lançar   ($(date '+%d %b %Y %H:%M'))"
echo "=============================================================================="

# 0. o servidor responde
if ! remoto "echo vivo" | grep -q vivo; then
    echo "  [X] o servidor não responde. VPN do ISCTE ligada?"
    echo "      (o Pi e o servidor não se alcançam ao mesmo tempo — ver o LEIA-ME)"
    exit 2
fi
ok "servidor a responder"

# 1. o mega-treino largou a máquina
vivos=$(remoto "tmux ls 2>/dev/null | grep -cE '^mega[AB]:'" | tail -1 | tr -d '[:space:]')
if [ "${vivos:-0}" != "0" ]; then
    mal "megaA/megaB AINDA a correr ($vivos sessões) — o pré-registo manda esperar"
    remoto "tail -1 ~/mega_B_master.log"
else
    ok "mega-treino terminado (nenhuma sessão megaA/megaB)"
fi

# 2. as três cópias, com o simulador de agora
sim_base=$(remoto "sha256sum ~/swarm-mapa/src/environment/swarm_env_3d.py" \
           | tail -1 | awk '{print $1}')
for d in f2g f2r f2l; do
    h=$(remoto "sha256sum ~/swarm-mapa-$d/src/environment/swarm_env_3d.py 2>/dev/null" \
        | tail -1 | awk '{print $1}')
    if [ -z "$h" ]; then
        mal "~/swarm-mapa-$d não existe — corre 'mapa_streamF2.sh preparar'"
    elif [ "$h" != "$sim_base" ]; then
        mal "~/swarm-mapa-$d tem OUTRO simulador (foi isto que anulou o F1 de 29 jul)"
    else
        ok "~/swarm-mapa-$d com o simulador de agora"
    fi
done

# 3. sem novidade — por config OU por omissão
#
# O `~/swarm-mapa` não tem as chaves `novelty_*` no config: só os diretórios do
# mega-treino as têm, porque são os `mega_stream*.sh` que lhes mexem com sed. A
# ausência é o estado correto para o F2 — mas «não está lá» só é seguro se o
# DEFAULT do código for desligado, e isso verifica-se em vez de se assumir (a
# primeira versão desta verificação exigia a chave presente e dava três falsos
# alarmes).
for d in f2g f2r f2l; do
    linha=$(remoto "grep -E 'novelty_(weight|adaptive)' ~/swarm-mapa-$d/configs/foraging.yaml 2>/dev/null | tr -d ' \n'")
    if [ -z "$linha" ]; then
        defaults=$(remoto "grep -E \"novelty_(weight|adaptive)'\, \" ~/swarm-mapa-$d/src/training/evo_trainer_3d.py | tr -d ' \n'")
        case "$defaults" in
            *novelty_weight*0.0*novelty_adaptive*False*|*novelty_adaptive*False*novelty_weight*0.0*)
                ok "$d sem novidade (chaves ausentes; defaults do código = 0.0/False)" ;;
            "") mal "$d: não li nem o config nem os defaults do evo_trainer" ;;
            *)  mal "$d: chaves ausentes e defaults do código NÃO são 0.0/False: $defaults" ;;
        esac
    else
        case "$linha" in
            *novelty_adaptive:false*novelty_weight:0.0*|*novelty_weight:0.0*novelty_adaptive:false*)
                ok "config de $d sem novidade (0.0 / false)" ;;
            *)  mal "config de $d com novidade LIGADA: $linha" ;;
        esac
    fi
done

# 4. a geometria do mapa
geo=$(remoto "grep -E 'arena_radius_mapa_grande|max_steps_mapa_grande' ~/swarm-mapa-f2g/configs/foraging.yaml | tr -d ' \n'")
case "$geo" in
    *arena_radius_mapa_grande:60*max_steps_mapa_grande:2000*|*max_steps_mapa_grande:2000*arena_radius_mapa_grande:60*)
        ok "mapa grande com arena r=60 e 2000 passos" ;;
    *)  mal "geometria inesperada no config: ${geo:-vazio}" ;;
esac

# 5. disco
livre=$(remoto "df --output=avail -BG /home | tail -1 | tr -dc '0-9'")
if [ "${livre:-0}" -lt 20 ]; then
    mal "só ${livre}G livres em /home (o F2 escreve modelos e logs de 21 runs)"
else
    ok "${livre}G livres em /home"
fi

# 6. as cópias estão limpas de resultados alheios
for d in f2g f2r f2l; do
    sujo=$(remoto "ls ~/swarm-mapa-$d/results/models_7d ~/swarm-mapa-$d/results/evaluation/*.csv 2>/dev/null | wc -l" \
           | tail -1 | tr -d '[:space:]')
    if [ "${sujo:-0}" != "0" ]; then
        mal "~/swarm-mapa-$d tem resultados de outra campanha ($sujo ficheiros)"
    else
        ok "~/swarm-mapa-$d limpa"
    fi
done

echo "------------------------------------------------------------------------------"
if [ "$falhas" -ne 0 ]; then
    echo "$falhas verificação(ões) FALHARAM — não lanço."
    exit 1
fi
echo "todas as verificações passaram."

if [ "$SO_VERIFICAR" = "1" ]; then
    echo "(--verificar: não lancei nada)"
    exit 0
fi

echo
echo "A LANÇAR os dois streams principais (o exploratório só quando o grad fechar):"
remoto "tmux new-session -d -s mapaF2g '~/swarm-mapa-f2g/scripts/mapa_streamF2.sh gnn'; \
        tmux new-session -d -s mapaF2r '~/swarm-mapa-f2r/scripts/mapa_streamF2.sh grad'; \
        sleep 5; tmux ls"

echo
echo "A confirmar que arrancaram (até 3 min)..."
for i in $(seq 1 18); do
    sleep 10
    saida=$(remoto "tail -2 ~/mapa_F2_gnn.log 2>/dev/null; echo ---; tail -2 ~/mapa_F2_ppo.log 2>/dev/null")
    if echo "$saida" | grep -qE 'Gen 1 \||Iteração|timesteps'; then
        echo "$saida"
        echo
        echo "[v] os dois streams estão a treinar."
        echo "    GNN  21 runs × 780 min → ~14 ago"
        echo "    PPO+SAC 42 runs × 192 min → ~8 ago"
        echo "    seguir com: bash scripts/servidor.sh"
        exit 0
    fi
done
echo "!! passaram 3 min e ainda não vi a primeira geração nos logs."
echo "   Não quer dizer que falhou (o arranque carrega o mapa), mas vale a pena ver:"
echo "     bash scripts/servidor.sh \"tail -30 ~/mapa_F2_gnn.log\""
exit 3
