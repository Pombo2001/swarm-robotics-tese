# Dados do MAPA GRANDE — atualizado a 2 ago 2026

> **Estes CSV estão VERSIONADOS de propósito**, ao contrário do resto de
> `results/`, que o `.gitignore` exclui. São a única cópia destes resultados: o
> precedente é o braço Novelty preliminar, cujos artefactos foram sobrescritos no
> servidor e hoje são o único número da tese sem fonte reproduzível. Adicionados
> com `git add -f`.
>
> Os **modelos** continuam fora do git (são 106 MB) — ver abaixo onde estão.

## ⚠️ Há DUAS pastas de F1, e só uma vale

| pasta | mundo | vale |
|---|---|---|
| `f1_zeroshot/` | `env_hash 267a7b547aed` — paredes de 30 m numa arena de raio 60: **45 m de céu aberto**, os agentes voavam por cima do labirinto | ⛔ **ANULADO a 29 jul.** Nenhum número, incluindo o veredicto. Ver `f1_zeroshot/ANULADO_29jul.md` |
| **`f1_zeroshot_v2/`** | `env_hash e930abe4d992` — paredes a `2×arena_radius` (`4b8a26a`) **e** teto de ±2 m em z (emenda 17) | ✅ **é o F1** |

A pasta anulada fica no repositório de propósito: é a prova documental de uma
campanha descartada, e apagá-la deixaria o `ANULADO_29jul.md` a falar de
ficheiros que não existem. **Não citar nada de lá.**

## O que está aqui

| Ficheiro | O que é | Vale como |
|---|---|---|
| `f1_zeroshot_v2/zeroshot_natural.csv` | **F1 — condição NATURAL**: 21 células (7 cenários de origem × 3 algoritmos) × 20 episódios = **420 episódios** | **resultado**, condição principal do pré-registo |
| `f1_zeroshot_v2/zeroshot_c1_escala.csv` | F1 — controlo **escala da observação** (`--norm-obs treino`), 420 ep | controlo |
| `f1_zeroshot_v2/zeroshot_c2_sem_obstaculos.csv` | F1 — controlo **sem obstáculos**, 420 ep | controlo |
| `f1_zeroshot_v2/zeroshot_c3_sem_porta_obs.csv` | F1 — controlo **sem features da porta**, 420 ep | controlo |
| `f1_zeroshot_v2/f1_grelha_por_condicao.csv` + `f1_veredicto.txt` + `f1_condicoes.png` | saída do `scripts/analise_f1_controlos.py` | análise |
| `f1_zeroshot/*` | a corrida anulada de 27-28 jul | ⛔ nada |
| `ab_sac/braco_AB_gradsteps5_buffer2M.csv` | A/B do SAC, braço `gradient_steps=5` + buffer 2M | decisão de configuração |
| `ab_sac/braco_C_entcoef_auto.csv` | A/B do SAC, braço `ent_coef=auto` | idem |
| `f0_gnn_curva.csv` | curva do GNN no *smoke test* de 2 h (19 gerações) | **nada** — o F0 não produz resultado |

> ⚠️ **Ao trazer mais corridas do servidor: nomes distintos.** Cada uma grava em
> `zeroshot_mapa_grande.csv` no seu diretório, e a 28 jul um `pscp` para a pasta
> onde já estava a natural apagou-a (recuperada do git). O
> `trazer_do_servidor.sh` passou a avisar e abortar.

## F1 — o resultado (fechado a 2 ago, 1680 episódios)

As quatro condições correram no mundo corrigido, entre 31 jul 02:32 e 1 ago 00:11
(as três de controlo em paralelo no servidor, ~8,5 h cada; a natural em
`~/swarm-mapa`). A grelha é a mesma nas quatro:

| campeão treinado em | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 0,0 | 0,0 | 0,0 |
| Muro em U | 0,0 | 0,0 | 0,0 |
| Gargalo | 0,0 | 0,0 | 0,0 |
| Quatro Salas | 0,0 | 0,0 | 0,0 |
| Porta Cooperativa | 0,0 | 0,0 | 0,0 |
| Perceção Cooperativa | 0,0 | 0,0 | 0,0 |
| Porta c/ Alternativa | 0,0 | 0,0 | 0,0 |
| **média** | **0,00** | **0,00** | **0,00** |

**84 das 84 células a zero absoluto**, nas quatro condições.

| condição | recolhas/ep | veredicto pré-registado (§3) |
|---|---|---|
| **natural** | 0,00 | — é a condição principal |
| escala da observação | 0,00 | **MESMO** ⇒ causa **excluída** (0 células ressuscitadas) |
| sem obstáculos | 0,00 | **MESMO** ⇒ causa **excluída** |
| sem *features* da porta | 0,00 | **MESMO** ⇒ causa **excluída** |

Os três confundentes registados a 24 e 27 jul ficam **excluídos** e vão para
apêndice; reporta-se a condição natural. Reproduz-se com:

```bash
python scripts/analise_f1_controlos.py \
    --csv results/mapa_grande/f1_zeroshot_v2/*.csv \
    --saida results/mapa_grande/f1_zeroshot_v2
```

### O zero mede transferência, não um mapa impossível

É a distinção que decide a leitura, e está medida — não argumentada.
`scripts/sanidade_mapa_grande.py` põe no mapa um navegador que **não aprendeu
nada** (desce o campo geodésico):

| | mapa grande | Quatro Salas |
|---|---|---|
| navegador geodésico | **54,0 rec/ep** | 86,5 rec/ep |
| GNN (campeão do próprio cenário) | 0,0 (0% do navegador) | 69% do navegador |

Há caminho, o ninho é alcançável e cabe no episódio. O que falha é a
transferência — que é o que a QI7 pergunta.

**Sanidade dos ficheiros:** o zero do PPO não é avaria — os mesmos modelos dão
68,3 recolhas/ep no Sandbox e 127,3 no Gargalo, contra 71,5 e 123,2 na tese.

## F2 — treino nativo (arranca 3 ago)

Ainda **não existe um único dado de F2**. Desenho em
`docs/PRE_REGISTO_MAPA_GRANDE.md` (emendas 19 e 20, de 2 ago): 3 algoritmos ×
**21 runs** (GNN @780 min, PPO/SAC @192 min) + um braço **exploratório** GNN
@2340 min × 3 runs. Lança-se com `scripts/mapa_streamF2.sh preparar` e depois um
tmux por stream, **cada um no seu diretório**.

## O que NÃO está aqui (fica no PC da torre)

| | Onde | Tamanho |
|---|---|---|
| Campeões da campanha 7d (21 modelos) | `results/models_7d/` | 50 MB |
| Modelos do *smoke test* F0 | `out/f0_smoke_27jul/` | 13 MB |
| Modelos e logs do A/B do SAC | `out/ab_sac_27jul/` | 43 MB |

Os campeões 7d **voltam a trazer-se do servidor** quando forem precisos:

```bash
scripts/trazer_do_servidor.sh \
  '/home/goncalo/swarm-robotics-tese/results/graficos_tese/09-07-2026_12h52m/modelos' \
  out/campeoes_7d                      # GNN (PPO/SAC de la sao de JUNHO — nao servem)
scripts/trazer_do_servidor.sh \
  '/home/goncalo/run7d_mlp/results/models_ppo/ppo_3d_final*.zip' \
  results/models_7d/models_ppo         # PPO e SAC vêm daqui
```

⚠️ Use `-p` (o script já usa) para **preservar as datas** — sem isso a guarda de
campanha do `eval_zeroshot_mapa.py` deixa passar qualquer modelo.
