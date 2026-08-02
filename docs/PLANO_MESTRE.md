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

# 0. ONDE ISTO ESTÁ (2 ago, tarde) — LÊ ISTO PRIMEIRO

1. ✅ **O F1 do mapa grande FECHOU** — e desta vez com dados válidos. A condição
   natural acabou a 1 ago 00:11 mas ficou no servidor (o esperador desistiu
   quando a VPN caiu para se chegar ao Pi); foi trazida a 2 ago. As quatro
   condições, **1680 episódios, 84 de 84 células a 0,00 recolhas/ep** — as três
   causas alternativas ficam **excluídas** e vão para apêndice. Tudo em
   `results/mapa_grande/f1_zeroshot_v2/` (a pasta `f1_zeroshot/` é a ANULADA:
   `env_hash 267a7b547aed` vs `e930abe4d992`). Com o navegador geodésico a fazer
   **53,0 rec/ep** no mesmo mapa (n=3 seeds; os 54,0 citados a 31 jul eram a
   média de 2 — ver `results/mapa_grande/sanidade/sanidade_navegador.txt`),
   **o zero mede transferência** — a resposta à QI7.
2. ✅ **megaA CONCLUÍDO** (2 ago 00:16 UTC, config reposto a 0.0/false). A fase 5
   está trazida: `results/mega_1mes/mega_A_fase5/` — Sandbox adaptativo, **21
   runs**, 55,7 comida/ep, 96,7% de sucesso. Falta a análise M1-M3 do
   pré-registo v2, com o megaB.
3. ⏳ **megaB na última fase** (7/7, perception adaptativo ×21). Medido a 2 ago
   15:46 UTC: 19 runs de 21, ritmo estável de 3h15/run ⇒ **treino fecha ~3 ago
   00:57 UTC**, máquina livre depois da avaliação (~03:00-05:00 UTC).
4. 🧰 **AMANHÃ (3 ago) SÃO DOIS COMANDOS, por esta ordem:**

       bash scripts/receber_megaB.sh     # traz as fases 6-7, verifica, gera figuras
       bash scripts/lancar_f2.sh         # 13 verificações e só depois lança

   Ambos recusam-se a agir se alguma condição falhar, e ambos dizem porquê. O
   `--verificar` corre só o diagnóstico. Ensaiados a 2 ago contra o servidor: o
   do F2 passa 12 de 13 (a que falha é o megaB vivo, que é a que tem de o
   impedir); o do megaB diz corretamente que a fase 7 ainda não arquivou.

5. 🚀 **F2 do mapa grande: pronto a disparar a 3 ago.** Emendas 19 e 20 do
   pré-registo (escritas a 2 ago, **com zero dados de F2**): n=7 → **21 runs**
   nos três algoritmos, mais um braço **exploratório** GNN @2340 min × 3. O
   acréscimo vai todo para runs, nunca para minutos/run — são os minutos que
   igualam as gerações às campanhas fechadas. Fecha ~14 ago, 8 dias antes do
   hard stop de 22 ago. **Lançar com `scripts/mapa_streamF2.sh preparar` e um
   tmux por stream** — cada um no SEU diretório (dois streams no mesmo diretório
   partilham CSV e sentinelas; era um bug do script, corrigido a 2 ago).

---

# 0-Y. ONDE ISTO ESTAVA (31 jul, fim do dia)

1. **O mapa grande é RESOLÚVEL, e o zero é das políticas.** Os 3 controlos do F1
   fecharam a **0,00 recolhas/ep** (420 ep cada) e a condição natural ia no mesmo
   caminho. `scripts/sanidade_mapa_grande.py` separou as duas leituras possíveis
   com um navegador que não aprendeu nada (descida do campo geodésico): **53,0
   rec/ep** no mapa grande, 82,0 no Quatro Salas. Há caminho, o ninho é
   alcançável, cabe no episódio ⇒ **o zero mede transferência**, que é o que a
   QI7 pergunta, e passa a ter um teto contra o qual se lê (a GNN faz 73% do
   navegador no Quatro Salas e 0% no mapa grande).
   ⏳ A condição natural fecha na noite de 31 jul; `scripts/trazer_f1_ao_fechar.sh`
   traz o CSV sozinho **assim que a VPN do ISCTE voltar** (está desligada desde
   as 14:52 para se chegar ao Pi — as duas redes não se alcançam ao mesmo tempo).

