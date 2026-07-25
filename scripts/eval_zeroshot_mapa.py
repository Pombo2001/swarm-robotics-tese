"""
eval_zeroshot_mapa.py — F1 do pré-registo: Zero-Shot de TOPOLOGIA
=================================================================
Avalia os modelos campeões (treinados nos 7 cenários) num mapa em que NUNCA
treinaram — por omissão o `mapa_grande`. Responde à pergunta da QI7: o que os
algoritmos aprenderam em cenários de dificuldade ISOLADA transfere para um
ambiente que os COMBINA a 4x a escala?

É Zero-Shot de topologia, e não de dimensão do enxame (a bateria N∈{10,20,50,100}
que já existe em `eval_scalability.py`). Só é possível porque a observação tem a
mesma dimensão em todos os cenários (16+(N-1)*5 = 111 com N=20): os `.pth`/`.zip`
existentes carregam sem alteração nenhuma.

⚠️ Isto NÃO substitui a fase F2 (treino nativo). É a fase F1 do
`docs/PRE_REGISTO_MAPA_GRANDE.md`: barata (horas, não dias), corre localmente e a
sua leitura não depende do treino nativo. O contraste F1 vs F2 é, em si, um
resultado — e é reportado mesmo que dê 0 em todas as células.

⚠️ UM ZERO TEM QUATRO CAUSAS POSSÍVEIS, e três delas não são a que o F1 mede.
Por isso a corrida tem condições de CONTROLO — cada uma desliga uma causa,
mantendo tudo o resto igual:

  (1) TOPOLOGIA composta a 4x a escala — o que o F1 existe para medir.
  (2) ESCALA das distâncias: são normalizadas pelo raio da arena, e o mapa corre
      a r=60 contra r=15 do treino, logo o modelo vê tudo comprimido 4x (÷120 em
      vez de ÷30).                              -> `--norm-obs treino`
  (3) OBSTÁCULOS: dos 8 cenários só o Sandbox e o mapa_grande têm obstáculos
      dispersos; os 5 labirintos têm ZERO. O campeão do Gargalo nunca viu um
      obstáculo na vida e no mapa encontra 106. -> `--controlo sem_obstaculos`
  (4) FEATURES DA PORTA (obs[12:16]): identicamente 0 no treino de quem não tem
      porta, vivas no mapa_grande (que tem). São 4 entradas mortas que passam a
      carregar sinal.                           -> `--controlo sem_porta_obs`

(3) e (4) foram acrescentadas a 25 jul 2026, depois de medir que só o Sandbox
treinou com obstáculos — e é o único campeão que recolhe alguma coisa no mapa.
A leitura de cada condição está pré-comprometida no pré-registo (secção 3).

Uso:
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 5   # rápido
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 20  # oficial
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --origens u_wall four_rooms
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --norm-obs treino
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --controlo sem_obstaculos
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --controlo sem_porta_obs

Retomável: se a corrida for interrompida (o PC desligou-se), basta repetir o mesmo
comando — as células já completas são saltadas. As condições convivem no mesmo
ficheiro (é esse o objetivo: compará-las), identificadas pelas colunas NormObs e
Controlo. Um CSV de outro ambiente (o mapa mudou entretanto) não é reutilizado nem
apagado: vai para `*_ANTIGO.csv`.

Saída: results/evaluation/zeroshot_<mapa>.csv  (1 linha por episódio)
"""
import argparse
import copy
import hashlib
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

try:
    # line_buffering: esta corrida leva horas e costuma ir para um ficheiro
    # (`> log 2>&1`). Sem isto o stdout fica em buffer de 8 kB e o log aparece
    # VAZIO durante quase todo o tempo — impossível saber se está a progredir ou
    # pendurado, que é precisamente o que se quer saber num job destes.
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import THESIS_SCENARIOS, SCENARIO_LABELS_SHORT, scenario_suffix

EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")

# Condições de controlo (ver o cabeçalho). "base" = o mapa como ele é.
CONTROLOS = ("base", "sem_obstaculos", "sem_porta_obs")

