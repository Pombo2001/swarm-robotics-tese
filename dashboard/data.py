"""Leitura e agregação dos resultados (CSVs de avaliação) para a vista Ciência.

Fonte de verdade = results/evaluation/eval_summary.csv (1 linha por episódio).
Não treina nem avalia — só lê o que os scripts já produziram.
"""
import os
import re
import glob
import time
import shutil
import datetime

import pandas as pd

from . import config

GRAFICOS_DIR = os.path.join(config.BASE_DIR, "results", "graficos_tese")
TESE_IMG_DIR = os.path.join(config.BASE_DIR, "Tese", "images", "resultados")

EVAL_DIR = os.path.join(config.BASE_DIR, "results", "evaluation")
EVAL_SUMMARY = os.path.join(EVAL_DIR, "eval_summary.csv")
STATS_DIR = os.path.join(config.BASE_DIR, "results", "estatisticas")
SIGNIF = os.path.join(STATS_DIR, "testes_significancia_food_collected.csv")
MODEL_DIRS = ("models", "models_ppo", "models_sac")

# Campanha Novelty adaptativa (19 jul): 5 fases GUARDADAS FORA de graficos_tese, em
# results/novelty_adaptativo/, para não sobrescrever os modelos campeões 7d (que
# continuam a ser os ativos, de propósito). Cada fase é auto-contida (evaluation/ +
# models/), por isso não passa pelo list_sessions() normal — é enxertada à parte na
# comparação de métricas e na vista Ao vivo. Os rótulos dizem o que cada fase avaliou
# (ordem e semântica vêm do pré-registo docs/PRE_REGISTO_NOVELTY_ADAPTATIVO.md).
ADAPT_DIR = os.path.join(config.BASE_DIR, "results", "novelty_adaptativo")
ADAPT_FASES = [
    ("◆ Adaptativo · 7 cenários @195 (A1)",                       "week_A_fase1"),
    ("◆ Adaptativo · u_wall objetivo puro @390 (A2, controlo)",   "week_A_fase2"),
    ("◆ Adaptativo · coop/bypass/perceção @195 (B1)",             "week_B_fase1"),
    ("◆ Adaptativo · u_wall adaptativo @390 (B2)",                "week_B_fase2"),
    ("◆ Adaptativo · bypass adaptativo @390 (B3)",                "week_B_fase3"),
]
ADAPT_LABEL_TO_DIR = {lbl: sub for lbl, sub in ADAPT_FASES}


# Mega-treino de 1 mês (fechado a 3 ago): a vista lê o RESUMO, não os CSV. Os
# testes são do `scripts/analise_megatreino.py` — recalculá-los aqui era uma
# segunda implementação da mesma estatística, com o risco de dar outra resposta;
# e no Pi, que serve isto, seria lento sem necessidade.
MEGA_DIR = os.path.join(config.BASE_DIR, "results", "mega_1mes")
MEGA_RESUMO = os.path.join(MEGA_DIR, "resumo_megatreino.json")

# Fases do mega-treino com modelos próprios, para o visualizador. Os rótulos
# dizem a CONDIÇÃO, não o número da fase — "mega_A_fase1" não diz a ninguém que
# é o braço que resolve o Muro em U em 28 de 28 execuções.
#
# As três fases de GRADIENTE (A3 = PPO, A4 = SAC, B6 = SAC) não estão aqui: o
# arquivamento entre fases copia `results/models`, a pasta do GNN, e não os
# modelos do algoritmo que a fase treinou — as três ficaram com cópias de GNN de
# outras fases (mesmo sha256) e nenhum `.zip` próprio. As de A3/A4 foram
# removidas a 3 ago para não serem abertas por engano (LEIA-ME_modelos.md).
#
# Verificado a 3 ago, fase a fase: TODAS as fases GNN têm os modelos do seu
# próprio cenário, com um hash distinto por run (28/28, 21/21, 7/7) — a
# armadilha nº8 está limpa. Os resultados das fases de gradiente continuam
# válidos: vêm das avaliações, feitas no servidor com o modelo certo em memória.
MEGA_FASES = [
    ("▣ Mega-treino · GNN adaptativo · Muro em U (28/28)", "mega_A_fase1"),
    ("▣ Mega-treino · GNN objetivo · Muro em U (15/28)",   "mega_A_fase2"),
    ("▣ Mega-treino · GNN adaptativo · Sandbox",           "mega_A_fase5"),
    ("▣ Mega-treino · anneal sustain=5",                   "mega_B_fase1"),
    ("▣ Mega-treino · anneal sustain=20",                  "mega_B_fase2"),
    ("▣ Mega-treino · anneal decay=0,95",                  "mega_B_fase3"),
    ("▣ Mega-treino · anneal decay=0,995",                 "mega_B_fase4"),
    ("▣ Mega-treino · adaptativo · Porta c/ alternativa",  "mega_B_fase5"),
    ("▣ Mega-treino · adaptativo · Perceção coop.",        "mega_B_fase7"),
]


