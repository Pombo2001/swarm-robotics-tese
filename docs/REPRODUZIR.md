# REPRODUZIR — de cada resultado da tese à sua origem

> **Objetivo:** para cada número, tabela e figura de resultados da tese, dizer **que dados
> o geram e que script o produz**. Serve dois fins: (1) defesa — responder na hora a "de
> onde vem este número?"; (2) auditoria — correr o pipeline e confirmar que a tese bate
> certo com os CSVs. Criado a **15 jul 2026** (estado pós-campanha 7d; a campanha de
> Novelty adaptativo ainda corria).
>
> ⚠️ **Este documento é o MAPA, não a auditoria.** A verificação número-a-número tem de
> correr onde os CSVs canónicos vivem (ver secção seguinte). Aqui está o caminho; falta
> alguém percorrê-lo com os dados à frente.

---

## ⚠️ Onde vivem os dados (torre de casa vs PC do trabalho)

A campanha final e o Novelty foram trazidos para a **torre de casa**; o PC do trabalho só
tem um subconjunto. Antes de tentar reproduzir/verificar, confirma onde estás.

| Fonte de dados | Caminho | PC trabalho | Torre |
|---|---|:---:|:---:|
| Escalabilidade (Zero-Shot) | `results/estatisticas/escalabilidade_*.csv` | ✅ | ✅ |
| Triagem da SLR | `docs/slr/screening.csv` + `docs/slr/raw/` | ✅ | ✅ |
| Figuras finais da tese | `Tese/images/resultados/*.png` (36) | ✅ | ✅ |
| **Eval por run da campanha 7d** | `results/graficos_tese/final_7d/eval_by_run_7d.csv` | ❌ | ✅ |
| **Figuras canónicas 7d** | `results/graficos_tese/final_7d/` | ❌ | ✅ |
| **Tabelas de significância** | `results/estatisticas/testes_significancia_*.{tex,csv}` | ❌ | ✅ |
| **Novelty (QI6)** | `results/novelty_final/{uwall,bypass}/` | ❌ | ✅ |
| Campanha Novelty adaptativo | (no servidor `.14`, fecha ~19-20 jul) | ❌ | ⏳ |

> A auditoria número-a-número (última secção) faz-se **na torre**, ou depois de trazer
> `final_7d/` + `novelty_final/` para cá com `python scripts/pos_campanha.py`.

---

## Pipeline de reprodução (ordem obrigatória)

Ao trazer QUALQUER campanha do servidor, esta é a sequência. Saltar passos = armadilhas
conhecidas (ver secção final).

```
1. python scripts/pos_campanha.py        # restaura modelos + torna a sessão auto-contida
                                          # (SEM isto, tudo usa modelos da campanha anterior)
2. python scripts/gerar_figuras_7d.py --install-oficial
                                          # FUNDE a campanha GNN (~/swarm-robotics-tese) com
                                          # a MLP (~/run7d_mlp); só o output DESTE script e
                                          # canónico. Gera eval_by_run_7d.csv + boxplots +
                                          # significância entre algoritmos + copia p/ a tese.
3. python scripts/statistical_tests.py    # Mann-Whitney U + Welch + rank-biserial, por
                                          # cenário, das CSVs de avaliação -> results/estatisticas/
4. python scripts/eval_scalability.py --episodes 20
                                          # Zero-Shot N in {10,20,50,100} -> escalabilidade_*.csv
```

**Porquê o passo 2 é indispensável (armadilha real):** a campanha 7d correu em **duas
instalações separadas** do servidor (GNN numa, PPO+SAC noutra). Os gráficos gerados *dentro*
de cada campanha misturam modelos antigos da outra família (o `all_best_scores.csv` do
servidor acumulava runs de campanhas anteriores). **Só a fusão feita pelo `gerar_figuras_7d.py`
serve para a tese** — os PNGs "brutos" de cada campanha não.

---

## Mapa: resultado da tese → dados → script

