# «Tabela» vs. «Quadro» — o que mudaria

> **APLICADO a 6 de setembro de 2026.** A decisão foi seguir a letra da norma:
> a tese diz agora «Quadro» e «Anexo». Este ficheiro fica como registo do que
> foi mudado e porquê — a recomendação no fim é a que eu tinha dado *antes* da
> decisão, e mantém-se aqui só para memória futura. Um detalhe que o
> levantamento original não previa: além das 20 referências, 9 menções e 5
> colisões, a mudança de género obrigou a corrigir duas concordâncias («o quadro
> é ger**ada**» → «ger**ado**»; «nos quadros comparativ**as**» →
> «comparativ**os**») e a alterar `scripts/slr_pipeline.py`, que gera o
> `prisma_gerado.tex` e reintroduziria «Apêndice» na próxima regeneração.

Levantamento feito a 6 de setembro de 2026 sobre `Tese/main.tex`,
`Tese/seccao_mapa_grande.tex` e `Tese/apendice_slr.tex`.

## O que a norma diz

Normas do Iscte de apresentação e harmonização gráfica (19 mai 2020), §2.2:

> As figuras são entendidas como representações do tipo diagrama, mapa, desenho ou
> outras de idêntica natureza e **os quadros como tabelas contendo dados numéricos
> ou qualitativos**. […] Ambas as representações têm numeração indexada ao capítulo
> (e.g. **Quadro 2.3**, para o 3º quadro do Capítulo 2, ou Figura 7.5, para a 5ª
> figura do Capítulo 7) e uma legenda descrevendo o seu conteúdo.

E no §1.vii, sobre os índices: «Índice de **quadros** e figuras».

Pela definição da norma, as 14 tabelas da tese são todas «quadros»: contêm dados
numéricos (resultados, hiperparâmetros, tempos) ou qualitativos (a síntese da
literatura). Nenhuma é diagrama, mapa ou desenho.

## Alcance da mudança

| O que | Quantos sítios | Como |
|---|---|---|
| Legendas das tabelas | 14 | **Automático** — 1 linha no preâmbulo |
| Título da lista de figuras/tabelas | 1 | 1 linha no preâmbulo (já existe, muda o texto) |
| Prefixo das entradas nessa lista | 1 | 1 linha no preâmbulo (já existe, muda o texto) |
| Referências cruzadas no corpo | 20 | **À mão** — a palavra está escrita no texto |
| Palavra «tabela(s)» solta em texto corrido | 9 | À mão, se se quiser coerência total |

As três primeiras linhas são de preâmbulo e resolvem-se assim:

```latex
\addto\captionsportuguese{\renewcommand{\tablename}{Quadro}}          % NOVA
\addto\captionsportuguese{\renewcommand{\listtablename}{Lista de Quadros}}  % main.tex:212
{\renewcommand\numberprefix{Quadro~}#1}{#2}}                          % main.tex:150
```

As 20 referências cruzadas têm de ser editadas uma a uma porque a palavra
«Tabela» está escrita literalmente antes do `\ref{}` — o LaTeX não a gera.
Atenção: 18 usam til (`Tabela~\ref`) e 2 usam espaço normal (`Tabela \ref`),
pelo que uma substituição cega por `Tabela~\ref` deixaria essas duas para trás.

## As 14 legendas, antes e depois

O texto da legenda não muda; muda só o rótulo que o LaTeX põe à frente.

| Ficheiro:linha | Antes | Depois | Legenda |
|---|---|---|---|
| main.tex:888 | Tabela 3.1 | Quadro 3.1 | Síntese dos estudos mais relevantes do corpo da revisão |
| main.tex:976 | Tabela 4.1 | Quadro 4.1 | Hiperparâmetros reais utilizados na simulação e no treino dos modelos |
| main.tex:1265 | Tabela 5.1 | Quadro 5.1 | Plano de testes experimentais |
| main.tex:1359 | Tabela 6.1 | Quadro 6.1 | Desempenho no cenário Sandbox |
| main.tex:1494 | Tabela 6.2 | Quadro 6.2 | Avaliação determinística nos sete cenários |
| seccao_mapa_grande.tex:236 | Tabela 6.3 | Quadro 6.3 | Treino nativo no mapa composto (F2) |
| main.tex:1593 | Tabela 6.4 | Quadro 6.4 | Escalabilidade *Zero-Shot* nos sete cenários |
| main.tex:1616 | Tabela 6.5 | Quadro 6.5 | O contraste arquitetural no Sandbox |
| main.tex:1660 | Tabela 6.6 | Quadro 6.6 | Desempenho computacional do simulador |
| main.tex:1680 | Tabela 6.7 | Quadro 6.7 | Custo computacional por algoritmo |
| main.tex:1711 | Tabela 6.8 | Quadro 6.8 | Significância das diferenças em recolhas por episódio |
| main.tex:1878 | Tabela A.1 | Quadro A.1 | Configuração do ambiente de simulação e da física |
| main.tex:1915 | Tabela A.2 | Quadro A.2 | Hiperparâmetros de treino dos três algoritmos |
| apendice_slr.tex:4 | Tabela B.1 | Quadro B.1 | Estudos incluídos na revisão sistemática (*n* = 58) |

