# =============================================================================
# GNN — Algoritmo Neuro-Evolutivo com Rede Neuronal de Grafos
# Desenvolvido de raiz (sem bibliotecas de RL externas)
#
# Paradigma: ALGORITMO GENÉTICO / EVOLUTION STRATEGIES
#   Baseado em: Salimans et al. (2017) "Evolution Strategies as a Scalable
#   Alternative to Reinforcement Learning" — mutação Gaussiana element-wise.
#
# Genoma: vector 1D contendo TODOS os pesos e biases da GNNAgent3D.
#   A política é o mapeamento directo do genoma → acções.
#   Topologia da rede é FIXA — não evolui estrutura, apenas pesos.
#
# Estratégia de mutação (Element-wise Gaussian Mutation com máscara):
#   Para cada peso w_i do filho:
#     com probabilidade mutation_rate (10%): w_i += N(0, sigma)
#     caso contrário: w_i permanece igual ao pai
#   Isto é equivalente a (1+λ)-ES com mask esparsa — não muta todos os pesos
#   em simultâneo (reduziria demasiado a diversidade com redes grandes).
#
# Elitismo: os 20% melhores (elite_count=6 de 30) são preservados sem mutação.
#   O restante da população é gerado a partir de cópias mutadas dos elites.
#
# Sigma decay: sigma começa em 0.1 e decai 0.1%/geração (×0.999) até mín. 0.03.
#   Exploração agressiva no início → refinamento gradual.
#
# Fitness: DOMINADA PELA TAREFA. Cada recolha (food) vale 10000 — muito acima
#   de qualquer reward de shaping —, e o shaping entra apenas COMPRIMIDO por uma
#   tangente hiperbólica (5000·tanh(reward/5000)) como gradiente/desempate quando
#   nenhum genoma ainda recolhe. Isto evita o reward hacking: a fitness anterior
#   era o reward bruto (que inclui o shaping de progresso + exploração), pelo que
#   a evolução maximizava o shaping sem cumprir a tarefa (ex.: 98k de fitness com
#   0 recolhas no Muro U). A exploração vem da estocasticidade da mutação Gaussiana.
#
#   Porquê tanh e não clip(±5000): o clip SATURAVA no teto +5000 sempre que o
#   shaping acumulado passava de 5000 (frequente: 500 passos × 20 agentes). Com o
#   teto atingido o termo virava CONSTANTE → deixava de dar gradiente. No Muro U
#   (food sempre 0) todos os genomas decentes ficavam com fitness=5000.0 EXACTO →
#   seleção cega, o GNN nunca progredia (origem dos valores redondos 5000/15000/
#   75000 nos logs). A tanh é monótona e nunca satura abruptamente: continua a
#   distinguir um genoma que se aproxima do ninho de outro que vagueia, mantendo
#   food a dominar (1 recolha = 10000 >> amplitude ±5000 do shaping).
#
# Avaliação: cada genoma corre eval_episodes episódios num conjunto de seeds FIXO
#   ao longo de todas as gerações (eval_seed_base constante). Antes a seed mudava
#   por geração (gen_seed = seed + gen), o que tornava a fitness ruidosa e fazia os
#   elites re-avaliados saltar/cair — as "quedas estranhas na recompensa média".
#   Conjunto fixo + eval_episodes>1 estabiliza a seleção e reduz overfitting a 1 mapa.
#
# Paralelismo: cada genoma é avaliado num processo separado (multiprocessing).
# =============================================================================
import os
import sys
# Limitar BLAS/OpenMP a 1 thread ANTES de importar numpy/torch. Cada genoma é
# avaliado num processo separado (Pool); sem este limite, cada um dos 30 workers
# tenta usar todos os núcleos em threads (ex.: 30 workers × 32 threads ≈ 965
# threads em 64 cores = 15× oversubscription, contenção brutal -> 1 geração
# demorava >17 min). Com 1 thread/worker, 30 workers cabem nos núcleos sem luta
# e cada geração acelera ~10-15×. NÃO afeta PPO/SAC (são scripts separados).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
import torch
import numpy as np
import copy
import time
import csv
import json
import argparse
import yaml
from datetime import datetime
from multiprocessing import Pool, cpu_count

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.agents.gnn_agent_3d import GNNAgent3D


