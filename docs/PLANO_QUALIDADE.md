# Plano de qualidade — de 5 ago ao hard stop (22 ago)

Escrito a 5 ago 2026, com o F2 a correr. Não é um plano de funcionalidades: é uma
lista de sítios onde o projeto pode estar errado sem dar sinal, por ordem do que
custa descobri-los tarde.

O critério que ordena tudo: **o que só se descobre depois de a campanha fechar
custa a tese**. A 16 de agosto faltam seis dias para o hard stop; um defeito no
pipeline de análise descoberto nessa altura não tem janela para ser corrigido com
dados novos.

## Como este plano nasceu

De três achados no mesmo dia, todos do mesmo feitio — nenhum era um erro de
cálculo, todos eram **afirmações que ninguém tinha testado**:

- a linha do tempo do dashboard dizia que o GNN fecharia «~14 ago», dois dias
  depois de o stream ter sido relançado;
- a **M3 do pré-registo não era calculável** — o pipeline nunca registou o estado
  da porta, e a falta só apareceria com a campanha fechada;
- eu próprio medi o custo da alternativa com uma régua diferente da do ambiente e
  publiquei 13,4% onde o número, já medido a 28 jul, era 17,0%.

O padrão: **os números têm verificador, as afirmações sobre os números não.**

---

## Eixo 1 — O que a campanha promete e o pipeline pode não produzir

| # | Verificação | Estado |
|---|---|---|
| 1.1 | M3 (`door_opened`) registada na avaliação | ✅ 5 ago — coluna + 5 testes + enviada às 4 pastas do servidor |
| 1.2 | M1 e M2 calculáveis do `eval_by_run.csv` | ✅ colunas presentes (`food_collected`, `success`, `Run`) |
| 1.3 | A análise F2 corre ponta a ponta com dados na forma real | ⬜ ensaiar com CSV sintético antes de 9 ago |
| 1.4 | `pos_campanha.py` (armadilha nº9) corre sobre a campanha do mapa | ⬜ |
| 1.5 | O limiar de decisão (⌈5/7 × n⌉ = 15/21) sai do n do CSV, não fixo | ⬜ confirmar no código |

## Eixo 2 — Afirmações sem verificador

| # | Verificação | Estado |
|---|---|---|
| 2.1 | Datas e estados do dashboard vs realidade do servidor | ✅ linha do tempo corrigida; ⬜ automatizar |
| 2.2 | Números da tese ↔ scripts que os reproduzem | ✅ 346 + `verificar_vertical.py`; ⬜ cobrir a secção do mapa grande quando fechar |
| 2.3 | Afirmações do pré-registo ↔ geometria atual do mapa | ✅ emendas 22-23 datadas |
| 2.4 | Uma métrica medida por duas réguas diferentes | ⬜ varrer o repositório à procura de segundos cálculos da mesma coisa |

## Eixo 3 — Código sem rede de segurança

| # | Verificação | Estado |
|---|---|---|
| 3.1 | Módulos sem um único teste | ⬜ inventariar |
| 3.2 | Os três visualizadores usam convenções de eixos diferentes | ⬜ decidir se se unificam ou se se documenta |
| 3.3 | Scripts que produzem números da tese e vivem fora do repositório | ✅ `verificar_vertical.py` trouxe os de hoje |

## Eixo 4 — Publicação

| # | Verificação | Estado |
|---|---|---|
| 4.1 | Dashboard: auditoria nos dois modos | ✅ 0 problemas (16 vistas, 1247 imagens) |
| 4.2 | 3D do browser mostra a altura e diz que as paredes estão cortadas | ✅ validado no browser (520 px do aviso no quadro 102, 0 no quadro 0) |
| 4.3 | Pi atualizado | ⬜ **exige a VPN DESLIGADA** — um comando, `scripts/atualizar_pi.sh` |
| 4.4 | O delta do Pi leva o que as vistas novas leem | ✅ envia `dashboard/` inteiro |

## Eixo 5 — Calendário

- **~9 ago** o grad fecha → o `f2lwatch` lança o exploratório sozinho.
- **~14 ago** exploratório fecha.
- **~16 ago** o GNN fecha → correr a análise M1-M3, integrar a secção do mapa
  grande, preencher os `\PORPREENCHER`.
- **22 ago** hard stop: o que não fechar até aqui vai para a defesa, não para a
  tese (regra 4 dos compromissos de reporte do pré-registo).

A folga real entre o fim do GNN e o hard stop são **seis dias**. É por isso que o
Eixo 1 tem de estar todo feito antes de 9 de agosto: quando os dados chegarem, a
análise tem de correr à primeira.
