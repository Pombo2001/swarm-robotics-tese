# Vitrine da defesa — que treinos mostrar, e porquê

> Escrito a **31 jul 2026**, depois de as campanhas todas passarem a ter figuras
> (`scripts/figuras_campanha.py`). Isto **não** substitui o arquivo: as 25
> campanhas exploratórias continuam lá e continuam a poder ser abertas. Isto diz
> o que se mostra **numa sala, com o relógio a andar**.

## A regra de seleção (a mesma para os três algoritmos)

Mostrar tudo é o mesmo que não mostrar nada, mas escolher os melhores treinos é
um convite a uma pergunta má na defesa. A regra, escrita antes de escolher:

1. **A unidade é a campanha, nunca a execução.** Nada de "o melhor run do GNN":
   mostra-se a distribuição das execuções (dot plot), com a média marcada e a
   contagem `n/N a 100%` visível. Se um algoritmo é mau, vê-se que é mau.
2. **Quando os três correram, aparecem os três.** Um cenário onde o SAC colapsa
   não perde o SAC da figura — é o colapso que é o resultado.
3. **Métrica comparável, sempre:** recolhas por episódio em avaliação
   determinística. A *fitness* evolutiva nunca vai ao lado da recompensa do
   PPO/SAC no mesmo eixo (escalas diferentes, grandezas diferentes).
4. **Cinco cenários, escolhidos para cobrir os quatro desfechos possíveis** —
   vitória, derrota, empate e falha geral. Não os cinco melhores.

## O retrato principal — campanha de 7 dias (`final_7d`)

n = 7 execuções por algoritmo × 7 cenários × 20 episódios.

| cenário | figura | porque está aqui |
|---|---|---|
| Porta Cooperativa | `dotplot_eval_cooperative_door.png` | **vitória limpa** do GNN (69,8 ± 0,9) — o desvio mais pequeno da tese |
| Quatro Salas | `dotplot_eval_four_rooms.png` | **vitória grande**: 59,8 contra 33,6 e 31,8 |
| Sandbox | `dotplot_eval_none.png` | **derrota** do GNN para o PPO (38,3 vs 71,5) — prova que não se escolheu o favorito |
| Gargalo | `dotplot_eval_bottleneck.png` | **empate** GNN/PPO (p=0,21) com o SAC a colapsar |
| Muro em U | `dotplot_eval_u_wall.png` | **ninguém resolve**, e a distribuição é bimodal nos três |

Acompanha: `comparacao_barras_geral.png` (os sete cenários de uma vez) e
`recolhas_por_cenario.png`.

## O remate — o Muro em U com n=28 (mega-treino, fases A1-A4)

É a campanha que responde ao único cenário sem vencedor, e o quadro está
completo: quatro braços, 28 execuções cada, 560 episódios por braço.

| braço | campanha | recolhas/ep | execuções a 100% |
|---|---|---|---|
| GNN, novidade **adaptativa** | `mega_A1` | **67,4** | **28/28** |
| GNN, objetivo puro | `mega_A2` | 32,5 | 15/28 |
| PPO | `mega_A3` | 35,6 | 14/28 |
| SAC | `mega_A4` | 10,1 | 14/28 |

Figura: `mega_A1/dotplot_eval_u_wall.png` ao lado de `mega_A2/…`. Vinte e oito
pontos todos acima de 30 contra uma nuvem partida ao meio — lê-se sem
explicação. **A análise formal segue o pré-registo** (`docs/PRE_REGISTO_MEGATREINO.md`,
M1); estes números são a leitura direta dos CSV, não a substituem.

## Se houver tempo para mais

- **QI6, dosagem adaptativa** — `adaptativo_A1` (Muro em U 68,5, 7/7 a 100%)
  contra `adaptativo_A2` (objetivo puro, 31,5, 4/7). O mesmo mecanismo, à escala
  pequena, antes de o mega-treino existir.
- **Porta com Alternativa a n=21** — `mega_B5`: 80,9 recolhas/ep, **21/21 a
  100%**. É o cenário decetivo, e é o reforço do T4.
- **Mapa grande (QI7)** — o navegador de referência faz 54 recolhas/ep e os três
  algoritmos fazem 0,00. Ver `scripts/sanidade_mapa_grande.py`.

## O que NÃO mostrar

- As 25 sessões de maio/junho: fitness antiga (a "cultivável"), campanhas de 1-3
  execuções, e metade sem gráficos. São arquivo, não são prova.
- Qualquer figura com a **fitness evolutiva** ao lado da recompensa do PPO/SAC.
- `final_7d/boxplot_eval_*` nos cenários bimodais: com n=7 os quartis são ruído
  e a caixa cheia sugere densidade onde não há execução nenhuma. O dot plot
  mostra o mesmo dado sem inventar.