# Campeão de cada cenário de origem, por algoritmo (a convenção de nomes do projeto).
_CAMPEAO = {
    "gnn": ("models", "gnn_3d_best{suf}.pth"),
    "ppo": ("models_ppo", "ppo_3d_final{suf}.zip"),
    "sac": ("models_sac", "sac_3d_final{suf}.zip"),
}


def _caminho_campeao(algo, origem):
    sub, padrao = _CAMPEAO[algo]
    fp = os.path.join(PROJECT_ROOT, "results", sub,
                      padrao.format(suf=scenario_suffix(origem)))
    return fp if os.path.exists(fp) else None


def _impressao_digital(cfg, mapa):
    """Impressão digital do ambiente FÍSICO: geometria + o que muda o episódio.

    Vai para uma coluna do CSV. Sem isto, retomar uma corrida DEPOIS de mexer no
    mapa juntava, no mesmo ficheiro, células de dois ambientes diferentes — e a
    comparação entre origens deixava de ser emparelhada sem dar sinal nenhum.

    O normalizador da observação NÃO entra aqui de propósito: não muda o mundo,
    só o que o modelo lê dele. Fica na coluna NormObs, para as duas condições
    poderem viver no mesmo ficheiro.
    """
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    e = SwarmForagingEnv3D(config=copy.deepcopy(cfg))
    e.reset(seed=0)
    partes = [
        "|".join("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (*w["pos"], *w["size"])
                 for w in e.walls),
        "obst=%d" % len(e.obstacles),
        "ninho=%.4f,%.4f" % (e.nest_pos[0], e.nest_pos[1]),
        "N=%d steps=%d arena=%.1f req=%d" % (
            e.num_agents, e.max_steps, e.arena_radius, e.required_to_eat),
    ]
    return hashlib.sha1("¬".join(partes).encode("utf-8")).hexdigest()[:12]


def _carregar_parciais(dest, digitais, norm_obs, controlo, episodes):
    """Lê o CSV de uma corrida interrompida e devolve (linhas, células feitas).

    A condição é o PAR (NormObs, Controlo) — as várias condições convivem no
    mesmo ficheiro (é esse o objetivo: compará-las), por isso as linhas das
    OUTRAS preservam-se tal como estão.

    O que não se mistura é ambiente. Cada condição tem a sua impressão digital
    esperada (`digitais`): a de `sem_obstaculos` é legitimamente diferente da
    base — muda o mundo de propósito — e comparar cada linha com a digital da
    SUA condição é o que distingue "controlo" de "o mapa mudou". Basta uma
    linha fora do sítio para o ficheiro inteiro ir para `*_ANTIGO.csv` (nunca
    apagado, nunca escrito por cima)."""
    if not os.path.exists(dest):
        return [], set()
    velho = pd.read_csv(dest)

    def _arquivar(porque):
        bak = dest.replace(".csv", "_ANTIGO.csv")
        os.replace(dest, bak)
        print("[!] %s\n    O CSV que lá estava foi guardado em %s; a começar do zero."
              % (porque, os.path.relpath(bak, PROJECT_ROOT)))
        return [], set()

    if "env_hash" not in velho.columns or "NormObs" not in velho.columns:
        return _arquivar("CSV de uma versão anterior do script (sem env_hash).")
    if "Controlo" not in velho.columns:
        # CSVs escritos antes de 25 jul: só existia a condição natural do mapa.
        # Preencher em vez de arquivar — senão a primeira corrida de controlo
        # mandava fora dias de avaliação que continuam perfeitamente válidos.
        velho["Controlo"] = "base"
        print("[=] CSV anterior aos controlos: %d episódios marcados como 'base'."
              % len(velho))

    fora = [(c, h) for c, h in zip(velho["Controlo"], velho["env_hash"])
            if digitais.get(c) != h]
    if fora:
        return _arquivar("O mapa mudou desde essa corrida (env_hash diferente em "
                         "%d episódios, ex.: condição '%s')." % (len(fora), fora[0][0]))

    def _e_desta(n, c):
        return n == norm_obs and c == controlo

    desta = velho[[_e_desta(n, c) for n, c in zip(velho["NormObs"], velho["Controlo"])]]
    feitas = {(a, o) for (a, o), g in desta.groupby(["Algorithm", "Origem"])
              if len(g) >= episodes} if not desta.empty else set()
    # Descarta células a meio: um bloco incompleto não é comparável com os outros.
    incompletas = [(a, o) for a, o in zip(desta["Algorithm"], desta["Origem"])
                   if (a, o) not in feitas]
    manter = velho[[(not _e_desta(n, c)) or ((a, o) in feitas) for n, c, a, o
                    in zip(velho["NormObs"], velho["Controlo"],
                           velho["Algorithm"], velho["Origem"])]]
    if feitas:
        print("[=] Retomada: %d células já completas nesta condição — a saltar."
              % len(feitas))
    if incompletas:
        print("[=] %d episódios de células incompletas descartados (voltam a correr)."
              % len(incompletas))
    outras = sum(1 for n, c in zip(manter["NormObs"], manter["Controlo"])
                 if not _e_desta(n, c))
    if outras:
        print("[=] %d episódios de outras condições preservados." % outras)
    return ([manter] if not manter.empty else []), feitas


