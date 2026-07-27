# PLANO MESTRE — Tese de Mestrado (19 jul → Outubro 2026)

> **Este é o ÚNICO ponto de re-entrada do projeto.** Escrito a **19 jul 2026**,
> **atualizado a 25 jul**. Funde o `PLANO_ATAQUE_FINAL.md` (lista acionável de
> 15 jul) com o `PLANO_DE_ATAQUE.md` (registo histórico) — ambos passaram para
> `docs/arquivo/` a 25 jul; não os atualizes, atualiza ESTE.
> O mapa do resto da pasta está em [`docs/README.md`](README.md).
>
> **Para o Claude/Opus:** lê este ficheiro do princípio ao fim antes de tocar em
> qualquer coisa. Verifica `git log` e as checkboxes — NÃO refaças trabalho fechado.
> A memória persistente (`memory/`) tem o detalhe de cada episódio; o índice é o
> `MEMORY.md`.

**Tese**: "Aprendizagem por Reforço para Controlo de Enxames" — ISCTE, Mestrado em IA
**Orientador**: Prof. Luís Nunes | **Versão composta ao orientador: 15 set** | entrega 30 set | defesa Outubro

---

# 0. LOG DE SESSÃO — 27 jul 2026 (Opus 5, torre)

> Rebase + tese recompilada de manhã; à tarde, **auditoria de física ao mapa
> grande antes de comprometer a janela de servidor**. Uma falha crítica
> encontrada (o servidor não tem o mapa) e um bug de colisão corrigido.

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

# 1. REGRAS INVIOLÁVEIS (do utilizador — não negociar)

1. Responder e escrever sempre em **PT-PT** (com todos os acentos).
2. **O código não é avaliado** — a tese e o artigo são. Todo o esforço vai para os documentos.
3. **Não lançar treinos nem mexer no servidor** sem o utilizador pedir explicitamente.
4. **Nunca concluir nada a partir de números de TREINO** (armadilha nº3) — o veredicto
   é sempre `eval_summary.csv` / `eval_by_run.csv`, da MESMA data dos modelos.
5. Nada de `Set-Content`/`Out-File` PS5.1 em YAMLs (o BOM parte-os) — usar a ferramenta Edit.
6. Antes de dar qualquer sessão por concluída: (a) a tese compila (0 refs indefinidas)?
   (b) os números citados batem com o CSV fonte (dizer qual)? (c) commit em PT descritivo?
   (d) checkboxes DESTE ficheiro atualizadas com a data?

---

# 2. ESTADO (o que está FECHADO — não reabrir)

> **Atualização de 24 jul:** o mega-treino P1.5 está a meio e saudável (megaA na fase
> A2, megaB na B3; durações reais batem com as estimadas ao décimo de dia; fim ~1-3 ago).
> Acrescentou-se o **mapa grande** como 8.º cenário — código fechado e pré-registado,
> por treinar (**P1.6**). O pacote para o orientador está pronto a enviar (**P2**).
> O resto desta secção é de 19 jul e mantém-se válido.

## Entregáveis
- **Tese: 117 págs**, compila limpa (pdflatex ×2 + biber), 0 refs indefinidas, **0 overfulls**.
  Revisão número-a-número COMPLETA a 18 jul (commits `17a13ad` + `2f536c7`): todos os
  números verificados contra CSVs/config/código, 5 figuras regeneradas, Lista de
  Acrónimos corrigida (estava VAZIA desde sempre), Apêndice A vs `foraging.yaml` conferido,
  geometria dos 7 cenários vs `swarm_env_3d.py` conferida.
- **Artigo: 9 págs** PT-PT, compila, `references.bib` sincronizado byte a byte com o da tese.
- PDFs de referência: `out/{Tese,Artigo}_Goncalo_Pombo_v14jul2026.pdf` (pós-18 jul, recompilar
  para versão nova ao enviar ao orientador).
- **`docs/REPRODUZIR.md`**: mapa resultado→dados→script; auditoria número-a-número FEITA
  (SLR, Sscale, tab:res_eval 21/21, tab:res_signif 21/21, §res_novelty, Rrobust).
