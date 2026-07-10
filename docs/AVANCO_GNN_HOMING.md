# Avanço do GNN: fitness de *homing* (28–29 jun 2026)

> ✅ **CONCLUÍDO E SUPERADO (10 jul 2026).** O plano de reescrita descrito abaixo foi
> executado: a tese e o artigo já refletem a campanha final de 7 dias. Os **números
> deste documento são de 29 jun** (treino de 3 dias) e ficaram desatualizados — os
> definitivos estão em `docs/PLANO_DE_ATAQUE.md` (secção "RESULTADOS FINAIS") e em
> `results/graficos_tese/final_7d/`. Mantém-se como registo do avanço metodológico,
> que continua válido: a *fitness* de homing é a que está em produção.

> Documento de trabalho. Regista o avanço metodológico (estável) e o **plano de
> reescrita da tese**, a executar **só quando o treino de 3 dias (`train3d`) terminar**
> e os resultados finais (eval + testes estatísticos) existirem. Ver memória
> `gnn-homing-fitness` e `server-training-setup`.

## 1. O que mudou (metodologia — estável, já no código)

A *fitness* do GNN evolutivo deixou de usar o **reward acumulado comprimido por `tanh`**
e passou a usar **homing** (proximidade FINAL ao ninho):

```
fitness = avg_food · 10000 + 5000 · avg_homing
homing  = média_episódios( média_agentes( clip((Φ_inicial − Φ_final)/Φ_inicial, 0, 1) ) )
```

- `Φ` = potencial **geodésico** ao ninho (`env._potential`, contorna paredes).
- `Φ_inicial` = `env.prev_pot` logo após `reset`; `Φ_final` = potencial de cada agente no fim.
- **Não-farmável**: só conta os extremos (início vs fim), não o caminho → vaguear a
  explorar não aumenta a fitness. Resolve o *farming de shaping* da versão `tanh`.
- Commits: `03e87bd` (de-saturação, intermédio) → `922f143` (homing, definitivo).
- Também: `sigma_min 0.01→0.03`, `sigma_decay 0.995→0.999` (exploração viva).

### Revisão de código (922f143) — veredicto: sólido, sem bugs
- `start_pot` capturado com `.copy()` após o reset → sem aliasing (`prev_pot` é mutado).
- `_potential` devolve `euclidiana + 2·R` em células bloqueadas → `frac` nunca dá NaN; `clip[0,1]`.
- Coerência: homing é geodésico; comer (linha 801) é euclidiano ao ninho. Φ_geo→0 ⇒ euclidiana→0.
- **Nota cosmética (não-bug):** após comer, o agente respawna a sul → termina longe → puxa
  o homing médio para baixo. Por isso cenários que comem muito têm homing baixo (ver §2).
  Irrelevante para a seleção porque `food·10000 ≫ 5000·homing`.

## 2. Resultados da VALIDAÇÃO (curta: 35 min, 1 seed) — `val_verdict.txt` 29 jun 00:31

Como `fitness = food·10000 + 5000·homing`, com `food=0` ⇒ `homing = fitness/5000`:

| Cenário | fitness | food | homing implícito | Leitura |
|---|---|---|---|---|
| four_rooms | 138062 | 13.75 | ~0.11* | come muito (*homing baixo = respawna longe após comer) |
| cooperative_door | 124840 | 12.25 | ~0.47 | come bem |
| **bottleneck** | 4280 | 0 | **0.86** | atravessa o túnel quase todo; falta consolidar a recolha |
| **bypass** | 3064 | 0 | **0.61** | chega a ~60% do caminho; não fecha |

**+ u_wall (validado antes, 922f143):** Gen 13 1ª recolha → Gen 22 = 7.25 recolhas/ep.

### Diagnóstico bottleneck/bypass
- **bottleneck — provavelmente NÃO está perdido.** homing 0.86 = os agentes já atravessam
  o túnel de 8m (LiDAR de 8m vê até à saída) e chegam perto do ninho; falta consolidar a
  recolha. Mesmo padrão do u_wall (homing sobe primeiro, comida vem depois). A validação
  foi só 35 min/1 seed; o `train3d` dá 195 min × 3 runs (~5.6×) → boa hipótese de fechar.
  **Confirmar pelo CSV quando o train3d chegar ao bottleneck (3º cenário).**