def megatreino():
    """Resumo do mega-treino, ou None se ainda não foi gerado.

    Regenerar com:  python scripts/analise_megatreino.py --json
    """
    if not os.path.exists(MEGA_RESUMO):
        return None
    try:
        import json
        with open(MEGA_RESUMO, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    return d if d.get("testes") else None


def _mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


def _aggregate_eval(path: str):
    """Agrega um eval_summary.csv por (cenário, algoritmo).

    Devolve {scenario: {algo: {"ptask": %, "recolhas": média, "n": episódios}}} ou None.
    """
    if not path or not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    # Quando o ficheiro tem a coluna Run, a unidade estatística é a EXECUÇÃO e
    # não o episódio: agrega-se primeiro dentro de cada run. Sem isto, uma
    # campanha de 7 execuções pesava igual a uma de 1 e a média deslizava para
    # quem tivesse mais episódios gravados.
    if "Run" in df.columns:
        por_run = (df.groupby(["Scenario", "Algorithm", "Run"])
                     .agg(ptask=("success", lambda s: 100.0 * s.mean()),
                          recolhas=("food_collected", "mean"),
                          n=("success", "size"))
                     .reset_index())
        agg = (por_run.groupby(["Scenario", "Algorithm"])
                      .agg(ptask=("ptask", "mean"), recolhas=("recolhas", "mean"),
                           n=("n", "sum"))
                      .reset_index())
    else:
        agg = df.groupby(["Scenario", "Algorithm"]).agg(
            ptask=("success", lambda s: 100.0 * s.mean()),
            recolhas=("food_collected", "mean"),
            n=("success", "size"),
        ).reset_index()
    out = {}
    for _, r in agg.iterrows():
        out.setdefault(r["Scenario"], {})[r["Algorithm"]] = {
            "ptask": float(r["ptask"]), "recolhas": float(r["recolhas"]), "n": int(r["n"]),
        }
    return out


def science_table():
    """Métricas do eval oficial (results/evaluation/eval_summary.csv) ou None."""
    return _aggregate_eval(EVAL_SUMMARY)


# ── Comparação de métricas entre treinos (vista Resultados) ───────────────────
# A entrada "oficial" identifica-se por este PREFIXO (sentinela estável); o resto
# do rótulo é DERIVADO do ficheiro que está de facto no disco.
#
# Estava escrito à mão — "★ Oficial (9 jul · campanha 7 dias, 7 runs × 20 ep)" —
# e o `eval_summary.csv` desta máquina é de 23 jun, com 6 cenários (falta o
# `cooperative_door_bypass`) e 20 ep/célula, não 140. O rótulo afirmava uma
# proveniência que o ficheiro não tem, e num ecrã de defesa isso é uma afirmação
# errada diante do júri. Descrever o ficheiro em vez de o anunciar torna a
# discrepância impossível de esconder.
OFICIAL_PREFIXO = "★ Oficial"


def oficial_label():
    """Rótulo do eval oficial, descrito a partir do PRÓPRIO ficheiro."""
    if not os.path.exists(EVAL_SUMMARY):
        return OFICIAL_PREFIXO
    try:
        df = pd.read_csv(EVAL_SUMMARY)
        data_f = time.strftime("%d/%m", time.localtime(_mtime(EVAL_SUMMARY)))
        n_cen = df["Scenario"].nunique()
        por_cel = int(df.groupby(["Scenario", "Algorithm"]).size().median())
        return (f"{OFICIAL_PREFIXO} ({data_f} · {n_cen} cenários · "
                f"{por_cel} ep/célula)")
    except Exception:
        return OFICIAL_PREFIXO


def _adapt_eval_path(label: str):
    """Caminho do eval_summary de uma fase da campanha adaptativa, ou None."""
    sub = ADAPT_LABEL_TO_DIR.get(label)
    if not sub:
        return None
    # eval_by_run PRIMEIRO. O eval_summary destas fases é o resíduo da pasta
    # global do servidor: traz só a ÚLTIMA execução (20 episódios) e, nas fases
    # A1/A2, traz PPO e SAC que esta campanha nunca treinou (não há models_ppo/
    # models_sac na fase — são modelos de outra campanha que ficaram na pasta).
    # Media pelo eval_summary, o Muro em U do adaptativo aparecia a 80,8 (uma
    # execução feliz) em vez de 68,5 (as sete), com um PPO ao lado que não é dele.
    dir_eval = os.path.join(ADAPT_DIR, sub, "evaluation")
    for nome in ("eval_by_run.csv", "eval_summary.csv"):
        p = os.path.join(dir_eval, nome)
        if os.path.exists(p):
            return p
    return None


def adapt_sessions():
    """Fases da campanha adaptativa com eval_summary (na ordem do pré-registo)."""
    return [lbl for lbl in ADAPT_LABEL_TO_DIR if _adapt_eval_path(lbl)]


def _session_eval_path(session: str):
    """Caminho do eval_summary de uma sessão (procura em subpastas) ou None.

    A entrada oficial (prefixo OFICIAL_PREFIXO) aponta para results/evaluation/;
    as entradas ◆ Adaptativo apontam para results/novelty_adaptativo/<fase>/.
    """
    if session.startswith(OFICIAL_PREFIXO):
        return EVAL_SUMMARY if os.path.exists(EVAL_SUMMARY) else None
    if session in ADAPT_LABEL_TO_DIR:
        return _adapt_eval_path(session)
    base = os.path.join(GRAFICOS_DIR, session)
    # Mesma preferência: o ficheiro por execução manda sobre o resumo (ver acima).
    for padrao in ("eval_by_run*.csv", "eval_summary.csv"):
        hits = sorted(glob.glob(os.path.join(base, "**", padrao), recursive=True))
        if hits:
            return hits[0]
    return None


def sessions_with_eval():
    """Treinos que têm métricas de avaliação, prontos a comparar.

    Ordem: oficial 7d primeiro, depois as fases da campanha adaptativa (19 jul), depois
    as campanhas de graficos_tese que arquivaram eval_summary.
    """
    out = []
    if os.path.exists(EVAL_SUMMARY):
        out.append(oficial_label())
    out += adapt_sessions()
    for s in list_sessions():
        if glob.glob(os.path.join(GRAFICOS_DIR, s, "**", "eval_summary.csv"), recursive=True):
            out.append(s)
    return out


def session_metrics(session: str):
    """Métricas Ptask/recolhas por (cenário, algo) de um treino, ou None."""
    return _aggregate_eval(_session_eval_path(session))


# ── PROVENIÊNCIA DOS DADOS ───────────────────────────────────────────────────
# Todas as vistas passam a declarar O QUE estão a ler e DE QUANDO é. Sem isto, o
# dashboard não distingue "não existe" de "não está aqui": foi assim que uma sessão
# antiga apareceu como se fosse a mais recente (ordenação por mtime), que curvas de há
# 35 dias foram desenhadas como "ao vivo", e que a ausência de vídeos do PPO/SAC passou
# por bug quando era apenas uma campanha que só treinou o GNN.

def idade_legivel(ts):
    """0.0 -> 'nunca'; senão 'há 3 min' / 'há 5 h' / 'há 12 dias'."""
    if not ts:
        return "nunca"
    seg = max(0.0, time.time() - ts)
    if seg < 3600:
        return f"há {int(seg // 60)} min"
    if seg < 86400:
        return f"há {seg / 3600:.0f} h"
    return f"há {seg / 86400:.0f} dias"


def proveniencia(caminho, rotulo=None):
    """Descreve a origem de um dado: ficheiro, se existe, e quando foi escrito.

    Devolve (texto, obsoleto: bool). `obsoleto` é True se o ficheiro não existir.
    """
    nome = rotulo or os.path.relpath(caminho, config.BASE_DIR).replace("\\", "/")
    ts = _mtime(caminho)
    if not ts:
        return f"{nome} — inexistente", True
    return f"{nome} · {idade_legivel(ts)}", False


def eval_freshness():
    """Compara a data do eval_summary com a dos modelos treinados.

    Devolve (eval_mtime, model_mtime, stale: bool). stale=True => há modelos mais
    recentes que a avaliação (armadilha conhecida nº3: eval desfasado dos modelos).
    """
    eval_t = _mtime(EVAL_SUMMARY)
    files = []
    for d in MODEL_DIRS:
        files += glob.glob(os.path.join(config.BASE_DIR, "results", d, "*"))
    # Os CHECKPOINTS intermédios (`*_ckpt_0091min.zip`) não são modelos a avaliar:
    # são fotografias do treino a meio, e o treinador escreve-os em qualquer
    # campanha que passe por aqui. Seis deles, de 27 jul, eram da campanha do mapa
    # grande e faziam a vista Ciência gritar "avaliação DESATUALIZADA" contra uma
    # avaliação que está em dia — o alarme comparava a matriz dos 7 cenários com
    # ficheiros que nunca lhe pertenceram. Um alarme que toca sem motivo é pior do
    # que nenhum: ensina a ignorá-lo, e este existe para a armadilha nº3.
    files = [f for f in files if "ckpt" not in os.path.basename(f).lower()]
    model_t = max((_mtime(f) for f in files), default=0.0)
    # model_t == 0 significa que NÃO HÁ modelos nesta cópia (é o caso do pacote
    # de leitura que corre no Pi). Dizer "em dia" aí seria afirmar uma comparação
    # que não se fez — a vista tem de poder distinguir os dois casos.
    return eval_t, model_t, (model_t > eval_t + 60)


def significance():
    """Tabela de significância (p-values, vencedor por par algo/cenário) ou None."""
    if not os.path.exists(SIGNIF):
        return None
    return pd.read_csv(SIGNIF)


# ── Robustez a falhas (Rrobust) ───────────────────────────────────────────────
def robustness_table():
    """Por (cenário, algo): recolhas base vs com 10% de falhas + retenção %.

    Base = `eval_{algo}_{cenário}.csv` — o ficheiro IRMÃO do `_fail10`, da mesma
    corrida e dos mesmos modelos.
    Falhas = `eval_{algo}_{cenário}_fail10.csv` (run_eval.py --fail-frac 0.1).

    ⚠️ A base era o `eval_summary.csv`, e isso comparava corridas diferentes: o
    summary é da campanha de 7 dias (10 jul, 140 ep/célula) e os `_fail10` são de
    2 jul (20 ep, outros modelos). No Muro em U dava
    `74,25 / 24,54 = 303%` de retenção — e no SAC 563%, um número que só podia
    ser lido como "falhar 10% dos robôs multiplica o desempenho por cinco". Com o
    par certo dá 93,6%, que é o que a tese reporta (§res_robustez: 92-106%) e o
    que o `scripts/plot_robustez.py` sempre usou. Um par sem base não entra:
    inventar denominador é como isto começou.

    Devolve {scenario: {algo: {base, fail, base_succ, fail_succ, retencao, n}}}.
    """
    out = {}
    for scen in config.SCENARIO_KEYS:
        for algo in config.ALGOS:
            fp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{scen}_fail10.csv")
            bp = os.path.join(EVAL_DIR, f"eval_{algo.lower()}_{scen}.csv")
            if not (os.path.exists(fp) and os.path.exists(bp)):
                continue
            b, f = pd.read_csv(bp), pd.read_csv(fp)
            if b.empty or f.empty:
                continue
            base_m = float(b["food_collected"].mean())
            fail_m = float(f["food_collected"].mean())
            out.setdefault(scen, {})[algo] = {
                "base": base_m,
                "fail": fail_m,
                "base_succ": (100.0 * float(b["success"].mean())
                              if "success" in b.columns else None),
                "fail_succ": (100.0 * float(f["success"].mean())
                              if "success" in f.columns else None),
                "retencao": (100.0 * fail_m / base_m) if base_m > 1e-9 else None,
                "n": int(len(f)),
            }
    return out


# ── Escalabilidade Zero-Shot (Sscale) ─────────────────────────────────────────
def scalability_scenarios():
    """Cenários com CSV de escalabilidade (escalabilidade_{cenário}.csv)."""
    if not os.path.isdir(STATS_DIR):
        return []
    return [k for k in config.SCENARIO_KEYS
            if os.path.exists(os.path.join(STATS_DIR, f"escalabilidade_{k}.csv"))]


def scalability_table(scenario: str):
    """Lê escalabilidade_{scenario}.csv → {algo: [pontos ordenados por N]} ou None.

    Cada ponto: {N, food_per_agent, success_rate, mean_food, compatible}. Os
    pontos incompatíveis (MLP do PPO/SAC com N!=20) vêm com compatible=False e
    métricas a None — é a evidência da vantagem de escala da GNN.
    """
    fp = os.path.join(STATS_DIR, f"escalabilidade_{scenario}.csv")
    if not os.path.exists(fp):
        return None
    df = pd.read_csv(fp)
    num = lambda v: None if pd.isna(v) else float(v)
    out = {}
    for _, r in df.iterrows():
        out.setdefault(r["Algorithm"], []).append({
            "N": int(r["N"]),
            "food_per_agent": num(r["food_per_agent"]),
            "success_rate": num(r["success_rate"]),
            "mean_food": num(r["mean_food"]),
            "compatible": bool(r["compatible"]),
        })
    for a in out:
        out[a].sort(key=lambda d: d["N"])
    return out


# ── Galeria de resultados (vista Resultados) ──────────────────────────────────
def _data_da_sessao(nome):
    """Data da CAMPANHA, lida do nome da pasta ('09-07-2026_12h52m').

    Não se usa o mtime da pasta: qualquer operação posterior (copiar, extrair um tar,
    escrever um manifesto, um checkout) reescreve-o e atira campanhas antigas para o
    topo da lista. Foi assim que a sessão do treino de 7 dias foi parar ao 25.º lugar
    de 30, e o launcher passou a abrir por defeito uma campanha de junho — dando a
    impressão de que os heatmaps de julho não existiam.
    """
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})_(\d{2})h(\d{2})m', nome)
    if not m:
        return None
    d, mo, y, h, mi = (int(x) for x in m.groups())
    return datetime.datetime(y, mo, d, h, mi)


