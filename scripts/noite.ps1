# Trabalho autonomo durante a noite — com travoes.
#
# Porque e que isto tem um GOAL e nao um "melhora o projeto"
# ----------------------------------------------------------
# Um agente sem condicao de paragem nao para: continua a mexer, e as 4 da manha
# esta a refatorar coisas que funcionavam. O goal aqui e inteiramente MECANICO —
# quatro comandos que saem com codigo 0 — por isso ou esta feito ou nao esta, e
# nao ha espaco para "achei que ficava melhor assim".
#
# O que ele NAO pode tocar esta escrito no prompt e e a parte mais importante do
# ficheiro: a tese esta fechada e verificada (334 valores), os dados de results/
# custaram 1671 horas de maquina, e o F2 esta a correr no servidor. Nada disso
# se corrige de madrugada sem alguem a olhar.
#
# Sobre a quota: quando bate no limite da sessao, o Claude Code PARA (nao
# adormece). Por isso o loop — espera 30 min e tenta outra vez, ate o goal estar
# cumprido. Cada iteracao arranca uma sessao LIMPA de proposito: com --continue
# arrastaria o contexto todo e gastaria quota a reler-se a si proprio.
#
# Uso (na torre, na raiz do repositorio):
#     powershell -File scripts\noite.ps1
#     powershell -File scripts\noite.ps1 -MaxHoras 8
#
# Ver o que fez, de manha:
#     git log --oneline --since=midnight
#     Get-Content scripts\noite.log -Tail 40

param(
    [int]$MaxHoras = 10,
    [int]$EsperaMinutos = 30
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$log = Join-Path $PSScriptRoot "noite.log"
$fim = (Get-Date).AddHours($MaxHoras)

# O goal. Quatro condicoes mecanicas + o que nao pode mexer.
# Mantido numa string unica para a scheduled task poder usar o mesmo texto.
$goal = @'
/goal Os quatro comandos abaixo saem todos com codigo 0 e sem problemas
reportados:
  1. python -m pytest tests/ -q
  2. python scripts/verificar_numeros_tese.py
  3. python scripts/auditar_dashboard.py
  4. python scripts/auditar_campanhas.py --tese

Corrige o que falhar, uma coisa de cada vez, e faz um commit por correcao com
uma mensagem que explique a CAUSA (nao "fix tests").

REGRAS — nao ha excepcoes a estas:
- NAO alteres Tese/, Artigo/ nem docs/. A tese esta fechada e verificada; se um
  numero da tese nao bater com os dados, PARA e escreve o que encontraste em
  scripts/noite_achados.md, sem corrigir nada.
- NAO alteres nem apagues nada dentro de results/. Sao 1671 horas de maquina e
  nao se regeneram.
- NAO toques no servidor de treino (nada de scripts/servidor.sh, lancar_f2.sh,
  mapa_streamF2.sh): o F2 esta a correr e um engano ali custa 11 dias.
- NAO faças git push. Commits locais so.
- Se um teste falhar por o ambiente nao ter alguma coisa (display, VPN, GPU),
  marca-o como skip com uma razao escrita, em vez de mudar o codigo que ele
  testa.
- Se te encontrares a refatorar codigo que ja passa nos quatro comandos, PARA:
  esse trabalho nao faz parte deste goal.

Antes de terminares, escreve em scripts/noite_achados.md o que correu, o que
corrigiste e o que ficou por resolver.
'@

"=== noite.ps1 arrancou $(Get-Date -Format 'dd/MM HH:mm') · limite $MaxHoras h ===" |
    Tee-Object -FilePath $log -Append

$iteracao = 0
while ((Get-Date) -lt $fim) {
    $iteracao++
    "--- iteracao $iteracao · $(Get-Date -Format 'HH:mm') ---" |
        Tee-Object -FilePath $log -Append

    claude -p $goal --permission-mode acceptEdits 2>&1 |
        Tee-Object -FilePath $log -Append

    if ($LASTEXITCODE -eq 0) {
        "=== goal cumprido a $(Get-Date -Format 'HH:mm') ===" |
            Tee-Object -FilePath $log -Append
        break
    }

    "saiu com $LASTEXITCODE — nova tentativa daqui a $EsperaMinutos min" |
        Tee-Object -FilePath $log -Append
    Start-Sleep -Seconds ($EsperaMinutos * 60)
}

if ((Get-Date) -ge $fim) {
    "=== parei por limite de tempo ($MaxHoras h) ===" |
        Tee-Object -FilePath $log -Append
}

"`nDe manha:  git log --oneline --since=midnight" | Tee-Object -FilePath $log -Append
"           Get-Content scripts\noite_achados.md" | Tee-Object -FilePath $log -Append
