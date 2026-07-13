# Protocolo da Revisão Sistemática da Literatura (SLR)

> **Regra de ouro:** este protocolo é definido **ANTES** de correr qualquer pesquisa.
> Tudo o que se executar depois é registado em `docs/slr/` — mesmo que dê mau resultado.
> Se uma decisão mudar a meio (p. ex. alargar uma base), regista-se aqui a alteração
> e a data, em vez de reescrever a história.

Data de início: **13 jul 2026** · Autor: Gonçalo Santos · Orientador: Prof. Luís Nunes

---

## 1. Pergunta da revisão

> Como se comparam, em controlo descentralizado de enxames robóticos, os paradigmas
> de **Aprendizagem por Reforço Multiagente (MARL)** e de **Otimização Bio-inspirada**,
> quanto a desempenho de tarefa, escalabilidade e robustez — e que lacunas de
> *benchmarking* comparativo persistem na literatura?

Esta pergunta é a que o Capítulo 3 já tenta responder; a revisão serve para a
sustentar com um corpo de literatura levantado de forma reproduzível.

## 2. Critérios de elegibilidade (definidos a priori)

**Inclusão (todos obrigatórios):**
- I1. Aborda controlo, navegação ou coordenação de **sistemas multi-robô / enxames**
  (≥ 2 agentes; exclui robô único).
- I2. Aplica **MARL / RL profundo** OU **otimização bio-inspirada / evolutiva**
  (PSO, ACO, AE, neuroevolução) ao problema de controlo.
- I3. Apresenta **validação empírica** (simulação dinâmica ou plataforma real) com
  resultados quantitativos.
- I4. Publicado entre **2020 e 2026**, em conferência ou revista com revisão por pares.
  (Exceção: obras seminais anteriores — Kennedy & Eberhart 1995, Dorigo 1992,
  Bonabeau et al. 1999 — são citadas como fundamentação, mas NÃO entram na contagem
  da revisão. Ver §6.)
- I5. Texto integral acessível (via ISCTE) e escrito em inglês ou português.

**Exclusão:**
- E1. Robô único, ou multi-agente puramente virtual sem componente robótica.
- E2. Puramente teórico/conceptual, sem validação experimental.
- E3. Sem dados quantitativos comparáveis (só descrição qualitativa).
- E4. Literatura cinzenta não revista por pares (preprints sem publicação, blogues,
  white papers). **Nota:** preprints do arXiv só entram se tiverem versão publicada.
- E5. Duplicado de outro registo já incluído.

## 3. Bases de dados

| Base | Porquê | Acesso |
|---|---|---|
| **Scopus** | cobertura ampla, boa desduplicação, exporta CSV/BibTeX | VPN ISCTE |
| **IEEE Xplore** | núcleo da robótica e engenharia (ICRA, IROS, RA-L, T-RO) | VPN ISCTE |
| **ACM Digital Library** | AAMAS e sistemas multiagente | VPN ISCTE |
| **Web of Science** *(opcional)* | validação cruzada | VPN ISCTE |

> Google Scholar **não** é usado como fonte primária: não é reproduzível (resultados
> variam por utilizador/sessão) nem exportável em bloco. Pode servir para
> *snowballing* (§5), desde que registado.

## 4. String de pesquisa

Versão adotada (Scopus), após calibração registada em `docs/slr/00_pesquisas.md`:

```
TITLE ( "swarm robot*" OR "robot swarm*" OR "multi-robot" )
AND TITLE-ABS-KEY ( "reinforcement learning" OR "MARL" OR "neuroevolution"
                    OR "evolutionary algorithm" OR "particle swarm"
                    OR "bio-inspired optimization" )
AND TITLE-ABS-KEY ( control OR navigation OR coordination OR foraging OR "path planning" )
AND PUBYEAR > 2019
```

> O conceito de enxame é exigido no **título** (e não em título/resumo/palavras-chave):
> a versão inicial devolvia 7 628 registos, porque `"multi-agent system"` no resumo
> apanha toda a literatura multiagente sem componente robótica. A versão adotada
> devolve **456**. As duas contagens estão registadas — calibrar a string é legítimo,
> desde que fique o rasto de o ter feito por critério e não por conveniência.

Adaptar a sintaxe a cada base (IEEE usa `("All Metadata":...)`, ACM usa a sua própria).
**Registar a string EXATA usada em cada base**, tal como foi colada, em
`docs/slr/00_pesquisas.md`.

## 5. Procedimento

1. **Executar** cada pesquisa. Anotar: base, data, string exata, **nº de resultados**.
2. **Exportar** todos os resultados (CSV ou BibTeX) para `docs/slr/raw/<base>.csv`.
3. **Desduplicar** por DOI e por título normalizado → `scripts/slr_pipeline.py dedup`.
4. **Triagem (título + resumo)**: decidir `incluir` / `excluir` + motivo (E1..E5),
   na coluna própria de `docs/slr/screening.csv`. Sem motivo, a linha não conta.
5. **Leitura integral** dos sobreviventes: confirmar ou excluir (novo motivo).
6. **Extração de dados** dos incluídos: paradigma, cenário, métricas, limitação.
7. **Snowballing** (opcional): referências relevantes citadas pelos incluídos.
   Entram marcadas com `origem=snowball`, para não contaminar as contagens da pesquisa.
8. **Gerar** o fluxograma PRISMA e o apêndice a partir dos números REAIS:
   `scripts/slr_pipeline.py prisma`.

## 6. Fronteira entre "revisão" e "fundamentação"

Nem todas as referências da tese vêm da revisão, e isso é normal e honesto:

- **Corpo da revisão** (entra no PRISMA e no apêndice): os artigos levantados por
  este protocolo, que respondem à pergunta da §1.
- **Fontes de fundamentação** (NÃO entram na contagem): as fontes primárias dos
  métodos usados (PPO, SAC, GAT, ES, novelty search, Dec-POMDP) e as obras seminais.
  São citadas no Cap. 2 e no Cap. 5 porque descrevem as ferramentas — não porque
  resultaram de uma pesquisa sistemática.

Esta distinção tem de estar **escrita no Cap. 3**, senão o leitor tenta reconciliar
o n do PRISMA com o número de entradas do `.bib` e não consegue.

## 7. Ameaças à validade (a declarar no capítulo)

- Revisão conduzida por **um único revisor** (sem dupla triagem independente) —
  limitação real de uma dissertação individual; declarar em vez de esconder.
- Restrição a inglês/português e a 4 bases: possível viés de cobertura.
- Recorte temporal 2020+: deliberado (foco no estado da arte pós-GNN), mas exclui
  trabalho fundacional relevante.
