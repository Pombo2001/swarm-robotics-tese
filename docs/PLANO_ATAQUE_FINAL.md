# PLANO DE ATAQUE FINAL — prompt de execução (15 jul → 15 set 2026)

> **Este documento é um PROMPT para o Claude/Opus.** Lê-o do princípio ao fim antes de
> tocar em qualquer ficheiro. Ele substitui o topo do `PLANO_DE_ATAQUE.md` como lista
> acionável; o `PLANO_DE_ATAQUE.md` continua a ser o registo histórico (armadilhas,
> tutorial do servidor, resultados) e deve ser consultado, não reescrito.
>
> Escrito a **15 jul 2026** com o repositório no branch `feat/novelty-search`
> (HEAD `cb9dcb9`). Se estiveres a ler isto semanas depois, verifica primeiro o que já
> foi feito (checkboxes abaixo + `git log`) e NÃO refaças trabalho fechado.

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
- [ ] Mesmo tratamento para **1 artigo NEAT** citado no Cap. 3 (também só lido por resumo).
- [ ] Contexto: a bibliografia já foi auditada 2× e apanharam-se referências fabricadas
      (ver `memory/bibliografia_auditoria.md`). O padrão a temer é sempre o mesmo:
      afirmação plausível sem fonte real por trás. Na dúvida, verificar contra o PDF.

## P1 — Fecho da campanha adaptativa (~19-20 jul, quando o utilizador trouxer os dados)

**Pré-registo (fazer ANTES de olhar para os resultados — escrever num commit):**
- [ ] Teste: Mann-Whitney exato + δ de Cliff sobre **médias por run (n=7)**,
      adaptativo vs objetivo puro (campanha 7d) e adaptativo vs Novelty fixo w=0.5
      (P1/P2) nos cenários onde estes existem (u_wall, bypass).
- [ ] Critério de sucesso pré-registado: o adaptativo **não degrada** os cenários que o
      objetivo já resolve (δ≈0 nos 5 fáceis) **e** mantém o ganho do fixo no u_wall
      (≥ taxa de convergência do w=0.5, 7/7). Se falhar qualquer metade → fica
      "trabalho futuro com evidência preliminar", e a QI6 NÃO muda.
- [ ] Reportar TODOS os runs; taxa de convergência como descritivo, magnitude como teste
      (n=7 não dá significância em proporções — Fisher 7/7 vs 3/7 dá p=0.070).

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

- [ ] **Passo 1**: trazer os 3 commits para `feat/novelty-search` (merge de
      `tese-final-graficos` ou cherry-pick; mostrar o diff ao utilizador antes —
      tocam em `dashboard/` e `Tese/images/`, pode haver conflitos com a galeria
      reorganizada de 14 jul).
- [ ] **Passo 2**: quando o utilizador aprovar, atualizar `main` (merge/ff de
      `feat/novelty-search`) e push. A partir daí, `main` = fonte de verdade.
- [ ] **Passo 3**: arrumar branches mortas (`backup-main-maio2026` mantém-se; as outras
      apagar só com autorização).
- [ ] Decidir/executar: apagar `launcher_dashboard.py` (substituído pela vista
      «Ao vivo (3D)» do dashboard — decisão já tomada a 14 jul, falta executar).

## P3 — Entregáveis e reprodutibilidade

- [ ] **`docs/REPRODUZIR.md`**: tabela "cada número/figura da tese → CSV/script que o
      gera". Fontes: `scripts/gerar_figuras_7d.py --install-oficial`,
      `results/graficos_tese/final_7d/eval_by_run_7d.csv`,
      `results/estatisticas/escalabilidade_*.csv`, `results/novelty_final/{uwall,bypass}/`,
      `scripts/statistical_tests.py`, `docs/slr/screening.csv` + `scripts/slr_pipeline.py`.
      Ao construí-la, VERIFICAR que cada número da tese bate certo com o CSV — é uma
      auditoria disfarçada de documentação.
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
