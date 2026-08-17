# Pré-registo → o que é reportado

*Gerado por `scripts/verificar_preregistos.py` em 17/08/2026 17:40.*

Um compromisso pré-registado que não seja reportado é o defeito mais
caro desta dissertação: é o que separa uma regra fixada à partida de
uma escolhida depois de ver os resultados. Esta tabela é gerada, não
escrita — se um compromisso deixar de ser cumprido, ela muda sozinha.


## Mapa grande (QI7)

| | compromisso | onde é reportado | evidência |
|---|---|---|---|
| ✅ | **MG-desenho-n** — 3 algoritmos × 21 execuções (emenda 19) | `results/mapa_grande/f2_*` | GNN 21 · PPO 21 · SAC 21 execuções |
| ✅ | **MG-desenho-ep** — avaliação determinística de 20 episódios | `results/mapa_grande/f2_*` | 20 episódios em todas as execuções |
| ✅ | **MG-desenho-params** — N=20, max_steps=2000, required_to_eat=1, 106 obstáculos | `configs/foraging.yaml + src/environment` | o simulador constrói exatamente o pré-registado |
| ✅ | **MG-rep-1** — todos os 3 algoritmos e todas as execuções, sem cherry-picking | `Tese/seccao_mapa_grande.tex (tab:f2_mapa_grande)` | a tabela do F2 tem as três linhas |
| ✅ | **MG-rep-2** — convergência = descritivo; magnitude = teste (M2 não vira teste por o n ter subido) | `Tese/seccao_mapa_grande.tex` | M2 rotulada descritiva e a limitação declara porquê |
| ✅ | **MG-rep-3** — o mapa NÃO entra nas tabelas dos sete cenários | `Tese/main.tex (tab:res_eval, tab:res_signif)` | as duas tabelas dos sete cenários não o mencionam |
| ✅ | **MG-rep-4** — o que fechar depois de 22 ago não entra na tese | `results/mapa_grande/f2_*/logs/_campanha_concluida.txt` | última campanha fechou 16/08 16:21 (limite 22/08) |
| ✅ | **MG-rep-5a** — emendas numeradas e datadas (nada muda em silêncio) | `docs/PRE_REGISTO_MAPA_GRANDE.md` | 24 emendas numeradas, 1..24, sem buracos |
| ✅ | **MG-expl** — braço exploratório GNN @2340 min × 3 (emenda 20) | `docs/PRE_REGISTO_MAPA_GRANDE.md` | não correu, e o pré-registo declara-o em emenda datada |
| ✅ | **MG-expl-tex** — a dissertação não invoca braços que não correram | `Tese/seccao_mapa_grande.tex` | a secção refere-o e declara, na mesma frase, que não foi lançado |
| ✅ | **MG-M1** — M1 reportada (valores conferidos por verificar_mapa_grande.py) | `Tese/seccao_mapa_grande.tex` | presente |
| ✅ | **MG-M2** — M2 reportada (valores conferidos por verificar_mapa_grande.py) | `Tese/seccao_mapa_grande.tex` | presente |
| ✅ | **MG-M3** — M3 reportada (valores conferidos por verificar_mapa_grande.py) | `Tese/seccao_mapa_grande.tex` | presente |
| ✅ | **MG-M3-valor** — M3 do GNN bate com o eval_by_run.csv | `Tese/seccao_mapa_grande.tex` | secção 43%, medido 43.3% |
| ✅ | **MG-F1** — F1 (zero-shot) reporta-se mesmo dando zero em tudo | `Tese/seccao_mapa_grande.tex` | as 84 células e os 1680 episódios estão reportados |
| ✅ | **MG-regra** — limiar ⌈5/7×n⌉=15 e nº de execuções convergentes declarado (emenda 21) | `Tese/seccao_mapa_grande.tex + main.tex (Conclusões)` | limiar 15 e k=4/21 declarados |
| ✅ | **MG-objpuro** — os 2 runs do braço errado (objetivo puro) declarados e fora de M1--M3 (emenda 23) | `docs/PRE_REGISTO_MAPA_GRANDE.md` | declarados na emenda 23, com o diretório onde ficaram |

## Mega-treino

| | compromisso | onde é reportado | evidência |
|---|---|---|---|
| ✅ | **MT-M1** — M1: magnitude (unilateral) + Fisher sobre convergência | `Tese/main.tex (sec:res_novelty)` | 28/28 vs 15/28 com Fisher, e bate com o resumo da análise |
| ✅ | **MT-M2** — M2: os 6 pares no Muro em U, p brutos e multiplicidade assinalada | `Tese/main.tex (sec:res_novelty)` | 6 pares na análise; o texto declara os p brutos e a multiplicidade |
| ✅ | **MT-M3** — M3: bypass adaptativo vs peso fixo, declarado como comparação entre campanhas | `Tese/main.tex (sec:res_novelty)` | n=21 vs n=7, e o texto declara que são campanhas diferentes |
| ✅ | **MT-expl** — exploratório: reportar TODAS as configs e fases | `Tese/main.tex (sec:res_novelty)` | as 4 células exploratórias estão reportadas (2 no resumo da análise) |
| 👤 | **MT-rep-1** — todos os runs, todas as configs, todas as fases | `Tese/main.tex (sec:res_novelty)` | as 12 células (A1-A5, B1-B7) estão cobertas por MT-M1..MT-expl; a exaustividade da prosa é leitura humana |

## Novelty adaptativo (QI6)

| | compromisso | onde é reportado | evidência |
|---|---|---|---|
| ✅ | **NA-T1** — T1 reportado | `Tese/main.tex (sec:res_novelty)` | presente |
| ✅ | **NA-T2** — T2 reportado | `Tese/main.tex (sec:res_novelty)` | presente |
| ✅ | **NA-T3** — T3 reportado | `Tese/main.tex (sec:res_novelty)` | presente |
| ✅ | **NA-T4** — T4 reportado | `Tese/main.tex (sec:res_novelty)` | presente |
| ✅ | **NA-rep-1** — reportar TODOS os 7 cenários e TODOS os 7 runs | `results/novelty_adaptativo/week_*_fase1` | 7 cenários × 7 execuções na condição primária |
| ✅ | **NA-rep-3** — p brutos + peso no δ, não em cruzar 0,05 | `Tese/main.tex (sec:res_novelty)` | declarado no parágrafo de T4 |
| ✅ | **NA-expl** — braços @390 min rotulados exploratórios | `Tese/main.tex (sec:res_novelty)` | rotulados no texto, fora da regra de decisão |

---

✅ verificado por medição ou por padrão encontrado no `.tex` · ❌ por cumprir · 👤 leitura humana