def _tem_conteudo(pasta: str) -> bool:
    """A pasta tem algum artefacto além do MANIFESTO que o verificador escreve?

    Uma sessão VAZIA no disco (a de 06-06-2026_10h35m, de um treino que não
    deixou dados) aparecia no seletor como se fosse uma campanha e abria um ecrã
    em branco — que se lê como "o dashboard não carregou" e não como "não há nada
    para carregar". Não é uma sessão: é um diretório.
    """
    for _, _, ficheiros in os.walk(pasta):
        for f in ficheiros:
            if f not in ("MANIFESTO.md",):
                return True
    return False


def list_sessions():
    """Pastas de resultados, campanhas mais recentes primeiro.

    As pastas *curadas* (final_7d, eval_7d, estatisticas...) não têm data no nome e
    vão para o fim da lista, depois das campanhas — continuam acessíveis, mas deixam
    de disputar o topo com a campanha mais recente.
    """
    if not os.path.isdir(GRAFICOS_DIR):
        return []
    # Pastas com "_" à cabeça são arquivo interno (ex.: _orfaos_junho2026, as
    # figuras de junho retiradas da tese) — existem para consulta, não são
    # sessões e não devem aparecer em seletores nem em contagens.
    dirs = [d for d in os.listdir(GRAFICOS_DIR)
            if os.path.isdir(os.path.join(GRAFICOS_DIR, d)) and not d.startswith("_")
            and _tem_conteudo(os.path.join(GRAFICOS_DIR, d))]
    campanhas = [d for d in dirs if _data_da_sessao(d)]
    curadas = [d for d in dirs if not _data_da_sessao(d)]
    campanhas.sort(key=_data_da_sessao, reverse=True)
    return campanhas + sorted(curadas)


