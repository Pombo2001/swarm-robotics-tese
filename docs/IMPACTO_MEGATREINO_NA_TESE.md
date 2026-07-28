# O que muda na tese quando o mega-treino fechar

> Escrito a **28 jul 2026**, com a campanha ainda a correr (megaA na fase 3,
> megaB na 5) e **sem integrar nada**. Serve para que a 3 de agosto seja *editar*
> e não *procurar* — o hard stop de integração é **22 ago** e a janela é curta.
>
> Os números do M1 já são conhecidos (fases 1 e 2 do megaA estão arquivadas e
> completas), mas **não entram na tese antes da análise oficial**, com a campanha
> fechada. Ver `results/mega_1mes/ANALISE_PARCIAL_28jul_NAO_OFICIAL.txt`.

---

## A regra que governa tudo isto

O `PRE_REGISTO_MEGATREINO.md` fixou-a antes de haver dados, e ela decide o
formato da integração:

> *"As células n=28 do u_wall são **autocontidas** (as 4 condições da MESMA
> campanha comparam-se entre si; os n=7 antigos ficam como verificação de
> consistência, **nunca se somam sem o declarar**)."*

**Consequência prática: não se reescrevem os números da Secção~\ref{sec:res_novelty}.**
A campanha de 7 dias e o mega-treino são duas campanhas, com orçamentos
diferentes (195 min/run em ambas, mas 7 vs 28 execuções), e a tese passa a
reportar as duas — a segunda como replicação da primeira, não como correção.

Quem chegar aqui com pressa e trocar `68,5 ± 13,1` por `67,4 ± 13,4` no T2 está
a violar o pré-registo. **Não é isso que se faz.**

---

## O que se acrescenta (não substitui)

### 1. Um parágrafo novo na §res_novelty — a replicação a n=28

Entra a seguir ao parágrafo dos quatro testes pré-registados (T1-T4), por volta
da **linha 1449** do `main.tex`. Diz, em substância:

- a campanha adaptativa foi **replicada com quatro vezes o número de execuções**
  no cenário que a motivou (Muro em U, n=28 por braço);
- o resultado **replica-se**: a magnitude do adaptativo mantém-se e a
  convergência passa a total;
- com n=28 o **Fisher exato sobre convergência torna-se reportável** — não era a
  n=7, e é a primeira vez na dissertação que se faz inferência sobre *proporções*
  de convergência, e não só sobre magnitude;
- o objetivo puro sai **menos mau** do que os sete runs sugeriam, o que é a
  informação nova: parte do contraste de 19 jul era ruído de amostragem pequena.

**Os números (a confirmar na análise oficial, mas já medidos nas fases fechadas):
adaptativo 67,4 ± 13,4 com 28/28 convergentes; objetivo 32,5 ± 32,5 com 15/28;
Mann-Whitney unilateral p < 0,0001; δ de Cliff +0,61; Fisher 28/28 vs 15/28,
p < 0,0001.** Contra os n=7 da tese: 68,5 ± 13,1 e 7/7 vs 24,5 ± 32,6 e 3/7
(p = 0,009, δ = +0,76).

⚠️ **A leitura honesta do δ:** desce de +0,76 para +0,61. Não é o efeito a
enfraquecer — é a estimativa a ficar melhor. Escrever isto explicitamente, ou a
descida parece um resultado pior escondido debaixo de um p mais pequeno.

### 2. A ablação do *annealing* — um argumento de robustez que a tese não faz

As quatro variantes (sustain 5/20, decay 0,95/0,995) convergem **7/7 nos dois
cenários**, entre 59,7 e 69,1 no Muro em U e 74,8 e 82,4 no bypass. Ou seja: o
mecanismo **não depende de acertar nos hiperparâmetros do anneal**.

