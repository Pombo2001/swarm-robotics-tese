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

⚠️ QUAL CAMPANHA ESTÁS A AVALIAR? A corrida de 25 jul 2026 (18 células, 6 h)
teve de ser DEITADA FORA por causa disto: o script carregava o que estivesse no
caminho esperado e não tinha opinião nenhuma sobre a data. Os `results/models*`
daquele PC eram de 24 jun — campeões de ANTES da fitness de homing, que dão 0,0
no seu próprio cenário — enquanto a tese reporta a campanha de 2-9 jul. A linha
do GNN não media transferência nenhuma: media modelos já partidos.

Duas defesas, desde a noite de 25 jul:
  · `--models-dir` — a raiz dos modelos deixa de ser `results/` em duro, para os
    campeões de uma campanha poderem viver numa pasta ISOLADA (nunca por cima
    dos `results/models*` ativos, que um treino a andar reescreve — armadilha
    nº9). Ex.: `--models-dir results/models_7d`.
  · guarda de data — a data de cada campeão (sidecar `.meta.json` se existir,
    senão o mtime do ficheiro) é VERIFICADA contra a janela da campanha de
    referência ANTES de correr a primeira célula, e vai para o CSV nas colunas
    `ModeloPath` / `ModeloData` / `ModeloFonte`. Um modelo anterior à campanha
    aborta a corrida; um posterior é avisado com estrondo (pode ser legítimo se
    a campanha foi repetida — mas é também exatamente o aspeto de apontar sem
    querer para um mega-treino a decorrer).

Uso:
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 5   # rápido
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --episodes 20  # oficial
    .venv/Scripts/python.exe scripts/eval_zeroshot_mapa.py --models-dir results/models_7d
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
import json
import os
import sys
import time
from datetime import datetime

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

# Raiz onde vivem os `models/`, `models_ppo/`, `models_sac/`. Por omissão a do
# repositório — mas os campeões de uma campanha arquivada devem ser extraídos
# para uma pasta própria e passados em `--models-dir`.
MODELS_DIR_OMISSAO = "results"

# Janela da campanha de referência: o mega-treino de 7 dias de 2-9 jul 2026, que
# é a campanha que a TESE reporta. Um campeão anterior a isto é de outra era do
# projeto (antes da fitness de homing) e não responde à pergunta do F1.
# Datas, não versões, porque é a única marca que os `.zip` do PPO/SAC têm.
CAMPANHA_INICIO = "2026-07-02"
CAMPANHA_FIM = "2026-07-10"


def _caminho_campeao(algo, origem, raiz=None):
    sub, padrao = _CAMPEAO[algo]
    raiz = raiz or os.path.join(PROJECT_ROOT, MODELS_DIR_OMISSAO)
    fp = os.path.join(raiz, sub, padrao.format(suf=scenario_suffix(origem)))
    return fp if os.path.exists(fp) else None


def _data_modelo(fp):
    """(datetime, fonte) de quando o modelo foi gravado. Nunca levanta.

    Duas fontes, por esta ordem:
      · `meta` — o sidecar `.meta.json` que o evo_trainer escreve ao lado do
        campeão (`saved_at`). É a fonte fiável: viaja com o ficheiro e diz
        quando o TREINO o gravou.
      · `mtime` — a data do ficheiro. É o que resta para os `.zip` do PPO/SAC,
        que não têm sidecar nenhum. Cuidado: uma cópia que não preserve
        timestamps (pscp sem `-p`, arrastar no explorador) carimba os ficheiros
        com a data de HOJE e a guarda deixa passar tudo. Extrair de `.tar.gz`
        preserva; é essa a via recomendada para trazer campeões do servidor.
    """
    meta = os.path.splitext(fp)[0] + ".meta.json"
    if os.path.exists(meta):
        try:
            with open(meta, encoding="utf-8") as f:
                quando = json.load(f).get("saved_at")
            if quando:
                return datetime.fromisoformat(quando), "meta"
        except (OSError, ValueError, json.JSONDecodeError):
            pass  # sidecar ilegível: cai para o mtime, que existe sempre
    return datetime.fromtimestamp(os.path.getmtime(fp)), "mtime"


def _inventario(algos, origens, raiz):
    """{(ALGO, origem): (caminho, datetime, fonte)} + as células sem campeão.

    Feito de UMA VEZ antes de avaliar seja o que for: é o que permite abortar
    por data ao segundo zero e não à sexta hora."""
    inv, em_falta = {}, []
    for algo in algos:
        for origem in origens:
            fp = _caminho_campeao(algo, origem, raiz)
            if fp is None:
                em_falta.append((algo.upper(), origem))
                continue
            quando, fonte = _data_modelo(fp)
            inv[(algo.upper(), origem)] = (fp, quando, fonte)
    return inv, em_falta


