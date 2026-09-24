# A tese em memória — folha de estudo para a defesa

> Escrita contra o PDF de **137 páginas** de 6 set 2026 (`Tese/main.pdf`), já na formatação
> das normas do Iscte; as páginas citadas são as **impressas no rodapé** — soma 22
> para chegar à página do leitor de PDF. Tudo o
> que está aqui está na dissertação; nenhum número foi arredondado de forma
> diferente da tese. Companheira do [`DEFESA_PERGUNTAS.md`](DEFESA_PERGUNTAS.md)
> (as perguntas que vêm primeiro) e dos slides em `Defesa/slides_defesa.pptx`
> (20 de apresentação + 6 de reserva, gerados por `Defesa/gerar_slides.py`, com as
> notas de orador e o orçamento de tempo; o 18.º é a demo ao vivo do Muro em U no
> painel). O guião de tempo está na §9, os slides de reserva na §10.

---

## 1. Em trinta segundos

Comparei, no mesmo simulador e com o mesmo protocolo, dois paradigmas de
controlo descentralizado de enxames — **MARL por gradiente** (PPO e SAC, uma MLP
com partilha de parâmetros) e **neuroevolução** de uma **rede de grafos com
atenção** — em **oito cenários** de dificuldade crescente, 7 execuções por
célula, avaliação determinística, estatística não-paramétrica sobre execuções,
campanhas pré-registadas. A hipótese de partida — a inteligência adaptativa do
MARL supera a robustez estática bio-inspirada em stress — **confirma-se só em
parte, e não onde a punha**: a vantagem de escala existe mas está na
**representação** (o grafo, que transfere de N=10 a N=100 sem retreino), não no
otimizador; nos cenários de gradiente enganador o que decide é o **desenho do
sinal de treino** e a **exploração doseada adaptativamente**, não o paradigma;
os métodos de gradiente ficam com a fiabilidade em espaço aberto e ≈ 8× menos
cómputo. Sem vencedor universal — um mapa de escolha.

## 2. A história em sete passos (a ordem em que os resultados se desbloqueiam)

1. **Lacuna.** Duas escolas (bio-inspirada offline vs. MARL online) e quase
   nenhuma comparação direta, com estatística, em cenários difíceis.
2. **Bancada.** Simulador 3D próprio, navegação cooperativa até ao ninho, LiDAR 8 m, 20
   agentes, 7 cenários que isolam uma dificuldade cada + 1 que as compõe.
3. **QI1 — não há dominante.** 15/21 células a 100 %. GNN ganha em 3 (Quatro
   Salas, Porta Cooperativa, Perceção), empata PPO nos gargalos; PPO ganha o
   Sandbox; Muro em U ninguém (bimodal nos três).
4. **QI5 — a fitness era a causa.** O «colapso do evolutivo» era *fitness
   exploitation*: com o homing terminal geodésico, os quatro gargalos passaram de 3/12
   execuções com chegadas (fitness antiga, treino) a 28/28 a 100 %.
   Necessário, não suficiente: o Muro em U continuou bimodal.
5. **QI6 — a novidade compra a descoberta.** Peso fixo: 7/7 no Muro em U mas
   custo na Porta com Alternativa. Dosagem adaptativa (pré-registada): 7/7 sem
   custo; a n=28, **28/28 vs 15/28** (objetivo) **vs 14/28** (PPO e SAC).
6. **QI2/QI3 — escala e falhas.** Só o grafo transfere (100 % em 28/28
   combinações; PPO/SAC incompatíveis por construção). Falhas de 10 %:
   92–106 % de retenção nos três — não discrimina.
7. **QI7 — a composição degrada a fiabilidade.** Zero-shot: 0 em 84/84 células
   (mapa resolúvel: navegador geodésico 53,0 rec/ep). Treino nativo: só o GNN,
   4/21 < limiar 15 pré-registado. **Negativo, reportado.**