Isto responde a uma objeção previsível na defesa ("escolheu os parâmetros que
funcionavam?") e a tese **não tem hoje resposta nenhuma para ela**. Entra como
parágrafo exploratório, rotulado como tal — o pré-registo é explícito em que a
pergunta é a sensibilidade, não um vencedor.

### 3. M2 e M3, quando as fases fecharem

- **M2** (4 braços a n=28 no u_wall): depende das fases 3 e 4 do megaA (PPO e
  SAC), a correr agora. A pergunta é se o "nenhuma diferença significativa entre
  os três algoritmos base no Muro em U" — hoje na tese, com n=7 — **se mantém ou
  se desfaz** com n=28. Se se desfizer, muda uma frase do Capítulo de Resultados
  (linha ~1582) e outra da QI1.
- **M3** (bypass adaptativo n=28 vs fixo n=7): depende da fase 5 do megaB. Testa
  se o δ = +0,59 (p = 0,073) do T4 se confirma ou se dissolve. O T4 está na
  **linha 1448**, e é o único dos quatro testes cuja leitura assenta só no
  tamanho de efeito.

---

## O que muda de estatuto (e é fácil esquecer)

### Trabalhos Futuros nº 1 — passa a estar parcialmente **feito**

Linha **1645**: *"Estender as 7 execuções independentes por configuração da
campanha final para 30, com prioridade para os cenários de comportamento bimodal
(Muro U, Sandbox-GNN, Gargalo-SAC), onde n=7 limita o poder estatístico"*.

É exatamente o que o mega-treino faz no Muro U (n=28 ≈ as 30 pedidas) e no
Sandbox (n=21). **Deixar isto escrito como trabalho futuro depois de o ter feito
é um erro que salta à vista de qualquer júri.** Reescrever para o que fica por
fazer: o Gargalo-SAC (fase 6 do megaB, n=21) e os restantes cenários.

### Limitações — a frase do n=7

Linha **1604**: *"Estas conclusões assentam em 7 execuções independentes por
configuração (…); o alargamento da bateria refinará as estimativas de variância,
em particular nos cenários bimodais."* Passa a ter de dizer que o alargamento
**foi feito** no cenário bimodal principal, e o que ele mostrou.

### Resumo e Abstract

Ambos citam os `7/7` no Muro em U (linhas **328** e **334**). Uma frase, ou uma
oração, para dizer que o resultado foi replicado a n=28. Cuidado com o espaço: o
Resumo já é denso e há um limite de página.

---

## O que **não** se toca

| | Porquê |
|---|---|
| `tab:res_eval` e `tab:res_signif` | São da campanha de 7 dias, com o seu protocolo. O mega-treino é outra campanha — juntá-los na mesma linha compara coisas diferentes |
| Os números T1-T4 de 19 jul | Ficam como estão, com a sua n. A replicação **acrescenta-se**, não substitui |
| QI2, QI3, QI4, QI5 | O mega-treino não lhes toca |
| A secção do mapa grande | É a QI7, campanha independente |

---

## Ordem de trabalho, a 3 de agosto

1. `pos_campanha.py` (armadilha nº9) → instalar em `results/mega_1mes/` →
   confirmar `_run{n}` → **só depois** `analise_megatreino.py`.
2. Confirmar que o M1 oficial (12 fases) bate com o parcial de 28 jul. Se não
   bater, é porque as fases 1 e 2 foram relidas de outro sítio — investigar antes
   de escrever seja o que for.
3. Escrever o parágrafo da replicação + o da ablação (secções 1 e 2 acima).
4. M2 e M3 conforme derem.
5. Corrigir o Trabalhos Futuros nº 1 e a frase das Limitações — **é o passo que
   se esquece**, porque não é onde estão os números novos.
6. Recompilar, verificar 0 refs indefinidas e 0 overfulls, commitar o PDF.

**Esforço estimado:** meio dia, se a análise correr limpa. O grosso é escrita,
não código — o `analise_megatreino.py` já corre sem erros contra dados reais
(validado a 28 jul com as seis fases arquivadas).
