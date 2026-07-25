# Pré-registo — Campanha do MAPA GRANDE (8.º cenário)

> **Escrito a 24 jul 2026, ANTES de existir qualquer dado de treino ou avaliação
> neste mapa.** Segue o precedente do `PRE_REGISTO_NOVELTY_ADAPTATIVO.md` (cuja regra
> de decisão foi cumprida sem desvios a 19 jul) e do `PRE_REGISTO_MEGATREINO.md`.
>
> **Estado ao escrever:** o mapa está integrado no simulador (`classic_scenario:
> mapa_grande`, commit `22922fb`), verificado por 6/6 suites de teste, e **nunca foi
> treinado**. O mega-treino P1.5 ocupa o servidor até ~3 ago; esta campanha só arranca
> depois. Análise: SÓ com `eval_by_run.csv` (armadilha nº3); unidade estatística =
> média por run; Mann-Whitney U exato + δ de Cliff.

---

## 1. Pergunta e enquadramento

**QI7 (nova):** as conclusões obtidas em sete cenários de dificuldade isolada
transferem-se para um ambiente que **combina** essas dificuldades a uma escala 4×
maior — ou a composição faz emergir modos de falha que os cenários isolados não
revelam?

Motivação: os 7 cenários da tese testam **uma** dificuldade cada (um gargalo, um
beco, quatro salas, uma porta). O mapa grande junta-as num percurso único de ~143 m
(pior caso) contra 34 m do Quatro Salas. É a diferença entre saber resolver cada
exercício e resolver o problema composto — a objeção mais natural a um *benchmark*
por cenários isolados.

**Porque é que isto interessa à tese:** a contribuição mais forte é a transferência
Zero-Shot para **dimensões de enxame** não vistas (28/28 células a 100%). Este mapa
estende a mesma pergunta a **topologia** não vista. Se a GNN transferir, o argumento
da representação (grafo com atenção) passa de "invariante a N" a "invariante a N *e*
robusto a composição".

---

## 2. Desenho (congelado antes dos dados)

**Cenário** (geometria fixa; ver `visualize_mapa_grande.py` e a planta em
`results/graficos_tese/mapa_grande/`): arena r=60 m; labirinto 103×62 m em 5 zonas
de oeste para este — **S** sala de partida (aberta, obstáculos, spawn) · **A**
gargalo + beco em U (boca virada a oeste, para o lado de onde o enxame chega) ·
**B** quatro salas (cruz completa, 4 aberturas) · **C** porta cooperativa +
alternativa longa · **D** câmara do ninho. *Zonas A e B corrigidas a 24 jul — ver a
emenda na secção 7; a geometria de `22922fb` não cumpria estes dois rótulos.*

| Parâmetro | Valor | Porquê (decidido agora, não depois) |
|---|---|---|
| `num_agents` | **20** | Mantém `obs_dim=111`, **igual aos 7 cenários** → comparação emparelhada e os modelos existentes carregam sem alteração. Com N=40 a dimensão passa a 211 e PPO/SAC precisariam de arquitetura nova. |
| `max_steps` | **2000** | A 0,2 m/passo (o limite **por eixo**) o pior ponto do mapa está a 777 passos **só de ida**: folga **2,6×** (2,9× a partir do pior spawn), acima do mínimo de 2,5× exigido. Conservador — o módulo máximo real do deslocamento é 0,2·√3 = 0,346 m/passo. |
| `required_to_eat` | **1** | A cooperação que este mapa mede está na **porta**. Exigir 3 no ninho empilharia uma 2.ª tarefa cooperativa e a métrica deixaria de isolar a navegação. |
| Obstáculos | **106, estáticos** | Estáticos, o mapa mede navegação+descoberta e é reprodutível. Móveis acrescentariam um eixo dinâmico que se confundiria com a dificuldade do labirinto. |
| Porta | com alternativa | Verificado: fechada custa +28,1 m (+23%), **não bloqueia**. Cooperar é vantajoso, não obrigatório. |

**Tudo o resto — recompensas (food 300), física, LiDAR (8 m, 8 raios), população,
sigma — congelado e idêntico às campanhas anteriores.** Sem isto a comparação com os
7 cenários não é limpa.