def _verificar_campanha(inv, inicio, fim):
    """Aborta se algum campeão for anterior à campanha de referência.

    É a guarda que faltava a 25 jul: 6 h de avaliação e 18 células gastas em
    modelos de 24 jun, três semanas anteriores à campanha que a tese reporta.
    O sintoma nos dados era mudo — zeros, que é exatamente o que o F1 procura.

    Anterior ao início da janela é ERRO (o modelo é de outra era do projeto).
    Posterior ao fim é AVISO com estrondo, não erro: pode ser uma campanha
    repetida de propósito, mas tem o aspeto exato de apontar sem querer para os
    `results/models*` de um treino a decorrer (armadilha nº9)."""
    if not inv:
        return
    d0 = datetime.fromisoformat(inicio) if inicio else None
    d1 = datetime.fromisoformat(fim) if fim else None

    def _linha(cel):
        fp, quando, fonte = inv[cel]
        return "      %-4s x %-26s %s  (%s)  %s" % (
            cel[0], cel[1], quando.strftime("%Y-%m-%d %H:%M"), fonte,
            os.path.relpath(fp, PROJECT_ROOT))

    velhos = [c for c in inv if d0 and inv[c][1] < d0]
    if velhos:
        raise SystemExit(
            "[X] %d campeões são ANTERIORES à campanha de referência (%s).\n"
            "%s\n"
            "    Foi assim que o F1 de 25 jul se perdeu: modelos de outra era do\n"
            "    projeto, que dão 0,0 até no cenário deles, avaliados como se\n"
            "    fossem os da tese. Aponta --models-dir à pasta da campanha certa\n"
            "    (ex.: results/models_7d, extraída de ~/eval7d.tar.gz) ou ajusta\n"
            "    --campanha-inicio se a referência mudou de propósito."
            % (len(velhos), inicio,
               "\n".join(_linha(c) for c in sorted(velhos))))

    novos = [c for c in inv if d1 and inv[c][1] > d1]
    if novos:
        print("[!!] %d campeões são POSTERIORES à janela da campanha (%s).\n%s\n"
              "     Se isto não era de propósito, é a armadilha nº9: estás a ler\n"
              "     modelos de um treino que está a reescrever a pasta AGORA.\n"
              "     A corrida continua — a data de cada modelo fica no CSV."
              % (len(novos), fim, "\n".join(_linha(c) for c in sorted(novos))))

    por_mtime = [c for c in inv if inv[c][2] == "mtime"]
    if por_mtime:
        print("[i] %d de %d campeões sem sidecar .meta.json — a data vem do mtime "
              "do ficheiro.\n    Uma cópia que não preserve timestamps engana esta "
              "guarda (usa .tar.gz)." % (len(por_mtime), len(inv)))


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


