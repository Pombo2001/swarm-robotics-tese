# Proposta: o que treinar (e o que NÃO treinar) nos últimos 2 meses

**Data**: 10 jul 2026 · **Prazo**: versão composta ao Prof. Nunes até **15 set** (entrega 30 set)
**Estado**: campanha de 7 dias FECHADA; tese (99 págs) e artigo (8 págs) escritos e coerentes com os dados.

> Documento autónomo, para leitura por quem não acompanhou o projeto.
> Contexto completo em `docs/PLANO_DE_ATAQUE.md` (secção "RESULTADOS FINAIS").

---

## 1. Onde estamos

Compararam-se três controladores para uma tarefa de *foraging* 3D com $N=20$ agentes:

| Sigla | Paradigma | Arquitetura |
|---|---|---|
| **GNN** | Neuroevolução (estratégia de evolução) | Rede de grafos com atenção sobre vizinhos |
| **PPO** | RL on-policy | MLP `[256,256]`, *parameter sharing* |
| **SAC** | RL off-policy | MLP `[256,256]`, *parameter sharing* |

**Campanha final**: 3 algos × 7 cenários × **7 runs** independentes = 147 treinos
(GNN 195 min/run com ~30 núcleos; PPO/SAC 48 min/run com 16 núcleos).
**Avaliação**: 20 episódios determinísticos por run, seeds emparelhadas entre algoritmos.
**Significância**: Mann-Whitney + δ de Cliff sobre as **médias por run** (n=7). A unidade
estatística independente é o *run de treino*, não o episódio.

Recolhas/ep (média ± dp *entre runs*), sucesso médio, **[runs a 100%]**:

| Cenário | GNN | PPO | SAC |
|---|---|---|---|
| Sandbox | 38.3±31.0 (86%) **[5/7]** | **71.5**±1.0 (100%) [7/7] | 69.2±1.9 (100%) [7/7] |
| Muro em U | 24.5±32.7 (43%) **[3/7]** | **39.6**±36.7 (71%) **[4/7]** | 9.0±15.1 (34%) **[2/7]** |
| Gargalo | 121.4±20.0 (100%) [7/7] | **123.2**±1.2 (100%) [7/7] | 41.4±36.8 (72%) **[5/7]** |
| Quatro Salas | **59.8**±13.2 (100%) [7/7] | 33.6±3.8 (100%) [7/7] | 31.8±3.3 (100%) [7/7] |
| Porta Cooperativa | **69.8**±1.0 (100%) [7/7] | 67.1±3.7 (100%) [7/7] | 62.1±2.5 (100%) [7/7] |
| Perceção Cooperativa | **19.0**±8.7 (91%) **[6/7]** | 15.3±0.4 (100%) [7/7] | 16.1±0.8 (100%) [7/7] |
| Porta c/ Alternativa | **86.7**±2.0 (100%) [7/7] | 85.3±4.0 (100%) [7/7] | 68.6±3.4 (100%) [7/7] |

**Achado central**: o "colapso do evolutivo" reportado em campanhas anteriores era um
**artefacto do desenho da função de aptidão**, não uma limitação do paradigma. A aptidão
antiga usava o **retorno acumulado**, que é *farmável*: o progresso e a exploração rendem a
cada passo, portanto genomas que deambulam indefinidamente maximizavam-na sem nunca entrar
no ninho (observaram-se retornos brutos ≈88 000 com **zero** recolhas), porque parar no
ninho corta o rendimento por passo. Substituindo-a pelo **homing terminal**

$$J(\theta) = \bar{f}\cdot 10^4 \;+\; 5000\cdot\bar{h}, \qquad
\bar{h}=\operatorname{clip}\!\big((\Phi_0-\Phi_T)/\Phi_0,\,0,\,1\big)$$

— que depende só dos estados **extremos** do episódio e por isso só se maximiza a *terminar*
junto ao ninho — o GNN converge em **28/28 runs** dos quatro labirintos não-decetivos.

---

## 2. As duas lacunas que restam

### Lacuna A — o Muro em U não está resolvido por ninguém, e não sabemos porquê falha
É o único cenário bimodal nos três paradigmas: cada run ou aprende o desvio e faz 100%, ou
falha por completo (GNN 3/7, PPO 4/7, SAC 2/7). **Nenhuma diferença é significativa.**

O ponto importante — e que é fácil enunciar mal — é que **o sinal de treino está correto**:
o potencial de progresso é **geodésico** neste cenário (`swarm_env_3d.py:259`), logo o
gradiente aponta sempre para o contorno do beco. O que falha é a **descoberta**: em execução
o agente só observa a bússola de *homing* **euclidiana** e o LiDAR local, pelo que percorrer
o desvio significa afastar-se, durante dezenas de passos, da única direção que ele perceciona
como sendo o ninho.

> Ou seja: o Muro em U é hoje o verdadeiro problema de **deceção sob observabilidade parcial**
> deste trabalho.

### Lacuna B — a comparação do Novelty Search está confundida com o orçamento
O resultado atual (Novelty **81.3** vs objetivo puro **64.5** no bypass, +26%, Wilcoxon
$p=8.7\times10^{-5}$, δ de Cliff $=+1.00$) foi obtido com **600 min de treino contra 195**.
Mede o efeito conjunto de *novidade + orçamento*, não a novidade. É a primeira objeção que
qualquer revisor levanta, e já está escrita como ressalva na tese.

Entretanto a campanha final mostrou que o **homing sozinho** resolve o bypass de forma
consistente (7/7 runs, 86.7 rec/ep — acima do resultado com novidade). Isso degradou a QI6
de "a novidade dá o melhor resultado" para "a novidade não é condição necessária".

---

## 3. Proposta

