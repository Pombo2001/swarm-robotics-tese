# Guião de defesa — as perguntas que vêm primeiro

> Escrito a 18 ago 2026 e revisto a 7 set 2026, contra o PDF de **137 páginas**
> já na formatação das normas do Iscte. Cada
> pergunta tem: o que está mesmo a ser perguntado, a resposta curta, e a
> **página** onde está a prova. As páginas são as **impressas no rodapé** da
> dissertação — soma 22 para chegar à página do leitor de PDF (`Tese/main.pdf`); se
> recompilares depois de mexer no texto, confirma-as com
> `pdftotext -enc UTF-8 Tese/main.pdf -` antes de imprimir isto.

A regra que atravessa tudo: **nunca defender um número que a tese não diga**. Se
a pergunta for por um valor que não está lá, a resposta é «não medi isso» — que é
sempre melhor do que uma estimativa dita em voz alta e registada em ata.

---

## 1. «O SAC está mal configurado. A temperatura é fixa.»

**O que está a ser perguntado:** se a fraqueza do SAC é do algoritmo ou da tua
configuração.

**Resposta.** É uma escolha de configuração, e está declarada no capítulo da
arquitetura (**p. 44**): $\alpha = 0{,}1$ constante, sem o ajuste dual da
formulação de referência. A tese não a esconde nem a defende — assume que remove
ao SAC o mecanismo com que ele regula a exploração, e que isso é **consistente**
com o sub-treino que a verificação de convergência já lhe documenta em três
células (**p. 49**). Por isso os valores do SAC são lidos como *desempenho
atingível nesta configuração e neste orçamento*, e não como limite do algoritmo.

**O que acrescentar se insistirem:** a forma da falha do SAC é diferente da dos
outros. No mega-treino a $n=28$, nenhuma das suas $28$ execuções passa de
$45{,}4$ chegadas/ep — é **uniformemente fraco**, e não bimodal como o PPO e o
GNN objetivo (**p. 65**). Sub-treino explicaria magnitude baixa; não explica
sozinho a ausência de qualquer execução boa.

---

## 2. «Sete execuções por célula são poucas.»

**Resposta.** Sim — e a unidade estatística está fixada nas notas de leitura
(**p. 50**): a execução, $n=7$ por grupo; alargar essa bateria é o trabalho
futuro n.º 1 (**p. 94**). Por isso o
único cenário em que a leitura depende de **contagens** e não de médias — o Muro
em U — foi replicado com **28 execuções por braço**: $28/28$ contra $15/28$,
Fisher exato $p < 0{,}0001$ (**p. 65**). Onde o alargamento não chegou, o que se
reporta são tamanhos de efeito, e a tese di-lo em vez de fingir poder que não
tem.

---

## 3. «A comparação é injusta: o evolutivo tem atenção sobre grafo, o PPO e o SAC têm um MLP.»

**Resposta.** É a **primeira** limitação declarada (**p. 89**). A conclusão
sobre a escala assenta no que é estrutural: uma MLP de entrada fixa não aceita
$N \neq 20$, seja qual for o otimizador. Que a GNN escalaria igual se treinada
por gradiente é inferência, e não medição — a tese diz que os dois fatores não
ficam isolados. A extensão prioritária (trabalho futuro n.º 2) é treinar a mesma
arquitetura por gradiente, o que separaria os dois efeitos.

**Cuidado:** não dizer «o PPO também escalaria com atenção». Não foi medido.

---

## 4. «A QI7 deu negativo. O que é que isso vale?»

**Resposta.** Vale como resultado, porque a regra estava fixada **antes** dos
dados: limiar de $15$ execuções convergentes em $21$, pré-registado, e o
resultado ficou em $4$ (**p. 71–83**, resposta às QI na **p. 88**). Reporta-se
negativo com a contagem à vista, e não se mudou de critério depois de ver a
amostra — que é o que separa um pré-registo de uma racionalização.

**A segunda metade da resposta, que é a que interessa:** o que a composição
degrada é sobretudo a **fiabilidade** do treino — as execuções que resolvem
fazem-no com magnitudes parecidas entre si, e as outras ficam a zero. E a leitura é condicionada ao orçamento: em $19$ das $21$ execuções
o melhor *fitness* ainda subia no último quinto do treino.

---

## 5. «O evolutivo usa 8× mais cómputo. A comparação é justa?»

**Resposta.** A assimetria está medida e declarada (**p. 78–80**): $195$
minutos com $\approx 30$ núcleos contra $48$ minutos com $16$. E a conclusão que
daí se tira é a **inversa** da que favoreceria o evolutivo: mesmo com $8\times$
menos núcleos-hora, os métodos de gradiente igualam ou superam-no em quatro dos
sete cenários. A vantagem de eficiência é dos gradientes, e a tese escreve-o.

