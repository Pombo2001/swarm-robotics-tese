# A/B do SAC no mapa grande — critério escrito ANTES dos dados

> **27 jul 2026.** Escrito antes de lançar os braços novos. O braço de controlo
> (baseline) já existe: é o F0 corrido hoje de manhã, cujos números estão abaixo
> e **não mudam**. Isto é uma decisão de **engenharia** (hiperparâmetros de um
> algoritmo de biblioteca), não uma hipótese científica da tese — mas segue o
> mesmo hábito do `PRE_REGISTO_MAPA_GRANDE.md`, porque a tentação de escolher o
> braço que der o número melhor é exatamente a mesma.

## 1. O que motivou isto (facto medido, não suspeita)

No F0 de hoje, o SAC fez **`n_updates = 26 000` para `total_timesteps = 2 600 000`**
— **um gradient step por cada 100 transições**. As 100 vêm do *parameter sharing*:
cada `step()` do `SubprocVecEnv` devolve `num_cpu × num_agents` = 5 × 20 transições,
e o SB3 faz `gradient_steps=1` por `step()`. O SAC é desenhado para um rácio de
replay ≈ 1.

⚠️ **Isto não é um bug e não invalida nada do que está publicado.** Nos 7 cenários
da tese o rácio era ainda mais baixo (`num_cpu=16` ⇒ 320 transições por update,
rácio 0,003) e o SAC produziu 62,1 na Porta Cooperativa e 68,6 no Bypass. A questão
aqui é outra: **num mapa com episódios 4× mais longos, compensa trocar amostras por
gradiente?**

## 2. Braços (2 h cada, em paralelo, `num_cpu=5`, seed 1, `mapa_grande`)

| braço | mudança | hipótese |
|---|---|---|
| **baseline** | nada (`ent_coef=0.1`, `gradient_steps=1`, buffer 500k) | já corrido: F0 de 27 jul |
| **A+B** | `gradient_steps=5`, `buffer_size=2M` | rácio 0,01 → 0,05; o buffer deixa de guardar só os últimos 19% |
| **C** | `ent_coef=auto` | deixa a política concentrar-se (o PPO fá-lo: `std` 0,996 → 0,809) |

Tudo o resto — ambiente, recompensas, rede [256,256], `learning_rate` 1e-4 —
idêntico nos três.

## 3. Números do baseline (fixos, não voltam a ser calculados)

- `ep_task_mean` = **0,0 em todas as 12 leituras** (nenhuma recolha em 2 h)
- `ep_rew_mean` por leitura: 366 · −155 · −23 · −70 · 63 · 31 · −214 · 45 · −96 ·
  −70 · 636 · 901 — **amplitude 1115**, desvio-padrão ≈ 340
- `critic_loss` 4970 → 96,6 · `actor_loss` −11,2 → −6,07 · `ep_len_mean` = 2000 sempre
- Referência de passeio aleatório, medida no mesmo mapa: **−127 por agente**
  (energia −2000, exploração +182, PBRS −720, tarefa 0, somados nos 20 agentes)

## 4. Critério de decisão (pré-comprometido)

Por ordem — só se passa ao seguinte em caso de empate:

1. **`ep_task_mean` > 0.** Qualquer braço que recolha alguma coisa em 2 h ganha aos
   que não recolhem. (O baseline não recolheu.)
2. **Estabilidade:** menor desvio-padrão do `ep_rew_mean` nas últimas 6 leituras.
   Um braço só conta como mais estável se descer o desvio-padrão em **≥30%**.
3. **Tendência:** média das últimas 3 leituras menos a das 3 primeiras.

**Compromissos:**
- Se **nenhum** braço recolher e nenhum baixar o desvio ≥30%, a conclusão é
  **"nada a corrigir"** e o F2 corre com o SAC **inalterado** — que é o que o
  `PRE_REGISTO_MAPA_GRANDE.md` já manda em §5 ("PPO/SAC não convergem em 2000
  passos → Reportar. O custo por episódio é 4× o dos outros cenários — faz parte
  do que o mapa mede").
- 2 h **não** provam convergência; provam diferença de regime. Nenhum braço será
  descrito como "o SAC corrigido" sem uma corrida com o orçamento do F2.
- Se um braço vencer, entra no `foraging.yaml` **com o default a manter o
  comportamento atual**, e a alteração é declarada como emenda datada no
  pré-registo do mapa — o SAC do mapa deixa de ser o SAC dos 7 cenários, e isso
  tem de estar escrito na secção de resultados do mapa.
- Um único braço, uma única seed: isto **não** é evidência publicável, é uma
  decisão de configuração. Não entra em tabelas da tese.