2. **O dashboard foi revisto de cima a baixo** (14 → 15 vistas, sem duplicações):
   a escalabilidade deixou de viver em dois sítios e juntou-se à robustez
   («Escala e robustez»); a comparação de campanhas passou para o pé da matriz
   oficial (Ciência); «Monitorizar» passou a **Servidor** (é lá que se treina) e
   «Resultados» a **Galeria**. Vistas novas: **Vitrine** (o que se mostra na
   defesa, `configs/vitrine.yaml`) e **Episódio 3D** (Canvas 2D no browser, sem
   three.js — o Ursina abre janela no ecrã do servidor e é inútil no Pi).

3. **Todas as campanhas têm figuras**: 1060 em 44 campanhas, 140 GIFs em 22.
   Faltavam porque `week_stream*.sh`/`mega_stream*.sh` arquivam
   `results/{evaluation,models,logs}` e **não** `graficos_tese/` — erro de
   transporte, não de geração. `scripts/figuras_campanha.py` regenera do que cá
   está, com os nomes que a tese cita.

4. **O dashboard corre no Raspberry Pi** para o orientador:
   `https://swarmroboticsgs.duckdns.org` (Let's Encrypt válido, websockets OK).
   ⚠️ **SEM PASSWORD** à data desta escrita — falta a Access List no Nginx Proxy
   Manager. Pacote e instruções: `scripts/empacotar_para_pi.py`, atualizações
   incrementais com `scripts/atualizar_pi.sh`.

5. **Mega-treino**: megaA na fase 5/5, megaB na **fase 7/7** (a última). Fins
   ~2-3 ago, como o pré-registo previa.

---

# 0-Z. ONDE ISTO ESTAVA (29 jul, meio-dia)

1. ⛔ **O F1 do mapa grande foi ANULADO** (29 jul) — pela **segunda** vez. Os
   robôs **voavam por cima das paredes**: o mundo é 3D, a arena é uma esfera de
   r=60 e as paredes tinham 30 m de altura em duro, deixando **45 m de céu
   aberto**. Medido: os campeões andaram a **59 m** durante o episódio inteiro —
   as células que recolheram, recolheram **a voar**. Corrigido em `4b8a26a` (a
   altura passa a ser `2×arena_radius`); os 7 cenários da tese ficam bit-a-bit
   iguais e **nenhum número da dissertação é afetado**. O veredicto de 28 jul
   («escala DIVERGE, obstáculos excluídos») **não se sustenta e não é citado**.
   Detalhe: emenda 16 do `PRE_REGISTO_MAPA_GRANDE.md`; aviso em
   `results/mapa_grande/f1_zeroshot/ANULADO_29jul.md`.
   **O F1 repete-se de raiz nas 4 condições, e o F2 não arranca antes disso.**
2. **O mega-treino continua a correr** (verificado 29 jul 08:50 UTC, load 49,6/64):
   **megaA na fase 4/5** (SAC u_wall @48×28, desde 28 jul 20:12) e **megaB na
   fase 5/7** (adaptativo bypass @195×21, desde 27 jul 12:55). Pelo ritmo real
   medido (GNN @195×28 levou 95-96 h; PPO @48×28 levou 27,5 h): **megaA fecha
   ~1 ago à noite, megaB ~3 ago de manhã** — como o pré-registo previu.
3. **O F2 está pronto a disparar**, mas só depois de megaA/megaB fecharem:
   `scripts/mapa_streamF2.sh {gnn|grad}`, já no servidor. Avisa e espera 120 s se
   apanhar o mega-treino vivo, em vez de bloquear. Hard stop de integração na
   tese: **22 ago**.
4. **O que NÃO viaja para outro PC:** os modelos. Campeões 7d
   (`results/models_7d/`, 50 MB), F0 (13 MB) e A/B do SAC (43 MB) ficam **na
   torre** — mas já não são precisos em PC nenhum: estão instalados no servidor,
   em `~/swarm-mapa/results/models_7d/`, com as datas de 3-9 jul preservadas.

---

# 0-A. LOG DE SESSÃO — 28 jul 2026, tarde/noite (Opus 5, torre)

> A manhã pôs os controlos do F1 a correr; a tarde recebeu-os, e usou a espera
> para dar ao dashboard as cinco vistas que faltavam para ele servir a defesa.

## ✅ O F1 fechou — e o veredicto sai de uma regra escrita antes dos dados

Os três controlos correram **~8,5 h cada, em paralelo** (previsto 6,5 h; a
estimativa da manhã pecava por otimista). Com a condição natural de 27 jul são
**1680 episódios em 4 condições × 21 células**. O `analise_f1_controlos.py`
aplica a regra do `PRE_REGISTO_MAPA_GRANDE.md` §3 sem a interpretar:

| condição | recolhas/ep | leitura pré-comprometida |
|---|---|---|
| natural (principal) | **4,96** | — |
| escala da observação | 3,15 | **DIVERGE** — 6 células ressuscitam, 4 morrem |
| sem obstáculos | 4,91 | **MESMO** (p=0,93) ⇒ causa **EXCLUÍDA**, vai para apêndice |
| sem features da porta | 4,13 | **DIVERGE** — 2 células ressuscitam |

O pré-registo é explícito em como se lê isto: *«um controlo que ressuscite os
campeões NÃO salva a leitura ‘a topologia é dura’: desmente-a»*. Detalhe que a
média esconde e o `LEIA-ME.md` regista: a escala **não melhora, redistribui** —
mata o Sandbox e a Perceção do GNN (7,2→0 e 17,3→0) e acende o Gargalo e a
Perceção do PPO. É consistente com a limitação já declarada: as duas
normalizações estão fora da distribuição de treino, de maneiras opostas.

Os 4 CSV estão **versionados** (`git add -f`, 432 KB) — são a única cópia.

## ⚠️ Um `pscp` apagou 420 episódios em silêncio (e o git salvou-os)

Cada corrida dos controlos grava em `zeroshot_mapa_grande.csv` **no seu
diretório**; trazer o segundo para a pasta onde já estava o primeiro fez o `pscp`
escrever por cima sem uma palavra. Perdeu-se a condição **natural** — quase 6 h
de servidor. Recuperou-se com um `git checkout`, e **só** porque esses CSV estão
versionados de propósito (a exceção ao `.gitignore` decidida a 27 jul, para não
repetir o buraco do braço Novelty preliminar, pagou-se no dia seguinte).

O `trazer_do_servidor.sh` passa a **avisar e ABORTAR** se o alvo já existir,
dizendo o tamanho e a data do que ia apagar (`TRAZER_FORCAR=1` força). Testado: o
mesmo comando que destruiu o ficheiro recusa-se agora a correr. Ficou como
**armadilha nº7** do `REPRODUZIR.md`, com a regra: ao trazer várias corridas da
mesma campanha, **nomes distintos, sempre**.

## ✅ O dashboard passou a servir a defesa (5 vistas novas)

- **Proveniência** — clica-se numa célula da tabela principal e vê-se, no mesmo
  ecrã: o valor impresso no `main.tex`, o valor medido no CSV, se concordam, as
  **sete médias por execução** em barras, o ficheiro, o modelo **com a data**, e o
  comando que reproduz aquela célula. Não recalcula a tese — lê os dois lados e
  mostra-os; a lógica vem importada do `verificar_numeros_tese.py`, nunca uma
  segunda cópia. Avisa a vermelho se o modelo cair fora da janela de 2-9 jul (foi
  um caso desses que anulou o F1 de 25 jul). É a resposta ao *«de onde vem este
  número?»* que o plano mandava ensaiar com um Markdown — numa sala ninguém abre
  um Markdown e procura a linha.
- **Prontidão** — cada linha é uma alínea da regra 6, verificada de facto: o
  verificador dos 308 valores corre **agora** (~2 s, nunca um resultado guardado);
  a compilação não é refeita mas compara-se a data do `.tex` com a do `.pdf` (o
  caso perigoso é enviar ao orientador um PDF anterior à última edição); os testes
  levam 3 min, por isso mostram o último resultado **com a hora** e só correm a
  pedido.
- **Defesa** — o **F4** que faltava no plano: um ecrã por questão de investigação,
  navegável com as setas. O texto **não** é escrito aqui, vem do `main.tex`
  (`sec:questoes_investigacao` e `sec:resposta_qi`), para não haver uma segunda
  narrativa que possa divergir da tese. QI4 e QI7 aparecem **sem número e a dizer
  porquê**.
- **Mapa grande** e **Escalabilidade** — a QI7 era a única questão sem
  representação; a QI2 passa a ser demonstrada em vez de explicada.
- **Arquivo** — apanhado por uma pergunta do utilizador (*«o arquivo não devia ter
  mais coisas?»*): listava 25 campanhas **exploratórias** e nenhuma das **cinco
  canónicas** (7d, Novelty fixo, Novelty adaptativo, mega-treino, mapa F1). Vivem
  fora de `graficos_tese/` por uma boa razão — nenhuma podia sobrescrever os
  campeões 7d (armadilha nº9) — e o efeito colateral foi ficarem invisíveis.

Dois defeitos vistos no browser e corrigidos na hora (parênteses vazios, planta
gigante), e **dois timers** que enchiam o log de tracebacks quando o browser
fechava (`curvas.py` e `treinar.py` não se protegiam como o `app.py`).

## ✅ O verificador passou a cobrir também o artigo (308 valores)

O artigo é o que vai ser submetido, e as suas tabelas são cópias reformatadas das
da tese: sobrevivem a correções da tese sem darem sinal — foi assim que 8 figuras
dele ficaram desatualizadas até 21 jul. A `tab:task` do artigo (105 valores)
passa a ser verificada contra o mesmo `eval_by_run_7d.csv`. Todos batem.

⚠️ Nota útil para quem ler as duas: o **`[n/7]` do artigo NÃO é a taxa de
sucesso** — é o número de execuções cuja taxa é 100%. No Muro U divergem muito
(PPO tem 71% de sucesso mas só 4 execuções em 7 chegam aos 100%). A tese não
reporta esta métrica.

## ✅ Documentação sobre si própria

O índice do `docs/` não listava dois ficheiros e dizia que o F1 do mapa estava
*«fechado a 25 jul»* — precisamente a corrida **anulada** por ter corrido com os
campeões da campanha errada. Um índice que diz isso manda alguém ler dados que não
valem. Mais 5 links partidos (todos em `docs/arquivo/`, de ficheiros movidos) e o
**passo 7** na sequência de reprodução do README: correr o verificador.
Verificação dos 39 links relativos: 0 partidos.

**12 commits, de `a926e1a` a `87ead6d`.**

---

# 0-B. LOG DE SESSÃO — 28 jul 2026, manhã (Opus 5, torre)

> Sessão curta e operacional: tirar os controlos do F1 de cima do PC local e
> pô-los no servidor, deixar o F2 pronto, e rever texto enquanto isso corre.

## ✅ Os controlos do F1 arrancaram no servidor (07:38 UTC)

O custo real foi medido antes de comprometer nada: **1 episódio = 1m34s num core**
do servidor ⇒ 21 células × 20 ep = ~11 h por condição, 33 h em sequência. Daí as
três correrem **em paralelo, uma por diretório** (`~/swarm-mapa-c{1,2,3}`, cópias
`cp -rp`). Não podiam partilhar diretório: as condições convivem no mesmo CSV e o
`eval_zeroshot_mapa.py` tem lock por ficheiro destino, por isso a segunda
abortava. Com `nice 10` e uma thread cada, a carga passou de 47 para 52 em 64
vCPU — megaA/megaB não dão por isso. **O ritmo observado é melhor que o estimado**
(~0,5 min/ep; o 1m34s do smoke era quase todo arranque): fim previsto ~11h30 UTC.

Validado **antes** de lançar: a impressão digital do ambiente no servidor dá
`267a7b547aed`, **igual à da torre** (a digital é geometria arredondada a 4 casas,
por isso é estável entre plataformas — ao contrário dos hashes de floats que
falharam a 27 jul); e só o controlo `sem_obstaculos` a altera (`dd557291eaa5`),
que é o único que mexe no mundo. A guarda de campanha passa: 21 campeões
instalados em `~/swarm-mapa/results/models_7d/` com as datas de **3-9 jul**
preservadas (`cp -p` — sem isso a guarda deixaria passar qualquer coisa).

## ✅ O F2 fica escrito antes de haver janela

`scripts/mapa_streamF2.sh {gnn|grad}` — 780 min/run para o GNN (91 h) e 192 para
PPO/SAC (45 h), como o pré-registo fixou, em dois streams. Já no servidor.

## 🔍 Revisão de texto: uma imprecisão real na secção do mapa

Verificações que **não** encontraram nada (não repetir): as 10 citações nominais
do `main.tex` batem todas com o primeiro autor do `.bib` — incluindo a
`sun2024graph`, cuja chave engana mas cujo primeiro autor **é** Chen, Xingran; os
dois `.bib` estão sincronizados nas 46 chaves comuns; e nenhum número do
Resumo/Abstract/Conclusões deixou de ter eco no corpo.

O que **estava** errado (emendas #14 e #15 do pré-registo, commit `ed90c50`):
os `128,8 m` chamados "percurso ótimo spawn→ninho" são a distância do **centro**
da caixa de partida — os spawns reais vão de **121-124 m** (melhor) a **138-139 m**
(pior). E o custo da alternativa é **+20%** (razão 1,205 medida sobre as posições
de partida), não os +21% que saíam de dividir o máximo do campo (155,4 m) pelo
percurso do centro do spawn — dois números que medem coisas diferentes. Nenhuma
conclusão muda; a descrição é que passa a dizer o que mede. Confirmados ao
centímetro: 155,4 m de máximo do campo (777 passos, folga 2,57×) e 139,2 m no
pior spawn (696 passos, 2,87×).

Compilação isolada com a secção inserida: **125 págs, 0 refs indefinidas, 0
overfulls, 0 erros** — e revertida a seguir, porque o mapa só entra com dados.

## ✅ O M1 do mega-treino já está respondido (sem integrar nada)

O `analise_megatreino.py` foi escrito a 27 jul **antes dos dados** e nunca tinha
visto um CSV real. Correu-se contra as **6 fases já arquivadas** no servidor
(trazidos só os `eval_by_run.csv`): **zero erros**. E como as fases 1 e 2 do
megaA estão completas (28/28 runs cada), o **M1 — o teste principal — está de
facto respondido**:

| u_wall, n=28 | recolhas/ep | convergentes |
|---|---|---|
| GNN **adaptativo** | **67,4 ± 13,4** | **28/28** |
| GNN objetivo | 32,5 ± 32,5 | 15/28 |

Mann-Whitney unilateral **p < 0,0001**, δ **+0,61**; Fisher 28/28 vs 15/28,
**p < 0,0001**. Contra os n=7 da tese (68,5 ± 13,1 e 7/7 vs 24,5 ± 32,6 e 3/7,
p = 0,009, δ = +0,76): **replica-se com o quádruplo do n**. O objetivo puro sai
menos mau do que sete runs sugeriam — parte do contraste de 19 jul era ruído de
amostragem pequena, e o δ desce por isso, não por o efeito enfraquecer.

E a ablação do *annealing* (exploratória): as 4 variantes dão **7/7 nos dois
cenários** (59,7-69,1 no Muro U; 74,8-82,4 no bypass) ⇒ o mecanismo **não depende
de acertar nos hiperparâmetros**, que é uma objeção previsível na defesa para a
qual a tese não tem hoje resposta.

⚠️ **Nada disto entra na tese agora** — o pré-registo manda analisar com a
campanha fechada, e faltam 6 fases. Guardado em
`results/mega_1mes/ANALISE_PARCIAL_28jul_NAO_OFICIAL.txt`. O que se edita quando
fechar está mapeado, com números de linha, em
[`IMPACTO_MEGATREINO_NA_TESE.md`](IMPACTO_MEGATREINO_NA_TESE.md) — incluindo a
regra que é fácil violar por pressa: as células n=28 são **autocontidas**, não
substituem os n=7.

## ✅ A regra 6(b) deixou de ser feita à mão

*"Os números citados batem com o CSV fonte?"* — verificado à mão a 18, 25 e 27
jul. Agora é `scripts/verificar_numeros_tese.py`, e cobre **as quatro peças de
resultados**: `tab:res_eval` (63 valores), `tab:res_scale_all` (35),
`tab:res_signif` (105) e as **afirmações em prosa** da §res_robustez. **203
valores + 4 afirmações, todos batem.**

Um `pre-commit` (instalar com `scripts/instalar_hooks.sh`) corre-o sozinho quando
o commit toca na tese ou nos CSV canónicos, e recusa o commit se algo divergir.
Testado nos dois sentidos, incluindo com um número sabotado. Escape: `--no-verify`.

⚠️ **Duas vezes o verificador acusou a tese e o enganado era ele** — os desvios
são amostrais (ddof=1, √(7/6)=1,08) e a retenção da escalabilidade é face a
**N=20**, a dimensão de treino. Ambas as convenções da tese são as defensáveis, e
ficaram comentadas no código para não se repetir a suspeita.

## ✅ Arrumação e salvaguardas

- **Armadilha nº9:** o `eval_all.py` (carregador comum do `eval_by_run` e do
  `eval_suite`) passa a **imprimir a data de cada modelo** e a marcar os de fora
  da janela da campanha. Renomear as pastas partia o dashboard e o `run_eval`.
- **11 testes** ao `analise_f1_controlos.py` prendem os três veredictos e as
  verificações de integridade. **59/59 na suite.**
- **7 acrónimos** em falta (22 → 29): a lista tinha `POMDP` sem `MDP`, `PSO` sem
  `ACO`, `PPO` sem `MAPPO`/`MADDPG`/`DQN` da mesma frase. `QMIX` fica **de fora**
  de propósito: não tem expansão estabelecida e inventar-lhe uma era pior.
- 4 figuras mortas do artigo removidas (3 eram heatmaps de **10 jun**, de modelos
  que a tese descreve como partidos). As 12 usadas são idênticas às da tese.
- `PLANO_MESTRE` 897 → 478 linhas; `INVENTARIO` e `REPRODUZIR` em dia.

**13 commits, de `f24cc30` a `7fb8556`.**

---

# 0-C. Sessões anteriores (24, 25 e 27 jul)

Arquivadas em [`arquivo/LOGS_SESSAO_jul2026.md`](arquivo/LOGS_SESSAO_jul2026.md)
— ocupavam 428 linhas aqui e empurravam as regras e as tarefas para o fim. Vale
a pena lá ir para duas coisas: a **tabela de onde vem cada campeão da campanha de
7 dias** (log de 27 jul) e **por que razão o F1 de 25 jul foi anulado** (log de
25 jul).

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
7. **Nada de treinos nem avaliações longas no PC local — só no servidor** (regra
   dada a 28 jul). O PC é para escrever, compilar e analisar; o que custa horas
   de CPU vai para a `.14`, em `tmux`, com log próprio.

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
      **Verificado 29 jul 08:50 UTC**: megaA na **fase 4/5** (SAC u_wall @48×28, desde
      28 jul 20:12), megaB na **fase 5/7** (adaptativo bypass @195×21, desde 27 jul
      12:55), load 49,6/64. Pelo ritmo real (GNN @195×28 = 95-96 h; PPO @48×28 =
      27,5 h): **megaA ~1 ago à noite, megaB ~3 ago de manhã**.
- [x] **megaA CONCLUÍDO** (2 ago 00:16 UTC) — config reposto a 0.0/false, confirmado.
      As 5 fases estão em `results/mega_1mes/` (a fase 5 trazida a 2 ago: Sandbox
      adaptativo, 21 runs × 20 ep, 55,7 comida/ep, 96,7% sucesso).
- [ ] **megaB**: fase 7/7, 19 runs de 21 a 2 ago 15:46 UTC ⇒ fecha ~3 ago 00:57 UTC.
      Na chegada: trazer fases 6-7, **confirmar o config de `~/swarm-novelty` reposto**
      (está em true/0.5 porque está a correr — é a armadilha do stream B), verificação
      `_run{n}` (armadilha nº8) e instalar SEM tocar nos modelos ativos.
- [ ] **Análise M1-M3 do pré-registo v2**, com as duas streams completas.
      **Hard stop de integração na tese: 22 ago.**

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
- [x] **F0 — smoke test local** (~1 h, GNN, 1 run): só confirmar que arranca. **Não
      produz resultado** e não entra em análise nenhuma.
- [x] ⛔ **F1 v1 — ANULADO a 29 jul** (4 condições, 1680 ep, ~34 h de servidor
      deitados fora): correu num mundo com **45 m de céu aberto por cima das
      paredes**, com os agentes a voar a 59 m o episódio inteiro. Corrigido em
      `4b8a26a` + emenda 16, e o teto de ±2 m na emenda 17. Fica no repositório
      como prova documental, em `results/mapa_grande/f1_zeroshot/`.
- [x] ✅ **F1 v2 — FECHADO a 2 ago.** Repetido de raiz nas 4 condições no mundo
      corrigido (`env_hash e930abe4d992`, controlos em paralelo 31 jul, natural
      a fechar 1 ago 00:11). **1680 episódios, 84/84 células a 0,00** ⇒ as três
      causas alternativas EXCLUÍDAS, reporta-se a natural. Dados e veredicto em
      `results/mapa_grande/f1_zeroshot_v2/`; a leitura está fixada pelo navegador
      geodésico (53,0 rec/ep no mesmo mapa, n=3): **o zero mede transferência**.
- [ ] **F2 — treino nativo**: 3 algoritmos × **21 runs** (emenda 19, 2 ago) +
      braço **exploratório** GNN @2340 min × 3 (emenda 20). **Arranca 3 ago**,
      quando o megaB largar a máquina. Fecha ~14 ago; hard stop **22 ago**.
      Lançar: `scripts/mapa_streamF2.sh preparar` (cria `~/swarm-mapa-f2{g,r,l}`)
      e depois `mapaF2g` + `mapaF2r`; o `longo` só quando o `grad` fechar
      (~8 ago) — três streams saturam os 64 vCPU.
      ⚠️ O script de 28 jul mandava correr os dois streams no MESMO diretório:
      partilhariam `results/logs/*.csv` e as sentinelas de conclusão. Corrigido a
      2 ago com o padrão dos controlos do F1 (um diretório por stream + guarda do
      simulador).

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