- **Git**: `main` é a fonte de verdade única (consolidada 15-16 jul); `feat/novelty-search`
  CONGELADA; backups em `backup/*` no GitHub (rollback:
  `git push origin backup/main-pre-consolidacao-15jul:main --force`).

## Ciência (resultados canónicos — a fonte de qualquer afirmação na tese)

**Campanha final 7d** (3 algos × 7 cenários × 7 runs = 147 treinos; eval 20 ep/run
emparelhada = 140 ep/célula; Mann-Whitney + δ de Cliff sobre médias por run, n=7):

| Cenário | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 38.3±31.0 (86%) [5/7] | **71.5±1.0** (100%) | 69.2±1.9 (100%) |
| Muro em U | 24.5±32.7 (43%) [3/7] | **39.6±36.7** (71%) [4/7] | 9.0±15.1 (34%) [2/7] |
| Gargalo | 121.4±20.0 (100%) | **123.2±1.2** (100%) | 41.4±36.8 (72%) [5/7] |
| Quatro Salas | **59.8±13.2** (100%) | 33.6±3.8 (100%) | 31.8±3.3 (100%) |
| Porta Cooperativa | **69.8±1.0** (100%) | 67.1±3.7 (100%) | 62.1±2.5 (100%) |
| Perceção Cooperativa | **19.0±8.7** (91%) [6/7] | 15.3±0.4 (100%) | 16.1±0.8 (100%) |
| Porta c/ Alternativa | **86.7±2.0** (100%) | 85.3±4.0 (100%) | 68.6±3.4 (100%) |

- **Achado central:** o "colapso do evolutivo" era **artefacto do desenho da fitness**
  (retorno acumulado farmável por deambulação). A **fitness de homing**
  (`J = f̄·10⁴ + 5000·h̄`) cura-o: GNN converge em 28/28 runs dos labirintos não-decetivos
  e é significativamente superior aos dois métodos de gradiente em 3 cenários.
- **Muro em U:** nenhum algoritmo o resolve de forma fiável (bimodal nos três; nenhuma
  diferença significativa). O problema é a **descoberta** sob observabilidade parcial.
- **Escalabilidade Zero-Shot: 28/28 células a 100%** (7 cenários × N∈{10,20,50,100});
  retenção per capita N=100: bypass 90%, coop_door 88%, u_wall 78%, Sandbox 39% (diluição
  de recurso, não falha de coordenação). CSVs: `results/estatisticas/escalabilidade_*.csv`.
- **Novelty fixo (w=0.5, orçamento igualado 195 min):** GANHA no Muro em U (7/7 a 100%,
  69.8±5.9 vs 3/7, p=0.026, δ=+0.71); PERDE no bypass (63.0 vs 86.7, p=0.0006, δ=−1.00).
  Leitura: instrumento **direcionado** — compra descoberta onde falta, desperdiça seleção
  onde sobra. Dados: `results/novelty_final/`. (O 81.3 de 2 jul era artefacto de 600 min.)
- **SLR conduzida a sério** (o PRISMA inicial era fabricado): 883 registos → 680 únicos →
  **58 estudos**; **a lacuna está MEDIDA: só 1 em 58 (Iskandar 2024) compara os paradigmas.**
  Pipeline: `scripts/slr_pipeline.py` a partir de `docs/slr/screening.csv`.
- **Bibliografia:** auditada 3×; Iskandar é REAL (2.º autor **Ali** Hammoud, confirmado na
  fonte primária); nomes NEAT corrigidos (Tameem Uz Zaman, Pigar Biteng). Lição
  permanente: **verificar NOMES e CONTEÚDO, não só DOIs.** Os DOIS `.bib` corrigem-se juntos.

## O que estava errado em planos antigos (REFUTADO — não citar)
~~GNN colapsa nos labirintos~~ · ~~PPO faz reward hacking no Muro U~~ (hoje é o melhor lá) ·
~~SAC resolve tudo~~ (é o mais frágil nos gargalos) · ~~Sscale 15%→100%~~ (é 100% em tudo) ·
~~Novelty 81.3 é o melhor resultado do bypass~~ (era orçamento desigual).

