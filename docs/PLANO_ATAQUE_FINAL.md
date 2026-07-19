# PLANO DE ATAQUE FINAL — prompt de execução (15 jul → 15 set 2026)

> ⚠️ **ARQUIVO (19 jul 2026).** Este plano foi fundido com o `PLANO_DE_ATAQUE.md` no
> **[`PLANO_MESTRE.md`](PLANO_MESTRE.md)**, que reflete o estado pós-revisão de 18 jul
> e é o único plano vivo. Lê e atualiza ESSE; este fica como registo do que foi
> decidido a 15-16 jul.

> **Este documento é um PROMPT para o Claude/Opus.** Lê-o do princípio ao fim antes de
> tocar em qualquer ficheiro. Ele substitui o topo do `PLANO_DE_ATAQUE.md` como lista
> acionável; o `PLANO_DE_ATAQUE.md` continua a ser o registo histórico (armadilhas,
> tutorial do servidor, resultados) e deve ser consultado, não reescrito.
>
> Escrito a **15 jul 2026**. O repositório foi entretanto consolidado: **a `main` é
> agora a fonte de verdade única** (ver o log de sessão abaixo). Se estiveres a ler isto
> semanas depois, verifica primeiro o que já foi feito (checkboxes + `git log`) e NÃO
> refaças trabalho fechado.

---

## 🔄 LOG DE SESSÃO — 15 jul 2026 (feito no PC do trabalho; para o Claude da torre)

> Resumo do que mudou neste PC nesta sessão, para quem fizer `git pull` na torre de casa.
> **Trabalha na `main`** — a `feat/novelty-search` foi consolidada para lá e está congelada.

**Git / consolidação (P2 — FEITO):**
- `main` avançada por *fast-forward* até à tese final: era 28 jun (`001ee24`) → agora inclui
  campanha 7d, escalabilidade Zero-Shot, Novelty e este plano. `origin/main` = `main` local.
- **4 branches de backup no GitHub** (nada se perde):
  - `backup/main-pre-consolidacao-15jul` ← ponto de **ROLLBACK** da main.
    Reverter tudo: `git push origin backup/main-pre-consolidacao-15jul:main --force`
  - `backup/tese-final-graficos-15jul2026` ← 3 commits da galeria + figuras de 26 jun.
  - `backup/main-local-mai2026` ← 16 commits antigos de Maio da main local.
- **Decisões tomadas (não reabrir):**
  - Figuras da tese: mantidas as canónicas de **10 jul** (campanha 7d). As de 26 jun NÃO
    foram trazidas (eram pré-campanha-final → seria regressão). Ficam no backup.
  - Galeria do dashboard: mantida a versão de **14 jul**. Os extras de 26 jun (pesquisa,
    envio por-secção) ficam no backup, não integrados. O dashboard não é avaliado.
- ~~**Pendente:** apagar `launcher_dashboard.py`~~ ✅ apagado a 16 jul (torre), README limpo.

**P0 — Iskandar 2024 (verificação FEITA; 3 correções APLICADAS):**
- Confirmado **REAL** (DOI `10.17587/mau.25.471-478` resolve para a revista oficial;
  indexado no Semantic Scholar; CC BY). Metadata do `.bib` correta. O flag "fabricado"
  de 21 jun era **falso alarme**. O achado do artigo (RL rápido mas fraco a generalizar;
  PSO robusto mas lento) até reforça a narrativa da tese.
- **3 correções de precisão APLICADAS** a `main.tex` (~698/717/760/771/786) e `artigo.tex`
  (~93/213), na mesma direção:
  1. "numa só tarefa" → reconhece que é avaliada em **ambientes de complexidade crescente**.
  2. "sem escalabilidade" → "sem transferência para **dimensões de enxame não vistas**
     (Zero-Shot)" — eles testam generalização entre ambientes, não entre tamanhos de enxame.
  3. "sem robustez" → "sem robustez **a falhas**" (o abstract usa "robustness" noutro sentido).
  ✅ **Compilado na torre (16 jul)**: tese 117 págs (pdflatex+biber, 0 refs indefinidas) e
  artigo 9 págs (pdflatex+bibtex, 0 refs indefinidas). PDFs frescos commitados.
