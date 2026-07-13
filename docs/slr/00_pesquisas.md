# Registo das pesquisas executadas

> Preenchido NO MOMENTO em que cada pesquisa foi corrida. É este registo que torna a
> revisão reproduzível — sem ele, os números do PRISMA não se conseguem justificar.

## Scopus — 13 jul 2026

**String exata** (pesquisa avançada, tal como foi colada):

```
TITLE ( "swarm robot*" OR "robot swarm*" OR "multi-robot" )
AND TITLE-ABS-KEY ( "reinforcement learning" OR "MARL" OR "neuroevolution"
                    OR "evolutionary algorithm" OR "particle swarm"
                    OR "bio-inspired optimization" )
AND TITLE-ABS-KEY ( control OR navigation OR coordination OR foraging OR "path planning" )
AND PUBYEAR > 2019
```

- **Resultados: 456 documentos**
- Exportado: CSV com citação + resumo + palavras-chave, **sem truncar** → `raw/scopus.csv`
- Acesso: conta institucional ISCTE (sessão autenticada no Scopus)

### Calibração da string (registar as tentativas faz parte do método)

| # | Alteração | Resultados |
|---|---|---|
| 1 | Conceito de enxame em `TITLE-ABS-KEY` (versão inicial do protocolo) | **7 628** — inviável de triar |
| 2 | Conceito de enxame restrito a `TITLE` (versão adotada) | **456** |

A tentativa 1 devolvia milhares porque `"multi-agent system"` no resumo apanha toda a
literatura de sistemas multiagente sem componente robótica. Exigir o conceito de
enxame/multi-robô **no título** concentra a pesquisa nos trabalhos cujo objeto de
estudo é o enxame — que é a pergunta da revisão (§1 do protocolo). A decisão foi
tomada por critério de âmbito, e não por conveniência do número; ambas as contagens
ficam registadas.

## IEEE Xplore — (por correr)

## ACM Digital Library — (não usada)

A justificar no capítulo: o Scopus indexa a maior parte das atas do IEEE e da ACM
relevantes para esta pergunta. A ACM foi dispensada, e isso é declarado nas ameaças à
validade (§7 do protocolo).

## Notas / desvios ao protocolo

- **13 jul 2026** — a string do §4 do protocolo foi ajustada como descrito acima
  (enxame no título, em vez de em título/resumo/palavras-chave). O protocolo foi
  atualizado em conformidade.
