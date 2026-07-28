# Dados do MAPA GRANDE — 27 jul 2026

> **Estes CSV estão VERSIONADOS de propósito**, ao contrário do resto de
> `results/`, que o `.gitignore` exclui. São 92 KB no total e são a única cópia
> destes resultados: o precedente é o braço Novelty preliminar, cujos artefactos
> foram sobrescritos no servidor e hoje são o único número da tese sem fonte
> reproduzível. Adicionados com `git add -f`.
>
> Os **modelos** continuam fora do git (são 106 MB) — ver abaixo onde estão.

## O que está aqui

| Ficheiro | O que é | Vale como |
|---|---|---|
| `f1_zeroshot/zeroshot_mapa_grande.csv` | **F1 — condição NATURAL**: 21 células (7 cenários de origem × 3 algoritmos) × 20 episódios = **420 episódios** | **resultado**, condição principal do pré-registo |
| `f1_zeroshot/zeroshot_c1_escala.csv` | F1 — controlo **escala da observação** (`--norm-obs treino`), 420 ep | controlo |
| `f1_zeroshot/zeroshot_c2_sem_obstaculos.csv` | F1 — controlo **sem obstáculos**, 420 ep | controlo |
| `f1_zeroshot/zeroshot_c3_sem_porta_obs.csv` | F1 — controlo **sem features da porta**, 420 ep | controlo |
| `f1_zeroshot/f1_grelha_por_condicao.csv` + `f1_veredicto.txt` + `f1_condicoes.png` | saída do `scripts/analise_f1_controlos.py` — a grelha das 4 condições, o veredicto e a figura | análise |
| `f1_zeroshot/zeroshot_mapa_grande_progresso.log` | registo célula a célula, com data do modelo usado em cada uma | proveniência |

> ⚠️ **Ao trazer mais corridas do servidor: nomes distintos.** Cada uma grava em
> `zeroshot_mapa_grande.csv` no seu diretório, e a 28 jul um `pscp` para a pasta
> onde já estava a natural apagou-a (recuperada do git). O
> `trazer_do_servidor.sh` passou a avisar e abortar.
| `ab_sac/braco_AB_gradsteps5_buffer2M.csv` | A/B do SAC, braço `gradient_steps=5` + buffer 2M | decisão de configuração |
| `ab_sac/braco_C_entcoef_auto.csv` | A/B do SAC, braço `ent_coef=auto` | idem |
| `f0_gnn_curva.csv` | curva do GNN no *smoke test* de 2 h (19 gerações) | **nada** — o F0 não produz resultado |

## F1 — a grelha (condição natural)

| campeão treinado em | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 7,2 | 0,0 | 19,6 |
| Muro em U | 0,0 | 0,0 | 0,0 |
| Gargalo | 0,0 | 0,0 | 0,0 |
| Quatro Salas | 0,0 | 0,0 | 0,0 |
| Porta Cooperativa | 0,0 | 0,0 | 21,6 |
| Perceção Cooperativa | 17,3 | 0,0 | 15,8 |
| Porta c/ Alternativa | 2,5 | 0,0 | 20,2 |
| **média** | **3,86** | **0,00** | **11,03** |

**14 das 21 células a zero absoluto.** Modelos da campanha 7d (3-9 jul), guarda de
campanha a passar, impressão digital do ambiente `267a7b547aed`.

## As quatro condições — F1 COMPLETO (28 jul)

Os três controlos correram no servidor a 28 jul (~8,5 h cada, em paralelo). Médias
por condição, sobre as mesmas 21 células emparelhadas:

| condição | recolhas/ep | veredicto pré-registado (§3) |
|---|---|---|
| **natural** | 4,96 | — é a condição principal |
| escala da observação | 3,15 | **DIVERGE** — 6 células ressuscitam, 4 morrem |
| sem obstáculos | 4,91 | **MESMO** ⇒ causa **excluída** (p=0,93) |
| sem *features* da porta | 4,13 | **DIVERGE** — 2 células ressuscitam |

⚠️ **Um controlo que ressuscita células NÃO salva a leitura "a topologia é dura":
desmente-a.** É o que o pré-registo fixou antes de haver dados, e é o que se
reporta. O veredicto integral está em `f1_zeroshot/f1_veredicto.txt`; reproduz-se
com `python scripts/analise_f1_controlos.py`.

Notar que a escala **não melhora** o resultado — redistribui-o: mata o Sandbox e a
Perceção do GNN (7,2→0 e 17,3→0) e acende o Gargalo e a Perceção do PPO. É
consistente com a limitação declarada no pré-registo: as duas normalizações estão
fora da distribuição de treino, de maneiras opostas.

**Sanidade verificada:** o zero do PPO não é avaria — os mesmos ficheiros dão
68,3 recolhas/ep no Sandbox e 127,3 no Gargalo, contra 71,5 e 123,2 na tese.

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