## 3. As sete questões — resposta de uma linha

| QI | Pergunta | Resposta |
|---|---|---|
| **1** | Qual paradigma é mais eficaz? | Nenhum domina: GNN (homing) superior em 3/7, empate no Gargalo e Porta c/ Alt.; PPO generalista fiável e ganha o Sandbox; SAC frágil nos gargalos; Muro em U por resolver. |
| **2** | Transfere-se para N≠20? | Só o grafo: 100 % em 28 combinações (N=10…100); MLP de entrada fixa (ℝ¹¹¹) é incompatível. Propriedade da **representação**. |
| **3** | E com 10 % de falhas? | Retenção 92–106 % nas 21 células, nos três: parameter sharing. Não é critério. |
| **4** | Quando preferir? | N fixo + cómputo → PPO; N variável/escala → grafo; navegação estruturada → evolutivo c/ homing; deceção → novidade adaptativa. |
| **5** | A fitness importa? | Decisivamente: homing terminal geodésico, 3/12 → 28/28 (entre campanhas, não ablação). Resolve o crédito, não a descoberta. |
| **6** | A novidade ajuda? | Sim onde a deceção morde (7/7 vs 3/7, p=0,026), com custo onde não (δ=−1,00); doseada adaptativamente, sem custo; **28/28** a n=28. |
| **7** | Compõe-se? | Não dentro deste orçamento: 4/21 < 15. Degrada sobretudo a fiabilidade. |

## 4. Os números para decorar

**Protocolo**
- 3 algoritmos × 7 cenários × **7 execuções** = **147 treinos**; **20 episódios**
  determinísticos emparelhados por modelo → **2 940 episódios**.
- Orçamentos: GNN **195 min**/execução (população 30); PPO/SAC **48 min** (16
  ambientes). Núcleos-hora: GNN **97,6** vs PPO/SAC **12,8** (**7,6× ≈ 8×** a
  favor do gradiente — a ordem importa, e escrita sem rótulos já induziu erro).
- Unidade estatística = **execução**; Mann-Whitney U, **δ de Cliff** (|δ| ≥
  0,474 grande), α = 0,05. Três **pré-registos**.
- Verificação: **28 verificadores**, 21 deles no hook de pre-commit (~965 valores
  no principal, 72 no do mapa composto, 45 no da configuração); ensaio de
  mutação com **92 mutações**, todas apanhadas; cobertura medida — 1 043 dos
  2 286 tokens numéricos do `main.tex` (46 %), com a lista do que falta.
- Simulador: 139 → **420 passos/s** após vetorização (2,58× no passo; LiDAR 19,5×),
  equivalência bit-exata.

**Quadro de avaliação (chegadas/ep · sucesso · execuções a 100 %)**

| Cenário | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 38,3 · 86 % · 5/7 | **71,5** · 100 % · 7/7 | 69,2 · 100 % · 7/7 |
| Muro em U | 24,5 · 43 % · 3/7 | 39,6 · 71 % · 4/7 | 9,0 · 34 % · 2/7 |
| Gargalo | 121,4 · 100 % · 7/7 | **123,2** · 100 % · 7/7 | 41,4 · 72 % · 5/7 |
| Quatro Salas | **59,8** · 100 % · 7/7 | 33,6 · 100 % · 7/7 | 31,8 · 100 % · 7/7 |
| Porta Cooperativa | **69,8** · 100 % · 7/7 | 67,1 · 100 % · 7/7 | 62,1 · 100 % · 7/7 |
| Perceção Cooperativa | **19,0** · 91 % · 6/7 | 15,3 · 100 % · 7/7 | 16,1 · 100 % · 7/7 |
| Porta com Alternativa | **86,7** · 100 % · 7/7 | 85,3 · 100 % · 7/7 | 68,6 · 100 % · 7/7 |

