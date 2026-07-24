# PLANO MESTRE — Tese de Mestrado (19 jul → Outubro 2026)

> **Este é o ÚNICO ponto de re-entrada do projeto.** Escrito a **19 jul 2026**,
> **atualizado a 24 jul** (mapa grande P1.6 + pacote do orientador P2). Funde o
> `PLANO_ATAQUE_FINAL.md` (lista acionável de 15 jul) com o `PLANO_DE_ATAQUE.md`
> (registo histórico) — ambos ficam como ARQUIVO; não os atualizes, atualiza ESTE.
>
> **Para o Claude/Opus:** lê este ficheiro do princípio ao fim antes de tocar em
> qualquer coisa. Verifica `git log` e as checkboxes — NÃO refaças trabalho fechado.
> A memória persistente (`memory/`) tem o detalhe de cada episódio; o índice é o
> `MEMORY.md`.

**Tese**: "Aprendizagem por Reforço para Controlo de Enxames" — ISCTE, Mestrado em IA
**Orientador**: Prof. Luís Nunes | **Versão composta ao orientador: 15 set** | entrega 30 set | defesa Outubro

---

# 0. LOG DE SESSÃO — 24 jul 2026 (Opus, PC do trabalho)

> Ponto de re-entrada rápido. O detalhe de cada item está nas secções próprias
> (P1.6 para o mapa, P2 para o orientador).

**Contexto ao começar:** este PC estava 9 dias desatualizado (25 commits por
puxar). Feito `git pull --ff-only`. **Trabalhar sempre na `main`.**

**Feito hoje (10 commits, todos em `origin/main`; o último é `e053a91`):**
1. **MAPA GRANDE — 8.º cenário, código FECHADO** (ver P1.6). Desenhado a partir
   de um esboço do utilizador, aprovado em planta 2D e em 3D **antes** de virar
   código, integrado como `mapa_grande` (r=60, 103×62 m, 5 zonas, 143 m de pior
   percurso). **Nunca treinado.**
2. **4 bugs corrigidos** — dois deles teriam invalidado a campanha inteira:
   - `max_steps` 1200→**2000** (a 0,2 m/passo o pior spawn está a 629 passos só
     de ida; 1200 nem dava para ida-e-volta);
   - orçamento do GNN **195→780 min/run** (a 57 min/geração, 195 min dariam 3,4
     gerações contra as 14 das campanhas fechadas — seria "o evolutivo falha"
     por artefacto do orçamento);
   - `required_to_eat` 3→**1**; `use_geodesic` sem o mapa (ficava sem campo
     geodésico).
   - **Bónus que afeta TODAS as campanhas:** `set_scenario` apagava os 37
     comentários do `foraging.yaml` a cada cenário. Agora é edição cirúrgica.
3. **`tests/test_mapa_grande.py`** — 11 testes, todos a passar. Cada um cobre um
   modo de falha que invalidaria a campanha (determinismo, fuga de estado entre
   cenários, porta com alternativa, obstáculos a selar corredores, `obs_dim`=111).
4. **Pré-registo** (`PRE_REGISTO_MAPA_GRANDE.md`) escrito **antes** de qualquer
   treino: QI7, fases F0/F1/F2, testes M1-M3, regra de decisão, modos de falha.
5. **Pipeline de figuras** do mapa + `eval_zeroshot_mapa.py` (F1).
6. **Pacote para o orientador PRONTO** (ver P2) — só falta enviar.

**Decisões tomadas (não reabrir):**
- **20 agentes**, não mais: `obs_dim = 16+(N-1)×5`; com 20 fica em 111 (= aos 7
  cenários) e os modelos existentes carregam. Com 40 seria 211 e PPO/SAC
  precisariam de arquitetura nova.
- **Obstáculos estáticos** (decisão do utilizador).
- **NÃO lançar F2 em paralelo com o mega-treino.** Servidor medido: 64 vCPU,
  load 38, 42% idle — mas um treino GNN pede sempre 30 workers, e 3 streams =
  90 processos em 64 núcleos (1,4× sobre-subscrito). O GNN faria 9,8 gerações
  em vez de 13,7 **e** o mega-treino renderia ~30% menos e atrasaria. Poupava 4
  dias e arriscava duas campanhas. **Esperar por ~3 ago.**

