# Guia de leitura — o artigo da dissertação

> Estado em **4 ago 2026**: o artigo foi reescrito de raiz a 10 jul com os dados
> da campanha de 7 dias, e hoje ganhou a **replicação a $n=28$** (mega-treino de
> um mês) mais as figuras corrigidas da tese. Está em **português**, compila sem
> erros nem referências por resolver, e tem **10 páginas** — 8,5 de corpo e 1,5
> de bibliografia. ⚠️ **O Prof. pediu 6 a 8**: ver o ponto 3 de «O que depende de
> ti». Este guia diz: (1) o que o **professor** pretende; (2) o que **mudou** face
> ao draft de junho e porquê; (3) o que ainda depende de ti.

---

## 1. O que o professor pretende deste artigo (do e-mail dele)

- **Porquê existe:** "as notas acima de 17, na maioria dos nossos cursos, só são
  atribuídas às dissertações que apresentam, além da dissertação, **um artigo**."
  → É o que separa uma boa nota de uma nota de excelência.

- **O que é:** "tem normalmente de **6 a 8 páginas** e sensivelmente a **mesma
  estrutura da dissertação**, mas é uma **forma destilada**, em que a dissertação
  pode ser referida para mais detalhes." → A tese **condensada**, remetendo para
  ela quando o leitor quiser o detalhe.

- **Para quem escreves:**
  1. **O júri** — "convencer um júri de que a sua resposta é válida e o seu método
     de chegar à resposta foi adequado."
  2. **Os teus colegas do próximo ano** — "escreva de forma clara e compreensível,
     também para eles."

- **Resultados negativos** "são, frequentemente, **uma resposta válida** à pergunta
  de investigação." → O Muro em U, que nenhum algoritmo resolve, está no artigo
  com essa dignidade, não escondido.

- **Obrigatório:** o *acknowledgement* da ISTAR (texto exato — já está).

- **Formato:** modelo LaTeX **Elsevier `elsarticle`** (o que ele anexou).

---

## 2. O que mudou (e porquê a história é OUTRA)

O draft de junho contava esta história:

> ~~"Os métodos de gradiente dominam a tarefa: o SAC resolve os seis cenários e o
> PPO cinco em seis. O controlador evolutivo **colapsa** nos estrangulamentos.
> Só ele escala. Trade-off central: desempenho vs. escalabilidade."~~

**A campanha de 7 dias inverteu isto.** A história agora é:

> *O colapso do evolutivo era um **artefacto do desenho da função de aptidão**, não
> uma limitação do paradigma. A aptidão antiga (retorno acumulado comprimido por
> tanh) era **farmável**: o genoma maximizava-a a deambular sem nunca entrar no
> ninho. Substituindo-a por **homing terminal** — que só se maximiza a TERMINAR
> junto ao ninho — o controlador evolutivo converge nas 28 execuções dos quatro
> labirintos não-decetivos e torna-se **estatisticamente superior** aos métodos de
> gradiente em três cenários. Os métodos de gradiente mantêm a fiabilidade em
> espaço aberto e ~8× menos núcleos-hora. Só o grafo com atenção escala zero-shot.*

O que isto muda, concretamente:

| Aspeto | Draft de junho | Agora |
|---|---|---|
| Cenários | 6 | **7** (junta a Porta c/ Alternativa, *deceptive*) |
| Execuções de treino | 1 por célula | **7** por célula (147 treinos) |
| Unidade estatística | o episódio (30) | **a execução de treino** (n=7) |
| Testes | Mann-Whitney + Welch | Mann-Whitney + **δ de Cliff** |
| GNN nos labirintos | colapsa (0 recolhas) | **28/28 execuções convergem** |
| PPO no Muro em U | *reward hacking*, 0 recolhas | bimodal, **4/7** execuções a 100% |
| Muro em U | SAC resolve-o | **ninguém** o resolve de forma fiável |
| Escalabilidade GNN | 15% → 100% de sucesso | **100% em todas** as dimensões |