- **bypass — o caso genuinamente difícil.** homing 0.61 + `required_to_eat=3` (cooperação)
  + percurso alternativo (defletor em y=8) **sem bússola** (a bússola da porta aponta para a
  porta curta, não para o desvio). Tarefa mais composta de todas; pode ficar a 0 — e isso é
  um resultado honesto (limitação da neuroevolução de fitness-de-episódio vs. credit
  assignment temporal do PPO/SAC).

## 3. PLANO DE REESCRITA DA TESE (executar só com resultados finais)

> **DECISÃO NARRATIVA (29 jun, utilizador):** adotar a **história do diagnóstico+cura**.
> Não esconder os resultados antigos: contá-los como *patologias diagnosticadas e
> corrigidas*. Isto transforma DUAS inconsistências num **contributo metodológico** e
> preserva os achados citáveis (reward hacking do PPO, fitness exploitation do GNN),
> agora com a respetiva correção e os resultados recuperados.

### 3.0 IMPORTANTE — são DUAS atualizações que interagem, não uma

A revisão de 29 jun (sobre o `main.tex` atual, 1638 linhas) confirmou que **nenhum**
resultado novo está na tese: os números (Sandbox 73,3; Porta Coop 67,7; GNN 0,77/2,63)
são de uma campanha **anterior** ao `treino_fds`. Há duas narrativas desatualizadas:

| Pilar atual da tese | Resultado final (treino_fds + train3d) |
|---|---|
| PPO "frágil" → falha Muro U por *reward hacking* (0%) | PPO faz Muro U **100%** — *reward hacking* **curado** |
| GNN "colapsa" em todos os gargalos (*fitness exploitation*) | GNN come em ≥3 labirintos; só bypass (e talvez bottleneck) resiste |

Confirmado: PPO/SAC (treino_fds) e GNN (train3d) usam **a mesma recompensa** (food 300)
→ comparação final metodologicamente limpa. O *trade-off* central (gradiente domina a
tarefa, grafo domina a escala *Zero-Shot*) **sobrevive**, mas atenua-se: PPO≈SAC na
tarefa e o "colapso" do GNN encolhe para o bypass.

### 3.1 Arco narrativo "diagnóstico + cura" (a tecer na Metodologia + Discussão)

Duas patologias da estrutura de recompensa/fitness — **não dos algoritmos** — foram
diagnosticadas e corrigidas:

1. **PPO — reward hacking no Muro U (recompensa v1).** O bónus de exploração
   *count-based* (`+2.0`/célula) dominava a recompensa esparsa de tarefa: a política
   maximizava-o vagueando pelo beco (recompensa recorde ≈132 mil, 0 recolhas).
   **Cura (recompensa simplificada, Prof. Nunes):** exploração `2.0→0.5`, comida
   `100→300`, dispersão e penalização de obstáculo `→0`, `required_to_eat=1` nos
   labirintos de navegação. A comida passa a dominar o shaping → PPO resolve Muro U (0→100%).
2. **GNN — fitness exploitation (fitness v1).** A fitness `f·10000 + β·tanh(R̄/β)`
   saturava (`tanh≈1`, planalto) quando nenhum genoma comia → seleção cega → colapso em
   todos os labirintos. **Cura (fitness de homing, §1):** `f·10000 + 5000·homing`,
   não-farmável → seleciona a pré-condição de comer → GNN come em ≥3 labirintos.

O argumento do **credit-assignment temporal** (neuroevolução fitness-de-episódio vs.
gradiente) deixa de explicar o "colapso geral" e **reserva-se para o que RESISTE** —
o bypass (e bottleneck se ficar a 0): tarefa composta (desvio sem bússola +
`required_to_eat=3`) que a evolução de escalar-por-episódio genuinamente não fecha.

### 3.2 Sítios a editar no `main.tex` (linhas confirmadas em 29 jun)

**A) Recompensa/fitness — descrever a versão FINAL na Metodologia:**
- **§975** progresso `10.0` ✅ (bate com config) — não mexer.
- **§976 exploração** — tese diz `+2.0`; config final = **`0.5`**. Atualizar valor.
- **§977 dispersão** — tese diz `-1.5` anti-clustering; config final = **`0.0`
  (desligada)**. Reescrever (a física de separação mantém-se; só o *sinal de recompensa*
  saiu). Mencionar `obstacle_penalty=0` também.
- **food_collected** — atualizar para `300` onde for citado.
- **Eq. `eq:fitness` (434–437)** — substituir `β·tanh(R̄/β)` por `5000·homing`; reescrever
  a justificação (cai o argumento da `tanh` monótona; entra o *homing não-farmável* vs
  *farming de shaping*). Definir homing = `clip((Φ_ini−Φ_fin)/Φ_ini,0,1)`, Φ geodésico.