---

# 3. A ÚNICA COISA A CORRER — campanha Novelty ADAPTATIVO (fecha 19-20 jul = AGORA)

Lançada 12 jul 19:46 no `.14`, 2 streams tmux (`week_A` fim ~18 jul, `week_B` ~19 jul):
Novelty adaptativo (w=0,5 decai ×0,98/gen após 10 gens consecutivas a comer) nos 7 cenários
@195 min × 7 runs (seeds 1-7) + braços de controlo @390 min. Fases arquivadas em
`~/week_{A,B}_fase*/`. ⚠️ A ordem dos cenários é a CANÓNICA de `src/scenarios.py`, não a
do `--scenarios`.

**Pré-registo COMPLETO e congelado ANTES dos dados:**
[`docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md`](PRE_REGISTO_NOVELTY_ADAPTATIVO.md) — hipótese,
testes confirmatórios T1-T4, regra de decisão da QI6 (sobe a resultado sse: não-degrada os
5 fáceis + ganho no u_wall + sem custo no bypass), compromissos de reporte (TODOS os runs).
**Segui-lo à letra; não escolher a conclusão depois de ver os dados.**

## Checklist da chegada (P1) — passos 1-3 FECHADOS a 19 jul (Fable)
- [x] **Confirmadas as duas streams CONCLUÍDAS** (19 jul): A fechou 18 jul 19:15 UTC,
      B fechou 19 jul 12:56 UTC; sem tmux, load 0.00; sentinela + `eval_by_run.csv`
      nas 5 fases.
- [x] **Tudo trazido** (19 jul): tarball em `out/week_adaptativo_19jul.tar.gz` (11 MB),
      extraído em `out/week_adaptativo_19jul/` e instalado em
      **`results/novelty_adaptativo/`** (fora do git, como o `novelty_final/`).
- [x] **Armadilha nº9 tratada por adaptação** — as fases NÃO são sessões `graficos_tese`
      (são cópias de `results/{evaluation,models,logs}` por fase, já auto-contidas e
      emparelhadas); o `pos_campanha.py` não se aplica e **os `results/models*` ativos
      (campeões 7d da tese) ficaram INTACTOS de propósito** — instalar os modelos
      adaptativos por cima criaria a armadilha inversa.
- [x] **`_run{1..7}` verificados** (armadilha nº8): 175 `.pth`; 7 runs × 20 ep por
      cenário nas 5 evals (A1: none/u_wall/bottleneck/four_rooms; B1: coop_door/
      bypass/perception; A2: u_wall controlo objetivo @390; B2: u_wall adaptativo @390;
      B3: bypass adaptativo @390) — bate com o pré-registo.
- [x] **Configs do servidor repostos** (19 jul): os dois dirs (`~/swarm-robotics-tese` e
      `~/swarm-novelty`) em `novelty_weight: 0.0`, `novelty_adaptive: false`
      (B reposto à mão; backup `foraging.yaml.bak_19jul`).
- [x] **ANÁLISE T1-T4 FEITA e INTEGRADA (19 jul, Fable)** — `scripts/analise_adaptativo.py`;
      unblinding registado no §7 do pré-registo. **Veredicto: SOBE A RESULTADO** (T1 sem
      degradação, todos p≥0,21; T2 u_wall 7/7, 68,5±13,1, p=0,009, δ=+0,76; T3 bypass sem
      custo, δ=−0,35 n.s.; T4 vs fixo: bypass δ=+0,59). Exploratório: objetivo puro @390
      no u_wall CONTINUA bimodal (4/7) → o ganho é do mecanismo; bypass adaptativo @390 =
      **88,7±0,6 [7/7] = melhor resultado da dissertação**. QI6 + sec:res_novelty +
      Discussão + Conclusões + Trabalhos Futuros reescritos na tese; abstract +
      contribuições (v) + §4.3 + conclusões no artigo. Tese 121 págs, artigo 10 págs,
      ambos 0 undefined / 0 overfulls.