**Condições:** 3 algoritmos (GNN adaptativo, PPO, SAC) × **7 runs** × seeds 1-7,
orçamento igualado por algoritmo. GNN com Novelty **adaptativo** (w₀=0,5, sustain=10,
decay=0,98) — não o objetivo puro: a QI6 mostrou que o adaptativo domina o objetivo
onde há descoberta a fazer e não custa onde não há, e este mapa é o caso extremo de
descoberta (LiDAR de 8 m numa arena de 120 m ⇒ o agente vê ~7% da largura).

### ⚠️ Orçamento por run — MEDIDO a 24 jul, antes de qualquer treino

O custo por geração do GNN **não** é comparável ao dos 7 cenários, e isto muda o
orçamento da campanha. Uma geração custa `pop_size × eval_episodes × max_steps`
passos de simulação:

| | `max_steps` | passos/geração | a 70 passos/s | 195 min/run dá |
|---|---|---|---|---|
| 7 cenários da tese | 500 | 60 000 | **14 min** | **14 gerações** |
| **mapa_grande** | 2000 | 240 000 | **57 min** | **3,4 gerações** |

**3,4 gerações não é evolução — é ruído de inicialização.** Com 195 min/run o GNN
não teria hipótese, e a leitura "o evolutivo falha no mapa composto" seria um
artefacto do orçamento, não um resultado. É exatamente o erro que a tese já
identificou uma vez (o "colapso do evolutivo" que era artefacto da fitness).

**Orçamento pré-registado para F2:** **780 min/run para o GNN** (≈13,7 gerações —
equipara-se às 14 das campanhas fechadas) e **192 min/run para PPO e SAC** (mantém
a proporção 4:1 usada em todas as campanhas anteriores). Custo total: **~3,8 dias
num stream, ~1,9 em dois** — cabe na janela de 19 dias entre o fim do mega-treino
(~3 ago) e o hard stop de 22 ago.

*Fundamentação da equiparação:* o critério não é "igualar minutos" mas "igualar
**gerações de evolução**", que é a unidade de otimização do GNN. Igualar minutos
entre mapas com episódios 4× mais longos seria dar ao GNN 1/4 da otimização e
chamar-lhe comparação justa.

⚠️ **Ainda a registar aqui antes do unblinding:** o `num_generations` efetivamente
alcançado por run (o tempo é o limite, não as gerações) e o tempo real da 1.ª fase.

---

## 3. Fases

| Fase | O quê | Objetivo |
|---|---|---|
| **F0** | Treino local de ~1 h (GNN, 1 run) | **Smoke test.** Só confirma que arranca, que a fitness sobe e que os artefactos aparecem. **Não produz resultado nenhum** e não entra em nenhuma análise. |
| **F1** | **Zero-Shot de topologia**: avaliar os campeões dos 7 cenários (GNN/PPO/SAC, campanha 7d) neste mapa, **sem retreino** | Custa horas, não dias. Responde a "o que já sabíamos transfere?" |
| **F2** | Treino nativo: 3 algos × 7 runs × seeds 1-7 | A comparação principal (M1-M3 abaixo). |

F1 antes de F2 de propósito: o zero-shot é barato e a sua leitura não depende do
treino nativo — e o contraste F1 vs F2 é, em si, um resultado.

### ⚠️ F1 tem TRÊS confundentes, e por isso corre em QUATRO condições

> **Escrito em duas datas.** O confundente (b) — a escala da observação — foi
> registado a **24 jul, com zero dados**. Os confundentes (c) e (d) foram
> acrescentados a **25 jul, já com 5 células da condição natural medidas**
> (GNN: Sandbox 16,3 · Muro em U 2,3 · Gargalo 0,0 · Quatro Salas 0,0 · Porta
> 0,0). Não houve dados nenhuns das condições novas quando a leitura abaixo foi
> pré-comprometida, mas **é honesto declarar que a suspeita nasceu de ver os
> zeros** — e não antes. Ver a emenda datada na secção 7.

**Resumo:** um zero no F1 tem quatro causas possíveis e só uma delas é a pergunta
da QI7. Cada condição desliga uma causa e deixa tudo o resto igual.

**(a) e (b) — texto original de 24 jul, mantido como foi escrito:** as distâncias
da observação (ao ninho, à porta, a cada vizinho) são normalizadas pelo **raio da
arena**. O mapa grande corre a r=60 e os 7 cenários a r=15, logo o mesmo modelo,
sem nada mudar nele, recebe todas as distâncias **comprimidas 4×** (÷120 em vez de
÷30): um vizinho a 15 m, que no treino lia 0,50, passa a ler 0,125.

