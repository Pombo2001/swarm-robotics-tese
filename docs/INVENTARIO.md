# INVENTÁRIO — o que existe e o que falta

> **Verificado a 27 jul 2026** por leitura direta do disco, não de memória
> (`git` em `cc20eb3`, árvore limpa). Responde a uma pergunta só: *o que é que eu
> tenho, e o que é que ainda não tenho?*
>
> O **plano** (o que fazer e por que ordem) é o
> [`PLANO_MESTRE.md`](PLANO_MESTRE.md). A **proveniência** (de que ficheiro vem
> cada número da tese) é o [`REPRODUZIR.md`](REPRODUZIR.md). Este documento é só
> o inventário.

---

## 1. Resultados, por questão de investigação

| | Questão | Estado | Onde |
|---|---|---|---|
| **QI1** | Desempenho na tarefa ($P_{task}$) e significância | ✅ **FECHADO** | `tab:res_eval`, `tab:res_signif` |
| **QI2** | Escalabilidade Zero-Shot ($S_{scale}$) — representação vs otimizador | ✅ **FECHADO** — 28/28 células a 100% | `tab:res_scale_all` |
| **QI3** | Robustez a falhas ($R_{robust}$) | ✅ **FECHADO** — retenção 92-106% | §res_robustez |
| **QI4** | Critério de escolha (síntese das três) | ✅ **FECHADO** (sem dados próprios) | §res_discussao |
| **QI5** | Desenho da aptidão (*homing* geodésico) | ✅ **FECHADO** — é o achado central | §res_discussao |
| **QI6** | Pressão por novidade, fixa e adaptativa | ✅ **FECHADO** sob pré-registo cumprido | §res_novelty |
| **QI7** | Composição de dificuldades (mapa grande) | 🔄 **EM CURSO** — F1 a correr, F2 por lançar | `seccao_mapa_grande.tex` (por incluir) |

**As seis primeiras não precisam de mais dados.** A tese está completa sem a QI7;
o mapa grande é acrescento, e o pré-registo já fixou que se não fechar até
**22 ago** vai para a defesa em vez da dissertação.

---

## 2. Dados — o que está no disco

### Campanhas fechadas ✅

| Campanha | Linhas | Ficheiro |
|---|---|---|
| **7 dias (2-9 jul)** — a que a tese reporta | 2940 | `results/graficos_tese/final_7d/eval_by_run_7d.csv` |
| Novelty fixo $w=0{,}5$ — Muro em U | 140 | `results/novelty_final/uwall/.../eval_by_run.csv` |
| Novelty fixo $w=0{,}5$ — Bypass | 140 | `results/novelty_final/bypass/.../eval_by_run.csv` |
| Adaptativo A1 (4 cenários @195) | 560 | `results/novelty_adaptativo/week_A_fase1/` |
| Adaptativo A2 (u_wall objetivo @390) | 140 | `week_A_fase2/` |
| Adaptativo B1 (3 cenários @195) | 420 | `week_B_fase1/` |
| Adaptativo B2 (u_wall adaptativo @390) | 140 | `week_B_fase2/` |
| Adaptativo B3 (bypass adaptativo @390) | 140 | `week_B_fase3/` |
| Escalabilidade | 7 CSV | `results/estatisticas/escalabilidade_*.csv` |
| Robustez (10% de falhas) | 21 CSV | `results/evaluation/eval_*_fail10.csv` |
| Significância | 2 CSV | `results/estatisticas/testes_significancia_*.csv` |
| Revisão sistemática | 680 | `docs/slr/screening.csv` (+ `raw/` com 883) |

*2940 = 3 algoritmos × 7 cenários × 7 execuções × 20 episódios. Confere.*

### Em curso 🔄

| | Estado | Fim previsto |
|---|---|---|
| **F1 zero-shot** (mapa grande, 21 células) | a correr neste PC | ~19:30 de 27 jul |
| **Mega-treino megaA** (5 fases) | a correr no servidor | ~1-2 ago |
| **Mega-treino megaB** (7 fases) | a correr no servidor | ~3 ago |

### Ainda não existe ❌

- **F2 do mapa grande** (treino nativo, 3 algoritmos × 7 execuções) — só arranca
  depois do mega-treino libertar o servidor (~3 ago). Custo estimado: **3,8 dias**
  em dois *streams*.
- Os 12 CSV do mega-treino (`results/mega_1mes/`) — chegam com a campanha.

---

## 3. Modelos

