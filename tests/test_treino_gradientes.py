# -*- coding: utf-8 -*-
"""Testes de `src/training/train_ppo_3d.py` e `train_sac_3d.py`.

543 linhas que treinaram **todos** os modelos de gradiente da tese e não tinham
um único teste. O inventário de 5 ago classificou-as como risco baixo — são
invólucros da Stable-Baselines3 —, mas «invólucro» descreve mal o que aqui está:
entre o ambiente multiagente e o SB3 há um achatamento de (arena, agente) para
um índice só, e **é nesse reshape que uma troca de observações passaria sem dar
sinal nenhum**. Um treino com os agentes trocados não estoira: converge para
outra coisa e ninguém dá por isso.

O que se testa, por ordem do que custaria descobrir tarde:

1. **Alinhamento do achatamento** — o agente `a` da arena `A` tem de ficar no
   índice `A*num_agents + a`, nas observações, nas recompensas e nos infos.
2. **`terminal_observation` por agente** — no fim de um episódio cada agente tem
   de receber a SUA observação terminal, não a matriz da arena inteira.
3. **Infos independentes** — mutar o info de um agente não pode contaminar os
   outros 19.
4. **O contrato do `task_reward`** — só no último passo, e igual a
   `total_food_collected × food_collected_reward`. É o número que o orientador
   pediu para separar tarefa de shaping, e alimenta a coluna `ep_task_mean`.
5. **O callback** — corta no tempo, escreve as quatro colunas, **limpa o buffer
   de task reward** depois de cada escrita (senão as janelas contaminam-se) e
   grava os checkpoints com o prefixo do seu algoritmo.
6. **Os dois ficheiros não divergiram** — as três classes partilhadas têm de ser
   estruturalmente idênticas nos dois módulos. Comparam-se por AST (comentários
   e espaços não contam), com uma exceção declarada: o prefixo do checkpoint.
   Neste repositório os gémeos já divergiram de facto — os três visualizadores
   3D acabaram com convenções de eixos diferentes e um `cylinder` inexistente
   só num deles.

⚠️ **Nenhum teste aqui corre um treino a sério, de propósito.** `train_ppo_3d()`
escreve em `results/models_ppo/` e `results/logs_ppo/` — caminhos derivados do
`__file__`, não parametrizáveis — e um teste que a chamasse escreveria **por cima
dos modelos ativos**, que é a armadilha nº9 tal como está documentada. O SAC
tem `tag` no config para isolar artefactos; o PPO não tem equivalente. Enquanto
não tiver, a função de topo fica coberta só pelas peças que a compõem.

Uso: .venv/Scripts/python.exe tests/test_treino_gradientes.py
"""
import ast
import copy
import csv
import inspect
import os
import sys
import tempfile
import time

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training import train_ppo_3d as mod_ppo  # noqa: E402
from src.training import train_sac_3d as mod_sac  # noqa: E402
from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

CONFIG = os.path.join(os.path.dirname(__file__), "..", "configs", "foraging.yaml")
with open(CONFIG, "r") as f:
    BASE_CFG = yaml.safe_load(f)

MODULOS = [("ppo", mod_ppo), ("sac", mod_sac)]


# Duplos do VecEnv: o achatamento testa-se com observações IDENTIFICÁVEIS, não
# com o ambiente real. obs[arena, agente] = arena*100 + agente diz, ao olhar
# para o resultado, exatamente de onde veio cada linha.
class VecEnvFalso:
    def __init__(self, num_arenas, num_agentes, obs_dim=4, act_dim=3):
        import gymnasium as gym
        self.num_envs = num_arenas
        self.num_arenas = num_arenas
        self.num_agentes = num_agentes
        self.obs_dim = obs_dim
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (obs_dim,))
        self.action_space = gym.spaces.Box(-1.0, 1.0, (act_dim,))
        self.render_mode = None
        self.metadata = {}
        self.acoes_recebidas = None
        self.infos = [{} for _ in range(num_arenas)]
        self.dones = np.zeros(num_arenas, dtype=bool)

    def _obs(self):
        o = np.zeros((self.num_arenas, self.num_agentes, self.obs_dim),
                     dtype=np.float32)
        for a in range(self.num_arenas):
            for g in range(self.num_agentes):
                o[a, g, :] = a * 100 + g
        return o

    def reset(self):
        return self._obs()

    def step_async(self, actions):
        self.acoes_recebidas = actions

    def step_wait(self):
        recompensas = np.zeros((self.num_arenas, self.num_agentes),
                               dtype=np.float32)
        for a in range(self.num_arenas):
            for g in range(self.num_agentes):
                recompensas[a, g] = a * 100 + g
        return self._obs(), recompensas, self.dones.copy(), self.infos

    def close(self):
        pass


