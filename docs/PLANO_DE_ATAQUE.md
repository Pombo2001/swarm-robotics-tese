# PLANO DE ATAQUE — Tese de Mestrado (até Outubro 2026)

> **Para o Claude/assistente**: este documento é o ponto de re-entrada do projeto.
> Lê isto primeiro; o histórico detalhado (decisões, bugs corrigidos, armadilhas) está
> na memória persistente (`memory/project_thesis_swarm.md` e `server_training_setup.md`).
> **Para o Gonçalo**: atualiza as checkboxes à medida que avanças; quando algo mudar de
> rumo, regista aqui a decisão e a data.

**Tese**: "Aprendizagem por Reforço para Controlo de Enxames" — ISCTE, Mestrado em IA
**Orientador**: Prof. Luís Nunes | **Prazo**: Outubro 2026 | **Hoje**: 2026-07-01

---

# 🏁 RESULTADOS FINAIS — campanha de 7 dias (10 jul 2026)

> ⚠️ **Tudo o que está abaixo desta secção é HISTÓRICO.** Várias conclusões dessas
> secções antigas (GNN colapsa nos labirintos; *reward hacking* do PPO no Muro U; SAC
> resolve tudo; Sscale 15%→100%) foram **REFUTADAS** pela campanha final. Lê-as como
> registo do percurso, não como estado do projeto.

**Protocolo**: 3 algoritmos × 7 cenários × **7 runs** independentes = 147 treinos
(GNN 195 min/run, PPO/SAC 48 min/run). Avaliação determinística: 20 ep/run com seeds
emparelhadas = 140 ep/célula. Significância: Mann-Whitney + δ de Cliff sobre as
**médias por run** (n=7) — a unidade independente é o run, não o episódio.

Recolhas/ep (média ± dp *entre runs*), sucesso médio, [runs a 100%]:

| Cenário | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 38.3±31.0 (86%) [5/7] | **71.5±1.0** (100%) [7/7] | 69.2±1.9 (100%) [7/7] |
| Muro em U | 24.5±32.7 (43%) [3/7] | **39.6±36.7** (71%) [4/7] | 9.0±15.1 (34%) [2/7] |
| Gargalo | 121.4±20.0 (100%) [7/7] | **123.2±1.2** (100%) [7/7] | 41.4±36.8 (72%) [5/7] |
| Quatro Salas | **59.8±13.2** (100%) [7/7] | 33.6±3.8 (100%) [7/7] | 31.8±3.3 (100%) [7/7] |
| Porta Cooperativa | **69.8±1.0** (100%) [7/7] | 67.1±3.7 (100%) [7/7] | 62.1±2.5 (100%) [7/7] |
| Perceção Cooperativa | **19.0±8.7** (91%) [6/7] | 15.3±0.4 (100%) [7/7] | 16.1±0.8 (100%) [7/7] |
| Porta c/ Alternativa | **86.7±2.0** (100%) [7/7] | 85.3±4.0 (100%) [7/7] | 68.6±3.4 (100%) [7/7] |

**Achado central**: o "colapso do evolutivo" era um **artefacto do desenho da fitness**
(o retorno acumulado é *farmável* por deambulação), não uma limitação do paradigma. Com
o **homing terminal** (`J = f̄·10⁴ + 5000·h̄`), o GNN converge em **28/28 runs** dos quatro
labirintos não-decetivos e é **significativamente superior a ambos** os métodos de gradiente
em 3 cenários (four_rooms, coop_door, perception) e superior ao SAC em mais 2 (bottleneck,
bypass, empatando com o PPO).

**Refutações explícitas do plano antigo:**
- ~~GNN colapsa nos labirintos~~ → curado pelo homing (28/28 runs).
- ~~PPO faz *reward hacking* no Muro U (0%)~~ → curado pela recompensa simplificada;
  hoje o PPO é o **melhor** no Muro U (4/7 runs a 100%). O *reward hacking* subsiste
  apenas como **nota histórica** sobre a calibração do bónus de exploração.
- ~~SAC resolve os 6 cenários~~ → o SAC é o **mais frágil** nos gargalos físicos
  (bottleneck 5/7, u_wall 2/7).
- ~~Sscale: GNN 15%→100% de sucesso~~ → GNN a **100% em todas** as dimensões
  (N=10→100); o que desce é a recolha *per capita* (3.82→1.36, recurso finito), e as
  recolhas totais **crescem** (38.2→136.3).
- **Muro em U**: nenhum algoritmo o resolve de forma fiável. É **bimodal** nos três
  (GNN 3/7, PPO 4/7, SAC 2/7) e **nenhuma diferença é significativa**. O sinal de treino
  está correto (potencial geodésico aponta para o desvio) — o que falha é a **descoberta**,
  porque o agente só observa a bússola euclidiana e o LiDAR local.
- **Novelty Search**: +26% vs objetivo puro (81.3 vs 64.5, Wilcoxon p=8.7e-5, δ=+1.00),
  MAS com 600 min vs 195 → confundido com orçamento. A campanha final mostra que o homing
  sozinho resolve o bypass (7/7, 86.7). Novelty deixa de ser "o melhor resultado" e passa
  a "mecanismo de robustez para orçamento curto / deceção mais severa".

> 📋 **Decisão em aberto — o que treinar nos últimos 2 meses:** ver
> **[`docs/PROPOSTA_TREINO_FINAL.md`](PROPOSTA_TREINO_FINAL.md)** (proposta autónoma, com custos,
> cautelas metodológicas e títulos alternativos para o artigo). Resumo: correr o **Novelty Search
> no Muro em U e no bypass com orçamento igualado** (~2 dias, fecha as duas lacunas que restam);
> **não** repetir a campanha 7×7 nem tentar a política de atenção por gradiente.

**Estado dos entregáveis** (branch `feat/novelty-search` — toda a tese final está aqui, **não na `main`**; fazer merge antes de 15 set):
- Tese: 99 págs, compila, Cap. 6 + Conclusões + QI1-6 alinhados com estes dados.
- Artigo: 8 págs PT-PT, reescrito (commit `ed1c069`), compila.
- Dados: `results/graficos_tese/final_7d/` (figuras canónicas + eval_by_run_7d.csv).
  Regenerar com `scripts/gerar_figuras_7d.py --install-oficial`.

---

## ⏱ ATUALIZAÇÃO 2 jul 2026 (manhã) — CHECKLIST DE RETOMA EXECUTADO ✅

> Eval do train3d fechou às 23h40 de 1 jul (sessão `01-07-2026_23h40m`); servidor sem tmux.
> Tudo trazido, src corrigido deployado, Novelty avaliado. Falta SÓ a decisão dos re-runs.

**✅ Feito (por ordem do checklist de 1→2 jul):**
1. Resultados trazidos para `out/res_0207/` (res_0207.tar.gz 71M + novelty_0207.tar.gz):
   sessão + evaluation + modelos + logs + `~/swarm-novelty`. **NÃO copiados ainda para
   `results/`** — à espera da decisão dos re-runs (evitar fixar eval com none/u_wall falsos).
2. **Deploy do src/+tests/ (HEAD `6e1d40a`) para o servidor** ✅ — fix nº8 + porta refactorizada
   confirmados (`.meta.json` no evo_trainer, `DOOR_` no env). Backup:
   `~/code_backup_pre_deploy_20260702.tar.gz`.
3. **⭐ CORREÇÃO à leitura de 1 jul: o bypass run 3 FECHOU em 65.0** (o "0" era a gen 56,
   a meio do run) → o modelo em disco resolve o deceptive. **Eval GNN bypass = 100% / 64.5.**
   As únicas vítimas reais da armadilha nº8 são none (eval 60%/0.6 vs R2=39.75 de treino)
   e u_wall (eval 0% vs R2=62.5).
4. **⭐ EVAL DO NOVELTY (20 ep, seed-base 1000, protocolo emparelhado): 81.30 ± 1.89 rec/ep,
   100% sucesso** — vs baseline 64.5 no mesmo protocolo → **+26% para o Novelty**, e muito
   estável (77–84). Corrido isolado em `~/swarm-novelty` (tmux `eval_novelty`); CSV no PC em
   `out/res_0207/swarm-novelty/results/eval_gnn_cooperative_door_bypass_NOVELTY.csv`.
   Caveat honesto: Novelty teve 600 min vs 195/run; o run 1 do baseline (80.5 treino) perdeu-se.