- ✅ **Fechado (16 jul, torre):** 2.º autor é **Ali** Hammoud — confirmado na FONTE PRIMÁRIA
  (agradecimentos da tese de doutoramento do Alaa Iskandar, Miskolc 2025, DOI
  10.14750/ME.2026.007, acesso livre no REAL-PhD) — corrigido nos DOIS `.bib`. A mesma tese
  incorpora o estudo comparativo (publicação k2) e **não contém p-value/t-test/Wilcoxon**
  (varrimento ao texto integral) → corrobora o "sem inferência estatística". PDF guardado
  para leitura do utilizador em `Desktop/Tese/Iskandar_PhD_2025_DRL_Swarm_Robotics.pdf`
  (81 págs; RL vs PSO ~págs 14-42) — substitui a compra do artigo (600 RUB).

**P3 — REPRODUZIR.md (CRIADO; auditoria parcial FEITA):**
- Novo `docs/REPRODUZIR.md`: mapa resultado→dados→script + pipeline + armadilhas.
- **Auditado no PC (bate 100%):** SLR (456+427=883 → 680 → 58) e Sscale (retenções
  90/88/78/39%, 28/28 células a 100%). **Falta na torre:** tabela de avaliação,
  significância e Novelty (`final_7d/`+`novelty_final/` não estão neste PC).

**P1 — campanha Novelty adaptativo:** ⏳ **ainda a correr** no `.14` (fecha ~19-20 jul).
A campanha NÃO está feita. Mas o **pré-registo está FEITO** (`PRE_REGISTO_NOVELTY_ADAPTATIVO.md`,
15 jul, antes dos dados): hipótese + testes T1-T4 + regra de decisão da QI6 + reporte.
Ao trazer: `pos_campanha.py` → registar anneal/@390 no pré-registo → T1-T4 → regra de decisão.

---

## Contexto em 10 linhas

- Tese de mestrado IA (ISCTE): compara **GNN neuroevolutiva vs PPO vs SAC** em foraging
  3D com enxames, 7 cenários. Orientador Prof. Luís Nunes. **Versão composta: 15 set**;
  entrega 30 set; defesa Outubro.
- A parte experimental está **praticamente fechada**: campanha final 7×7×7 runs feita,
  escalabilidade zero-shot 28/28 fechada, P1/P2 do Novelty (orçamento igualado) corridas
  com estatística limpa. Tese 117 págs + artigo 9 págs, ambos compilam sem erros.
- Achado central: o "colapso do evolutivo" era artefacto da fitness (retorno acumulado
  farmável); a **fitness de homing** cura-o (28/28 runs). Novelty é instrumento
  direcionado: ganha no Muro em U (p=0.026), perde no bypass (p=0.0006).
- **A correr no servidor `.14`** (lançada 12 jul, fins ~19-20 jul): campanha de Novelty
  **adaptativo** (w decai após descoberta) nos 7 cenários @195min + controlos @390min.
- O que falta NÃO é experimentação — é **integridade das fontes, consolidação e entrega**.

Regras do utilizador: responder em PT-PT; o código não é avaliado (a tese e o artigo são);
não lançar treinos nem mexer no servidor sem o utilizador pedir; nunca concluir nada
a partir de números de TREINO (armadilha nº3 — só `eval_summary.csv`/`eval_by_run.csv`).

---

## P0 — Integridade da moldura científica (fazer PRIMEIRO, é a única coisa que pode obrigar a reescrever)

- [ ] **Ler o Iskandar et al. 2024 na íntegra** (é tarefa do utilizador — o teu papel é
      facilitá-la e depois verificar as consequências). É o ÚNICO estudo dos 58 da SLR
      que compara MARL vs bio-inspirado; toda a lacuna "1 em 58" e partes do Cap. 3
      foram escritas a partir do resumo. Depois da leitura:
      - Procurar no `Tese/main.tex` e `Artigo/artigo.tex` todas as afirmações sobre
        Iskandar (grep por `[Ii]skandar`) e confirmar frase a frase contra o PDF real.
      - Se o artigo fizer mais do que o abstract sugere (ex.: já medir escalabilidade),
        ajustar o enquadramento da lacuna ANTES de qualquer outra edição à tese.
