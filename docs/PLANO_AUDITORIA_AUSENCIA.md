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

- [ ] **B1 — mapear o que NÃO é verificado.** Listar as afirmações numéricas do
      `main.tex` sem verificador associado, classificadas em: (i) automatizável,
      (ii) verificável só à mão, (iii) não é resultado (ano, página, dimensão).
      Entregável: `docs/COBERTURA_VERIFICADOR.md` com a lista e a contagem.
- [ ] **B2 — automatizar as (i).** Acrescentar ao `verificar_numeros_tese.py`,
      lendo do `.tex` e não fixando no script (é a regra que já lá está).
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

- nada ainda.