- [x] **Passou → o w adaptativo passou a RESULTADO** (integrado em `sec:res_novelty` +
      QI6 na tese e no artigo, commit `704a36e` de 19 jul). A alternativa pré-registada
      ("se não passar, reportar como resultado negativo honesto") não chegou a aplicar-se.
- [x] **Recompilado e commitado** (19 jul, `704a36e`): tese 121 págs, artigo 10 págs,
      ambos 0 refs indefinidas / 0 overfulls. *(Checkboxes fechadas a 24 jul — o trabalho
      estava feito desde 19 jul, só faltava marcá-lo aqui.)*

---

# 4. TAREFAS ABERTAS (por prioridade, depois do P1)

## P1.5 — MEGA-TREINO DE 1 MÊS ⏳ **LANÇADO 19 jul 19:23 UTC** (composição aprovada: «piores mapas»)
- [x] Pré-registo v2 escrito ANTES dos dados: **[`PRE_REGISTO_MEGATREINO.md`](PRE_REGISTO_MEGATREINO.md)**
      (proposta original: [`PROPOSTA_MEGATREINO_1MES.md`](PROPOSTA_MEGATREINO_1MES.md)).
- [x] **A CORRER**: tmux `megaA` (`~/swarm-robotics-tese`, scripts `mega_streamA.sh`):
      u_wall n=28 nos 4 braços (adapt→obj→PPO→SAC) + Sandbox adaptativo n=21, fim ~1 ago;
      tmux `megaB` (`~/swarm-novelty`, `mega_streamB.sh`): ablação anneal (sustain 5/20,
      decay 0,95/0,995 em u_wall+bypass ×7) + bypass adaptativo n=21 + SAC bottleneck n=21
      + perception adaptativo n=21, fim ~3 ago. Arquivo por fase em `~/mega_{A,B}_fase*/`;
      arranque confirmado (Gen 1 26s, w=0,500).
- [ ] Na chegada: verificação `_run{n}` + instalar em `results/mega_1mes/` SEM tocar nos
      modelos ativos; confirmar configs repostos (os scripts repõem no fim — verificar);
      análise M1-M3 do pré-registo v2. **Hard stop de integração na tese: 22 ago.**

## P1.6 — MAPA GRANDE (8.º cenário) 🆕 **código FECHADO a 24 jul; treino só depois do mega-treino**

Ideia do utilizador (24 jul): um mapa **muito maior e composto**, que junte as
dificuldades dos 7 cenários num percurso único, para testar se as conclusões obtidas
em cenários de dificuldade isolada transferem para um ambiente combinado. Desenhado a
partir de um esboço do utilizador, **aprovado visualmente em planta 2D e em 3D antes
de virar código** — e só depois integrado.

**Estado: implementado, testado, NUNCA treinado.** Commits `da0c166` (geometria),
`22922fb` (integração), `ce45b9c` (correções + pré-registo).

- [x] **Geometria aprovada** (r=60): labirinto 103×62 m em 5 zonas — **S** sala de
      partida (aberta, obstáculos, spawn) · **A** gargalo + beco em U (**boca a
      oeste**, virada ao lado por onde o enxame chega) · **B** quatro salas (**cruz
      completa, 4 aberturas**) · **C** porta cooperativa + alternativa longa · **D**
      câmara do ninho. Pior percurso **155 m** (4,5× os 34 m do Quatro Salas; era
      143 m antes de as zonas A e B serem corrigidas a 24 jul — ver o log, ponto 8).
      106 obstáculos **estáticos** (decisão do utilizador).
- [x] **Integrado como `mapa_grande`** em `src/scenarios.py` + `swarm_env_3d.py`.
      Verificado: `obs_dim=111` **igual aos 7 cenários** → os modelos GNN existentes
      abrem o mapa sem alteração nenhuma (zero-shot de topologia já funciona).
