# Plano de revisão do dashboard — o que o ecrã diz, e não só o que os dados dizem

> Documento vivo. Cada passagem regista o que encontrou no fim (secção
> «Registo»). Criado a 20 ago 2026, depois de a revisão das 16 vistas ter
> encontrado sete defeitos que **nenhum dos dezoito verificadores via**.

## Porque existe

O projeto tem dezoito verificadores e uma auditoria do dashboard. Todos passam,
e mesmo assim quem abre o dashboard encontra coisas em falta. A razão é simples
e vale a pena escrevê-la:

| o que já é verificado | o que ninguém verificava |
|---|---|
| os **números** do ecrã batem com os CSV | o que a **frase à volta do número** afirma |
| os ficheiros **existem** | se o que existe **chega** para o que a vista promete |
| as vistas **constroem** sem rebentar | se o que constroem se **lê** |

Os sete defeitos de 20 ago são todos da coluna da direita: a resposta à QI7
truncada a meio, um painel a pedir trabalho já feito, um estado laranja sobre
uma campanha concluída, uma etiqueta cortada pela margem, uma cronologia parada
há uma semana, uma contagem que dizia 2 ao lado de um texto que diz 4, e
«run» em quinze sítios depois de a tese passar a «execução».

## As nove famílias de defeito (todas já aconteceram)

Cada passagem procura estas nove. Não são hipóteses: cada uma tem um caso real.

1. **Frase fixa que envelheceu.** Texto escrito à mão sobre um estado que
   entretanto mudou. *Caso: a vista do mapa pediu «falta escrever na
   dissertação» durante três dias depois de a QI7 estar escrita.*
2. **Texto truncado.** Um extrato que corta a meio. *Caso: a resposta à QI7 na
   Defesa lia-se «Parcialmente, e ao preço» — e é o último ecrã.*
3. **Estado com a cor errada.** Verde/laranja/cinzento a dizer o contrário do
   que se passa. *Caso: o F2 laranja por estar parado, quando parado ali quer
   dizer concluído.*
4. **Elemento cortado ou ilegível.** *Caso: a etiqueta «100% · imune» a sair
   fora da grelha; as figuras a 4 pt.*
5. **Cronologia ou inventário parados.** *Caso: a linha do tempo do Overview
   ficou em 13 ago com o trabalho de 17, 18 e 20 por registar.*
6. **Contagem ambígua.** Dois números certos que se contradizem à vista. *Caso:
   «2/21 execuções» ao lado de um texto que diz 4 de 21 — uma conta as que têm
   100% dos episódios, a outra as que têm ≥1 recolha.*
7. **Terminologia divergente.** O ecrã e a tese a chamarem nomes diferentes à
   mesma coisa. *Caso: «run» vs «execução»; «Mapa Grande» vs «mapa composto».*
8. **Artefacto que existe mas não está onde é procurado.** *Caso: os heatmaps e
   vídeos do mapa composto, dispersos por três pastas datadas.*
9. **Identificador exposto como se fosse nome.** Uma chave do código dentro de
   uma frase. Num caminho ou num comando está no sítio certo; numa frase não
   diz nada a quem lê. *Caso: «12 fases (u_wall a n=28)» no Arquivo, e dois
   seletores que ofereciam «u_wall objetivo puro @390».*

## Procedimento de uma passagem

Percorrer as **16 vistas**, uma a uma, no browser e com o dashboard a correr.
Em cada vista, seis perguntas — pela ordem, porque a última é a mais cara:

1. **O que esta vista promete?** Ler o título e o subtítulo. Se o que está
   abaixo não cumpre a promessa, é defeito — mesmo que os dados estejam certos.
2. **Alguma frase afirma um estado?** («falta», «ainda não», «a correr», «por
   fazer»). Para cada uma: é lida de um ficheiro ou está escrita à mão? Se está
   escrita à mão, é candidata a defeito nº1.
3. **Algum texto vem de fora** (do `.tex`, de um CSV, de um log)? Confirmar que
   chega inteiro — defeito nº2.
