# `scripts/` — o que é cada coisa

Oitenta e tal ficheiros à mesma altura. Este índice agrupa-os por aquilo que
fazem; os nomes seguem uma convenção que vale a pena conhecer antes de
procurar:

| prefixo | responde a |
|---|---|
| `verificar_` | **o que a tese afirma bate com os dados?** — sai 0 ou 1, e alguns correm no *pre-commit* |
| `auditar_` | **este artefacto está completo e coerente?** (campanha, dashboard, cenário) |
| `analise_` | **a análise PRÉ-REGISTADA** de uma campanha: a regra estava escrita antes dos dados |
| `eval_` | avaliação determinística de modelos treinados |
| `figuras_` / `gerar_figuras_` | as imagens que entram na dissertação |
| `*.sh` | correm **no servidor** do ISCTE, ou falam com ele |

Nada aqui é obrigatório para reproduzir a tese: esse caminho está em
[`docs/REPRODUZIR.md`](../docs/REPRODUZIR.md).

---

## Verificadores — a tese contra os dados

Os marcados com **⟨hook⟩** correm no `pre-commit` sempre que a tese ou os dados
mudam, e recusam o commit se um número deixar de bater
(`scripts/instalar_hooks.sh` instala-os).

| script | o que confere |
|---|---|
| `verificar_numeros_tese.py` **⟨hook⟩** | o grosso: tabelas, prosa, Resumo/Abstract, coerência interna e o artigo — ~965 valores |
| `verificar_mapa_grande.py` **⟨hook⟩** | os 72 valores da secção do mapa composto (QI7) |
| `verificar_estrutura_tese.py` **⟨hook⟩** | acrónimos, figuras/tabelas órfãs, páginas com uma linha só, rótulos das tabelas |
| `verificar_ptpt.py` **⟨hook⟩** | português de Portugal: léxico, `babel`, e a concordância de «execução» |
| `verificar_remissoes.py` **⟨hook⟩** | cada «Figura~\ref{...}» aponta mesmo para uma figura |
| `verificar_contagens_prosa.py` **⟨hook⟩** | os «X/Y execuções» escritos em prosa |
| `verificar_protocolo.py` **⟨hook⟩** | os valores de protocolo (execuções, episódios, minutos) existem nas campanhas |
| `verificar_vertical.py` **⟨hook⟩** | os números da limitação «dimensão vertical» |
| `verificar_spawn_gargalo.py` **⟨hook⟩** | os números da limitação «spawn dentro da barreira» |
| `verificar_parte1.py` | os números dos capítulos 1 a 4 |
| `verificar_slr_corpo.py` | o que a tese afirma sobre o corpo da revisão sistemática |
| `verificar_bibliografia.py` | as referências existem e são o que a bibliografia diz |
| `verificar_preregistos.py` | os compromissos dos três pré-registos foram cumpridos e reportados |
| `verificar_figuras_tese.py` | cada figura do PDF é a que os dados produzem hoje |
| `verificar_figuras_artigo.py` **⟨hook⟩** | as figuras do artigo acompanham as da tese (cópias idênticas, versões da coluna não mais velhas) |
| `verificar_planalto.py` | as curvas estabilizaram dentro do orçamento |
| `verificar_dashboard.py` | os números do dashboard são os da tese |
| `verificar_paridade_pi.py` | tudo o que as vistas leem é enviado para o Raspberry Pi |
| `verificar_sessao.py` | uma sessão de treino produziu todos os artefactos |
| `cobertura_verificador.py` | **que afirmações da tese ainda não têm verificador** (gera `docs/COBERTURA_VERIFICADOR.md`) |
| `ensaiar_verificador.py` | estraga a tese de propósito e confirma que os verificadores acusam |

## Auditorias

| script | |
|---|---|
| `auditar_campanhas.py` | cada campanha tem dados, gráficos, vídeo, heatmaps e modelos |
| `auditar_dashboard.py` | corre antes de publicar no Pi |
| `auditar_mapa_grande.py` | o 8.º cenário contra os sete fechados |
| `ensaiar_reproduzir.py` | ensaia o `docs/REPRODUZIR.md` de ponta a ponta |

## Análise pré-registada

A regra de decisão estava escrita antes de existirem dados; estes scripts
aplicam-na e não a escolhem.

| script | pré-registo |
|---|---|
| `analise_megatreino.py` | mega-treino de 1 mês (M1, M2, M3) |
| `analise_adaptativo.py` | dosagem adaptativa da novidade (T1-T4, QI6) |
| `analise_exploratoria_megatreino.py` | as células exploratórias, rotuladas como tal |
| `analise_mapa_grande.py` | mapa composto: F1 e F2 |
| `analise_f1_controlos.py` | as quatro condições do F1, lidas em conjunto |
| `projetar_limiar_f2.py` | o limiar de convergência ainda é alcançável? |
| `fechar_qi7.py` | aplica a regra do pré-registo e **escreve a QI7 na dissertação** |
| `statistical_tests.py` | Mann-Whitney e delta de Cliff entre algoritmos |