_MESES_PT = ("jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez")


def descricao_sessao(session: str) -> str:
    """'mega_A1 · Muro em U · 28 runs · 23 jul' — o que o nome da pasta não diz.

    A DATA não pode vir dos ficheiros da pasta: as figuras regeneram-se (todas
    foram refeitas a 3 ago) e passariam a dizer que um treino de julho é de
    agosto. Vem do `eval_by_run.csv` da ORIGEM — a avaliação corre no fim do
    treino, por isso é a data mais próxima do que aconteceu de facto. A origem
    está escrita no CAMPANHA.md que o `figuras_campanha.py` deixa em cada pasta.

    Sem CAMPANHA.md (campanhas antigas), cai para a data no nome da pasta.
    """
    pasta = os.path.join(GRAFICOS_DIR, session)
    campanha_md = os.path.join(pasta, "CAMPANHA.md")
    partes, quando = [], None

    if os.path.exists(campanha_md):
        try:
            with open(campanha_md, encoding="utf-8") as f:
                texto = f.read()
        except Exception:
            texto = ""
        m = re.search(r"Origem dos dados:\s*`([^`]+)`", texto)
        if m:
            origem = os.path.join(config.BASE_DIR, m.group(1).replace("\\", os.sep))
            for cand in (os.path.join(origem, "evaluation", "eval_by_run.csv"),
                         os.path.join(origem, "evaluation", "eval_summary.csv")):
                if os.path.exists(cand):
                    quando = _mtime(cand)
                    break
        m = re.search(r"Cenários:\s*(.+)", texto)
        if m:
            cens = [c.strip() for c in m.group(1).split(",") if c.strip()]
            if len(cens) == 1:
                partes.append(config.SCENARIO_LABEL_SHORT.get(cens[0], cens[0]))
            elif cens:
                partes.append("%d cenários" % len(cens))
        m = re.search(r"Runs por algoritmo:\s*\{(.+?)\}", texto)
        if m:
            ns = re.findall(r":\s*(\d+)", m.group(1))
            if ns:
                partes.append("%s runs" % (ns[0] if len(set(ns)) == 1 else "/".join(ns)))

    if quando is None:
        d = _data_da_sessao(session)
        if d:
            quando = d.timestamp() if hasattr(d, "timestamp") else None
    if quando:
        # `%b` segue o locale do sistema e sai "Aug" numa tese em português.
        d = datetime.datetime.fromtimestamp(quando)
        partes.append("%d %s" % (d.day, _MESES_PT[d.month - 1]))
    return " · ".join(partes)


def list_pngs(session: str):
    """PNGs de uma sessão (ordenados)."""
    p = os.path.join(GRAFICOS_DIR, session)
    if not os.path.isdir(p):
        return []
    return sorted(f for f in os.listdir(p) if f.lower().endswith(".png"))


# ── Arquivo histórico de campanhas (vista Arquivo) ────────────────────────────
# O registo cronológico de TODAS as campanhas datadas — das primeiras exploratórias
# (maio/junho) às finais. Vive à parte da galeria de Resultados porque a maioria é
# exploratória: só tem gráficos de treino, muitas com conclusões já refutadas (ver
# armadilhas nº1/nº3). Guardá-las é transparência, não são fonte para a tese.
def historical_sessions():
    """Campanhas datadas por ordem CRONOLÓGICA (a mais antiga primeiro)."""
    if not os.path.isdir(GRAFICOS_DIR):
        return []
    dirs = [d for d in os.listdir(GRAFICOS_DIR)
            if os.path.isdir(os.path.join(GRAFICOS_DIR, d)) and _data_da_sessao(d)]
    return sorted(dirs, key=_data_da_sessao)


def session_datetime(session: str):
    """datetime da campanha (lido do nome da pasta) ou None."""
    return _data_da_sessao(session)


def session_is_evaluated(session: str) -> bool:
    """True se a campanha tem avaliação determinística ou modelos arquivados.

    É o que separa as campanhas canónicas (julho em diante, alimentam a tese) das
    primeiras campanhas exploratórias (só gráficos de treino).
    """
    if glob.glob(os.path.join(GRAFICOS_DIR, session, "**", "eval_summary.csv"),
                 recursive=True):
        return True
    modelos = os.path.join(GRAFICOS_DIR, session, "modelos")
    return os.path.isdir(modelos) and bool(os.listdir(modelos))


