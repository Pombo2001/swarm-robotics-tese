# mega_A_fase3 (PPO) — não há modelos desta fase

A pasta `models/` que aqui esteve **não era desta fase**: continha
`gnn_3d_best*.pth` com o mesmo sha256 dos da `mega_A_fase2` (GNN objetivo).
O arquivamento entre fases copia `results/models` — a pasta do GNN, que fica
intocada quando a fase treina PPO — em vez dos modelos do PPO. Os modelos
do PPO desta fase nunca chegaram a ser guardados (confirmado a 3 ago: também
não estão no servidor).

Apagada a 3 ago para não ser aberta por engano no visualizador: quem
escolhesse "PPO do mega-treino" veria um GNN de outra condição.

**Os resultados NÃO são afetados.** As médias, os desvios e as contagens de
convergência vêm de `evaluation/eval_by_run.csv`, que foi produzido no
servidor no fim do treino, com o modelo certo em memória. É o que a tese cita
(PPO: 35,6 ± 36,0, 14/28) e o que o verificador confere.

O que se perde é a possibilidade de **rever** o PPO desta fase a mexer ou de
o re-avaliar sem retreinar.