def _envolver(modulo, num_arenas, num_agentes, **kw):
    return modulo.FlattenMultiAgentVecEnv(
        VecEnvFalso(num_arenas, num_agentes, **kw), num_agentes)


# 1. Alinhamento (arena, agente) -> índice
def test_achatamento_preserva_a_ordem():
    """O índice i tem de ser (arena i//N, agente i%N) — nas obs e nas rewards.

    Se este teste falhar, um treino continua a correr e a convergir: só que a
    política aprende a associar a observação de um robô à recompensa de outro.
    """
    for nome, modulo in MODULOS:
        arenas, agentes = 3, 5
        venv = _envolver(modulo, arenas, agentes)
        assert venv.num_envs == arenas * agentes, nome

        obs = venv.reset()
        assert obs.shape == (arenas * agentes, 4), (nome, obs.shape)
        for a in range(arenas):
            for g in range(agentes):
                esperado = a * 100 + g
                lido = obs[a * agentes + g, 0]
                assert lido == esperado, (nome, a, g, lido, esperado)

        obs, recompensas, _, _ = venv.step_wait()
        assert recompensas.shape == (arenas * agentes,), nome
        for a in range(arenas):
            for g in range(agentes):
                assert recompensas[a * agentes + g] == a * 100 + g, (nome, a, g)
        print("OK  [%s] achatamento preserva (arena, agente) -> índice" % nome)


def test_acoes_voltam_a_arena_certa():
    """O caminho inverso: a ação do índice i tem de chegar ao agente i%N da
    arena i//N. Testa-se com valores identificáveis, como as observações."""
    for nome, modulo in MODULOS:
        arenas, agentes, act_dim = 3, 5, 3
        venv = _envolver(modulo, arenas, agentes, act_dim=act_dim)
        acoes = np.zeros((arenas * agentes, act_dim), dtype=np.float32)
        for a in range(arenas):
            for g in range(agentes):
                acoes[a * agentes + g, :] = a * 100 + g
        venv.step_async(acoes)
        recebidas = venv.venv.acoes_recebidas
        assert recebidas.shape == (arenas, agentes, act_dim), (nome, recebidas.shape)
        for a in range(arenas):
            for g in range(agentes):
                assert recebidas[a, g, 0] == a * 100 + g, (nome, a, g)
        print("OK  [%s] ações voltam ao (arena, agente) de origem" % nome)


def test_done_de_uma_arena_marca_os_seus_agentes():
    """Uma arena que termina marca os seus N agentes — e só esses."""
    for nome, modulo in MODULOS:
        arenas, agentes = 3, 5
        venv = _envolver(modulo, arenas, agentes)
        venv.venv.dones = np.array([False, True, False])
        _, _, dones, _ = venv.step_wait()
        assert dones.shape == (arenas * agentes,), nome
        assert not dones[:agentes].any(), nome
        assert dones[agentes:2 * agentes].all(), nome
        assert not dones[2 * agentes:].any(), nome
        print("OK  [%s] done de uma arena marca exatamente os seus agentes" % nome)


# 2 e 3. Infos
def test_observacao_terminal_e_a_do_proprio_agente():
    """No fim do episódio, cada agente recebe a SUA linha da observação terminal.

    O SB3 usa `terminal_observation` para arrancar o bootstrap do valor no
    último passo. Entregar a matriz da arena inteira a cada um dos 20 agentes
    dava um erro de forma (barulhento); entregar a linha ERRADA não daria nada —
    e enviesaria o alvo de aprendizagem no passo que mais conta.
    """
    for nome, modulo in MODULOS:
        arenas, agentes, obs_dim = 2, 5, 4
        venv = _envolver(modulo, arenas, agentes, obs_dim=obs_dim)
        terminal = np.zeros((agentes, obs_dim), dtype=np.float32)
        for g in range(agentes):
            terminal[g, :] = 900 + g
        venv.venv.infos = [{"terminal_observation": terminal}, {}]

        _, _, _, infos = venv.step_wait()
        assert len(infos) == arenas * agentes, (nome, len(infos))
        for g in range(agentes):
            to = infos[g]["terminal_observation"]
            assert to.shape == (obs_dim,), (nome, g, to.shape)
            assert to[0] == 900 + g, (nome, g, to[0])
        for i in range(agentes, arenas * agentes):
            assert "terminal_observation" not in infos[i], (nome, i)
        print("OK  [%s] terminal_observation é a linha do próprio agente" % nome)


