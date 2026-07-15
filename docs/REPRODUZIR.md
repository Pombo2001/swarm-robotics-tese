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
| **Rrobust** — §res_robustez (§1476) | saída de `run_eval.py --fail-frac 0.1` | `run_eval.py` + `plot_robustez.py` | ⚠️ confirmar |
| **Custo computacional** — `tab:res_computacional` (§1498) | tempos dos logs de treino | (ver §res_computacional) | ⚠️ confirmar |
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

- [ ] `tab:res_eval` (§1367) — cada célula (média±dp, sucesso, [runs a 100%]) confere com
      `final_7d/eval_by_run_7d.csv`?
- [ ] Tabela/frases de significância — os p-values e δ citados no Cap. 6 conferem com
      `results/estatisticas/testes_significancia_*.csv`?
- [x] **`tab:res_scale_all` / `tab:res_scale` — VERIFICADO (15 jul, PC do trabalho)** contra
      `escalabilidade_*.csv`: retenção per capita N=100 vs N=20 confere ao pormenor —
      bypass **90%**, coop_door **88%**, u_wall **78%**, none/Sandbox **39%** (+ bottleneck 58%,
      four_rooms 66%, coop_perception 45%). Sucesso do GNN: **28/28 células a 100%**. ✅
- [x] **SLR — VERIFICADO (15 jul, PC do trabalho)** contra `screening.csv` + `raw/`:
      Scopus **456** + IEEE **427** = **883** identificados; **203** duplicados; **680** únicos
      triados (linhas do CSV); **58** com `decisao=incluir`. Todos batem certo. ✅
      *(O split 21 MARL / 23 bio-inspirado NÃO é coluna do CSV — classificação manual, conferir no texto.)*
- [ ] `tab:res_eval` (§1367) — cada célula (média±dp, sucesso, [runs a 100%]) confere com
      `final_7d/eval_by_run_7d.csv`? **(exige torre)**
- [ ] Significância — os p-values e δ do Cap. 6 conferem com `testes_significancia_*.csv`? **(torre)**
- [ ] §res_novelty — os números do Novelty (Muro em U 7/7 a 100%, 69.8±5.9; p=0.026, δ=+0.71;
      bypass p=0.0006, δ=−1.00) conferem com `novelty_final/`? **(exige torre)**

> **Feito a 15 jul:** Sscale e SLR — os dados estavam no PC do trabalho e **conferem 100%**.
> Falta a parte que exige a torre (`final_7d/` + `novelty_final/`): tabela de avaliação,
> significância e Novelty. Trazer com `pos_campanha.py` ou correr lá.
