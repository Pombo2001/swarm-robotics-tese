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

## IEEE Xplore — 13 jul 2026

**String exata** (Command Search, tal como foi colada):

```
("Document Title":"swarm robot*" OR "Document Title":"robot swarm*" OR "Document Title":"multi-robot")
AND ("All Metadata":"reinforcement learning" OR "All Metadata":"MARL" OR "All Metadata":"neuroevolution"
     OR "All Metadata":"evolutionary algorithm" OR "All Metadata":"particle swarm"
     OR "All Metadata":"bio-inspired optimization")
AND ("All Metadata":"control" OR "All Metadata":"navigation" OR "All Metadata":"coordination"
     OR "All Metadata":"foraging" OR "All Metadata":"path planning")
```

- Filtro aplicado na interface: **intervalo de anos 2020–2026** (equivalente ao
  `PUBYEAR > 2019` do Scopus, que a sintaxe do IEEE não aceita na própria string).
- Sem o filtro de anos: 725 resultados. **Com o filtro: 427 documentos.**
- Exportado: CSV de resultados (inclui resumo) → `raw/ieee.csv`
- Acesso: b-on / ISCTE

## ACM Digital Library — não usada

O Scopus indexa a maior parte das atas do IEEE e da ACM relevantes para esta pergunta,
e a sobreposição observada entre as duas bases já usadas é substancial (203 duplicados
em 883 registos, ~23%). A ACM foi dispensada por essa razão, e a decisão é declarada
nas ameaças à validade (§7 do protocolo) em vez de omitida.

---

# Contagens consolidadas (para o fluxograma PRISMA)

Geradas por `scripts/slr_pipeline.py ingest` a partir dos exports em `raw/`:

| Fase | n |
|---|---|
| Identificados (Scopus 456 + IEEE 427) | **883** |
| Duplicados removidos (por DOI / título normalizado) | **203** |
| **Registos únicos para triagem** | **680** |
| Triados (título/resumo) | *a preencher* |
| Avaliados em texto integral | *a preencher* |
| **Incluídos** | *a preencher* |

> As fases seguintes são preenchidas automaticamente a partir de `screening.csv`
> quando se corre `python scripts/slr_pipeline.py prisma`.

## Notas / desvios ao protocolo

- **13 jul 2026** — a string do §4 do protocolo foi ajustada como descrito acima
  (enxame no título, em vez de em título/resumo/palavras-chave). O protocolo foi
  atualizado em conformidade.
