# Plano de auditoria — janela de ausência (a partir de 14 ago 2026)

**Estado à partida:** tese em 121 páginas, 0 overfull, 0 referências indefinidas.
147 testes passam, 6 verificadores batem, auditoria do dashboard a 0 problemas.
Nada está partido — por isso este plano não é de reparação, é de **procura**.

**Prazo que manda:** 22 ago (hard stop). O F2/GNN fecha ~17 ago.

---

## Como este plano se usa

Não corro sozinho: só trabalho quando sou invocado. Este documento é, por isso,
uma **fila de trabalho com estado**, não um calendário. Cada item é fechado e
independente, para poder ser apanhado a meio sem contexto nenhum.

- as caixas `[ ]` → `[x]` marcam-se aqui, à medida;
- cada achado é escrito na secção **Achados** no fim, com data;
- ordem: **A antes de tudo**, depois B → G. Dentro de cada letra, de cima para baixo.

### O que eu decido e o que não decido

| Faço sem perguntar | Só reporto, não mexo |
|---|---|
| corrigir código, scripts, dashboard | qualquer frase da tese ou do artigo |
| regenerar figuras a partir dos dados | escolher a leitura da QI7 (A/B/C) |
| acrescentar testes e verificadores | apagar dados ou resultados de campanhas |
| commitar cada correção, uma por commit | publicar no Pi ou enviar e-mail |

A regra fina: **posso mudar como um número é obtido; não posso mudar o número
que a tese afirma.** Se um verificador novo apanhar uma divergência entre a
tese e os dados, isso vai para *Achados* e fica à espera — não se corrige a
tese por iniciativa minha, porque a correção certa pode ser em qualquer um dos
dois lados e essa é uma decisão de autoria.

---

## A. O que chega durante a ausência  *(prioridade máxima)*

- [ ] **A1 — o F2/GNN fechar (~17 ago).** Ao detetar `eval_by_run.csv` do GNN em
      `results/mapa_grande/f2*/`:
      1. `bash scripts/estado_f2.sh` (precisa da VPN desligada);
      2. `python scripts/analise_mapa_grande.py`;
      3. `python scripts/fechar_qi7.py` — **modo seco, sem `--escrever`**.
      Reportar: k por algoritmo, a leitura que a regra dá (A/B/C) e os 5 valores
      que entrariam. **Não escrever na tese.** A regra escolhe a leitura; quem a
      sanciona és tu.
      *Falha parece-se com:* o script recusar-se a escrever (GNN < 21 execuções)
      — é o comportamento correto, não um erro.

- [ ] **A2 — vigiar que o braço não morre.** Se o `estado_f2.json` deixar de
      avançar por mais de ~26 h (duas execuções de 13 h), dizê-lo. Foi assim que
      se perderam 3 dias a 10 ago: o watcher lia o log errado.

---

## B. Números afirmados vs números verificados

O verificador cobre 352 valores (tese + artigo). O corpo do `main.tex` tem
**2170 tokens numéricos, 267 distintos**. A diferença não é toda afirmação
verificável — muitos são anos, secções, dimensões —, mas a fração por cobrir
não está mapeada em lado nenhum.

- [x] **B1 — mapear o que NÃO é verificado.** FEITO a 14 ago —
      `scripts/cobertura_verificador.py` + `docs/COBERTURA_VERIFICADOR.md`.
      **212 de 1806 tokens (12%) são lidos por algum verificador**; dos 1594 que
      sobram, 495 são automatizáveis, 468 precisam de leitura, 631 não são
      resultados. O maior buraco é a secção do Novelty (**164**), que é onde
      vive a QI6. Ver *Achados*.
- [~] **B2 — automatizar as (i).** EM CURSO. Feita a secção do Novelty (a maior):
      **41 valores** passam a ser verificados, e o buraco dessa secção cai de
      164 para 118. Cobertura global 12% → 14%. A seguir, por ordem: Resposta às
      QI (61), Escalabilidade (35), Discussão Global (27), Conclusões (25).