def _pid_vivo(pid):
    """O processo ainda existe? Sem dependências novas (não há psutil no venv).

    Serve para distinguir um lock ORFÃO (a corrida morreu — PC suspendeu, um
    instalador pediu o fecho das aplicações, Ctrl+C) de uma corrida mesmo viva.
    Sem isto, um lock órfão obrigava a apagar ficheiros à mão para retomar, que
    é precisamente o tipo de passo manual em que se acaba a usar --forçar por
    hábito e a apagar dados a sério."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return bool(ok) and code.value == 259     # STILL_ACTIVE


class _CorridaUnica:
    """Impede duas corridas em simultâneo sobre o mesmo CSV — e deixa rasto.

    Cada corrida mantém as suas linhas EM MEMÓRIA e reescreve o ficheiro inteiro
    a cada célula. Duas ao mesmo tempo não se corrompem uma à outra: a última a
    gravar simplesmente apaga as células da outra, sem erro nenhum — e só se dá
    por isso ao contar as células no fim (ou nem isso).

    Duas defesas, porque nenhuma chega sozinha:
      · ficheiro .lock com o PID, validado com _pid_vivo (lock órfão é assumido
        sem perguntar; corrida viva aborta);
      · mtime do CSV — apanha corridas lançadas por versões anteriores a isto,
        que não escrevem lock nenhum.

    E um DIÁRIO (`*_progresso.log`), escrito pela própria corrida com flush a
    cada linha. O log do shell (`> ficheiro`) ficou a 0 bytes durante as 3h da
    corrida de 25 jul, que entretanto morreu sem deixar rasto: só ao contar as
    linhas do CSV se percebeu. O ficheiro do shell depende de como foi lançada;
    este não."""

    JANELA_MIN = 25

    def __init__(self, dest, etiqueta, ignorar=False):
        self.lock = dest.replace(".csv", ".lock")
        self.diario = dest.replace(".csv", "_progresso.log")
        self.dest = dest
        self.etiqueta = etiqueta
        self.ignorar = ignorar

    def _dono(self):
        """(pid, texto) do lock existente, ou (None, texto)."""
        try:
            with open(self.lock, encoding="utf-8") as f:
                texto = f.read().strip()
        except OSError:
            return None, ""
        for parte in texto.split():
            if parte.startswith("pid="):
                try:
                    return int(parte[4:]), texto
                except ValueError:
                    break
        return None, texto

    def _acabou_em_paz(self):
        """A última corrida registada no diário fechou-se a si própria?

        Distingue "acabou agora mesmo" de "está a correr". Sem isto, encadear
        uma condição a seguir à outra era impossível: mal a primeira fecha, o
        CSV tem minutos de idade e a guarda de mtime abaixo abortava a segunda
        — e a saída fácil seria passar --ignorar-corrida-ativa sempre, que é
        como se perde uma guarda a sério."""
        try:
            with open(self.diario, encoding="utf-8") as f:
                linhas = [l for l in f.read().splitlines() if l.strip()]
        except OSError:
            return False
        return bool(linhas) and ("FIM" in linhas[-1] or "MORREU" in linhas[-1])

    def __enter__(self):
        if not self.ignorar and os.path.exists(self.lock):
            pid, texto = self._dono()
            if pid is not None and _pid_vivo(pid):
                raise SystemExit(
                    f"[X] Já há uma corrida VIVA a escrever este CSV:\n      {texto}\n"
                    f"    Duas corridas apagam células uma à outra. Espera pelo fim\n"
                    f"    (ou pára o pid {pid}) — o trabalho já feito não se perde: a\n"
                    f"    corrida seguinte retoma as células que faltam.")
            print(f"[=] Lock órfão de uma corrida que morreu ({texto}) — a assumir.")
        if (not self.ignorar and not os.path.exists(self.lock)
                and os.path.exists(self.dest) and not self._acabou_em_paz()):
            idade = (time.time() - os.path.getmtime(self.dest)) / 60
            if idade < self.JANELA_MIN:
                raise SystemExit(
                    f"[X] O CSV foi escrito há {idade:.0f} min, não há lock e o diário não\n"
                    f"    fecha com FIM — é capaz de estar a correr uma versão anterior\n"
                    f"    deste script (uma célula demora ~20 min), e duas corridas apagam\n"
                    f"    células uma à outra. Confirma com Get-Process python; se não\n"
                    f"    houver nenhuma, usa --ignorar-corrida-ativa.")
        self.registar(f"ARRANQUE {self.etiqueta}")
        return self

    def registar(self, msg):
        """Uma linha no diário + o estado atual no lock (com flush)."""
        carimbo = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.lock, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} {self.etiqueta} ultimo={carimbo} :: {msg}\n")
        with open(self.diario, "a", encoding="utf-8") as f:
            f.write(f"{carimbo}  pid={os.getpid()}  {self.etiqueta}  {msg}\n")

    def __exit__(self, exc_type, *_):
        self.registar("FIM" if exc_type is None else f"MORREU ({exc_type.__name__})")
        try:
            os.remove(self.lock)
        except OSError:
            pass
        return False


def _aplicar_controlo(cfg, controlo, mapa):
    """Liga no config a condição de controlo pedida. 'base' não toca em nada.

    Ambas as chaves são no-op por omissão no ambiente, e ambas só existem para
    o zero-shot: nenhuma campanha de treino as deve usar."""
    if controlo == "base":
        return cfg
    if controlo == "sem_obstaculos":
        if mapa != "mapa_grande":
            raise SystemExit("[X] --controlo sem_obstaculos só está definido para "
                             "o mapa_grande (é a chave num_obstacles_mapa_grande).")
        cfg["environment"]["num_obstacles_mapa_grande"] = 0
    elif controlo == "sem_porta_obs":
        cfg["environment"]["obs_zero_door_feats"] = True
    else:
        raise ValueError("--controlo tem de ser um de %s" % (CONTROLOS,))
    return cfg


def avaliar(mapa="mapa_grande", origens=None, algos=None, episodes=20,
            seed_base=1000, norm_obs="mapa", refazer=False, controlo="base",
            ignorar_corrida_ativa=False):
    from scripts.eval_all import eval_algo

    origens = origens or THESIS_SCENARIOS
    algos = algos or ["gnn", "ppo", "sac"]
    if controlo not in CONTROLOS:
        raise SystemExit("[X] --controlo tem de ser um de %s" % (CONTROLOS,))

    # Config temporário com o cenário-alvo — o eval_algo lê o classic_scenario
    # do config, e não queremos tocar no configs/foraging.yaml do repositório.
    with open(os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg = copy.deepcopy(cfg)
    cfg["environment"]["classic_scenario"] = mapa

    # ── Normalizador das distâncias na observação ────────────────────────────
    # 'mapa'  : o do próprio mapa (r=60 -> ÷120). É a condição natural.
    # 'treino': o dos 7 cenários (r=15 -> ÷30). CONTROLO — ver o pré-registo.
    # Sem o par, um zero decorre de duas causas que não se distinguem:
    # topologia nova OU todas as distâncias comprimidas 4x à entrada do modelo.
    if norm_obs == "treino":
        cfg["environment"]["obs_norm_radius"] = float(
            cfg["environment"].get("arena_radius", 15.0))
    elif norm_obs != "mapa":
        raise ValueError("--norm-obs tem de ser 'mapa' ou 'treino'")

    # Guarda: os campeões só carregam se obs_dim bater certo (16+(N-1)*5).
    n_ag = cfg["environment"].get("num_agents")
    if n_ag != 20:
        raise SystemExit(
            f"[X] num_agents={n_ag} no configs/foraging.yaml. Os campeões dos 7 "
            f"cenários foram treinados com 20 (obs_dim=111) e com {n_ag} a "
            f"observação passa a {16 + (n_ag - 1) * 5} dims. Corrige o config "
            f"antes de correr o zero-shot.")

    # Guardar o config ANTES do controlo: as digitais das outras condições têm
    # de sair daqui, senão a de 'base' era calculada já com o controlo aplicado
    # (e o ficheiro inteiro ia para _ANTIGO na primeira retoma).
    cfg_neutro = copy.deepcopy(cfg)
    _aplicar_controlo(cfg, controlo, mapa)

    os.makedirs(EVAL_DIR, exist_ok=True)
    # Um config temporário POR CONDIÇÃO. Com um nome só, lançar o controlo com a
    # corrida base ainda a andar trocava-lhe o ambiente a meio: o eval_algo relê
    # este ficheiro a cada célula, por isso a base passaria a avaliar o controlo
    # e a gravá-lo com a etiqueta 'base' — sem erro nenhum, como o set_scenario
    # que engolia exceções.
    tmp_cfg = os.path.join(EVAL_DIR, f"_cfg_zeroshot_{mapa}_{norm_obs}_{controlo}.yaml")
    with open(tmp_cfg, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    dest = os.path.join(EVAL_DIR, f"zeroshot_{mapa}.csv")
    # A digital de CADA condição, para o _carregar_parciais poder distinguir
    # "isto é o controlo, que muda o mundo de propósito" de "o mapa mudou".
    digitais = {c: _impressao_digital(
        _aplicar_controlo(copy.deepcopy(cfg_neutro), c, mapa), mapa)
        for c in CONTROLOS}
    digital = digitais[controlo]
    print(f"[i] ambiente {digital} | controlo: {controlo} | normalizador da obs: "
          f"{norm_obs} (÷{2 * (cfg['environment'].get('obs_norm_radius') or 60.0):.0f})")

    def _gravar():
        todo = pd.concat(linhas, ignore_index=True)
        todo.to_csv(dest, index=False)
        return todo

    sem_campeao = []
    etiqueta = f"mapa={mapa} norm={norm_obs} controlo={controlo}"
    with _CorridaUnica(dest, etiqueta, ignorar=ignorar_corrida_ativa) as corrida:
        if refazer and os.path.exists(dest):
            os.replace(dest, dest.replace(".csv", "_ANTIGO.csv"))
            linhas, feitas = [], set()
        else:
            linhas, feitas = _carregar_parciais(dest, digitais, norm_obs,
                                                controlo, episodes)

        for algo in algos:
            for origem in origens:
                if (algo.upper(), origem) in feitas:
                    continue
                fp = _caminho_campeao(algo, origem)
                if fp is None:
                    print(f"[--] {algo.upper():4s} treinado em {origem}: sem campeão — saltar")
                    sem_campeao.append((algo.upper(), origem))
                    continue
                print(f"\n[>>] {algo.upper()} treinado em '{origem}' -> avaliado em '{mapa}'")
                corrida.registar(f"a correr {algo.upper()} x {origem}")
                df, _ = eval_algo(algo, mapa, tmp_cfg, episodes,
                                  seed_base=seed_base, model_path=fp)
                if df is None or df.empty:
                    corrida.registar(f"SEM DADOS {algo.upper()} x {origem}")
                    continue
                df = df.copy()
                df["Algorithm"] = algo.upper()
                df["Origem"] = origem
                df["Mapa"] = mapa
                df["NormObs"] = norm_obs
                df["Controlo"] = controlo
                df["env_hash"] = digital
                linhas.append(df)
                # Gravar a CADA célula, não só no fim: uma corrida destas leva
                # horas e se for interrompida a meio (PC desligado, Ctrl+C) o que
                # já custou fica no disco — e a corrida seguinte RETOMA daqui (as
                # células completas são saltadas), em vez de escrever por cima.
                total = len(_gravar())
                print(f"     [gravado: {total} episódios acumulados]")
                corrida.registar(
                    f"FEITA {algo.upper()} x {origem}: {df['food_collected'].mean():.1f} "
                    f"recolhas/ep, {100 * df['success'].mean():.0f}% sucesso "
                    f"({total} episódios no ficheiro)")

    if not linhas:
        print("\n[!] Nenhuma célula avaliada — não há campeões nos caminhos esperados.")
        return pd.DataFrame()

    out = _gravar()
    print(f"\n[OK] {len(out)} episódios -> {os.path.relpath(dest, PROJECT_ROOT)}")

    # Resumo desta condição (descritivo — a inferência faz-se no pré-registo)
    desta = out[(out["NormObs"] == norm_obs) & (out["Controlo"] == controlo)]
    print(f"\nRECOLHAS/EP (média ± dp) [taxa de sucesso] — norm={norm_obs} "
          f"controlo={controlo}")
    print("-" * 62)
    for algo in desta["Algorithm"].unique():
        sub = desta[desta["Algorithm"] == algo]
        for origem in sub["Origem"].unique():
            c = sub[sub["Origem"] == origem]
            print("%-5s treinado em %-24s %5.1f ± %4.1f  [%3.0f%%]" % (
                algo, SCENARIO_LABELS_SHORT.get(origem, origem),
                c["food_collected"].mean(), c["food_collected"].std(ddof=0),
                100 * c["success"].mean()))

    # Um buraco na grelha é um resultado que não existe — e um "sem campeão"
    # perdido a meio de horas de log passa despercebido. Repetir no fim.
    if sem_campeao:
        print(f"\n[!] {len(sem_campeao)} células NÃO avaliadas por falta de "
              f"campeão no disco (a grelha fica incompleta):")
        for algo, origem in sem_campeao:
            sub, padrao = _CAMPEAO[algo.lower()]
            print(f"      {algo:4s} x {origem:26s} falta results/{sub}/"
                  f"{padrao.format(suf=scenario_suffix(origem))}")

    # Mapa do que já existe no ficheiro, por condição — para saber o que falta
    # correr sem ter de abrir o CSV.
    print("\nCÉLULAS POR CONDIÇÃO (n = episódios)")
    for (n_obs, ctrl), g in out.groupby(["NormObs", "Controlo"]):
        cel = g.groupby(["Algorithm", "Origem"]).size()
        print(f"  norm={n_obs:6s} controlo={ctrl:14s} {len(cel):2d} células, "
              f"{len(g):3d} episódios")
    try:
        os.remove(tmp_cfg)
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapa", default="mapa_grande")
    ap.add_argument("--origens", nargs="*", default=None,
                    help="cenários de origem dos campeões (por omissão: os 7 da tese)")
    ap.add_argument("--algos", nargs="*", default=None)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--norm-obs", choices=["mapa", "treino"], default="mapa",
                    help="normalizador das distâncias na observação: 'mapa' (r=60, "
                         "natural) ou 'treino' (r=15, condição de CONTROLO)")
    ap.add_argument("--controlo", choices=list(CONTROLOS), default="base",
                    help="condição de controlo: 'base' (o mapa como é), "
                         "'sem_obstaculos' (0 obstáculos — os labirintos de treino "
                         "também não tinham nenhum) ou 'sem_porta_obs' (as 4 "
                         "features da porta a zero, como no treino sem porta)")
    ap.add_argument("--refazer", action="store_true",
                    help="ignora o CSV existente e recomeça (guarda-o em _ANTIGO)")
    ap.add_argument("--ignorar-corrida-ativa", action="store_true",
                    help="salta a guarda que impede duas corridas em simultâneo "
                         "sobre o mesmo CSV (só se souberes que não há nenhuma)")
    a = ap.parse_args()
    avaliar(a.mapa, a.origens, a.algos, a.episodes, a.seed_base,
            norm_obs=a.norm_obs, refazer=a.refazer, controlo=a.controlo,
            ignorar_corrida_ativa=a.ignorar_corrida_ativa)


if __name__ == "__main__":
    main()