Significância (n=7): GNN > PPO e SAC em Quatro Salas, Porta Cooperativa e
Perceção (δ ≥ +0,71); GNN > SAC no Gargalo e Porta c/ Alt. (δ = +1,00), empate
com PPO (p = 0,21 / n.s.); PPO e SAC > GNN no Sandbox (δ = ±1,00); Muro em U:
nada significativo.

**Novidade (QI6)**
- Peso fixo w=0,5, orçamento igualado: Muro em U **7/7**, 69,8 ± 5,9 vs 24,5 ±
  32,6 (p = 0,026, δ = +0,71); Porta c/ Alt. 63,0 vs 86,7 (p = 0,0006, δ = −1,00).
- Adaptativo (pré-registado, T1–T4): Muro em U 7/7, 68,5 ± 13,1 (p = 0,009, δ =
  +0,76); Porta c/ Alt. 77,2 vs 86,7 (n.s.); vs peso fixo δ = +0,59.
- Controlo de orçamento: objetivo puro com 390 min → **4/7**, 31,5 ± 35,0 (não se
  compra com tempo). Adaptativo 390 min: 77,8 (U) e **88,7 ± 0,6** (Porta c/ Alt.)
  — o melhor da tese.
- **Mega-treino n=28**: adaptativo **28/28**, 67,4 ± 13,4; objetivo 15/28, 32,5;
  PPO 14/28, 35,6; SAC 14/28, 10,1 (nenhuma execução > 45,4). Fisher p < 0,0001;
  GNN objetivo vs PPO p = 0,088 (indistinguíveis). Na Porta com Alternativa, a
  n=28 o adaptativo supera o peso fixo **com** significância (80,9 vs 63,0;
  p = 0,0016, δ = +0,77) — o efeito que a n=7 ficara aquém do limiar.
- Ablação da temperagem (4 variantes): 7/7 em ambos os cenários — insensível à afinação.

**Escala (QI2)** — GNN, chegadas por agente, N=20 → N=100 e retenção: Sandbox
3,29 → 1,27 (39 %); Perceção 45 %; Gargalo 58 % (passagem única de 2,5 m; totais
138,6 → 403,6); Quatro Salas 66 %; Muro em U 78 %; Porta Coop. 88 %; Porta c/
Alt. **90 %**. Sandbox totais: 37,4 → 65,8 → 97,5 → 127,3.

**Robustez (QI3)** — retenção **92–106 %** (GNN nos labirintos 92–97 %; o 106 %
do SAC na Perceção é menos congestão, dentro do desvio).

**Mapa composto (QI7)** — 103 × 62 m, raio 60 m (vs 15), 128,8 m do spawn ao
ninho, 106 obstáculos. F1 zero-shot: **0,00 em 84/84 células, 1 680 episódios**,
4 condições (escala da observação, sem obstáculos, sem features da porta
excluídas). Navegador geodésico: **53,0** rec/ep (82,0 no Quatro Salas). F2 nativo,
21 execuções × 3 algoritmos: GNN **4/21** (limiar pré-registado 15), 1,7 rec/ep;
PPO e SAC 0/21. 19/21 execuções ainda a subir no último quinto (780 min).

**Custo** — 28 sessões, **2 078 h** de treino; mega-treino de 1 mês (stream B 341 h).

## 5. Frases que podes dizer tal e qual

- «Não há vencedor universal; há um mapa de escolha.»
- «A vantagem de escala está na representação, não no otimizador.»
- «O colapso do evolutivo era um artefacto do sinal de treino — *fitness
  exploitation* — e não uma limitação do paradigma.»
- «A exploração tem preço; doseada adaptativamente, deixa de ter.»
- «O que separa os braços no Muro em U não é o paradigma, é a dosagem da
  exploração: o GNN objetivo e o PPO são indistinguíveis.»
- «O que a composição degrada é sobretudo a fiabilidade.»
- «A unidade estatística é a execução, não o episódio.»
- «Cada número da tese é conferido contra os CSV a cada commit.»

