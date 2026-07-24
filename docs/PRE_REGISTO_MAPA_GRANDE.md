# Pré-registo — Campanha do MAPA GRANDE (8.º cenário)

> **Escrito a 24 jul 2026, ANTES de existir qualquer dado de treino ou avaliação
> neste mapa.** Segue o precedente do `PRE_REGISTO_NOVELTY_ADAPTATIVO.md` (cuja regra
> de decisão foi cumprida sem desvios a 19 jul) e do `PRE_REGISTO_MEGATREINO.md`.
>
> **Estado ao escrever:** o mapa está integrado no simulador (`classic_scenario:
> mapa_grande`, commit `22922fb`), verificado por 6/6 suites de teste, e **nunca foi
> treinado**. O mega-treino P1.5 ocupa o servidor até ~3 ago; esta campanha só arranca
> depois. Análise: SÓ com `eval_by_run.csv` (armadilha nº3); unidade estatística =
> média por run; Mann-Whitney U exato + δ de Cliff.

---

## 1. Pergunta e enquadramento

**QI7 (nova):** as conclusões obtidas em sete cenários de dificuldade isolada
transferem-se para um ambiente que **combina** essas dificuldades a uma escala 4×
maior — ou a composição faz emergir modos de falha que os cenários isolados não
revelam?

Motivação: os 7 cenários da tese testam **uma** dificuldade cada (um gargalo, um
beco, quatro salas, uma porta). O mapa grande junta-as num percurso único de ~143 m
(pior caso) contra 34 m do Quatro Salas. É a diferença entre saber resolver cada
exercício e resolver o problema composto — a objeção mais natural a um *benchmark*
por cenários isolados.

**Porque é que isto interessa à tese:** a contribuição mais forte é a transferência
Zero-Shot para **dimensões de enxame** não vistas (28/28 células a 100%). Este mapa
estende a mesma pergunta a **topologia** não vista. Se a GNN transferir, o argumento
da representação (grafo com atenção) passa de "invariante a N" a "invariante a N *e*
robusto a composição".

---

## 2. Desenho (congelado antes dos dados)

**Cenário** (geometria fixa, commit `22922fb`; ver `visualize_mapa_grande.py`):
arena r=60 m; labirinto 103×62 m em 5 zonas de oeste para este — **S** sala de
partida (aberta, obstáculos, spawn) · **A** gargalo + beco em U · **B** quatro salas
· **C** porta cooperativa + alternativa longa · **D** câmara do ninho.

| Parâmetro | Valor | Porquê (decidido agora, não depois) |
|---|---|---|
| `num_agents` | **20** | Mantém `obs_dim=111`, **igual aos 7 cenários** → comparação emparelhada e os modelos existentes carregam sem alteração. Com N=40 a dimensão passa a 211 e PPO/SAC precisariam de arquitetura nova. |
| `max_steps` | **2000** | v_max=0,2 m/passo → o pior spawn está a 629 passos **só de ida**. 2000 dá folga 3,2× sobre a ida — a mesma que o Quatro Salas tem com 500. |
| `required_to_eat` | **1** | A cooperação que este mapa mede está na **porta**. Exigir 3 no ninho empilharia uma 2.ª tarefa cooperativa e a métrica deixaria de isolar a navegação. |
| Obstáculos | **106, estáticos** | Estáticos, o mapa mede navegação+descoberta e é reprodutível. Móveis acrescentariam um eixo dinâmico que se confundiria com a dificuldade do labirinto. |
| Porta | com alternativa | Verificado: fechada custa +28,1 m (+23%), **não bloqueia**. Cooperar é vantajoso, não obrigatório. |

**Tudo o resto — recompensas (food 300), física, LiDAR (8 m, 8 raios), população,
sigma — congelado e idêntico às campanhas anteriores.** Sem isto a comparação com os
7 cenários não é limpa.

**Condições:** 3 algoritmos (GNN adaptativo, PPO, SAC) × **7 runs** × seeds 1-7,
orçamento igualado por algoritmo. GNN com Novelty **adaptativo** (w₀=0,5, sustain=10,
decay=0,98) — não o objetivo puro: a QI6 mostrou que o adaptativo domina o objetivo
onde há descoberta a fazer e não custa onde não há, e este mapa é o caso extremo de
descoberta (LiDAR de 8 m numa arena de 120 m ⇒ o agente vê ~7% da largura).

⚠️ **A registar aqui ANTES do unblinding:** o orçamento por run (min/run) e o
`num_generations` efetivo, assim que o servidor estiver livre e o custo por geração
for medido. Registar também o tempo real da primeira fase.

---

## 3. Fases

| Fase | O quê | Objetivo |
|---|---|---|
| **F0** | Treino local de ~1 h (GNN, 1 run) | **Smoke test.** Só confirma que arranca, que a fitness sobe e que os artefactos aparecem. **Não produz resultado nenhum** e não entra em nenhuma análise. |
| **F1** | **Zero-Shot de topologia**: avaliar os campeões dos 7 cenários (GNN/PPO/SAC, campanha 7d) neste mapa, **sem retreino** | Custa horas, não dias. Responde a "o que já sabíamos transfere?" |
| **F2** | Treino nativo: 3 algos × 7 runs × seeds 1-7 | A comparação principal (M1-M3 abaixo). |

