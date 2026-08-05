#!/bin/bash
# Lança o braço EXPLORATÓRIO do F2 (emenda 20) assim que o stream dos gradientes
# largar a máquina. Corre NO SERVIDOR, dentro do seu próprio tmux.
#
# Porquê um watcher e não lançar já
# ---------------------------------
# O `longo` são 3 runs × 2340 min de GNN, e o GNN leva 30 dos 64 vCPU. Com o
# `mapaF2g` (outros 30) e o `mapaF2r` ainda vivos, três streams pesados fazem
# cada run render MENOS gerações — e são as gerações por run que o pré-registo
# fixa para M1-M3 poderem comparar-se com as campanhas fechadas. O braço GNN
# principal já leva 11 dias investidos; atrasá-lo para adiantar um exploratório
# que nem entra em M1-M3 seria trocar o que conta pelo que não conta.
#
# Porquê no servidor e não na torre
# ---------------------------------
# O `esperar_f1.sh` espera a partir do PC: precisa do PC ligado, da VPN de pé e
# de ~2 000 ligações SSH ao longo de dias. Aqui a espera é local à máquina que
# vai lançar — nada disto pode falhar por a torre ter adormecido.
#
# Uso (no servidor):
#     tmux new-session -d -s f2lwatch '~/f2_longo_ao_fechar.sh'
#     tail -f ~/f2_longo_watch.log
#
# Não lança se: já houver um `mapaF2l`; o diretório não existir; faltar disco; ou
# o stream dos gradientes ter DESAPARECIDO SEM CONCLUIR — nesse caso o que falta
# é relançar o grad (que conta para M1-M3), e a decisão é do utilizador. Isso é
# registado em letras gordas no log em vez de ser resolvido por adivinhação.
set -u

LOG=~/f2_longo_watch.log
DIR=~/swarm-mapa-f2l
MASTER_GRAD=~/mapa_F2grad_master.log
INTERVALO=${F2_WATCH_INTERVALO:-300}
DISCO_MIN_GB=${F2_DISCO_MIN_GB:-10}

registar() { echo "[watch $(date -u '+%d %b %H:%M')] $*" | tee -a "$LOG"; }

registar "ARRANQUE — à espera que o mapaF2r feche para lançar o exploratório"

# --- Guardas que não dependem de esperar ------------------------------------
if tmux ls 2>/dev/null | grep -qE '^mapaF2l:'; then
    registar "⛔ já existe uma sessão mapaF2l. Nada a fazer."
    exit 0
fi
if [ ! -x "$DIR/scripts/mapa_streamF2.sh" ]; then
    registar "⛔ sem $DIR/scripts/mapa_streamF2.sh — corre 'mapa_streamF2.sh preparar'."
    exit 2
fi

# --- Espera ------------------------------------------------------------------
# A ausência da sessão só vale se o tmux RESPONDEU. `tmux ls` devolve !=0 e
# escreve "no server running" quando não há servidor tmux nenhum — que é
# indistinguível de "acabou" se se olhar só para o grep. Distingue-se aqui: sem
# servidor tmux não há mapaF2g nem mapaF2r, e isso é um estado que merece log.
while true; do
    sessoes=$(tmux ls -F '#{session_name}' 2>/dev/null)
    if echo "$sessoes" | grep -qE '^mapaF2r$'; then
        sleep "$INTERVALO"
        continue
    fi
    registar "o mapaF2r já não está vivo (sessões: ${sessoes:-nenhuma})"
    break
done

# --- O grad chegou ao fim, ou morreu a meio? --------------------------------
# 'CONCLU' sem acento de propósito: o script escreve "CONCLUÍDO" e um grep com
# acento depende do locale de quem corre isto.
if [ ! -f "$MASTER_GRAD" ] || ! grep -q 'CONCLU' "$MASTER_GRAD"; then
    registar "⛔⛔ o mapaF2r desapareceu SEM 'CONCLUÍDO' no $(basename "$MASTER_GRAD")."
    registar "     PPO/SAC contam para M1-M3: o que falta é relançar o GRAD, não"
    registar "     adiantar o exploratório. NÃO lancei nada. Últimas linhas:"
    tail -5 "$MASTER_GRAD" 2>/dev/null | tee -a "$LOG"
    exit 3
fi
registar "grad CONCLUÍDO: $(grep 'CONCLU' "$MASTER_GRAD" | tail -1)"

livre_gb=$(df -BG --output=avail "$HOME" 2>/dev/null | tail -1 | tr -dc '0-9')
if [ -n "$livre_gb" ] && [ "$livre_gb" -lt "$DISCO_MIN_GB" ]; then
    registar "⛔ só ${livre_gb}G livres (< ${DISCO_MIN_GB}G) — não lanço."
    exit 4
fi
registar "disco: ${livre_gb:-?}G livres"

# --- Lançar ------------------------------------------------------------------
# O próprio mapa_streamF2.sh volta a verificar que o mapaF2r não está vivo e
# escreve+relê o braço (0.5/true) antes de treinar, abortando se não bater. Esta
# dupla verificação é de propósito: foi a falta dela que deixou correr 26 h do
# braço errado (4 ago).
tmux new-session -d -s mapaF2l "$DIR/scripts/mapa_streamF2.sh longo"
sleep "${F2_ESPERA_ARRANQUE:-20}"   # variável para o ensaio não esperar 20 s
if tmux ls 2>/dev/null | grep -qE '^mapaF2l:'; then
    registar "✅ mapaF2l LANÇADO (3 runs × 2340 min ≈ 4,9 dias)"
    registar "   confirmar o braço:  grep 'braço' ~/mapa_F2longo_master.log"
else
    registar "⛔ o tmux mapaF2l não ficou vivo 20 s depois de lançado."
    tail -5 ~/mapa_F2longo_master.log 2>/dev/null | tee -a "$LOG"
    exit 5
fi
