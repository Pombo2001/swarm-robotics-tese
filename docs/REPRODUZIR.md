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
| Figuras finais da tese | `Tese/images/resultados/*.png` (39) | ✅ | ✅ |
| **Eval por run da campanha 7d** | `results/graficos_tese/final_7d/eval_by_run_7d.csv` | ❌ | ✅ |
| **Figuras canónicas 7d** | `results/graficos_tese/final_7d/` | ❌ | ✅ |
| **Tabelas de significância** | `results/estatisticas/testes_significancia_*.{tex,csv}` | ❌ | ✅ |
| **Novelty (QI6)** | `results/novelty_final/{uwall,bypass}/` | ❌ | ✅ |
| Campanha Novelty adaptativo | `results/novelty_adaptativo/` (trazida a 19 jul) | ❌ | ✅ |
| **F1 do mapa grande** (QI7) | `results/mapa_grande/f1_zeroshot_v2/` — **versionado**, exceção deliberada ao `.gitignore`. ⚠️ `f1_zeroshot/` (sem `_v2`) é a corrida **ANULADA** a 29 jul, em que os agentes voavam por cima das paredes; fica no disco como registo e **não se usa** | ✅ | ✅ |
| Campeões da campanha 7d | `results/models_7d/` (21 modelos, 3-9 jul) | ❌ | ✅ + servidor |
| Mega-treino (12 fases) | `results/mega_1mes/` — **as 12 fases fechadas e trazidas** (megaA 2 ago, megaB 3 ago); `resumo_megatreino.json` traz M1-M3 já calculados | ❌ | ✅ |
| **F2 do mapa grande** (QI7) | `results/mapa_grande/f2_{gnn,grad_ppo,grad_sac}/` — **versionado**, como o F1. Fechado a 16 ago (PPO 7 ago, SAC 10 ago); a sentinela de conclusão de cada braço é `logs/_campanha_concluida.txt` | ✅ | ✅ |

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
3. python scripts/statistical_tests.py    # OPCIONAL, e a unidade é o EPISÓDIO (ver abaixo)
                                          # Wilcoxon/Mann-Whitney + Welch + δ de Cliff, das
                                          # CSVs de avaliação -> testes_significancia_POR_EPISODIO_*
4. python scripts/eval_scalability.py --episodes 20
                                          # Zero-Shot N in {10,20,50,100} -> escalabilidade_*.csv