- [x] **Artigos NEAT verificados (16 jul, torre)** — `zaman2025neat` (IRCE 2025) e
      `biteng2025training` (ICMA 2025) são REAIS (DOIs resolvem no Semantic Scholar; grupo
      MARS/UTRGV de Qi Lu) e as afirmações da tese (§707) e do artigo (§194/§625) conferem
      com os abstracts: fitness de retorno acumulado, arenas abertas c/ obstáculos dispersos,
      escalabilidade, sem colapso. MAS os nomes próprios no `.bib` estavam FABRICADOS
      ("Tanvir U."→**Tameem Uz** Zaman; "Preston"→**Pigar** Biteng) — corrigidos nos DOIS
      `.bib`. Nota: a afirmação "arenas sem estrangulamentos decetivos" assenta no abstract;
      confirmar no PDF integral quando o utilizador ler (risco baixo).
- [ ] Contexto: a bibliografia já foi auditada 2× e apanharam-se referências fabricadas
      (ver `memory/bibliografia_auditoria.md`). O padrão a temer é sempre o mesmo:
      afirmação plausível sem fonte real por trás. Na dúvida, verificar contra o PDF.

## P1 — Fecho da campanha adaptativa (~19-20 jul, quando o utilizador trouxer os dados)

**Pré-registo — [x] FEITO (15 jul): [`docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md`](PRE_REGISTO_NOVELTY_ADAPTATIVO.md)**
Escrito e commitado ANTES de os dados de avaliação existirem. Fixa hipótese, testes
confirmatórios T1-T4 (Mann-Whitney + δ sobre médias por run, n=7), a **regra de decisão
pré-comprometida** da QI6 (sobe a resultado sse: não-degrada os 5 fáceis + ganho no u_wall
+ sem custo no bypass) e os compromissos de reporte (todos os runs; convergência descritiva,
magnitude como teste). ✅ Parâmetros do anneal (w₀=0,5; gatilho=10 gens a comer; decay
×0,98/gen até 0) e braços @390 (A fase 2 = controlo u_wall OBJETIVO; B fases 2-3 = u_wall/
bypass ADAPTATIVO) **registados a 16 jul, antes do unblinding** (fontes: scripts+configs+código
do servidor). O pré-registo está completo; falta só a campanha fechar.

**Mecânica da chegada (armadilhas conhecidas):**
- [ ] `python scripts/pos_campanha.py` ao trazer QUALQUER campanha (armadilha nº9:
      `results/models/` já teve modelos de junho a contaminar evals locais).
- [ ] Repor nos DOIS dirs do servidor: `novelty_weight: 0.0`, `novelty_adaptive: false`
      (o dir do stream B fica em 0.5 pelo script — repor à mão).
- [ ] Verificar que existem `_run{1..7}` por cenário (armadilha nº8: save do último run).
- [ ] Só depois: integrar na tese (`sec:res_novelty` + QI6) **se** o pré-registo passar.

## P2 — Consolidação do repositório (fazer cedo, NÃO a 14 set)

Estado a 15 jul (verificado com `git cherry` / `rev-list`):
- `feat/novelty-search` = branch de trabalho, tem TODA a tese final (72 commits à frente
  de `origin/main`; `main` é ancestral estrito → fast-forward possível).
- `tese-final-graficos` local tem **3 commits exclusivos** (`e7ea0a8`, `9d4a1df`,
  `14085ff` — galeria do dashboard com pesquisa/A-B + gráficos por-cenário exportados
  para a tese) que NÃO estão em `feat/novelty-search`. Não perder.

- [x] ~~Passos 1-3~~ **RESOLVIDO de outra forma a 15 jul (PC do trabalho)** — ver o log de
      sessão no topo: `main` avançada por ff até à tese final; os 3 commits da galeria
      ficaram no backup `backup/tese-final-graficos-15jul2026` por DECISÃO (não integrados);
      branches antigas preservadas como `backup/*` no GitHub. P2 fechado.
- [x] **Apagado `launcher_dashboard.py` (16 jul)** — substituído pela vista «Ao vivo (3D)»
      do dashboard; README atualizado (`python -m dashboard.app` / `iniciar_dashboard.bat`).

## P3 — Entregáveis e reprodutibilidade