- [x] **Isolamento dos 7 cenários da tese** (campanhas fechadas, números já no texto):
      `arena_radius_mapa_grande=60` e `max_steps_mapa_grande=2000` são overrides **por
      cenário**; o `arena_radius` global fica em 15. Novo `THESIS_SCENARIOS` separa "os
      7 da tese" de "todos os cenários" — o mapa aparece nas vistas de operação mas
      **não** nas tabelas de resultados enquanto não tiver campanha avaliada.
      Regressão verificada: os 7 mantêm arena, paredes, obstáculos, steps e geodésico.
- [x] **Botão «Ver o mapa em 3D»** na vista Ao vivo, no MESMO visualizador Ursina dos
      outros mapas (`visualize_mapa_grande.py`), a ler a geometria do **ambiente real**.
- [x] **`dashboard/config.py` deixou de ter cópia dos cenários** — importa de
      `src/scenarios.py`. Já divergia nos rótulos; com um 8.º mapa a entrar era repetir
      o erro que fez o 7.º cenário ser treinado mas nunca avaliado.
- [x] **Pré-registo escrito ANTES de qualquer treino**:
      [`docs/PRE_REGISTO_MAPA_GRANDE.md`](PRE_REGISTO_MAPA_GRANDE.md) — QI7, desenho
      congelado com justificação de cada parâmetro, fases F0/F1/F2, testes M1-M3, regra
      de decisão e modos de falha antecipados.
- [ ] **F0 — smoke test local** (~1 h, GNN, 1 run): só confirmar que arranca. **Não
      produz resultado** e não entra em análise nenhuma.
- [ ] **F1 — zero-shot de topologia**: avaliar os campeões dos 7 cenários neste mapa
      sem retreino (custa horas, não dias; não precisa do servidor). **Correr as DUAS
      condições** de normalização (`--norm-obs mapa` e `--norm-obs treino`) — sem o
      par, um zero confunde topologia com escala da observação. O script é retomável
      (o PC caiu a meio a 24 jul): repetir o mesmo comando salta o que já está feito.
      Fumo validado a 25 jul (Sandbox, 2 ep: 15,5 recolhas/ep nas duas condições).
- [ ] **F2 — treino nativo**: 3 algoritmos × 7 runs × seeds 1-7. **Só depois do
      mega-treino fechar (~3 ago).** Hard stop de integração na tese: **22 ago**.

### ⚠️ Dois bugs apanhados na auditoria de 24 jul (a pedido do utilizador)

Ambos silenciosos — teriam produzido "os 3 algoritmos falham" sem sinal de que a culpa
era do parâmetro. Ficam registados porque a lição é geral:

1. **`max_steps` impossível de cumprir.** v_max = 0,2 m/passo (`move_local` clipado a
   ±1 × 0,2) e o pior spawn está a 126 m ⇒ **629 passos só de ida**. Os 1200 iniciais
   não davam sequer para ida-e-volta (1259). Corrigido para **2000** (folga 3,2× sobre
   a ida — a mesma que o Quatro Salas tem com 500). **Lição: `max_steps` de um cenário
   novo calcula-se a partir da distância geodésica e da velocidade máxima, não por
   analogia com outro cenário.**
2. **`required_to_eat` a 3.** O cenário caía no ramo `else` e exigia 3 agentes
   simultâneos no ninho (raio 1,5 m) ao fim de 143 m — uma 2.ª tarefa cooperativa
   acidental empilhada sobre a navegação. Corrigido para **1**. **Lição: acrescentar um
   cenário obriga a rever TODAS as listas que discriminam cenários por nome**
   (`_nav_scenarios`, `use_geodesic`, `DOOR_SCENARIOS`, `MAZE_SCENARIOS`).

Um terceiro, apanhado antes por teste: `use_geodesic` era uma lista escrita à mão e o
mapa ficou **sem campo geodésico** — num percurso de 143 m, exatamente o mínimo local
que o geodésico existe para eliminar. Passou a derivar de `MAZE_SCENARIOS`.

### Verificações que NÃO alteraram código (mas respondem a perguntas do utilizador)