---

## 6. «Seis comparações por par sem correção de multiplicidade.»

**Resposta.** Está assinalado no próprio parágrafo (**p. 65**): os $p$ dos seis
pares de M2 são **brutos**, por compromisso pré-registado — declarar a
multiplicidade e ancorar a leitura no tamanho de efeito, em vez de corrigir os
valores. O efeito principal (M1) não depende disso: $\delta = +0{,}61$ com
$p < 0{,}0001$ unilateral, e a convergência separada por Fisher exato.

---

## 7. «Como sabemos que os números da tese são os dos dados?»

**Resposta.** Porque não são escritos à mão: um conjunto de verificadores lê o
`.tex`, recalcula cada valor a partir dos CSV canónicos e recusa o commit se
algum deixar de bater (`scripts/verificar_numeros_tese.py`, no *hook* de
pre-commit). E os verificadores são eles próprios postos à prova: o
`ensaiar_verificador.py` estraga a tese de propósito, **92 mutações**, uma de
cada vez, e exige que cada uma seja apanhada. O `docs/REPRODUZIR.md` refaz o
percurso comando a comando e é ensaiado contra o disco.

---

## 8. «Qual é, então, a contribuição em uma frase?»

Que **o desenho do sinal de treino e a representação decidem mais do que o
paradigma de otimização**: o colapso do evolutivo era um artefacto da aptidão e
curou-se com *homing* terminal; a escalabilidade é da atenção sobre grafo, não do
otimizador; e a deceção espacial só cede a exploração **doseada** — um mecanismo,
não um paradigma, e em princípio transponível para qualquer um deles.

---

## Perguntas do júri simulado (22 set 2026)

> Saídas de uma leitura integral da tese «como se fosse o júri». Cada resposta foi
> verificada contra o código, o histórico do git e o PDF recompilado a 22 set.

**«A observação é mesmo local?»** (§4.2.2 · §7.3)

Não inteiramente, e a tese di-lo (§4.2.2, p. 31, e §7.3, p. 89). **Local é a perceção do ambiente**: os obstáculos só se veem pelo LiDAR de 8 m, sem mapa. **A do enxame é global**: cada robô recebe a direção, a distância e o sinal de comunicação de *todos* os outros, sem limite de alcance nem oclusão pelas paredes. É igual para os três controladores, pelo que não favorece nenhum na comparação. A consequência honesta: a escalabilidade foi medida sem as restrições de comunicação de um enxame real. Se insistirem: a atenção já aprende a pesar cada vizinho, e um corte por raio seria a extensão natural. Não foi medido.

---

**«Como sabe que a escala é da representação e não do otimizador?» / «Porque não truncaram aos 19 vizinhos mais próximos?»** (§3 · §7.3)

Há uma parte estrutural e outra de inferência. **A estrutural**: uma MLP de entrada fixa (ℝ¹¹¹) não pode receber N≠20, seja qual for o otimizador. Por isso o PPO e o SAC nem entram no teste. **A inferência**: que a GNN escalaria igual se fosse treinada por gradiente. Apoia-se no mecanismo (o número de parâmetros não depende de N; Chen et al.) e não numa experiência minha. A tese diz que os dois fatores não ficam isolados experimentalmente. Truncar ou completar a observação daria uma MLP escalável, e seria uma *baseline* legítima. Não a fiz. A extensão prioritária é a atenção numa política de gradiente (trabalho futuro n.º 2, §7.5).

---

**«São 21 testes sem correção para comparações múltiplas.»** (Quadro 6.8)

Os p do Quadro 6.8 (p. 81) são brutos e vêm acompanhados do δ de Cliff. Fiz as contas sobre o próprio quadro. **Com Benjamini-Hochberg** (taxa de falsas descobertas a 5 %), **os 14 resultados significativos mantêm-se todos**. **Com Holm** (erro de família), mantêm-se 9 e caem 5: PPO>SAC no Sandbox, GNN>PPO e PPO>SAC na Porta Cooperativa, e GNN>PPO e GNN>SAC na Perceção. Portanto, «o evolutivo supera ambos em três cenários» vale com controlo da taxa de falsas descobertas. Com o critério mais estrito, o resultado robusto é o **Quatro Salas**: p = 0,0006 e δ = +1,00 contra os dois, que é o mínimo possível com 7 contra 7, ou seja, separação total. Na Porta Cooperativa a diferença para o PPO é também pequena na prática (69,8 contra 67,1).

---

**«Onde está o controlo da QI5? O que mudou além da fitness?»** (§7.2 · QI5)

