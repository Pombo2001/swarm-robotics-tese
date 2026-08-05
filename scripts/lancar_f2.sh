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
#   3. cada stream vai treinar o BRAÇO que o pré-registo fixa — GNN adaptativo
#      (0.5/true) nos dois streams de GNN, sem novidade nos gradientes. Esta
#      verificação já existiu ao contrário e certificou 26 h do braço errado;
#      ver a nota longa junto à verificação;
#   4. o cenário do config é o que o run_experiments vai sobrepor, e a arena do
#      mapa grande está nos 60 m com 2000 passos;
#   5. há disco;
#   6. os `_fail10`, `models_7d` e CSV do F1 NÃO estão nas cópias (o F2 treina
#      de raiz — se estiverem, o `arquivar` leva-os como se fossem desta campanha).
#
# Só depois lança, e confirma que os dois streams escreveram a primeira geração.
#
# UMA ligação, não vinte  (3 ago)
# -------------------------------
# A primeira versão fazia uma ligação SSH por verificação. Em série, o servidor
# aborta algumas ("Software caused connection abort") — e como o stderr ia para
# /dev/null, uma ligação abortada devolvia string vazia. As verificações 1 e 6
# são CONTAGENS: vazio lê-se como "0 sessões do mega-treino" e "0 ficheiros
# alheios", exatamente os dois verdes que autorizam o lançamento. Era o verde
# falso mais perigoso do script, e vi os dois sentidos do erro no mesmo dia (a
# 3 ago disse que as três cópias não existiam quando existiam).
#
# Agora tudo o que é preciso saber vem num só bloco `chave=valor`, lido numa
# ligação, e as verificações fazem-se em cima do que chegou. O `__FIM__` corre
# sempre (`;`, não `&&`), por isso a sua ausência distingue "não liguei" de
# "liguei e não havia nada" — e sem marcador o script recusa-se a lançar.
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

# Devolve a saída do comando remoto, ou !=0 se a ligação não chegou ao fim.
# Duas tentativas: o abort é intermitente e a segunda quase sempre passa; uma
# VPN em baixo falha as duas. NÃO acrescenta newline à saída — os consumidores
# fazem `tail -1` e uma linha em branco no fim lê-se como resposta vazia.
remoto() {
    local saida tentativa
    for tentativa in 1 2; do
        saida=$(bash "$SRV" "{ $*
} ; printf '__FIM__\n'" 2>/dev/null)
        if [[ "$saida" == *__FIM__* ]]; then
            printf '%s' "${saida%%__FIM__*}"
            return 0
        fi
        [ "$tentativa" = 1 ] && sleep 3
    done
    return 3
}

echo "=============================================================================="
echo "F2 DO MAPA GRANDE — verificações antes de lançar   ($(date '+%d %b %Y %H:%M'))"
echo "=============================================================================="

# ----------------------------------------------------------------------------
# Tudo o que é preciso saber do servidor, numa ligação só.
# Heredoc entre aspas: nada aqui dentro é expandido pela shell LOCAL.
# ----------------------------------------------------------------------------
read -r -d '' RECOLHA <<'REMOTO' || true
echo "MEGA=$(tmux ls 2>/dev/null | grep -cE '^mega[AB]:')"
echo "SIM_base=$(sha256sum ~/swarm-mapa/src/environment/swarm_env_3d.py 2>/dev/null | awk '{print $1}')"
for d in f2g f2r f2l; do
    echo "SIM_$d=$(sha256sum ~/swarm-mapa-$d/src/environment/swarm_env_3d.py 2>/dev/null | awk '{print $1}')"
    echo "NOV_$d=$(grep -hE 'novelty_(weight|adaptive)' ~/swarm-mapa-$d/configs/foraging.yaml 2>/dev/null | tr -d ' \n')"
    echo "DEF_$d=$(grep -hE "novelty_(weight|adaptive)', " ~/swarm-mapa-$d/src/training/evo_trainer_3d.py 2>/dev/null | tr -d ' \n')"
    # O que o script VAI escrever no arranque — a única declaração do braço que
    # existe antes de treinar. Extrai-se a chamada do RAMO deste stream (o
    # ficheiro tem as três: gnn, grad e longo). Por contexto e não por posição:
    # a ordem das chamadas no ficheiro não é um contrato.
    case "$d" in
        f2g) marca='MODO" = "gnn"' ;;
        f2r) marca='MODO" = "grad"' ;;
        *)   marca='EXPLORATÓRIO (emenda 20)' ;;
    esac
    echo "CFGNOV_$d=$(awk -v m="$marca" 'index($0,m){f=1} f && /^ *config_novelty /{print $1 $2 $3; exit}' \
        ~/swarm-mapa-$d/scripts/mapa_streamF2.sh 2>/dev/null | tr -d ' \n')"
    echo "SUJO_$d=$(ls ~/swarm-mapa-$d/results/models_7d ~/swarm-mapa-$d/results/evaluation/*.csv 2>/dev/null | wc -l)"
