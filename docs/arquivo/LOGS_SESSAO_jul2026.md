# LOGS DE SESSÃO ARQUIVADOS — julho 2026

> Movidos do `PLANO_MESTRE.md` a **28 jul 2026**, quando ocupavam 428 das 897
> linhas do ficheiro, empurrando as regras e as tarefas para o fim. Nada foi
> alterado: é o texto tal como foi escrito em cada sessão.
>
> O plano vivo é o [`PLANO_MESTRE.md`](../PLANO_MESTRE.md), que mantém sempre o
> log da sessão mais recente. Estes ficam para consulta — sobretudo o de 27 jul,
> que tem a tabela de onde vem cada campeão da campanha de 7 dias, e o de 25 jul,
> que explica por que razão o F1 desse dia foi anulado.

---

# 0-B. LOG DE SESSÃO — 27 jul 2026 (Opus 5, torre)

> Rebase + tese recompilada de manhã; à tarde, **auditoria de física ao mapa
> grande antes de comprometer a janela de servidor**. Uma falha crítica
> encontrada (o servidor não tem o mapa) e um bug de colisão corrigido.

## 🔬 O QUE CORREU NESTE PC A 27 JUL (e o que deu)

| corrida | duração | resultado |
|---|---|---|
| **F0 — smoke test**, 3 algoritmos no mapa grande | 2 h cada, em paralelo | GNN 19 gerações, fitness 750→2594; PPO 4,2M timesteps; SAC 2,6M. **Todos arrancam e treinam.** Comida 0,0 nos três — esperado em 2 h. |
| **A/B do SAC**, 2 braços | 2 h cada | Nenhum recolheu. A+B corta o desvio-padrão 65%; C piora 80%. **Decisão: SAC inalterado no F2.** |
| **F1 — zero-shot**, 21 células × 20 ep | ~5 h (morreu a meio, retomado) | **420 episódios, grelha completa.** GNN 3,86 · PPO 0,00 · SAC 11,03 |

**Sinal mais forte do F1:** o **PPO dá zero nas 7 células** — e não é avaria: os
mesmos ficheiros dão 68,3 recolhas/ep no Sandbox e 127,3 no Gargalo (a tese
reporta 71,5 e 123,2). O SAC é o que mais transfere (4 de 7 células). Os três
labirintos puros dão zero nos três algoritmos.

⚠️ **Nada disto responde à QI7 ainda** — faltam as três condições de controlo.

O F1 morreu às 17:47 sem causa conhecida (a 25 jul foi o RestartManager do
Windows). **Não se perdeu nada**: o script grava célula a célula e a retoma saltou
as 16 já feitas. Dados em `results/mapa_grande/` (versionados).

## 📝 SECÇÃO DO MAPA GRANDE — escrita e validada, à espera de números (27 jul)

`Tese/seccao_mapa_grande.tex` tem a secção **inteira** nas partes que não dependem
de resultados: motivação e QI7, as cinco zonas, os três parâmetros congelados com
justificação, o protocolo F1/F2, a explicação dos quatro confundentes, as
limitações e a nota metodológica sobre o desenho do mapa. A planta está instalada
em `Tese/images/resultados/mapa_grande_planta.png`.

**NÃO está incluída no `main.tex`** — de propósito: o mapa não tem campanha, e o
pré-registo compromete-se a que só entre com dados. Validada por compilação
isolada: **0 erros, 0 refs indefinidas, 0 overfulls; acrescenta 4 páginas** (121 →
125).

**16 marcadores `\PORPREENCHER{...}`** a vermelho marcam cada número em falta — se
for compilada com buracos, saltam à vista. A Discussão tem **as duas leituras já
escritas** (converge / não converge), pré-comprometidas no pré-registo: preenche-se
uma e apaga-se a outra, sem escrever a interpretação depois de ver os números.

Ao integrar (só até 22 ago): preencher, escolher a leitura, `\input` a seguir a
`sec:res_novelty`, e acrescentar QI7 às Conclusões + uma frase ao Resumo/Abstract.