```

**⚠️ O passo 3 NÃO produz a tabela da tese (corrigido a 5 ago).** A unidade dele é o
**episódio**; a da tese é a **execução de treino** — «o que evita a inflação de $n$ que é
comum na literatura comparada» (Contributos). Vinte episódios do mesmo modelo não são
vinte observações independentes. A tabela `tab:res_signif` sai do **passo 2**.

Até 5 de agosto os dois escreviam no **mesmo ficheiro**
(`results/estatisticas/testes_significancia_food_collected.csv`), e a única coisa que
mantinha a tabela certa era esta ordem: o passo 3 sobrescrevia o passo 2, e depois alguém
voltava a correr o passo 2. O backup `..._pre7d.csv` ainda guarda 42 comparações com
`wilcoxon` — a prova de que a sobrescrita aconteceu. Hoje o passo 3 escreve com nome
próprio (`..._por_episodio_*`) e a ordem deixou de poder estragar nada.

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
| **Significância** `tab:res_signif` (Mann-Whitney + δ de Cliff sobre **médias por run**) | `final_7d/eval_by_run_7d.csv` | **`gerar_figuras_7d.py`** → `results/estatisticas/testes_significancia_food_collected.csv`. ⚠️ NÃO é o `statistical_tests.py`: esse compara episódios e escreve `..._por_episodio_*` (corrigido a 5 ago) | ⚠️ torre |
| **Sscale** — Zero-Shot `tab:res_scale_all` (§1431), `tab:res_scale` (§1454), fig `escalabilidade_zeroshot_*` | `results/estatisticas/escalabilidade_*.csv` | `eval_scalability.py` (GNN invariante; PPO/SAC = "N/A" para N≠20) | ✅ PC |
| **Novelty (QI6)** — §res_novelty (§1408) | `results/novelty_final/{uwall,bypass}/` (eval_by_run 7×20 ep) | `eval_by_run.py` + `statistical_tests.py` | ⚠️ torre |
| **Rrobust** — §res_robustez (§1476) | `results/evaluation/eval_{algo}_{cen}[_fail10].csv` (retenção = fail10/base) | `run_eval.py --fail-frac 0.1` | ✅ torre, VERIFICADO 16 jul: 21/21 células, retenção 92,4–105,8% (tese: 92–106% ✓); GNN 92,4–96,9% (✓); >100% só na Perceção Coop. (✓) |
| **Custo computacional** — `tab:res_computacional` (§1498) | medição direta no simulador | `scripts/benchmark_sim.py` (novo, 16 jul) | ✅ torre, VERIFICADO+ATUALIZADO 16 jul: 139 passos/s era PRÉ-vetorização; medição atual ≈420 passos/s (3,0×, consistente c/ o 2,58× do passo); tabela da tese atualizada c/ ambos |
| **QI7 — F1 do mapa grande** (zero-shot de topologia), `seccao_mapa_grande.tex` §Transferência | `results/mapa_grande/f1_zeroshot_v2/zeroshot_*.csv` — as **quatro** condições (**versionado**; ⚠️ `f1_zeroshot/`, sem `_v2`, é a corrida ANULADA a 29 jul); 1 linha por episódio, com `NormObs`/`Controlo`/`env_hash`/`ModeloPath`/`ModeloData`) | `eval_zeroshot_mapa.py` (produz) → `analise_f1_controlos.py` (lê as 4 condições e aplica o veredicto do pré-registo §3) | ✅ PC — **as quatro condições fechadas e no disco** (repetidas de raiz a 31 jul, depois da correção das paredes): 84 células, 1680 episódios, todas a 0,00 |
| **QI6 replicada a n=28** — mega-treino, §res_novelty (28/28 vs 15/28, Fisher; os 6 pares de M2; a ablação do anilamento; as 3 células exploratórias) | `results/mega_1mes/*/evaluation/eval_by_run.csv` (12 fases) + `resumo_megatreino.json` | `mega_stream{A,B}.sh` no servidor → `analise_megatreino.py` (imprime; o JSON é o registo) | ✅ PC |
| **QI7 — F2 do mapa grande** (treino nativo) | `results/mapa_grande/f2_*/evaluation/eval_by_run.csv` (3 braços × 21 execuções × 20 ep = 1260 episódios) | `mapa_streamF2.sh {gnn\|grad}` no servidor → `analise_mapa_grande.py` | ✅ PC — **fechado**: PPO 7 ago, SAC 10 ago, GNN 16 ago. O braço `longo` (exploratório) foi **cancelado** e não tem dados (emenda 24) |
| **Figuras** (mecanismo) | `Tese/images/resultados/*.png` | copiar o PNG com o nome que o `\figresultado` espera + recompilar (sem editar o `.tex`) | ✅ PC |

> A **QI7** (composição de dificuldades) é a única cujas duas fases se leem em
> conjunto: o contraste entre o que transfere sem retreino (F1) e o que se aprende
> de raiz (F2) é, ele próprio, o resultado. Nenhuma delas entra nas tabelas dos
> sete cenários — ver `PRE_REGISTO_MAPA_GRANDE.md`, compromisso 3.
>
> As 6 perguntas de investigação (QI1–QI6) mapeiam assim: **QI1** Ptask+significância ·
> **QI2** Sscale (representação vs otimizador) · **QI3** Rrobust · **QI4** síntese das três
> (o "mapa de escolha" — não tem dados próprios) · **QI5** desenho da aptidão (homing) ·
> **QI6** Novelty. Cada uma remete para uma linha acima.
> *(Corrigido a 25 jul: dizia "QI1/QI3 Ptask" e "QI4 Rrobust", trocando as duas — na tese
> a QI3 é a robustez e a QI4 é o critério de escolha.)*

---

## Como isto se audita hoje (os verificadores)

O mapa acima diz de onde vem cada número. Estes comandos **confirmam-no**, e são
o que se corre antes de qualquer entrega. Todos leem os valores esperados do
`.tex` ou dos CSV — nenhum tem números fixados lá dentro, que é o defeito que
transformaria um verificador numa segunda cópia da tese.

| Comando | O que confirma | Escala |
|---|---|---|
| `python scripts/verificar_numeros_tese.py` | os números do corpo da dissertação **e do artigo** contra os CSV, o config e o ambiente instanciado | ~640 valores em 14 blocos |
| `python scripts/verificar_mapa_grande.py` | a secção da QI7 inteira: geometria, F1, F2, M1-M3, Trabalhos Futuros | 62 valores |
| `python scripts/verificar_protocolo.py` | o **vocabulário do protocolo** espalhado pela prosa («7 execuções», «195 minutos», «20 episódios», `$n=28$`) contra as campanhas que de facto correram | 155 valores |
| `python scripts/verificar_figuras_tese.py` | cada figura do PDF **pixel a pixel** contra a fonte em `results/` (`--listar` diz de que guião sai) | 46 figuras |
| `python scripts/verificar_bibliografia.py` | autor, ano e título de cada entrada citada contra CrossRef/DataCite; e os dois `.bib` entre si | 19 com DOI + 46 comuns |
| `python scripts/verificar_preregistos.py` | cada **compromisso pré-registado** contra o que a tese reporta (`--escrever` gera `PREREGISTO_VS_REPORTADO.md`) | 29 compromissos |
| `python scripts/verificar_dashboard.py` | os números do dashboard contra os da tese (mesma fonte, mesmo valor) | 44 valores |
| `python scripts/verificar_paridade_pi.py` | tudo o que as vistas leem vai no delta do `atualizar_pi.sh` | 316 leituras |
| `python scripts/ensaiar_reproduzir.py` | **este documento** contra o disco: cada caminho existe, cada script compila, e o estado que ele afirma ainda é verdade | 75 caminhos, 26 scripts |
| `python -m pytest tests -q` | a suite completa (física, avaliação, dashboard, verificadores) | 161 testes |

⚠️ **Um verificador só vale depois de ter falhado uma vez de propósito.** Os de
figuras, de pré-registos e de paridade têm ensaios de mutação
(`tests/test_verificar_preregistos.py`, `tests/test_paridade_pi.py`,
`scripts/ensaiar_verificador.py`): mutila-se a fonte e exige-se que acusem. O de
figuras foi assim que se corrigiu — dava por boa uma figura com um quadrado de
40×40 pixels pintado por cima, porque o limiar era relativo.

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
6. **Validar um script de análise escreve por cima dos resultados reais** (28 jul):
   ao testar o `analise_f1_controlos.py` com um CSV sintético, o veredicto **falso**
   foi escrito na pasta que a tese cita. Apagado no minuto seguinte, mas o padrão
   é geral — um script de análise cujo destino é fixo não distingue um ensaio de
   uma corrida boa. O `analise_f1_controlos.py` passou a **exigir `--saida`**
   quando algum CSV de entrada vem de fora da pasta canónica.
   *(Verificado a seguir: o `analise_adaptativo.py`, o `analise_megatreino.py` e o
   `analise_mapa_grande.py` **não escrevem ficheiro nenhum** — só imprimem, e
   guarda-se a saída com `>` quando se quer. Não têm este problema nem precisam
   da guarda; o `analise_f1_controlos.py` é o único que grava.)*
7. **Trazer do servidor sobrescreve em silêncio** (28 jul): cada corrida grava o
   resultado com o **mesmo nome** no **seu** diretório (`zeroshot_mapa_grande.csv`
   em `~/swarm-mapa-c{1,2,3}/`). Ao trazer o segundo para a pasta onde já estava
   o primeiro, o `pscp` escreveu por cima sem uma palavra — e o que se perdeu foi
   a **condição natural do F1**, 420 episódios e 6 h de servidor. Recuperou-se com
   `git checkout` **porque esses CSV estão versionados de propósito** (a exceção
   ao `.gitignore` decidida a 27 jul pagou-se no dia seguinte). Desde então o
   `trazer_do_servidor.sh` **avisa e aborta** se o alvo já existir
   (`TRAZER_FORCAR=1` para forçar). Ao trazer várias corridas da mesma campanha:
   nomes distintos, sempre.
8. **Hashes de floats não atravessam máquinas** (27 jul): um teste que comparava
   SHA-256 de somas de floats falhou no servidor sem ser regressão (266,003105779438
   aqui vs ...439 lá). Comparar com tolerância. A impressão digital do ambiente do
   mapa não sofre disto **porque arredonda a 4 casas antes de encadear** — e por
   isso dá `267a7b547aed` nas duas máquinas.

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
- [x] ✅ **RESOLVIDO (27 jul): a tese já declara a perda de proveniência no corpo.**
      A decisão que ficou pendente a 16 jul ("acrescentar nota ou deixar como
      está") estava, afinal, tomada: o §res_novelty diz textualmente que *"os
      artefactos brutos desta execução preliminar (avaliação por episódio e
      modelo) não foram retidos --- foram entretanto sobrescritos no servidor de
      treino por campanhas posteriores ---, pelo que os valores citados
      constituem o registo da altura e não são reproduzíveis a partir dos dados
      arquivados"*, e contrasta-o com as campanhas seguintes, que têm todos os
      dados versionados. **Nada a fazer.** O detalhe original fica abaixo.
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
>
> **Feito a 27 jul (torre) — auditoria de PROVENIÊNCIA:** verificou-se que as
> **17/17 fontes** prometidas por este mapa existem de facto neste PC (SLR bruta e
> triada, `eval_by_run_7d.csv`, significância, os 7 CSV de escalabilidade,
> Novelty final e adaptativo, os 21 CSV de `fail10` e 14 de base, o
> `benchmark_sim.py` e as 37 figuras). Nenhuma linha do mapa aponta para um
> ficheiro que só exista no servidor — na defesa, qualquer "de onde vem este
> número?" tem resposta na hora, sem VPN. Acresce que os **campeões da campanha
> 7d** passaram a estar no disco em `results/models_7d/` (21/21, datados de 3-9
> jul, guarda de campanha a passar), o que também torna o F1 reproduzível
> localmente.
>
> **Feito a 17 ago (torre) — o mapa deixou de ser só um mapa.** Correu-se o
> `scripts/ensaiar_reproduzir.py` sobre este documento: os **75 caminhos** que ele
> promete existem, os **26 scripts** que cita existem e compilam, e os 4 passos do
> pipeline apontam para ficheiros reais. Os únicos achados foram de **estado**, e
> são os que este mapa tem de mais frágil: dizia que o F2 estava «a correr desde 3
> ago» (fechou a 16), que o mega-treino tinha «6 fases por fechar» (tem as 12 no
> disco) e que os controlos do F1 estavam «no servidor» (estão cá desde 31 jul).
> Corrigidos, e o ensaio passou a verificá-los — uma linha que envelhece deixa de
> o poder fazer em silêncio. Acrescentou-se também a linha da **QI6 replicada a
> n=28** (mega-treino), que estava reportada na tese e não tinha entrada no mapa.
>
> **Feito a 28 jul (torre):** acrescentadas as duas linhas da **QI7** ao mapa. O
> F1 é a primeira fonte de resultados **versionada no git** (`results/mapa_grande/`,
> exceção deliberada ao `.gitignore`) — decidida precisamente por causa do buraco
> do braço Novelty preliminar, que é o único número da tese sem artefacto. As
> armadilhas 6 e 7 são novas e vieram de erros desta semana.
