# Pré-registo v2 — Mega-treino de 1 mês «piores mapas» (lançado 19-20 jul 2026)

> Escrito a 19 jul 2026, ANTES de qualquer dado de avaliação desta campanha existir.
> Composição aprovada pelo utilizador («treinar os piores mapas; faz o que for melhor»).
> Segue o precedente do `PRE_REGISTO_NOVELTY_ADAPTATIVO.md`, cuja regra de decisão foi
> cumprida sem desvios a 19 jul. Análise: SÓ com `eval_by_run.csv` (armadilha nº3);
> unidade estatística = média por run; Mann-Whitney U exato + δ de Cliff.

## Composição (2 streams, fases com arquivo próprio; hard stop de integração 22 ago)

**Stream A (`~/swarm-robotics-tese`, tmux `megaA`)** — u_wall a n=28 + Sandbox:
- A1: GNN **adaptativo** (w₀=0,5; defaults sustain=10, decay=0,98) u_wall @195×**28** (~3,8 d)
- A2: GNN **objetivo** u_wall @195×**28** (~3,8 d)
- A3: **PPO** u_wall @48×**28** (~0,9 d) · A4: **SAC** u_wall @48×**28** (~0,9 d)
- A5: GNN adaptativo **none (Sandbox)** @195×**21** (~2,8 d)
- Fim estimado: ~1 ago. Arquivo: `~/mega_A_fase{1..5}/`.

**Stream B (`~/swarm-novelty`, tmux `megaB`)** — ablação do anneal + reforços:
- B1: sustain=**5** u_wall+bypass @195×7 cada (~1,9 d)
- B2: sustain=**20** idem (~1,9 d)
- B3: decay=**0,95** idem (~1,9 d)
- B4: decay=**0,995** idem (~1,9 d)
- B5: adaptativo default **bypass** @195×**21** (reforço T4; n total 7+21=28) (~2,8 d)
- B6: **SAC bottleneck** @48×**21** (célula 5/7) (~0,7 d)
- B7: GNN adaptativo **cooperative_perception** @195×**21** (célula 5/7) (~2,8 d)
- Fim estimado: ~3 ago. Arquivo: `~/mega_B_fase{1..7}/`.

Seeds = nº do run (1..N), como sempre. As células n=28 do u_wall são **autocontidas**
(as 4 condições da MESMA campanha comparam-se entre si; os n=7 antigos ficam como
verificação de consistência, nunca se somam sem o declarar).

## Hipóteses e testes confirmatórios

- **M1 (principal):** no u_wall a n=28, o adaptativo tem maior magnitude que o objetivo
  (MW unilateral sobre médias por run) e maior taxa de convergência (descritivo). Com
  n=28, um Fisher exato sobre convergência passa a ser reportável (com n=7 não era).
- **M2:** u_wall a n=28 nos 4 braços — o quadro «nenhuma diferença significativa entre
  os 3 algoritmos base» mantém-se ou desfaz-se? (bilateral, 6 pares; reportar p brutos
  + δ; multiplicidade assinalada.)
- **M3 (reforço T4):** bypass adaptativo n=28 vs fixo n=7 (bilateral) — o δ=+0,59
  (p=0,073) de 19 jul confirma-se ou dissolve-se?

## Exploratório (rotulado; sem regra de decisão binária)

- **Ablação do anneal** (B1-B4 vs default n=7 de 19 jul): caracterização por δ; a
  pergunta é a SENSIBILIDADE do mecanismo, não um vencedor. Reportar TODAS as configs.
- **Sandbox adaptativo n=21** (A5): a novidade reduz os runs degenerados do GNN em
  aberto? (sinal descritivo de 19 jul: 6/7 vs 5/7, δ=+0,27 n.s.)
- **Perceção adaptativa n=21+7** (B7): o 5/7 de 19 jul é acaso ou custo real?

## Compromissos de reporte

1. Todos os runs, todas as configs, todas as fases — sem exceção nem subconjuntos.
2. Convergência = descritivo (exceto Fisher em M1, agora com n que o suporta);
   magnitude = teste; com n=7 nas ablações, o peso está no δ.
3. O que fechar depois de 22 ago não entra na tese (vai para a defesa) — decidido ANTES.
4. Qualquer desvio a este documento é datado abaixo, nunca silencioso.

## Mecânica

- Scripts: `scripts/mega_streamA.sh` + `scripts/mega_streamB.sh` (padrão week_*: sed ao
  config por fase, retry com --resume, arquivo + normalização do config no fim).
- No fim de TUDO: os dois configs ficam repostos (0.0/false) pelos próprios scripts —
  VERIFICAR à mão na chegada (armadilha do stream B de 19 jul).
- Na chegada: verificação `_run{n}` + instalar em `results/mega_1mes/` SEM tocar nos
  modelos ativos (precedente de 19 jul).