- **Os robôs saltam por cima das paredes?** **Não.** Forcei os 20 agentes contra a
  parede central com ação +z e +y durante 400 passos: sobem até z≈14,7 m e
  **atravessaram 0**. Colisão é AABB a 3D (paredes de z=−15 a +15) com deslizamento +
  correção de penetração.
- **A porta faz sentido?** **Sim.** Com o painel fechado o caminho custa 155,5 m contra
  128,8 m com ela aberta: há **alternativa (+21%)**, não bloqueia. Cooperar é
  vantajoso, não obrigatório — a estrutura do `cooperative_door_bypass`. (Era
  147,8/119,7 = +24% antes da correção das zonas A e B.)
- **A população chega?** **20 é o valor certo**, apesar de a densidade ser 9× mais
  esparsa (318 vs 35 m²/agente; igualar exigiria 180 agentes). Razão: `obs_dim =
  16+(N−1)×5` **muda com N** — com 20 fica em 111 (igual aos 7 cenários, modelos
  existentes carregam); com 40 seria 211 e PPO/SAC precisariam de arquitetura nova,
  matando a comparação emparelhada. O custo também é super-linear (20→40 = 2,8× o
  tempo). A esparsidade é o problema que o mapa mede, não um defeito a corrigir.

## P2 — Draft cedo ao orientador (fim de julho, NÃO esperar por 15 set)

> ⚠️ **É o item mais atrasado do plano, e o único que não depende de servidor nenhum.**
> O pacote está PRONTO desde 24 jul — falta só o utilizador confirmar 3 pontos e enviar.

- [x] **Pacote preparado (24 jul)**: PDFs datados em `out/envio_orientador_24jul2026/`
      (tese 121 págs + artigo 10 págs, do commit `704a36e` — fontes e PDF em sincronia)
      e o corpo do e-mail em [`EMAIL_ORIENTADOR_24jul2026.md`](EMAIL_ORIENTADOR_24jul2026.md),
      com anexo opcional de resultados. Todos os números verificados contra `main.tex`.
      Na tabela do anexo só vão a negrito as superioridades **significativas** — o
      Gargalo (p=0,21), o Muro em U e a Porta c/ Alternativa (p=0,85) são empates, e
      destacar o maior valor reintroduziria o erro que o commit `0c25d9e` corrigiu.
- [ ] **Enviar** (falta confirmar: qual foi a última versão que o Prof. viu de facto;
      a capa 2026; e ler o Iskandar antes da reunião — ver P3).