def _minmax(x):
    """Normaliza para [0,1] por geração (min-max). Vetor constante → zeros, para
    não amplificar ruído quando todos os genomas têm o mesmo score."""
    x = np.asarray(x, dtype=float)
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def evaluate_genome(args):
    # Reforço por worker: garante 1 thread mesmo que o fork tenha herdado outro
    # valor; redes pequenas avaliam mais rápido single-thread (sem overhead de
    # threading) e evita a contenção entre os 30 processos do Pool.
    torch.set_num_threads(1)
    weights, config_path, eval_seed = args
    # Os pesos chegam como arrays numpy (ver args_list em train(): evita o estouro
    # de file descriptors do pickle de tensores torch). Reconstrói o state_dict.
    weights = {k: torch.from_numpy(v) if isinstance(v, np.ndarray) else v
               for k, v in weights.items()}
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    guillotine_threshold = config['simulation'].get('guillotine_threshold', -200)
    eval_episodes = config.get('evolution', {}).get('eval_episodes', 2)

    env = SwarmForagingEnv3D(config_path)
    agent = GNNAgent3D("worker_agent", env.action_space("robot_0"), config_path)
    agent.load_state_dict(weights)

    episode_rewards = []
    episode_foods = []
    episode_homing = []   # fração [0,1] de aproximação ao ninho no FIM do episódio
    episode_bc = []       # behavior characterization p/ Novelty Search (centroide final x,y)
    total_steps = 0

    for ep in range(eval_episodes):
        # Conjunto de seeds de avaliação FIXO entre gerações: todos os genomas e
        # os elites re-avaliados enfrentam os mesmos mapas -> seleção estável e
        # reproduzível, sem o ruído de avaliar cada geração numa seed diferente.
        ep_seed = (eval_seed + ep) if eval_seed is not None else None
        obs_dict, _ = env.reset(seed=ep_seed)
        # Potencial (distância geodésica/euclidiana ao ninho) de cada agente no
        # INÍCIO. O env calcula-o no reset (env.prev_pot). Serve de referência para
        # medir homing = quanto os agentes se aproximaram do ninho até ao fim.
        start_pot = np.array(env.prev_pot, dtype=float).copy()
        episode_reward = 0
        steps = 0
        done = False

        while not done:
            obs_list = [obs_dict[a] for a in env.agents]
            obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)

            with torch.no_grad():
                actions_tensor = agent(obs_tensor)
                actions_np = actions_tensor.cpu().numpy()

            actions = {id: act for id, act in zip(env.agents, actions_np)}
            obs_dict, rewards, terms, truncs, _ = env.step(actions)

            episode_reward += sum(rewards.values())
            steps += 1

            if steps == 150 and episode_reward < guillotine_threshold:
                episode_reward -= 1000
                done = True

            if any(terms.values()) or any(truncs.values()):
                done = True

        episode_rewards.append(episode_reward)
        # total_food_collected é zerado no reset, por isso é lido por episódio
        # (antes só o último episódio contava — bug).
        episode_foods.append(int(env.total_food_collected))
        # Homing: quão perto do ninho os agentes TERMINAM. Usa-se o potencial final
        # (geodésico nos labirintos -> contorna paredes). frac=1 se o agente chega ao
        # ninho (pot=0), 0 se não se aproximou. É NÃO-FARMÁVEL: depende só dos extremos
        # (início vs fim), não do caminho -> ao contrário do reward acumulado, vaguear
        # a explorar não o aumenta. Agentes no ninho ficam com pot=0 (frac=1).
        end_pot = np.array([env._potential(p) for p in env.agent_positions], dtype=float)
        frac = np.clip((start_pot - end_pot) / (start_pot + 1e-6), 0.0, 1.0)
        episode_homing.append(float(np.mean(frac)))
        # BC do Novelty Search: posição final (x,y) do centroide do swarm. Captura
        # PARA ONDE o genoma levou os agentes — genomas que exploram regiões novas
        # (ex. o desvio do bypass) ganham novelty mesmo sem food. Só usado se
        # novelty_weight>0; barato de calcular sempre.
        episode_bc.append(np.mean(np.asarray(env.agent_positions)[:, :2], axis=0))
        total_steps += steps

    avg_reward = float(np.mean(episode_rewards))   # reward bruto (só diagnóstico)
    avg_food   = float(np.mean(episode_foods))     # recolhas (tarefa pura)
    avg_homing = float(np.mean(episode_homing))    # aproximação ao ninho [0,1]
    # Fitness DOMINADA PELA TAREFA: cada recolha vale food_weight (>> shaping). O
    # shaping é o HOMING (proximidade FINAL ao ninho), NÃO o reward acumulado.
    # PORQUÊ: o reward acumulado (progresso + exploração) é FARMÁVEL — o GNN
    # maximizava-o a vaguear/explorar sem nunca entrar no ninho (RewBruto ~88000,
    # comida 0), porque parar no ninho corta o rendimento por passo. Selecionar pelo
    # homing premeia genomas cujos agentes ACABAM no ninho (= pré-condição de comer,
    # required_to_eat=1 nos labirintos); assim que um come, food*food_weight domina.
    # O homing é não-farmável (só conta o estado final, não o caminho).
    evo = config.get('evolution', {})
    food_weight = evo.get('fitness_food_weight', 10000.0)
    shaping_amp = evo.get('fitness_shaping_amplitude', 5000.0)
    shaping_term = shaping_amp * avg_homing
    fitness = avg_food * food_weight + shaping_term
    bc = np.mean(np.asarray(episode_bc), axis=0)   # (2,) centroide final médio
    return fitness, total_steps, avg_food, avg_reward, avg_homing, bc