É uma **comparação entre campanhas, e não uma ablação**, e a tese diz isso na resposta à QI5. Na última campanha com a fitness inicial, **3 de 12** execuções dos quatro cenários de gargalo chegaram ao ninho no treino. Com o homing, **28 de 28** convergem a 100 %. Entre as duas mudou também o decaimento de σ, e a anterior não teve avaliação determinística. O que sustenta a causa é o mecanismo, que se observa diretamente. Com a tanh, a aptidão convergia para um valor comum a toda a população, e a seleção ficava sem sinal. Na versão desaturada, os genomas farmavam retorno (≈ 88 000) com zero chegadas. O homing remove esse farm por construção. O que falta, e digo-o: uma ablação só da fitness, com tudo o resto igual.

---

**«A escala e a robustez foram medidas só no modelo campeão?»** (§6.12 · §6.13)

Sim: um modelo por cenário, 20 episódios por célula, e as legendas dizem-no. Na robustez, a retenção é um rácio entre duas avaliações da mesma fonte, por isso escolher o campeão não a enviesa. Mas os «100 % em 28/28» da escala são do campeão, e não das 7 execuções. Não medi se as outras transferem. Se perguntarem pelo Sandbox: as duas execuções degeneradas do GNN já não resolvem com N=20.

---

**«10 % de falhas é pouco.»** (§6.13)

São 2 robôs em 20, a meio do episódio. Uma retenção de 92 a 106 % está perto do que a simples perda de agentes daria. Por isso a conclusão é modesta, e é a que a tese tira: nenhum paradigma colapsa e o teste **não discrimina** entre eles (QI4). Frações maiores, de 30 a 50 %, seriam o teste que discrimina. Não o fiz.

---

**«Os resultados são reproduzíveis?»** (§4.5)

A **avaliação** é exata *na mesma máquina*: reavaliar os modelos arquivados com as mesmas sementes dá os mesmos números. Noutra máquina (147 modelos reavaliados a 23 set) a vírgula flutuante desloca-os ~1 chegada/ep; nenhuma contagem de convergência muda, as comparações do GNN mantêm-se, e só dois PPO–SAC no limiar trocam de lado (Sandbox 0,03 → 0,10; Perceção 0,055 → 0,040). O **treino** reproduz o protocolo, mas não bit a bit, porque o orçamento é em minutos e o número de passos depende da máquina. A tese corrigiu esta frase (§4.5).

---

**«O que é que o PPO tem de adaptativo depois de treinado?»** (§1.2)

Nada. Nos dois paradigmas a política fica fixa depois do treino, e a tese di-lo logo na definição do problema: mede-se tolerância, e não adaptação em execução. A hipótese herdou o vocabulário da literatura (*online* contra *offline*). A resposta da tese é precisamente que a «adaptabilidade» que aqui importa, que é aceitar outro N, está na representação e não no algoritmo.

---

**«São drones ou robôs terrestres?»** (§7.3)

O simulador é 3D (a ação tem Δz e a arena é esférica), mas as tarefas são planares. É uma limitação declarada: a altitude não é observada, e voar alto custa chegadas (ρ = −0,74, indicativo). No mapa composto o movimento vertical foi limitado a ±2 m. A comparação com o e-puck e o Khepera é sobre sensores e o *deployment gap*, e não sobre a dinâmica. Não dizer «são drones».

---

**«3 das 7 execuções do GNN nas Quatro Salas atravessam paredes, e é aí que o GNN mais ganha.»** (§7.3 · p. 90)

Está medido e declarado. As três que atravessam fazem 55,7 chegadas/ep e as quatro limpas fazem 60,3. A distância aos métodos de gradiente (33,6 e 31,8) é muito maior do que isso, por isso a superioridade não depende das travessias. Onde a costura pesa é no campeão adaptativo das Quatro Salas, e essa célula está declarada como contaminada.

---

## O que NÃO dizer

- **«O SAC é mau.»** → é fraco *nesta configuração e neste orçamento*, e três das
  suas células estão sub-treinadas por medição própria.
- **«O mapa composto não é resolúvel.»** → é: um navegador geodésico faz
  $53$ chegadas por episódio nele. O que falha é aprendê-lo.
- **«A QI7 falhou.»** → a campanha correu e respondeu; a resposta é negativa.
- **«Os robôs só veem à sua volta.»** → só os obstáculos; os outros robôs, veem-nos todos.
- **«De 0 % para 100 %.»** → na última campanha com a fitness antiga foram 3 em
  12 execuções; é uma comparação entre campanhas, não uma ablação.
- **Qualquer número que não esteja no PDF.** Se não está lá, não foi medido.