Sem tratamento, um zero-shot a zero admite **duas** explicações que os dados não
separam: (a) a topologia composta é demasiado difícil — a pergunta da QI7; ou (b) a
observação chega fora da escala em que a política foi treinada — um artefacto de
implementação. Atribuir (a) sem excluir (b) seria repetir, noutra roupagem, o erro
do "colapso do evolutivo". *(A 25 jul percebeu-se que as explicações não eram duas
mas quatro — daí (c) e (d).)*

**(c) Obstáculos — os campeões dos labirintos nunca viram um.** Medido a 25 jul,
cenário a cenário: dos 8 cenários **só o Sandbox (100) e o mapa_grande (106) têm
obstáculos dispersos**; `u_wall`, `bottleneck`, `four_rooms`, `cooperative_door`,
`cooperative_door_bypass` e `cooperative_perception` têm **zero**. Um campeão do
Gargalo nunca encontrou um obstáculo em toda a sua evolução, e no mapa encontra
106 — o LiDAR passa a acusar coisas que nunca existiram no mundo dele. "0 recolhas"
pode então ser a topologia composta **ou** só isto.

**(d) As 4 features da porta na observação.** `obs[12:16]` (direção + distância
egocêntricas à porta) são **identicamente 0** no treino de todos os cenários sem
porta e ficam **vivas** no mapa_grande, que tem porta: medido `[0,999 0,043 0
0,629]`. São quatro entradas mortas que passam a carregar sinal — distribuição
nova à entrada da rede, sem relação com a dificuldade do labirinto.

**Pré-registado:** o F1 corre nas quatro condições, com as mesmas seeds:

| Condição | O que muda | O que isola |
|---|---|---|
| **natural** (`--norm-obs mapa`) | nada | O que acontece de facto ao pegar num campeão e largá-lo no mapa novo. **É a condição principal.** |
| **escala** (`--norm-obs treino`) | `obs_norm_radius` = 15 ⇒ ÷30 | Distâncias na escala do treino, física do mapa inalterada. |
| **obstáculos** (`--controlo sem_obstaculos`) | 106 ⇒ 0 obstáculos | O mundo passa a ser só paredes, como nos labirintos onde os campeões treinaram. |
| **porta na obs** (`--controlo sem_porta_obs`) | `obs[12:16]` ⇒ 0 | Repõe os zeros do treino **sem tirar a porta do mundo** (continua a ser preciso abri-la ou contorná-la). |

*Leitura pré-comprometida (idêntica para as três condições de controlo):* se a
condição de controlo der **o mesmo** que a natural, essa causa está excluída e
reporta-se só a natural (o controlo vai para apêndice). Se **divergir**, o
zero-shot de topologia está confundido com essa causa e **é isso que se reporta** —
sem escolher a condição que der o número melhor, e sem transformar a condição de
controlo na condição principal. Um controlo que ressuscite os campeões **não**
salva a leitura "a topologia é dura": desmente-a.

*O que nenhuma destas condições resolve, e fica declarado como limitação:* na
condição **escala** as distâncias passam a valer **mais de 1** (até ≈2,5 na
bússola da porta), valor que nenhum modelo viu em treino. As duas condições de
normalização estão fora da distribuição de treino de maneiras diferentes —
comprimida (natural) ou fora de gama (controlo). Não há terceira hipótese sem
retreinar, e retreinar é a fase F2.

As condições ficam nas colunas `NormObs` e `Controlo` do CSV (convivem no mesmo
ficheiro, com a impressão digital do ambiente por condição); as figuras usam
sempre `(mapa, base)`.

*Nota:* cada controlo muda **uma** coisa e mais nada — verificado em
`tests/test_mapa_grande.py` (`test_normalizador_da_obs`,
`test_controlo_sem_obstaculos`, `test_controlo_porta_na_obs`): as paredes, o
ninho, o spawn e as restantes 107 dimensões da observação ficam bit-a-bit iguais.
Nos 7 cenários todas as chaves são no-op por omissão, e as observações continuam
bit-a-bit iguais às das campanhas fechadas.

---

## 4. Hipóteses e testes confirmatórios

