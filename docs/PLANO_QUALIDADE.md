# Plano de qualidade — de 5 ago ao hard stop (22 ago)

Escrito a 5 ago 2026, com o F2 a correr. Não é um plano de funcionalidades: é uma
lista de sítios onde o projeto pode estar errado sem dar sinal, por ordem do que
custa descobri-los tarde.

O critério que ordena tudo: **o que só se descobre depois de a campanha fechar
custa a tese**. A 16 de agosto faltam seis dias para o hard stop; um defeito no
pipeline de análise descoberto nessa altura não tem janela para ser corrigido com
dados novos.

## Como este plano nasceu

De três achados no mesmo dia, todos do mesmo feitio — nenhum era um erro de
cálculo, todos eram **afirmações que ninguém tinha testado**:

- a linha do tempo do dashboard dizia que o GNN fecharia «~14 ago», dois dias
  depois de o stream ter sido relançado;
- a **M3 do pré-registo não era calculável** — o pipeline nunca registou o estado
  da porta, e a falta só apareceria com a campanha fechada;
- eu próprio medi o custo da alternativa com uma régua diferente da do ambiente e
  publiquei 13,4% onde o número, já medido a 28 jul, era 17,0%.

O padrão: **os números têm verificador, as afirmações sobre os números não.**

---

## Eixo 1 — O que a campanha promete e o pipeline pode não produzir

| # | Verificação | Estado |
|---|---|---|
| 1.1 | M3 (`door_opened`) registada na avaliação | ✅ 5 ago — coluna + 5 testes + enviada às 4 pastas do servidor |
| 1.2 | M1 e M2 calculáveis do `eval_by_run.csv` | ✅ colunas presentes (`food_collected`, `success`, `Run`) |
| 1.3 | A análise F2 corre ponta a ponta com dados na forma real | ✅ `scripts/testes/ensaio_analise_f2.py` — 3 cenários de resultado |
| 1.4 | `pos_campanha.py` (armadilha nº9) corre sobre a campanha do mapa | ✅ corrido — e apanhou o defeito da «última sessão» por mtime |
| 1.7 | O 8.º cenário fica fora das tabelas e figuras dos sete | ✅ `gerar_figuras_7d` e `plot_robustez` passam a filtrar por `THESIS_SCENARIOS` |
| 1.8 | Os scripts do F1 apontam para os dados **válidos** | ✅ o default do `analise_f1_controlos` era a pasta ANULADA |
| 1.5 | O limiar de decisão (⌈5/7 × n⌉ = 15/21) sai do n do CSV, não fixo | ✅ testado nos dois lados: 15 sobe, 14 dá negativo |
| 1.6 | A secção do mapa grande compila **dentro** do `main.tex` | ✅ 6 ago — **129 págs**, 0 refs, 0 overfull, 0 floats grandes demais; `\input` comentado outra vez |
| 1.9 | A secção do mapa grande está escrita para o **n da campanha** | ✅ 6 ago — estava para **n=7** com a campanha a correr a **n=21** (emenda 19); F1 escrito (84 células a 0,00) e **leitura C** (convergência parcial) redigida; `\PORPREENCHER` 16 → **5** |

## Eixo 2 — Afirmações sem verificador

| # | Verificação | Estado |
|---|---|---|
| 2.1 | Datas e estados do dashboard vs realidade do servidor | ✅ 6 ago — `scripts/estado_f2.sh` grava um instantâneo datado (`results/estado_f2.json`) e as 3 vistas leem-no; apanhou «o F2 arranca 3 ago» e «o F2 ainda não correu» com a campanha a correr há 3 dias |
| 2.2 | Números da tese ↔ scripts que os reproduzem | ✅ **352** + `verificar_vertical.py` + 16 contagens em prosa (no hook); 6 ago juntou as **legendas das trajetórias** (78/72/72/25 vs os JSON dos episódios) e **duas frases do artigo**; ⬜ cobrir a secção do mapa grande quando fechar |
| 2.5 | A documentação aponta para ficheiros que existem — e para os **certos** | ✅ 94 caminhos existem; o `REPRODUZIR` e o `INVENTARIO` mandavam para os dados anulados do F1 |
| 2.6 | Dois scripts a escrever o mesmo ficheiro com metodologias diferentes | ✅ `statistical_tests` (episódio) separado do canónico (run) |
| 2.3 | Afirmações do pré-registo ↔ geometria atual do mapa | ✅ emendas 22-23 datadas |
| 2.7 | As FIGURAS afirmam a geometria certa | ✅ 6 ago — as 7 dos cenários mostravam um mundo plano (o `render_maps.py` dizia-o em comentário); agora com a esfera do domínio, as paredes à altura real e os obstáculos nas cotas reais. ⚠️ `Artigo/images` tinha divergido pela 2.ª vez |
| 2.4 | Uma métrica medida por duas réguas diferentes | ✅ **seis** cópias do δ de Cliff fixadas por teste (3 rebentavam com arrays); constantes duplicadas no visualizador ligadas ao ambiente |

