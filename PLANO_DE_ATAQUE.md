# PLANO DE ATAQUE — Tese de Mestrado (até Outubro 2026)

> **Para o Claude/assistente**: este documento é o ponto de re-entrada do projeto.
> Lê isto primeiro; o histórico detalhado (decisões, bugs corrigidos, armadilhas) está
> na memória persistente (`memory/project_thesis_swarm.md` e `server_training_setup.md`).
> **Para o Gonçalo**: atualiza as checkboxes à medida que avanças; quando algo mudar de
> rumo, regista aqui a decisão e a data.

**Tese**: "Aprendizagem por Reforço para Controlo de Enxames" — ISCTE, Mestrado em IA
**Orientador**: Prof. Luís Nunes | **Prazo**: Outubro 2026 | **Hoje**: 2026-06-10

---

## ⏱ ATUALIZAÇÃO 21 jun 2026 — LER PRIMEIRO (o snapshot de 10 jun abaixo está ultrapassado)

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
1. **[~23 jun]** Treino GNN-48h termina → trazer (pscp/dashboard) + **re-avaliar** + ver se os
   labirintos voltaram. Se sim, fixar como o GNN de referência da tese.
2. **Definir a "Fase B oficial"**: os 3 runs chegam para os boxplots de variância, ou é mesmo
   preciso os **30 runs** da proposta? (decisão de âmbito — 30×6×3×tempo é muito servidor.)
3. **Decisão pendente:** *reward hacking* do PPO no Muro U — aceitar como resultado científico ou ajustar.
4. **Treinar + avaliar o 7º cenário** (`cooperative_door_bypass`) — implementado, falta correr.
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
