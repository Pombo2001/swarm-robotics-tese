# Avanço do GNN: fitness de *homing* (28–29 jun 2026)

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

A narrativa atual do `main.tex` assenta no GNN a colapsar nos labirintos via `tanh`
saturada. Com o homing, isto inverte-se parcialmente. Sítios a rever (linhas de 29 jun):

- **Eq. 434 / `eq:fitness`** — substituir `β·tanh(R̄/β)` por `5000·homing`; reescrever o
  parágrafo de justificação (o argumento da `tanh` monótona deixa de se aplicar; passa a
  ser o argumento do *homing não-farmável* vs *farming de shaping*).
- **§1112** — "GNN falha 0% nos três cenários com gargalos" → atualizar com os cenários
  que passam a comer (u_wall, four_rooms, cooperative_door, e bottleneck se fechar).
- **§1185** (curvas) e **§1255** (visão global) — "GNN estagna / colapsa nos gargalos".
- **§1437 "Anatomia do colapso evolutivo"** — a explicação via `tanh` saturada deixa de
  ser exata; reformular: o colapso era da *escolha de fitness* (shaping farmável), não
  intrínseco à neuroevolução. Manter o argumento do credit-assignment para o que RESISTE
  (bypass, e bottleneck se ficar a 0).
- **§1453 (Conclusões)** — "controlador evolutivo colapsa nos cenários de gargalo".
- **Inconsistência paralela:** a tese diz "seis cenários" mas o projeto tem 7
  (cooperative_door_bypass). Alinhar quando se reescrever (ver memória `scenarios-fonte-unica`).

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