F1 antes de F2 de propósito: o zero-shot é barato e a sua leitura não depende do
treino nativo — e o contraste F1 vs F2 é, em si, um resultado.

---

## 4. Hipóteses e testes confirmatórios

Métrica: `food_collected` (recolhas/ep) da avaliação determinística (20 ep/run,
seeds emparelhadas), via `eval_by_run.py`. Sucesso = descritivo, nunca teste.

- **M1 — GNN vs métodos de gradiente (magnitude).** GNN adaptativo vs PPO e vs SAC,
  bilateral, sobre médias por run (n=7).
  *Expectativa pré-registada:* a GNN **não é inferior** a nenhum dos dois. Não se
  pré-regista superioridade: nos 7 cenários a GNN ganha em 3, empata em 2 e perde
  no Sandbox — não há base para prever domínio num mapa composto.
- **M2 — Convergência.** Taxa de runs que atingem ≥1 recolha (descritivo) e runs a
  100% (descritivo). Com n=7, **nenhuma inferência sobre proporções** (Fisher 7/7 vs
  3/7 dá p=0,070 — não chega).
- **M3 — Uso da porta cooperativa.** Fração de episódios em que a porta é aberta,
  por algoritmo (descritivo + δ). Testa se a cooperação emerge quando é *vantajosa*
  mas não obrigatória — a pergunta que o `bypass` levanta, aqui a 143 m de distância.

### Regra de decisão sobre a QI7 (pré-comprometida)

- **Sobe a resultado** (secção nova no Cap. de Resultados + QI7 nas Conclusões)
  **se** F2 produzir ≥5/7 runs convergentes em pelo menos um algoritmo **e** M1 for
  interpretável (i.e., a campanha não degenerou).
- **Resultado negativo honesto, reportado na mesma** se nenhum algoritmo convergir:
  passa a evidenciar o **limite** dos três métodos sob composição+escala, e reforça a
  limitação já declarada na tese. Um mapa que nenhum algoritmo resolve **é** um
  resultado — não é uma campanha falhada, e não se repete com parâmetros diferentes
  à procura de um número melhor.
- **F1 (zero-shot) reporta-se em qualquer caso**, mesmo que dê 0 em todas as células.

### Compromissos de reporte (não negociáveis)

1. **Todos os 3 algoritmos, todos os 7 runs, todas as fases.** Sem cherry-picking.
2. Convergência = descritivo; magnitude (Mann-Whitney) = teste. Com n=7 o peso está
   no **δ**, não em cruzar 0,05.
3. **O mapa não entra nas tabelas dos 7 cenários** (`tab:res_eval`, `tab:res_signif`).
   Vai para uma secção própria: os 7 têm campanhas com orçamento e protocolo
   próprios, e misturá-los seria comparar coisas diferentes na mesma linha. Por isso
   `THESIS_SCENARIOS` está separado de `SCENARIOS` no código.
4. Se a campanha fechar depois de **22 ago** (hard stop de integração, herdado do
   `PRE_REGISTO_MEGATREINO.md`), **não entra na tese** — vai para a defesa.
5. Qualquer desvio a este documento é datado abaixo, nunca silencioso.

---

## 5. Modos de falha antecipados (escritos antes, para não serem racionalizados depois)

| Risco | Sinal | Resposta pré-decidida |
|---|---|---|
| Nenhum algoritmo chega ao ninho | 0 recolhas em todos os runs de F2 | **Reportar como está.** É o resultado, não um bug a contornar. Verificar só que o geodésico existe e que `max_steps` é o registado. |
| PPO/SAC não convergem em 2000 passos | fitness plana | Reportar. O custo por episódio é 4× o dos outros cenários — faz parte do que o mapa mede. |
| A porta nunca é aberta | M3 ≈ 0 em todos | Resultado legítimo: com alternativa a +23%, pode não compensar. **Não** tornar a porta obrigatória a meio. |
| Runs degenerados (agente preso na sala S) | recolhas 0 com fitness de homing alta | Reportar o run. Não substituir seeds. |
| Custo de treino maior que o previsto | fase F2 não fecha até 22 ago | Cortar F2 para 2 algoritmos (GNN + o melhor dos gradientes nos 7), **declarando-o**. Nunca reduzir runs abaixo de 7. |

---

## 6. Mecânica (quando a campanha fechar)

1. `python scripts/pos_campanha.py` (armadilha nº9 — modelos de campanhas
   anteriores contaminam evals locais).
2. Confirmar `_run{1..7}` por algoritmo (armadilha nº8).
3. Instalar em `results/mapa_grande/` **sem tocar nos modelos ativos** (precedente
   de 19 jul).
4. Repor configs no servidor.
5. `eval_by_run.py` → `statistical_tests.py` → M1-M3 → regra de decisão.

---

*Assinatura temporal: este plano existe no git antes de o mapa ter sido treinado uma
única vez (commit datado de 24 jul 2026).*