- [x] **`docs/REPRODUZIR.md` CRIADO (15 jul)** — mapa "resultado da tese → dados → script",
      com nota de onde vivem os dados (torre vs PC), pipeline de reprodução e armadilhas.
      **2 itens da auditoria já VERIFICADOS aqui** (dados no PC): SLR (883/680/58 batem com
      `screening.csv`) e Sscale (retenções 90/88/78/39% + 28/28 a 100% batem com
      `escalabilidade_*.csv`). **Parte da torre FEITA (16 jul)**: `tab:res_eval` (21/21 células;
      3 dp mal arredondados corrigidos no `main.tex`), `tab:res_signif` (21/21 linhas) e
      §res_novelty (p e δ recalculados de raiz) — tudo confere. Pendente menor: trazer do
      servidor o CSV do braço Novelty preliminar (81,3) de `~/swarm-novelty` (ver REPRODUZIR.md).
- [ ] **Revisão ponta-a-ponta da tese** (consistência número-texto-figura): fazer por
      capítulos, com os CSVs abertos ao lado. Cuidado especial: números antigos que
      sobreviveram a reescritas (73,3 / 67,7 / 0,77 são de campanhas pré-treino_fds).
- [ ] **Artigo**: decidir com o orientador o alvo (conferência vs submissão interna) —
      deadlines externos condicionam tudo o resto. Título: recomendação já feita
      (opção 1 do anexo da `PROPOSTA_TREINO_FINAL.md`).
- [ ] **Draft cedo ao orientador**: enviar a versão pós-campanha-adaptativa (fim de
      julho), não esperar por 15 set.
- [ ] Preparação da defesa (setembro): slides + modo Demo do dashboard (F4, único
      pedaço do dashboard por fazer).

## Opcional (só se sobrar tempo de servidor E o utilizador pedir)

- Ablação de observação no Muro em U: LiDAR 8→16 raios, 7 runs @195min. Testa
  diretamente a hipótese "deceção sob observabilidade parcial". Se mais sensação local
  não ajudar, reforça que o problema é descoberta (legitima o Novelty). Cortar primeiro.

## O que NÃO fazer (decisões já tomadas — não reabrir)

- ❌ Repetir a campanha 7×7 com mais runs (~28 dias de GNN; retorno ≈ 0).
- ❌ Política de atenção por gradiente em SB3 (risco de 3 semanas sem convergir —
  fica como trabalho futuro, já declarado na tese como limitação nº1).
- ❌ Reescrever secções da tese que estão fechadas e coerentes com os dados finais,
  a menos que P0 (Iskandar) ou P1 (adaptativo) o exijam.
- ❌ Editar `main.tex` com números de treino (armadilha nº3) ou de evals desfasados
  dos modelos (armadilha do CSV da mesma data).
- ❌ `Set-Content`/`Out-File` PS5.1 em YAMLs (BOM parte-os) — usar a ferramenta Edit.

## Verificação de cada sessão de trabalho

Antes de dar qualquer tarefa por concluída:
1. A tese compila? (`pdflatex -interaction=nonstopmode main.tex` ×2 em `Tese/`;
   `biber main` se o `.bib` mudou; 0 referências indefinidas.)
2. Os números citados batem com o CSV fonte? (indicar qual.)
3. O que mudou está commitado com mensagem em PT descritiva, no branch certo?
4. Atualizar as checkboxes DESTE ficheiro e a secção "ESTADO" do `PLANO_DE_ATAQUE.md`
   com a data.

## Calendário-alvo

| Janela | Foco |
|---|---|
| 15-19 jul | P0 (Iskandar/NEAT) + P2 passo 1 (branches) + pré-registo P1 |
| 19-25 jul | P1 (chegada da campanha adaptativa, análise, integração se passar) |
| 26 jul - 8 ago | P3 (REPRODUZIR.md + revisão ponta-a-ponta) + draft ao orientador |
| ago | Ciclos de revisão com o orientador; artigo fechado; alvo decidido |
| 1-15 set | Só polimento (refs, acrónimos, normas ISCTE, listas) + buffer |
| set/out | Defesa: slides + modo Demo (F4) |

Buffer real: ~2 semanas. Se algo derrapar, corta pela ordem: Opcional → F4 fancy →
profundidade da revisão do artigo. A tese composta a 15 set é inegociável.