## Eixo 3 — Código sem rede de segurança

| # | Verificação | Estado |
|---|---|---|
| 3.1 | Módulos sem um único teste | ✅ inventariado — ver abaixo |
| 3.2 | Os três visualizadores usam convenções de eixos diferentes | ✅ 6 ago — `visualize_algo.py --algo`; a vista «Ao vivo (3D)» aponta-lhe e os três originais foram apagados |
| 3.4 | Revisão de código (5 ago) | ✅ feita — resultados abaixo |

### Revisão de código — o que vale a pena, por ordem

**Depois de 22 ago** (nada disto se toca com a campanha a correr):

1. ~~**Fundir `visualize_{gnn,ppo,sac}.py`.**~~ ✅ **feito a 6 ago** — antecipado
   porque não toca no simulador nem em nada que a campanha use. São 205, 205 e 222 linhas; o `ppo` e
   o `sac` diferem em **12 linhas** (o algoritmo, o título, o caminho do modelo
   e a classe que carrega). São ~630 linhas onde bastariam ~230 com `--algo`.
   Não são código morto — a vista «Ao vivo (3D)» invoca-os — e têm o que o
   `main_visualizer` não tem (slider de velocidade, telemetria de distâncias).
   Já divergiram de facto: a 5 ago encontrei convenções de eixos diferentes
   entre eles e o `main_visualizer`, e o `cylinder` inexistente só num deles.
2. **`swarm_env_3d.step()`: 407 linhas, 74 ramos** — a função mais crítica do
   projeto e a mais ramificada. ⚠️ **Não tocar enquanto o F2 correr**: qualquer
   alteração, mesmo equivalente, obrigaria a reverificar a equivalência
   bit-a-bit dos oito cenários e invalidaria a comparabilidade da campanha.
3. **`compare_pair` do `statistical_tests`** (Wilcoxon emparelhado por igualdade
   de tamanho) — já documentado no cabeçalho do ficheiro; não alimenta a tese.
4. **Testes para `train_ppo_3d` / `train_sac_3d`** (261 e 282 linhas sem um
   único teste). Risco baixo — são invólucros da Stable-Baselines3.

**O que a revisão decidiu NÃO mudar, e porquê:**

- **43 «exceções engolidas»**: quase todas são idiomas benignos
  (`matplotlib.use("Agg")`, `sys.stdout.reconfigure`, imports opcionais). Tratá-las
  como defeito seria ruído.
- **`cliffs_delta` em 6 ficheiros e `compara` em 4**: a duplicação está fixada
  por teste (as seis têm de concordar); unificar código que já produziu números
  publicados é pior do que a duplicação.
- **`create_thesis_plots_3d`, 497 linhas**: código de figuras, risco baixo,
  ganho baixo.
- 0 `except:` nus, 0 argumentos por omissão mutáveis.
| 3.3 | Scripts que produzem números da tese e vivem fora do repositório | ✅ `verificar_vertical.py` trouxe os de hoje |

### O padrão que se repete

Dos onze defeitos encontrados a 5 de agosto, **cinco** são a mesma coisa: uma
decisão tomada por um sinal que se altera sozinho, ou uma segunda régua para uma
grandeza que já tinha a sua.

| Defeito | Sinal frágil | Onde |
|---|---|---|
| «última sessão» | `mtime` da pasta | `verificar_sessao` |
| que modelos ficam ativos | `mtime` da pasta | `restaurar_modelos` |
| campanha do PDF de reunião | `mtime` da pasta | `gerar_pdf_reuniao` |
| tabela de significância certa | **ordem** por que se correm dois scripts | `statistical_tests` vs `gerar_figuras_7d` |
| 8.º cenário fora das tabelas | **não haver dados** dele ainda | `gerar_figuras_7d`, `plot_robustez` |

A regra que sai daqui: **uma garantia que depende de um acidente não é uma
garantia**. Quando algo tem de ser verdade, tem de ser verdade por construção —
a data do treino está no nome da pasta, a lista dos sete cenários existe no
código, e cada ficheiro tem um só produtor.

### Inventário de testes (5 ago)

110 testes passam. O que **não** tem rede, por ordem do que produz números que a
tese publica:

| Módulo | Linhas | Testes | Risco |
|---|---|---|---|
| `scripts/statistical_tests.py` | — | via `test_estatistica_consistente` (só o δ) | ⚠️ escolhe Wilcoxon *emparelhado* quando as amostras têm o mesmo tamanho — **não é o caminho que produziu a tabela da tese** (essa vem do `gerar_figuras_7d.py`, com Mann-Whitney explícito), mas é uma armadilha para quem o reutilizar |
| `src/training/train_ppo_3d.py` | 261 | nenhum | baixo (wrapper da Stable-Baselines3) |
| `src/training/train_sac_3d.py` | 282 | nenhum | baixo (idem) |
| `scripts/eval_suite.py` / `eval_by_run.py` | — | só a coluna `door_opened` | médio — são eles que produzem os CSV de toda a tese |