Secção a secção:

- **Resumo:** o achado é o **desenho da aptidão**, não o trade-off simples.
- **1. Introdução:** contribuição agora **tripla** — protocolo; o colapso como
  artefacto corrigível; escalabilidade como propriedade da representação. Assume
  explicitamente que a versão preliminar concluía o oposto.
- **2. Trabalho Relacionado:** juntei o *Novelty Search* (Lehman & Stanley, 2011).
- **3. Metodologia:** 7 cenários, LiDAR 8 m, recompensa **simplificada a 4 termos**
  (era "seis termos"), equação de aptidão nova (`J = f̄·10⁴ + 5000·h̄`), protocolo
  com 7 execuções e a justificação de por que a unidade estatística é a execução.
- **4. Resultados:** tabela com **[runs a 100%]** por célula (a coluna que revela a
  bimodalidade); secção nova sobre o Muro em U; secção nova sobre Novelty Search;
  tabela de significância com **21** comparações e δ de Cliff.
- **5. Discussão:** a anatomia do colapso **e da sua cura**; a variância invertida
  (GNN falha no aberto, SAC falha nos gargalos).
- **6. Limitações:** honesto quanto a n=7 ser pouco nos cenários bimodais.

### Figuras (7, todas regeneradas da campanha final)
Painel dos 7 mapas · potencial geodésico vs. euclidiano · recolhas por cenário ·
**boxplot do Muro em U** (mostra a bimodalidade) · escalabilidade zero-shot ·
robustez a falhas.

> ⚠️ Removi os **heatmaps de ocupação** do Muro em U que estavam no draft. A
> legenda antiga dizia "o GNN fica preso, o PPO faz reward hacking, o SAC contorna"
> — nada disso continua verdade, e o cenário é agora bimodal (a figura mostraria
> só a execução que ficou guardada como oficial, o que induziria o leitor em erro).

---

## 3. O que ainda depende de ti

1. **Ler o PDF** (`Artigo/artigo.pdf`, 10 págs). O artigo e a tese contam a mesma
   história, agora incluindo o mega-treino (secção 4.4, `n=28`).

2. **Título.** Continua o de junho: *"Aprendizagem Adaptativa versus Robustez
   Estática: Comparação de Aprendizagem por Reforço e Neuroevolução para Controlo
   de Enxames"*. Ainda encaixa, mas repara que o achado central deixou de ser o
   contraste "adaptativo vs. estático" e passou a ser o **desenho da aptidão**. Se
   quiseres, proponho títulos alternativos.

3. ⚠️ **10 páginas contra as 6–8 pedidas.** O corpo são 8,5 e a bibliografia 1,5;
   já estava assim antes desta atualização (o mega-treino entrou sem acrescentar
   página, por reflow das colunas). Se for para cortar até 8, os candidatos, por
   ordem de custo:
   - **Robustez** (§4.6 + Figura 7): a própria secção conclui que a robustez *não*
     discrimina entre paradigmas — é a que menos sustenta a tese central. ≈¾ pág.
   - **Experiência preliminar do Novelty** (o parágrafo do $+26\%$ com orçamento
     triplo): já está desmascarado como artefacto no parágrafo seguinte, e a
     história fecha sem ele. ≈⅓ pág.
   - **Tabela 2** (as 21 comparações par a par): pode remeter-se para a tese, com
     as significâncias resumidas em prosa. ≈½ pág.
   Não cortar: o mega-treino ($n=28$) é o resultado com mais poder estatístico do
   trabalho todo.

4. **Língua:** mantive **PT-PT** (decisão tua de 22 jun).

---

## Como ver o artigo
O PDF está em `Artigo/artigo.pdf`. O fonte é `Artigo/artigo.tex`. Recompilar:
`pdflatex artigo` → `bibtex artigo` → `pdflatex artigo` (×2).