### ⭐ Prioridade 1 — Novelty Search no **Muro em U**, orçamento igualado
`7 runs × 195 min ≈ 23 h`

A experiência mais afiada que ainda é possível fazer. A tese afirma textualmente que o Muro em
U "isola o ingrediente que falta a todos" e que é "precisamente a motivação da linha de Novelty
Search" — **mas o Novelty nunca foi corrido no Muro em U.** É uma promessa por cumprir.

Os dois desfechos servem:
- **Se a convergência subir acima de 3/7** → a QI6 passa de "a novidade não é necessária" para
  *"a novidade resolve o único cenário que a procura objetiva não resolve"*. Contributo a sério.
- **Se não subir** → resultado negativo limpo sobre os limites da pressão por novidade, com o
  mesmo orçamento e o mesmo protocolo. Publicável e honesto.

### ⭐ Prioridade 2 — Novelty Search no **bypass**, orçamento igualado (195 min)
`7 runs × 195 min ≈ 23 h`

Fecha a Lacuna B de vez: mede a novidade **isolada** do orçamento, no mesmo cenário e protocolo
onde a comparação original foi feita.

### Prioridade 3 (opcional) — alargar o **Muro em U** para ~30 runs, nos 3 algoritmos
`GNN 23×195min ≈ 75h · PPO 23×48min ≈ 18h · SAC ≈ 18h` → ~4 dias com paralelismo

**Aviso honesto: isto não garante significância.** Se as taxas verdadeiras forem as observadas
(PPO 4/7 ≈ 0.57, SAC 2/7 ≈ 0.29), um teste exato de Fisher com n=30 por grupo dá **p ≈ 0.07** —
continua sem estrela. Para 80% de poder a essa diferença seriam precisos ~48 runs por grupo.

O que se ganha não é a significância, é um **intervalo de confiança utilizável** para a
probabilidade de convergência: com 3/7 o IC95% vai de ≈0.16 a ≈0.75 (não diz nada); com n=30
estreita para algo reportável. Melhoria real, mas modesta. **É o primeiro a cortar se o tempo apertar.**

### ❌ O que NÃO fazer

**Não repetir a campanha completa 7×7 com mais runs.** Custa ~28 dias de GNN em série
(~2 semanas com os dois servidores), consome praticamente toda a janela até 15 set, e o retorno
é variância mais apertada em células que **já estão a 100% em todos os runs**. Além disso reabre
um texto que está fechado e coerente. Não compensa.

**Não tentar a política de atenção treinada por gradiente.** Isolaria o otimizador da arquitetura
e daria escalabilidade *zero-shot* ao PPO — cientificamente é o passo mais valioso de todos, e é
a limitação nº 1 declarada na tese. Mas é implementação nova de uma *custom policy* em SB3 com
observação de cardinalidade variável, com risco real de consumir três semanas e não convergir.
Fica onde está: **trabalho futuro**.

---

## 4. Custo total e calendário

| | Wall-clock | Servidor |
|---|---|---|
| Prioridade 1 + 2 | **~2 dias** (em paralelo nos dois servidores) | `.14` + `.26` |
| Prioridade 3 | ~4 dias | `.14` (GNN) + `.26` (PPO/SAC) |
| **Total** | **< 1 semana** | |

Sobram ~7 semanas para integrar os resultados, rever a tese e o artigo. Margem confortável.

**Estado do servidor** (verificado 10 jul, 11:42): `.14` livre, 64 vCPU, load 0.00, sem `tmux`.
`results/logs/_sessao_treino.txt` tem 49 linhas (7 cenários × 7 runs do GNN).

---

## 5. Cautelas metodológicas (não negociáveis)

1. **Pré-registar o número de runs.** Decidir *antes* de ver os resultados e **reportar todos**.
   Correr dez e ficar com os sete melhores invalida a estatística.
2. **Seeds sem colisão.** `run_experiments.py` passa `--seed <índice do run>` (linha 148), e
   `--resume` salta os runs já registados em `_sessao_treino.txt`. Runs novos ⇒ seeds 8, 9, 10…
   Não há sobreposição com os 7 existentes — mas também não há desculpa para cherry-picking.
3. **Confirmar que o servidor tem o código do HEAD antes de lançar.** A armadilha em que o
   `.pth` guardava apenas o **último** run já mordeu uma vez (corrigida em `d9a2c45`).
4. **Orçamento igualado.** O ponto inteiro das prioridades 1 e 2 é os 195 min. Se se der mais
   tempo ao Novelty, repete-se o erro que se quer corrigir.
5. **Não alterar `configs/foraging.yaml` nem `src/` entre campanhas.** Os runs novos têm de ser
   comparáveis com os 7 existentes.

---

## Anexo — títulos alternativos para o artigo

O título atual (*"Aprendizagem Adaptativa versus Robustez Estática"*) enquadra um contraste que
os dados dissolveram: o achado que sobrevive é sobre o **sinal de treino**, e há um segundo
achado independente sobre a **representação**.

1. **"Aptidão, Representação e Otimizador: Uma Comparação Controlada entre Neuroevolução e
   Aprendizagem por Reforço no Controlo de Enxames"** — nomeia os três fatores que o trabalho
   separa. *Recomendado.*
2. **"O Desenho da Aptidão Como Fator Decisivo na Neuroevolução de Enxames"** — põe o achado
   central à frente, mas subalterniza a escalabilidade.
3. **"Colapso Aparente: Como o Desenho da Função de Aptidão Determina a Neuroevolução no
   Controlo de Enxames"** — o mais memorável e honesto sobre o percurso (concluiu-se o oposto
   antes). Arriscado se o júri for conservador.
4. Manter o atual + subtítulo *"…: o papel decisivo do desenho da aptidão"*. Menor risco.
