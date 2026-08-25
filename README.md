# Aprendizagem por Reforço para Controlo de Enxames

Simulador 3D de *swarm robotics* (forrageamento cooperativo) e bancada de comparação
entre **três controladores descentralizados** — neuroevolução com rede de grafos, PPO e
SAC — em oito cenários de dificuldade crescente.

Dissertação de Mestrado em Inteligência Artificial, ISCTE-IUL (2026).
Orientação: Prof. Luís Nunes.

**A pergunta:** a inteligência adaptativa (MARL) supera a robustez estática
(bio-inspirada) em cenários de *stress* dinâmico? A resposta curta é *só em parte* — e
a parte que se confirma não está onde a hipótese a punha.

---

## O que este trabalho mede

Sete questões de investigação, sete campanhas fechadas, **2940 episódios de avaliação
determinística** só na campanha principal. Os números abaixo saem todos de CSV
versionados e são conferidos automaticamente (ver [Rigor](#rigor-o-que-impede-este-repositório-de-mentir)).

| | Resultado |
|---|---|
| **Desempenho por tarefa** | O controlador evolutivo com *fitness* de *homing* é **estatisticamente superior** aos métodos de gradiente em três dos sete cenários e indistinguível do melhor deles em mais dois. O PPO é o generalista fiável (converge em todas as execuções de seis cenários); o SAC é o único que falha execuções no Gargalo. |
| **Escalabilidade** | Só a arquitetura de grafo transfere de **N=10 para N=100 sem retreino** — 100 % de sucesso nas 28 combinações cenário × dimensão. O PPO e o SAC são **estruturalmente incompatíveis** com N≠20: a MLP tem entrada fixa. Não é um resultado fraco, é o resultado. |
| **Robustez a falhas** | Com 10 % dos agentes a falhar a meio do episódio, os três paradigmas retêm **92–106 %** do desempenho nas 21 combinações algoritmo–cenário. A redundância vem do *parameter sharing*. |
| **Deceção espacial** | O Muro em U é o único cenário que **nenhum** algoritmo base resolve de forma fiável — é bimodal nos três. Só a hibridização com procura por novidade o resolve, e uma replicação com **28 execuções por braço** mostra que a novidade **doseada adaptativamente** é a única condição de toda a dissertação sem uma execução falhada: **28/28**, contra 15/28 do objetivo puro e 14/28 de cada método de gradiente (Fisher exato, *p* < 0,0001). |
| **Composição de dificuldades** | Um oitavo cenário compõe num só labirinto de **103 × 62 m** quatro das dificuldades que os outros isolam. Transferência sem retreino: **zero** em 84 de 84 células. Com treino nativo, só o evolutivo o resolve — em **4 de 21 execuções**, abaixo do limiar de 15 fixado *antes* dos dados. **Reportado como negativo**, com o número à vista. |
| **Custo** | O evolutivo paga ≈ **8×** mais núcleos-hora por execução do que os métodos de gradiente. |

O contributo metodológico principal é outro, e é uma correção: o «colapso do
evolutivo» que a literatura reporta era, neste sistema, um **artefacto do sinal de
treino**. Substituir o retorno acumulado por *homing* terminal levou o controlador de
0 % a 100 % de sucesso nos quatro cenários de gargalo.

---

## Rigor: o que impede este repositório de mentir

Um número escrito à mão numa tese não tem como se defender de uma campanha que foi
repetida. Por isso a proveniência é automática:

- **24 verificadores** (`scripts/verificar_*.py`) que leem o `.tex` e os CSV e falham
  se discordarem — **849 valores** conferidos só no principal, mais as tabelas de
  configuração contra o `foraging.yaml`, as figuras do PDF contra os dados que as
  produzem (pixel a pixel), as referências contra o CrossRef/arXiv/OpenAlex, e as
  frases onde o número está na palavra («o único», «nenhuma passa de»);
- **183 testes** (`pytest tests/`), incluindo equivalência bit-a-bit do LiDAR
  vetorizado e a física da porta cooperativa;
- um **`pre-commit`** que corre os verificadores relevantes sempre que um commit toca
  na tese, nos dados ou no dashboard (`scripts/instalar_hooks.sh`);
- **três pré-registos** (`docs/PRE_REGISTO_*.md`) com hipótese, métricas e regra de
  decisão fixadas antes de haver dados — incluindo as **emendas datadas** e um braço
  pré-registado que acabou por não correr.

A revisão sistemática que fundamenta o Capítulo 3 foi conduzida de facto: 883 registos
identificados, 680 após desduplicação, **58 estudos incluídos**, com o registo de
triagem completo em `docs/slr/screening.csv` — cada exclusão com o seu motivo.

---

## Os oito cenários

| Chave | Nome na dissertação | O que testa |
|-------|--------------------|-------------|
| `none` | Sandbox | Arena aberta, ninho e obstáculos móveis — a linha de base. |
| `u_wall` | Muro em U | Deceção espacial: o caminho direto ao ninho é uma armadilha. |
| `bottleneck` | Gargalo | Passagem única de 2,5 m — congestionamento. |
| `four_rooms` | Quatro Salas | Navegação em labirinto com quatro passagens. |
| `cooperative_door` | Porta Cooperativa | Porta que só abre com 3 robôs em simultâneo. |
| `cooperative_perception` | Perceção Cooperativa | Alvo móvel, capturado quando rodeado por 3+ robôs. |
| `cooperative_door_bypass` | Porta com Alternativa | Como a anterior, mas com desvio lateral — cenário *deceptive*. |
| `mapa_grande` | Mapa Composto | 103 × 62 m: partida → gargalo + beco em U → quatro salas → porta com alternativa → câmara do ninho. Percurso mínimo de ~155 m. |

> Fonte única dos cenários e das etiquetas: **`src/scenarios.py`**. A lista esteve
> espalhada por oito ficheiros e o sétimo cenário chegou a ser treinado e nunca
> avaliado — não se duplica.

## Os três controladores

| Sigla | Ficheiro | Paradigma |
|-------|----------|-----------|
| **GNN** | `src/training/evo_trainer_3d.py` | Neuroevolução sobre rede de grafos com atenção QKV. Desenvolvido de raiz. |
| **PPO** | `src/training/train_ppo_3d.py` | RL *on-policy* (*stable-baselines3*). |
| **SAC** | `src/training/train_sac_3d.py` | RL *off-policy* com entropia regularizada (*stable-baselines3*). |

Os três partilham uma única política entre os agentes (*parameter sharing*). A
observação de cada agente tem `16 + (N−1) × 5 = 111` valores para N=20: direção e
distância ao ninho, 8 raios de LiDAR (alcance 8 m) e, por vizinho, direção, distância e
estado de sinalização. A exploração é incentivada **só por *reward shaping*** — não há
curiosidade intrínseca.

---

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10+. O treino usa GPU se houver (`device="auto"`).

## Utilização

### Dashboard

```powershell
python -m dashboard.app
```

Quinze vistas: da operação (treinar, servidor, visualizador 3D ao vivo) à leitura dos
resultados (Ciência, Escala e robustez, Mapa composto, Defesa, Proveniência, Galeria,
Vídeos, Episódio 3D, Arquivo). A vista **Proveniência** responde, célula a célula, à
pergunta «de onde vem este número?».

### Linha de comandos

```powershell
# Treino
python src/training/train_ppo_3d.py --time_limit 30
python src/training/evo_trainer_3d.py --time_limit 30

# Avaliação determinística (a unidade estatística é a MÉDIA POR EXECUÇÃO)
python scripts/eval_by_run.py --episodes 20 --scenario u_wall

# Escalabilidade Zero-Shot e resiliência a falhas
python scripts/eval_scalability.py --episodes 20
python scripts/run_eval.py --algo sac --scenario none --episodes 20 --fail-frac 0.1

# Visualizador 3D
python visualization/visualize_algo.py --algo gnn

# As réguas
python scripts/verificar_numeros_tese.py
pytest tests/ -q
```

### Reproduzir os resultados da dissertação

A sequência canónica está em **[`docs/REPRODUZIR.md`](docs/REPRODUZIR.md)** — é ela que
diz de que ficheiro sai cada número. Duas notas que poupam um dia de trabalho:

1. ao trazer uma campanha do servidor, `python scripts/pos_campanha.py` **antes** de
   qualquer avaliação — sem isso avalia-se a campanha anterior;
2. o protocolo é **7 execuções × 20 episódios** com sementes emparelhadas, e a unidade
   estatística é a **média por execução**. Juntar episódios de execuções diferentes
   inflaciona o *n*.

---

## Estrutura

```
configs/foraging.yaml      Configuração única (ambiente, recompensa, treino)
src/
  environment/             Ambiente Gymnasium: física, LiDAR vetorizado, recompensas
  agents/                  Rede de grafos com atenção (política do controlador evolutivo)
  training/                evo_trainer_3d · train_ppo_3d · train_sac_3d
  scenarios.py             Fonte única dos oito cenários e das suas etiquetas
scripts/                   90 guiões: campanhas, avaliação, estatística, figuras e as réguas
  README.md                Índice de todos eles, um a um
dashboard/                 Dashboard NiceGUI (python -m dashboard.app)
visualization/             Visualizadores 3D (Ursina)
tests/                     183 testes
Tese/                      Dissertação LaTeX — 137 páginas
Artigo/                    Artigo destilado da dissertação
docs/                      Protocolo, pré-registos, reprodução, revisão sistemática
results/                   Dados, modelos e figuras (não versionado — ver REPRODUZIR.md)
```

---

## Citação

```bibtex
@mastersthesis{pombo2026enxames,
  title  = {Aprendizagem por Reforço para Controlo de Enxames},
  author = {Pombo, Gonçalo},
  school = {ISCTE --- Instituto Universitário de Lisboa},
  year   = {2026},
}
```
