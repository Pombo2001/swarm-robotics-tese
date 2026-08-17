# Plano de ataque — revisão final (17 a 22 ago 2026)

**Estado à partida (17 ago, depois de a QI7 entrar):** tese em **129 páginas**,
0 overfull, 0 referências indefinidas. 143 testes passam. 8 verificadores, com
**62 valores** só na secção do mapa grande e cobertura global de **28%** dos
tokens numéricos. Auditoria do dashboard a 0 problemas. **Nenhuma campanha por
fechar** — o servidor está vazio.

**Prazo:** 22 ago (hard stop). São **5 dias**, e o trabalho já não é produzir
resultados: é garantir que o que está escrito resiste a ser lido com atenção.

---

## Como este plano se lê

Cada item diz **quem o faz**. Há coisas que eu não posso fazer por ti — ler a
dissertação de fio a pavio é uma delas, e é a que mais vale.

| símbolo | significado |
|---|---|
| 🤖 | faço eu, sem te perguntar nada |
| 👤 | só tu podes: leitura, redação, decisão de autoria |
| 🤝 | eu preparo e reporto, tu decides |

A ordem é por **risco × custo de descobrir tarde**, não por conforto.

---

## P0 — o que bloqueia a entrega

### 0.1 👤 Ler a QI7 inteira, de olhos frescos *(≈1 h)*

Foi escrita hoje por um guião, a partir dos dados. Os números estão verificados
(62 deles), a **redação não**. Ler:

- a secção completa (**p. 79–86**), com atenção à Discussão (p. 83–84);
- o parágrafo das Conclusões, a resposta às QI (p. 76–79) e as frases do Resumo
  e do Abstract.

O que procurar não são números — é se **o argumento é teu**. A Discussão afirma
que a bimodalidade do Muro em U «sobrevive à escala». É defensável e é o que os
dados mostram; mas é uma leitura, e é a que o júri vai atacar primeiro.

### 0.2 🤝 O artigo não sabe que a QI7 existe *(decisão + ≈2 h se sim)*

Medido hoje: **zero menções** ao mapa grande, ao mapa composto ou à QI7 em
`Artigo/artigo.tex`, cuja última alteração é de 14 ago. A dissertação tem agora
um oitavo cenário e uma questão de investigação que o artigo não reporta.

Três saídas, e a escolha é tua:
1. **integrar** — uma subsecção curta de resultados + uma frase nas conclusões;
2. **declarar o recorte** — uma nota a dizer que o artigo cobre os sete
   cenários, e a dissertação o oitavo;
3. **deixar como está** — só se o artigo não for submetido nem anexado.

A (3) é a única que não exige trabalho, e é também a única em que dois
documentos teus dizem coisas diferentes sobre o mesmo trabalho.

### 0.3 👤 Confirmar o regulamento sobre uso de ferramentas de IA *(≈15 min)*

A declaração de triagem assistida saiu hoje, a teu pedido. Vale a pena
confirmares o texto do regulamento do ISCTE: se ele **exigir** a declaração, o
que hoje é conformidade passa a ser omissão. É uma leitura de 15 minutos que
fecha a questão nos dois sentidos.

---

## P1 — os defeitos que este projeto já cometeu

Cada um destes já aconteceu uma vez. É por isso que estão à frente.

### 1.1 🤖 Figuras: ligar cada uma à sua fonte *(C1 do plano anterior)*

A tese referencia **46 figuras** (todas presentes; as 6 «em falta» estão em
linhas comentadas — ver 3.3). As da tese são **cópias** das das campanhas e
derivam em silêncio: a 21 jul havia 8 desatualizadas, a 4 ago capturas 3D
anteriores à correção das paredes.

Para cada figura: de que dados e de que script sai; regenerar; comparar
bit-a-bit. Onde mudar, a versão que está no PDF estava errada.

### 1.2 🤖 Legendas vs conteúdo *(C3)*

A 4 ago um heatmap com **0 recolhas** tinha legenda a dizer «navegação
resolvida». Reler as 46 legendas contra o que a figura mostra. É leitura, não
script — mas posso fazer o primeiro passe e trazer-te só os casos duvidosos.