| Resultado (secção/tabela) | Dados-fonte | Script que gera | Onde |
|---|---|---|---|
| **Cap. 3 — SLR**: fluxograma PRISMA, apêndice, "1 em 58", 21/23/58 | `docs/slr/screening.csv` (+ `raw/`) | `slr_pipeline.py prisma` → `Tese/prisma_gerado.tex` + `Tese/apendice_slr.tex` (via `\input`, linhas 690/1709) | ✅ PC |
| **Ptask** — tabela principal de avaliação `tab:res_eval` (§1367); boxplots de eval (`boxplot_eval_*`); §res_ptask/global | `results/evaluation/eval_{algo}_{cenario}.csv` + `final_7d/eval_by_run_7d.csv` | `gerar_figuras_7d.py` (funde GNN+MLP) | ⚠️ torre |
| **Significância** (Mann-Whitney/Welch/rank-biserial) por cenário | CSVs de avaliação (mesma métrica p/ todos: `food_collected`/sucesso) | `statistical_tests.py` → `results/estatisticas/testes_significancia_*.{tex,csv}` | ⚠️ torre |
| **Sscale** — Zero-Shot `tab:res_scale_all` (§1431), `tab:res_scale` (§1454), fig `escalabilidade_zeroshot_*` | `results/estatisticas/escalabilidade_*.csv` | `eval_scalability.py` (GNN invariante; PPO/SAC = "N/A" para N≠20) | ✅ PC |
| **Novelty (QI6)** — §res_novelty (§1408) | `results/novelty_final/{uwall,bypass}/` (eval_by_run 7×20 ep) | `eval_by_run.py` + `statistical_tests.py` | ⚠️ torre |
| **Rrobust** — §res_robustez (§1476) | `results/evaluation/eval_{algo}_{cen}[_fail10].csv` (retenção = fail10/base) | `run_eval.py --fail-frac 0.1` | ✅ torre, VERIFICADO 16 jul: 21/21 células, retenção 92,4–105,8% (tese: 92–106% ✓); GNN 92,4–96,9% (✓); >100% só na Perceção Coop. (✓) |
| **Custo computacional** — `tab:res_computacional` (§1498) | medição direta no simulador | `scripts/benchmark_sim.py` (novo, 16 jul) | ✅ torre, VERIFICADO+ATUALIZADO 16 jul: 139 passos/s era PRÉ-vetorização; medição atual ≈420 passos/s (3,0×, consistente c/ o 2,58× do passo); tabela da tese atualizada c/ ambos |
| **Figuras** (mecanismo) | `Tese/images/resultados/*.png` | copiar o PNG com o nome que o `\figresultado` espera + recompilar (sem editar o `.tex`) | ✅ PC |

> As 6 perguntas de investigação (QI1–QI6) mapeiam assim: QI1/QI3 Ptask+significância ·
> QI2 Sscale (representação vs otimizador) · QI4 Rrobust · QI5 desenho da aptidão (homing)
> · QI6 Novelty. Cada uma remete para uma linha acima.

---

## Armadilhas de reprodução (não repetir — do histórico)

1. **Modelos da campanha anterior** (armadilha nº9): `results/models*` já teve modelos de
   junho a contaminar a avaliação local (bottleneck deu 0 recolhas em vez de 121, durante
   dias). **Correr sempre `pos_campanha.py` ao chegar.**
2. **Gráficos "brutos" do servidor não são canónicos** — misturam famílias/campanhas. Só o
   `gerar_figuras_7d.py` funde corretamente. (Ver acima.)
3. **CSV de avaliação tem de ser da MESMA data dos modelos** — já enganou duas vezes. Ao
   re-treinar, re-avaliar SEMPRE antes de concluir.
4. **Números de TREINO ≠ resultado** (armadilha nº3): fitness (GNN) e recompensa (PPO/SAC)
   têm escalas incompatíveis. O veredicto oficial é a **avaliação** (`eval_*`), nunca o log
   de treino. Não concluir nada no Cap. 6 a partir de scores de treino.
5. **Windows**: não escrever YAML/`.tex` com `Set-Content`/`Out-File` PS5.1 (mete BOM).

---