class GeneticTrainer3D:
    def __init__(self, config_path, time_limit_minutes=120, seed=None,
                 log_dir=None, model_dir=None):
        # log_dir/model_dir: overrides opcionais (testes correm em dirs isolados
        # para não tocar nos CSVs/modelos reais); por omissão, results/ do repo.
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.time_limit_seconds = time_limit_minutes * 60
        # Reprodutibilidade: semeia a população inicial e as mutações.
        self.seed = seed
        if seed is not None:
            np.random.seed(seed)
            torch.manual_seed(seed)

        # Seeds de AVALIAÇÃO fixas ao longo das gerações: todos os genomas (e os
        # elites re-avaliados) enfrentam SEMPRE o mesmo conjunto de eval_episodes
        # mapas. Estabiliza a seleção e a curva de fitness — elimina o overfitting
        # a uma seed sortuda que mudava a cada geração (antes: gen_seed = seed + gen,
        # causa das "quedas estranhas" na recompensa média). Runs distintos (--seed
        # diferente) usam conjuntos distintos; dentro de um run o conjunto é fixo.
        self.eval_seed_base = (seed if seed is not None else 0) + 10000

        temp_env = SwarmForagingEnv3D(config_path)
        self.template_agent = GNNAgent3D("template_3d", temp_env.action_space("robot_0"), config_path)

        evo_config = self.config.get('evolution', {})
        self.pop_size = evo_config.get('pop_size', 30)
        self.mutation_rate = evo_config.get('mutation_rate', 0.10)
        self.sigma = evo_config.get('sigma', 0.1)  # desvio da mutação Gaussiana (foraging.yaml)
        # Piso e decaimento da sigma lidos do config: manter exploração viva ao longo
        # das gerações (antes 0.01/0.995 colapsava ~0.055 em 120 gen -> convergência
        # prematura -> campeão decora as seeds de avaliação = overfitting). Defaults
        # mais conservadores; o elitismo preserva os melhores, a sigma só afeta filhos.
        self.sigma_min = evo_config.get('sigma_min', 0.03)
        self.sigma_decay = evo_config.get('sigma_decay', 0.999)

        # ── Novelty Search (Lehman & Stanley 2011) — desligado por defeito ──
        # novelty_weight=0 → seleção 100% pelo objetivo (comportamento idêntico ao
        # histórico). >0 → score de seleção = blend normalizado objetivo/novelty,
        # para escapar a ótimos DECEPTIVE (ex. cooperative_door_bypass, onde o
        # gradiente de homing aponta para um beco). O save/log seguem sempre o
        # OBJETIVO. Ver _novelty_scores e o bloco de seleção em train().
        self.novelty_weight = evo_config.get('novelty_weight', 0.0)
        self.novelty_k = evo_config.get('novelty_k', 10)
        self.novelty_archive_max = evo_config.get('novelty_archive_max', 1000)
        self.novelty_add_per_gen = evo_config.get('novelty_add_per_gen', 3)
        self.novelty_archive = []

        # ── Novelty ADAPTATIVO — anneal do peso após a descoberta ──
        # Evidência (campanhas de 11 jul 2026, orçamento igualado 7×195 min):
        # w=0.5 FIXO ganha no u_wall (7/7 vs 3/7 — a novidade paga a DESCOBERTA do
        # desvio) mas perde no bypass (63.0 vs 86.7 — depois de descobrir, metade da
        # pressão seletiva continua gasta em diversidade redundante e custa
        # MAGNITUDE). O anneal junta os dois regimes: w mantém-se cheio enquanto o
        # melhor genoma não come; após novelty_sustain_gens gerações consecutivas
        # com comida, decai ×novelty_decay/geração até 0 (seleção volta ao objetivo
        # puro). Nunca re-arma: o elitismo preserva os genomas que comem, e re-armar
        # tornaria a seleção não-estacionária.
        self.novelty_adaptive = evo_config.get('novelty_adaptive', False)
        self.novelty_decay = evo_config.get('novelty_decay', 0.98)
        self.novelty_sustain_gens = evo_config.get('novelty_sustain_gens', 10)
        self._food_streak = 0
        self._novelty_annealing = False

        # ── Cache da fitness dos elites ──
        # Os elites entram intactos na população seguinte e eram RE-avaliados em
        # todas as gerações com as MESMAS seeds fixas e política determinística →
        # resultado idêntico (verificável nos logs: fitness do melhor constante
        # entre gerações sem melhoria). Guardar o resultado poupa elite_count/pop
        # (~20%) das avaliações por geração. A novelty continua correta: recalcula-se
        # em todas as gerações a partir dos BCs (cacheados para os elites), porque o
        # arquivo cresce. Desligável no config para testes de equivalência.
        self.elite_cache = evo_config.get('elite_cache', True)
        self._elite_results = None   # resultados (na ordem 0..elite_count-1) dos elites
        self.elite_count = max(3, int(self.pop_size * 0.2))

        self.population = []
        for i in range(self.pop_size):
            random_brain = GNNAgent3D(f"temp_{i}", temp_env.action_space("robot_0"), config_path)
            self.population.append(copy.deepcopy(random_brain.state_dict()))

        self.log_dir = log_dir or os.path.join(os.path.dirname(__file__), '../../results/logs')
        self.model_dir = model_dir or os.path.join(os.path.dirname(__file__), '../../results/models')
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)

        # Sufixo do cenário para não sobrescrever modelos entre cenários.
        # Convenção: none → sem sufixo; outros → _{scenario}
        scenario = self.config['environment'].get('classic_scenario', 'none')
        self.model_suffix = f"_{scenario}" if scenario and scenario != "none" else ""

        # Melhor fitness já GRAVADA neste run (memória do processo): evita regravar
        # um genoma pior quando a fitness da geração oscila (o melhor POR GERAÇÃO
        # pode descer ligeiramente entre gerações).
        self._run_saved_fitness = None

        # CSV canónico (dashboard/monitorização lê este nome fixo) + CSV POR RUN.
        # O canónico é sobrescrito a cada run (mode 'w'), pelo que em campanhas
        # multi-run as curvas dos runs anteriores só sobreviviam via parse do log
        # do tee — o CSV por run preserva-as (analise pós-campanha sem regex).
        self.history_file = os.path.join(self.log_dir, 'gnn_3d_training.csv')
        self._history_files = [self.history_file]
        if self.seed is not None:
            self._history_files.append(os.path.join(
                self.log_dir, f'gnn_3d_training{self.model_suffix}_run{self.seed}.csv'))
        for path in self._history_files:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestep', 'best_fitness', 'avg_fitness',
                                 'best_task_food', 'time'])
            os.chmod(path, 0o666)

    def _save_models(self, best_obj_genome, best_obj_fitness):
        """Guarda o melhor genoma SEM perder campeões de runs anteriores (armadilha nº8).

        Antes gravava `gnn_3d_best{sufixo}.pth` incondicionalmente → em treinos
        multi-run (run_experiments, --seed = nº do run) o ÚLTIMO run apagava os
        campeões dos anteriores (perderam-se u_wall 62.5, none 39.8 e bypass 80.5
        no train3d de 1 jul). Agora:
        - `..._run{seed}.pth`: melhor do RUN atual — cada run fica preservado.
        - `gnn_3d_best{sufixo}.pth` (campeão): só é sobrescrito se a fitness for
          >= à registada no sidecar `.meta.json`. Exceção: --seed 1 (1º run de uma
          campanha nova) sobrescreve sempre — recomeça a campanha, para não ficar
          preso a fitness de campanhas antigas com outra escala de recompensa.
        """
        if self._run_saved_fitness is not None and best_obj_fitness < self._run_saved_fitness:
            return  # o run já tem gravado um genoma melhor que o desta geração
        self._run_saved_fitness = best_obj_fitness

        self.template_agent.load_state_dict(best_obj_genome)
        state = self.template_agent.state_dict()

        if self.seed is not None:
            run_path = os.path.join(self.model_dir,
                                    f"gnn_3d_best{self.model_suffix}_run{self.seed}.pth")
            torch.save(state, run_path)
            os.chmod(run_path, 0o666)

        champ_path = os.path.join(self.model_dir, f"gnn_3d_best{self.model_suffix}.pth")
        meta_path = champ_path[:-4] + ".meta.json"
        if self.seed != 1 and os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    prev = float(json.load(f)["fitness"])
            except Exception:
                prev = None
            if prev is not None and best_obj_fitness < prev:
                return  # o campeão de um run anterior é melhor — mantém-se
        torch.save(state, champ_path)
        os.chmod(champ_path, 0o666)
        with open(meta_path, "w") as f:
            json.dump({"fitness": float(best_obj_fitness), "seed": self.seed,
                       "saved_at": datetime.now().isoformat(timespec="seconds")}, f)
        os.chmod(meta_path, 0o666)

    def _novelty_scores(self, bcs):
        """Novelty de cada genoma = distância média aos k vizinhos mais próximos no
        conjunto (população atual ∪ arquivo histórico de comportamentos). Empurra a
        busca para posições finais do swarm ainda não vistas → escapa a deceptive.
        Atualiza o arquivo com os BCs mais novos da geração (cap FIFO)."""
        bcs = np.asarray(bcs, dtype=float)
        pts = bcs if not self.novelty_archive else np.vstack([bcs, np.asarray(self.novelty_archive)])
        k = min(self.novelty_k, len(pts) - 1)
        nov = np.zeros(len(bcs))
        if k > 0:
            for i in range(len(bcs)):
                d = np.sort(np.linalg.norm(pts - bcs[i], axis=1))[1:k + 1]  # exclui o próprio (0)
                nov[i] = float(np.mean(d))
        # Arquivo: junta os comportamentos mais novos desta geração (cap FIFO).
        for idx in np.argsort(nov)[::-1][:self.novelty_add_per_gen]:
            self.novelty_archive.append(bcs[idx])
        if len(self.novelty_archive) > self.novelty_archive_max:
            self.novelty_archive = self.novelty_archive[-self.novelty_archive_max:]
        return nov

    def _update_novelty_weight(self, best_food):
        """Anneal do peso da novidade (só com novelty_adaptive). Chamar UMA vez por
        geração, DEPOIS da seleção (a geração corrente usa o w com que foi
        selecionada, tal como a sigma). Máquina de estados:
        - fase de descoberta: w intacto; conta gerações consecutivas em que o melhor
          genoma (por objetivo) come (best_food>0). Comida sustentada durante
          novelty_sustain_gens gerações → passa a anneal. Com elitismo + seeds de
          avaliação fixas, um genoma que come nunca sai da elite (minmax do objetivo
          dá-lhe sel_score>=1-w), por isso a streak não oscila por ruído.
        - fase de anneal: w ×= novelty_decay por geração; abaixo de 1e-3 fecha em 0.0
          exato, o que desliga o ramo de novelty no train() (seleção = objetivo puro,
          bit-idêntica ao histórico). Não re-arma."""
        if not (self.novelty_adaptive and self.novelty_weight > 0.0):
            return
        if self._novelty_annealing:
            self.novelty_weight *= self.novelty_decay
            if self.novelty_weight < 1e-3:
                self.novelty_weight = 0.0
            return
        self._food_streak = self._food_streak + 1 if best_food > 0 else 0
        if self._food_streak >= self.novelty_sustain_gens:
            self._novelty_annealing = True

    def train(self):
        # Avalia a população toda em paralelo (1 genoma por núcleo). Em servidores
        # com muitos núcleos, isto reduz drasticamente o tempo por geração —
        # crucial para a neuroevolução, que precisa de muitas gerações.
        num_cores = min(self.pop_size, cpu_count())

        print(f"[START] Treino GNN 3D Iniciado (Meta: Orcamento de {self.time_limit_seconds / 60:.1f} minutos)")
        print(f"[ACELERACAO] {num_cores} NUCLEOS DO RYZEN A AVALIAR EM PARALELO!")
        print("[INFO] Funcionalidades: Pure Evolution + Guilhotina")

        global_timestep = 0
        overall_start_time = time.time()
        gen = 1
        # Fallback: se o tempo esgotar antes da 1ª geração terminar, ainda há algo
        # para guardar (evita NameError no save final).
        population_sorted = self.population
        best_obj_genome = self.population[0]   # melhor por OBJETIVO (food) — o que se guarda
        best_obj_fitness = float("-inf")       # idem (genoma não avaliado não bate campeões)

        with Pool(processes=num_cores) as pool:
            while True:
                cumulative_time = time.time() - overall_start_time
                if cumulative_time >= self.time_limit_seconds:
                    print(f"\n[FIM DO TEMPO] O cronometro atingiu o limite. A fechar e guardar o modelo...")
                    break

                # Conjunto de seeds de avaliação FIXO entre gerações (ver __init__).
                # Converte cada genoma (state_dict de tensores torch) para arrays
                # NUMPY antes de o enviar aos workers. Motivo: o pickle de tensores
                # torch usa memória partilhada/file-descriptors por tensor (com
                # pop_size=30 são 450+ por geração) -> estoura o ulimit
                # ("OSError: [Errno 24] Too many open files") e, mesmo subindo o
                # ulimit, fica lentíssimo (o resource_sharer engasga e o Pool deixa
                # de paralelizar: 1 geração passava de ~60s para >9min). Os arrays
                # numpy fazem pickle POR VALOR — rápidos e sem FDs. São reconvertidos
                # em tensores dentro de evaluate_genome.
                # Cache dos elites: population[0..elite_count-1] são os elites da
                # geração anterior (intactos, deep-copy) — o seu resultado com as
                # seeds fixas é determinístico, logo reutiliza-se. Só os filhos
                # mutados vão ao Pool. Na 1ª geração (sem cache) avalia-se tudo.
                cached = (self._elite_results if self.elite_cache else None) or []
                args_list = [({k: v.detach().cpu().numpy() for k, v in self.population[i].items()},
                              self.config_path, self.eval_seed_base)
                             for i in range(len(cached), self.pop_size)]
                results = cached + pool.map(evaluate_genome, args_list)

                obj_scores   = np.array([res[0] for res in results])
                food_counts  = [res[2] for res in results]
                rewards_raw  = [res[3] for res in results]
                homing_vals  = [res[4] for res in results]
                bcs          = np.array([res[5] for res in results])
                # Só os passos realmente EXECUTADOS nesta geração contam para o
                # timestep global (os elites cacheados não correram episódios).
                total_steps_this_gen = sum(res[1] for res in results[len(cached):])
                global_timestep += total_steps_this_gen

                cumulative_time = time.time() - overall_start_time

                # Score de SELEÇÃO: por defeito é o objetivo puro (idêntico ao
                # histórico). Com Novelty Search (novelty_weight>0) faz-se um blend
                # normalizado objetivo/novelty para escapar a deceptive. O SAVE e o
                # LOG seguem sempre o OBJETIVO (best_obj_idx) — guardamos quem resolve
                # a tarefa, não quem é só comportamentalmente novo.
                if self.novelty_weight > 0.0:
                    nov_raw = self._novelty_scores(bcs)
                    sel_scores = ((1.0 - self.novelty_weight) * _minmax(obj_scores)
                                  + self.novelty_weight * _minmax(nov_raw))
                    gen_novelty = float(np.mean(nov_raw))
                else:
                    sel_scores = obj_scores
                    gen_novelty = 0.0

                best_obj_idx = int(np.argmax(obj_scores))   # melhor por tarefa (log/save)
                best_obj_genome = self.population[best_obj_idx]

                sorted_indices = np.argsort(sel_scores)[::-1]
                scores = obj_scores[sorted_indices]   # objetivo reordenado (compat. log)
                population_sorted = [self.population[i] for i in sorted_indices]

                elite_count = self.elite_count
                new_population = [copy.deepcopy(population_sorted[i]) for i in range(elite_count)]
                # Resultados dos elites (na MESMA ordem em que entram na população
                # seguinte) — reutilizados na próxima geração se elite_cache ativo.
                self._elite_results = [results[i] for i in sorted_indices[:elite_count]]

                while len(new_population) < self.pop_size:
                    parent_idx = np.random.randint(0, elite_count)
                    child = copy.deepcopy(population_sorted[parent_idx])

                    for key in child.keys():
                        # Element-wise mutation
                        mask = (torch.rand_like(child[key]) < self.mutation_rate).float()
                        child[key] += mask * torch.randn_like(child[key]) * self.sigma

                    new_population.append(child)

                self.population = new_population

                # Estatísticas reportadas/guardadas seguem o MELHOR POR OBJETIVO
                # (best_obj_idx), não o melhor por seleção — com novelty estes podem
                # divergir e queremos sempre acompanhar quem resolve a tarefa.
                best_obj_fitness = float(obj_scores[best_obj_idx])
                best_food = food_counts[best_obj_idx]
                best_reward = rewards_raw[best_obj_idx]
                best_homing = homing_vals[best_obj_idx]
                # Homing = proximidade final ao ninho do melhor genoma ([0,1]; 1=chegou).
                # É o sinal de seleção dos labirintos: deve subir antes de aparecer
                # comida. RewBruto fica só como diagnóstico (já não entra na fitness).
                # w atual no log quando a novelty está ativa (com anneal vê-se o
                # decaimento e o momento em que fecha em 0). flush=True fura o
                # buffer de 8KB do pipe para o tee — sem isto as linhas Gen só
                # apareciam no log a cada ~55 gerações.
                novelty_str = (f"Novelty: {gen_novelty:.2f} | w: {self.novelty_weight:.3f} | "
                               if self.novelty_weight > 0.0 else "")
                print(
                    f"Gen {gen} | Steps: {global_timestep} | "
                    f"Fitness: {best_obj_fitness:.1f} | Média: {np.mean(obj_scores):.1f} | "
                    f"Comida (melhor): {best_food} | Homing: {best_homing:.3f} | "
                    f"{novelty_str}"
                    f"RewBruto: {best_reward:.0f} | Sigma: {self.sigma:.4f} | "
                    f"Tempo: {cumulative_time:.1f}s", flush=True)

                # Apply Adaptive Mutation (Decay)
                self.sigma = max(self.sigma_min, self.sigma * self.sigma_decay)
                # Anneal da novelty (se adaptativa) — mesma cadência da sigma: a
                # geração corrente foi selecionada com o w antigo; o novo vale já
                # para a próxima.
                self._update_novelty_weight(best_food)

                for path in self._history_files:
                    with open(path, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([global_timestep, best_obj_fitness, np.mean(obj_scores),
                                         best_food, cumulative_time])

                if gen % 10 == 0:
                    self._save_models(best_obj_genome, best_obj_fitness)

                gen += 1

        self._save_models(best_obj_genome, best_obj_fitness)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_limit", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=None,
                        help="Semente de reprodutibilidade (omitir = aleatorio)")
    parser.add_argument("--config", type=str, default=None,
                        help="Caminho do config YAML (default: configs/foraging.yaml). "
                             "Permite correr um treino isolado (ex. Novelty Search num "
                             "config dedicado) sem mexer no foraging.yaml partilhado.")
    args = parser.parse_args()

    from multiprocessing import freeze_support

    freeze_support()

    config_path = args.config or os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')
    trainer = GeneticTrainer3D(config_path, time_limit_minutes=args.time_limit, seed=args.seed)
    trainer.train()