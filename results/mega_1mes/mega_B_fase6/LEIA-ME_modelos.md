# mega_B_fase6 (SAC · Gargalo) — os modelos desta fase não existem

A pasta `models/` desta fase contém `gnn_3d_best*.pth` e **nenhum `.zip` do
SAC**. Os ficheiros que lá estão são de outras fases do stream B (o
`gnn_3d_best_cooperative_door.pth` tem o mesmo sha256 nas fases 5, 6 e 7): o
arquivamento entre fases copia `results/models` — a pasta do GNN, que fica
intocada quando a fase treina SAC.

Ficam onde estão (ao contrário das fases A3/A4, cuja pasta foi apagada) porque
aqui não induzem em erro no visualizador: esta fase não aparece no seletor do
«Ao vivo (3D)», precisamente por não ter modelos próprios.

**Os resultados NÃO são afetados.** As médias e as contagens vêm de
`evaluation/eval_by_run.csv`, produzido no servidor no fim do treino com o
modelo certo em memória.

O que se perde é rever este SAC a mexer ou re-avaliá-lo sem retreinar.