## 6. As limitações que admito antes de me perguntarem

1. **Arquitetura assimétrica** (grafo só no evolutivo) — representação e
   otimizador não ficam isolados. Trabalho futuro n.º 2.
1. **Perceção global do enxame** — cada robô vê todos os outros, sem limite de
   alcance; local é só a perceção dos obstáculos. Comum aos três.
2. **7 execuções** — replicado a 28 onde a leitura é de contagens.
3. **Orçamento**: 7/21 células ainda subiam; SAC nos gargalos = limite inferior
   (α = 0,1 fixo, declarado na p. 44).
4. **Só simulação.**
5. **Dimensão vertical** usada mas não observada (ρ = −0,74 com as chegadas).
6. **Duas costuras na física das paredes** (teto e junções em T): 11 de 343
   modelos atravessam, todos GNN; na campanha final 3/70 (Quatro Salas, execuções
   1, 4, 6), sem inflacionar (55,7 vs 60,3); a A1 adaptativa nas Quatro Salas
   está contaminada.
7. **Spawn no Gargalo** sobrepõe a barreira (17,9 %) — penaliza, não favorece.
8. **QI7 num só mapa.**

## 7. O que NÃO dizer

- «O PPO também escalaria com atenção» — não foi medido.
- Um número que a tese não diga. «Não medi isso» é sempre melhor.
- «A novidade melhora sempre» — com peso fixo custa (δ = −1,00 na Porta c/ Alt.).
- «O evolutivo é melhor» — é melhor em navegação estruturada e ≈ 8× mais caro.
- Que a QI7 «quase» deu — deu negativo, com o limiar fixado antes dos dados.

## 8. Onde está cada coisa (para procurar na hora)

| O quê | Onde |
|---|---|
| QIs | Cap. 1, §Questões de Investigação (p. 4–5) |
| Simulador, cenários, recompensa | Cap. 4 (p. 29–42) |
| RS2C / PPO / SAC / neuroevolução / novidade | Cap. 5 (p. 43–48) |
| Protocolo e notas de leitura | §6.1 (p. 49–50) |
| Quadro de avaliação e significância | §6.2 (p. 51) e §6.15 (p. 81) |
| Novidade e mega-treino | §6.10 (p. 61–65) |
| Mapa composto | §6.11 |
| Escala / robustez / custo | §6.12–6.14 |
| Limitações | §7.3 (p. 89–92) |
| Guião de perguntas | `docs/DEFESA_PERGUNTAS.md` |

## 9. O guião em 15 minutos

O plano vive em `Defesa/gerar_slides.py` (lista `PLANO`) e é escrito nas notas de
cada slide: cada uma abre com `[começa → sai · duração]`. Soma **14:40** e deixa
20 s de folga — um plano que usa os quinze minutos todos falha no primeiro
tropeção. **Dois relógios para decorar: ao entrar na QI6 devem ser 7:25; ao sair
dela, 8:40.** Se estiveres atrasado aí, corta a §Fiabilidade e a §Contributos —
são as duas que a conclusão repete.