## Avaliação

| script | |
|---|---|
| `eval_by_run.py` | avaliação determinística de todas as execuções de uma campanha |
| `eval_suite.py` | os sete cenários + os gráficos de tarefa |
| `eval_all.py` | os três algoritmos lado a lado |
| `eval_scalability.py` | transferência zero-shot para N variável (QI2) |
| `eval_zeroshot_mapa.py` | F1: zero-shot de topologia no mapa composto |
| `run_eval.py` | avaliação sistemática de modelos treinados |
| `benchmark_sim.py` | throughput do simulador (tabela do desempenho computacional) |
| `sanidade_mapa_grande.py` | o mapa composto é resolúvel? (controlador de referência) |
| `testar_horizonte_mapa_grande.py` | quem dá zero fica sem tempo ou fica preso? |
| `onde_param_mapa_grande.py` | onde é que os campeões param, por distância geodésica |

## Treino e campanhas

Os `.sh` correm no servidor do ISCTE (ver `servidor.sh` para o acesso).

| script | |
|---|---|
| `run_experiments.py` | orquestra as campanhas locais |
| `launch_7d.sh` | watchdog do treino longo de 7 dias |
| `mega_streamA.sh`, `mega_streamB.sh` | as duas streams do mega-treino de 1 mês |
| `mapa_streamF2.sh` | treino nativo no mapa composto (F2) |
| `lancar_f2.sh` | lança o F2 com as verificações antes de disparar |
| `f2_longo_ao_fechar.sh` | lança o braço exploratório quando os gradientes largarem a máquina |
| `controlos_f1.sh` | as condições de controlo do F1 |
| `esperar_f1.sh`, `trazer_f1_ao_fechar.sh` | esperam pelo fecho e trazem os CSV |
| `estado_f2.sh` | instantâneo datado do F2 tal como está no servidor |
| `receber_megaB.sh` | receção da última stream do mega-treino |
| `pos_campanha.py` | checklist de chegada: um comando, três garantias |
| `restaurar_modelos.py` | repõe os modelos arquivados de uma sessão |
| `run_treino24.sh`, `run_treino48.sh`, `analise_pos_treino.sh` | campanhas antigas, mantidas como registo |

## Figuras e visualização

| script | |
|---|---|
| `gerar_figuras_7d.py` | as figuras da campanha final (curvas, dotplots, desempenho global) |
| `gerar_figuras_mapa_grande.py` | planta e figuras do 8.º cenário |
| `figuras_campanha.py` | as mesmas figuras para qualquer campanha |
| `figuras_megatreino.py` | M1, M2 e M3 do mega-treino |
| `figuras_artigo.py` | as versões estreitas, desenhadas para a coluna de 8,9 cm do artigo |
| `plot_results.py`, `plot_robustez.py` | curvas de treino e robustez a falhas |
| `heatmaps.py` | ocupação dos robôs e potencial geodésico |
| `render_maps.py` | renders 3D dos cenários (PyVista) |
| `rastos_mapa_grande.py` | por onde passa cada controlador, em planta |
| `captura_episodio.py`, `record_episode.py` | capturas e GIF de um episódio |
| `exportar_episodio_3d.py` | exporta um episódio para o browser o desenhar |
| `curvas_agregadas.py` | média entre execuções sem a serra |
| `gerar_pdf_reuniao.py` | os gráficos-chave num PDF para reunião |

## Revisão sistemática

| script | |
|---|---|
| `slr_pipeline.py` | o pipeline completo (ver `docs/PROTOCOLO_SLR.md`) |
| `classificar_slr.py` | escreve a classificação dos 58 incluídos, com proveniência |

## Dashboard e publicação

| script | |
|---|---|
| `atualizar_pi.sh` | envia para o Raspberry Pi só o que mudou |
| `empacotar_para_pi.py` | empacota o dashboard em modo leitura |
| `progress.py` | progresso partilhado entre os geradores e o dashboard |

## Servidor e ambiente

| script | |
|---|---|
| `servidor.sh` | o host e o utilizador certos, num sítio só |
| `trazer_do_servidor.sh` | traz ficheiros do servidor |
| `deploy_mapa.sh` | envia o código do mapa composto para um diretório isolado |
| `instalar_hooks.sh` | instala o `pre-commit` deste repositório |

## Validação avulsa

| script | |
|---|---|
| `test_cenario_bypass.py` | validação do 7.º cenário: geometria, porta e caminho alternativo. Vive aqui e não em `tests/` porque é um ensaio manual, não parte da suite |
| `preview_mapa_grande.py` | **retirado** — a geometria do mapa composto passou para o simulador; o ficheiro fica como nota de que já ali esteve |

## Subpastas

- `hooks/` — a fonte do `pre-commit` que o `instalar_hooks.sh` copia.
- `testes/` — ensaios de scripts que não cabem na suite (`pytest tests/`):
  a análise do F2, a integração da QI7, o lançador diferido, e o
  `conferir_readme_scripts.py`, que garante que este índice nomeia todos os
  scripts da pasta e nenhum que já não exista.
