# PROPOSTA — Super mega-treino de 1 mês (20 jul → ~20 ago 2026)

> Pedido do utilizador a 19 jul (última sessão Fable): «queria meter um super mega treino
> de 1 mês». Este documento desenha o melhor uso possível de ~30 dias × 64 vCPU do `.14`,
> respeitando as decisões já tomadas e o calendário. **Para o Opus executar: escrever o
> pré-registo v2 ANTES de lançar** (o padrão que acabou de dar a QI6 limpa).

---

## 0. A restrição que manda em tudo: o calendário

- **Versão composta a 15 set é inegociável.** Resultados que cheguem depois de ~22 ago
  não entram na tese com conforto — entram, no máximo, nos slides da defesa.
- Logo, o mega-treino tem de ser **faseado com valor progressivo** (padrão `week_A/B`:
  cada fase arquiva `results/{evaluation,models,logs}` e escreve sentinela ao fechar).
  O que tiver fechado a 22 ago usa-se; o resto é bónus para a defesa. **Nunca** uma
  campanha monolítica de 30 dias que só dá fruto no fim.
- A tese JÁ está defensável. O mega-treino é upgrade, não salvamento — desenhar para
  que um crash a meio não custe nada (watchdog `launch_7d.sh` + fases + `--resume`).

## 1. Resposta direta: «tem algo para melhorar o treino?»

**No throughput/código: não há nada crítico pendente.** As alavancas grandes já estão
dentro: LiDAR vetorizado (19,5×), observações em batch (2,58×), cache de elites, saves
por run (armadilha nº8), CSVs incrementais, watchdog com sentinela. Mais gerações por
run compram pouco (o @390 mostrou ganho marginal no adaptativo, nulo no objetivo).
**A alavanca real nesta fase é desenho experimental** — onde apontar os núcleos, não
como os acelerar.

## 2. O que NÃO fazer com o mês (decisões tomadas — manter)

- ❌ Repetir a campanha 7×7×N completa (retorno ≈ 0; a tabela principal está fechada).
- ❌ Política de atenção por gradiente (custom policy SB3): risco de 3 semanas sem
  convergir ÀS PORTAS do prazo; se meio-funcionasse, obrigava a reescrever a narrativa
  da limitação nº1. Continua trabalho futuro. (Se sobrar servidor em setembro, é outra
  conversa — não neste mês.)
- ❌ Mexer na recompensa, física ou cenários existentes (invalida comparabilidade).

## 3. Desenho recomendado — 2 streams paralelas (~60/64 núcleos)

Custos por run: GNN/adaptativo @195 min ≈ 3,25 h (30 núcleos); PPO/SAC ≈ 0,8 h (16).
Uma stream GNN dedicada faz ~7 runs/dia.

### Stream A — «Poder estatístico onde ele falta» (o upgrade científico maior)

O único cenário sem veredicto é o u_wall («sete runs não bastam para distinguir 2/7 de
4/7» — dito na tese; Trab. Futuros item 1 promete 30 runs). Cumpri-lo na célula onde
importa é o upgrade mais barato e mais citável:

| Braço (u_wall, seeds NOVAS 8-28) | Runs novos | n final | Custo |
|---|---|---|---|
| GNN objetivo | +21 | 28 | ~68 h |
| GNN adaptativo | +21 | 28 | ~68 h |
| PPO | +21 | 28 | ~17 h |
| SAC | +21 | 28 | ~17 h |
| **Fecha também:** Sandbox-GNN adaptativo (+14, n=21) | +14 | 21 | ~46 h |
| Gargalo-SAC (+14, n=21) | +14 | 21 | ~11 h |

≈ **9-10 dias** de stream. O que compra: (a) taxa de convergência do u_wall com IC
decente nos 4 braços; (b) o T4 marginal (adaptativo vs fixo no bypass, p=0,073) pode
ser reforçado com +14 runs de cada braço se sobrar tempo; (c) o run degenerado do
bottleneck adaptativo e a Perceção 5/7 ganham contexto (n maior diz se são acaso).
⚠️ Seeds 8+ são uma EXTENSÃO da amostra — reportar sempre os n totais, nunca escolher
o subconjunto; pré-registar isto.