## As 20 referências cruzadas a editar

Todas seguem o mesmo padrão: `Tabela~\ref{...}` → `Quadro~\ref{...}`.
As duas assinaladas com ⚠ usam espaço em vez de til.

| # | Ficheiro:linha | Texto atual |
|---|---|---|
| 1 | main.tex:883 | `Tabela~\ref{tab:sota_summary}` |
| 2 | main.tex:971 | ⚠ `Tabela \ref{tab:hyperparameters}` |
| 3 | main.tex:1260 | ⚠ `Tabela \ref{tab:experiments_priority}` |
| 4 | main.tex:1303 | `Tabela~\ref{tab:res_eval}` |
| 5 | main.tex:1354 | `Tabela~\ref{tab:res_sandbox}` |
| 6 | main.tex:1489 | `Tabela~\ref{tab:res_eval}` |
| 7 | main.tex:1541 | `Tabela~\ref{tab:res_eval}` |
| 8 | main.tex:1549 | `Tabela~\ref{tab:res_eval}` |
| 9 | main.tex:1588 | `Tabela~\ref{tab:res_scale_all}` |
| 10 | main.tex:1588 | `Tabela~\ref{tab:res_scale}` |
| 11 | main.tex:1647 | `Tabela~\ref{tab:res_eval}` |
| 12 | main.tex:1653 | `Tabela~\ref{tab:res_computacional}` |
| 13 | main.tex:1675 | `Tabela~\ref{tab:res_tempos}` |
| 14 | main.tex:1706 | `Tabela~\ref{tab:res_signif}` |
| 15 | main.tex:1749 | `Tabela~\ref{tab:res_tempos}` |
| 16 | main.tex:1872 | `Tabela~\ref{tab:apx_env}` |
| 17 | main.tex:1872 | `Tabela~\ref{tab:apx_train}` |
| 18 | main.tex:1947 | `Tabela~\ref{tab:slr_incluidos}` |
| 19 | seccao_mapa_grande.tex:249 | `Tabela~\ref{tab:f2_mapa_grande}` |
| 20 | seccao_mapa_grande.tex:405 | `Tabelas~\ref{tab:res_eval} e~\ref{tab:res_signif}` (plural → «Quadros») |

Os `\label{}` podem ficar como estão — `tab:` é só um nome interno, nunca
aparece no PDF. Mudá-los obrigaria a editar os mesmos 20 sítios outra vez, sem
ganho nenhum.

## A palavra «tabela» solta no texto (9 sítios)

Estas não são referências a nenhum quadro em particular; são frases do tipo «a
leitura da tabela expõe o padrão». Se o rótulo passar a «Quadro», estas ficam a
destoar.

- main.tex:915 — «A leitura da **tabela** expõe o padrão: …»
- main.tex:1158 — «… aparece automaticamente nas campanhas, nas **tabelas** e nas figuras.»
- main.tex:1279 — «… que gera as **tabelas** e figuras do Capítulo…»
- main.tex:1694 — «A **tabela** responde à pergunta “quanto custa”…»
- main.tex:1743 — «A leitura da **tabela** desfaz a narrativa simples…»
- main.tex:1832 — «Na campanha final, que sustenta as **tabelas** desta dissertação…»
- main.tex:1949 — «A **tabela** é gerada automaticamente a partir do registo…»
- seccao_mapa_grande.tex:176 — «O resultado do F1 dispensa **tabela**: das 21 células…»
- seccao_mapa_grande.tex:404 — «… **não entra** nas **tabelas** comparativas dos sete cenários…»

## O argumento contra

A palavra «quadro» já é usada 5 vezes no texto no seu sentido corrente, e
nenhuma delas se refere a uma tabela:

- main.tex:1303 — «mostram um **quadro** maioritariamente robusto»
- main.tex:1545 — «o **quadro** inverte-se: ambos os braços convergem…»
- main.tex:1553 — «duas análises exploratórias […] completam o **quadro**»
- main.tex:1755 — (idem, no parágrafo da composição de dificuldades)
- main.tex:1757 — «o **quadro** final é mais rico do que o antecipado»

Adotar «Quadro» como rótulo cria frases como «o quadro que o Quadro 6.2 traça»,
e obriga a reescrever estas cinco para evitar a colisão. São mais 5 edições de
texto, além das 20 + 9 acima.

## Recomendação

**Deixar como está.** A norma escreve «Quadro», mas:

1. É a convenção estabelecida em teses técnicas do DCTI escrever «Tabela»;
2. O risco de rejeição por este motivo é praticamente nulo — a rejeição prevista
   nas normas é por incumprimento de estrutura e composição gráfica, e o rótulo
   está numerado e indexado ao capítulo como o §2.2 exige (`Tabela 6.2`, tal como
   `Figura 6.20`), com a legenda no topo;
3. A colisão semântica com os 5 usos correntes de «quadro» piora a legibilidade.

Se ainda assim quiseres alinhar com a letra da norma, o trabalho total é: 3
linhas de preâmbulo + 20 referências cruzadas + 9 menções soltas + 5 reescritas
para evitar a colisão. Uma passagem, sem risco de partir a compilação.