**Verificado (não alterou código):** os robôs **não** passam por cima das
paredes (teste empírico: sobem a z≈14,7 m, atravessam 0); a porta **tem
alternativa** (+23%, não bloqueia); os 7 cenários da tese ficaram intactos.

**Primeiro sinal do zero-shot (F1, 2 de 21 células — NÃO é conclusão):** o GNN
do **Sandbox** faz 14-20 recolhas/ep no mapa novo sem lá ter treinado (10/10
episódios); o do **Quatro Salas** faz 0. Se se confirmar, é especialização vs
generalização — boa matéria de discussão.

**Próximo passo, por urgência:** (1) **enviar o draft ao orientador** — é o item
mais atrasado e o único que não depende de servidor; (2) F1 zero-shot (local,
opcional); (3) F2 no servidor depois de ~3 ago.

---

# 1. REGRAS INVIOLÁVEIS (do utilizador — não negociar)

1. Responder e escrever sempre em **PT-PT** (com todos os acentos).
2. **O código não é avaliado** — a tese e o artigo são. Todo o esforço vai para os documentos.
3. **Não lançar treinos nem mexer no servidor** sem o utilizador pedir explicitamente.
4. **Nunca concluir nada a partir de números de TREINO** (armadilha nº3) — o veredicto
   é sempre `eval_summary.csv` / `eval_by_run.csv`, da MESMA data dos modelos.
5. Nada de `Set-Content`/`Out-File` PS5.1 em YAMLs (o BOM parte-os) — usar a ferramenta Edit.
6. Antes de dar qualquer sessão por concluída: (a) a tese compila (0 refs indefinidas)?
   (b) os números citados batem com o CSV fonte (dizer qual)? (c) commit em PT descritivo?
   (d) checkboxes DESTE ficheiro atualizadas com a data?

---

# 2. ESTADO (o que está FECHADO — não reabrir)

> **Atualização de 24 jul:** o mega-treino P1.5 está a meio e saudável (megaA na fase
> A2, megaB na B3; durações reais batem com as estimadas ao décimo de dia; fim ~1-3 ago).
> Acrescentou-se o **mapa grande** como 8.º cenário — código fechado e pré-registado,
> por treinar (**P1.6**). O pacote para o orientador está pronto a enviar (**P2**).
> O resto desta secção é de 19 jul e mantém-se válido.

## Entregáveis
- **Tese: 117 págs**, compila limpa (pdflatex ×2 + biber), 0 refs indefinidas, **0 overfulls**.
  Revisão número-a-número COMPLETA a 18 jul (commits `17a13ad` + `2f536c7`): todos os
  números verificados contra CSVs/config/código, 5 figuras regeneradas, Lista de
  Acrónimos corrigida (estava VAZIA desde sempre), Apêndice A vs `foraging.yaml` conferido,
  geometria dos 7 cenários vs `swarm_env_3d.py` conferida.
- **Artigo: 9 págs** PT-PT, compila, `references.bib` sincronizado byte a byte com o da tese.
- PDFs de referência: `out/{Tese,Artigo}_Goncalo_Pombo_v14jul2026.pdf` (pós-18 jul, recompilar
  para versão nova ao enviar ao orientador).
- **`docs/REPRODUZIR.md`**: mapa resultado→dados→script; auditoria número-a-número FEITA
  (SLR, Sscale, tab:res_eval 21/21, tab:res_signif 21/21, §res_novelty, Rrobust).
- **Git**: `main` é a fonte de verdade única (consolidada 15-16 jul); `feat/novelty-search`
  CONGELADA; backups em `backup/*` no GitHub (rollback:
  `git push origin backup/main-pre-consolidacao-15jul:main --force`).

## Ciência (resultados canónicos — a fonte de qualquer afirmação na tese)

**Campanha final 7d** (3 algos × 7 cenários × 7 runs = 147 treinos; eval 20 ep/run
emparelhada = 140 ep/célula; Mann-Whitney + δ de Cliff sobre médias por run, n=7):