### Stream B — «Caracterizar o mecanismo adaptativo» (a nova fronteira da tese)

O anneal validado usa (w₀=0,5; gatilho=10 gens; decay ×0,98; sem re-arm) — UMA célula
do espaço de desenho. Ablação pré-registada em u_wall + bypass (7 runs × 195 min cada):

1. `sustain` 5 vs 20 gens (o gatilho importa?) — 2 configs × 2 cenários = 28 runs ≈ 91 h
2. `decay` 0,95 vs 0,995 (a velocidade importa?) — idem ≈ 91 h
3. **re-arm sob estagnação** (a variante prometida nos Trab. Futuros; exige ~20 linhas
   no `evo_trainer_3d.py` + teste) — 2 cenários ≈ 45 h

≈ **9-10 dias**. O que compra: a secção 6.9 passa de "funciona" a "funciona e sabemos
porquê/quão sensível é" — a diferença entre um resultado e um mecanismo caracterizado.

### Fases baratas (encaixar nos intervalos, sem treino)

- **Sscale dos campeões adaptativos** (28 células × 20 ep, só avaliação, ~3 h): o
  melhor modelo do bypass (88,7) escala como o objetivo? Fecho bonito para a QI2×QI6.
- **Vídeos/GIFs do u_wall adaptativo resolvido** para a defesa (minutos).

### Opcional (só se as streams A e B fecharem cedo)

- **LiDAR 8→16 raios no u_wall** (7 runs obj + 7 adapt): testa «deceção sob
  observabilidade parcial». ⚠️ `num_rays=8` está *hardcoded* em 2 sítios do
  `swarm_env_3d.py` e muda a dimensão da observação (16→24) — exige alteração pequena
  de código + teste de equivalência com 8 raios antes de lançar. Cortar primeiro.
- **Piloto de currículo** (Iskandar): arenas progressivamente fechadas → u_wall. Exige
  cenários novos (código) — só com as duas streams fechadas e vontade.

## 4. Cronograma e regras de lançamento

| Janela | Stream A | Stream B |
|---|---|---|
| ~21 jul → ~31 jul | u_wall 4 braços (fases 1-4) | ablação sustain + decay |
| ~1 ago → ~10 ago | Sandbox/Gargalo + reforço T4 | re-arm + Sscale adaptativo |
| ~10 ago → ~20 ago | margem p/ crashes e extensões | opcionais |
| **22 ago** | **HARD STOP de integração na tese** | (resto → slides) |

Regras (não negociáveis, herdadas das armadilhas):
1. **Pré-registo v2 antes do 1º run** (hipóteses, testes, n finais, regra de reporte).
2. Fases com arquivo próprio + sentinela (padrão `week_*`); watchdog com `--resume`.
3. Ordem canónica de `src/scenarios.py` ao estimar fins (⚠️ não é a do `--scenarios`).
4. No fim de CADA fase adaptativa: repor `novelty_weight: 0.0` / `novelty_adaptive:
   false` no dir respetivo (verificar à mão — armadilha do stream B).
5. Ao trazer: verificação de `_run{n}` + instalar em `results/` SEM tocar nos modelos
   ativos (campeões 7d) — o precedente de 19 jul.
6. **Não lançar sem o utilizador aprovar a composição final** desta proposta.

## 5. Recomendação em uma frase

Gastar o mês a transformar as duas frases mais fracas da tese — «sete runs não bastam»
(u_wall) e «a dosagem adaptativa fica por caracterizar» — em resultados com n=21-28 e
uma ablação pré-registada; e não gastar um único núcleo em repetir o que está fechado
nem em apostas de convergência incerta a 8 semanas do prazo.