| # | Slide | dura | sai a | A frase que tem de sair |
|---|---|---|---|---|
| 1 | Capa | 20 s | 0:20 | «Quinze minutos: o problema, o método, sete perguntas e as respostas.» |
| 2 | Roteiro | 20 s | 0:40 | «Cinco partes: contexto, método, resultados, balanço e demo.» |
| 3 | O problema | 45 s | 1:25 | «Faltam comparações diretas, com estatística, em cenários difíceis.» |
| 4 | Sete questões | 40 s | 2:05 | «Quatro comparam paradigmas; três descem aos mecanismos.» |
| 5 | Simulador e cenários | 60 s | 3:05 | «Sete cenários isolam uma dificuldade cada; o oitavo compõe quatro.» |
| 6 | Os três controladores | 50 s | 3:55 | «Mesmo simulador e mesma observação; a arquitetura é a variável que difere.» |
| 7 | O protocolo | 45 s | 4:40 | «A unidade estatística é a execução, não o episódio.» |
| 8 | **QI1** — desempenho | 65 s | 5:45 | «Não há vencedor universal: 15 das 21 células a 100 %.» |
| 9 | A forma da distribuição | 40 s | 6:25 | «Com n=7 a caixa mente: o Muro em U é bimodal, não “média 24,5”.» |
| 10 | **QI5** — a fitness | 60 s | 7:25 | «O colapso do evolutivo era o sinal de treino: de 3 em 12 execuções com chegadas para 28 em 28.» |
| 11 | **QI6** — deceção | 75 s | 8:40 | «28/28 contra 15/28: decide a dosagem da exploração, não o paradigma.» |
| 12 | **QI2** — escala | 50 s | 9:30 | «Zero-shot é propriedade da representação, não do otimizador.» |
| 13 | **QI3** — falhas | 30 s | 10:00 | «92–106 % nos três: a robustez não discrimina — e isso é uma resposta.» |
| 14 | **QI7** — composição | 60 s | 11:00 | «A resposta é negativa, e o limiar estava fixado antes dos dados.» |
| 15 | **QI4** — mapa de escolha | 40 s | 11:40 | «Em vez de um vencedor, os eixos que devem ditar a escolha.» |
| 16 | Limitações | 40 s | 12:20 | «A assimetria é a primeira limitação — e é o que permite atribuir a escala à representação.» |
| 17 | Contributos | 30 s | 12:50 | «O principal é metodológico: a fitness era a causa e a cura.» |
| 18 | Conclusão | 35 s | 13:25 | «A vantagem de escala está na representação, não no otimizador.» |
| 19 | Demo ao vivo | 60 s | 14:25 | «Qualquer número do painel tem proveniência: dois cliques até ao CSV.» |
| 20 | Obrigado | 15 s | 14:40 | — |

> O rodapé dos slides numera a partir da 2.ª (a capa e o «Obrigado» não levam
> número): o slide 11 desta tabela mostra **10** no canto. É por esse rótulo que
> a demo remete para o plano B.

## 10. Os slides de reserva — que anexo para que pergunta

Vêm depois do «Obrigado», numerados **A1–A6** e com o rodapé a dizer que não
fazem parte da apresentação. Não se mostram: salta-se para eles quando a pergunta
vier. Cada um projeta a tabela que, sem ele, terias de citar de memória — e a
diferença entre dizer «cerca de oito vezes mais caro» e mostrar 97,6 contra 12,8
é a diferença entre ter estudado e ter medido.

| Anexo | Responde a | O que projeta |
|---|---|---|
| **A1** | «e no cenário X?» · «essa diferença é significativa?» | as 21 células — chegadas/ep · sucesso · execuções a 100 % — e a linha de significância |
| **A2** | «a novidade é robusta?» · «e com mais execuções?» | os quatro braços a n=7 e a n=28, os controlos de orçamento e a ablação |
| **A3** | «a QI7 deu negativo — vale o quê?» | as duas fases, o navegador geodésico a 53,0 e o limiar pré-registado de 15 |
| **A4** | «8× mais caro, a comparação é justa?» · «o SAC está mal configurado» | 97,6 vs 12,8 núcleos-hora, e o α = 0,1 declarado na p. 44 |
| **A5** | «o que é, ao certo, uma execução que falha?» | os três mapas de ocupação no Muro em U — o corredor que o SAC nunca encontra |
| **A6** | «como sabemos que os números são os dos dados?» | 28 verificadores, 92 mutações, e a cobertura medida com a lista do que falta |

## 11. Vocabulário — a definição em uma linha

Para não hesitar num termo. É o mesmo glossário da cábula
(`Defesa/cabula.html`, secção 20), que o «Modo teste» tapa e revela ao toque.