## Verificação pendente (a auditoria número-a-número)

Isto é o que falta para o `REPRODUZIR.md` deixar de ser mapa e passar a auditoria. **Correr
na torre** (onde estão `final_7d/` e `novelty_final/`):

- [x] **`tab:res_eval` — VERIFICADO (16 jul, torre)** contra `final_7d/eval_by_run_7d.csv`
      e `resumo_por_cenario_7d.csv`: 21/21 células conferem em sucesso e média. **3 dp
      estavam mal arredondados** (arredondamento duplo na transcrição) e foram CORRIGIDOS
      no `main.tex`: u_wall GNN 32,7→**32,6**; Gargalo GNN 20,0→**19,9**; Porta Coop. GNN
      1,0→**0,9**. O 32,7 repetia-se no texto (§res_novelty + QI6) — corrigido também. ✅
- [x] **Significância — VERIFICADA (16 jul, torre)**: as 21 linhas da `tab:res_signif`
      (médias, U, p, δ, veredicto) conferem com `testes_significancia_food_collected.csv`
      (= `testes_significancia_runs_7d.csv`). Sem alterações. ✅
- [x] **`tab:res_scale_all` / `tab:res_scale` — VERIFICADO (15 jul, PC do trabalho)** contra
      `escalabilidade_*.csv`: retenção per capita N=100 vs N=20 confere ao pormenor —
      bypass **90%**, coop_door **88%**, u_wall **78%**, none/Sandbox **39%** (+ bottleneck 58%,
      four_rooms 66%, coop_perception 45%). Sucesso do GNN: **28/28 células a 100%**. ✅
- [x] **SLR — VERIFICADO (15 jul, PC do trabalho)** contra `screening.csv` + `raw/`:
      Scopus **456** + IEEE **427** = **883** identificados; **203** duplicados; **680** únicos
      triados (linhas do CSV); **58** com `decisao=incluir`. Todos batem certo. ✅
      *(O split 21 MARL / 23 bio-inspirado NÃO é coluna do CSV — classificação manual, conferir no texto.)*
- [x] **§res_novelty — VERIFICADO (16 jul, torre)** contra `novelty_final/{uwall,bypass}/
      results/evaluation/eval_by_run.csv` + `final_7d/eval_by_run_7d.csv` (braço objetivo),
      Mann-Whitney exato e δ **recalculados de raiz**: u_wall Novelty 69,8±5,9, 7/7 a 100%
      vs obj 24,5±32,6, 3/7 (p=0,0262→"0,026" ✓, δ=+0,71 ✓); bypass Novelty 63,0±21,9, 7/7
      vs obj 86,7±2,0 (p=0,0006 ✓, δ=−1,00 ✓). Tudo confere. ✅
- [x] ⚠️ **Comparação preliminar (§res_novelty, "indício") — FONTE PERDIDA (verificado
      16 jul no servidor)**: o braço objetivo (64,5±3,5, 20 ep) está coberto por
      `results/evaluation/eval_comparacao_cooperative_door_bypass.csv`, mas o CSV
      por-episódio E o modelo do braço Novelty preliminar (81,3±1,9, 600 min, 2 jul)
      foram **sobrescritos** em `~/swarm-novelty` pela fase 1 da week_B (14-15 jul) e
      nunca tinham sido trazidos nem commitados. O Wilcoxon p=8,7×10⁻⁵ e o 81,3±1,9
      ficam sem artefacto reprodutível — os números foram registados na altura (sessão
      de 2 jul), mas não há CSV para mostrar na defesa. A tese JÁ despromove esta
      comparação a "indício, não resultado" com as ressalvas certas; decidir com o
      utilizador se se acrescenta uma nota de "dados não retidos" ou se fica como está.

> **Feito a 15 jul (PC):** Sscale e SLR conferem 100%. **Feito a 16 jul (torre):**
> `tab:res_eval` (3 dp corrigidos), `tab:res_signif` e §res_novelty — **auditoria
> número-a-número COMPLETA**. Único buraco: o CSV do braço Novelty preliminar (ver ⚠️ acima).