def _carregar_parciais(dest, digitais, norm_obs, controlo, episodes, esperado):
    """Lê o CSV de uma corrida interrompida e devolve (linhas, células feitas).

    A condição é o PAR (NormObs, Controlo) — as várias condições convivem no
    mesmo ficheiro (é esse o objetivo: compará-las), por isso as linhas das
    OUTRAS preservam-se tal como estão.

    O que não se mistura é ambiente. Cada condição tem a sua impressão digital
    esperada (`digitais`): a de `sem_obstaculos` é legitimamente diferente da
    base — muda o mundo de propósito — e comparar cada linha com a digital da
    SUA condição é o que distingue "controlo" de "o mapa mudou". Basta uma
    linha fora do sítio para o ficheiro inteiro ir para `*_ANTIGO.csv` (nunca
    apagado, nunca escrito por cima).

    Nem MODELO: uma célula só conta como feita se tiver sido avaliada com o
    campeão que está agora no `--models-dir`, com a mesma data (`esperado`).
    Sem isto, repetir o F1 com os modelos certos deixava lá dentro, dadas como
    feitas, as células da corrida com os modelos errados."""
    if not os.path.exists(dest):
        return [], set()
    velho = pd.read_csv(dest)

    def _arquivar(porque):
        # Nunca escrever por cima de um _ANTIGO que já exista: senão a segunda
        # vez que isto acontece apaga em silêncio o arquivo da primeira (e é
        # justamente aí que estão os dados que se quer poder reexaminar).
        bak = dest.replace(".csv", "_ANTIGO.csv")
        if os.path.exists(bak):
            bak = dest.replace(".csv", time.strftime("_ANTIGO_%Y%m%d_%H%M%S.csv"))
        os.replace(dest, bak)
        print("[!] %s\n    O CSV que lá estava foi guardado em %s; a começar do zero."
              % (porque, os.path.relpath(bak, PROJECT_ROOT)))
        return [], set()

    if "env_hash" not in velho.columns or "NormObs" not in velho.columns:
        return _arquivar("CSV de uma versão anterior do script (sem env_hash).")
    if "ModeloData" not in velho.columns or "ModeloPath" not in velho.columns:
        # CSVs anteriores a esta guarda: não registam QUE modelo avaliaram, e o único
        # que existe nesse estado é o do F1 de 25 jul — corrido com os campeões
        # de 24 jun. Não há como validar linha a linha o que não foi gravado.
        return _arquivar("CSV sem ModeloPath/ModeloData: não se sabe que modelos "
                         "foram avaliados (anterior à guarda de campanha).")
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

    def _modelo_bate(cel, g):
        """Todos os episódios desta célula foram corridos com o campeão de agora?"""
        esp = esperado.get(cel)
        if esp is None:                       # o campeão desapareceu do disco
            return False
        return (set(g["ModeloPath"].astype(str)) == {esp[0]}
                and set(g["ModeloData"].astype(str)) == {esp[1]})

    feitas, trocadas = set(), []
    if not desta.empty:
        for cel, g in desta.groupby(["Algorithm", "Origem"]):
            if len(g) < episodes:
                continue
            (feitas.add(cel) if _modelo_bate(cel, g) else trocadas.append(cel))
    # Descarta células a meio: um bloco incompleto não é comparável com os outros.
    incompletas = [(a, o) for a, o in zip(desta["Algorithm"], desta["Origem"])
                   if (a, o) not in feitas]
    manter = velho[[(not _e_desta(n, c)) or ((a, o) in feitas) for n, c, a, o
                    in zip(velho["NormObs"], velho["Controlo"],
                           velho["Algorithm"], velho["Origem"])]]
    if feitas:
        print("[=] Retomada: %d células já completas nesta condição — a saltar."
              % len(feitas))
    if trocadas:
        eps_troc = sum(1 for a, o in zip(desta["Algorithm"], desta["Origem"])
                       if (a, o) in set(trocadas))
        print("[!] %d células completas foram avaliadas com OUTRO modelo (ou outra "
              "data)\n    e voltam a correr — %d episódios descartados: %s"
              % (len(trocadas), eps_troc,
                 ", ".join("%s x %s" % c for c in sorted(trocadas))))
        incompletas = [c for c in incompletas if c not in set(trocadas)]
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
            ignorar_corrida_ativa=False, models_dir=None,
            campanha_inicio=CAMPANHA_INICIO, campanha_fim=CAMPANHA_FIM):
    from scripts.eval_all import eval_algo

    origens = origens or THESIS_SCENARIOS
    algos = algos or ["gnn", "ppo", "sac"]
    if controlo not in CONTROLOS:
        raise SystemExit("[X] --controlo tem de ser um de %s" % (CONTROLOS,))

    # ── Que modelos, de que campanha ─────────────────────────────────────────
    # Antes de tudo o resto: o inventário completo dos campeões, com data, e a
    # guarda de campanha. Uma corrida destas leva horas e falha em SILÊNCIO
    # quando os modelos estão errados (dá zeros, que é um resultado possível) —
    # por isso o momento de rebentar é aqui, não a meio.
    raiz = os.path.abspath(os.path.join(PROJECT_ROOT,
                                        models_dir or MODELS_DIR_OMISSAO))
    if not os.path.isdir(raiz):
        raise SystemExit("[X] --models-dir não existe: %s" % raiz)
    inventario, em_falta = _inventario(algos, origens, raiz)
    print("[i] modelos: %s" % os.path.relpath(raiz, PROJECT_ROOT))
    _verificar_campanha(inventario, campanha_inicio, campanha_fim)
    if inventario:
        datas = sorted(v[1] for v in inventario.values())
        print("[i] %d campeões, gravados entre %s e %s"
              % (len(inventario), datas[0].strftime("%Y-%m-%d"),
                 datas[-1].strftime("%Y-%m-%d")))

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

    # O que se espera encontrar no CSV para uma célula já feita: o caminho do
    # campeão (relativo à raiz do projeto, para o ficheiro não depender de onde
    # a pasta está montada) e a data desse modelo.
    esperado = {cel: (os.path.relpath(fp, PROJECT_ROOT).replace("\\", "/"),
                      quando.isoformat(timespec="seconds"))
                for cel, (fp, quando, _f) in inventario.items()}

    etiqueta = (f"mapa={mapa} norm={norm_obs} controlo={controlo} "
                f"modelos={os.path.relpath(raiz, PROJECT_ROOT)}")
    with _CorridaUnica(dest, etiqueta, ignorar=ignorar_corrida_ativa) as corrida:
        if refazer and os.path.exists(dest):
            os.replace(dest, dest.replace(".csv", "_ANTIGO.csv"))
            linhas, feitas = [], set()
        else:
            linhas, feitas = _carregar_parciais(dest, digitais, norm_obs,
                                                controlo, episodes, esperado)

        for algo in algos:
            for origem in origens:
                cel = (algo.upper(), origem)
                if cel in feitas:
                    continue
                if cel not in inventario:
                    print(f"[--] {algo.upper():4s} treinado em {origem}: sem campeão — saltar")
                    continue
                fp, quando, fonte = inventario[cel]
                print(f"\n[>>] {algo.upper()} treinado em '{origem}' -> avaliado em "
                      f"'{mapa}'  [modelo de {quando:%Y-%m-%d}, {fonte}]")
                corrida.registar(f"a correr {algo.upper()} x {origem} "
                                 f"(modelo de {quando:%Y-%m-%d})")
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
                # QUE modelo produziu esta linha. É o que faltava ao CSV de 25
                # jul: sem isto, um ficheiro de resultados não sabe dizer de que
                # campanha é — e a resposta só aparece por arqueologia de datas
                # de pastas, tarde de mais.
                df["ModeloPath"], df["ModeloData"] = esperado[cel]
                df["ModeloFonte"] = fonte
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
        print("\n[!] Nenhuma célula avaliada — não há campeões em %s "
              "(subpastas models/, models_ppo/, models_sac/)."
              % os.path.relpath(raiz, PROJECT_ROOT))
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
    if em_falta:
        print(f"\n[!] {len(em_falta)} células NÃO avaliadas por falta de "
              f"campeão no disco (a grelha fica incompleta):")
        for algo, origem in em_falta:
            sub, padrao = _CAMPEAO[algo.lower()]
            print(f"      {algo:4s} x {origem:26s} falta "
                  f"{os.path.relpath(raiz, PROJECT_ROOT)}/{sub}/"
                  f"{padrao.format(suf=scenario_suffix(origem))}")

    # De que campanha são estes resultados — a pergunta que o CSV de 25 jul não
    # sabia responder. Fica no fim do log, junto dos números.
    print("\nMODELOS AVALIADOS (por data de gravação)")
    for cel in sorted(inventario):
        fp, quando, fonte = inventario[cel]
        print("  %-4s x %-26s %s  (%s)" % (
            cel[0], cel[1], quando.strftime("%Y-%m-%d %H:%M"), fonte))

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
    ap.add_argument("--models-dir", default=MODELS_DIR_OMISSAO,
                    help="raiz com models/, models_ppo/ e models_sac/ (por "
                         "omissão 'results'). Aponta-a à pasta ISOLADA da "
                         "campanha a avaliar, ex.: results/models_7d")
    ap.add_argument("--campanha-inicio", default=CAMPANHA_INICIO,
                    help="data mínima dos campeões (AAAA-MM-DD). Um modelo "
                         "anterior a isto ABORTA a corrida — foi assim que se "
                         "perderam as 6 h do F1 de 25 jul 2026")
    ap.add_argument("--campanha-fim", default=CAMPANHA_FIM,
                    help="fim da janela da campanha (AAAA-MM-DD). Modelos "
                         "posteriores são avisados, não abortam")
    ap.add_argument("--sem-guarda-data", action="store_true",
                    help="desliga a guarda de campanha por completo (as datas "
                         "continuam a ir para o CSV)")
    a = ap.parse_args()
    avaliar(a.mapa, a.origens, a.algos, a.episodes, a.seed_base,
            norm_obs=a.norm_obs, refazer=a.refazer, controlo=a.controlo,
            ignorar_corrida_ativa=a.ignorar_corrida_ativa,
            models_dir=a.models_dir,
            campanha_inicio=None if a.sem_guarda_data else a.campanha_inicio,
            campanha_fim=None if a.sem_guarda_data else a.campanha_fim)


if __name__ == "__main__":
    main()