### 1.3 🤖 Bibliografia: autor + ano + título contra a fonte *(E1, E2)*

A auditoria de 16 jul apanhou **nomes de autores fabricados com DOIs válidos** —
passou porque se verificaram os DOIs e não os nomes. São **45 entradas citadas**
de 49 no `.bib`. Verificar as citadas, e sincronizar os dois `.bib` (tese e
artigo), que já divergiram uma vez.

### 1.4 🤖 Pré-registo → o que é reportado *(F1, F2)*

Três pré-registos com emendas até à 21. **Um compromisso pré-registado que não
seja reportado é o defeito mais caro que esta tese pode ter** — mais do que um
número errado, porque é o que separa uma regra fixada à partida de uma escolhida
depois. Tabela: compromisso → onde é reportado → bate. Inclui as células do
Sandbox que estavam por reportar a 4 ago.

---

## P2 — o dashboard

O dashboard não é entregável, mas é o que projetas na defesa.

### 2.1 🤖 Os números do dashboard vs os da tese *(B3)*

O Overview afirma 28 sessões, 2940 episódios, 1671 h, 341 h, 6/7 cenários. **Um
número que apareça nos dois sítios tem de ser o mesmo número** — foi assim que 2
KPIs mentiram a 4 ago. Verificar contra as mesmas fontes que a tese usa.

### 2.2 👤 Ver as 16 vistas ao olho *(≈40 min)*

A auditoria automática diz «16 de 16 construíram» — isso prova que não
rebentam, não que estejam certas. A 2 ago só 5 de 16 tinham sido vistas por
alguém. Abrir uma a uma em `localhost:8080` e olhar.

⚠️ Já sabido, e por corrigir: os PNG da campanha do GNN na **Galeria** vêm do
`eval_summary.csv`, que só tem o modelo campeão — mostram *81% · 7,4 rec/ep*
onde a campanha dá *17,4% · 1,69*. Os números das tabelas do dashboard estão
certos; as imagens é que são do melhor caso. **Não usar esses três gráficos numa
apresentação sem os regenerar** (🤖 posso regenerá-los a partir dos 21 runs).

### 2.3 🤖 Paridade Pi ↔ local *(G2)*

Escrever a verificação que compara o que as vistas leem com o que o
`atualizar_pi.sh` envia, e que falha quando alguém acrescenta uma leitura nova
sem a acrescentar ao script. **Não publicar** — a publicação é em lote e a teu
pedido.

---

## P3 — se sobrar tempo

### 3.1 🤖 Ensaiar o `docs/REPRODUZIR.md` de ponta a ponta *(D1, D2)*

Comando a comando, em diretório limpo. Cada um que não corra, ou que dê um
número diferente do prometido, é achado. É literalmente a pergunta «de onde vem
este número?» que o júri faz.

### 3.2 🤖 Continuar a cobertura dos verificadores *(B2)*

28% dos tokens numéricos. A seguir, por ordem de visibilidade: Conclusões (25
valores), Sandbox (19), Desempenho Computacional (17), Resumo (8).

### 3.3 🤖 Limpeza *(≈20 min)*

- Seis `\includegraphics` de ficheiros inexistentes, em linhas comentadas
  (`images/scen_*.png`, linhas 1037–1052 do `main.tex`) — lixo que só confunde
  quem ler o fonte.
- Quatro entradas do `.bib` não citadas: confirmar se sobram de propósito.

---

## Sugestão de calendário

| dia | 🤖 eu | 👤 tu |
|---|---|---|
| **18 ago** | figuras (1.1) + legendas, 1.º passe (1.2) | ler a QI7 (0.1) |
| **19 ago** | bibliografia (1.3) | decidir o artigo (0.2) + regulamento (0.3) |
| **20 ago** | pré-registo (1.4) + dashboard (2.1) | ver as 16 vistas (2.2) |
| **21 ago** | paridade Pi (2.3) + REPRODUZIR (3.1) | reler o que eu tiver mudado |
| **22 ago** | corrida final: testes, verificadores, compilação | **entrega** |