**B) Resultados/Discussão — narrar diagnóstico+cura e reportar v2:**
- **§1110** — PPO "colapsa 0% no Muro U / reward hacking": reframe como **diagnóstico**
  (recompensa v1) + resultado final curado (v2, 100%). Atualizar os números (73,3 etc.)
  pelos do `eval_summary.csv` final.
- **§1112** — "GNN falha 0% nos três gargalos": atualizar com os que passam a comer
  (u_wall, four_rooms, cooperative_door [+ bottleneck se fechar]); manter o caso que resiste.
- **§1185 (curvas)** — "GNN estagna" + "PPO reward hacking no Muro U": atualizar ambos.
- **§1255 (visão global, três perfis)** — reescrever perfis do PPO (já não frágil ao
  Muro U) e do GNN (resolve vários labirintos; resiste no bypass).
- **§1401 (desempenho de tarefa)** — "SAC 6, PPO 5 falha Muro U, GNN colapsa" →
  atualizar (PPO/SAC resolvem os 7; GNN come em ≥3, resiste no bypass).
- **§1437 "Anatomia do colapso evolutivo"** — reformular para **diagnóstico+cura**: o
  colapso era da *escolha de fitness* (shaping farmável + tanh saturada), curado pelo
  homing; o credit-assignment explica só o residual (bypass).

**C) Conclusões e Resumos:**
- **§1453 (Conclusões)** — "PPO falha Muro U por reward hacking; GNN colapsa nos
  gargalos": reescrever para o quadro curado + o *trade-off* na escala (que se mantém).
- **§300 (Resumo PT) / §306 (Abstract EN)** — "SAC resolve os seis cenários": passar a 7
  e mencionar PPO; reafirmar o *trade-off* na escala (núcleo intacto).

**D) Contagem de cenários (6 vs 7):**
- **§919, §929 (fig 3D), §941 (fig planta)** — "seis cenários" + figuras com 6. O
  projeto tem 7 (`cooperative_door_bypass`). DECISÃO pendente: incluir o bypass como 7º
  (exige render em `scripts/render_maps.py` + nova figura) ou mantê-lo só nos resultados.
  Ver memória `scenarios-fonte-unica`.

## 4. Pendente (pós-train3d) — pipeline já preparado

O `train3d` (run_experiments) JÁ gera automaticamente no fim: `eval_suite` (3 algos × 7
cenários, 20 ep) + `plot_results` + vídeos. **Falta só** a estatística e a escalabilidade,
empacotadas em **`scripts/analise_pos_treino.sh`** (portável Linux/Windows-GitBash):

1. Trazer `results/` do servidor com pscp (ou correr o script no servidor logo após o train3d).
2. `bash scripts/analise_pos_treino.sh` — corre:
   - `eval_suite --episodes 30` (re-avalia com amostra robusta p/ estatística),
   - `statistical_tests` food_collected + success → CSV **+ tabela `.tex`** em `results/estatisticas/`,
   - `eval_scalability` (zero-shot N∈{10,20,50,100}, GNN invariante).
3. Copiar PNGs de `results/evaluation/` + `results/graficos_tese/<sessao>/` → `Tese/images/resultados/`.
4. Executar o plano de reescrita acima (secção 3); colar as tabelas `.tex` da estatística.

## 4. Pendente (pós-train3d) — pipeline já preparado

O `train3d` (run_experiments) JÁ gera automaticamente no fim: `eval_suite` (3 algos × 7
cenários, 20 ep) + `plot_results` + vídeos. **Falta só** a estatística e a escalabilidade,
empacotadas em **`scripts/analise_pos_treino.sh`** (portável Linux/Windows-GitBash):

1. Trazer `results/` do servidor com pscp (ou correr o script no servidor logo após o train3d).
2. `bash scripts/analise_pos_treino.sh` — corre:
   - `eval_suite --episodes 30` (re-avalia com amostra robusta p/ estatística),
   - `statistical_tests` food_collected + success → CSV **+ tabela `.tex`** em `results/estatisticas/`,
   - `eval_scalability` (zero-shot N∈{10,20,50,100}, GNN invariante).
3. Copiar PNGs de `results/evaluation/` + `results/graficos_tese/<sessao>/` → `Tese/images/resultados/`.
4. Executar o plano de reescrita acima (secção 3); colar as tabelas `.tex` da estatística.
