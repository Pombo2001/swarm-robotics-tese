# Pré-registo — Campanha de Novelty Search Adaptativo (QI6)

> **Escrito a 15 jul 2026, ANTES de os dados de avaliação existirem.** A campanha foi
> lançada a 12 jul 19:46 no servidor `.14` e fecha ~19-20 jul. Este documento fixa as
> hipóteses, a análise e as regras de decisão **antes do *unblinding***, para que a
> conclusão sobre a QI6 não seja escolhida depois de ver os resultados. É a aplicação
> direta da cautela nº1 da `PROPOSTA_TREINO_FINAL.md` ("pré-registar o número de runs,
> decidir antes de ver, reportar todos").
>
> **Estado quando isto foi escrito:** só há sinais de *treino* (não de avaliação) —
> `cooperative_door` 7/7 convergente, `none` bimodal 5/7. Nada disto entra na decisão:
> o veredicto é sempre a **avaliação** (`eval_by_run`), nunca o log de treino (armadilha nº3).

---

## 1. Pergunta e hipótese

**QI6:** a pressão por novidade melhora o controlo evolutivo de enxames? E, se sim, uma
**dosagem adaptativa** (peso `w` que decai após a descoberta) é preferível a um peso fixo?

O que já se sabe (resultados fechados, orçamento igualado a 195 min, 7 runs, seeds 1-7):
- **Novelty fixo `w=0.5`** *ganha* no Muro em U (7/7 a 100%, 69.8±5.9 vs objetivo 3/7,
  24.5±32.7; p=0.026, δ=+0.71) e *perde* no bypass (63.0±21.9 vs 86.7±2.0; p=0.0006, δ=−1.00).
- Leitura: a novidade é um instrumento **direcionado** — compra descoberta onde falta,
  desperdiça seleção onde já sobra. **Dosagem adaptativa** é a hipótese que fecha esta tensão.

**Hipótese pré-registada (H):** o Novelty **adaptativo** (`w` decai após a descoberta),
ao mesmo orçamento (195 min, 7 runs, seeds 1-7), **mantém o ganho no Muro em U sem pagar
o custo do peso fixo nos cenários que a otimização objetiva já resolve** — em particular
sem a degradação que o `w=0.5` sofre no bypass.

---

## 2. Desenho e condições (o que está congelado)

- **Condição experimental primária:** GNN + Novelty adaptativo, 7 cenários × **7 runs**
  × **195 min/run**, **seeds 1-7** (mesmo protocolo emparelhado das outras campanhas — é
  uma *condição diferente*, não uma extensão da amostra baseline).
- **Único delta no config:** `evolution.novelty_weight` (>0) + o *schedule* de anneal do `w`.
  Tudo o resto — recompensa (food 300), física, LiDAR, população, sigma — **congelado**,
  idêntico à campanha 7d e às P1/P2. Sem isto a comparação não é limpa.
- **Braços de controlo @390 min:** existem (2 streams; stream A ~18 jul, stream B ~19 jul).
  São uma verificação de **sensibilidade ao orçamento** (dobro do tempo), classificada aqui
  como análise **secundária/exploratória** (ponto 4). ⚠️ **A confirmar do log do servidor
  antes do *unblinding*:** o que exatamente é o braço @390 (adaptativo @390? objetivo @390?),
  e os parâmetros exatos do anneal (`w` inicial, taxa de decaimento, gatilho da descoberta).
  Registá-los aqui **antes** de olhar para a avaliação.

## 3. Baselines de comparação (já existentes, fixos)

| Cenário | Objetivo puro (7d) média±dp [100%] | Novelty fixo w=0.5 |
|---|---|---|
| Sandbox (none) | 38.3±31.0 [5/7] | — |
| **Muro em U** | 24.5±32.7 [3/7] | **7/7 a 100%, 69.8±5.9** |
| Gargalo | 121.4±20.0 [7/7] | — |
| Quatro Salas | 59.8±13.2 [7/7] | — |
| Porta Cooperativa | 69.8±1.0 [7/7] | — |
| Perceção Cooperativa | 19.0±8.7 [6/7] | — |
| **Porta c/ Alternativa (bypass)** | 86.7±2.0 [7/7] | **7/7 a 100%, 63.0±21.9** |

---

## 4. Plano de análise (pré-registado)

**Unidade estatística:** a **média por run** (n=7 por célula), NÃO o episódio — igual ao
resto da tese. Métrica: `food_collected` (recolhas/ep) da avaliação determinística (20 ep,
seeds emparelhadas), via `eval_by_run.py`. Sucesso reportado como descritivo, nunca como teste.

**Teste:** Mann-Whitney U exato + δ de Cliff sobre as médias por run. Igual às outras células.

### Testes confirmatórios (decididos agora)

- **T1 — Não-degradação (5 cenários fáceis):** adaptativo vs objetivo puro (7d) em
  `none, bottleneck, four_rooms, cooperative_door, cooperative_perception`. Bilateral.
  *Expectativa pré-registada:* **sem degradação significativa** em nenhum (δ pequeno).
- **T2 — Ganho no Muro em U:** adaptativo vs objetivo puro (7d) em `u_wall`. Unilateral
  (adaptativo > objetivo) na magnitude, **mais** a taxa de convergência (runs a 100%) como
  descritivo.
- **T3 — Sem custo no bypass:** adaptativo vs objetivo puro (7d) em `cooperative_door_bypass`.
  O ponto é NÃO reproduzir a perda do fixo (δ=−1.00). *Expectativa:* δ próximo de 0.
- **T4 — Adaptativo vs fixo:** adaptativo vs Novelty fixo `w=0.5` em `u_wall` e `bypass`
  (as duas únicas células onde o fixo existe). Testa se o anneal **melhora sobre a dosagem
  estática** — mantém o u_wall e recupera o bypass.

### Regra de decisão sobre a QI6 (pré-comprometida)

- **Sobe a resultado** (adaptativo passa de "trabalho futuro" a achado; reescreve QI6 +
  Trabalhos Futuros) **sse e só se**: T1 sem degradação nos 5 **E** T2 confirma o ganho no
  Muro em U (magnitude p<0.05 **ou** convergência ≥ 7/7 do fixo) **E** T3 sem custo no bypass.
- **Fica resultado nulo limpo** (adaptativo "seguro mas não benéfico"; QI6 **não muda**,
  mantém-se a leitura atual da novidade como instrumento direcionado) se T1 passa mas T2 falha.
- **Contraindicação honesta** (não recomendar dosagem adaptativa; reportar na mesma) se T1
  falhar — i.e., o adaptativo degrada algum dos 5 cenários fáceis.

### Compromissos de reporte (não negociáveis)

1. **Reportar TODOS os 7 cenários e TODOS os 7 runs.** Sem cherry-picking, sem "os 7 melhores
   de 10". As seeds são 1-7, fixas.
2. **Taxa de convergência = descritivo; magnitude (Mann-Whitney) = teste.** Nunca inferir
   significância de proporções com n=7 (Fisher 7/7 vs 3/7 dá p=0.070 — não chega).
3. Correção de multiplicidade: são vários testes (5 de não-degradação + 4 de foco). Reportar
   os p brutos **e** assinalar que, com n=7, o peso recai nos **tamanhos de efeito (δ)**, não
   em cruzar 0.05. Não transformar um p marginal num título.
4. Se o adaptativo não subir a QI6, a secção `sec:res_novelty` mantém-se; acrescenta-se só
   uma linha com a evidência preliminar do adaptativo. **Não reabrir texto fechado sem T1-T4.**

## 5. Análise secundária / exploratória (rotulada como tal)

- **Braços @390 min:** sensibilidade ao orçamento. Comparar o adaptativo @195 com o braço
  @390 (assim que a definição exata for confirmada, ponto 2). Rotulado **exploratório** — não
  entra na regra de decisão da QI6, que é a orçamento igualado (195).
- Curvas de `w(t)` (anneal): confirmar em avaliação o que o treino sugere (`w`→~0.005). Descritivo.

## 6. Mecânica da chegada (quando a campanha fechar, ~19-20 jul)

1. `python scripts/pos_campanha.py` (armadilha nº9 — modelos de junho contaminam eval local).
2. Confirmar `_run{1..7}` por cenário (armadilha nº8 — save do último run).
3. **Repor no servidor** `novelty_weight: 0.0` e o adaptativo desligado nos dois dirs.
4. Registar neste ficheiro (ponto 2) os parâmetros do anneal e a definição do braço @390,
   **antes** de correr a análise.
5. `eval_by_run.py` + `statistical_tests.py` → aplicar T1-T4 → aplicar a regra de decisão.

---

*Assinatura temporal: este plano existe no git antes de a campanha fechar (commit datado de
15 jul 2026). Qualquer desvio posterior a T1-T4 ou às regras de decisão deve ser justificado
e datado abaixo, não silenciosamente incorporado.*