O dia 22 fica **inteiro** para a corrida final e para o que correr mal. Não é
folga: é o que impede que um problema descoberto às 18h do último dia seja um
problema descoberto tarde demais.

---

## Achados

*(cada entrada: data, item, o que se mediu, o que se fez)*

### 17 ago — o artigo ficou para trás da tese

`Artigo/artigo.tex` não tem uma única menção ao mapa grande, ao mapa composto ou
à QI7 — última alteração a 14 ago, três dias antes de a secção entrar na
dissertação. Não é um erro do artigo (ele nunca prometeu cobrir o oitavo
cenário); é uma **divergência entre dois documentos do mesmo trabalho**, e é
preciso decidir o que fazer com ela antes de qualquer um dos dois sair. Ver 0.2.

### 17 ago — 1.1 e 1.2 — as 46 figuras: 43 batem, 3 divergem com explicação

**Feito.** `scripts/verificar_figuras_tese.py` compara **pixel a pixel** cada
figura do PDF com o ficheiro homónimo em `results/`, e diz de que guião sai
(`--listar`). O medo era encontrar figuras velhas como a 21 jul e a 4 ago: não
se confirmou. **43 das 46 são idênticas à fonte.**

**As três que divergem são os heatmaps de ocupação do Muro em U**, e a tese
está do lado certo: usa a versão de **6 episódios** (a do pipeline canónico,
`plot_results.py`), que é a que a legenda descreve — «6 episódios por painel».
A cópia em `final_7d` foi regenerada a 31 jul pelo `figuras_campanha.py`, que
corre **4**. Não é a tese que está desatualizada; é a pasta de onde ela copia
que passou a ter outra coisa. Ficam declaradas no verificador, com a razão: se
alguém copiar de `final_7d` para a tese, a legenda passa a mentir sem que nada
mude no texto.

**Uma figura não tinha fonte nenhuma — e era minha.** A dos percursos entrou
hoje na dissertação como `mapa_grande_rastos.png` mas era gerada como
`rastos_mapa_grande.png`: gerar com um nome e copiar com outro quebra a única
ligação automática entre o PDF e o que o produziu. O guião passou a gravar com
o nome final.

⚠️ **E o ensaio desmentiu o meu próprio verificador.** Pintei um quadrado de
40×40 pixels no meio de uma figura da tese e ele deu-a por boa: o limiar era
«0,05% dos pixels», que numa figura de 3000×2000 são 3000 pixels de tolerância.
Uma barra de erro com a altura errada mexe em muito menos. Passou a ser um
limiar **absoluto** de 50 pixels, e o ensaio apanha a mutação.

### 17 ago — 1.2 — legendas contra o conteúdo: dois achados, e nenhum é um número errado

Lidas as 28 legendas e vistas as figuras que fazem afirmações verificáveis. **A
maioria bate**, incluindo as que mais podiam falhar: os heatmaps de ocupação do
Muro em U dizem «6 ep, 473 / 412 / 0 recolhas» e é isso que está impresso em
cada painel; o GNN contorna mesmo pela esquerda e o PPO pela direita; o SAC
mostra a ocupação colada às faces interiores das pernas do U, como a legenda
descreve; o potencial euclidiano está à esquerda e o geodésico à direita; a
figura da escalabilidade tem mesmo um único ponto para PPO e SAC; os dotplots
têm sete pontos por algoritmo e as médias impressas batem com a
Tabela~\ref{tab:res_eval}.

Os dois problemas que apareceram são de **redação**, e por isso ficam aqui em
vez de serem corrigidos:

**(a) A figura da robustez e a tabela principal dizem números muito diferentes
sobre a mesma célula, e nada na tese os concilia.** A `robustez_falhas.png`
mostra o GNN no Muro em U a ~79 recolhas/ep; a `tab:res_eval` e o dotplot da
mesma dissertação dizem $24{,}5$. Ambos estão certos: a figura da robustez usa
o **modelo campeão** de cada célula (`results/evaluation/eval_*.csv`, um modelo
× 20 episódios) e a tabela usa a **média das médias dos sete *runs***. O texto
diz «sobre os modelos da campanha final», o que é verdade e não chega — não diz
*quantos*. Nos cenários bimodais a diferença é enorme (Sandbox $62{,}1$ vs
$38{,}3$; Muro em U $79{,}3$ vs $24{,}5$; Porta c/ Alternativa $64{,}5$ vs
$86{,}7$). O rácio que a figura mede — a retenção — não é afetado, porque base e
falha vêm da mesma fonte.

*Proposta:* uma frase na legenda ou na secção, do género «a base é a avaliação
do modelo campeão de cada célula, não a média das sete execuções da
Tabela~\ref{tab:res_eval}; a retenção é um rácio entre duas medições da mesma
fonte e não é afetada por essa escolha».

**(b) A legenda do mega-treino descreve o SAC como bimodal, e ele não é.** Diz
que «o GNN objetivo, o PPO e o SAC repartem-se entre execuções que resolvem o
cenário e execuções que ficam a zero». Medido nas 28 execuções do Muro em U: o
PPO tem 3 zeros e **14 execuções acima de 60** recolhas/ep — bimodal, sim. O
SAC tem 11 zeros e **zero execuções acima de 60**; o seu máximo é $45{,}4$ e o
resto distribui-se continuamente entre 0 e 45. O SAC não tem execuções «que
resolvem o cenário» no sentido em que os outros têm: tem execuções fracas e
execuções nulas. A figura mostra-o com clareza — é a legenda que generaliza a
mais.

*Proposta:* distinguir os dois padrões numa oração — «o PPO reparte-se entre
execuções que resolvem e execuções a zero; o SAC não chega sequer a metade da
magnitude dos outros braços em nenhuma das 28».

### 17 ago — 1.4 — pré-registo vs reportado: 28 compromissos cumpridos, e o que faltava era um braço que nunca correu

**Feito.** `scripts/verificar_preregistos.py` põe os três pré-registos lado a
lado com o que a dissertação reporta: **29 compromissos**, dos quais 28
verificados por medição ou por padrão no `.tex` e 1 remetido para leitura humana.
A tabela é gerada, não escrita (`--escrever` → `docs/PREREGISTO_VS_REPORTADO.md`),
por isso muda sozinha se um compromisso deixar de ser cumprido.

O que ele confirma sem margem: o **desenho executado** é o pré-registado (3
algoritmos × 21 execuções × 20 episódios, N=20, `max_steps=2000`,
`required_to_eat=1`, 106 obstáculos — lidos dos CSV e do simulador, não do
texto); as três campanhas fecharam **antes** do hard stop; M1--M3 e T1--T4 estão
todas reportadas; o oitavo cenário **não** entrou nas tabelas dos sete; a M2
continua descritiva com a razão declarada; e as células exploratórias do
mega-treino que ninguém precisaria de publicar — o Sandbox a 20/21, a Perceção a
17/21, o SAC no Gargalo a 7/21 — estão lá.

**O achado é um desvio por declarar, e é do tipo que mais custa.** A emenda 20
pré-registou um **braço exploratório de orçamento longo** (GNN @2340 min × 3
execuções) para responder de antemão à objeção *«faltou treino»*. Ele **nunca
correu**: a 13 de agosto, com o veredicto já selado pela aritmética, decidiu-se
não o lançar. A decisão está certa e está registada no `PLANO_QUALIDADE.md` — mas
**não estava no pré-registo**, que se compromete a datar todos os desvios, e a
secção da dissertação invocava-o numa frase (*«o braço exploratório de orçamento
longo responde apenas à objeção do orçamento»*) que o dava por existente. Quem
lesse a secção contaria com um braço que não há.