5. Eval completa (`eval_summary.csv`, 21 combos × 20 ep): GNN 100% em bottleneck (88.6),
   four_rooms (40.7), coop_door (67.2), perception (21.1), **bypass (64.5)**; PPO/SAC 100%
   nos 7 (PPO u_wall 65.8 — cura do treino_fds confirmada de novo).

### 🚀 TREINO DE 7 DIAS (utilizador fora 1 semana a partir de ~4 jul) — PREPARAÇÃO FEITA (2 jul)

**Decisão do utilizador:** aproveitar a semana fora para um treino longo; foco = ponto 2
(estatística séria: boxplots de EVAL, Rrobust/Sscale nos modelos novos, significância).

**Pipeline endurecido para correr SEM supervisão (4 correções, código local, por deployar):**
1. `run_experiments.py` — curvas/scores gravados **incrementalmente após cada run**
   (merge por Scenario/Algorithm/**Run**, escrita atómica). Antes: tudo em memória até
   ao fim → crash ao dia N perdia a campanha, e o --resume apagava runs pré-crash do CSV.
   `generate_plots` passou a ler do disco. Testado (4 casos de merge, pandas local).
2. `train_ppo_3d.py`/`train_sac_3d.py` — **armadilha nº8 também nos MLP**: o `_final.zip`
   era sobrescrito pelo último run. Agora guardam também `_run{seed}.zip` por run.
3. **`scripts/eval_by_run.py` (novo)** — avalia TODOS os modelos `_run{n}` com o protocolo
   emparelhado → `results/evaluation/eval_by_run.csv` (long, coluna Run) = boxplots de EVAL
   + input p/ statistical_tests por run. Chamado automaticamente no fim do run_experiments.
   (`eval_all.py` ganhou `model_path=` override para isto.)
4. **`scripts/launch_7d.sh` (novo)** — watchdog: campanha nova limpa o `_sessao_treino.txt`
   e corre `run_experiments --resume` em loop (máx 10 tentativas, sleep 120, pipefail,
   log `treino_7d_<data>.log`). Crash a meio da semana → relança sozinho.

**Composição proposta (por confirmar com o utilizador antes de lançar):**
- GNN 7 runs × 7 cenários × 195 min ≈ 6.6 dias (tmux principal, ~/swarm-robotics-tese);
- PPO/SAC 7 runs × 7 cenários × 48 min ≈ 3.3 dias em PARALELO num dir isolado
  (PPO usa só 8 cores; load total ~46/64) — boxplots N=7 para os 3 algos.
- ⚠️ duas instâncias de run_experiments NÃO podem partilhar o mesmo dir (config
  `foraging.yaml`, logs e `_sessao_treino.txt` são partilhados) → dir isolado obrigatório.

**✅ SMOKE TEST COMPLETO (2 jul, tarde/noite) — pipeline SELADO para o lançamento:**
- 1º smoke (3 algos × 2 runs × 2 min) validou: `_run{n}` nos 3 algos, CSVs incrementais,
  `eval_by_run.csv`, watchdog a relançar com `--resume`.
- 🐛→✅ **Bug real apanhado pelo smoke**: o `render_maps` (PyVista/VTK) ABORTA o processo
  em servidores headless (SIGABRT nativo, try/except não apanha) DEPOIS de todo o trabalho
  útil — o watchdog relançava em loop uma campanha completa (3 relances observados).
  **Fix triplo**: (1) `plot_results` corre o render_maps num SUBPROCESSO isolado;
  (2) `run_experiments` escreve sentinela `results/logs/_campanha_concluida.txt` no fim;
  (3) `launch_7d.sh` decide pela SENTINELA, não pelo exit code.
- 2º smoke (fase final, `SWARM_KEEP_SESSION=1`): **sentinela presente, CONCLUÍDA, 0 mortes** ✅.
- Código corrigido deployado em `~/swarm-robotics-tese` E `~/smoke7d`.

**🚀 LANÇADO (2 jul 18:30 UTC, decisão do utilizador "executa") — A CORRER:**
- tmux **`treino7d_gnn`** (~/swarm-robotics-tese): `launch_7d.sh --algo GNN --runs 7
  --time-gnn 195 --eval-episodes 20` → 7×7×195 min ≈ 159h treino → **fim ~9 jul
  (manhã) + eval/relatório/vídeos ~3h**. Com fix nº8: guarda `_run{1..7}.pth` + campeão.
- tmux **`treino7d_mlp`** (~/run7d_mlp, dir ISOLADO novo: cp de src+scripts+configs,
  venv partilhada): PPO 7 runs (48 min/run) → depois SAC 7 runs → ≈81h → **fim ~6 jul
  (manhã)**. Modelos `_run{n}.zip` por run (fix novo).
- Load ~46/64 (30 GNN + 16 PPO). Arranque confirmado aos 90s (watchdog + PPO a treinar).
- No fim de cada campanha: eval 20 ep + eval_by_run + gráficos + GIFs automáticos;
  sentinela `_campanha_concluida.txt` fecha o watchdog.
- ⚠️ Ao trazer resultados: os models/ e sessões ANTIGOS do servidor foram todos
  arquivados no PC ANTES do lançamento (out/res_0207 + results/ locais, 2 jul).

**⬜ DECISÃO PENDENTE (única coisa em aberto do checklist):** re-correr os campeões perdidos
com o fix nº8 já deployado (seed = nº do run → reproduzíveis): `none` seed 2 (39.75) e
`u_wall` seed 2 (62.5) ≈ 2×195 min ≈ 6.5h; `bypass` seed 1 (80.5) é opcional (já há 64.5
em eval; o Novelty 81.3 cobre a história do deceptive) → +195 min se se quiser.
Depois dos re-runs: re-avaliar, copiar tudo para `results/`, atualizar
`docs/AVANCO_GNN_HOMING.md` + Cap 6, e mergear as branches.

---

## ⏱ ATUALIZAÇÃO 1→2 jul 2026 (noite) — LER PRIMEIRO AO RETOMAR

> Sessão noturna: armadilha nº8 descoberta+corrigida, porta refactorizada (bit-exacta),
> dashboard redesenhado. O train3d fechou o TREINO; a avaliação automática ficou a
> decorrer durante a noite (às 21:53 ia em 5/21 combinações, fim estimado ~00h20).

**✅ AO RETOMAR (checklist, por ordem):**
1. `plink ... "tmux ls; ls -lt ~/swarm-robotics-tese/results/graficos_tese/ | head -4"`
   → deve existir a sessão nova (timestamp de ~02-07). Se a eval ainda correr, esperar.
2. Trazer por pscp: sessão nova + `results/evaluation` + `results/models` + logs
   **+ `~/swarm-novelty/`** (modelo Novelty 83.5 + log + CSV).
3. ⚠️ O eval automático mede SÓ os modelos do run 3 (armadilha nº8, abaixo) — u_wall,
   none e bypass vão aparecer maus SEM ser verdade. Interpretar com a tabela de treino
   da secção de 1 jul.
4. Deploy do código corrigido para o servidor (pscp `src/` — leva o fix do save
   `d9a2c45` E o refactor da porta `d6d94b4`, bit-exacto) ANTES de qualquer retreino.
5. **Decisão pendente:** re-correr os runs bons perdidos para recuperar os campeões
   (seed = nº do run → reproduzíveis): `none` seed 2 (39.8), `u_wall` seed 2 (62.5),
   `bypass` seed 1 (80.5) ≈ 3×195 min ≈ 10h de servidor. Com o fix, cada run passa a
   guardar `_run{n}.pth` e o campeão só é substituído por melhor.
6. Avaliar o modelo **Novelty** no bypass com o MESMO protocolo (eval 20 ep) → única
   comparação justa Novelty vs baseline.

**🐛→✅ ARMADILHA nº8 (descoberta 1 jul, corrigida em `d9a2c45`):** o `evo_trainer_3d.py`
gravava `gnn_3d_best{suf}.pth` incondicionalmente → com `--runs 3`, o run 3 sobrescrevia
sempre os campeões dos runs 1-2. Descoberto porque o eval do train3d deu none 60%/0.6 e
u_wall 0% — números que batem certo com os runs 3 (1.0 e 0.0), não com os melhores.
Perdidos: u_wall 62.5, none 39.8, **bypass 80.5**; o Novelty (83.5) SOBREVIVE (dir isolado).
Fix: `_run{seed}.pth` por run + campeão só substituído se fitness ≥ sidecar `.meta.json`
(seed=1 recomeça campanha). NOTA: evals de TODAS as campanhas multi-run antigas (Fase B,
treino_fds, GNN-48h) mediam o último run → GNN possivelmente subestimado no histórico.

**✅ Refactor da porta cooperativa (`d6d94b4`)** — pedido do utilizador ("estava martelada"):
fim do teleporte da parede para (999,999,999) (abrir agora REMOVE o painel), constantes
`DOOR_*` únicas, `_add_cooperative_door()`/`_update_door()`, `has_door` em vez de tuplos
repetidos, band-aid do geodésico removido. **Bit-exacto** (A/B 12 rollouts, max|Δ|=0.0,
incluindo o passo da abertura) + `tests/test_door.py` novo (5 casos). Não afeta treinos.

**✅ Dashboard "Swarm Observatory" (`0844553`)** — redesign completo P&B noturno
(decisão do utilizador: "preto e branco modo noturno"): `dashboard/theme.py` (fonte única
de estilo), vista **Overview** nova (hero com boids em canvas, KPIs count-up, cartões de
estado, timeline do projeto), casca nova. Utilizador aprovou ("ficou muito bom").

**ℹ️ Curvas do GNN (pergunta do utilizador):** 3 padrões de sobe-e-desce — (1) dente-de-serra
grande = arranque de run novo (CSV concatena runs; normal); (2) oscilações pequenas do
"melhor" só com Novelty ativo = melhor-por-objetivo pode sair da elite (esperado; com o
fix nº8 o .pth guarda sempre o pico); (3) quedas grandes a MEIO de um run = bug antigo de
seed-overfitting, curado a 14 jun — se reaparecer em treino novo, é anomalia.

---

## ⏱ ATUALIZAÇÃO 1 jul 2026 (train3d TERMINOU o treino: GNN come nos 7/7 cenários; Novelty comeu no bypass MAS o baseline também)

> Verificação noturna dos 2 treinos do servidor. Memórias: `memory/novelty_search_bypass.md`
> (atualizada com o veredicto), `memory/gnn_homing_fitness.md`.

**1) Novelty Search TERMINOU e COMEU no bypass.** 747 gerações em 10h (fim 30 jun 19:43 UTC);
**Comida (melhor) = 83.5** rec/ep no `cooperative_door_bypass`, fitness ~837k, homing ~0.42.
Modelo em `~/swarm-novelty/results/models/gnn_3d_best_cooperative_door_bypass.pth` (AINDA no servidor).

**2) ⚠️ REVIRAVOLTA: o baseline (objetivo puro) TAMBÉM comeu no bypass** — run 1 = **80.5**,
run 2 = **56.75** (run 3 falhou, 0). A premissa "o objetivo puro não escapa ao deceptive" vinha da
validação de **35 min**; com **195 min** a fitness de homing resolve sozinha. Consequências:
- O ganho do Novelty (83.5 vs 80.5) é **marginal** e a comparação **não é direta** (Novelty teve
  600 min + env vetorizado → 747 gens vs ~153/run do baseline).
- **Narrativa para a tese**: a CURA principal é a **fitness de homing**; o Novelty entra como
  experiência complementar/robustez, não como o desbloqueio. Decidir com números de EVAL, não de treino.

**3) train3d: treino CONCLUÍDO (21 runs), avaliação automática A CORRER** (verificado 21:13 do
servidor: gráficos/CSVs gerados, eval de 20 ep em curso; sessão final em `graficos_tese/` ainda
por criar). Melhor comida por run (números de TREINO — máx do log, 3 runs por cenário, na ordem):
| Cenário | R1 | R2 | R3 | Histórico (todos os treinos anteriores) |
|---|---|---|---|---|
| none | 37.8 | 39.8 | 1.0 ⚠️ | comia |
| u_wall | 46.8 | 62.5 | 0.0 ⚠️ | 0 |
| **bottleneck** | **132.3** | **131.0** | **88.3** | **0 (nem na validação de 28 jun)** |
| four_rooms | 59.3 | 42.8 | 44.8 | 0 |
| cooperative_door | 59.3 | 59.5 | 67.5 | 0 |
| cooperative_perception | 23.3 | 23.5 | 24.8 | comia |
| bypass (deceptive) | 80.5 | 56.8 | 0 | 0 |
- **A fitness de homing curou o GNN em TODOS os labirintos** (7/7 cenários com comida; o bottleneck,
  que era 0 até na validação, passou a melhor resultado). Só precisava de tempo (343 gens vs ~30).
- Variância entre runs mantém-se (2 runs falhados) = assinatura do método, boa para os boxplots.
- ⚠️ **Armadilha nº 3**: números acima são de treino; o veredicto oficial é o `eval_summary.csv`
  desta sessão (20 ep). NÃO concluir nada no Cap 6 sem ele.

**PRÓXIMOS PASSOS (quando a eval fechar, esta noite):**
1. Trazer por pscp: sessão `graficos_tese/<01-07-...>` + `results/evaluation` + modelos + logs
   **+ o modelo/log do Novelty** (`~/swarm-novelty/`).
2. Re-avaliar localmente (eval_suite 30 ep) + `statistical_tests.py`; avaliar também o modelo
   Novelty no bypass com o MESMO protocolo → comparação justa Novelty vs baseline.
3. Com números de eval: atualizar `docs/AVANCO_GNN_HOMING.md` + reescrever Cap 6 (narrativa
   "diagnóstico + cura", decisão de 29 jun; agora com a cura confirmada nos 7 cenários).
4. Mergear `test/lidar-vetorizado` + `feat/novelty-search` em `tese-final-graficos` (validadas).

---

## ⏱ ATUALIZAÇÃO 30 jun 2026 (obs vetorizadas + Novelty Search lançado para o bypass)

> Sessão dedicada a **melhores resultados** (pedido do utilizador), foco no **GNN** (PPO/SAC já
> a 100% nos 7 cenários). Memórias: `memory/obs_vetorizadas.md`, `memory/novelty_search_bypass.md`.

**1) Diagnóstico de recursos do servidor (.14).** Único utilizador. 64 vCPU (2× Xeon 4216),
**125 GiB RAM**, sem GPU. Com o `train3d` (30 workers) o load é ~25 → o constrangimento é **só CPU**;
RAM (122 GiB livres) e disco (79 GB) não limitam. Há folga para +1 treino em paralelo.

**2) Quick win nº2 — observações vetorizadas (✅ integrado, bit-exacto).** Profiling mostrou que,
depois do LiDAR, o gargalo passou a ser `_get_observations` (**78% do step()**): loop O(N²) Python
de vizinhos com `norm`/`cross`/`dot` por par. Vetorizado (bases F/R/U em batch + projeções via
`einsum`/broadcasting). **`0.00e+00` em 42000 cenas-agente** (7 cenários); `_get_observations`
2.55→0.42 ms (6.1×); **step() inteiro 3.48→~1.35 ms (2.58×)**. Soma com o LiDAR. Teste de regressão
`tests/test_obs_equivalence.py`. Commit `71006f8` na branch `test/lidar-vetorizado` (NÃO pushed).
Bit-exacto ⇒ não invalida modelos nem a tese; só acelera (mais gerações/treino = melhor evolução).

**3) Novelty Search para o `bypass` deceptive (✅ implementado + treino A CORRER).** O GNN come em
3/5 labirintos (homing), mas o `cooperative_door_bypass` fica a 0 porque é um ótimo **deceptive**
(o gradiente de homing aponta para o beco). Implementado **Novelty Search** (Lehman & Stanley 2011)
em `evo_trainer_3d.py`, **config-driven** (`novelty_weight=0` → idêntico ao histórico):
- BC = centroide final (x,y) do swarm; novelty = dist. média aos k-NN (população ∪ arquivo FIFO);
  seleção = blend min-max `(1-w)·obj + w·novelty`. **Save/log seguem sempre o OBJETIVO** (food).
- `--config` novo no `__main__` → treino isolado sem mexer no `foraging.yaml` partilhado.
- Commit `761f216` na branch **`feat/novelty-search`**. Smoke local + no servidor OK.
- **Treino LANÇADO** (30 jun 09:42 UTC, decisão: paralelo moderado): tmux **`novelty_bypass`**,
  ISOLADO em `~/swarm-novelty/` (risco ZERO p/ o train3d), pop 24, novelty_weight 0.5, seed 42,
  10h. Sinal de sucesso = **`Comida (melhor) > 0`** no log. Monitorização automática de 3/3h
  (trigger `trig_011R2tP3nFEkhXPwS4jUYKYx`, push+email) — avisa quando comer.

**4) `train3d` (baseline, objetivo puro) — continua A CORRER**, saudável, ~32h de ~68h (30 jun).
Não foi tocado. Conclusão estimada **~1 jul**. É a baseline contra a qual se compara o Novelty.

**Próximos passos:** se o Novelty fizer o GNN comer no bypass → resultado FORTE p/ a tese (GNN
resolve o deceptive); atualizar `docs/AVANCO_GNN_HOMING.md` e o Cap 6. Mergear as branches de perf
(`test/lidar-vetorizado`) e `feat/novelty-search` em `tese-final-graficos` quando validadas.

---

## ⏱ ATUALIZAÇÃO 29 jun 2026 (treino 3 dias a meio + revisão da reescrita da tese + LiDAR vetorizado integrado)

**1) Treino de 3 dias (`train3d`, só GNN) — A CORRER, saudável.** Verificado 29 jun 16:48 UTC:
tmux `train3d` vivo, ~16h20 de ~68h, load 25, **a comer 62.5 recolhas/ep** no ~5º cenário
(cooperative_door). Conclusão estimada **~1 jul** (tarde). CSV `results/logs/gnn_3d_training.csv`
é a fonte fiável ao vivo (o `.log` via `tee` está block-buffered). Loop de verificação horária
ativo nesta sessão (plink+VPN). Validação prévia: GNN come em **3/5 labirintos** (u_wall 7.25,
four_rooms 13.75, cooperative_door 12.25); **bottleneck** homing 0.86 (pode fechar com 195min);
**bypass** o caso difícil (pode resistir — resultado honesto). Ver `memory/gnn_homing_fitness.md`.

**2) Revisão do plano de reescrita da tese — são DUAS atualizações, não uma.** Ao rever
`docs/AVANCO_GNN_HOMING.md §3` descobri que a tese tem **duas** narrativas desatualizadas que
interagem (o plano antigo só via a do GNN):
- **GNN colapsa** nos labirintos (tanh saturada) → curado pelo **homing**.
- **PPO reward hacking no Muro U** (7 sítios: §437,1110,1112,1185,1255,1401,1453) → **curado pelo
  treino_fds** (recompensa simplificada): PPO u_wall **0→100%**. Nenhum número novo está na tese
  ainda (73,3/67,7/0,77 são de campanha ANTERIOR ao treino_fds).
- Também desfasado: §976 exploração 2.0→**0.5**, §977 dispersão −1.5→**0** (desligada), food
  100→**300**, required_to_eat=1 nos labirintos de navegação.
- **DECISÃO (utilizador, 29 jun): narrativa "diagnóstico + CURA"** — contar as 2 patologias como
  diagnosticadas+corrigidas (contributo metodológico), não esconder os resultados antigos. O
  *trade-off* central (gradiente=tarefa, grafo=escala Zero-Shot) SOBREVIVE mas atenua (PPO≈SAC).
  Plano detalhado e sítios com nº de linha em `docs/AVANCO_GNN_HOMING.md §3` (reescrito 29 jun).
  **NÃO editar `main.tex` até os resultados finais (train3d) existirem.**

**3) Pesquisa de otimizações + LiDAR vetorizado INTEGRADO (✅ feito hoje).** Pesquisei a
literatura recente (ver fontes na conversa); quick win nº1 = **vetorizar o LiDAR** (maior
multiplicador de throughput, e bit-exacto ⇒ não invalida modelos nem a tese).
- ✅ **Integrado** em `swarm_env_3d.py`: novo método `_lidar_scan` (slab method NumPy) substitui
  o triplo loop Python; cantos das AABB pré-computados 1×/step. **Bit-exacto** vs. o loop
  (`0.00e+00`, 0/8000 cenas) e **~19.5× mais rápido** na parte do LiDAR.
- ✅ **Teste de regressão** `tests/test_lidar_equivalence.py` (8000 cenas, casos-limite) — rede de
  segurança permanente. Smoke test 4/4 e equivalência no env real (7 cenários × 20 agentes) = `0.00e+00`.
- ⚠️ NÃO afeta o `train3d` (servidor, código antigo). Qualquer treino futuro fica idêntico, só + rápido.
- 🔜 Otimizações pesquisadas ainda por fazer (próxima iteração): RecurrentPPO (memória/POMDP),
  Novelty/Quality-Diversity no evolutivo (para o bypass deceptive), 8→16 raios LiDAR,
  vetorizar LiDAR também sobre os 20 agentes. Ver `memory/lidar_vetorizado.md`.

---

## ⏱ ATUALIZAÇÃO 28 jun 2026 (noite) — (GNN come em labirintos: fitness de HOMING + treino 3 dias a correr)

**AVANÇO PRINCIPAL — o GNN passou a comer em labirintos pela 1ª vez.** Resolvido o colapso
crónico do GNN nos labirintos (0% em todos os treinos anteriores). Ver `memory/gnn_homing_fitness.md`.

- 🔬 **Diagnóstico (causa raiz):** a fitness `food*10000 + 5000·tanh(reward/5000)` levava a
  **farming de shaping** — nos labirintos (food=0 p/ todos), o GNN maximizava o reward de exploração
  vagueando SEM entrar no ninho (entrar dá signaling=1, 0 reward/passo → parar é "perda"). Como
  nenhum genoma comia, o termo `food*10000` nunca ativava → seleção cega. Não era falta de tempo
  (123 gen e na mesma 0) nem arquitetura — era a **fitness (seleção)**.
- ✅ **Correção (commits `03e87bd` + `922f143`):** fitness de **HOMING** =
  `avg_food*10000 + 5000·avg_homing`, onde homing = proximidade FINAL ao ninho
  (`frac = clip((Φ_ini − Φ_fim)/Φ_ini, 0, 1)`, Φ = potencial geodésico). **Não-farmável** (só conta
  os extremos, vaguear não aumenta) e seleciona a PRÉ-CONDIÇÃO de comer. Também: `sigma_min 0.01→0.03`,
  `sigma_decay 0.995→0.999`. Só mexe no GNN — PPO/SAC intactos.
- ✅ **Validado no `u_wall`** (servidor, 35 min, seed 42): gen 13 = 1ª recolha, gen 22 = **7.25 rec/ep**.
  Antes: **0** em todos os treinos (10jun/FaseB/treino_fds).
- 🔄 **A CORRER AGORA (28 jun 22:09, `.14`):** servidor estava livre; código sincronizado por pscp
  (= HEAD `922f143`). Dois tmux encadeados:
  - `val_gnn` — valida a fitness de homing nos restantes labirintos (`bottleneck → four_rooms →
    cooperative_door → cooperative_door_bypass`, 35 min cada, seed 42). Script `val_gnn_labirintos.sh`.
  - `val_watch` — `watch_and_train.sh`: espera o `val_gnn` acabar, analisa `max(best_task_food)` por
    cenário → `val_verdict.txt`, e **se ≥1 labirinto comeu LANÇA AUTOMATICAMENTE** o treino de 3 dias.
  - **Treino 3 dias (só GNN):** `run_experiments --algo GNN --runs 3 --time-gnn 195 --scenarios
    none,u_wall,bottleneck,four_rooms,cooperative_door,cooperative_perception,cooperative_door_bypass
    --eval-episodes 20` → tmux `train3d`, log `treino_3dias_gnn.log` (~68h + eval/gráficos).
- 📋 **AO RETOMAR:** `plink ... "cat val_verdict.txt; tmux ls; tail results/logs/gnn_3d_training.csv"`
  (fitness > 5000 com homing ⇒ já há comida). No fim, trazer `results/` por pscp e re-correr eval +
  `statistical_tests` + atualizar Cap 6 (só os números do GNN mudam; PPO/SAC mantêm o treino_fds).
- ⚠️ Pendente de antes: auditoria entrada-a-entrada do `references.bib` (~16 entradas suspeitas).

---

## ⏱ ATUALIZAÇÃO 24 jun 2026 (GNN-48h terminou + fix do dashboard)

**Treino GNN-48h CONCLUÍDO** (sessão `23-06-2026_19h39m`, recolhido para `out/res_servidor/`
e copiado para `results/graficos_tese/` + `results/evaluation/`). `eval_summary.csv` de 23 jun
20:39 (posterior ao fim do treino → corresponde aos modelos, sem a armadilha nº 3). Confirmado
no servidor: sem tmux, sem processos. `_sessao_treino.txt` = GNN × 6 cenários × 3 runs.

- 📊 **Resultado MISTO — labirintos só recuperaram em parte.** Sucesso% / recolhas/ep (eval):
  | Cenário | GNN | PPO | SAC |
  |---|---|---|---|
  | none | 100% / 35.5 | 100% / 71.7 | 100% / 21.0 |
  | **u_wall (Muro U)** | **100% / 13.4** ✅ | 0% / 0 | 0% / 0 |
  | bottleneck | **0% / 0** ❌ | 100% / 41.4 | 100% / 36.5 |
  | four_rooms | **0% / 0** ❌ | 100% / 10.9 | 55% / 0.9 |
  | cooperative_door | **0% / 0** ❌ | 100% / 66.6 | 100% / 62.3 |
  | cooperative_perception | 100% / 16.7 ✅ | 100% / 17.8 | 100% / 9.5 |
  - ✅ **Muro U recuperado** e é vitória EXCLUSIVA do GNN (PPO/SAC a 0% — reward hacking do PPO).
  - ❌ **bottleneck, four_rooms, cooperative_door ficaram a 0%** — NÃO recuperaram (o 24h v2 fazia
    Muro U *e* Porta Coop a 100%; este não). 
  - ⚠️ *Fitness exploitation* persiste: `cooperative_door` run 1 teve fitness de treino **527 500**
    (~52 food) mas **0 recolhas na avaliação**; runs 2/3 em `5000.0` exato (0 food).
  - **DECISÃO PENDENTE:** fixar este como GNN de referência (ganha-se o Muro U) ou 3ª tentativa nos
    3 labirintos que falharam. Os boxplots de variância (3 runs) já existem nesta sessão.

- 🛠 **Fix do dashboard (botão "Trazer resultados"):** `remote.fetch_results` só descarregava o
  tarball para `out/` — não o desempacotava → a sessão **nunca aparecia** na vista Resultados
  (que lê de `results/graficos_tese/`). Agora `fetch_results` **desempacota automaticamente na
  raiz do projeto** (novo `_extract_into_project()`, extrai só caminhos relativos seguros) → a
  sessão e o eval caem logo no sítio certo. Validado: `list_sessions()` passou a ver `23-06-...`.
- 🛠 **`.venv` local recriado** (Python 3.13) **só com o dashboard**: `nicegui`/`plotly`/`pandas`
  (versões do `requirements.txt`). Chega para Resultados/Ciência/Monitorizar; treinar/avaliar
  localmente exige o `requirements.txt` completo (torch etc.) — ainda não instalado.

- 🔄 **A CORRER AGORA: treino "fim-de-semana" com a RECOMPENSA SIMPLIFICADA** (`tmux treino_fds`,
  `.14`, lançado **24 jun 09:01 UTC**). **ARMADILHA EVITADA:** o servidor tinha a recompensa
  ANTIGA (food 100, exploração 2.0, penalizações on) e código de 14 jun (6 cenários) — o GNN-48h
  acima foi treinado com ESSA recompensa antiga. Antes de lançar, **deployei o código+config
  simplificados** (local→servidor: `src/`+`scripts/`+`configs/`; backup em
  `~/code_backup_pre_fds_20260624_0859.tar.gz`). Servidor confirmado: food **300**, exploração
  **0.5**, penalizações **0.0**, **7 cenários**. Plano:
  `run_experiments.py --runs 3 --time 48 --time-gnn 160 --time-ppo 48 --eval-episodes 20`
  → **7 cenários × 3 algos × 3 runs**, GNN **160 min/run** (≈3,3× PPO/SAC=48 min) = foco no GNN +
  labirintos. ~90h treino + eval/gráficos → **fim ~domingo 28 de manhã**. Avaliação dos 7 cenários
  e relatório completo correm automaticamente no fim. Monitorizar pela vista Servidor do dashboard
  (deteta `treino_fds.log` e a sessão tmux). Receita de arranque: `out/launch_fds.sh` (local).

- 🐛→✅ **BUG CRÍTICO encontrado e corrigido no `evo_trainer_3d.py`** (24 jun, ~11h): o 1º
  arranque do treino crashava na **geração 1** com `OSError: [Errno 24] Too many open files`.
  Causa: `pool.map` enviava os genomas como **`state_dict` de tensores torch**; o pickle de
  tensores usa memória partilhada/**file descriptors por tensor** (pop=30 × ~15 tensores = 450+
  FDs/geração) → estourava o `ulimit` (1024). Subir o `ulimit` **não** chegou: mesmo sem crashar,
  o `resource_sharer` engasgava e o `Pool` deixava de paralelizar (1 geração passou de ~60s para
  **>9 min**, load 0.00). **Fix definitivo:** converter o genoma para **arrays numpy** antes do
  `pool.map` (pickle por valor, sem FDs) e reconstruir o tensor dentro de `evaluate_genome`.
  Validado: gerações a **~145s** (ritmo normal, = ao treino antigo), load ~25, 0 erros. O treino
  foi **relançado limpo às 11:32 UTC**. Nota: este bug existia no código LOCAL (o GNN-48h correu
  no código antigo do servidor, de 14 jun, que não tinha o problema). `ulimit -n 65535` ficou no
  `launch_fds.sh` por segurança.

---

## ⏱ ATUALIZAÇÃO 22 jun 2026 (saúde do código + vídeos 3D)

Sessão de **otimização/regularização** (não toca em treino/recompensa → não invalida resultados):

- ✅ **`main` sincronizada** com `tese-final-graficos` (estava **13 commits atrás**; fast-forward
  `58ad5bd→13e9c7c`, local+remoto). Branches de backup mantidas. Trabalhar na `tese-final-graficos`.
- ✅ **Fonte única de cenários** — novo `src/scenarios.py` (`SCENARIOS`, `MAZE_SCENARIOS`, labels
  longo/curto, `ALGO_LABELS/COLORS`, `scenario_suffix`). 9 ficheiros ligados (heatmaps, render_maps,
  eval_suite, eval_all, run_eval, plot_robustez, statistical_tests, run_experiments, record_3d).
  **Corrigiu BUG real:** as listas estavam duplicadas com **6 vs 7 cenários** → o 7º
  (`cooperative_door_bypass`) era **treinado mas NUNCA avaliado** (nem heatmaps/robustez). Agora os
  7 entram em todo o lado **automaticamente** → ao re-treinar/re-avaliar, o bypass já é coberto.
  −34 linhas líquidas; 4/4 smoke tests; `plot_robustez` corre limpo. **Importar SEMPRE de `src.scenarios`.**
- ✅ **Vídeos 3D dos episódios** — novo `scripts/record_3d.py` (PyVista offscreen→MP4, z REAL dos
  robôs; o treino é mesmo 3D, z varia ~[-7,+1] m). Guarda em `<pasta-do-treino>/videos/`. No pipeline
  do `plot_results` **atrás de `SWARM_VIDEOS=1`** (gravar 21 vídeos demora minutos); à parte:
  `python scripts/record_3d.py --all`. Decidido PyVista (não Ursina — já é o motor da tese).
- 🔜 **Adiado (otimização futura):** `load_model` único nos 4 visualizadores; **vetorizar a
  avaliação** (batch predict — `eval_suite` ~30 min é lento). Fazer quando se re-avaliar o GNN-48h.

---

## ⏱ ATUALIZAÇÃO 21 jun 2026 (o snapshot de 10 jun abaixo está ultrapassado)

**Feito desde 10 jun:**
- ✅ **Dashboard reformulado COMPLETO** (secção 6 / Fase F1–F3): pacote `dashboard/` em **NiceGUI**
  (browser) com as 4 vistas — Treinar, Monitorizar/Servidor ISCTE, Ciência, Resultados — + curvas
  de aprendizagem ao vivo (Plotly) + **comparação de treinos A/B** (números e imagens), no browser
  **e** no launcher desktop. Falta só **F4 (modo Demo)** para a defesa.
- ✅ **Cap 6 e Cap 7 redigidos** (análise das figuras, tabela de significância colada, discussão
  global, limitações, trabalhos futuros). Tese compila limpa, **87 págs**.
- ✅ **Mecanismo do colapso do GNN escrito** na Discussão (Cap 6): neuroevolução cega + recompensa
  esparsa → planalto de *fitness*; variância entre *runs* como assinatura do método.
- ✅ **Bibliografia auditada e corrigida** (21 jun, commit `f825cab`): removidas **2 refs
  FABRICADAS** (`iskandar2024comparative`, `wang2022comparative`) + **12 órfãs**; metadados de
  `majid2023deep`/`lin2025survey` corrigidos; substitutos reais verificados na web. **0 refs indefinidas**.
- ✅ **Fitness GNN `tanh` + `eval_episodes=4` + seeds fixas** validados em produção.

**A história do GNN (importante):**
- **24h v2** (16 jun, 1 run, com `tanh`): GNN melhorou muito nos labirintos (Muro U 100%, Porta Coop 100%).
- **Fase B** (18 jun, **3 runs**): deu os boxplots de variância MAS o GNN **REGREDIU** nos labirintos
  (todos 0%) por tempo/run curto (55 min). Confirmado visualmente (Muro U: **41→0 recolhas**).
  Ver `memory/faseb_vs_anteriores.md`. **O 24h v2 foi o melhor GNN** nos labirintos.
- 🔄 **A CORRER AGORA: re-treino GNN-48h** (`tmux treino_gnn48`, `.14`, lançado 21 jun 17:22):
  **só GNN**, 3 runs × **160 min/run** (~3× o 24h v2) para recuperar os labirintos. **Fim ~23 jun**.
  (PPO/SAC não são tocados — `--algo GNN`.)

**PRÓXIMOS PASSOS (por ordem):**
1. ~~**[~23 jun]** Treino GNN-48h termina → trazer + re-avaliar + ver se os labirintos voltaram.~~
   ✅ **FEITO (24 jun)** — ver atualização no topo. Labirintos só recuperaram em parte (Muro U sim;
   bottleneck/four_rooms/cooperative_door a 0%). **Decisão pendente:** fixar como referência ou 3ª tentativa.
2. **Definir a "Fase B oficial"**: os 3 runs chegam para os boxplots de variância, ou é mesmo
   preciso os **30 runs** da proposta? (decisão de âmbito — 30×6×3×tempo é muito servidor.)
3. **Decisão pendente:** *reward hacking* do PPO no Muro U — aceitar como resultado científico ou ajustar.
4. **Treinar + avaliar o 7º cenário** (`cooperative_door_bypass`) — implementado, falta correr.
   (A lacuna da AVALIAÇÃO já foi corrigida a 22 jun: o pipeline já o avalia automaticamente.)
5. **Revisão completa da tese** ponta a ponta (consistência texto-número-figura) + confirmar a lista
   de autores de 3 refs ainda com "and others" (`heimann2024runtime`, `schmickl2025gnn`, `he2024self`).
6. **Fase D — ARTIGO 6–8 págs** (crítico p/ nota >17) — **ainda por começar**.
7. **Fase E** — modo Demo do dashboard (F4) + preparação da defesa.

---

## 1. Onde estamos (10 jun 2026)

### Feito ✅
- Simulador 3D completo (foraging, 6 cenários, física, LiDAR, geodésico no reward)
- 3 algoritmos: GNN evolutiva (atenção sobre vizinhos), PPO e SAC (SB3, MLP + parameter sharing)
- Pipeline de avaliação reprodutível: `eval_suite.py` (determinístico, seeds emparelhadas),
  `statistical_tests.py` (Wilcoxon/Welch/Cliff), `eval_scalability.py` (Sscale),
  `run_eval.py --fail-frac` (Rrobust), `plot_robustez.py`, `heatmaps.py`, `render_maps.py`
- Treino de 24h no servidor ISCTE concluído e **re-avaliado localmente (30 ep)**:
  - **SAC**: 100% sucesso nos 6 cenários (único)
  - **PPO**: 100% em 5/6; **falha o Muro U a 0%** com reward ~132k = *reward hacking* (exploração)
  - **GNN**: 0% nos 3 labirintos; *fitness exploitation* comprovado (score 75k vs 2.6 recolhas)
  - **Rrobust**: retenção 94–99% (PPO/SAC) com 10% de falhas; **Sscale**: só a GNN escala
    (15%→100% sucesso de N=10→100), PPO/SAC incompatíveis com N≠20
- Tese (`Tese/main.tex`): 77 págs, compila limpa; Caps 1–5 escritos; Cap 6 estruturado com
  28 figuras automáticas (`\figresultado`) **todas preenchidas**; tabela de significância gerada
- Acknowledgement FCT/ISTAR adicionado (exigência do orientador, e-mail jun 2026)

### Em curso 🔄
- **Treino de 48h CONCLUÍDO** (terminou 11 jun 21h15; pasta `graficos_tese/11-06-2026_21h15m`).
  **Recolhido para o PC em 14 jun** (`out/res48h/`). Resultado-chave da comparação 48h vs 24h:
  o treino mais longo **não melhorou** PPO/SAC (já tinham convergido às ~24h); PPO continua a
  falhar o Muro U a 0% (*reward hacking*, reward ~96k); SAC com queda no Four Rooms (variância
  de 1 run); **GNN com *fitness exploitation* flagrante** — Perceção Coop. fitness 9.7k–18.9k
  mas 0.15 recolhas/ep. Os números do 24h e 48h são ambos provisórios (1 run) → falta a Fase B.

### Estado face ao e-mail do orientador (jun 2026)
| Expectativa do prof. | Estado |
|---|---|
| Introdução, Estado da Arte, Contexto escritos | ✅ Feito (Cap 1–3, SLR PRISMA) |
| Metodologia e Experiências adiantados | ✅ Feito (Cap 4–5 alinhados com o código) |
| Experiências em curso | ✅ Treino 48h a correr |
| Resultados e Conclusões em falta | 🔄 Esperado nesta fase — estrutura pronta |
| Artigo 6–8 págs (necessário p/ nota >17) | ❌ Por começar — ver Fase D |

**Veredicto: estás DENTRO do calendário** — à frente na infraestrutura experimental,
no ponto certo da escrita. O que falta é exatamente o que o prof. diz que deve faltar.

---

## 2. Fases até Outubro

### Fase A — Junho: fechar a base experimental
- [x] Recolher resultados do **treino de 48h** (14 jun → `out/res48h/`; tutorial na secção 4.4)
- [ ] Re-correr o pipeline completo sobre os modelos de 48h:
      `eval_suite.py --episodes 30` → `statistical_tests.py` → `plot_robustez.py` →
      `eval_scalability.py` → copiar PNGs p/ `Tese/images/resultados/` → recompilar
- [x] **Investigar números redondos da GNN** — RESOLVIDO (14 jun, ver `memory/gnn_evo_diagnostico.md`):
      `fitness = avg_food*10000 + clip(avg_reward, ±5000)`; o `5000.0` exato = 0 recolhas + shaping
      saturado no teto do clip. Não é bug. Elitismo (6/30) já existe; fitness já dominada pela tarefa.
- [x] **Corrigir variância do GNN antes da Fase B** (14 jun) — `eval_episodes` 1→4 (`foraging.yaml`)
      + seeds de avaliação FIXAS (`evo_trainer_3d.py`: `eval_seed_base`, era `seed+gen`). VALIDADO em
      smoke (cenário none, seed 42): best_fitness monótono não-decrescente, 0 quedas (elites mantêm o
      valor exato); antes saltava ±10-20k. SÓ depois disto correr os 30 runs.
- [x] **7º cenário sugerido pelo Prof. Nunes IMPLEMENTADO** (15 jun, branch
      `feature/cenario-porta-alternativa`) — `cooperative_door_bypass`: porta cooperativa
      (caminho curto, 3 robôs) + percurso ALTERNATIVO longo sem porta. Porta validada (abre só
      com ≥3 agentes); bypass navegável e 1.7× mais longo (geodésico 33m vs 20m) → cooperar
      dá melhor score. Registado em todos os scripts (treino/eval/labels/visualizadores).
      Teste: `scripts/test_cenario_bypass.py` (4/4 verde). **Falta:** treinar+avaliar este cenário.
- [ ] Decidir o que fazer ao *reward hacking* do PPO no Muro U (aceitar como resultado
      científico válido — é uma resposta à pergunta de investigação — ou ajustar `exploration_bonus`)
- [ ] **Reformular o launcher** (DECISÃO 10 jun: arranca DEPOIS de recolhidos/avaliados os
      resultados do treino de 48h — proposta completa na secção 6; começar pela F1)

### Fase B — Julho: protocolo estatístico definitivo
- [ ] **30 runs por cenário/algoritmo** nos servidores ISCTE (exigência da proposta de tese;
      hoje só há 1 run → boxplots degenerados, NÃO usáveis)
- [ ] Repetir Rrobust e Sscale sobre os modelos finais
- [ ] Gerar gráficos finais (boxplots reais, comparações, heatmaps) e fixar a sessão
      "oficial" dos resultados da tese
- [ ] Dashboard melhorado/dinâmico (objetivo do Gonçalo) — útil p/ demo na defesa
      → **proposta completa na secção 6 deste documento**

### Fase C — Julho/Agosto: escrever Resultados e Conclusões
- [ ] Cap 6: texto de análise sobre as figuras (narrativa já validada:
      SAC robusto em navegação / PPO eficiente mas vulnerável a reward hacking /
      GNN perde em Ptask mas é a única escalável — trade-off central)
- [ ] Incluir a tabela `results/estatisticas/testes_significancia_food_collected.tex`
- [ ] Cap 7 Conclusões + Limitações + Trabalho Futuro
- [ ] TODOs antigos: coerência do título da capa (PT vs EN), Deployment Gap, apêndices,
      auditar qualidade do `.bib` (entradas duvidosas: "ResearchGate Publication", PMC, etc.)
- [ ] Rever a tese completa de uma ponta à outra (consistência número-texto-figura)

### Fase D — Agosto/Setembro: o ARTIGO (chave para >17)
- [ ] 6–8 páginas, formato conferência IEEE 2 colunas — **modelo: o artigo do IWSSIP
      "Occlusion-Aware Pedestrian Detection" (alunos ISCTE + Prof. Nunes), na pasta
      `C:\Users\gonca\Desktop\artigos prof\`**
- [ ] Estrutura destilada da dissertação: Intro → Related Work (resumo da SLR) →
      Método (simulador + 3 algos) → Resultados (Ptask/Rrobust/Sscale + significância) →
      Conclusões. A dissertação é citada para detalhes.
- [ ] Incluir o acknowledgement FCT/ISTAR (mesmo texto da tese)
- [ ] Discutir com o orientador o alvo (conferência vs. submissão interna ISCTE)

### Fase E — Setembro/Outubro: polimento e entrega
- [ ] Ciclos de revisão com o orientador (enviar draft cedo — early & often)
- [ ] Verificação final: refs, acrónimos, listas de figuras/tabelas, normas ISCTE da capa
- [ ] Preparar a defesa: slides + demo do dashboard/visualizador
- [ ] Buffer para imprevistos (≥2 semanas)

---

## 3. Avisos e armadilhas conhecidas (não repetir erros)

1. **`analise_treino_24h.md`** (na pasta da sessão 09-06) tem conclusões ERRADAS
   ("PPO 100% em tudo") — não usar. A fonte de verdade é `results/evaluation/eval_summary.csv`.
2. **Boxplots da sessão 09-06 são degenerados** (1 run; caption "5 runs" é falso) — excluir
   até haver 30 runs.
3. **CSV de avaliação tem de ser da MESMA data dos modelos** — já fomos enganados por
   evals desatualizados duas vezes. Ao re-treinar: re-avaliar SEMPRE antes de concluir.
4. `success = food>0` (métrica fraca; reportar sempre também recolhas/ep).
5. `comparacao_barras_geral` mistura escalas fitness/reward — usar só como demonstração
   do problema (argumento *fitness exploitation*).
6. Windows: `Set-Content` PS5.1 mete BOM que parte YAMLs; usar a ferramenta Edit.
   Scripts novos: `sys.stdout.reconfigure(encoding="utf-8")` contra crashes cp1252.
7. Rotina Noturna do launcher = forma oficial de retreinar local; servidores ISCTE p/ treinos
   longos (tmux; ver memória `server_training_setup`).

---

## 4. Servidores ISCTE — TUTORIAL: aceder, navegar e extrair resultados

**Pré-requisito: a VPN do ISCTE TEM de estar ligada** (senão o `ssh` dá timeout).
Máquinas: `SERVIDOR_DE_TREINO` (hostname `dellicious`) e `SEGUNDA_MAQUINA`.
User `goncalo`; password é a pessoal do Gonçalo — **não está escrita aqui de propósito** (repo git).
Host key (ed25519) da `.14`: `SHA256:HOSTKEY_REMOVIDA`.

### 4.1 Ligar (sessão interativa)
```powershell
ssh goncalo@SERVIDOR_DE_TREINO          # escreve a password quando aparecer "password:"
```

### 4.2 Onde estão as coisas no servidor (mapa de pastas)
Tudo vive em `~/swarm-robotics-tese/` (Python 3.12, `.venv`). O que interessa para resultados:
```
~/swarm-robotics-tese/
├── results/
│   ├── graficos_tese/<DD-MM-YYYY_HHhMMm>/   ← PACOTE FINAL de cada treino:
│   │     • PNGs: boxplot_*, comparacao_mapa_*, desempenho_global_{gnn,ppo,sac},
│   │       heatmap_geodesico_*, heatmap_ocupacao_{algo}_{cenario},
│   │       taxa_sucesso_por_cenario, recolhas_por_cenario, comparacao_barras_geral
│   │     • CSVs: dados_historicos.csv (curvas), dados_melhores_scores.csv (fitness/run)
│   │     • info_treino.yaml (hiperparâmetros usados nesse treino) ← guardar sempre
│   ├── evaluation/        ← eval_{algo}_{cenario}.csv, eval_comparacao_*, eval_summary.csv
│   │                        (eval_summary.csv = FONTE DE VERDADE: 1 linha/episódio,
│   │                         colunas success/food_collected/total_reward)
│   ├── logs/  logs_ppo/  logs_sac/     ← logs de treino (GNN / PPO / SAC)
│   └── models/  models_ppo/  models_sac/  ← modelos treinados (.pth / .zip)
│         (nomes com sufixo de cenário: _{scenario}; "none" = sem sufixo)
```
> Nota: `results/estatisticas/` e `results/heatmaps/` podem **não** existir no servidor —
> são gerados localmente pelo pipeline. Por isso o `tar` de extração usa `--ignore-failed-read`.

A pasta de cada treino tem o timestamp de **quando terminou**. Para saber qual é o mais recente:
```powershell
ssh goncalo@SERVIDOR_DE_TREINO "ls -lt ~/swarm-robotics-tese/results/graficos_tese/"
```
(ex.: `11-06-2026_21h15m` = treino de 48h; `09-06-2026_15h34m` = treino de 24h)

### 4.3 Verificar um treino que ainda está a correr
```powershell
ssh goncalo@SERVIDOR_DE_TREINO "tmux ls"                                  # sessões ativas
ssh goncalo@SERVIDOR_DE_TREINO "tmux capture-pane -pt treino48h -S -60"   # últimas linhas SEM anexar
ssh goncalo@SERVIDOR_DE_TREINO "uptime"                                   # load ~24 = a treinar a fundo
```
Anexar: `tmux attach -t treino48h`. Sair **sem matar**: `Ctrl+B` depois `D`. **Nunca `Ctrl+C`.**
O treino de 48h foi lançado **sem `tee`** → não tem ficheiro de log, só o buffer do tmux.

### 4.4 Extrair os resultados para o PC (procedimento testado — 14 jun 2026)
A forma robusta é **empacotar no servidor e trazer 1 ficheiro** (evita scp recursivo lento):
```powershell
# 1) Empacotar no servidor (ajusta a pasta <DD-MM-...>; --ignore-failed-read tolera pastas em falta)
ssh goncalo@SERVIDOR_DE_TREINO "cd ~/swarm-robotics-tese && tar czf /tmp/res.tar.gz --ignore-failed-read results/graficos_tese/<PASTA> results/evaluation results/logs results/logs_ppo results/logs_sac && ls -lh /tmp/res.tar.gz"

# 2) Trazer para o PC (pasta out/ do projeto)
scp goncalo@SERVIDOR_DE_TREINO:/tmp/res.tar.gz "$env:USERPROFILE\Desktop\Tese\CODE\swarm-robotics-tese\out\res.tar.gz"

# 3) Extrair localmente
New-Item -ItemType Directory -Force "out\res" | Out-Null
tar xzf "out\res.tar.gz" -C "out\res"

# (Opcional) Trazer também os MODELOS, p/ re-avaliar localmente com eval_suite
ssh goncalo@SERVIDOR_DE_TREINO "cd ~/swarm-robotics-tese && tar czf /tmp/models.tar.gz results/models results/models_ppo results/models_sac && ls -lh /tmp/models.tar.gz"
scp goncalo@SERVIDOR_DE_TREINO:/tmp/models.tar.gz "$env:USERPROFILE\Desktop\Tese\CODE\swarm-robotics-tese\out\models.tar.gz"
```
Cada `ssh`/`scp` pede a password (uma vez cada). Se errares, é `Permission denied` — repete.

**Para o Claude/assistente extrair sozinho** (a password é interativa e o classificador bloqueia
instalar chave persistente): usar o PuTTY já instalado, passando a password e a host key na linha
de comando — `plink` para comandos remotos, `pscp` para copiar:
```bash
plink -ssh -batch -hostkey SHA256:HOSTKEY_REMOVIDA -pw '<PASS>' goncalo@SERVIDOR_DE_TREINO "<comando remoto>"
pscp  -batch -hostkey SHA256:HOSTKEY_REMOVIDA -pw '<PASS>' goncalo@SERVIDOR_DE_TREINO:/tmp/res.tar.gz "<destino local>"
```
(o `-hostkey` evita o prompt interativo do cache do PuTTY; a fingerprint obtém-se com
`plink -ssh -batch -pw x goncalo@SERVIDOR_DE_TREINO true` na 1ª tentativa falhada).

Detalhes adicionais (histórico, comando exato do treino, scp do código): `memory/server_training_setup.md`.

---

## 5. Comandos-chave (pipeline de resultados)

```bash
# Avaliação completa (30 ep, emparelhada) + gráficos de tarefa
.venv/Scripts/python.exe scripts/eval_suite.py --episodes 30

# Significância estatística (gera CSV + tabela LaTeX)
.venv/Scripts/python.exe scripts/statistical_tests.py

# Rrobust (por algo/cenário) e gráfico
.venv/Scripts/python.exe scripts/run_eval.py --algo sac --scenario u_wall --episodes 30 --fail-frac 0.1 --seed-base 1000
.venv/Scripts/python.exe scripts/plot_robustez.py

# Sscale (zero-shot N variável)
.venv/Scripts/python.exe scripts/eval_scalability.py --episodes 20

# Tese (na pasta Tese/)
pdflatex -interaction=nonstopmode main.tex   # ×2; biber main se o .bib mudar
```

Figuras da tese vivem em `Tese/images/resultados/` (mecanismo `\figresultado` — copiar o PNG
com o nome certo e recompilar; sem editar o .tex).

---

## 6. Reformulação do Launcher/Dashboard (proposta 10 jun 2026 — APENAS IDEIA, nada implementado)

> **DECISÃO (Gonçalo, 10 jun)**: avançar com isto **depois do treino de 48h** estar recolhido
> e re-avaliado (ordem: resultados 48h primeiro, launcher a seguir). Começar pela fase F1.

### 6.1 Diagnóstico do launcher atual (`launcher_dashboard.py`, 1185 linhas)

**O que funciona bem** (preservar): lançar treinos por algoritmo/cenário, Tour, Rotina Noturna
com pesos de tempo, galeria de PNGs com descrições didáticas, barra de progresso do relatório,
edição do `foraging.yaml` sem BOM.

**Fraquezas identificadas:**
1. **Monólito** — UI, lógica de processos, paths e textos tudo num ficheiro; difícil de evoluir.
2. **Treinos correm em consolas Windows separadas** (`CREATE_NEW_CONSOLE`) — o dashboard não vê
   o output; o utilizador salta entre janelas soltas. Já causou confusão (processos "invisíveis").
3. **Métricas ao vivo = 1 número** (último valor do CSV, poll de 1s). Não há curvas de
   aprendizagem ao vivo — é o oposto de "dinâmico".
4. **Galeria estática**: 1 PNG de cada vez, sem zoom, sem comparar sessões lado a lado, sem
   filtros. A lista de gráficos é hardcoded e já não cobre os novos (taxa_sucesso, recolhas,
   heatmaps, robustez, escalabilidade).
5. **As métricas científicas da tese não aparecem** — Ptask/Rrobust/Sscale/significância vivem
   em CSVs (`eval_summary.csv`, `estatisticas/`) que o dashboard ignora por completo.
6. **O servidor ISCTE é invisível** — o treino mais importante (48h) só se consulta por ssh manual.
7. Código órfão/duplicado: `_render_maps`, `_render_heatmaps`, `_eval_model` já não têm botão;
   estimativa de tempos duplicada em `_update_night_est` e `_start_night`; descrições falam em
   "5 runs" (desatualizado); typo na linha ~883.

### 6.2 Visão: "Mission Control" da tese

Reorganizar por **fluxo de trabalho real** (treinar → acompanhar → avaliar → usar na tese),
em 4 vistas:

1. **🚀 Treinar** — funde Treino Rápido + Tour + Rotina Noturna numa só vista com uma
   **fila de trabalhos (job queue)**: cada job = (algo(s) × cenário(s) × tempo × runs).
   Presets "Rápido", "Tour", "Noturna" preenchem a fila. Opção "avaliar no fim" (eval_suite)
   e "gerar gráficos no fim" — o pipeline completo numa só ação, sem passos manuais esquecidos.
2. **📡 Monitorizar** — o coração "dinâmico":
   - **Curvas de aprendizagem ao vivo** (ler os CSVs de treino e redesenhar; não 1 número, a curva);
   - **Consola integrada** com o stdout dos treinos (lançar com `PIPE` em vez de consolas soltas);
   - **Painel Servidor ISCTE**: estado do tmux (`tmux capture-pane` via ssh em thread), load,
     ETA do treino, botão "trazer resultados (scp)". O treino de 48h passa a estar à vista.
3. **🔬 Ciência** — tabela-matriz **algoritmo × cenário** com Ptask (% sucesso), recolhas/ep,
   semáforos verde/amarelo/vermelho, lida do `eval_summary.csv`; painéis Rrobust (retenção %),
   Sscale (sucesso vs N) e significância (p-values do `statistical_tests.py`). É o "estado da
   tese" num ecrã — e deteta logo evals desfasados dos modelos (armadilha conhecida nº 3).
4. **🖼 Resultados** — galeria com filtros (sessão/tipo/cenário), zoom, **comparação A/B lado a
   lado** (ex.: treino 24h vs 48h), e botão **"📤 Enviar para a Tese"** que copia o PNG para
   `Tese/images/resultados/` com o nome que o `\figresultado` espera (hoje é manual e sujeito a erro).

Extra para a defesa: **modo Demo** — um ecrã único com visualizador 3D + heatmap + métricas,
preparado para apresentar ao júri.

### 6.3 Arquitetura e tecnologia

- Partir o monólito num pacote `dashboard/` (`ui/` vistas, `jobs.py` fila+ProcessRunner com PIPE,
  `data.py` leitura de CSVs/sessões, `remote.py` ssh/scp, `catalog.py` descrições dos gráficos).
  Os scripts existentes (run_experiments, eval_suite, plot_results…) continuam a ser o backend —
  o dashboard só orquestra. **A Rotina Noturna oficial não muda de semântica.**
- **Tecnologia — decisão em aberto, 2 opções:**
  - **Opção A (recomendada): NiceGUI** (web local, abre no browser). Aspeto moderno
    (Material/Tailwind) sem esforço, gráficos Plotly interativos nativos, atualização live via
    websockets, tabelas com sort/filtro. É a forma mais barata de obter o "look atualizado e
    dinâmico". Bónus: acessível por rede local (telemóvel/2º ecrã na defesa). Custo: dependência
    nova + reescrita da camada UI (a lógica reaproveita-se).
  - **Opção B (conservadora): manter CustomTkinter** e fazer facelift — embeber matplotlib
    (FigureCanvasTkAgg) para curvas ao vivo, consola integrada, tabela Ciência. Menos risco,
    menos "wow"; o limite é o próprio Tkinter.
- Migração **incremental**: o launcher antigo mantém-se funcional até a versão nova ter paridade
  (não partir a ferramenta de trabalho a meio dos treinos da Fase B).

### 6.4 Faseamento sugerido (encaixa nas Fases A/B do plano)

1. **F1 — Esqueleto + Treinar + consola integrada** (job queue, processos com PIPE) ← maior ganho funcional
2. **F2 — Monitorizar** (curvas ao vivo + painel servidor ISCTE)
3. **F3 — Ciência + galeria nova** (tabela Ptask/Rrobust/Sscale, comparação A/B, "Enviar para a Tese")
4. **F4 — Modo Demo + polish** (perto da defesa, Fase E)

Critério de pronto: tudo o que o launcher atual faz + monitorização live + tabela Ciência,
sem janelas de consola soltas.
