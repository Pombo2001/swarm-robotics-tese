# Aprendizagem por Reforço para Controlo de Enxames

Simulador 3D de *swarm robotics* (forrageamento) e bancada de comparação entre três
controladores descentralizados. Projeto de tese de mestrado em Inteligência Artificial
(ISCTE-IUL).

**Hipótese central:** a inteligência adaptativa (MARL com redes de grafos) supera a
robustez estática (bio-inspirada) em cenários de *stress* dinâmico.

---

## Algoritmos comparados

| Sigla | Ficheiro | Paradigma | Notas |
|-------|----------|-----------|-------|
| **GNN** | `src/training/evo_trainer_3d.py` | Neuro-evolução (Evolution Strategies) | Rede de grafos com atenção QKV sobre vizinhos; mutação Gaussiana com máscara + elitismo. Desenvolvido de raiz. |
| **PPO** | `src/training/train_ppo_3d.py` | RL on-policy (Actor-Critic) | *stable-baselines3*; clipping do ratio de políticas. |
| **SAC** | `src/training/train_sac_3d.py` | RL off-policy (entropia regularizada) | *stable-baselines3*; `ent_coef=0.1` fixo para evitar regressão em treinos longos. |

Os três usam **parameter sharing**: 8 arenas × 20 agentes = 160 "agentes virtuais"
partilham uma única política (`FlattenMultiAgentVecEnv` no PPO/SAC; um genoma avaliado
em paralelo no GNN). A exploração é incentivada **apenas por reward shaping** (não há
ICM/curiosidade intrínseca).

## Cenários (`classic_scenario`)

| Chave | Descrição |
|-------|-----------|
| `none` | Sandbox: arena aberta, ninho e obstáculos móveis. |
| `u_wall` | Muro em U a bloquear o caminho direto ao ninho. |
| `bottleneck` | Duas paredes com passagem estreita de 1,5 m. |
| `four_rooms` | Labirinto de quatro salas com passagens específicas. |
| `cooperative_door` | Porta que só abre com 3 robôs a empurrar em simultâneo. |
| `cooperative_perception` | Alvo móvel capturado quando rodeado por 3+ robôs a 360°. |

---

## Estrutura do projeto

```
configs/foraging.yaml          Configuração única (ambiente, treino, visualização)
dashboard/                     Dashboard NiceGUI (ponto de entrada: python -m dashboard.app)
  app.py / views/ / remote.py  Vistas (Treinar/Servidor/Ciência/Resultados) + ligação ao servidor
launcher_dashboard.py          Launcher CustomTkinter antigo (mantido; migração incremental)
src/
  environment/swarm_env_3d.py  Ambiente Gymnasium (física, LiDAR, recompensas)
  agents/gnn_agent_3d.py       Rede de grafos com atenção (política do GNN)
  training/                    evo_trainer_3d / train_ppo_3d / train_sac_3d
scripts/
  run_experiments.py           Automação de baterias de treino (Rotina Noturna / Tour)
  run_eval.py                  Avaliação determinística de 1 algoritmo (+ Rrobust via --fail-frac)
  eval_all.py                  Avaliação comparativa dos 3 algoritmos
  eval_scalability.py          Sscale: transferência Zero-Shot para N variável
  statistical_tests.py         Testes de significância (Mann-Whitney / t de Welch)
  plot_results.py              Geração dos gráficos da tese
  run_treino24.sh / 48.sh      Lançadores de treino no servidor ISCTE (via tmux)
visualization/
  visualize_{gnn,ppo,sac}.py   Visualizadores 3D Ursina (usados pelo launcher)
  main_visualizer.py           Visualizador 3D unificado (--algo)
tests/                         test_simulation.py (smoke) + test_dashboard_jobs.py
Tese/                          Dissertação LaTeX (main.tex, references.bib, images/)
Artigo/                        Artigo destilado para a dissertação (Elsevier, PT)
docs/                          Documentos de trabalho (plano, respostas, updates de reunião)
results/                       Logs, modelos e gráficos gerados (não versionado)
```

**Convenção de nomes dos modelos:** o Sandbox (`none`) é guardado **sem** sufixo
(`gnn_3d_best.pth`, `ppo_3d_final.zip`, `sac_3d_final.zip`); os restantes cenários com
`_{scenario}` (ex.: `ppo_3d_final_four_rooms.zip`). Cada algoritmo tem as suas pastas:
GNN em `results/{models,logs}/`, PPO em `results/{models_ppo,logs_ppo}/` e
SAC em `results/{models_sac,logs_sac}/`.

---

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Requer Python 3.10+. O treino tira partido de GPU (CUDA) se disponível (`device="auto"`).

