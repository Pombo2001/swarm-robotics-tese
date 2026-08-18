# Guião de defesa — as perguntas que vêm primeiro

> Escrito a 18 ago 2026, contra o PDF de **136 páginas** dessa data. Cada
> pergunta tem: o que está mesmo a ser perguntado, a resposta curta, e a
> **página** onde está a prova. As páginas são as do PDF (`Tese/main.pdf`); se
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
arquitetura (**p. 68**): $\alpha = 0{,}1$ constante, sem o ajuste dual da
formulação de referência. A tese não a esconde nem a defende — assume que remove
ao SAC o mecanismo com que ele regula a exploração, e que isso é **consistente**
com o sub-treino que a verificação de convergência já lhe documenta em três
células (**p. 73–74**). Por isso os valores do SAC são lidos como *desempenho
atingível nesta configuração e neste orçamento*, e não como limite do algoritmo.

**O que acrescentar se insistirem:** a forma da falha do SAC é diferente da dos
outros. No mega-treino a $n=28$, nenhuma das suas $28$ execuções passa de
$45{,}4$ recolhas/ep — é **uniformemente fraco**, e não bimodal como o PPO e o
GNN objetivo (**p. 88–89**). Sub-treino explicaria magnitude baixa; não explica
sozinho a ausência de qualquer execução boa.

---

## 2. «Sete execuções por célula são poucas.»

**Resposta.** Sim, e é a segunda limitação declarada (**p. 111**). Por isso o
único cenário em que a leitura depende de **contagens** e não de médias — o Muro
em U — foi replicado com **28 execuções por braço**: $28/28$ contra $15/28$,
Fisher exato $p < 0{,}0001$ (**p. 88**). Onde o alargamento não chegou, o que se
reporta são tamanhos de efeito, e a tese di-lo em vez de fingir poder que não
tem.

---

## 3. «A comparação é injusta: o evolutivo tem atenção sobre grafo, o PPO e o SAC têm um MLP.»

**Resposta.** É a **primeira** limitação declarada (**p. 111**), e é deliberada
na leitura: exatamente por a arquitetura ser a variável que difere, a conclusão
sobre escalabilidade é atribuída à **representação** e não ao otimizador. Isso é
o que a assimetria permite concluir — e é também por isso que o trabalho futuro
número um é treinar a mesma arquitetura por gradiente, que separaria os dois
efeitos.

**Cuidado:** não dizer «o PPO também escalaria com atenção». Não foi medido.

---

## 4. «A QI7 deu negativo. O que é que isso vale?»

**Resposta.** Vale como resultado, porque a regra estava fixada **antes** dos
dados: limiar de $15$ execuções convergentes em $21$, pré-registado, e o
resultado ficou em $4$ (**p. 90–105**, resposta às QI na **p. 110**). Reporta-se
negativo com a contagem à vista, e não se mudou de critério depois de ver a
amostra — que é o que separa um pré-registo de uma racionalização.

**A segunda metade da resposta, que é a que interessa:** o que a composição
degrada é a **fiabilidade** do treino, não a magnitude de quem aprende — as
execuções que resolvem fazem-no com magnitude comparável entre si, e as outras
ficam a zero. E a leitura é condicionada ao orçamento: em $19$ das $21$ execuções
o melhor *fitness* ainda subia no último quinto do treino.

---

## 5. «O evolutivo usa 8× mais cómputo. A comparação é justa?»

**Resposta.** A assimetria está medida e declarada (**p. 105–107**): $195$
minutos com $\approx 30$ núcleos contra $48$ minutos com $16$. E a conclusão que
daí se tira é a **inversa** da que favoreceria o evolutivo: mesmo com $8\times$
menos núcleos-hora, os métodos de gradiente igualam ou superam-no em quatro dos
sete cenários. A vantagem de eficiência é dos gradientes, e a tese escreve-o.

---

## 6. «Seis comparações por par sem correção de multiplicidade.»

**Resposta.** Está assinalado no próprio parágrafo (**p. 88**): os $p$ dos seis
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
`ensaiar_verificador.py` estraga a tese de propósito, **87 mutações**, uma de
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

## O que NÃO dizer

- **«O SAC é mau.»** → é fraco *nesta configuração e neste orçamento*, e três das
  suas células estão sub-treinadas por medição própria.
- **«O mapa composto não é resolúvel.»** → é: um navegador geodésico recolhe
  $53$ itens por episódio nele. O que falha é aprendê-lo.
- **«A QI7 falhou.»** → a campanha correu e respondeu; a resposta é negativa.
- **Qualquer número que não esteja no PDF.** Se não está lá, não foi medido.