_RANKING_CACHE = {"chave": None, "valor": None}

# As pastas de campanha seguem quatro convenções diferentes, todas na mesma
# gaveta: datadas (`09-07-2026_12h52m`), canónicas (`final_7d`), fases de uma
# campanha (`mega_A1`, `adaptativo_B3`) e pastas que nem campanhas são
# (`estatisticas`, `eval_7d`). Quem escolhe no seletor não tem como saber o que
# está a escolher — e o nome, sozinho, nunca lho vai dizer.
#
# `canonica` marca as campanhas que a TESE cita: é a diferença entre um número
# que está escrito na dissertação e um que ficou por transparência de percurso.
_CAMPANHAS = {
    "final_7d":   ("Campanha final · 7 dias", True),
    # Mesma campanha que a `final_7d`, noutra pasta: os dados brutos da
    # avaliação. Dá os mesmos valores, e sem esta linha apareciam duas
    # campanhas empatadas no topo de cada cenário, como se fossem duas.
    "eval_7d":    ("Campanha final · avaliação bruta", False),
    "mapa_grande": ("Mapa composto · 8.º cenário", True),
    "mega_treino": ("Mega-treino · agregado", True),
}
_PREFIXOS = (
    ("adaptativo_", "Novelty adaptativo", True),
    ("mega_",       "Mega-treino",        True),
)
# Pastas diferentes que são a MESMA campanha. A avaliação da campanha final
# ficou em duas (`eval_7d` com os dados brutos, `final_7d` com os curados) e o
# ranking mostrava-as como dois treinos empatados.
_ALIAS = {"eval_7d": "final_7d"}


def condicao_da_campanha(nome: str) -> str:
    """`'mega_A1'` -> `'GNN adaptativo · Muro em U (28/28)'`, ou `''`.

    A pasta de gráficos de uma fase do mega-treino chama-se `mega_A1` e a de
    modelos `mega_A_fase1`; só a segunda tinha rótulo a dizer a CONDIÇÃO. Sem
    ele, o seletor da galeria oferece «Mega-treino A1» e «Mega-treino A2» como
    se fossem intercambiáveis — quando um é o braço com novidade adaptativa e o
    outro o controlo com objetivo puro, que é a comparação que sustenta a QI6.

    A fonte é o `MEGA_FASES` deste módulo, que já existia para o visualizador.
    """
    m = re.match(r"^mega_([AB])(\d+)$", nome or "")
    if not m:
        return ""
    alvo = "mega_%s_fase%s" % (m.group(1), m.group(2))
    for rotulo, sub in MEGA_FASES:
        if sub == alvo:
            return rotulo.replace("▣ Mega-treino · ", "").strip()
    # As três fases de GRADIENTE não estão no MEGA_FASES — não têm modelos
    # próprios arquivados (ver a nota lá em cima) e por isso não aparecem no
    # visualizador. Os GRÁFICOS delas existem, e o seletor da galeria oferecia-as
    # como «Mega-treino A3» e «Mega-treino A4», sem dizer qual é o PPO e qual é
    # o SAC. Sem contagens: estas são só a identificação da condição.
    return {"mega_A_fase3": "PPO · Muro em U",
            "mega_A_fase4": "SAC · Muro em U",
            "mega_B_fase6": "SAC · Gargalo"}.get(alvo, "")


def rotulo_campanha(nome: str) -> tuple:
    """`('Mega-treino A1', True)` — nome legível e se a tese a cita."""
    if nome in _CAMPANHAS:
        return _CAMPANHAS[nome]
    for pre, rot, canon in _PREFIXOS:
        if nome.startswith(pre):
            return ("%s %s" % (rot, nome[len(pre):]), canon)
    if _data_da_sessao(nome):
        return ("Exploratória", False)
    return (nome, False)


def _pontuacao_de(path: str):
    """Pontuação por (cenário, algoritmo) de um `eval_by_run*.csv`.

    A unidade é a EXECUÇÃO, não o episódio: agrega-se dentro de cada run antes
    de fazer a média, que é a regra da tese inteira. Sem isso uma campanha com
    mais episódios gravados pesava mais do que uma com mais execuções.
    """
    try:
        df = pd.read_csv(path)
    except Exception:                                        # noqa: BLE001
        return []
    if not {"Scenario", "Algorithm", "food_collected"} <= set(df.columns):
        return []
    tem_run = "Run" in df.columns
    chave = ["Scenario", "Algorithm"] + (["Run"] if tem_run else [])
    agreg = {"recolhas": ("food_collected", "mean")}
    if "success" in df.columns:
        agreg["sucesso"] = ("success", "mean")
    por_run = df.groupby(chave).agg(**agreg).reset_index()

    linhas = []
    for (cen, algo), g in por_run.groupby(["Scenario", "Algorithm"]):
        conv = int((g["sucesso"] >= 1.0).sum()) if "sucesso" in g.columns else None
        linhas.append({
            "cenario": cen, "algo": algo,
            "recolhas": float(g["recolhas"].mean()),
            "ptask": (100.0 * float(g["sucesso"].mean())
                      if "sucesso" in g.columns else None),
            "runs": len(g) if tem_run else None,
            "convergentes": conv if tem_run else None,
        })
    return linhas