## Como usar

### Dashboard (recomendado)

```powershell
python launcher_dashboard.py
```

Permite editar a configuração, treinar cada algoritmo, lançar a **Rotina Noturna**
(treina os 6 cenários × 3 algoritmos distribuindo um orçamento de horas), visualizar
modelos em 3D e gerar os gráficos da tese.

### Linha de comandos

```powershell
# Treino individual (minutos)
python src/training/train_ppo_3d.py --time_limit 30
python src/training/evo_trainer_3d.py --time_limit 30

# Bateria de experiências (vários runs / cenários)
python scripts/run_experiments.py --runs 5 --time 60 --time-ppo 84 --time-gnn 84

# Avaliação determinística
python scripts/run_eval.py --algo ppo --episodes 20 --scenario four_rooms
python scripts/eval_all.py --episodes 20 --scenario none

# Visualização 3D
python visualization/main_visualizer.py --algo sac

# Gráficos da tese
python scripts/plot_results.py

# Smoke test
python tests/test_simulation.py
```

O cenário ativo é o `classic_scenario` em `configs/foraging.yaml` (alterável pelo
dashboard ou por `--scenario` nos scripts de avaliação).

---

## Análise para a tese (métricas Ptask, Rrobust, Sscale)

As três métricas definidas na proposta têm suporte direto:

| Métrica | O que mede | Como obter |
|---------|-----------|------------|
| **Ptask** | Taxa de conclusão da missão | `eval_all.py` → `success` / `food_collected` por episódio |
| **Rrobust** | Resiliência à falha de 10% dos agentes a meio do episódio | `run_eval.py --fail-frac 0.1` (comparar com `--fail-frac 0.0`) |
| **Sscale** | Transferência Zero-Shot para N∈{10,20,50,100} sem retreino | `eval_scalability.py` |

A **significância estatística** entre algoritmos obtém-se com `statistical_tests.py`,
que opera sobre a métrica de tarefa da avaliação (comparável entre algoritmos, ao
contrário da recompensa de treino) e gera tabela CSV + LaTeX.

### Reproduzir os resultados da tese

```powershell
# 1. Treinar (30 runs por cenário, via dashboard "Rotina Noturna" ou CLI)
python scripts/run_experiments.py --runs 30 --time 60

# 2. Avaliar cada cenário (>=30 episódios para os testes terem poder estatístico)
foreach ($s in "none","u_wall","bottleneck","four_rooms","cooperative_door","cooperative_perception") {
    python scripts/eval_all.py --episodes 30 --scenario $s --no-pause
}

# 3. Testes de significância (Mann-Whitney / t de Welch)
python scripts/statistical_tests.py --metric food_collected

# 4. Resiliência (Rrobust): baseline vs 10% de falhas
python scripts/run_eval.py --algo sac --scenario none --episodes 30
python scripts/run_eval.py --algo sac --scenario none --episodes 30 --fail-frac 0.1

# 5. Escalabilidade Zero-Shot (Sscale)
python scripts/eval_scalability.py --scenario none --sizes 10,20,50,100 --episodes 30

# 6. Gráficos finais
python scripts/plot_results.py
```

> **Nota arquitetural (Sscale):** só a **GNN** é invariante ao número de agentes
> (agrega vizinhos por atenção). O PPO e o SAC usam uma MLP de entrada fixa, pelo que
> são incompatíveis com N≠20 — o `eval_scalability.py` deteta e regista isto como
> evidência empírica da vantagem de escalabilidade da GNN.

---

## Modelo de observação e recompensa

**Observação por agente** (`12 + (N−1)×5` valores):
direção egocêntrica + distância ao ninho (bússola de *homing* sempre ativa) · 8 raios
LiDAR (alcance 5 m, deteta paredes e obstáculos) · por cada vizinho: direção (3) +
distância (1) + estado de sinalização (1).

**Recompensa** = *progress shaping* (aproximar-se do ninho) + custo de energia
(−0,05/passo) + bónus de exploração *count-based* (células novas) − penalizações
(colisão, aglomeração fora de zonas de cooperação) + recompensa de tarefa pura
(+100 quando `required_to_eat` agentes chegam ao ninho). A métrica reportada separa
*task reward* (recolhas × 100, sem shaping) da recompensa total — para comparar treino
com avaliação.

## Configuração

Todos os hiperparâmetros estão em `configs/foraging.yaml`, divididos em secções:
`environment`, `physics`, `rewards`, `evolution` (GNN), `ppo`, `sac`, `plotting`,
`visualization` e `simulation`. Os scripts de treino reescrevem a chave
`classic_scenario` consoante o cenário em curso.
