# Rascunho — Resposta ao Prof. Luís Nunes

> **Estado:** rascunho, POR ENVIAR (15 jun 2026).
> O retreino com as correções ainda está a decorrer (acaba ~22h de 15 jun). Decisão pendente:
> enviar já ou esperar os gráficos novos do GNN para anexar (mais forte mostrar o GNN já corrigido).

**Assunto:** Re: Resultados do treino de 24h — explicação do GNN evolutivo e correções

---

Caro Professor Luís Nunes,

Obrigado pelo feedback detalhado. Respondo abaixo ponto a ponto às questões que levantou sobre o GNN, e descrevo as correções que já apliquei na sequência da sua análise.

## 1. Que tipo de evolução, com que parâmetros e com que função de fitness

O algoritmo é um **algoritmo evolutivo de neuroevolução, implementado de raiz** (sem bibliotecas externas), da família dos algoritmos genéticos simples com **mutação gaussiana e seleção por truncamento** (próximo de um (μ+λ)-ES). O genoma é o vetor 1D com todos os pesos e biases da rede de política (topologia fixa). Parâmetros:

- **População:** 30 indivíduos
- **Seleção / elitismo:** os 20% melhores (6 de 30) são preservados sem mutação; os restantes nascem **só** a partir desses elites (truncation selection)
- **Mutação:** é o único operador (não há crossover). Para cada peso, com probabilidade `mutation_rate = 0.1`, soma-se ruído gaussiano `N(0, σ)`
- **σ (desvio da mutação):** começa em `0.1` e decai 0.5%/geração até um mínimo de `0.01` (exploração ampla no início, afinação no fim)
- **Avaliação:** cada genoma é avaliado em **4 episódios** (ver ponto 3 — era 1 antes)

A **função de fitness** é:

J(θ) = f̄ × 10000 + 5000 · tanh( R̄ / 5000 )

onde **f̄** = nº médio de recolhas (a tarefa pura) e **R̄** = retorno acumulado médio (a recompensa com *shaping* geodésico, igual à dos PPO/SAC).

## 2. Em que difere a fitness da recompensa (e porque é possível aumentar uma sem a outra)

O Professor pôs o dedo exatamente no problema. A **recompensa** (R̄) é o retorno acumulado com *shaping* (aproximar-se geodesicamente da comida, etc.). A **fitness** foi deliberadamente desenhada para que a **tarefa domine**: cada recolha vale 10000, e o *shaping* entra apenas comprimido por `tanh` numa banda de (−5000, +5000), como gradiente/desempate **quando ainda ninguém recolhe**.

Isto separa as duas grandezas precisamente porque é possível **aumentar a recompensa sem aumentar a tarefa** — um agente que apenas ronda a comida acumula *shaping* positivo (recompensa sobe) sem nunca recolher (f̄ = 0). Foi este o *reward hacking* que observámos quando a fitness era a recompensa bruta (fitness ~98k com 0 recolhas). A fórmula atual penaliza isso: sem recolhas, a fitness fica limitada ao termo `tanh` (≤ 5000).

## 3. As "quedas estranhas" na recompensa média — causa identificada e corrigida

Investiguei as quedas que assinalou e a causa foi **dupla**:

- **(a) Variância de avaliação.** Cada genoma era avaliado num **único** episódio e a *seed* mudava a cada geração. Um campeão tinha sorte numa *seed* (1–2 recolhas → fitness ~15–18k → eleito), mas não generalizava; na geração seguinte, com outra *seed*, caía. Isto explica os saltos do tipo `gen7 = 18948 → gen8 = 8563`.
- **(b) Saturação da fitness.** A versão anterior usava `clip(shaping, ±5000)` em vez de `tanh`. Quando ninguém recolhia (os labirintos), o termo saturava no teto `+5000` para **todos** os genomas → a fitness ficava constante (ex.: `5000.0` exato) → a seleção ficava **cega** e a evolução não tinha gradiente. (Era também a origem dos números redondos — 5000/15000/75000 — nos logs.)

**Correções já aplicadas:**

1. Avaliação passou de **1 → 4 episódios** por genoma, com **seeds fixas** ao longo de toda a evolução (sinal de seleção estável, sem ruído de *seed*).
2. `clip(±5000)` → `5000·tanh(R̄/5000)`: monótona, nunca satura abruptamente, dá sempre gradiente à seleção mesmo quando ainda não há recolhas.
3. Mantive (e confirmei) o **elitismo** que sugeriu — já existia a 20%.

Validei numericamente as alterações e o sinal de seleção ficou monótono não-decrescente (sem as quedas). **Está neste momento a correr um novo treino com estas correções** para confirmar o efeito nos resultados completos; envio os gráficos assim que terminar.

## 4. Diferença no comportamento final do GNN vs. PPO/SAC na Perceção Cooperativa

Os *heatmaps* de ocupação respondem diretamente a esta pergunta e **corroboram a sua hipótese** de que havia um problema na fitness (e não apenas evolução mais lenta):

- **PPO:** varrimento radial denso a partir do centro — cobre o espaço de forma sistemática (~100 recolhas)
- **SAC:** ocupação densa e espalhada por toda a arena (~142 recolhas)
- **GNN:** trajetórias **orbitais esparsas que não cobrem o centro** — ~2 recolhas

Ou seja, o comportamento do GNN era genuinamente pior (não apenas mais lento), o que aponta para o problema de fitness que corrigi acima.

## 5. Comparação entre cenários

Concordo — comparar cenários entre si com funções/escalas diferentes não é informativo. Corrigi os gráficos: cada algoritmo passa a ter o **seu próprio eixo** (a fitness do GNN deixou de partilhar eixo com a recompensa do PPO/SAC) e as barras gerais passaram a usar as **recolhas** (`food_collected`), que é a métrica de tarefa comparável entre todos.

## 6. 7º cenário (porta com percurso alternativo longo)

Achei a sugestão muito pertinente — testar se a aprendizagem "descobre" a cooperação mesmo havendo um percurso sub-ótimo sem porta. Vou incluí-lo como cenário adicional / trabalho futuro, sem substituir as experiências já realizadas.

Cumprimentos,
Gonçalo

---

## Notas internas (não enviar)

- **Referência da mutação:** o prof. perguntou (email de maio) se a estratégia veio de alguma referência. A descrição é honesta (GA simples com mutação gaussiana). Referência mais próxima para citar, se quiseres: **Such et al. 2017, "Deep Neuroevolution"**. (A tese atualmente diz "Salimans et al. 2017" na linha 442 do `main.tex` — algo impreciso, o nosso é GA com truncation+elitismo, não o NES de Salimans.)
- **Anexos sugeridos quando enviar:** heatmaps de ocupação (coop_perception, os 3 algoritmos), gráficos `comparacao_mapa_*` em painéis separados, curva de fitness do GNN já com `tanh`.
- Idealmente esperar o fim do treino de 24h (acaba ~22h de 15 jun) para anexar o GNN corrigido.