| | Ficheiros | Data | Nota |
|---|---|---|---|
| **Campeões 7d** (`results/models_7d/`) | 7 GNN + 7 PPO + 7 SAC | **3-9 jul** ✅ | Trazidos a 27 jul; guarda de campanha a passar. **São estes os da tese.** |
| Modelos **ativos** (`results/models*`) | 7 GNN + 7 PPO + 7 SAC | GNN 3 jul, **PPO/SAC 24 jun** ⚠️ | Os MLP são de antes da campanha 7d — foi o que anulou o F1 de 25 jul |
| Smoke test do mapa (F0) | 8 | 27 jul | `out/f0_smoke_27jul/` — fora de `results/` de propósito |
| A/B do SAC | 6 | 27 jul | `out/ab_sac_27jul/` |

> ⚠️ **Não avaliar a partir de `results/models_ppo|models_sac`.** Os campeões MLP
> da campanha 7d vivem em `results/models_7d/`; os que estão nas pastas ativas são
> de 24 jun e dão zero no próprio cenário de treino. É a armadilha nº9, e já custou
> uma corrida de 6 h.

---

## 4. Documentos

| | Estado |
|---|---|
| **Tese** (`Tese/main.pdf`) | ✅ 121 páginas, 0 refs indefinidas, 0 *overfulls* |
| **Artigo** (`Artigo/artigo.pdf`) | ✅ 10 páginas, idem |
| Secção do mapa grande | 📝 escrita e validada, **por incluir** (faltam os números) |
| Pacote para o orientador | ✅ `out/envio_orientador/` (11,4 MB), **por enviar** |
| Draft do e-mail | ✅ `EMAIL_ORIENTADOR_24jul2026.md` |
| Pré-registos | ✅ 3 (adaptativo, mega-treino, mapa grande) + o A/B do SAC |
| `REPRODUZIR.md` | ✅ auditoria número-a-número completa; 17/17 fontes presentes |

---

## 5. Ferramentas prontas a usar

| | Para quê |
|---|---|
| `scripts/analise_adaptativo.py` | QI6 — já correu sem desvios |
| `scripts/analise_megatreino.py` | **M1-M3 do mega-treino** — pronto antes dos dados; mecânica validada contra números publicados |
| `scripts/analise_mapa_grande.py` | **F1 + F2 do mapa** — pronto antes dos dados |
| `scripts/eval_zeroshot_mapa.py` | F1, com guarda de campanha (recusa modelos da campanha errada) |
| `scripts/pos_campanha.py` | passo 1 obrigatório ao trazer campanhas |
| `scripts/servidor.sh` / `trazer_do_servidor.sh` | estado do servidor / trazer ficheiros |

---

## 6. O que falta, e de quem depende

### Depende do **servidor** (~3 ago)
- [ ] Trazer o mega-treino, correr `analise_megatreino.py`, integrar
- [ ] Enviar o código do mapa para `~/swarm-mapa/` (**o servidor ainda não tem o
      mapa** — `scenarios.py` de lá é de 2 jul)
- [ ] Lançar o F2

### Depende de **mim** (posso fazer já)
- [ ] Slides da defesa — estrutura e narrativa
- [ ] Modo Demo do dashboard (F4) — único pedaço por fazer
- [ ] Vídeos/GIFs dos episódios para a defesa
- [ ] Script de *deploy* para o servidor

### Depende **do Gonçalo**
- [ ] **Enviar o pacote ao orientador** (está pronto)
- [ ] Confirmar qual foi a última versão que o Professor viu
- [ ] Confirmar o ano da capa (2026)
- [ ] **Ler o Iskandar** — é o único dos 58 estudos que compara os paradigmas e
      sustenta a afirmação da lacuna
- [ ] Ler um dos artigos de NEAT
- [ ] Rever o PDF do artigo
- [ ] Decidir o alvo do artigo (conferência vs submissão interna)

---

## 7. Decisões já tomadas (não reabrir)

- **Título:** mantém-se o atual (20 jul)
- **SAC no F2:** inalterado, como nos 7 cenários (27 jul) — o A/B está documentado
- **Correção de física:** só no `mapa_grande`; os 7 cenários ficam bit-a-bit iguais
- **Servidor:** não se toca até o mega-treino fechar
- **O mapa grande não entra** nas tabelas dos 7 cenários

---

## 8. Calendário

| Data | O quê |
|---|---|
| ~1-3 ago | Mega-treino fecha; servidor livre |
| **22 ago** | **Hard stop** — o que fechar depois vai para a defesa, não para a tese |
| **15 set** | Versão composta ao orientador (inegociável) |
| 30 set | Entrega |
| Outubro | Defesa |

Entre 3 e 22 ago há **19 dias** e a campanha do mapa custa ~3,8 — há folga para a
correr mais do que uma vez se correr mal.