- [ ] **B3 — o dashboard afirma números também.** O Overview diz 25 sessões,
      2940 episódios, 1671 h, 341 h, 6/7 cenários. Conferir contra as mesmas
      fontes da tese: **um número que apareça nos dois sítios tem de ser o mesmo
      número.** Se divergirem, é achado (foi assim que 2 KPIs mentiram a 4 ago).

---

## C. Figuras  *(o defeito que este projeto já cometeu duas vezes)*

As figuras da tese são **cópias** das das campanhas e derivam em silêncio: a 21
jul havia 8 desatualizadas; a 4 ago, capturas 3D de 6 jun, anteriores à correção
das paredes. Medido hoje: **30 das 46 figuras referenciadas são mais antigas que
o CSV mais recente do `final_7d`.** Isso é indício, não prova — a maioria não
deriva desse CSV.

- [ ] **C1 — ligar cada figura à sua fonte.** Para as 46, determinar de que
      dados/script sai. Depois comparar mtime figura vs mtime fonte, e onde a
      figura for mais antiga, **regenerar e comparar bit-a-bit**: se mudar, a
      versão no PDF estava errada — achado, com a diferença descrita.
- [ ] **C2 — travar a deriva das 10 do artigo.** Hoje as 10 figuras do artigo
      são md5-idênticas às da tese. Escrever um teste que o exija, para deixar de
      depender de alguém se lembrar.
- [ ] **C3 — legendas vs conteúdo.** A 4 ago um heatmap com 0 recolhas tinha
      legenda a dizer «navegação resolvida». Reler as 46 legendas contra o que a
      figura mostra. É trabalho de leitura, não de script; faz-se por lotes.

---

## D. Reprodutibilidade — o ensaio da defesa

- [ ] **D1 — executar o `docs/REPRODUZIR.md` de ponta a ponta**, comando a
      comando, num diretório limpo. Cada um que não corra, ou que dê um número
      diferente do prometido, é achado. É literalmente a pergunta «de onde vem
      este número?» que o júri faz.
- [ ] **D2 — `docs/INVENTARIO.md`**: os caminhos que promete existem?

---

## E. Bibliografia

A auditoria de 16 jul apanhou **nomes de autores fabricados** com DOIs válidos —
o erro passou porque se verificaram os DOIs e não os nomes.

- [ ] **E1 — conferir autor+ano+título de cada entrada citada**, nos dois `.bib`
      (tese e artigo), contra a fonte primária. Priorizar as citadas no corpo.
- [ ] **E2 — os dois `.bib` estão sincronizados?** Já divergiram uma vez.

---

## F. Pré-registo vs o que é reportado

Três pré-registos (mega-treino, novelty adaptativo, mapa grande) com emendas até
à 21. Um compromisso pré-registado que não seja reportado é o defeito mais caro
que esta tese pode ter — mais do que um número errado.

- [ ] **F1 — tabela compromisso → onde é reportado → bate?**, para os três
      documentos. As células por reportar do Sandbox (20/21 a 4 ago) e as três do
      pré-registo entram aqui.
- [ ] **F2 — as emendas 19 e 21** (n=21, limiar proporcional) estão refletidas em
      todo o lado onde o limiar aparece? Inclui dashboard e artigo.

---

## G. Rotina, sempre que for invocado

- [ ] **G1** — `python -m pytest tests/ -q` (≈7 min) + `scripts/auditar_dashboard.py`.
      Qualquer regressão trava tudo o resto até estar corrigida.
- [ ] **G2 — paridade Pi ↔ local.** O delta já deixou de fora o que as vistas
      leem **duas vezes** (`d3db185` a 12 ago, `2afc3aa` hoje). Escrever uma
      verificação que compare o que as vistas leem com o que o delta envia, e
      que falhe quando alguém acrescenta uma leitura nova sem a acrescentar ao
      script. **Não publicar** — a publicação é em lote e a pedido.

---

## Achados

