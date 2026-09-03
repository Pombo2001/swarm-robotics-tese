# A tese em memória — folha de estudo para a defesa

> Escrita a 3 set 2026 contra o PDF de **141 páginas** (`Tese/main.pdf`). Tudo o
> que está aqui está na dissertação; nenhum número foi arredondado de forma
> diferente da tese. Companheira do [`DEFESA_PERGUNTAS.md`](DEFESA_PERGUNTAS.md)
> (as perguntas que vêm primeiro) e dos slides em `Defesa/slides_defesa.pptx`
> (19 slides gerados por `Defesa/gerar_slides.py`, com as notas de orador; o 18.º é a demo ao vivo do Muro em U no painel).

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
2. **Bancada.** Simulador 3D próprio, foraging cooperativo, LiDAR 8 m, 20
   agentes, 7 cenários que isolam uma dificuldade cada + 1 que as compõe.
3. **QI1 — não há dominante.** 15/21 células a 100 %. GNN ganha em 3 (Quatro
   Salas, Porta Cooperativa, Perceção), empata PPO nos gargalos; PPO ganha o
   Sandbox; Muro em U ninguém (bimodal nos três).
4. **QI5 — a fitness era a causa.** O «colapso do evolutivo» era *fitness
   exploitation*: o homing terminal geodésico levou 28 execuções de 0 % a 100 %.
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
| **3** | E com 10 % de falhas? | Retenção 92–106 % nas 21 células, nos três: parameter sharing + observação local. Não é critério. |
| **4** | Quando preferir? | N fixo + cómputo → PPO; N variável/escala → grafo; navegação estruturada → evolutivo c/ homing; deceção → novidade adaptativa. |
| **5** | A fitness importa? | Decisivamente: homing terminal geodésico, 0 % → 100 % em 28 execuções. Resolve o crédito, não a descoberta. |
| **6** | A novidade ajuda? | Sim onde a deceção morde (7/7 vs 3/7, p=0,026), com custo onde não (δ=−1,00); doseada adaptativamente, sem custo; **28/28** a n=28. |
| **7** | Compõe-se? | Não dentro deste orçamento: 4/21 < 15. Degrada a fiabilidade, não a magnitude. |

## 4. Os números para decorar

**Protocolo**
- 3 algoritmos × 7 cenários × **7 execuções** = **147 treinos**; **20 episódios**
  determinísticos emparelhados por modelo → **2 940 episódios**.
- Orçamentos: GNN **195 min**/execução (população 30); PPO/SAC **48 min** (16
  ambientes). Núcleos-hora: GNN **97,6** vs PPO/SAC **12,8** (**7,6× ≈ 8×** a
  favor do gradiente — a ordem importa, e escrita sem rótulos já induziu erro).
- Unidade estatística = **execução**; Mann-Whitney U, **δ de Cliff** (|δ| ≥
  0,474 grande), α = 0,05. Três **pré-registos**. **18 verificadores**.
- Simulador: 139 → **420 passos/s** após vetorização (2,58× no passo; LiDAR 19,5×),
  equivalência bit-exata.

**Tabela de avaliação (recolhas/ep · sucesso · execuções a 100 %)**

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
  GNN objetivo vs PPO p = 0,088 (indistinguíveis).
- Ablação da temperagem (4 variantes): 7/7 em ambos os cenários — insensível à afinação.

**Escala (QI2)** — GNN, recolhas por agente, N=20 → N=100 e retenção: Sandbox
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
- «O que a composição degrada é a fiabilidade, não a magnitude.»
- «A unidade estatística é a execução, não o episódio.»
- «Cada número da tese é conferido contra os CSV a cada commit.»

## 6. As limitações que admito antes de me perguntarem

1. **Arquitetura assimétrica** (grafo só no evolutivo) — e é isso que permite
   atribuir a escala à representação. Trabalho futuro n.º 1.
2. **7 execuções** — replicado a 28 onde a leitura é de contagens.
3. **Orçamento**: 7/21 células ainda subiam; SAC nos gargalos = limite inferior
   (α = 0,1 fixo, declarado na p. 68).
4. **Só simulação.**
5. **Dimensão vertical** usada mas não observada (ρ = −0,74 com as recolhas).
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
| Simulador, cenários, recompensa | Cap. 4 (p. ~55–66) |
| RS2C / PPO / SAC / neuroevolução / novidade | Cap. 5 (p. ~67–72) |
| Protocolo e notas de leitura | §6.1 (p. 73–74) |
| Tabela de avaliação e significância | §6.2 e §6.12 (tab. res_eval, res_signif) |
| Novidade e mega-treino | §6.10 (p. ~85–90) |
| Mapa composto | §6.11 |
| Escala / robustez / custo | §6.12–6.14 |
| Limitações | §7.3 (p. ~93–96) |
| Guião de perguntas | `docs/DEFESA_PERGUNTAS.md` |