done
echo "GEO=$(grep -hE 'arena_radius_mapa_grande|max_steps_mapa_grande' ~/swarm-mapa-f2g/configs/foraging.yaml 2>/dev/null | tr -d ' \n')"
echo "DISCO=$(df --output=avail -BG /home | tail -1 | tr -dc '0-9')"
echo "ULTIMA_MEGA=$(tail -1 ~/mega_B_master.log 2>/dev/null | tr -d '\r')"
REMOTO

dados=$(remoto "$RECOLHA") || {
    echo "  [X] o servidor não respondeu (duas tentativas)."
    echo "      VPN do ISCTE ligada? (o Pi e o servidor não se alcançam ao mesmo"
    echo "      tempo — ver o LEIA-ME). Nada foi verificado, nada foi lançado."
    exit 2
}
ok "servidor a responder"

declare -A V=()
while IFS='=' read -r chave valor; do
    [ -n "$chave" ] && V["$chave"]="${valor%$'\r'}"
done <<< "$dados"

# Uma recolha truncada a meio invalida tudo o que vem a seguir: uma chave em
# falta lê-se como vazia, e vazio é o valor que faz passar as contagens.
for esperada in MEGA SIM_base GEO DISCO; do
    if [ -z "${V[$esperada]+x}" ]; then
        echo "  [X] a resposta do servidor veio truncada (falta '$esperada')."
        echo "      Não verifico nem lanço nada em cima de leitura incompleta."
        exit 2
    fi
done

# 1. o mega-treino largou a máquina
if [ -z "${V[MEGA]}" ]; then
    mal "não consegui contar as sessões do mega-treino (resposta vazia)"
elif [ "${V[MEGA]}" != "0" ]; then
    mal "megaA/megaB AINDA a correr (${V[MEGA]} sessões) — o pré-registo manda esperar"
    echo "      última linha: ${V[ULTIMA_MEGA]:-(sem log)}"
else
    ok "mega-treino terminado (nenhuma sessão megaA/megaB)"
fi

# 2. as três cópias, com o simulador de agora
if [ -z "${V[SIM_base]}" ]; then
    mal "não li o sha256 do simulador de ~/swarm-mapa (a referência)"
fi
for d in f2g f2r f2l; do
    h="${V[SIM_$d]:-}"
    if [ -z "$h" ]; then
        mal "~/swarm-mapa-$d não existe — corre 'mapa_streamF2.sh preparar'"
    elif [ "$h" != "${V[SIM_base]}" ]; then
        mal "~/swarm-mapa-$d tem OUTRO simulador (foi isto que anulou o F1 de 29 jul)"
    else
        ok "~/swarm-mapa-$d com o simulador de agora"
    fi
done