*(cada entrada: data, item, o que se mediu, o que se fez ou porque não se fez)*

### 14 ago — B1 — a cobertura dos verificadores é de 12%, e o buraco maior é a QI6

**Medido.** 1806 tokens numéricos no corpo do `main.tex`; **212 lidos** por algum
dos seis verificadores. Dos 1594 restantes: 495 automatizáveis, 468 a precisar de
leitura, 631 que não são resultados. Por secção, os automatizáveis concentram-se
em: Novelty Search **164**, Resposta às QI **61**, Escalabilidade **35**,
Discussão Global **27**, Conclusões **25**, Resumo **8**.

**A medição teve de ser corrigida a meio, e isso é parte do achado.** A primeira
instrumentação só embrulhava o módulo `re` e deu 6% — número que não batia com os
352 valores que o verificador diz conferir. A causa não era o verificador estar a
mentir: o `ler_tabela()` lê as tabelas com `find()` e `split('&')`, sem uma única
expressão regular, e escapava inteiro à medição. Uma medição que só vê metade dos
instrumentos mede o instrumento, não a tese.

**Verificado à mão o pior caso, e não há erro.** Antes de tratar os 164 como
dívida, confirmei os valores-chave da secção do Novelty contra os
`eval_by_run.csv`: u_wall novidade fixa $69{,}8 \pm 5{,}9$, bypass fixa
$63{,}0 \pm 21{,}9$, adaptativo u_wall $68{,}5 \pm 13{,}1$, adaptativo bypass
$77{,}2 \pm 16{,}7$, exploratório $88{,}7 \pm 0{,}6$, objetivo puro com o dobro
do orçamento $4/7$ no Muro em U. **Batem todos.** O problema é de cobertura, não
de conteúdo — o que muda a urgência, mas não a conclusão: são números que ninguém
volta a conferir se algum CSV for regenerado.

**Nada foi mudado na tese.** Nenhum número desta secção precisou de correção.

### 15 ago — B2 — a secção do Novelty passa a ser verificada: 41 valores, todos batem

**Feito.** `verificar_novelty()` no `verificar_numeros_tese.py`: nove afirmações
em prosa, 41 valores (médias, desvios, convergências, $p$ e $\delta$), lidos do
`.tex` e confrontados com os `eval_by_run` das seis campanhas. Cobertura global
**12% → 14%**; a secção do Novelty cai de 164 por verificar para 118.

**Uma diferença de método, declarada na saída.** Nas tabelas, este verificador
compara a tese com o CSV que o `statistical_tests.py` produziu e recusa repetir
os testes — duas implementações podiam discordar. A secção do Novelty **nunca
teve esse CSV**: os testes correram nos scripts de análise e o resultado ficou
só na prosa. Aqui, recalcular é a única verificação possível; o $\delta$ vem
importado do `statistical_tests`, para não haver uma segunda implementação dele.

**Duas correções ao próprio verificador, antes de ele valer alguma coisa:**
1. No par da Porta com Alternativa a tese escreve o objetivo primeiro e a
   novidade depois; eu tinha mapeado as séries pela ordem da frase e não pela
   dos grupos, e o verificador acusava 4 divergências de $\approx 24$ recolhas
   que eram só ele a comparar cada braço com o outro.
2. A tolerância era um número escolhido por mim (0,002 para o $p$), e acusava
   `$p=0{,}32$` de errado por os dados darem $0{,}3176$. Passa a sair das
   **casas decimais que a tese escreveu**: uma afirmação a duas casas julga-se a
   duas casas. Exigir mais é chamar erro a um arredondamento correto.

**A medição de cobertura também teve de ser corrigida** (segunda vez): só
reconhecia como «o `.tex`» strings com mais de 20 000 caracteres, e a
verificação nova recorta a secção (14 636) e busca só dentro dela. Uma medição
que não vê o instrumento novo dá a ilusão de que nada mudou.

**Nada foi mudado na tese.** Os 41 valores batem todos.