| Cenário | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 38.3±31.0 (86%) [5/7] | **71.5±1.0** (100%) | 69.2±1.9 (100%) |
| Muro em U | 24.5±32.7 (43%) [3/7] | **39.6±36.7** (71%) [4/7] | 9.0±15.1 (34%) [2/7] |
| Gargalo | 121.4±20.0 (100%) | **123.2±1.2** (100%) | 41.4±36.8 (72%) [5/7] |
| Quatro Salas | **59.8±13.2** (100%) | 33.6±3.8 (100%) | 31.8±3.3 (100%) |
| Porta Cooperativa | **69.8±1.0** (100%) | 67.1±3.7 (100%) | 62.1±2.5 (100%) |
| Perceção Cooperativa | **19.0±8.7** (91%) [6/7] | 15.3±0.4 (100%) | 16.1±0.8 (100%) |
| Porta c/ Alternativa | **86.7±2.0** (100%) | 85.3±4.0 (100%) | 68.6±3.4 (100%) |

- **Achado central:** o "colapso do evolutivo" era **artefacto do desenho da fitness**
  (retorno acumulado farmável por deambulação). A **fitness de homing**
  (`J = f̄·10⁴ + 5000·h̄`) cura-o: GNN converge em 28/28 runs dos labirintos não-decetivos
  e é significativamente superior aos dois métodos de gradiente em 3 cenários.
- **Muro em U:** nenhum algoritmo o resolve de forma fiável (bimodal nos três; nenhuma
  diferença significativa). O problema é a **descoberta** sob observabilidade parcial.
- **Escalabilidade Zero-Shot: 28/28 células a 100%** (7 cenários × N∈{10,20,50,100});
  retenção per capita N=100: bypass 90%, coop_door 88%, u_wall 78%, Sandbox 39% (diluição
  de recurso, não falha de coordenação). CSVs: `results/estatisticas/escalabilidade_*.csv`.
- **Novelty fixo (w=0.5, orçamento igualado 195 min):** GANHA no Muro em U (7/7 a 100%,
  69.8±5.9 vs 3/7, p=0.026, δ=+0.71); PERDE no bypass (63.0 vs 86.7, p=0.0006, δ=−1.00).
  Leitura: instrumento **direcionado** — compra descoberta onde falta, desperdiça seleção
  onde sobra. Dados: `results/novelty_final/`. (O 81.3 de 2 jul era artefacto de 600 min.)
- **SLR conduzida a sério** (o PRISMA inicial era fabricado): 883 registos → 680 únicos →
  **58 estudos**; **a lacuna está MEDIDA: só 1 em 58 (Iskandar 2024) compara os paradigmas.**
  Pipeline: `scripts/slr_pipeline.py` a partir de `docs/slr/screening.csv`.
- **Bibliografia:** auditada 3×; Iskandar é REAL (2.º autor **Ali** Hammoud, confirmado na
  fonte primária); nomes NEAT corrigidos (Tameem Uz Zaman, Pigar Biteng). Lição
  permanente: **verificar NOMES e CONTEÚDO, não só DOIs.** Os DOIS `.bib` corrigem-se juntos.

## O que estava errado em planos antigos (REFUTADO — não citar)
~~GNN colapsa nos labirintos~~ · ~~PPO faz reward hacking no Muro U~~ (hoje é o melhor lá) ·
~~SAC resolve tudo~~ (é o mais frágil nos gargalos) · ~~Sscale 15%→100%~~ (é 100% em tudo) ·
~~Novelty 81.3 é o melhor resultado do bypass~~ (era orçamento desigual).

---

# 3. A ÚNICA COISA A CORRER — campanha Novelty ADAPTATIVO (fecha 19-20 jul = AGORA)

Lançada 12 jul 19:46 no `.14`, 2 streams tmux (`week_A` fim ~18 jul, `week_B` ~19 jul):
Novelty adaptativo (w=0,5 decai ×0,98/gen após 10 gens consecutivas a comer) nos 7 cenários
@195 min × 7 runs (seeds 1-7) + braços de controlo @390 min. Fases arquivadas em
`~/week_{A,B}_fase*/`. ⚠️ A ordem dos cenários é a CANÓNICA de `src/scenarios.py`, não a
do `--scenarios`.

**Pré-registo COMPLETO e congelado ANTES dos dados:**
[`docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md`](PRE_REGISTO_NOVELTY_ADAPTATIVO.md) — hipótese,
testes confirmatórios T1-T4, regra de decisão da QI6 (sobe a resultado sse: não-degrada os
5 fáceis + ganho no u_wall + sem custo no bypass), compromissos de reporte (TODOS os runs).
**Segui-lo à letra; não escolher a conclusão depois de ver os dados.**