Métrica: `food_collected` (recolhas/ep) da avaliação determinística (20 ep/run,
seeds emparelhadas), via `eval_by_run.py`. Sucesso = descritivo, nunca teste.

- **M1 — GNN vs métodos de gradiente (magnitude).** GNN adaptativo vs PPO e vs SAC,
  bilateral, sobre médias por run (n=7).
  *Expectativa pré-registada:* a GNN **não é inferior** a nenhum dos dois. Não se
  pré-regista superioridade: nos 7 cenários a GNN ganha em 3, empata em 2 e perde
  no Sandbox — não há base para prever domínio num mapa composto.
- **M2 — Convergência.** Taxa de runs que atingem ≥1 recolha (descritivo) e runs a
  100% (descritivo). Com n=7, **nenhuma inferência sobre proporções** (Fisher 7/7 vs
  3/7 dá p=0,070 — não chega).
- **M3 — Uso da porta cooperativa.** Fração de episódios em que a porta é aberta,
  por algoritmo (descritivo + δ). Testa se a cooperação emerge quando é *vantajosa*
  mas não obrigatória — a pergunta que o `bypass` levanta, aqui a 143 m de distância.

### Regra de decisão sobre a QI7 (pré-comprometida)

- **Sobe a resultado** (secção nova no Cap. de Resultados + QI7 nas Conclusões)
  **se** F2 produzir ≥5/7 runs convergentes em pelo menos um algoritmo **e** M1 for
  interpretável (i.e., a campanha não degenerou).
- **Resultado negativo honesto, reportado na mesma** se nenhum algoritmo convergir:
  passa a evidenciar o **limite** dos três métodos sob composição+escala, e reforça a
  limitação já declarada na tese. Um mapa que nenhum algoritmo resolve **é** um
  resultado — não é uma campanha falhada, e não se repete com parâmetros diferentes
  à procura de um número melhor.
- **F1 (zero-shot) reporta-se em qualquer caso**, mesmo que dê 0 em todas as células.

### Compromissos de reporte (não negociáveis)

1. **Todos os 3 algoritmos, todos os 7 runs, todas as fases.** Sem cherry-picking.
2. Convergência = descritivo; magnitude (Mann-Whitney) = teste. Com n=7 o peso está
   no **δ**, não em cruzar 0,05.
3. **O mapa não entra nas tabelas dos 7 cenários** (`tab:res_eval`, `tab:res_signif`).
   Vai para uma secção própria: os 7 têm campanhas com orçamento e protocolo
   próprios, e misturá-los seria comparar coisas diferentes na mesma linha. Por isso
   `THESIS_SCENARIOS` está separado de `SCENARIOS` no código.
4. Se a campanha fechar depois de **22 ago** (hard stop de integração, herdado do
   `PRE_REGISTO_MEGATREINO.md`), **não entra na tese** — vai para a defesa.
5. Qualquer desvio a este documento é datado abaixo, nunca silencioso.

---

## 5. Modos de falha antecipados (escritos antes, para não serem racionalizados depois)

| Risco | Sinal | Resposta pré-decidida |
|---|---|---|
| Nenhum algoritmo chega ao ninho | 0 recolhas em todos os runs de F2 | **Reportar como está.** É o resultado, não um bug a contornar. Verificar só que o geodésico existe e que `max_steps` é o registado. |
| PPO/SAC não convergem em 2000 passos | fitness plana | Reportar. O custo por episódio é 4× o dos outros cenários — faz parte do que o mapa mede. |
| A porta nunca é aberta | M3 ≈ 0 em todos | Resultado legítimo: com alternativa a +23%, pode não compensar. **Não** tornar a porta obrigatória a meio. |
| Runs degenerados (agente preso na sala S) | recolhas 0 com fitness de homing alta | Reportar o run. Não substituir seeds. |
| Custo de treino maior que o previsto | fase F2 não fecha até 22 ago | Cortar F2 para 2 algoritmos (GNN + o melhor dos gradientes nos 7), **declarando-o**. Nunca reduzir runs abaixo de 7. |

---

## 6. Mecânica (quando a campanha fechar)

1. `python scripts/pos_campanha.py` (armadilha nº9 — modelos de campanhas
   anteriores contaminam evals locais).
2. Confirmar `_run{1..7}` por algoritmo (armadilha nº8).
3. Instalar em `results/mapa_grande/` **sem tocar nos modelos ativos** (precedente
   de 19 jul).