⚠️ Não corrigir o `compare_pair` do `statistical_tests.py` a meio da campanha:
não alimenta nenhum número publicado, e mexer nele agora é risco sem retorno. Vai
para depois de 22 ago.

## Eixo 4 — Publicação

| # | Verificação | Estado |
|---|---|---|
| 4.1 | Dashboard: auditoria nos dois modos | ✅ 0 problemas (16 vistas, 1247 imagens) |
| 4.2 | 3D do browser mostra a altura e diz que as paredes estão cortadas | ✅ validado no browser (520 px do aviso no quadro 102, 0 no quadro 0) |
| 4.3 | Pi atualizado | ⬜ **exige a VPN DESLIGADA** — um comando, `scripts/atualizar_pi.sh` |
| 4.4 | O delta do Pi leva o que as vistas novas leem | ✅ envia `dashboard/` inteiro |

## Plano de ataque — de 6 ago ao hard stop (escrito a 6 ago)

O utilizador está fora de 7 a 10 de agosto. O que corre sozinho, o que fica à
espera dele, e o que se adianta entretanto.

### A. Corre sozinho, sem ninguém à frente (7–10 ago)

| quando | o quê | se falhar |
|---|---|---|
| ~9 ago | o `mapaF2r` fecha (PPO 21/21 + SAC 21/21) e o `f2lwatch` lança o exploratório | **não lança** se o grad morrer sem `CONCLUÍDO` — é de propósito, a decisão é do utilizador. Custo: o exploratório atrasa até segunda; não entra em M1–M3 |
| até ~16 ago | o `mapaF2g` continua os 21 runs do GNN adaptativo | nada a fazer |

Não há nada a carregar em botões durante o fim de semana. O único risco real é o
servidor cair, e isso resolve-se na segunda com um relançamento.

### B. O que se adianta já (não depende de dados novos)

Por ordem do que custa mais descobrir tarde:

1. **Verificador da secção do mapa grande.** Os 5 `\PORPREENCHER` que faltam vão
   ser preenchidos a 16 ago, com seis dias de folga: os números têm de entrar já
   verificados contra os CSV, como os outros 352. Escrever o verificador **antes**
   de haver números é a única forma de não o escrever à pressa depois.
2. **Conclusões + Resumo com a QI7, nos três desfechos.** A secção já está
   escrita para os três; falta o parágrafo das Conclusões e a frase do
   Resumo/Abstract. É texto que não depende do resultado — só de qual dos três
   se escolhe.
3. **Testes para `train_ppo_3d` e `train_sac_3d`** (543 linhas sem um único
   teste). Não tocam na campanha a correr: são invólucros da Stable-Baselines3.
4. **Nota de rodapé do spawn no Gargalo.** Medido a 6 ago: **18%** dos agentes
   nascem dentro da barreira (o spawn vai de $y=-12$ a $-2$ e a parede cobre
   $-4$ a $4$), mas a separação física **põe-nos fora ao primeiro passo** —
   mediana 1, máximo 1, nenhum preso em 200 passos. Uma frase nas limitações
   chega; corrigir o spawn mudaria a física dos sete cenários e está fora de
   questão até 22 ago.
5. **Lote para o Pi** — acumulado desde 5 ago (visualizador corrigido, figuras
   dos cenários, `estado_f2.json` nas vistas, linha do tempo). Vai quando o
   utilizador pedir, com a VPN desligada.

### C. Quando os dados chegarem

| data | o quê |
|---|---|
| 11–14 ago | a decisão do limiar **sela-se** (`scripts/projetar_limiar_f2.py`): basta o 7.º run não convergente para 15/21 ficar impossível |
| ~14 ago | exploratório fecha — reporta-se à parte, com n=3, e **não** altera o veredicto |
| ~16 ago | GNN fecha → `analise_mapa_grande.py`, preencher os 5 buracos, escolher **uma** das três leituras, descomentar o `\input` |
| 16–22 ago | Conclusões, Resumo, verificação final e revisão do PDF |

Correr `scripts/estado_f2.sh` sempre que se espreitar o servidor: as vistas do
dashboard leem o instantâneo, e sem ele voltam a envelhecer sozinhas.

## Eixo 5 — Calendário

- **~9 ago** o grad fecha → o `f2lwatch` lança o exploratório sozinho.
- **~14 ago** exploratório fecha.
- **~16 ago** o GNN fecha → correr a análise M1-M3, integrar a secção do mapa
  grande, preencher os `\PORPREENCHER`.
- **22 ago** hard stop: o que não fechar até aqui vai para a defesa, não para a
  tese (regra 4 dos compromissos de reporte do pré-registo).

A folga real entre o fim do GNN e o hard stop são **seis dias**. É por isso que o
Eixo 1 tem de estar todo feito antes de 9 de agosto: quando os dados chegarem, a
análise tem de correr à primeira.