- [ ] **Confirmar com o utilizador a capa: 2025→2026** (mudada a 18 jul, por confirmar).
- [ ] Perguntar o alvo do artigo (conferência vs submissão interna) — deadlines externos
      condicionam o resto. Modelo de formato: artigo IWSSIP em
      `C:\Users\gonca\Desktop\artigos prof\`. Título: recomendação no anexo da
      `PROPOSTA_TREINO_FINAL.md` (opção 1).

## P3 — Tarefas do UTILIZADOR (facilitar, lembrar, verificar consequências)
- [ ] **LER o Iskandar** (PDF pronto: `Desktop/Tese/Iskandar_PhD_2025_DRL_Swarm_Robotics.pdf`,
      RL vs PSO ~págs 14-42) — é o único comparativo dos 58; tudo o que a tese diz dele
      veio de resumos + varrimentos. Depois da leitura: grep `[Ii]skandar` em
      `main.tex`/`artigo.tex` e confirmar frase a frase.
- [ ] Ler um dos artigos NEAT (a afirmação "arenas sem estrangulamentos decetivos" assenta
      no abstract; risco baixo).
- [ ] Rever o PDF do artigo.
- [x] **Título DECIDIDO (20 jul): MANTER o atual** — "Aprendizagem Adaptativa versus
      Robustez Estática: Comparação de Aprendizagem por Reforço e Neuroevolução para
      Controlo de Enxames". A campanha adaptativa (19 jul) revalidou o contraste
      adaptativo↔estático, pelo que o anexo de títulos da `PROPOSTA_TREINO_FINAL.md`
      (16 jul, que recomendava trocar) está DESATUALIZADO — não reabrir.

## P4 — Agosto: ciclos de revisão
- [ ] Incorporar feedback do orientador (esperar 1-2 ciclos).
- [ ] Fechar o artigo (com o alvo decidido).
- [ ] Trazer do servidor o CSV do braço Novelty preliminar de `~/swarm-novelty` se ainda
      existir (dado como PERDIDO em `cf44368`; menor).

## P5 — 1-15 set: SÓ polimento (a tese composta a 15 set é INEGOCIÁVEL)
- [ ] Verificação final: refs, acrónimos, listas de figuras/tabelas, normas ISCTE da capa.
- [ ] Nada de mudanças de conteúdo nesta janela salvo exigência do orientador.

## P6 — set/out: defesa
- [ ] Slides.
- [ ] **Modo Demo do dashboard (F4)** — único pedaço do dashboard por fazer (ecrã único:
      visualizador + heatmap + métricas para o júri). O dashboard é `python -m dashboard.app`
      (NiceGUI); o launcher antigo foi APAGADO a 16 jul.
- [ ] Ensaiar respostas com o `REPRODUZIR.md` ("de onde vem este número?" → resposta na hora).

## Opcional (só se sobrar tempo de servidor E o utilizador pedir)
- Ablação LiDAR 8→16 raios no Muro em U (7 runs @195min) — testa "deceção sob
  observabilidade parcial". Cortar primeiro se algo derrapar.

---

# 5. O QUE NÃO FAZER (decisões tomadas — não reabrir)

- ❌ Repetir a campanha 7×7 com mais runs (~28 dias de GNN; retorno ≈ 0).
- ❌ Política de atenção por gradiente em SB3 (fica como trabalho futuro, já declarado).
- ❌ Reescrever secções fechadas e coerentes com os dados, salvo exigência do P1/P3.
- ❌ Reabrir as decisões de consolidação de 15 jul (figuras de 26 jun ficam no backup;
      galeria de 14 jul é a boa).
- ❌ Concluir seja o que for de números de treino ou de evals desfasados dos modelos.
- ❌ Lançar treinos por iniciativa própria.

---

# 6. ARMADILHAS (o custo de as esquecer já foi pago — mais de uma vez)

| nº | Armadilha | Antídoto |
|---|---|---|
| 1 | `analise_treino_24h.md` tem conclusões ERRADAS | fonte de verdade = `eval_summary.csv` |
| 2 | Boxplots da sessão 09-06 degenerados (1 run) | não usar |
| 3 | **Números de TREINO ≠ avaliação** | só `eval_summary.csv`/`eval_by_run.csv`, da MESMA data dos modelos |
| 4 | `success = food>0` é métrica fraca | reportar sempre também recolhas/ep |
| 5 | `comparacao_barras_geral` mistura escalas | usar só como demo do fitness exploitation |
| 6 | BOM do PS5.1 parte YAMLs | usar a ferramenta Edit; scripts com `sys.stdout.reconfigure(encoding="utf-8")` |
| 7 | Nomes/conteúdo de referências fabricados | verificar NOMES e afirmações contra o PDF, não só DOIs; os 2 `.bib` juntos |
| 8 | `.pth`/`.zip` sobrescrito pelo último run | verificar `_run{1..7}` por cenário; campeão via `.meta.json` |
| 9 | `results/models/` com modelos de campanha ANTERIOR | **`python scripts/pos_campanha.py` a CADA chegada** |
| 10 | `plot_robustez.py` desemparelha se usar o summary das 7 runs | a base é `eval_{algo}_{cen}.csv` (corrigido 18 jul — não reverter) |
| 11 | `eval_scalability.py` re-avalia modelos do disco | usar `--replot` enquanto os modelos locais não forem os da campanha |
| 12 | Números antigos sobrevivem a reescritas | 73,3 / 67,7 / 0,77 são pré-treino_fds; grep antes de confiar |

---

# 7. SERVIDOR ISCTE (resumo operacional)

- **VPN do ISCTE ligada** primeiro, senão timeout. Máquina: `SERVIDOR_DE_TREINO` (`dellicious`),
  user `goncalo`, password pessoal (não está no repo). Host key ed25519:
  `SHA256:HOSTKEY_REMOVIDA`. 64 vCPU, 125 GiB RAM, sem GPU.
- Para o Claude operar sozinho (password interativa bloqueada): `plink` (comandos) e
  `pscp` (ficheiros) com `-batch -hostkey SHA256:... -pw '<PASS>'`.
- Código vive em `~/swarm-robotics-tese/` (+ dirs isolados por campanha, ex.
  `~/week_{A,B}*`). Ver treinos: `tmux ls`; `tmux capture-pane -pt <sessão> -S -60`.
  **Nunca Ctrl+C num tmux de treino.**
- Extração robusta: `tar czf` no servidor → `pscp` de 1 ficheiro → extrair em `out/`.
  Tutorial completo passo-a-passo: `PLANO_DE_ATAQUE.md` §4 (arquivo) e
  `memory/server_training_setup.md`.
- Pipeline local pós-chegada: `pos_campanha.py` → `eval_by_run`/`eval_suite` →
  `statistical_tests.py` → `gerar_figuras_7d.py --install-oficial` (figuras canónicas) →
  recompilar tese. Detalhe: `docs/REPRODUZIR.md`.

---

# 8. MAPA DE DOCUMENTOS E DADOS

| O quê | Onde |
|---|---|
| **Este plano (único vivo)** | `docs/PLANO_MESTRE.md` |
| Arquivo histórico (armadilhas na origem, tutorial servidor, cronologia) | `docs/arquivo/PLANO_DE_ATAQUE.md` |
| Plano de 15 jul (superado por este) | `docs/arquivo/PLANO_ATAQUE_FINAL.md` |
| Pré-registo da campanha adaptativa | `docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md` |
| Pré-registo do mega-treino (P1.5) | `docs/PRE_REGISTO_MEGATREINO.md` |
| Pré-registo do mapa grande (P1.6) | `docs/PRE_REGISTO_MAPA_GRANDE.md` |
| Draft do e-mail ao orientador (P2) | `docs/EMAIL_ORIENTADOR_24jul2026.md` |
| Reprodutibilidade (número → CSV → script) | `docs/REPRODUZIR.md` |
| Proposta/cautelas do treino final + títulos do artigo | `docs/PROPOSTA_TREINO_FINAL.md` |
| SLR (protocolo, screening, pipeline) | `docs/PROTOCOLO_SLR.md`, `docs/slr/` |
| Tese / Artigo | `Tese/main.tex` (117 págs) / `Artigo/artigo.tex` (9 págs) |
| Figuras da tese | `Tese/images/resultados/` (36 PNGs, mecanismo `\figresultado`) |
| Eval canónica 7d | `results/graficos_tese/final_7d/eval_by_run_7d.csv` (torre) |
| Novelty P1/P2 | `results/novelty_final/{uwall,bypass}/` (torre) |
| Escalabilidade | `results/estatisticas/escalabilidade_*.csv` |
| Memória persistente | `memory/` (índice em `MEMORY.md`) |

---

# 9. CALENDÁRIO (atualizado a 19 jul)

| Janela | Foco |
|---|---|
| **19-25 jul** | **P1**: chegada da campanha adaptativa → pré-registo T1-T4 → integração (ou reporte negativo) |
| 26 jul - 3 ago | P2: draft completo ao orientador; capa confirmada; alvo do artigo perguntado |
| ago | Ciclos de revisão com o orientador; artigo fechado; utilizador lê Iskandar/NEAT |
| 1-15 set | SÓ polimento + buffer. **Versão composta a 15 set — inegociável** |
| 15-30 set | Entrega formal (30 set) |
| out | Defesa: slides + modo Demo (F4) + ensaio com REPRODUZIR.md |

Buffer real: ~2 semanas. Se algo derrapar, corta por esta ordem: Opcional (ablação) →
F4 fancy → profundidade da revisão do artigo. A tese está num estado em que **não fazer
nada de novo já dá uma tese defensável** — o risco maior é estragar o que está fechado,
não faltar trabalho.