4. Repor configs no servidor.
5. `eval_by_run.py` → `statistical_tests.py` → M1-M3 → regra de decisão.

---

---

## 7. Emendas (datadas — nada muda em silêncio)

### 24 jul 2026, fim do dia — auditoria ao mapa antes de treinar (0 dados existentes)

Segunda passagem ao código do mapa, ainda **antes de qualquer treino** e com **zero
dados de F1/F2 no repositório** (a corrida de F1 tinha 2 de 21 células e foi
interrompida por falha de energia; foi descartada, não analisada). Nada aqui foi
decidido à vista de resultados.

1. **Confundente da normalização da observação** — documentado acima; F1 passa a ter
   condição de controlo. É a emenda com consequência científica.
2. **Disco livre à volta do ninho** (`nest_radius + obstacle_radius + 0,5`). Faltava:
   o `_spawn_obstacles` genérico tem esta regra desde sempre e o
   `_spawn_obstacles_mapa_grande` não a herdou. Em **24% dos episódios** havia um
   obstáculo dentro da zona de recolha (raio 1,5 m) e num deles a 0,36 m do centro —
   um estorvo à entrega **sorteado por episódio**, isto é, variância entre runs que a
   avaliação emparelhada não cancela. Sem a correção, parte do desvio-padrão de F2
   seria layout, não algoritmo.
3. **Clareira de spawn a cobrir a caixa toda.** A clareira era um círculo de raio
   0,085·W e a caixa de spawn um retângulo cuja diagonal é maior — os cantos ficavam
   de fora e **0,2% dos agentes nasciam dentro de um obstáculo** (penalização e
   empurrão no passo 0). A caixa e a clareira passam a derivar da mesma função
   (`_mapa_grande_spawn_box`), que era o que permitia as duas divergirem.
4. **`max_steps=2000` mantém-se.** A tabela original dizia "v_max = 0,2 m/passo ⇒ 629
   passos de ida": é o limite por eixo. O deslocamento é a soma vetorial de três
   componentes ortogonais, pelo que o módulo máximo é 0,2·√3 = **0,346 m/passo**.
   **O número registado é conservador** e a decisão não muda.

### 24 jul 2026, fim do dia (cont.) — duas zonas não cumpriam o rótulo

Auditoria **topológica** ao desenho (a anterior era ao código). Ainda sem qualquer
dado. Duas das cinco zonas não compunham a dificuldade que o nome anuncia — e é
essa composição que fundamenta a QI7:

5. **O beco em U não era armadilha nenhuma.** A bússola do ninho é **euclidiana**:
   um bolso só arma quando a linha reta agente→ninho lhe entra pela boca e bate no
   fundo. O U tinha a boca virada a **este** e o ninho está a este — os agentes
   chegavam-lhe pelas costas e contornavam-no. Medido sobre 60 pontos de entrada na
   zona A: **0% eram atraídos para dentro** do bolso, e o caminho ótimo passava a
   **15,3 m** do interior. Eram 162 m² (3% do labirinto) sem função.
   **Corrigido espelhando o U** (fundo a este, boca a oeste): passa a **37%**.
   A zona A passa a compor de facto a deceção sob observabilidade parcial do
   `u_wall`, e não só o gargalo. O desvio continua a existir e é livre — a rota
   correta (para sul, até ao gargalo) não foi tocada.
6. **A zona "Quatro Salas" eram duas salas.** Tinha **uma** parede horizontal com
   **uma** abertura. O `four_rooms` original é uma **cruz** (eixo horizontal +
   vertical) com **quatro** aberturas ligando NO-SO-SE-NE em ciclo, sem atalho pelo
   centro. **Corrigido** com a cruz completa, aberturas a 0,63 do meio-vão (a
   proporção do original) e **deslocadas** da entrada (y=−H/4) e da saída (y=+H/4)
   da zona — alinhadas, a travessia seria uma linha reta. Verificado: selando a
   cruz, o espaço da zona parte-se em **4 componentes de área igual** (251/251/250/250 m²).

**Consequências medidas, todas verificadas depois da mudança:**