## ✅ CAMPEÕES 7d TRAZIDOS — o F1 está desbloqueado (27 jul, tarde)

`results/models_7d/` tem os **21/21 campeões** (7 cenários × 3 algoritmos), datados
de **3-9 jul**, e a guarda de campanha do `eval_zeroshot_mapa.py` **passa**. Só
leitura no servidor (`pscp`); nada foi escrito lá. Script novo:
[`scripts/trazer_do_servidor.sh`](../scripts/trazer_do_servidor.sh) — o par do
`servidor.sh`, com `-p` para **preservar as datas** (sem isso a guarda deixa passar
tudo, porque a data passa a ser a de hoje).

⚠️ **A armadilha nº9 apanhada outra vez, e a guarda provou-se.** A primeira
tentativa apontou à sessão auto-contida `graficos_tese/09-07-2026_12h52m/modelos/`,
que tem os três algoritmos — mas os **PPO/SAC de lá são de 24-28 JUNHO**: essa
sessão foi gerada no diretório do **GNN**, e ao arquivar copiou o que estivesse em
`results/models_{ppo,sac}` desse diretório, que eram os MLP antigos. A campanha MLP
de 7 dias correu noutro sítio. As fontes certas, por algoritmo:

| algoritmo | fonte no servidor | datas |
|---|---|---|
| GNN | `~/swarm-robotics-tese/results/graficos_tese/09-07-2026_12h52m/modelos/models/` | 3-9 jul |
| PPO | `~/run7d_mlp/results/models_ppo/` | 3-4 jul |
| SAC | `~/run7d_mlp/results/models_sac/` | 4-6 jul |

**A grelha do F1 passa de 18 para 21 células:** existem agora campeões do
`cooperative_door_bypass` nos três algoritmos, que era a lacuna registada a 25 jul.
Falta só **correr** o F1 (~6 h; não neste PC enquanto o A/B do SAC estiver a correr).

## 🔴 O SERVIDOR NÃO TEM O MAPA — a campanha falhava no arranque

`grep -c mapa_grande ~/swarm-robotics-tese/src/scenarios.py` = **0**; esse ficheiro
é de **2 jul** e o mapa nasceu a 24 jul. O `run_experiments.py --scenarios
mapa_grande` teria impresso `[!] Cenários desconhecidos ignorados` e treinado outra
coisa. A máquina **não tem git** — o código vai por `pscp`.

**Decidido (utilizador, 27 jul): não mexer no servidor até o mega-treino fechar.**
A campanha do mapa corre de um **diretório isolado `~/swarm-mapa/`** (o padrão do
`~/swarm-novelty`), enviado por `pscp` a ~3 ago. Enviar agora contaminava megaA/megaB,
que reescrevem `configs/foraging.yaml` por `sed` a cada fase.

## 🟡 Bug de colisão corrigido (só no mapa_grande)

Push-out das paredes corre **antes** da separação inter-agente ⇒ com o enxame
amontoado, um agente é enterrado no painel e no passo seguinte é expulso **pelo lado
errado**. 20 agentes contra a divisória B→C: **12 passavam**; contra o painel da
porta: **4** — o enxame chegaria ao ninho **sem cooperar**, esvaziando a M3.
Corrigido com 2.ª passagem do push-out que devolve o agente ao lado de **onde veio**.
Emenda #10 do `PRE_REGISTO_MAPA_GRANDE.md`. **Os 7 cenários ficam bit-a-bit iguais**
(assinatura sha256 igual antes/depois — `test_fisica_dos_7_bit_a_bit`). 46/46.

## ✅ O que a auditoria NÃO encontrou (não refazer)

Sem *tunneling* (paredes 1,5 m vs 0,2 m/passo, margem 9×); retângulo exterior
estanque; obstáculos com ≥1,45 m de folga às paredes; aberturas 5,0/2,5/2,5/4,75 m;
caminho com a porta fechada (177 m vs 153 m); `obs_dim=(111,)` igual aos 7 ⇒ os
modelos carregam; `eval_by_run`/`eval_suite` já incluem o mapa. Com política de
*homing* (120 000 passos-agente): **0 travessias** mesmo antes da correção.