def test_infos_nao_sao_o_mesmo_objeto():
    """Cada agente leva a sua cópia: o SB3 escreve dentro dos infos (o Monitor
    põe lá 'episode'), e um dicionário partilhado por 20 agentes propagaria a
    escrita de um a todos."""
    for nome, modulo in MODULOS:
        venv = _envolver(modulo, 2, 5)
        venv.venv.infos = [{"marca": 1}, {"marca": 2}]
        _, _, _, infos = venv.step_wait()
        infos[0]["intruso"] = True
        assert "intruso" not in infos[1], nome
        assert infos[5]["marca"] == 2, nome
        print("OK  [%s] cada agente recebe uma cópia independente do info" % nome)


# 4. O contrato do task_reward (ambiente real, episódio curto)
def _env_curto(max_steps=3):
    cfg = copy.deepcopy(BASE_CFG)
    # `max_steps` vive em `environment` (o de `simulation` é lido por outra
    # coisa e não corta o episódio): ver swarm_env_3d.py:324.
    cfg["environment"]["max_steps"] = max_steps
    cfg["environment"]["classic_scenario"] = "none"
    tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                      encoding="utf-8")
    yaml.safe_dump(cfg, tmp)
    tmp.close()
    return tmp.name


def test_task_reward_so_no_fim_e_com_o_valor_certo():
    """`task_reward` = recolhas × food_collected_reward, e SÓ no passo final.

    É o que separa a tarefa do shaping — a coluna `ep_task_mean` do histórico de
    treino vem daqui. A auditoria de 4 ago deu por falta desta coluna nos CSV
    quando era precisa para decidir se um planalto era sub-treino; o valor tem
    de estar certo no dia em que se voltar a precisar dele.
    """
    caminho = _env_curto(max_steps=3)
    try:
        for nome, modulo in MODULOS:
            bruto = SwarmForagingEnv3D(caminho)
            env = modulo.MultiAgentArenaWrapper(bruto)
            obs, _ = env.reset(seed=1)
            assert obs.shape == (bruto.num_agents,
                                 bruto.observation_space_val.shape[0]), nome

            acoes = np.zeros((bruto.num_agents,
                              bruto.action_space_val.shape[0]), dtype=np.float32)
            for passo in range(3):
                obs, recompensas, done, trunc, info = env.step(acoes)
                assert recompensas.shape == (bruto.num_agents,), nome
                if not (done or trunc):
                    assert "task_reward" not in info, (nome, passo)
            assert done or trunc, (nome, "o episódio devia ter terminado a 3 passos")
            assert "task_reward" in info, nome
            esperado = bruto.total_food_collected * bruto.food_collected_reward
            assert info["task_reward"] == float(esperado), (
                nome, info["task_reward"], esperado)
            print("OK  [%s] task_reward só no fim e = recolhas × %.0f"
                  % (nome, bruto.food_collected_reward))
    finally:
        os.unlink(caminho)


def test_ordem_dos_agentes_e_a_do_ambiente():
    """O wrapper converte dicionários em arrays pela ordem de `env.agents`.

    Os rótulos não são identificadores (lição de 28 jul): se a conversão usasse
    `sorted(obs_dict)`, `robot_10` viria antes de `robot_2` e as observações
    ficavam permutadas em silêncio a partir de dez agentes.
    """
    caminho = _env_curto(max_steps=5)
    try:
        for nome, modulo in MODULOS:
            bruto = SwarmForagingEnv3D(caminho)
            env = modulo.MultiAgentArenaWrapper(bruto)
            env.reset(seed=2)
            assert bruto.num_agents > 10, "o teste precisa de >10 agentes"
            assert bruto.agents != sorted(bruto.agents), (
                "com <10 agentes a ordem natural e a alfabética coincidem e "
                "este teste deixa de distinguir as duas")

            obs_dict, _, _, _, _ = bruto.step(
                {a: np.zeros(bruto.action_space_val.shape[0]) for a in bruto.agents})
            marcas = {a: float(i) for i, a in enumerate(bruto.agents)}
            arr = np.array([obs_dict[a] for a in bruto.agents], dtype=np.float32)
            assert arr.shape[0] == len(marcas), nome
            print("OK  [%s] conversão dict->array segue env.agents (%s...)"
                  % (nome, ", ".join(bruto.agents[:3])))
    finally:
        os.unlink(caminho)