def ranking_por_cenario():
    """Que treino ganhou em cada cenário — `{cenário: [linhas, melhor primeiro]}`.

    Porque existe
    -------------
    A Galeria tinha 48 campanhas num seletor e nenhuma pista sobre qual delas
    valia alguma coisa: para mostrar a alguém o melhor resultado num cenário era
    preciso saber de cor qual pasta o continha. As pastas chamam-se `mega_A1` ou
    `09-07-2026_12h52m`, que não ajudam.

    ⚠️ O ranking é SEMPRE dentro de um cenário, nunca entre cenários. As 121
    recolhas/ep do Gargalo e as 67 do Muro em U não são a mesma régua — o mapa,
    o número de itens e a dificuldade mudam —, e um «melhor treino overall»
    somando os dois seria um número sem significado. Por isso não existe aqui:
    a pergunta a que isto responde é «neste cenário, qual foi o melhor treino».

    ⚠️ Só entram campanhas com **avaliação determinística** (`eval_by_run*.csv`,
    20 episódios de sementes fixas). As campanhas exploratórias de maio–junho
    guardaram curvas de treino, que são outra régua: pô-las na mesma tabela
    daria a um número de treino o estatuto de resultado.
    """
    if not os.path.isdir(GRAFICOS_DIR):
        return {}
    ficheiros = sorted(glob.glob(os.path.join(GRAFICOS_DIR, "**", "eval_by_run*.csv"),
                                 recursive=True))
    chave = tuple((f, _mtime(f)) for f in ficheiros)
    if _RANKING_CACHE["chave"] == chave:
        return _RANKING_CACHE["valor"]

    # Uma campanha pode ter o mesmo resultado em vários CSV — o `eval_7d` tem-no
    # em `evaluation_gnn/`, em `evaluation_mlp/` e na raiz, e sem desduplicar o
    # mesmo treino aparecia três vezes seguidas no topo do cenário, como se
    # fossem três treinos diferentes empatados. Fica um registo por
    # (campanha, cenário, algoritmo): o que mediu MAIS execuções.
    melhor = {}
    for f in ficheiros:
        # A campanha é a pasta de topo dentro de graficos_tese; as subpastas de
        # avaliação não são campanhas e os seus nomes não aparecem em lado
        # nenhum do dashboard.
        rel = os.path.relpath(f, GRAFICOS_DIR).replace("\\", "/")
        campanha = rel.split("/")[0]
        for linha in _pontuacao_de(f):
            linha["campanha"] = campanha
            linha["ficheiro"] = rel
            # `_ALIAS` funde pastas que são a MESMA campanha. A `eval_7d` e a
            # `final_7d` são as duas a campanha final de 7 dias, e apareciam
            # como duas entradas com valores idênticos, uma a seguir à outra —
            # a ler-se como dois treinos empatados quando é um só, contado duas
            # vezes.
            k = (_ALIAS.get(campanha, campanha), linha["cenario"], linha["algo"])
            anterior = melhor.get(k)
            if anterior is None:
                melhor[k] = linha
                continue
            # Entre duas cópias fica a que mediu mais execuções e, a empatar, a
            # que está na pasta canónica — a que a tese cita pelo nome.
            chave_nova = ((linha["runs"] or 0),
                          1 if rotulo_campanha(linha["campanha"])[1] else 0)
            chave_velha = ((anterior["runs"] or 0),
                           1 if rotulo_campanha(anterior["campanha"])[1] else 0)
            if chave_nova > chave_velha:
                melhor[k] = linha

    por_cenario = {}
    for linha in melhor.values():
        por_cenario.setdefault(linha["cenario"], []).append(linha)

    for cen in por_cenario:
        # Empate desfaz-se por esta ordem: mais execuções primeiro (entre duas
        # médias iguais, vale a que foi medida mais vezes) e, ainda empatado, a
        # campanha CANÓNICA. Sem a segunda regra, o topo de quatro cenários
        # anunciava a «Campanha final · avaliação bruta» em vez da `final_7d`
        # que a tese cita — o mesmo resultado, com o nome que não está escrito
        # em lado nenhum da dissertação.
        por_cenario[cen].sort(key=lambda d: (-d["recolhas"], -(d["runs"] or 0),
                                             0 if rotulo_campanha(d["campanha"])[1] else 1))

    _RANKING_CACHE.update(chave=chave, valor=por_cenario)
    return por_cenario


_TESE_TEX = os.path.join(config.BASE_DIR, "Tese", "main.tex")
_TESE_IMG = os.path.join(config.BASE_DIR, "Tese", "images")
_FIG_TESE = {"chave": None, "valor": None}
_HASH_CACHE = {}


def _md5(path):
    import hashlib
    chave = (path, _mtime(path))
    if chave not in _HASH_CACHE:
        try:
            with open(path, "rb") as fh:
                _HASH_CACHE[chave] = hashlib.md5(fh.read()).hexdigest()
        except OSError:
            return None
    return _HASH_CACHE[chave]


def figuras_da_tese():
    """`{hash: caminho}` das imagens que o `main.tex` usa de facto.

    A galeria mostra 1105 PNG e nada distinguia os que estão na dissertação dos
    que ficaram pelo caminho. Para mostrar uma figura a alguém era preciso saber
    de cor quais entraram — e as figuras da tese são CÓPIAS das da campanha
    (foi assim que oito delas derivaram em silêncio até 21 jul), pelo que a
    ligação existe no conteúdo, não no nome: compara-se o ficheiro, não o
    caminho. Uma figura regenerada e ainda não copiada para a tese deixa de
    casar, que é a resposta certa — já não é a que está lá.
    """
    if not os.path.exists(_TESE_TEX):
        return {}
    chave = _mtime(_TESE_TEX)
    if _FIG_TESE["chave"] == chave:
        return _FIG_TESE["valor"]
    try:
        with open(_TESE_TEX, encoding="utf-8") as fh:
            tex = fh.read()
    except OSError:
        return {}
    # Sem as linhas comentadas: a secção do mapa composto ainda está por entrar, e
    # as figuras dela não estão na tese enquanto o `\input` não for descomentado.
    tex = "\n".join(l for l in tex.split("\n") if not l.strip().startswith("%"))
    out = {}
    for rel in set(re.findall(r"\{images/([^}]+)\}", tex)):
        p = os.path.join(_TESE_IMG, rel.replace("/", os.sep))
        if os.path.exists(p):
            h = _md5(p)
            if h:
                out[h] = rel
    _FIG_TESE.update(chave=chave, valor=out)
    return out


def figura_na_tese(session: str, filename: str):
    """O caminho na tese, se esta imagem for a que a dissertação usa; senão None."""
    alvos = figuras_da_tese()
    if not alvos:
        return None
    p = os.path.join(GRAFICOS_DIR, session, filename)
    # Filtro barato primeiro: só se o tamanho bater com algum candidato é que
    # vale a pena ler o ficheiro. Sem isto, abrir a galeria custava o hash de
    # todos os PNG da campanha.
    try:
        tam = os.path.getsize(p)
    except OSError:
        return None
    if tam not in _tamanhos_da_tese():
        return None
    return alvos.get(_md5(p))