## 📊 Calendário e orçamento (contas feitas sobre os arranques reais)

- **megaA** fecha **~1-2 ago** (F2 hoje ~13h UTC → PPO 22 h → SAC 22 h → GNN none 68 h)
- **megaB** fecha **~3 ago** (F4 hoje ~12h UTC → bypass 68 h → SAC 17 h → perception 68 h)
- **F2 do mapa = ~3,8 dias em dois streams** (GNN 7×780 min = 91 h; PPO/SAC 7×192 min).
  Entre 3 e 22 ago há 19 dias ⇒ **espaço para correr a campanha 4 vezes**. Não são 20 dias.
- **Custo por geração medido no F0: 428 s** (16 núcleos, com PPO+SAC a competir) contra
  os **57 min** estimados no pré-registo ⇒ os 780 min/run dão ~200 gerações, não 13,7.
  Medir no servidor antes de decidir cortar o orçamento (emenda #12).

## F0 local (3 algoritmos, 120 min, config isolado)

GNN fitness a subir (750→1359 em 5 gerações), PPO 412 updates, SAC 200k timesteps
`ep_rew_mean` 366. ⚠️ `configs/foraging.yaml` está temporariamente em `mapa_grande`
com `num_cpu: 5` (PPO/SAC leem o caminho em duro) — **repor com `git checkout` quando
os treinos acabarem**.

---

# 0-bis. LOG DE SESSÃO — 25 jul 2026 (Opus 5, PC do trabalho)

> Sessão de **auditoria ao mapa + controlos do F1**, fechada às 23h com a
> descoberta de que o F1 desse dia correu com os modelos errados e com a guarda
> que o impede de se repetir. Zero treinos lançados no servidor. O que mudou de
> facto está em `docs/PRE_REGISTO_MAPA_GRANDE.md`, secção 3 e emendas de 25 jul.

## ⚠️ SE VAIS PARA A TORRE, É ISTO (por ordem)

> **✅ Passos 1 e 2 FEITOS na torre a 27 jul de manhã** (`e3d231b`). O rebase
> apanhou tudo o que o PC do trabalho enviou (`8c189f6`, pushed 07:58; rebase às
> 08:04) — verificado: guarda do zero-shot, `mapa_grande`, pré-registo, Modo
> Defesa e dot plot todos na árvore, `pytest tests/` **44/44**. A tese foi
> recompilada (**121 págs, 0 refs indefinidas, 0 overfulls**) e o PDF commitado.
> A recompilação apanhou ainda uma contradição: o corpo do `main.tex` dizia que a
> fome é "só Sandbox" enquanto o Apêndice A (corrigido a 25 jul) diz Sandbox **e**
> Perceção Cooperativa — o corpo foi alinhado com o código (`not use_geodesic`).
> **Restam os passos 3 e 4.**

1. **`git pull`.** Tudo está em `origin/main` — o último é o `f8be1bb`
   (**guarda de campanha no `eval_zeroshot_mapa.py`**: `--models-dir`, data de
   cada campeão verificada antes da 1.ª célula, proveniência no CSV, 12 testes
   novos). A torre precisa dele antes de repetir o F1, senão repete-o com o
   script velho, que aceita qualquer modelo.
2. **RECOMPILAR A TESE** (`pdflatex ×2 + biber`, em `Tese/`). O `main.tex` mudou
   hoje (3 correções, ver abaixo) e o `main.pdf` que está no repo é de 24 jul,
   logo **está desatualizado**. Confirmar 0 refs indefinidas e 0 overfulls, e
   commitar o PDF novo. Não há LaTeX no PC do trabalho — só se pode fazer aí.
3. **NÃO olhar para o F1 que está no CSV** — está anulado (modelos de 24 jun; ver
   o bloco 🛑 abaixo). O que fazer é **trazer os campeões 7d** de `~/eval7d.tar.gz`
   e `~/run7d_mlp` para `results/models_7d/` e repetir com `--models-dir`. A
   guarda nova recusa-se a correr enquanto lá não estiverem, e o CSV velho vai
   sozinho para `_ANTIGO` na primeira corrida boa.
4. **Decidir onde correm os controlos** — a resposta provável é *no servidor*,
   não em PC: são ~6 h por condição (×2 condições) e o servidor tem 64 vCPU.
   Mas ver primeiro a regra de capacidade em [[servidor-iscte-treinos]]: com
   megaA+megaB vivos, **não** lançar uma 3.ª stream pesada.

**Estado do F1 (zero-shot de topologia), corrido LOCALMENTE:**
- A corrida lançada às 13:28 **morreu por volta das 15:06** (o `RestartManager`
  do Windows abriu sessão às 16:31 — um instalador a mandar fechar aplicações).
  Ninguém deu por isso: o log do shell estava a **0 bytes**. **Retomada às 16:46**
  e as 5 células já feitas foram saltadas, não repetidas.
- **COMPLETO às 21:56 — 18/18 células, 360 episódios.** Grelha de 18 e não 21
  porque **não há campeões do `cooperative_door_bypass` no disco** — ver ponto
  próprio mais abaixo.
- Resultado da condição natural (recolhas/ep, 20 ep/célula; sucesso entre
  parênteses). **Atenção à leitura da tabela:** as linhas são o cenário onde
  cada campeão foi TREINADO no passado; os 360 episódios correram **todos** no
  `mapa_grande`, e nenhum modelo foi treinado (é avaliação, não treino).

  | campeão treinado em | GNN | PPO | SAC |
  |---|---|---|---|
  | Sandbox | **16,3** (100%) | 0,0 (0%) | **11,5** (100%) |
  | Muro em U | 2,3 (55%) | 0,0 | 0,0 |
  | Gargalo | 0,0 | 0,0 | 0,1 (10%) |
  | Quatro Salas | 0,0 | 0,0 | 0,0 |
  | Porta Cooperativa | 0,0 | 0,0 | 0,8 (20%) |
  | Perceção Cooperativa | 2,3 (100%) | **18,4** (100%) | **18,4** (100%) |

  Médias por algoritmo: SAC 5,12 · GNN 3,48 · PPO 3,08 — empate técnico, e os
  três puxados pelas mesmas duas linhas. **10 das 18 células a zero absoluto.**
### 🛑 O F1 DE 25 JUL CORREU COM OS MODELOS ERRADOS — REPETIR

Descoberto ao fim da noite de 25 jul, a verificar o plano. **Os `results/models*`
DESTE PC são de 24 jun** — três semanas antes da campanha de 7 dias que a tese
reporta (2-9 jul). O `eval_zeroshot_mapa.py` carrega o que estiver no caminho
esperado e não tem opinião sobre a data; o pré-registo diz "campeões da campanha
7d", e não foi isso que correu.

O que torna isto indiscutível, e não uma questão de datas: os campeões GNN de
24 jun dão **0,0 no seu PRÓPRIO cenário** (`eval_summary.csv` de 23 jun:
Gargalo 0,0 · Quatro Salas 0,0 · Porta Cooperativa 0,0) enquanto a tese reporta
**121,4 · 59,8 · 69,8** para essas células. São os campeões de **antes da fitness
de homing** — o "colapso do evolutivo" que a tese descreve como curado.

**Consequências:**
- A linha do **GNN** nos labirintos não mede transferência nenhuma: mede modelos
  que já estavam partidos. **Não usar.**
- As linhas do **PPO e SAC** continuam de pé: os modelos de 24 jun funcionam bem
  nos cenários deles (Gargalo 41,4 e 36,5; Porta Coop. 66,6 e 62,3) e mesmo
  assim dão 0 no mapa novo. Isso é transferência a sério — com os confundentes
  por descartar.
- **A leitura "os campeões dos labirintos decoraram a geometria" fica SEM
  suporte** e não deve ser escrita em lado nenhum. Era o que estava aqui escrito
  às 22h; ficou refutado às 23h pelos próprios dados.

**Onde estão os campeões certos** (verificado no servidor a 25 jul):
- **NÃO** em `~/swarm-robotics-tese/results/models*` — esse dir está a ser
  reescrito pelo MEGA-TREINO agora (16 `.pth` de 24 jul para cá; o `u_wall` é
  de 24 jul e o `bottleneck` tem `meta.json` com `saved_at 2026-07-15`). É a
  armadilha nº9 a acontecer em direto.
- Nos arquivos da campanha: **`~/eval7d.tar.gz`** e **`~/run7d_mlp`** (PPO/SAC).
- Trazer para uma pasta ISOLADA (ex.: `results/models_7d/`) e apontar o F1 lá —
  **nunca** por cima de `results/models*`, ou perde-se a rastreabilidade do que
  foi avaliado com o quê.

**Guarda posta no script (25 jul, 23h — FEITO).** O `eval_zeroshot_mapa.py` já
não aceita avaliar o que lhe calhar à mão:
- **`--models-dir`** — a raiz dos modelos deixa de estar em duro. Aponta-se à
  pasta ISOLADA da campanha (`results/models_7d/`), nunca aos `results/models*`
  ativos.
- **Guarda de campanha** — a data de cada campeão (sidecar `.meta.json`, senão o
  mtime) é verificada contra `--campanha-inicio`/`--campanha-fim` (por omissão
  `2026-07-02`–`2026-07-10`, a campanha 7d) **antes da primeira célula**:
  anterior **aborta**, posterior **avisa** (pode ser campanha repetida — mas é
  também o aspeto de estar a ler uma pasta que um treino reescreve). Verificado
  contra o disco real: aborta a apontar o `gnn_3d_best_u_wall.pth` de 24 jun.
- **O CSV passa a dizer de que campanha é**: colunas `ModeloPath`, `ModeloData`,
  `ModeloFonte`. Um CSV sem elas não é retomado (vai para `_ANTIGO`, agora com
  carimbo temporal — o `_ANTIGO` anterior deixou de ser apagado por cima), e uma
  célula avaliada com outro modelo **volta a correr mesmo estando completa**:
  sem isto, repetir o F1 herdava em silêncio as 18 células erradas.
- `--sem-guarda-data` para desligar tudo (as datas continuam a ir para o CSV).
- **12 testes novos** (`tests/test_zeroshot_guarda.py`), **44/44** na suite.

Comando da repetição, quando os campeões 7d estiverem no disco:
```
.venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 20 \
    --models-dir results/models_7d
```
- **Onde ver o estado:** `results/evaluation/zeroshot_mapa_grande_progresso.log`
  (escrito pela própria corrida, com flush; sobrevive à morte dela) e o ficheiro
  `.lock` com o estado atual. No PowerShell, `Get-Content ... -Encoding UTF8`.

**Os zeros NÃO são do mapa** — auditoria independente feita antes de os
interpretar: 0/20 agentes sem caminho ao ninho com os 106 obstáculos (e também
com a **porta fechada**, pela alternativa); um oráculo que desce o gradiente
geodésico faz **52 recolhas/ep**; folga do `max_steps` **2,89×**; folga lateral do
caminho ótimo igual à dos 7 cenários. O mapa é resolúvel com margem.

**Mas os zeros também não são interpretáveis ainda: encontrei DOIS confundentes
novos** (com 5 células já medidas — está declarado no pré-registo):
1. **Obstáculos.** Dos 8 cenários **só o Sandbox (100) e o mapa_grande (106) têm
   obstáculos**; os outros 6 têm **zero**. O único campeão que treinou com
   obstáculos é o único que recolhe alguma coisa (16,3 vs ≈0).
2. **As 4 features da porta** (`obs[12:16]`): identicamente 0 no treino de quem
   não tem porta, vivas no mapa (`[0,999 0,043 0 0,629]`).

**Preparado (por correr):** `--controlo sem_obstaculos` e `--controlo
sem_porta_obs`, cada um a desligar uma causa e mais nada, com leitura
pré-comprometida no pré-registo. As condições convivem no mesmo CSV (colunas
`NormObs` e `Controlo`, com impressão digital do ambiente **por condição**).

**Outros estragos apanhados e tratados:**
- O gerador de figuras recusava-se a fazer figuras assim que existisse uma
  condição de controlo no CSV (validava o `env_hash` do ficheiro **inteiro**) e
  misturava condições no heatmap. Corrigido: filtra `(mapa, base)` primeiro.
- Duas corridas em simultâneo apagavam células uma à outra em silêncio (cada uma
  reescreve o CSV inteiro a partir da sua memória) e partilhavam o mesmo config
  temporário — lançar o controlo com a base a andar trocava-lhe o ambiente a
  meio. Agora: config por condição + lock com PID (que se sabe órfão sozinho).
- **Faltam os campeões do `cooperative_door_bypass`** (nenhum `.pth`/`.zip`
  local, nos 3 algoritmos): o F1 salta 3 células e a grelha fica incompleta. O
  script passa a repetir o aviso no fim, mas os modelos têm de vir do servidor.

**Testes:** 17/17 no `test_mapa_grande.py` (3 novos: travessia **com**
obstáculos — o campo geodésico do ambiente só conhece paredes —, e um por
controlo, a provar que cada um muda **uma** coisa e deixa o resto bit-a-bit).
`pytest tests/` também passou a correr (32 passed): um `sys.exit(0)` à
importação abortava a coleção inteira e nenhum teste corria.

## Releitura da TESE (25 jul) — 3 correções, tudo o resto confere

Verificação estática + número-a-número contra os CSVs que existem neste PC.

**Corrigido** (commit `6090748`):
1. `tab:res_scale_all`: **duas células não batiam** com `escalabilidade_*.csv` —
   Quatro Salas N=50 dizia 3,25 (CSV: 3,255 → **3,26**) e Muro U N=10 dizia 3,83
   (CSV: 3,835 → **3,84**). Arredondamento para baixo em dois empates.
2. Apêndice A dizia que o `hunger_timer_max` é **"só Sandbox"**; o código aplica-o
   quando `not use_geodesic`, ou seja também na **Perceção Cooperativa**.
3. `REPRODUZIR.md` trocava QI3 com QI4 no mapa resultado→dados.

**Conferido e sem erros:** 0 refs indefinidas (135 usos/98 labels), 0 labels
duplicados, 0 citações fora do `.bib`, `\begin`/`\end` equilibrados, as 30
figuras de resultados existem em disco (nenhuma cai no placeholder), 0
TODO/placeholder no corpo; `tab:res_eval` e `tab:res_signif` batem célula a
célula com a tabela canónica da secção 2 deste ficheiro (21/21 e 21/21) e são
coerentes entre si; Apêndice A bate com o `foraging.yaml` atual (24 parâmetros +
hiperparâmetros dos 3 algoritmos); 15/21 a 100%, o 1,8× do Quatro Salas, o ≈8×
de núcleos-hora e o 28/28 conferem; as outras 33 células do Sscale batem.

**Não verificável neste PC** (dados na torre, auditados a 16-18 jul segundo o
`REPRODUZIR.md`): Ptask por run, significância, novelty e Rrobust.

**A tese não menciona o mapa grande em lado nenhum** — correto por agora (não
tem campanha). Se o F2 fechar antes de 22 ago, a secção é escrita de raiz.

## Servidor (verificado às 20:35 de 25 jul, com VPN)

Ambas as campanhas **vivas e saudáveis**: megaA na FASE 2 (GNN objetivo `u_wall`
@195×28, **Gen 132**), megaB na FASE 4 (ablação `decay=0.995`, **Gen 318**,
comida 51,25). `load average 36,3` em 64 núcleos (42% livre) — o esperado para
duas streams. Uptime 100 dias. **Nada a fazer; não lançar uma 3.ª stream.**

**Próximo passo:** deixar o F1 fechar; só depois decidir se os controlos correm
para todas as células ou só para as que derem 0 (custa ~6 h cada condição, e
**não neste PC**).

---

# 0-bis. LOG DE SESSÃO — 24 jul 2026 (Opus, PC do trabalho)

> Ponto de re-entrada rápido. O detalhe de cada item está nas secções próprias
> (P1.6 para o mapa, P2 para o orientador).

**Contexto ao começar:** este PC estava 9 dias desatualizado (25 commits por
puxar). Feito `git pull --ff-only`. **Trabalhar sempre na `main`.**

**Feito hoje (10 commits, todos em `origin/main`; o último é `e053a91`):**
1. **MAPA GRANDE — 8.º cenário, código FECHADO** (ver P1.6). Desenhado a partir
   de um esboço do utilizador, aprovado em planta 2D e em 3D **antes** de virar
   código, integrado como `mapa_grande` (r=60, 103×62 m, 5 zonas, 155 m de pior
   percurso). **Nunca treinado.**
2. **4 bugs corrigidos** — dois deles teriam invalidado a campanha inteira:
   - `max_steps` 1200→**2000** (a 0,2 m/passo o pior spawn está a 629 passos só
     de ida; 1200 nem dava para ida-e-volta);
   - orçamento do GNN **195→780 min/run** (a 57 min/geração, 195 min dariam 3,4
     gerações contra as 14 das campanhas fechadas — seria "o evolutivo falha"
     por artefacto do orçamento);
   - `required_to_eat` 3→**1**; `use_geodesic` sem o mapa (ficava sem campo
     geodésico).
   - **Bónus que afeta TODAS as campanhas:** `set_scenario` apagava os 37
     comentários do `foraging.yaml` a cada cenário. Agora é edição cirúrgica.
3. **`tests/test_mapa_grande.py`** — 11 testes, todos a passar. Cada um cobre um
   modo de falha que invalidaria a campanha (determinismo, fuga de estado entre
   cenários, porta com alternativa, obstáculos a selar corredores, `obs_dim`=111).
4. **Pré-registo** (`PRE_REGISTO_MAPA_GRANDE.md`) escrito **antes** de qualquer
   treino: QI7, fases F0/F1/F2, testes M1-M3, regra de decisão, modos de falha.
5. **Pipeline de figuras** do mapa + `eval_zeroshot_mapa.py` (F1).
6. **Pacote para o orientador PRONTO** (ver P2) — só falta enviar.
7. **Segunda auditoria ao mapa, ao fim do dia (Opus 5)** — o F1 tinha sido
   interrompido por falha de energia (2 de 21 células); em vez de o repetir,
   revisão estática do que ficou escrito. Emendas datadas na secção 7 do
   `PRE_REGISTO_MAPA_GRANDE.md`:
   - **Confundente da normalização da observação** (o único com consequência
     científica): as distâncias são normalizadas pelo raio da arena, logo o
     mesmo campeão vê tudo **comprimido 4×** no mapa (÷120 vs ÷30). Um zero no
     zero-shot admitia duas causas — topologia difícil ou observação fora de
     escala. F1 passa a correr em **duas condições** (`--norm-obs mapa|treino`),
     com leitura pré-comprometida. Nos 7 cenários nada muda (bit-a-bit).
   - **Obstáculo dentro da zona de recolha em 24% dos episódios** (o disco livre
     à volta do ninho, que o `_spawn_obstacles` genérico tem, faltava aqui) e
     **0,2% dos agentes a nascer dentro de um obstáculo** (a clareira de spawn
     era um círculo menor que a diagonal da caixa). Ambos são variância de
     layout sorteada por episódio, que a avaliação emparelhada não cancela.
   - **`eval_zeroshot_mapa.py` dizia-se retomável e não era**: ao recomeçar
     escrevia por cima do CSV. Agora salta as células completas e guarda uma
     impressão digital do ambiente — dados de um mapa anterior nunca se
     misturam com os novos.
   - **`set_scenario` engolia exceções**: se a troca de cenário falhasse, a
     campanha seguia a treinar o cenário **anterior** e a gravar com o sufixo do
     novo, sem erro. Passa a rebentar.
   - 14/14 testes do mapa (3 novos) e as 5 suites antigas a passar.
8. **Auditoria TOPOLÓGICA ao desenho — duas zonas não cumpriam o rótulo.** A
   auditoria de cima era ao código; esta é à geometria. Corrigido (aprovado pelo
   utilizador), ainda com **zero dados**:
   - **O beco em U não era armadilha nenhuma.** A bússola do ninho é euclidiana,
     logo um bolso só arma se a linha reta agente→ninho lhe entrar pela boca. O U
     tinha a boca a **este** e o ninho está a este: os agentes chegavam-lhe pelas
     costas e contornavam-no. **0 de 60** pontos de entrada eram atraídos, e o
     caminho ótimo passava a 15,3 m. Espelhado (boca a oeste) → **37%**.
   - **A zona "Quatro Salas" eram DUAS salas** (uma parede, uma abertura). Agora é
     a cruz completa com 4 aberturas em ciclo, como o `four_rooms`; selando-a, a
     zona parte-se em **4 componentes de área igual**.
   - Consequências: pior percurso 143→**155 m**, desvio 1,34→**1,47×**, folga do
     `max_steps` 3,2→**2,6×** (acima do mínimo 2,5× pré-registado, por isso
     `max_steps` fica em 2000), porta +24→**+21%**. Espaço livre continua numa só
     componente, **0 ilhas inacessíveis**.
   - **O mapa continua resolúvel** (25 jul, teste de fumo local: campeão do
     Sandbox em zero-shot faz **15,5 recolhas/ep, 100%**). Não é resultado — é a
     garantia de não gastar servidor num mapa impossível.

**Decisões tomadas (não reabrir):**
- **20 agentes**, não mais: `obs_dim = 16+(N-1)×5`; com 20 fica em 111 (= aos 7
  cenários) e os modelos existentes carregam. Com 40 seria 211 e PPO/SAC
  precisariam de arquitetura nova.
- **Obstáculos estáticos** (decisão do utilizador).
- **NÃO lançar F2 em paralelo com o mega-treino.** Servidor medido: 64 vCPU,
  load 38, 42% idle — mas um treino GNN pede sempre 30 workers, e 3 streams =
  90 processos em 64 núcleos (1,4× sobre-subscrito). O GNN faria 9,8 gerações
  em vez de 13,7 **e** o mega-treino renderia ~30% menos e atrasaria. Poupava 4
  dias e arriscava duas campanhas. **Esperar por ~3 ago.**

**Verificado (não alterou código):** os robôs **não** passam por cima das
paredes (teste empírico: sobem a z≈14,7 m, atravessam 0); a porta **tem
alternativa** (+21%, não bloqueia); os 7 cenários da tese ficaram intactos
(comparação bit-a-bit com a versão anterior do simulador: erro 0,0e+00 em
observações, recompensas e posições).

⚠️ **O "primeiro sinal do zero-shot" de 24 jul foi DESCARTADO.** Eram 2 de 21
células (Sandbox 14-20 recolhas/ep, Quatro Salas 0), obtidas na geometria antes
das correções das zonas A e B — não são comparáveis com nada do que vier. O CSV
está em `results/evaluation/zeroshot_mapa_grande_ANTIGO.csv` e não entra em
análise nenhuma. **F1 tem de correr de novo, nas duas condições de
normalização.** A leitura "especialização vs generalização" fica como hipótese a
testar, não como sinal.
*(25 jul: o F1 foi relançado na geometria nova e está a meio — ver secção 0.
As condições passaram de duas a quatro.)*

**Próximo passo, por urgência:** (1) **enviar o draft ao orientador** — é o item
mais atrasado e o único que não depende de servidor; (2) F1 zero-shot (local, **a
correr desde 25 jul**); (3) F2 no servidor depois de ~3 ago.

---