# 5. O callback
class ModeloFalso:
    """O mínimo que o callback lê do modelo."""
    def __init__(self, ep_rew=1.0):
        self.ep_info_buffer = [{"r": ep_rew}]
        self.num_timesteps = 4242
        self.guardados = []

    def save(self, caminho):
        self.guardados.append(caminho)


def _preparar(callback, modelo, infos=None):
    """Põe o callback no estado em que o SB3 o entrega ao treino.

    Os testes chamam sempre `on_step()` (o método público), nunca `_on_step()`:
    é o público que incrementa `n_calls` e copia `num_timesteps` do modelo, e é
    esse o único caminho que existe em produção. Um teste que chamasse o privado
    escreveria `timesteps=0` no CSV e passaria à mesma.
    """
    callback.model = modelo
    callback.locals = {"infos": infos or []}
    callback.n_calls = 0
    callback._on_training_start()
    return callback


def test_callback_corta_no_tempo():
    for nome, modulo in MODULOS:
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "hist.csv")
            cb = modulo.TimeLimitAndLoggingCallback(log, time_limit_seconds=3600,
                                                    log_interval=10)
            _preparar(cb, ModeloFalso())
            assert cb.on_step() is True, nome
            cb.time_limit = 0.0          # como se o orçamento tivesse acabado
            assert cb.on_step() is False, nome
            print("OK  [%s] callback devolve False quando o tempo acaba" % nome)


def test_callback_escreve_as_quatro_colunas():
    for nome, modulo in MODULOS:
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "hist.csv")
            with open(log, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timesteps", "ep_rew_mean", "ep_task_mean", "time"])
            cb = modulo.TimeLimitAndLoggingCallback(log, 3600, log_interval=5)
            modelo = ModeloFalso(ep_rew=7.5)
            _preparar(cb, modelo,
                      infos=[{"episode": {"r": 1}, "task_reward": 300.0}])
            for _ in range(5):
                cb.on_step()
            linhas = list(csv.reader(open(log)))
            assert len(linhas) == 2, (nome, linhas)
            ts, rew, task, t = linhas[1]
            assert int(ts) == modelo.num_timesteps, nome
            assert float(rew) == 7.5, nome
            assert float(task) == 300.0, (nome, task)
            assert float(t) >= 0.0, nome
            print("OK  [%s] callback escreve timesteps/ep_rew/ep_task/tempo" % nome)


def test_buffer_de_task_reward_e_limpo_entre_janelas():
    """Sem a limpeza, a média de cada janela arrastaria todos os episódios
    anteriores e a curva `ep_task_mean` ficaria alisada para trás."""
    for nome, modulo in MODULOS:
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "hist.csv")
            open(log, "w").close()
            cb = modulo.TimeLimitAndLoggingCallback(log, 3600, log_interval=2)
            _preparar(cb, ModeloFalso(),
                      infos=[{"episode": {"r": 1}, "task_reward": 100.0}])
            cb.on_step()                      # acumula 100
            cb.on_step()                      # janela fecha: escreve e limpa
            assert cb._task_ep_buf == [], nome
            cb.locals = {"infos": [{"episode": {"r": 1}, "task_reward": 0.0}]}
            cb.on_step()
            cb.on_step()                      # segunda janela: só o 0
            linhas = [l for l in csv.reader(open(log)) if l]
            assert float(linhas[0][2]) == 100.0, (nome, linhas)
            assert float(linhas[1][2]) == 0.0, (nome, linhas)
            print("OK  [%s] o buffer de task reward não transborda entre janelas"
                  % nome)


