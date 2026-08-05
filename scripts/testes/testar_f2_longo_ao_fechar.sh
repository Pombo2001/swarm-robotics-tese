#!/usr/bin/env bash
# Ensaia o f2_longo_ao_fechar.sh contra um `tmux` e um HOME falsos.
# Um watcher que so se testa esperando 4 dias nao se testa nunca.
#
# O tmux falso guarda ESTADO (o conjunto de sessoes vivas), como o verdadeiro:
# `new-session` acrescenta, e um contador faz o mapaF2r desaparecer a meio para
# se ensaiar a espera.
set -u
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/f2_longo_ao_fechar.sh"
BASE="${TMPDIR:-/tmp}/ensaio_f2_longo"
passou=0; falhou=0

verificar() {  # verificar <nome> <esperado_exit> <padrao_no_log>
    local nome="$1" esperado="$2" padrao="$3"
    if [ "$CODIGO" = "$esperado" ] && grep -q "$padrao" "$FAKE/f2_longo_watch.log" 2>/dev/null; then
        echo "  [v] $nome (exit $CODIGO)"; passou=$((passou+1))
    else
        echo "  [X] $nome — exit=$CODIGO (esperado $esperado), padrao '$padrao'"
        sed 's/^/        /' "$FAKE/f2_longo_watch.log" 2>/dev/null | tail -4
        falhou=$((falhou+1))
    fi
}

preparar() {   # preparar "<sessoes iniciais>" [<chamadas ate o mapaF2r sair>]
    rm -rf "$BASE"; mkdir -p "$BASE/bin" "$BASE/home"
    FAKE="$BASE/home"
    echo "$1" | tr ' ' '\n' | grep -v '^$' > "$BASE/estado.txt"
    echo "${2:-0}" > "$BASE/sai_apos.txt"
    echo 0 > "$BASE/n.txt"
    cat > "$BASE/bin/tmux" <<'EOF'
#!/usr/bin/env bash
BASE="$(dirname "$(dirname "$0")")"
case "${1:-}" in
  ls)
    n=$(( $(cat "$BASE/n.txt") + 1 )); echo "$n" > "$BASE/n.txt"
    sai=$(cat "$BASE/sai_apos.txt")
    if [ "$sai" -gt 0 ] && [ "$n" -ge "$sai" ]; then
        grep -v '^mapaF2r$' "$BASE/estado.txt" > "$BASE/e.tmp" && mv "$BASE/e.tmp" "$BASE/estado.txt"
    fi
    [ -s "$BASE/estado.txt" ] || exit 1
    while read -r s; do
        if [ "${2:-}" = "-F" ]; then echo "$s"; else echo "$s: 1 windows"; fi
    done < "$BASE/estado.txt"
    ;;
  new-session)
    echo "$*" >> "$BASE/lancamentos.txt"
    echo "mapaF2l" >> "$BASE/estado.txt"
    ;;
esac
exit 0
EOF
    chmod +x "$BASE/bin/tmux"
    mkdir -p "$FAKE/swarm-mapa-f2l/scripts"
    printf '#!/bin/bash\nexit 0\n' > "$FAKE/swarm-mapa-f2l/scripts/mapa_streamF2.sh"
    chmod +x "$FAKE/swarm-mapa-f2l/scripts/mapa_streamF2.sh"
}

correr() {
    HOME="$FAKE" PATH="$BASE/bin:$PATH" F2_WATCH_INTERVALO=1 F2_ESPERA_ARRANQUE=0 \
        bash "$SCRIPT" >/dev/null 2>&1
    CODIGO=$?
}

echo "== 1. ja existe um mapaF2l =="
preparar "mapaF2g mapaF2r mapaF2l"
correr; verificar "sai sem lancar" 0 "existe uma sess"

echo "== 2. diretorio do stream em falta =="
preparar "mapaF2g"
rm -rf "$FAKE/swarm-mapa-f2l"
correr; verificar "recusa" 2 "mapa_streamF2.sh"

echo "== 3. o grad desapareceu SEM concluir =="
preparar "mapaF2g"
printf '[mapaF2grad] FASE 1/2: PPO\n' > "$FAKE/mapa_F2grad_master.log"
correr; verificar "nao lanca nada" 3 "SEM 'CONCLU"

echo "== 4. sem tmux nenhum a responder (nao ha servidor) =="
preparar ""
printf '[mapaF2grad] CONCLUIDO\n' > "$FAKE/mapa_F2grad_master.log"
correr; verificar "trata como 'ja nao esta vivo' e segue" 0 "vivo (sess"

echo "== 5. espera enquanto o mapaF2r vive, e lanca quando ele sai =="
preparar "mapaF2g mapaF2r" 3      # ao 3.o `tmux ls`, o mapaF2r desaparece
printf '[mapaF2grad] FASE 2/2: SAC\n[mapaF2grad] CONCLUIDO Wed Aug 09\n' \
    > "$FAKE/mapa_F2grad_master.log"
correr; verificar "lancou" 0 "mapaF2l LAN"
if grep -q -- "-s mapaF2l" "$BASE/lancamentos.txt" 2>/dev/null; then
    echo "  [v] lancou a sessao certa: $(tr -d '\n' < "$BASE/lancamentos.txt" | cut -c1-64)"
    passou=$((passou+1))
else
    echo "  [X] nao lancou o mapaF2l"; falhou=$((falhou+1))
fi
if [ "$(grep -c . "$BASE/lancamentos.txt" 2>/dev/null || echo 0)" = 1 ]; then
    echo "  [v] lancou UMA vez"; passou=$((passou+1))
else
    echo "  [X] lancou $(grep -c . "$BASE/lancamentos.txt") vezes"; falhou=$((falhou+1))
fi

echo
echo "$passou passaram, $falhou falharam"
[ "$falhou" -eq 0 ]