4. **As cores e os ícones dizem a verdade?** Verde = bom/feito, laranja =
   atenção, cinzento = não há. Defeito nº3.
5. **Lê-se?** Etiquetas cortadas, texto sobreposto, números sem unidade,
   legendas que não cabem. Defeito nº4.
6. **Os números batem entre si NA MESMA vista?** Não com o CSV — isso já está
   verificado —, mas uns com os outros e com o texto ao lado. Defeito nº6.

Depois das 16, três verificações transversais:

7. **Terminologia:** procurar no código das vistas as formas abandonadas
   (`run`, `Mapa Grande`, `Beco Sem Saída`, `Perceção Coop.`). Defeito nº7.
8. **Cronologia e inventário:** a última entrada da linha do tempo é do último
   trabalho feito? O inventário de horas inclui as campanhas que fecharam?
   Defeito nº5.
9. **Artefactos:** correr `auditar_dashboard.py` e `auditar_campanhas.py` — a
   matriz 7×3 e os melhores treinos por cenário. Defeito nº8.

## O que fica automatizado (e não precisa de olho outra vez)

| régua | apanha | família |
|---|---|---|
| `verificar_dashboard.py` | os 51 valores do ecrã contra a tese | nº6 |
| `verificar_dashboard.py` → `vocabulario` | formas abandonadas e chaves internas no texto do ecrã | nº7, nº9 |
| `verificar_vitrine.py` | os 18 números escritos à mão das legendas, contra os CSV | nº1, nº6 |
| `verificar_comandos_dashboard.py` | os 13 comandos que o dashboard manda copiar | nº1 |
| `verificar_ptpt.py` | brasileirismos e concordância nos 23 ficheiros de ecrã | nº7 |
| `auditar_dashboard.py` → `audita_exibicao` | a matriz 7×3 e os 7 melhores treinos: curva, dot plot, heatmap, vídeo | nº8 |
| `auditar_dashboard.py` → vistas vazias | uma vista que mostra «não há» quando há | nº8 |
| `test_dashboard_conteudo.py` | as 16 vistas constroem, nos dois modos | — |
| a resposta às QI acaba em ponto final | o defeito nº2 na Defesa | nº2 |
| `verificar_paridade_pi.py` | o que as vistas leem vai todo para o Pi | nº8 |

As quatro primeiras correm no `pre-commit` quando `dashboard/` ou
`configs/vitrine.yaml` mudam.

**O que continua a exigir olho:** as promessas (1), as frases de estado (2), as
cores (4) e a legibilidade (5). É por isso que este plano existe em vez de mais
um script.

## Ordem das passagens

Uma passagem completa custa ~1 h. A ordem das vistas não é a da barra lateral —
é a da **exposição**: primeiro o que se projeta numa defesa, depois o que se
consulta, por fim o que só o autor abre.

1. **Defesa** · **Vitrine** · **Ciência** — o que o júri vê
2. **Mapa composto** · **Escala e robustez** · **Proveniência** — o que sustenta
3. **Overview** — a primeira página, e a que envelhece mais depressa
4. **Galeria** · **Vídeos** · **Episódio 3D** — as provas
5. **Arquivo** · **Prontidão** — os bastidores
6. **Treinar** · **Servidor** · **Ao vivo (3D)** — operação (não vão para o Pi)

## Registo

### 20 ago 2026 — primeira passagem (16 vistas)

Sete defeitos, todos corrigidos em `c1dc464`:

| # | família | vista | defeito |
|---|---|---|---|
| 1 | nº2 | Defesa | a resposta à QI7 mostrava «Parcialmente, e ao preço» |
| 2 | nº1 | Mapa composto | pedia «falta escrever na dissertação», já escrita |
| 3 | nº3 | Mapa composto | F2 laranja depois de concluído |
| 4 | nº4 | Escala e robustez | «100% · imune» cortada pela margem |
| 5 | nº5 | Overview | cronologia parada a 13 ago |
| 6 | nº6 | Vídeos | «2/21 execuções» sem dizer que são as que fazem 100% |
| 7 | nº7 | quinze sítios | «run» depois da migração para «execução» |