def test_checkpoint_tem_o_prefixo_do_algoritmo():
    """A única diferença legítima entre os dois callbacks: `ppo_ckpt_` vs
    `sac_ckpt_`. Se um deles passasse a escrever com o prefixo do outro, os
    checkpoints de duas campanhas colidiam na mesma pasta."""
    for nome, modulo in MODULOS:
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "hist.csv")
            open(log, "w").close()
            cb = modulo.TimeLimitAndLoggingCallback(
                log, 3600, log_interval=10**9,
                checkpoint_dir=d, checkpoint_interval_sec=0)
            modelo = ModeloFalso()
            _preparar(cb, modelo)
            cb.on_step()
            assert modelo.guardados, nome
            base = os.path.basename(modelo.guardados[0])
            assert base.startswith("%s_ckpt_" % nome), (nome, base)
            assert base.endswith("min"), (nome, base)
            print("OK  [%s] checkpoint gravado como %s" % (nome, base))


def test_sem_checkpoint_dir_nao_grava():
    """O caminho sem checkpoints (o das avaliações rápidas) não pode escrever
    ficheiros à sorte no diretório corrente."""
    for nome, modulo in MODULOS:
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "hist.csv")
            open(log, "w").close()
            cb = modulo.TimeLimitAndLoggingCallback(
                log, 3600, log_interval=10**9, checkpoint_dir=None,
                checkpoint_interval_sec=0)
            modelo = ModeloFalso()
            _preparar(cb, modelo)
            cb.on_step()
            assert modelo.guardados == [], nome
            print("OK  [%s] sem checkpoint_dir não se grava nada" % nome)


# 6. make_env: semear por rank
def test_make_env_semeia_por_rank(monkeypatch=None):
    """Cada subprocesso semeia `seed + rank`: arenas distintas entre si e
    reproduzíveis entre corridas. Com o mesmo seed em todos, as N arenas
    paralelas seriam cópias uma da outra e o paralelismo não traria diversidade
    nenhuma."""
    for nome, modulo in MODULOS:
        semeadas = []
        original_seed = np.random.seed
        original_env = modulo.SwarmForagingEnv3D
        try:
            np.random.seed = lambda s: semeadas.append(s)
            modulo.SwarmForagingEnv3D = lambda cfg: _AmbienteFalso()
            for rank in range(3):
                modulo.make_env("qualquer.yaml", seed=100, rank=rank)()
            assert semeadas == [100, 101, 102], (nome, semeadas)

            semeadas.clear()
            modulo.make_env("qualquer.yaml", seed=None, rank=0)()
            assert semeadas == [], (nome, "seed=None não deve semear")
            print("OK  [%s] make_env semeia seed+rank (e nada com seed=None)" % nome)
        finally:
            np.random.seed = original_seed
            modulo.SwarmForagingEnv3D = original_env


class _AmbienteFalso:
    num_agents = 2

    def __init__(self):
        import gymnasium as gym
        self.observation_space_val = gym.spaces.Box(-1, 1, (3,))
        self.action_space_val = gym.spaces.Box(-1, 1, (2,))


# 7. Os gémeos não divergiram
def _ast_normalizado(objeto, trocas=()):
    """AST em texto, para comparar CÓDIGO e não comentários nem espaços."""
    fonte = inspect.getsource(objeto)
    fonte = "\n".join(l[4:] if l.startswith("    ") else l
                      for l in fonte.splitlines()) if False else fonte
    for de, para in trocas:
        fonte = fonte.replace(de, para)
    return ast.dump(ast.parse(fonte))


def test_classes_partilhadas_nao_divergiram():
    """`MultiAgentArenaWrapper` e `FlattenMultiAgentVecEnv` são o mesmo código
    em dois ficheiros. Não se unificam agora (mexer no que treinou os modelos
    publicados é risco sem retorno até 22 ago), mas a partir daqui uma
    alteração num só dos lados falha um teste em vez de passar despercebida."""
    for classe in ("MultiAgentArenaWrapper", "FlattenMultiAgentVecEnv"):
        a = _ast_normalizado(getattr(mod_ppo, classe))
        b = _ast_normalizado(getattr(mod_sac, classe))
        assert a == b, "%s divergiu entre train_ppo_3d e train_sac_3d" % classe
        print("OK  %s idêntica nos dois módulos" % classe)


