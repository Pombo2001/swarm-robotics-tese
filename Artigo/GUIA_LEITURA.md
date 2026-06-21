# Guia de leitura — o artigo da dissertação

> Para leres com calma e dares a tua opinião. Tens aqui: (1) o que o **professor**
> pretende deste artigo; (2) o que **eu já escrevi** no draft (`artigo.tex`),
> secção a secção; (3) as **decisões** que dependem de ti.

---

## 1. O que o professor pretende deste artigo (do e-mail dele)

O Prof. Nunes foi explícito no e-mail. Em resumo:

- **Porquê existe:** "as notas acima de 17, na maioria dos nossos cursos, só são
  atribuídas às dissertações que apresentam, além da dissertação, **um artigo**."
  → O artigo é o que separa uma boa nota de uma nota de excelência. **É opcional
  no sentido formal, mas obrigatório se queres >17.**

- **O que é:** "tem normalmente de **6 a 8 páginas** e sensivelmente a **mesma
  estrutura da dissertação**, mas é uma **forma destilada** de comunicação dos
  resultados, em que a dissertação pode ser referida para mais detalhes."
  → Não é um resumo nem um capítulo novo. É a tese **condensada**: as mesmas
  secções (Intro → Estado da Arte → Método → Resultados → Conclusões), mas curtas,
  remetendo para a dissertação quando o leitor quiser o detalhe.

- **Para quem escreves** (o prof. insiste nisto):
  1. **O júri** — "convencer um júri de que a sua resposta é válida e o seu método
     de chegar à resposta foi adequado." O foco é a **validade do método** e da
     **resposta à pergunta de investigação**.
  2. **Os teus colegas do próximo ano** — que vão usar a tua dissertação como
     inspiração. → "escreva de forma clara e compreensível, também para eles."

- **Uma frase importante do e-mail** (alívio para ti): resultados negativos
  "acontecem muitas vezes e são, frequentemente, **uma resposta válida** à pergunta
  de investigação." → O facto de o GNN evolutivo **falhar** nos labirintos NÃO é um
  problema do trabalho; é um **resultado científico legítimo**, desde que bem
  explicado. O artigo deve assumir isso com confiança, não escondê-lo.

- **Obrigatório incluir:** o *acknowledgement* da ISTAR (texto exato que ele deu —
  já está no draft).

- **Formato:** modelo LaTeX **Elsevier `elsarticle`** (o que ele anexou) — é o que
  usei. Os exemplos que ele deu (IWSSIP "Occlusion-Aware Pedestrian Detection",
  etc.) servem para veres o **tom e a densidade** esperados.

**Em síntese, o professor quer:** uma versão curta (6–8 págs), honesta e clara da
tua tese, que convença o júri de que o **método** é sólido e a **resposta** (o
trade-off que encontraste) é válida — mesmo incluindo os resultados negativos.

---

## 2. O que eu já escrevi no draft (`artigo.tex`)

Escrevi um **primeiro rascunho completo** (todas as secções com texto real, não
"encher"). Está em **inglês** (norma dos exemplos do prof). Compila sem erros.
Tem ~3 páginas — **falta crescer** para as 6–8 (ver secção 3).

A **mensagem central** do artigo (a "história") é esta:

> *Não há um vencedor universal. Os métodos de gradiente (SAC, PPO) ganham na
> execução da tarefa num enxame de tamanho fixo; mas só a rede com atenção sobre
> grafo (o controlador evolutivo) escala para tamanhos de enxame nunca vistos
> (de 10 para 100 robôs) sem retreino. Há um **trade-off central**, e a escolha
> do paradigma depende do que a aplicação exige.*

Secção a secção, em linguagem simples:

- **Abstract / Resumo:** o problema (duas escolas que raramente se comparam), o
  que fizemos (benchmark dos 3 algoritmos em 6 cenários) e o achado principal
  (o trade-off). É a "montra" do artigo.

- **1. Introduction:** porque é que controlar enxames é difícil; a lacuna
  (faltam comparações diretas entre MARL e bio-inspirado); a nossa contribuição
  (um benchmark imparcial com 3 eixos: desempenho, robustez, escalabilidade).

- **2. Related Work:** versão curtíssima da tua revisão da literatura. Só com as
  referências **reais** (depois da limpeza de ontem). Posiciona o teu trabalho
  como a comparação sistemática que faltava.

- **3. Methodology:** o ambiente (foraging 3D, 6 cenários, LiDAR, recompensa
  geodésica), os 3 controladores (GNN evolutivo com atenção; PPO e SAC), e o
  protocolo de avaliação (Ptask, Rrobust, Sscale + testes estatísticos).

- **4. Results:** uma tabela com as taxas de sucesso; o *reward hacking* do PPO no
  Muro U; a escalabilidade (só o GNN escala, 15%→100%); a robustez (todos aguentam
  10% de falhas).

- **5. Discussion:** **o porquê** — o mecanismo do colapso do GNN (evolução cega à
  recompensa esparsa → "planalto de fitness"; variância entre execuções). E a
  ressalva honesta: estamos a comparar *arquitetura* E *método* ao mesmo tempo.

- **6. Conclusions:** a hipótese confirma-se **parcialmente**; o trade-off; o que
  fica para trabalho futuro.

- **Acknowledgements:** o texto da ISTAR, exato.

---

## 3. Decisões que dependem de ti (pensa nestas amanhã)

1. **Língua — inglês ou português?**
   Pus em **inglês** (todos os exemplos do prof são em inglês; um artigo costuma
   visar conferência internacional). Mas a tua tese está em português. **Decide:**
   inglês (recomendado) ou PT?

2. **O teu nome para a capa.**
   Pus "Gonçalo Pombo" (do teu e-mail/git). Confirma o nome completo como queres
   que apareça.

3. **Título.**
   Propus: *"Adaptive Learning versus Static Robustness: Benchmarking Reinforcement
   Learning and Neuroevolution for Swarm Control"*. Vê se gostas ou se preferes
   outro ângulo.

4. **Tamanho — falta crescer para 6–8 páginas.**
   O draft tem ~3. O que mais ajuda a chegar lá (e que o prof. vai querer ver):
   - **Figuras** (reaproveitadas da tese, já existem): mapa do simulador, curva de
     escalabilidade (15%→100%), um ou dois heatmaps, boxplots.
   - A **tabela de significância** completa (já a tens na tese).
   - Expandir um pouco o Related Work e os Resultados.
   As figuras sozinhas levam-no quase às 6 páginas.

5. **Que resultados usar?**
   Usei os **oficiais de 10 jun** (a fonte de verdade da tese). Quando o re-treino
   do GNN-48h terminar (~23 jun), podemos decidir se atualizamos algum número.

---

## Como ver o artigo
O PDF está em `Artigo/artigo.pdf` (abre-o para veres o aspeto Elsevier).
O texto-fonte é `Artigo/artigo.tex`. Para recompilar:
`pdflatex artigo` → `bibtex artigo` → `pdflatex artigo` (×2).
