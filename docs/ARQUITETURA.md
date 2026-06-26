# Arquitetura do sistema

Documento de apoio ao capítulo de Implementação da dissertação. Descreve o fluxo
**dados → treino → avaliação → análise** e como os módulos se ligam. (O detalhe de
hiperparâmetros está em `configs/foraging.yaml`; o detalhe de uso está no `README.md`.)

## Visão geral

O sistema tem quatro estágios encadeados, todos parametrizados por um único ficheiro
de configuração (`configs/foraging.yaml`) e orquestrados pelo dashboard:

```
┌─────────────────────┐
│  configs/           │   Fonte única de verdade: ambiente, física, recompensas,
│  foraging.yaml      │   hiperparâmetros (evolution/ppo/sac), plotting, visualização.
└──────────┬──────────┘
           │ (lido por todos os estágios)
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. AMBIENTE                                                              │
│  src/environment/swarm_env_3d.py   Ambiente Gymnasium (física, LiDAR,     │
│                                    recompensas, falhas de agentes).        │
│  src/scenarios.py                  6+1 cenários (muros, gargalo, salas,    │
│                                    portas/perceção cooperativas) + labels. │
└──────────┬──────────────────────────────────────────────────────────────┘
           │ observações / recompensas
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. TREINO  (3 controladores descentralizados, parameter sharing)        │
│  src/training/evo_trainer_3d.py    GNN — neuro-evolução (ES + atenção QKV) │
│  src/training/train_ppo_3d.py      PPO — stable-baselines3 (on-policy)     │
│  src/training/train_sac_3d.py      SAC — stable-baselines3 (off-policy)    │
│  src/agents/gnn_agent_3d.py        Política GNN (atenção sobre vizinhos)   │
│                                                                           │
│  Saídas:  results/models{,_ppo,_sac}/   pesos treinados (.pth / .zip)      │
│           results/logs{,_ppo,_sac}/     histórico de treino (CSV)          │
└──────────┬──────────────────────────────────────────────────────────────┘
           │ modelos treinados
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. AVALIAÇÃO  (determinística, emparelhada por seeds)                    │
│  scripts/run_eval.py        1 algoritmo × 1 cenário (+ --fail-frac → Rrobust)│
│  scripts/eval_all.py        os 3 algoritmos no mesmo cenário              │
│  scripts/eval_scalability.py  Sscale: transferência zero-shot N∈{10..100} │
│  scripts/statistical_tests.py Mann-Whitney / t de Welch + tabela LaTeX    │
│                                                                           │
│  Saídas:  results/evaluation/   eval_summary.csv (fonte de verdade),       │
│                                 eval_{algo}_{cen}[_fail10].csv             │
│           results/estatisticas/ escalabilidade_*.csv, significância_*.csv  │
└──────────┬──────────────────────────────────────────────────────────────┘
           │ CSVs de métricas
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. ANÁLISE / APRESENTAÇÃO                                                │
│  scripts/plot_results.py    gráficos da tese (curvas, boxplots, barras)   │
│  scripts/heatmaps.py        heatmaps de ocupação / geodésicos             │
│  scripts/plot_robustez.py   gráfico Rrobust (base vs 10% falhas)          │
│  dashboard/  (NiceGUI)      Mission Control — vê e compara tudo ao vivo    │
│                                                                           │
│  Saídas:  results/graficos_tese/<sessão>/  PNGs + GIFs por sessão         │
│           Tese/images/resultados/          imagens exportadas para a tese  │
└───────────────────────────────────────────────────────────────────────────┘
```

## As três métricas da tese

| Métrica | O que mede | Estágio / artefacto |
|---------|------------|---------------------|
| **Ptask** | Taxa de conclusão da missão (sucesso, recolhas/ep) | `eval_summary.csv` → vista *Ciência* |
| **Rrobust** | Resiliência a falha de 10% dos agentes a meio do episódio | `run_eval.py --fail-frac 0.1` → `eval_*_fail10.csv` → vista *Ciência* |
| **Sscale** | Transferência zero-shot para N≠20 sem retreino | `eval_scalability.py` → `escalabilidade_*.csv` → vista *Ciência* |

> **Nota arquitetural (Sscale):** só a GNN é invariante ao número de agentes (agrega
> vizinhos por atenção). PPO/SAC usam MLP de entrada fixa e são incompatíveis com
> N≠20 — registado como evidência empírica da vantagem de escala da GNN.

## Dashboard (`dashboard/`)

Aplicação NiceGUI (`python -m dashboard.app`, porta 8080). Não treina nem avalia: é
uma camada de **orquestração e leitura** sobre os scripts em `scripts/`.

```
dashboard/
  app.py            Entrypoint: header, barra lateral (OPERAÇÃO/ANÁLISE), tema escuro.
  config.py         Fonte única: cenários, algoritmos, cores, labels, caminhos.
  data.py           Leitura/agregação dos CSVs (eval_summary, fail10, escalabilidade…).
  jobs.py           Fila de treino assíncrona (independente do estado do browser).
  remote.py         Ligação ao servidor de treino (ISCTE).
  views/
    treinar.py      Lançar treinos / Rotina Noturna.
    servidor.py     Estado do servidor remoto.
    curvas.py       Curvas de treino ao vivo (Monitorizar).
    ciencia.py      Estado científico: matriz Ptask, significância, Rrobust, Sscale.
    resultados.py   Galeria de gráficos, comparação A/B, exportar para a tese.
    videos.py       GIFs dos episódios por algoritmo/cenário.
```

**Princípio de design:** `dashboard/config.py` e `dashboard/data.py` são a *única*
fonte de constantes (cenários, labels, cores) e de leitura de resultados; as vistas só
desenham. Isto evita divergências entre vistas (ex.: labels de cenário) e mantém o
dashboard sempre coerente com os CSVs mais recentes produzidos pelos scripts.

## Convenção de nomes dos modelos

O cenário Sandbox (`none`) é guardado **sem** sufixo (`gnn_3d_best.pth`,
`ppo_3d_final.zip`, `sac_3d_final.zip`); os restantes com `_{cenário}`
(ex.: `ppo_3d_final_four_rooms.zip`). Cada algoritmo tem as suas pastas:
GNN em `results/{models,logs}/`, PPO em `results/{models_ppo,logs_ppo}/`,
SAC em `results/{models_sac,logs_sac}/`.
</content>
</invoke>