## Checklist da chegada (P1) — passos 1-3 FECHADOS a 19 jul (Fable)
- [x] **Confirmadas as duas streams CONCLUÍDAS** (19 jul): A fechou 18 jul 19:15 UTC,
      B fechou 19 jul 12:56 UTC; sem tmux, load 0.00; sentinela + `eval_by_run.csv`
      nas 5 fases.
- [x] **Tudo trazido** (19 jul): tarball em `out/week_adaptativo_19jul.tar.gz` (11 MB),
      extraído em `out/week_adaptativo_19jul/` e instalado em
      **`results/novelty_adaptativo/`** (fora do git, como o `novelty_final/`).
- [x] **Armadilha nº9 tratada por adaptação** — as fases NÃO são sessões `graficos_tese`
      (são cópias de `results/{evaluation,models,logs}` por fase, já auto-contidas e
      emparelhadas); o `pos_campanha.py` não se aplica e **os `results/models*` ativos
      (campeões 7d da tese) ficaram INTACTOS de propósito** — instalar os modelos
      adaptativos por cima criaria a armadilha inversa.
- [x] **`_run{1..7}` verificados** (armadilha nº8): 175 `.pth`; 7 runs × 20 ep por
      cenário nas 5 evals (A1: none/u_wall/bottleneck/four_rooms; B1: coop_door/
      bypass/perception; A2: u_wall controlo objetivo @390; B2: u_wall adaptativo @390;
      B3: bypass adaptativo @390) — bate com o pré-registo.
- [x] **Configs do servidor repostos** (19 jul): os dois dirs (`~/swarm-robotics-tese` e
      `~/swarm-novelty`) em `novelty_weight: 0.0`, `novelty_adaptive: false`
      (B reposto à mão; backup `foraging.yaml.bak_19jul`).
- [x] **ANÁLISE T1-T4 FEITA e INTEGRADA (19 jul, Fable)** — `scripts/analise_adaptativo.py`;
      unblinding registado no §7 do pré-registo. **Veredicto: SOBE A RESULTADO** (T1 sem
      degradação, todos p≥0,21; T2 u_wall 7/7, 68,5±13,1, p=0,009, δ=+0,76; T3 bypass sem
      custo, δ=−0,35 n.s.; T4 vs fixo: bypass δ=+0,59). Exploratório: objetivo puro @390
      no u_wall CONTINUA bimodal (4/7) → o ganho é do mecanismo; bypass adaptativo @390 =
      **88,7±0,6 [7/7] = melhor resultado da dissertação**. QI6 + sec:res_novelty +
      Discussão + Conclusões + Trabalhos Futuros reescritos na tese; abstract +
      contribuições (v) + §4.3 + conclusões no artigo. Tese 121 págs, artigo 10 págs,
      ambos 0 undefined / 0 overfulls.
- [x] **Passou → o w adaptativo passou a RESULTADO** (integrado em `sec:res_novelty` +
      QI6 na tese e no artigo, commit `704a36e` de 19 jul). A alternativa pré-registada
      ("se não passar, reportar como resultado negativo honesto") não chegou a aplicar-se.
- [x] **Recompilado e commitado** (19 jul, `704a36e`): tese 121 págs, artigo 10 págs,
      ambos 0 refs indefinidas / 0 overfulls. *(Checkboxes fechadas a 24 jul — o trabalho
      estava feito desde 19 jul, só faltava marcá-lo aqui.)*

---

# 4. TAREFAS ABERTAS (por prioridade, depois do P1)

## P1.5 — MEGA-TREINO DE 1 MÊS ⏳ **LANÇADO 19 jul 19:23 UTC** (composição aprovada: «piores mapas»)
- [x] Pré-registo v2 escrito ANTES dos dados: **[`PRE_REGISTO_MEGATREINO.md`](PRE_REGISTO_MEGATREINO.md)**
      (proposta original: [`PROPOSTA_MEGATREINO_1MES.md`](PROPOSTA_MEGATREINO_1MES.md)).
- [x] **A CORRER**: tmux `megaA` (`~/swarm-robotics-tese`, scripts `mega_streamA.sh`):
      u_wall n=28 nos 4 braços (adapt→obj→PPO→SAC) + Sandbox adaptativo n=21, fim ~1 ago;
      tmux `megaB` (`~/swarm-novelty`, `mega_streamB.sh`): ablação anneal (sustain 5/20,
      decay 0,95/0,995 em u_wall+bypass ×7) + bypass adaptativo n=21 + SAC bottleneck n=21
      + perception adaptativo n=21, fim ~3 ago. Arquivo por fase em `~/mega_{A,B}_fase*/`;
      arranque confirmado (Gen 1 26s, w=0,500).