| | antes | depois |
|---|---|---|
| Espaço livre / componentes ligadas | 5352 m² / **1**, 0 ilhas | 5252 m² / **1**, 0 ilhas |
| Percurso ótimo spawn→ninho | 116,8 m | **128,8 m** (desvio 1,34× → **1,47×**) |
| Pior percurso do mapa | 143,5 m | **155,4 m** |
| Folga do `max_steps=2000` (a 0,2 m/passo) | 3,2× | **2,6×** (2,9× do pior spawn) — acima do mínimo 2,5× |
| Porta: custo da alternativa | +24% | **+21%** (continua vantajosa e não obrigatória) |
| Atração para o bolso do U | 0% | **37%** |
| Salas na zona B | 2 | **4** |

O mapa **continua a ser resolúvel**: teste local de fumo (25 jul, GNN campeão do
Sandbox, zero-shot, 2 ep) dá **15,5 recolhas/ep, 100% de sucesso** na condição
natural e 14,5 na de controlo. Não é resultado — é a confirmação de que a
geometria mais dura não tornou a tarefa impossível antes de gastar servidor.

`max_steps` **não** sobe: 2,6× cumpre o mínimo pré-registado, e subi-lo aumentaria
proporcionalmente o custo por geração (já 57 min), que é o recurso escasso.

**Consequência operacional:** os pontos 2 e 3 alteram o sorteio dos obstáculos, logo
o mapa gerado por cada seed. Qualquer avaliação anterior a esta data **não é
comparável** com as que vierem — por isso o CSV do F1 passou a guardar uma impressão
digital do ambiente (`env_hash`) e recusa-se a retomar por cima de dados de outro
mapa. Os 7 cenários da tese ficam **bit-a-bit iguais** (verificado por comparação
direta com a versão anterior do simulador, erro 0,0e+00 em observações, recompensas
e posições).

### 25 jul 2026 — dois confundentes novos, encontrados **com 5 células já medidas**

**Declaração de honestidade, primeiro.** Ao contrário das emendas de 24 jul, esta
foi escrita **depois de ver dados**: a corrida oficial de F1 (condição natural)
tinha 5 das 18 células fechadas, todas do GNN — Sandbox 16,3 · Muro em U 2,3 ·
Gargalo 0,0 · Quatro Salas 0,0 · Porta Cooperativa 0,0 (20 ep/célula). Foram os
três zeros que motivaram procurar mais causas. Nenhuma das condições novas tinha
sido corrida quando a leitura foi pré-comprometida (secção 3), e nenhuma célula
já medida foi apagada ou repetida — mas a ordem dos acontecimentos fica registada
porque é ela que determina o peso que estes controlos podem ter num argumento.

7. **Obstáculos (c).** Medição do nº de obstáculos por cenário: só o Sandbox (100)
   e o mapa_grande (106) têm; os outros seis têm **zero**. O único campeão que
   alguma vez treinou com obstáculos é **o único que recolhe alguma coisa** no
   mapa (16,3 vs ≈0). A correlação é perfeita nas 5 células medidas e é uma
   explicação alternativa completa para o resultado — que ninguém tinha visto
   porque a lista de obstáculos por cenário nunca fora comparada.
   **Controlo novo:** `--controlo sem_obstaculos` (`num_obstacles_mapa_grande: 0`).
8. **Features da porta (d).** `obs[12:16]` medido a zero em `none`/`u_wall`/
   `bottleneck`/`four_rooms` e a `[0,999 0,043 0 0,629]` no mapa_grande.
   **Controlo novo:** `--controlo sem_porta_obs` (`obs_zero_door_feats: true`).
   Zera **só** essas 4 dimensões; a porta continua no mundo, a ter de ser aberta
   ou contornada.
9. **Limitação declarada, sem correção possível dentro do F1:** na condição
   `--norm-obs treino` as distâncias passam a >1 (até ≈2,5), fora da gama de
   treino. As duas condições de normalização são ambas OOD, de maneiras opostas.
   Fica escrito em vez de descoberto por um arguente.

**O que NÃO mudou:** a condição natural continua a ser a principal; nenhuma célula
foi repetida; a impressão digital da condição base mantém-se `267a7b547aed`
(verificado depois das alterações ao ambiente — os dois controlos são no-op por
omissão). A condição `sem_obstaculos` tem, de propósito, outra digital
(`dd557291eaa5`): é outro mundo, e o CSV guarda a digital **por condição** para
não confundir "controlo" com "o mapa mudou".