# 3. o BRAÇO de cada stream é o que o pré-registo fixa
#
# ⚠️ Esta verificação já existiu ao contrário, e custou 26 h de máquina (4 ago).
# Chamava-se «sem novidade — por config OU por omissão», dava verde quando as
# chaves `novelty_*` estavam ausentes e vermelho se a novidade estivesse LIGADA.
# Isto é o inverso do que a secção 2 do pré-registo manda: «GNN com Novelty
# **adaptativo** (w₀=0,5, sustain=10, decay=0,98) — **não o objetivo puro**: a
# QI6 mostrou que o adaptativo domina o objetivo». Os dois primeiros runs do F2
# treinaram, portanto, o braço errado, com o lançador a certificá-lo.
#
# Verifica-se o SCRIPT que vai correr, não o estado do config: é o
# `mapa_streamF2.sh` que escreve as chaves em cada arranque (config_novelty), e
# o config antes do arranque não diz nada sobre o que vai ser treinado. O que o
# script declara é a única fonte da verdade disponível antes de lançar.
for d in f2g f2r f2l; do
    esperado_w="0.5"; esperado_a="true"; rotulo="GNN adaptativo"
    if [ "$d" = "f2r" ]; then
        esperado_w="0.0"; esperado_a="false"; rotulo="gradientes (sem novidade)"
    fi
    linha="${V[CFGNOV_$d]:-}"
    if [ -z "$linha" ]; then
        mal "$d: o mapa_streamF2.sh não declara o braço (falta config_novelty) —"
        echo "      é exatamente assim que se treina o braço errado em silêncio."
    elif [[ "$linha" == *"config_novelty$esperado_w$esperado_a"* ]]; then
        ok "$d lança o braço certo: $rotulo ($esperado_w / $esperado_a)"
    else
        mal "$d declara '$linha', esperado 'config_novelty $esperado_w $esperado_a' ($rotulo)"
    fi
done

# 3b. e o config não pode contradizer o script (se tiver as chaves, que batam)
for d in f2g f2l; do
    linha="${V[NOV_$d]:-}"
    case "$linha" in
        "") ok "$d: config sem chaves de novidade — o script escreve-as no arranque" ;;
        *novelty_adaptive:true*novelty_weight:0.5*|*novelty_weight:0.5*novelty_adaptive:true*)
            ok "config de $d já com o braço adaptativo (0.5 / true)" ;;
        *)  mal "config de $d contradiz o pré-registo: $linha" ;;
    esac
done

# 4. a geometria do mapa
case "${V[GEO]}" in
    *arena_radius_mapa_grande:60*max_steps_mapa_grande:2000*|*max_steps_mapa_grande:2000*arena_radius_mapa_grande:60*)
        ok "mapa grande com arena r=60 e 2000 passos" ;;
    *)  mal "geometria inesperada no config: ${V[GEO]:-vazio}" ;;
esac

# 5. disco
if [ -z "${V[DISCO]}" ]; then
    mal "não li o espaço livre em /home"
elif [ "${V[DISCO]}" -lt 20 ]; then
    mal "só ${V[DISCO]}G livres em /home (o F2 escreve modelos e logs de 21 runs)"
else
    ok "${V[DISCO]}G livres em /home"
fi

# 6. as cópias estão limpas de resultados alheios
for d in f2g f2r f2l; do
    sujo="${V[SUJO_$d]:-}"
    if [ -z "$sujo" ]; then
        mal "não consegui listar os resultados de ~/swarm-mapa-$d (resposta vazia)"
    elif [ "$sujo" != "0" ]; then
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
sessoes=$(remoto "tmux new-session -d -s mapaF2g '~/swarm-mapa-f2g/scripts/mapa_streamF2.sh gnn'
tmux new-session -d -s mapaF2r '~/swarm-mapa-f2r/scripts/mapa_streamF2.sh grad'
sleep 5
tmux ls") || {
    echo "  [X] a ligação partiu DURANTE o lançamento — estado desconhecido."
    echo "      Vê o que ficou de pé antes de repetir (pode ter lançado um stream só):"
    echo "        bash scripts/servidor.sh \"tmux ls\""
    exit 2
}
echo "$sessoes"

# Uma das duas pode ter falhado sozinha (diretório, permissões) e o script não
# daria por isso — a confirmação nos logs abaixo passa com um stream só a andar.
for s in mapaF2g mapaF2r; do
    echo "$sessoes" | grep -q "^$s:" || mal "a sessão $s NÃO está de pé"
done
if [ "$falhas" -ne 0 ]; then
    echo "!! lancei mas nem todos os streams estão a correr — vê o 'tmux ls' acima."
    exit 3
fi

echo
echo "A confirmar que arrancaram (até 3 min)..."
for i in $(seq 1 18); do
    sleep 10
    saida=$(remoto "tail -2 ~/mapa_F2_gnn.log 2>/dev/null; echo ---; tail -2 ~/mapa_F2_ppo.log 2>/dev/null") || continue
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