| Termo | Uma linha |
|---|---|
| **Dec-POMDP** | Processo de decisão de Markov parcialmente observável, descentralizado e cooperativo. Cada agente decide com a sua observação; todos partilham a recompensa. |
| **Parameter sharing** | Os N agentes partilham um único conjunto de pesos. Multiplica o *batch* efetivo por N e dá a redundância que explica a robustez a falhas. |
| **PBRS** | *Potential-based reward shaping*, 10·(Φₜ₋₁ − Φₜ). Na forma exata de Ng et al., γΦ(s′) − Φ(s), não altera a política ótima; aqui falta o γ (= 0,99), pelo que a preserva só de forma aproximada — a tese declara-o. |
| **Distância geodésica** | Caminho mais curto que contorna os obstáculos (Dijkstra 8-conexa, grelha 0,4 m). Elimina o mínimo local de «contornar afasta» que a euclidiana cria. |
| **Fitness exploitation** | O análogo evolutivo do *reward hacking*: a população maximiza o termo de *shaping* sem cumprir a tarefa, e a aptidão satura num planalto sem pressão seletiva. |
| **Homing terminal** | clip((Φ₀ − Φ_T)/Φ₀, 0, 1): só depende dos estados extremos do episódio, pelo que vaguear não o aumenta. É a cura da QI5. |
| **Novelty search** | Troca parte da pressão pelo objetivo por pressão pela diversidade comportamental. Influencia só a **seleção**; o campeão reportado é sempre o melhor pelo objetivo. |
| **Dosagem adaptativa** | O peso da novidade decai depois de a descoberta se sustentar: paga-se exploração enquanto ela compra descoberta, e deixa de se pagar quando não compra. |
| **BC** | *Behaviour characterization*: o descritor que resume o comportamento de um genoma. Aqui, o centroide final do enxame, (x, y) ∈ ℝ². |
| **Zero-shot transfer** | Aplicar a política treinada com N=20 a N ∈ {10, 50, 100} **sem qualquer retreino**. |
| **Deceptive** | Paisagem em que seguir o gradiente da recompensa afasta da solução. O Muro em U por geometria; a Porta com Alternativa por desenho. |
| **Bimodal** | A distribuição das execuções tem dois picos e nada no meio — resolve ou fica a zero. A média não descreve nenhuma delas; por isso se reportam pontos. |
| **δ de Cliff** | Tamanho de efeito não-paramétrico em [−1, 1]: fração de pares em que A supera B, menos a inversa. \|δ\| ≥ 0,474 convenciona-se grande; ±1,00 é separação total. |
| **Mann-Whitney U** | Teste não-paramétrico para amostras independentes — o de todas as comparações entre algoritmos, sobre as médias por execução. O Wilcoxon *signed-rank* só aparece no teste preliminar da novidade, feito por episódio. |
| **Retenção per capita** | Chegadas por agente a N=100 a dividir pelas de N=20. Mede diluição do recurso, não perda de coordenação. |
| **Núcleos-hora** | Núcleos × horas de uma execução: a moeda que torna comparáveis 195 min com 30 genomas e 48 min com 16 ambientes. |
| **Estigmergia** | Coordenação por sinais deixados no ambiente. Aqui, o bit que ativa quando um vizinho chega ao ninho e repousa — recrutamento sem comunicação explícita. |
| **Wall-sliding** | Em vez de imobilizar o agente contra um muro, projeta-se o movimento ortogonalmente à normal da face: o agente desliza. |
| **Deployment gap** | O fosso entre o desempenho em simulação e no robô físico. Antecipado no desenho do simulador, mas **não** validado nesta tese. |
| **Guilhotina** | Corte precoce do episódio de avaliação evolutiva: se a recompensa acumulada for inferior a −200 aos 150 passos, termina e o genoma leva −1000. Poupa CPU em genomas disfuncionais. |