**Auditoria independente do mapa feita no mesmo dia** (o mapa não tem culpa dos
zeros, e isso teve de ser provado antes de os interpretar):

| Verificação | Resultado |
|---|---|
| Caminho ao ninho **com** os 106 obstáculos, 8 seeds | 0/20 agentes sem caminho; idem com a **porta fechada** (alternativa +26 m) |
| Componentes do espaço navegável do retângulo | 1 (as outras 4 são as bolsas seladas entre o retângulo e o círculo da arena, onde ninguém nasce nem entra) |
| Oráculo (descer o gradiente geodésico) | **52 recolhas/ep** — o mapa é resolúvel com folga |
| Pior percurso medido a partir dos spawns reais | 138,5 m ⇒ 692 passos de ida ⇒ folga **2,89×** |
| Folga lateral do caminho ótimo | mín. 0,30 m, 20% do percurso <0,5 m — **igual aos 7 cenários** (u_wall 49%, four_rooms 11%) |

Testes novos que fixam isto: `test_atravessavel_com_obstaculos` (o campo geodésico
do ambiente só conhece paredes — um obstáculo a selar um corredor não dava erro
nenhum), `test_controlo_sem_obstaculos`, `test_controlo_porta_na_obs`.
17/17 a passar.

### 25 jul 2026, 23h — o F1 desse dia é ANULADO: campeões da campanha errada

Nada muda no desenho. Muda o que conta como dado: **a corrida de F1 de 25 jul
(18 células, 360 episódios, ~6 h) não é evidência de nada e não é reportada.**

**O que aconteceu.** O `eval_zeroshot_mapa.py` carregava os campeões de
`results/models*` sem verificar de que campanha eram. Os desse PC são de **24
jun**; a campanha que a tese reporta é a de **2-9 jul**. Foram avaliados os
campeões de antes da fitness de *homing*.

**Como se sabe que é isso, e não uma questão de datas:** os campeões GNN de 24
jun dão **0,0 no seu próprio cenário de treino** (`eval_summary.csv` de 23 jun:
Gargalo, Quatro Salas e Porta Cooperativa a zero) enquanto a tese reporta 121,4 ·
59,8 · 69,8 nessas células. São modelos partidos, e um modelo partido dá zero no
mapa_grande por razões que nada têm a ver com a topologia — que é precisamente o
que o F1 mede.

**Consequência para a leitura pré-comprometida da secção 3:** a linha do GNN sai
inteira; as de PPO e SAC descrevem modelos que funcionam no cenário deles (41,4 e
36,5 no Gargalo; 66,6 e 62,3 na Porta Cooperativa) e mesmo assim dão 0 no mapa —
essas continuam de pé, sujeitas aos confundentes já declarados. **A leitura "os
campeões dos labirintos decoraram a geometria" fica sem suporte** e não é escrita
em lado nenhum.

**Guarda posta no script antes de repetir** (é a razão de esta emenda existir em
vez de a corrida ser só repetida em silêncio):
- `--models-dir` — a raiz dos modelos deixa de estar em duro. Os campeões da
  campanha 7d vêm de `~/eval7d.tar.gz` e `~/run7d_mlp` para uma pasta **isolada**
  (`results/models_7d/`), nunca por cima dos `results/models*` ativos, que um
  treino a decorrer reescreve (armadilha nº9).
- **Guarda de campanha**: a data de cada campeão (sidecar `.meta.json`, senão o
  mtime) é verificada contra a janela `2026-07-02`–`2026-07-10` **antes da
  primeira célula**. Anterior aborta; posterior avisa. As datas vão para o CSV
  (`ModeloPath`, `ModeloData`, `ModeloFonte`), por isso qualquer ficheiro de
  resultados passa a saber dizer de que campanha é.
- Um CSV **sem** essas colunas não é retomado (vai para `_ANTIGO`), e uma célula
  avaliada com outro modelo volta a correr mesmo que esteja completa — senão a
  repetição herdava em silêncio as células erradas.
- 12 testes novos em `tests/test_zeroshot_guarda.py`; 44/44 na suite.

**O que fica por fazer**, e é a condição para haver F1: trazer os campeões 7d do
servidor. Enquanto não estiverem no disco, a guarda impede a corrida — que é o
comportamento pretendido.

---

*Assinatura temporal: este plano existe no git antes de o mapa ter sido treinado uma
única vez (commit datado de 24 jul 2026).*