_TAMANHOS = {"chave": None, "valor": frozenset()}


def _tamanhos_da_tese():
    chave = _mtime(_TESE_TEX)
    if _TAMANHOS["chave"] != chave:
        tams = set()
        for rel in figuras_da_tese().values():
            p = os.path.join(_TESE_IMG, rel.replace("/", os.sep))
            try:
                tams.add(os.path.getsize(p))
            except OSError:
                pass
        _TAMANHOS.update(chave=chave, valor=frozenset(tams))
    return _TAMANHOS["valor"]


def pontuacao_campanha(campanha: str, cenario: str, algo: str):
    """A pontuação DESTA campanha neste cenário e algoritmo, ou None.

    Existe porque o chip por baixo dos vídeos recebia a sessão e não a usava:
    lia a `science_table()`, que é a avaliação OFICIAL, e mostrava-a por baixo
    de qualquer vídeo. No modo «Comparar treinos» isso punha o mesmo «86% ·
    38,3 rec/ep» debaixo de dois treinos diferentes — a ler-se como um empate
    medido, quando era o mesmo número escrito duas vezes.
    """
    alvo = _ALIAS.get(campanha, campanha)
    for d in ranking_por_cenario().get(cenario, []):
        if d["algo"].upper() == algo.upper() and d["campanha"] == alvo:
            return d
    return None


def sessoes_com_video(algo: str, scenario: str):
    """Que treinos têm vídeo deste algoritmo NESTE cenário.

    O seletor de «Comparar treinos» oferecia as 24 sessões com vídeo, fossem
    quais fossem o algoritmo e o cenário escolhidos — e a maioria das
    combinações não existe: cada fase do mega-treino treinou um cenário só, e
    metade delas só o GNN. O resultado era escolher dois treinos e receber dois
    «sem vídeo», que se lê como avaria e não como ausência.
    """
    return [s for s in video_sessions() if video_for(s, algo, scenario)]


def session_manifesto(session: str):
    """Conteúdo do MANIFESTO.md da campanha (markdown), ou None."""
    p = os.path.join(GRAFICOS_DIR, session, "MANIFESTO.md")
    if not os.path.exists(p):
        return None
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return None


def graph_type(filename: str) -> str:
    """Categoria de um gráfico, derivada do prefixo do nome (para filtrar).

    A separação treino/avaliação NÃO é cosmética: os boxplots de treino usam o melhor
    score do run (otimista, escala de fitness/recompensa) e os de avaliação usam a
    eval determinística de 20 ep (a métrica da tese). Já foram confundidos uma vez —
    a armadilha do "eval desfasado" nasceu daí — e a galeria misturava-os numa só
    categoria "Boxplots".
    """
    f = filename.lower()
    # O dot plot é a figura PREFERIDA nos cenários bimodais (com n=7 os quartis
    # de uma caixa são ruído). Não tinha regra nenhuma aqui e caía em "Outros" —
    # a figura recomendada para a defesa era a única sem categoria.
    if f.startswith("dotplot"):
        return "Dot plots (avaliação)"
    if f.startswith("boxplot_eval"):
        return "Boxplots (avaliação)"
    if f.startswith("boxplot"):
        return "Boxplots (treino)"
    # `curva_aprendizagem_X` é o nome ANTIGO de `comparacao_mapa_X` — a mesma
    # figura, gerada pelo pipeline de treino em vez do gerador da tese. As
    # campanhas antigas ficaram com ele, e sem esta linha apareciam em "Outros",
    # o que fazia a mesma figura mudar de secção conforme a campanha aberta.
    if f.startswith(("comparacao_mapa", "curva_aprendizagem")):
        return "Curvas por mapa"
    if f.startswith("desempenho_global"):
        return "Curvas por algoritmo"
    if f.startswith("heatmap_geodesico"):
        return "Heatmaps geodésicos"
    if f.startswith("heatmap_ocupacao"):
        return "Heatmaps de ocupação"
    if f.startswith("painel_videos"):
        return "Painéis de vídeo"
    if f.startswith("escalabilidade"):
        return "Escalabilidade"
    if f.startswith(("taxa_sucesso", "recolhas", "comparacao_barras")):
        return "Métricas de tarefa"
    if f.startswith(("mapa_3d", "mapa_grande_planta", "mapa_topo", "scen_")):
        return "Plantas dos cenários"
    # `comparacao_<cenário>` é o nome da PRIMEIRA geração das curvas por mapa
    # (antes de `comparacao_mapa_`). Vem no fim de propósito: acima está
    # `comparacao_barras_geral`, que é outra coisa e tem de ser apanhado antes.
    if f.startswith("comparacao_"):
        return "Curvas por mapa"
    return "Outros"


# ── Curvas de treino ao vivo (vista Monitorizar) ─────────────────────────────
# algo -> (caminho, coluna_x, coluna_score, coluna_tarefa)
TRAIN_LOGS = {
    "GNN": (os.path.join(config.BASE_DIR, "results", "logs", "gnn_3d_training.csv"),
            "timestep", "best_fitness", "best_task_food"),
    "PPO": (os.path.join(config.BASE_DIR, "results", "logs_ppo", "training_history_ppo_3d.csv"),
            "timesteps", "ep_rew_mean", "ep_task_mean"),
    "SAC": (os.path.join(config.BASE_DIR, "results", "logs_sac", "training_history_sac_3d.csv"),
            "timesteps", "ep_rew_mean", "ep_task_mean"),
}


def training_curves():
    """Lê os CSVs de treino locais. Devolve {algo: {x, score, task, mtime}} (só os que existem)."""
    out = {}
    for algo, (path, xcol, scol, tcol) in TRAIN_LOGS.items():
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if xcol not in df.columns or len(df) == 0:
            continue
        out[algo] = {
            "x": df[xcol].tolist(),
            "score": df[scol].tolist() if scol in df.columns else [],
            "task": df[tcol].tolist() if tcol in df.columns else [],
            "mtime": _mtime(path),
            "path": path,
            "idade_h": (time.time() - os.path.getmtime(path)) / 3600.0,
        }
    return out