Corrigido nos dois sítios: **emenda 24** no pré-registo (o que se perde, o que
não muda, e a distinção entre a decisão humana de 13 ago e a falha técnica do
*watcher* a 10 ago) e a frase da secção, que passa a dizer que o braço não foi
lançado e que a objeção do orçamento se responde por **medição sobre as 21
execuções que existem** — medição que, honestamente, *sustenta* a objeção: em 19
das 21 o pico do *fitness* está nos últimos 20% das gerações.

⚠️ **O verificador foi posto à prova antes de se acreditar nele**
(`tests/test_verificar_preregistos.py`, 8 ensaios): comentar a M2, meter o mapa
grande na `tab:res_eval`, apagar a emenda do cancelamento, invocar o braço sem
ressalva, trocar o valor da M3 e abrir um buraco na numeração das emendas — todas
as mutações são apanhadas. A primeira é a que interessa: o `.tex` é lido **sem
comentários**, porque a QI7 inteira viveu meses dentro deles e um parser ingénuo
dá por reportado o que ainda não está.

Ficou também atualizado o `results/mapa_grande/LEIA-ME.md`, que ainda anunciava
«ainda não existe um único dado de F2» com a campanha fechada há um dia.

### 17 ago — 1.3 e E2 — bibliografia: as 19 com DOI batem, e os dois `.bib` estão sincronizados

**Feito.** `scripts/verificar_bibliografia.py` compara cada entrada citada com
o registo dos editores — CrossRef, e **DataCite** quando o CrossRef devolve 404,
que é o caso das teses de doutoramento com DOI da própria universidade. Compara
apelido do primeiro autor, lista de autores, ano e título; guarda as respostas
em `docs/slr/cache_crossref.json` para a auditoria se repetir sem rede.

* **19 entradas com DOI: todas corretas.** Nenhum nome fabricado, que era o
  defeito de 16 jul.
* **Os dois `.bib` estão sincronizados**: 46 entradas comuns, **zero**
  divergências campo a campo; a tese tem 3 a mais (`bonabeau1999swarm`,
  `iskandar2025phd`, `riviere2020glas`) e o artigo nenhuma que a tese não tenha.
* **6 das 26 sem DOI** foram confirmadas por busca de título; as outras **20
  ficam para leitura humana** — são clássicos que o CrossRef não indexa (arXiv,
  NeurIPS, ICLR, livros). Isso está dito na saída, não escondido.

⚠️ **Três entradas têm identificador que não corresponde ao autor**:
`gupta2025influx` → Somvanshi, `lin2025survey` → Ekechi, `sun2024graph` →
Chen, `zheng2025lns2` → Wang. São restos das correções de 16 jul — a chave
BibTeX ficou a antiga e o campo `author` foi corrigido. Não afeta o PDF (a
chave é só um identificador interno), mas engana quem ler o `.bib`.

**Três defeitos meus, apanhados por o instrumento ter sido posto à prova:**

1. O leitor de `.bib` **ignorava o último campo de cada entrada** — que é onde
   vive o `doi`. Concluiu «nenhuma das 45 tem DOI» quando 19 têm. Um parser que
   perde dados em silêncio produz auditorias tranquilas e falsas.
2. A normalização de nomes desfazia os acentos LaTeX **pela ordem errada**:
   `Rivi{\`e}re` ficava `rivi ere` e o verificador acusava o CrossRef de não ter
   o autor que tem. Dois falsos positivos.
3. A busca por título aceitava «o mais parecido» e deu **oito acusações falsas
   de uma vez**: «Attention is All You Need» casou com «Is Attention All You
   Need?», o PSO com um capítulo introdutório sobre PSO, e o livro do Tegmark
   com uma *recensão* do livro do Tegmark — cujo autor é o recenseador. Passou a
   exigir Jaccard ≥ 0,85 no título **e** o ano a menos de dois anos.

Fica uma questão para leitura, não um erro: o DataCite dá `publicationYear:
2026` à tese de Iskandar e o `.bib` diz 2025. Fui à capa do PDF: diz **«Miskolc
2025»**. O 2026 é o ano do depósito do DOI (registado a 27 fev 2026). Cita-se o
documento, não o depósito — está declarado no verificador com essa razão.
