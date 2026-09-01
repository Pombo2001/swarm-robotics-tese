"""Média entre runs de curvas de treino — sem a serra.

O problema que isto resolve
Cada run escreve o seu histórico nos SEUS passos: o GNN loga 238-1113 pontos por
run, o PPO 15-23, o SAC 7-11. Depois de normalizar o eixo X para 0-100% do
orçamento, dois runs quase nunca partilham o mesmo x.

O `sns.lineplot(x=..., y=..., errorbar='sd')` agrupa pelos valores EXATOS de x.
Com grelhas desalinhadas, a esmagadora maioria dos x tem um único run — a
linha desenhada não é média nenhuma, é um run de cada vez, e a legenda que diz
"média entre runs, banda = ±1 desvio padrão" está a afirmar o que a figura não
faz. Em cenários com runs bimodais (uns resolvem, outros ficam a zero) o traço
salta entre os dois modos e sai a serra que se vê nas figuras de 16 jul.

A correção: interpolar cada run na MESMA grelha e só depois agregar. Aí cada
ponto da linha é média de n runs e a banda é o desvio entre eles — o que a
legenda sempre prometeu.

Isto já tinha sido corrigido a 21 jul, mas só na figura `desempenho_global_*`
(por bins de 2%, ver gerar_figuras_7d.py). O comentário dessa correção afirma
que "a banda ±sd por run está nos painéis por cenário" — e esses painéis eram
precisamente os que tinham o defeito.

Porquê interpolar em vez de fazer bins
Com bins, um bin onde só 2 dos 7 runs calharam ter pontos produz uma média de 2
runs a seguir a uma de 7 — degraus outra vez, mais pequenos. A interpolação dá
n=7 em todos os pontos da grelha, que é o que torna a banda comparável ao longo
do eixo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def resolucao_grelha(n_pontos_por_run: list[int] | np.ndarray,
                     *, minimo: int = 11, maximo: int = 51) -> int:
    """Quantos pontos deve ter a grelha comum, dada a densidade dos runs.

    Sobre-amostrar não inventa dados (a interpolação é linear entre pontos
    medidos), mas desenhar 51 pontos a partir de runs com 9 sugere uma resolução
    que a medição não tem. Seguimos a mediana dos runs, presa a [minimo, maximo].
    """
    if len(n_pontos_por_run) == 0:
        return minimo
    mediana = int(np.median(np.asarray(n_pontos_por_run, dtype=float)))
    return int(np.clip(mediana, minimo, maximo))


def curva_media_entre_runs(d: pd.DataFrame, *, col_x: str = "TrainingProgress",
                           col_y: str = "Score", col_run: str = "Run",
                           n_grelha: int | None = None,
                           x_min: float = 0.0, x_max: float = 100.0):
    """Média e desvio ENTRE RUNS ao longo de uma grelha comum de x.

    Devolve `(x, media, desvio, n_runs, n_grelha)`. Cada run é interpolado
    linearmente na grelha; runs com um único ponto são ignorados (não definem
    curva). O desvio é populacional entre runs — com n=7 a distinção para o
    amostral é cosmética, mas fica explícita para quem ler a figura.
    """
    if d.empty:
        vazio = np.array([])
        return vazio, vazio, vazio, 0, 0

    runs = [g.sort_values(col_x) for _, g in d.groupby(col_run)]
    runs = [g for g in runs if len(g) >= 2]
    if not runs:
        vazio = np.array([])
        return vazio, vazio, vazio, 0, 0

    if n_grelha is None:
        n_grelha = resolucao_grelha([len(g) for g in runs])

    x = np.linspace(x_min, x_max, n_grelha)
    # `np.interp` prolonga em patamar fora do intervalo de cada run. Como o x já
    # é o progresso normalizado (cada run vai de 0 a 100 por construção), isso só
    # toca nas pontas e não fabrica tendência nenhuma.
    matriz = np.vstack([np.interp(x, g[col_x].to_numpy(dtype=float),
                                  g[col_y].to_numpy(dtype=float)) for g in runs])
    return x, matriz.mean(axis=0), matriz.std(axis=0), len(runs), n_grelha


def desenhar_curva_media(ax, d: pd.DataFrame, *, cor: str, col_y: str = "Score",
                         **kwargs):
    """Desenha no `ax` a linha média entre runs e a banda ±1 desvio.

    A banda é truncada em zero quando nenhum run observou valor negativo: com
    runs bimodais (uns resolvem, outros ficam a zero) o desvio é maior do que a
    média e a banda descia a fitness negativa — uma região que a métrica não pode
    ocupar. Se a métrica admite valores negativos (a recompensa episódica admite,
    por causa do custo de energia), a banda desce à vontade.

    Devolve o número de pontos da grelha usada, para quem quiser dizê-lo na nota
    de rodapé da figura.
    """
    x, media, desvio, n_runs, n_grelha = curva_media_entre_runs(d, col_y=col_y, **kwargs)
    if x.size == 0:
        return 0
    inferior = media - desvio
    if not d.empty and float(d[col_y].min()) >= 0.0:
        inferior = np.maximum(inferior, 0.0)
    ax.fill_between(x, inferior, media + desvio, color=cor, alpha=0.22, linewidth=0)
    ax.plot(x, media, color=cor, linewidth=2.5)
    return n_grelha