- [ ] Na chegada: verificação `_run{n}` + instalar em `results/mega_1mes/` SEM tocar nos
      modelos ativos; confirmar configs repostos (os scripts repõem no fim — verificar);
      análise M1-M3 do pré-registo v2. **Hard stop de integração na tese: 22 ago.**

## P1.6 — MAPA GRANDE (8.º cenário) 🆕 **código FECHADO a 24 jul; treino só depois do mega-treino**

Ideia do utilizador (24 jul): um mapa **muito maior e composto**, que junte as
dificuldades dos 7 cenários num percurso único, para testar se as conclusões obtidas
em cenários de dificuldade isolada transferem para um ambiente combinado. Desenhado a
partir de um esboço do utilizador, **aprovado visualmente em planta 2D e em 3D antes
de virar código** — e só depois integrado.

**Estado: implementado, testado, NUNCA treinado.** Commits `da0c166` (geometria),
`22922fb` (integração), `ce45b9c` (correções + pré-registo).

- [x] **Geometria aprovada** (r=60): labirinto 103×62 m em 5 zonas — **S** sala de
      partida (aberta, obstáculos, spawn) · **A** gargalo + beco em U · **B** quatro
      salas · **C** porta cooperativa + alternativa longa · **D** câmara do ninho.
      Pior percurso **143 m** (4,2× os 34 m do Quatro Salas). 106 obstáculos
      **estáticos** (decisão do utilizador).
- [x] **Integrado como `mapa_grande`** em `src/scenarios.py` + `swarm_env_3d.py`.
      Verificado: `obs_dim=111` **igual aos 7 cenários** → os modelos GNN existentes
      abrem o mapa sem alteração nenhuma (zero-shot de topologia já funciona).
- [x] **Isolamento dos 7 cenários da tese** (campanhas fechadas, números já no texto):
      `arena_radius_mapa_grande=60` e `max_steps_mapa_grande=2000` são overrides **por
      cenário**; o `arena_radius` global fica em 15. Novo `THESIS_SCENARIOS` separa "os
      7 da tese" de "todos os cenários" — o mapa aparece nas vistas de operação mas
      **não** nas tabelas de resultados enquanto não tiver campanha avaliada.
      Regressão verificada: os 7 mantêm arena, paredes, obstáculos, steps e geodésico.
- [x] **Botão «Ver o mapa em 3D»** na vista Ao vivo, no MESMO visualizador Ursina dos
      outros mapas (`visualize_mapa_grande.py`), a ler a geometria do **ambiente real**.
- [x] **`dashboard/config.py` deixou de ter cópia dos cenários** — importa de
      `src/scenarios.py`. Já divergia nos rótulos; com um 8.º mapa a entrar era repetir
      o erro que fez o 7.º cenário ser treinado mas nunca avaliado.
- [x] **Pré-registo escrito ANTES de qualquer treino**:
      [`docs/PRE_REGISTO_MAPA_GRANDE.md`](PRE_REGISTO_MAPA_GRANDE.md) — QI7, desenho
      congelado com justificação de cada parâmetro, fases F0/F1/F2, testes M1-M3, regra
      de decisão e modos de falha antecipados.
- [ ] **F0 — smoke test local** (~1 h, GNN, 1 run): só confirmar que arranca. **Não
      produz resultado** e não entra em análise nenhuma.
- [ ] **F1 — zero-shot de topologia**: avaliar os campeões dos 7 cenários neste mapa
      sem retreino (custa horas, não dias; não precisa do servidor).
- [ ] **F2 — treino nativo**: 3 algoritmos × 7 runs × seeds 1-7. **Só depois do
      mega-treino fechar (~3 ago).** Hard stop de integração na tese: **22 ago**.

### ⚠️ Dois bugs apanhados na auditoria de 24 jul (a pedido do utilizador)

Ambos silenciosos — teriam produzido "os 3 algoritmos falham" sem sinal de que a culpa
era do parâmetro. Ficam registados porque a lição é geral:

1. **`max_steps` impossível de cumprir.** v_max = 0,2 m/passo (`move_local` clipado a
   ±1 × 0,2) e o pior spawn está a 126 m ⇒ **629 passos só de ida**. Os 1200 iniciais
   não davam sequer para ida-e-volta (1259). Corrigido para **2000** (folga 3,2× sobre
   a ida — a mesma que o Quatro Salas tem com 500). **Lição: `max_steps` de um cenário
   novo calcula-se a partir da distância geodésica e da velocidade máxima, não por
   analogia com outro cenário.**
2. **`required_to_eat` a 3.** O cenário caía no ramo `else` e exigia 3 agentes
   simultâneos no ninho (raio 1,5 m) ao fim de 143 m — uma 2.ª tarefa cooperativa
   acidental empilhada sobre a navegação. Corrigido para **1**. **Lição: acrescentar um
   cenário obriga a rever TODAS as listas que discriminam cenários por nome**
   (`_nav_scenarios`, `use_geodesic`, `DOOR_SCENARIOS`, `MAZE_SCENARIOS`).

Um terceiro, apanhado antes por teste: `use_geodesic` era uma lista escrita à mão e o
mapa ficou **sem campo geodésico** — num percurso de 143 m, exatamente o mínimo local
que o geodésico existe para eliminar. Passou a derivar de `MAZE_SCENARIOS`.

### Verificações que NÃO alteraram código (mas respondem a perguntas do utilizador)

- **Os robôs saltam por cima das paredes?** **Não.** Forcei os 20 agentes contra a
  parede central com ação +z e +y durante 400 passos: sobem até z≈14,7 m e
  **atravessaram 0**. Colisão é AABB a 3D (paredes de z=−15 a +15) com deslizamento +
  correção de penetração.
- **A porta faz sentido?** **Sim.** Com o painel fechado o caminho custa 147,8 m contra
  119,7 m com ela aberta: há **alternativa (+23%)**, não bloqueia. Cooperar é
  vantajoso, não obrigatório — a estrutura do `cooperative_door_bypass`.
- **A população chega?** **20 é o valor certo**, apesar de a densidade ser 9× mais
  esparsa (318 vs 35 m²/agente; igualar exigiria 180 agentes). Razão: `obs_dim =
  16+(N−1)×5` **muda com N** — com 20 fica em 111 (igual aos 7 cenários, modelos
  existentes carregam); com 40 seria 211 e PPO/SAC precisariam de arquitetura nova,
  matando a comparação emparelhada. O custo também é super-linear (20→40 = 2,8× o
  tempo). A esparsidade é o problema que o mapa mede, não um defeito a corrigir.

## P2 — Draft cedo ao orientador (fim de julho, NÃO esperar por 15 set)

> ⚠️ **É o item mais atrasado do plano, e o único que não depende de servidor nenhum.**
> O pacote está PRONTO desde 24 jul — falta só o utilizador confirmar 3 pontos e enviar.

- [x] **Pacote preparado (24 jul)**: PDFs datados em `out/envio_orientador_24jul2026/`
      (tese 121 págs + artigo 10 págs, do commit `704a36e` — fontes e PDF em sincronia)
      e o corpo do e-mail em [`EMAIL_ORIENTADOR_24jul2026.md`](EMAIL_ORIENTADOR_24jul2026.md),
      com anexo opcional de resultados. Todos os números verificados contra `main.tex`.
      Na tabela do anexo só vão a negrito as superioridades **significativas** — o
      Gargalo (p=0,21), o Muro em U e a Porta c/ Alternativa (p=0,85) são empates, e
      destacar o maior valor reintroduziria o erro que o commit `0c25d9e` corrigiu.
- [ ] **Enviar** (falta confirmar: qual foi a última versão que o Prof. viu de facto;
      a capa 2026; e ler o Iskandar antes da reunião — ver P3).