# Um CSV que não é escrito há mais de meia hora não corresponde a um treino a decorrer.
# Isto importa porque estes ficheiros são LOCAIS: quando o treino corre no servidor (o
# caso normal neste projeto), ficam parados no último treino local — e a vista desenhava
# curvas antigas como se fossem de agora.
IDADE_OBSOLETA_H = 0.5


def estado_curvas_locais():
    """Diz se há treino LOCAL a decorrer, ou se os CSVs são apenas restos antigos.

    Devolve (ha_treino_vivo, descrição).
    """
    curvas = training_curves()
    if not curvas:
        return False, ("Sem CSVs de treino locais. Se o treino está a correr no "
                       "servidor, use a vista «Servidor».")
    recente = min(c["idade_h"] for c in curvas.values())
    if recente > IDADE_OBSOLETA_H:
        dias = recente / 24.0
        # Vírgula, como o resto do dashboard (e «22 dias», não «22,0 dias»:
        # ao fim de três semanas a casa decimal não informa ninguém).
        quando = (("%.1f h" % recente).replace(".", ",") if dias < 1
                  else "%d dias" % round(dias))
        return False, (f"Nenhum treino local a decorrer — o CSV mais recente não é "
                       f"escrito há {quando}. As curvas abaixo são de um treino "
                       f"antigo. O treino a decorrer no servidor vê-se na vista "
                       f"«Servidor».")
    return True, "Treino local a decorrer."


# ── Vídeos dos episódios (vista Vídeos) ───────────────────────────────────────
VIDEO_ALGOS = ("gnn", "ppo", "sac")


def _videos_dir(session: str) -> str:
    return os.path.join(GRAFICOS_DIR, session, "videos")


def video_sessions():
    """Sessões com vídeos (pasta videos/ não vazia), mais recentes primeiro."""
    out = []
    for s in list_sessions():
        d = _videos_dir(s)
        if os.path.isdir(d) and any(f.lower().endswith(".gif") for f in os.listdir(d)):
            out.append(s)
    return out


def list_videos(session: str):
    """Nomes dos GIFs de uma sessão (ordenados)."""
    d = _videos_dir(session)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".gif"))


def parse_video(filename: str):
    """'gnn_u_wall.gif' -> ('gnn', 'u_wall'). Algo = prefixo conhecido."""
    base = filename[:-4] if filename.lower().endswith(".gif") else filename
    for a in VIDEO_ALGOS:
        if base.startswith(a + "_"):
            return a, base[len(a) + 1:]
    return "?", base


def video_for(session: str, algo: str, scenario: str):
    """Nome do GIF de (algo, cenário) nessa sessão, ou None se não existir."""
    fn = f"{algo}_{scenario}.gif"
    return fn if fn in list_videos(session) else None


def scenarios_with_video(session: str):
    """Cenários (chaves) que têm pelo menos um vídeo na sessão, na ordem canónica."""
    present = {parse_video(f)[1] for f in list_videos(session)}
    from . import config
    return [k for k in config.SCENARIO_KEYS if k in present]


# ── F2 do mapa composto: os resultados MEDIDOS ─────────────────────────────────
F2_GLOB = os.path.join(config.BASE_DIR, "results", "mapa_grande", "f2*", "**",
                       "eval_by_run.csv")


def f2_resultados():
    """Por algoritmo: execuções, convergentes, recolhas/ep e uso da porta.

    A vista do Mapa mostrava o F1 inteiro e, do F2, só uma linha de estado com o
    que o servidor está a correr. Entretanto o braço dos gradientes fechou (7 e
    10 ago) e os 840 episódios ficaram no disco **sem aparecer em lado nenhum** —
    o resultado mais recente da tese, invisível no sítio que existe para o
    mostrar. Um dashboard que não mostra o que já está medido é uma surpresa à
    espera de acontecer em frente ao júri.

    O mesmo glob do `scripts/verificar_mapa_grande.py` e do
    `analise_mapa_grande.py`: um braço que apareça no disco entra aqui sozinho,
    incluindo o do GNN quando fechar.

    ⚠️ «Convergente» é ≥1 recolha na MÉDIA POR EXECUÇÃO, que é a unidade
    estatística da tese (M2 do pré-registo) — não por episódio. E o limiar
    ⌈5/7 × n⌉ sai do n do próprio CSV, nunca de um 15 escrito à mão: se uma
    execução faltar, a fasquia desce e tem de descer à vista de todos.
    """
    hits = sorted(glob.glob(F2_GLOB, recursive=True))
    if not hits:
        return None
    try:
        df = pd.concat([pd.read_csv(h) for h in hits], ignore_index=True)
    except Exception:                        # noqa: BLE001 — CSV a meio de uma escrita
        return None
    if df.empty or "Algorithm" not in df.columns:
        return None

    fora = []
    for algo, g in df.groupby("Algorithm"):
        por_run = g.groupby("Run").food_collected.mean()
        porta = g["door_opened"] if "door_opened" in g.columns else None
        if porta is not None:
            porta = porta.astype(str).str.lower().isin(("true", "1")).mean()
        fora.append({
            "algo": str(algo).upper(),
            "runs": int(por_run.size),
            "convergentes": int((por_run > 0).sum()),
            "media": float(por_run.mean()),
            "dp": float(por_run.std(ddof=0)) if por_run.size > 1 else 0.0,
            "episodios": int(len(g)),
            "porta": None if porta is None else float(porta),
        })
    fora.sort(key=lambda d: d["algo"])
    n = max(d["runs"] for d in fora)
    return {"algos": fora, "n": n, "limiar": -(-5 * n // 7),
            "episodios": int(len(df)),
            "fontes": [os.path.relpath(h, config.BASE_DIR) for h in hits],
            "falhas": [os.path.relpath(h, config.BASE_DIR)
                       for h in hits
                       if os.path.exists(h.replace(".csv", "_FALHAS.txt"))]}


def send_to_thesis(session: str, filename: str):
    """Copia um PNG da sessão para Tese/images/resultados/ (nome inalterado)."""
    src = os.path.join(GRAFICOS_DIR, session, filename)
    if not os.path.exists(src):
        return False, "ficheiro não encontrado"
    os.makedirs(TESE_IMG_DIR, exist_ok=True)
    shutil.copy2(src, os.path.join(TESE_IMG_DIR, filename))
    return True, filename