Mais, no mesmo dia: as campanhas exploratórias incompletas saíram da exibição
(52 → 30) e os heatmaps e vídeos do mapa composto foram consolidados na
campanha (`7797a47`, `62f5553`).

### 20 ago 2026 — segunda passagem (alvos declarados)

Alvos escolhidos **antes** de olhar, para não se procurar só o que é fácil.
Nove defeitos, e uma família nova.

- [x] **Vitrine** — três notas não diziam de quem era o número («59,8 contra
      33,6 (PPO)» sem nomear o vencedor), e o texto de abertura ainda dizia
      «não o melhor **run**».
- [x] **Proveniência** — os comandos foram corridos de facto. O de reprodução
      usava `--algo`/`--scenario` quando o script declara `--algos`/`--scenarios`:
      **corria por acaso**, porque o argparse aceita prefixos não ambíguos.
      Passa aos nomes exatos.
- [x] **Arquivo** — «12 fases (u_wall a n=28)»: chave interna na prosa. A
      contagem «as primeiras N são exploratórias» é calculada, não fixa ✓.
- [x] **Prontidão** — o cartão **Prazos** estava mudo: sem cor e sem uma linha,
      a dois dias do hard stop, porque o texto todo ia para o detalhe fechado.
      Ao corrigir apareceram mais dois: `%b` escrevia «22 Aug» num painel em
      português, e a contagem em horas dizia «amanhã» a 2 dias de calendário.
- [x] **Overview** — «28 sessões de treino» ao lado de 30 campanhas na Galeria
      (passa a «sessões de treino datadas»); «em dia» sem dizer em relação a
      quê (passa a «em dia com os modelos»); e a cronologia dizia «duas
      execuções **completos** do objetivo puro».
- [x] **Escala e robustez / Mapa composto** — tinham **dicionários próprios**
      de rótulos. Com os de `src/`, os do `config.py` e estes dois, havia
      **cinco** vocabulários: o mesmo ecrã dizia «Perceção coop.» num gráfico e
      «Perceção Coop.» na tabela ao lado. As cópias foram removidas.

**Família nova, a nº9: identificador exposto como se fosse nome.** `u_wall`,
`bypass`, `four_rooms` são chaves do código; num caminho estão no sítio certo,
numa frase não dizem nada a quem lê. Aconteceu no Arquivo e em dois seletores
de campanha.

Réguas que saíram desta passagem — a parte que não é preciso rever outra vez:

| régua | apanha | ensaiada |
|---|---|---|
| `verificar_vitrine.py` | os 18 números escritos à mão das legendas, contra os CSV; figuras que não existem; campanhas escondidas | 6/6 mutações |
| `verificar_dashboard.py` → `vocabulario` | formas abandonadas e chaves internas em texto de ecrã, e os 7 nomes contra a `tab:res_eval` | 7/7 mutações |
| `verificar_comandos_dashboard.py` | os 13 comandos que o dashboard manda copiar: o ficheiro existe, as opções são as declaradas | 4/4 mutações |
| `verificar_ptpt.py` (alargado) | brasileirismos e concordância nos **23 ficheiros de ecrã**, não só nos `.tex` | 3/3 mutações |

As quatro entraram no `pre-commit`, no ramo que dispara quando `dashboard/` ou
`configs/vitrine.yaml` mudam.

### Próxima passagem — por fazer

- [ ] **Episódio 3D** — ver um episódio de cada algoritmo até ao fim.
- [ ] **Galeria e Vídeos** — abrir dez figuras ao acaso e confirmar que a
      legenda descreve o que a imagem mostra.
- [ ] **Ciência e Defesa** — as sete respostas às QI, lidas do princípio ao fim.
- [ ] **Treinar / Servidor / Ao vivo** — só na torre; confirmar que não prometem
      o que não podem fazer sem VPN.
- [ ] **A cópia do Pi** — a última publicação é de 6 ago; tudo isto só lá chega
      quando `atualizar_pi.sh` correr.