- [ ] **Confirmar com o utilizador a capa: 2025→2026** (mudada a 18 jul, por confirmar).
- [ ] Perguntar o alvo do artigo (conferência vs submissão interna) — deadlines externos
      condicionam o resto. Modelo de formato: artigo IWSSIP em
      `C:\Users\gonca\Desktop\artigos prof\`. Título: recomendação no anexo da
      `PROPOSTA_TREINO_FINAL.md` (opção 1).

## P3 — Tarefas do UTILIZADOR (facilitar, lembrar, verificar consequências)
- [ ] **LER o Iskandar** (PDF pronto: `Desktop/Tese/Iskandar_PhD_2025_DRL_Swarm_Robotics.pdf`,
      RL vs PSO ~págs 14-42) — é o único comparativo dos 58; tudo o que a tese diz dele
      veio de resumos + varrimentos. Depois da leitura: grep `[Ii]skandar` em
      `main.tex`/`artigo.tex` e confirmar frase a frase.
- [ ] Ler um dos artigos NEAT (a afirmação "arenas sem estrangulamentos decetivos" assenta
      no abstract; risco baixo).
- [ ] Rever o PDF do artigo + decidir o título.

## P4 — Agosto: ciclos de revisão
- [ ] Incorporar feedback do orientador (esperar 1-2 ciclos).
- [ ] Fechar o artigo (com o alvo decidido).
- [ ] Trazer do servidor o CSV do braço Novelty preliminar de `~/swarm-novelty` se ainda
      existir (dado como PERDIDO em `cf44368`; menor).

## P5 — 1-15 set: SÓ polimento (a tese composta a 15 set é INEGOCIÁVEL)
- [ ] Verificação final: refs, acrónimos, listas de figuras/tabelas, normas ISCTE da capa.
- [ ] Nada de mudanças de conteúdo nesta janela salvo exigência do orientador.

## P6 — set/out: defesa
- [ ] Slides.
- [ ] **Modo Demo do dashboard (F4)** — único pedaço do dashboard por fazer (ecrã único:
      visualizador + heatmap + métricas para o júri). O dashboard é `python -m dashboard.app`
      (NiceGUI); o launcher antigo foi APAGADO a 16 jul.
- [ ] Ensaiar respostas com o `REPRODUZIR.md` ("de onde vem este número?" → resposta na hora).

## Opcional (só se sobrar tempo de servidor E o utilizador pedir)
- Ablação LiDAR 8→16 raios no Muro em U (7 runs @195min) — testa "deceção sob
  observabilidade parcial". Cortar primeiro se algo derrapar.

---

# 5. O QUE NÃO FAZER (decisões tomadas — não reabrir)

- ❌ Repetir a campanha 7×7 com mais runs (~28 dias de GNN; retorno ≈ 0).
- ❌ Política de atenção por gradiente em SB3 (fica como trabalho futuro, já declarado).
- ❌ Reescrever secções fechadas e coerentes com os dados, salvo exigência do P1/P3.
- ❌ Reabrir as decisões de consolidação de 15 jul (figuras de 26 jun ficam no backup;
      galeria de 14 jul é a boa).
- ❌ Concluir seja o que for de números de treino ou de evals desfasados dos modelos.
- ❌ Lançar treinos por iniciativa própria.

---

# 6. ARMADILHAS (o custo de as esquecer já foi pago — mais de uma vez)

| nº | Armadilha | Antídoto |
|---|---|---|
| 1 | `analise_treino_24h.md` tem conclusões ERRADAS | fonte de verdade = `eval_summary.csv` |
| 2 | Boxplots da sessão 09-06 degenerados (1 run) | não usar |
| 3 | **Números de TREINO ≠ avaliação** | só `eval_summary.csv`/`eval_by_run.csv`, da MESMA data dos modelos |
| 4 | `success = food>0` é métrica fraca | reportar sempre também recolhas/ep |
| 5 | `comparacao_barras_geral` mistura escalas | usar só como demo do fitness exploitation |
| 6 | BOM do PS5.1 parte YAMLs | usar a ferramenta Edit; scripts com `sys.stdout.reconfigure(encoding="utf-8")` |
| 7 | Nomes/conteúdo de referências fabricados | verificar NOMES e afirmações contra o PDF, não só DOIs; os 2 `.bib` juntos |
| 8 | `.pth`/`.zip` sobrescrito pelo último run | verificar `_run{1..7}` por cenário; campeão via `.meta.json` |
| 9 | `results/models/` com modelos de campanha ANTERIOR | **`python scripts/pos_campanha.py` a CADA chegada** |
| 10 | `plot_robustez.py` desemparelha se usar o summary das 7 runs | a base é `eval_{algo}_{cen}.csv` (corrigido 18 jul — não reverter) |
| 11 | `eval_scalability.py` re-avalia modelos do disco | usar `--replot` enquanto os modelos locais não forem os da campanha |
| 12 | Números antigos sobrevivem a reescritas | 73,3 / 67,7 / 0,77 são pré-treino_fds; grep antes de confiar |

---

# 7. SERVIDOR ISCTE (resumo operacional)

- **VPN do ISCTE ligada** primeiro, senão timeout. Máquina: `SERVIDOR_DE_TREINO` (`dellicious`),
  user `goncalo`, password pessoal (não está no repo). Host key ed25519:
  `SHA256:HOSTKEY_REMOVIDA`. 64 vCPU, 125 GiB RAM, sem GPU.
- Para o Claude operar sozinho (password interativa bloqueada): `plink` (comandos) e
  `pscp` (ficheiros) com `-batch -hostkey SHA256:... -pw '<PASS>'`.
- Código vive em `~/swarm-robotics-tese/` (+ dirs isolados por campanha, ex.
  `~/week_{A,B}*`). Ver treinos: `tmux ls`; `tmux capture-pane -pt <sessão> -S -60`.
  **Nunca Ctrl+C num tmux de treino.**
- Extração robusta: `tar czf` no servidor → `pscp` de 1 ficheiro → extrair em `out/`.
  Tutorial completo passo-a-passo: `PLANO_DE_ATAQUE.md` §4 (arquivo) e
  `memory/server_training_setup.md`.
- Pipeline local pós-chegada: `pos_campanha.py` → `eval_by_run`/`eval_suite` →
  `statistical_tests.py` → `gerar_figuras_7d.py --install-oficial` (figuras canónicas) →
  recompilar tese. Detalhe: `docs/REPRODUZIR.md`.

---

# 8. MAPA DE DOCUMENTOS E DADOS

| O quê | Onde |
|---|---|
| **Este plano (único vivo)** | `docs/PLANO_MESTRE.md` |
| Arquivo histórico (armadilhas na origem, tutorial servidor, cronologia) | `docs/PLANO_DE_ATAQUE.md` |
| Plano de 15 jul (superado por este) | `docs/PLANO_ATAQUE_FINAL.md` |
| Pré-registo da campanha adaptativa | `docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md` |
| Pré-registo do mega-treino (P1.5) | `docs/PRE_REGISTO_MEGATREINO.md` |
| Pré-registo do mapa grande (P1.6) | `docs/PRE_REGISTO_MAPA_GRANDE.md` |
| Draft do e-mail ao orientador (P2) | `docs/EMAIL_ORIENTADOR_24jul2026.md` |
| Reprodutibilidade (número → CSV → script) | `docs/REPRODUZIR.md` |
| Proposta/cautelas do treino final + títulos do artigo | `docs/PROPOSTA_TREINO_FINAL.md` |
| SLR (protocolo, screening, pipeline) | `docs/PROTOCOLO_SLR.md`, `docs/slr/` |
| Tese / Artigo | `Tese/main.tex` (117 págs) / `Artigo/artigo.tex` (9 págs) |
| Figuras da tese | `Tese/images/resultados/` (36 PNGs, mecanismo `\figresultado`) |
| Eval canónica 7d | `results/graficos_tese/final_7d/eval_by_run_7d.csv` (torre) |
| Novelty P1/P2 | `results/novelty_final/{uwall,bypass}/` (torre) |
| Escalabilidade | `results/estatisticas/escalabilidade_*.csv` |
| Memória persistente | `memory/` (índice em `MEMORY.md`) |

---

# 9. CALENDÁRIO (atualizado a 19 jul)

| Janela | Foco |
|---|---|
| **19-25 jul** | **P1**: chegada da campanha adaptativa → pré-registo T1-T4 → integração (ou reporte negativo) |
| 26 jul - 3 ago | P2: draft completo ao orientador; capa confirmada; alvo do artigo perguntado |
| ago | Ciclos de revisão com o orientador; artigo fechado; utilizador lê Iskandar/NEAT |
| 1-15 set | SÓ polimento + buffer. **Versão composta a 15 set — inegociável** |
| 15-30 set | Entrega formal (30 set) |
| out | Defesa: slides + modo Demo (F4) + ensaio com REPRODUZIR.md |

Buffer real: ~2 semanas. Se algo derrapar, corta por esta ordem: Opcional (ablação) →
F4 fancy → profundidade da revisão do artigo. A tese está num estado em que **não fazer
nada de novo já dá uma tese defensável** — o risco maior é estragar o que está fechado,
não faltar trabalho.