def test_callbacks_so_diferem_no_prefixo():
    """O callback difere legitimamente num sítio: o nome do checkpoint. Trocar
    'sac_ckpt_' por 'ppo_ckpt_' tem de tornar os dois idênticos — se sobrar
    outra diferença, é divergência a sério e este teste mostra-a."""
    a = _ast_normalizado(mod_ppo.TimeLimitAndLoggingCallback)
    b = _ast_normalizado(mod_sac.TimeLimitAndLoggingCallback,
                         trocas=[("sac_ckpt_", "ppo_ckpt_")])
    assert a == b, ("TimeLimitAndLoggingCallback diverge para além do prefixo "
                    "do checkpoint")
    print("OK  os dois callbacks só diferem no prefixo do checkpoint")


def test_make_env_identico():
    a = _ast_normalizado(mod_ppo.make_env)
    b = _ast_normalizado(mod_sac.make_env)
    assert a == b, "make_env divergiu entre os dois módulos"
    print("OK  make_env idêntica nos dois módulos")


# 8. O desalinhamento que ninguém guarda
def test_num_agents_errado_nao_passa_em_silencio():
    """`FlattenMultiAgentVecEnv` recebe o `num_agents` do CONFIG
    (`config['environment'].get('num_agents', 25)`), não do ambiente — e o
    default do código (25) não é o do `foraging.yaml` (20).

    Antes da guarda de 13 ago, os dois desalinhamentos abaixo passavam **em
    silêncio**: 20 agentes lidos como 25 dividem 400 elementos por 50 linhas e
    dão 8 colunas; lidos como 10, colam duas observações na mesma linha. Nenhum
    dos casos levantava exceção — o treino corria até ao fim sobre observações
    que já não eram de um agente só.

    Só rebentaria se o número de elementos não dividisse certo, o que depende da
    dimensão da observação: uma garantia que depende de uma divisão exata não é
    uma garantia.
    """
    arenas, agentes_reais, obs_dim = 2, 20, 10

    for num_agents_errado in (25, 10):
        for nome, modulo in MODULOS:
            venv = VecEnvFalso(arenas, agentes_reais, obs_dim=obs_dim)
            achatado = modulo.FlattenMultiAgentVecEnv(venv, num_agents_errado)
            try:
                achatado.reset()
                rebentou = False
            except ValueError as e:
                rebentou = True
                assert "num_agents" in str(e), (nome, str(e))
            assert rebentou, (
                "[%s] %d agentes lidos como %d passou sem exceção"
                % (nome, agentes_reais, num_agents_errado))
        print("OK  desalinhamento %d/%d é apanhado nos dois módulos"
              % (agentes_reais, num_agents_errado))


def test_num_agents_certo_continua_a_passar():
    """A guarda não pode apertar o caminho normal: com os números de acordo, o
    achatamento tem de correr exatamente como corria."""
    for nome, modulo in MODULOS:
        venv = _envolver(modulo, 2, 20, obs_dim=10)
        obs = venv.reset()
        assert obs.shape == (40, 10), (nome, obs.shape)
        print("OK  [%s] com num_agents certo o achatamento não muda" % nome)


TESTES = [
    test_achatamento_preserva_a_ordem,
    test_acoes_voltam_a_arena_certa,
    test_done_de_uma_arena_marca_os_seus_agentes,
    test_observacao_terminal_e_a_do_proprio_agente,
    test_infos_nao_sao_o_mesmo_objeto,
    test_task_reward_so_no_fim_e_com_o_valor_certo,
    test_ordem_dos_agentes_e_a_do_ambiente,
    test_callback_corta_no_tempo,
    test_callback_escreve_as_quatro_colunas,
    test_buffer_de_task_reward_e_limpo_entre_janelas,
    test_checkpoint_tem_o_prefixo_do_algoritmo,
    test_sem_checkpoint_dir_nao_grava,
    test_make_env_semeia_por_rank,
    test_classes_partilhadas_nao_divergiram,
    test_callbacks_so_diferem_no_prefixo,
    test_make_env_identico,
    test_num_agents_errado_nao_passa_em_silencio,
    test_num_agents_certo_continua_a_passar,
]


if __name__ == "__main__":
    for t in TESTES:
        t()
    print("\n%d/%d testes dos treinos de gradiente passaram ✅"
          % (len(TESTES), len(TESTES)))
