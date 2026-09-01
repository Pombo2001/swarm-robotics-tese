# -*- coding: utf-8 -*-
"""Reproduz a Tabela de custo computacional por algoritmo (tese, §6.14.1).

Porque existe
A tabela entrou a 30 de agosto de 2026, a pedido do orientador («seria
interessante uma tabela de comparação de tempos de execução»). Os seus números
não vêm de nenhum CSV de avaliação — vêm dos REGISTOS DE TREINO da campanha de
replicação (mega_1mes, Muro em U, n=28 por braço), que nenhuma outra régua lê:

  · o evolutivo escreve `logs/gnn_3d_training_u_wall_run*.csv` com o par
    (timestep, time) acumulados;
  · o PPO e o SAC não escrevem CSV nenhum — o que existe é o `.log` da fase,
    com as tabelas do Stable-Baselines3 (`total_timesteps`, `time_elapsed`).

ARMADILHA: as pastas `logs/` das fases 3 e 4 (PPO e SAC) contêm cópias
   IDÊNTICAS dos CSV do GNN da fase 2 — herdadas do diretório de trabalho no
   servidor. Ler os `.csv` dessas fases dá os números do evolutivo com o rótulo
   errado; por isso o PPO e o SAC leem-se SÓ do `.log`.

Unidades: o SB3 conta TRANSIÇÕES DE AGENTE (16 arenas × 20 agentes × 64
   passos = 20 480 por iteração) e o treinador evolutivo conta PASSOS DE
   AMBIENTE. Para comparar, divide-se o do SB3 por N=20.

Os `results/mega_1mes/` não são versionados: fora da máquina onde a campanha foi
trazida, o verificador diz o que falta e sai com 0 (não é uma divergência).

Uso:
    .venv/Scripts/python.exe scripts/verificar_tempos.py
"""
import csv
import glob
import io
import os
import re
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEGA = os.path.join(RAIZ, "results", "mega_1mes")
MAIN_TEX = os.path.join(RAIZ, "Tese", "main.tex")

N_AGENTES = 20
# fase -> (rótulo na tese, núcleos, fonte)
BRACOS = (
    ("mega_A_fase1", "GNN adaptativo", 30, "csv"),
    ("mega_A_fase2", "GNN objetivo", 30, "csv"),
    ("mega_A_fase3", "PPO", 16, "log"),
    ("mega_A_fase4", "SAC", 16, "log"),
)


def _do_csv(fase):
    """(passos de ambiente, segundos) da última linha de cada execução."""
    padrao = os.path.join(MEGA, fase, "logs", "gnn_3d_training_u_wall_run*.csv")
    saida = []
    for f in sorted(glob.glob(padrao)):
        linhas = list(csv.DictReader(io.open(f, encoding="utf-8")))
        if not linhas:
            continue
        ts, t = float(linhas[-1]["timestep"]), float(linhas[-1]["time"])
        if t > 0:
            saida.append((ts, t))
    return saida


def _do_log(fase):
    """Idem, do .log da fase: um bloco por execução, aberto por [START]."""
    caminho = os.path.join(MEGA, fase, "%s.log" % fase)
    if not os.path.exists(caminho):
        return []
    texto = io.open(caminho, encoding="utf-8", errors="replace").read()
    saida = []
    for bloco in texto.split("[START]")[1:]:
        passos = re.findall(r"total_timesteps\s*\|\s*(\d+)", bloco)
        segs = re.findall(r"time_elapsed\s*\|\s*([\d.e+]+)", bloco)
        if not passos or not segs:
            continue
        t = float(segs[-1])
        if t > 0:
            saida.append((int(passos[-1]) / float(N_AGENTES), t))
    return saida


def celulas_da_tabela(tex, rotulo):
    """Os números da linha da tab:res_tempos que começa por `rotulo`."""
    corpo = tex.split(r"\label{tab:res_tempos}", 1)
    if len(corpo) < 2:
        return None
    corpo = corpo[1].split(r"\end{tabular}", 1)[0]
    for linha in corpo.splitlines():
        if linha.strip().startswith(rotulo + " &"):
            nums = []
            for cel in linha.split("&")[1:]:
                m = re.search(r"(\d+(?:\{,\}\d+)?)", cel)
                nums.append(float(m.group(1).replace("{,}", ".")) if m else None)
            return nums
    return None


def main():
    print("=" * 72)
    print("VERIFICAÇÃO: custo computacional por algoritmo  vs  registos de treino")
    print("=" * 72)

    if not os.path.isdir(MEGA):
        print("   sem `results/mega_1mes/` nesta máquina — nada a conferir.")
        print("   (a campanha não está versionada; traga-a antes de conferir)")
        return 0

    tex = re.sub(r"(?<!\\)%[^\n]*", "", io.open(MAIN_TEX, encoding="utf-8").read())
    if r"\label{tab:res_tempos}" not in tex:
        print("   a tese não tem a tabela `tab:res_tempos` — nada a conferir.")
        return 0

    problemas, medidos = [], {}
    for fase, rot, nucleos, fonte in BRACOS:
        dados = _do_csv(fase) if fonte == "csv" else _do_log(fase)
        if not dados:
            print("   %-16s sem registos de treino em %s — saltado" % (rot, fase))
            continue
        dur = st.median([t / 60.0 for _, t in dados])
        passos = st.median([p for p, _ in dados])
        debito = st.median([p / t for p, t in dados]) / nucleos
        nucleos_hora = dur / 60.0 * nucleos
        medidos[rot] = (nucleos, dur, nucleos_hora, passos / 1e6, debito, len(dados))

        na_tese = celulas_da_tabela(tex, rot)
        if na_tese is None:
            problemas.append("%s: não encontrei a linha na tab:res_tempos" % rot)
            continue
        esperado = [nucleos, dur, nucleos_hora, passos / 1e6, debito]
        rotulos = ("núcleos", "duração (min)", "núcleos-hora",
                   "passos sim. (10^6)", "passos/s por núcleo")
        for i, (r, calc) in enumerate(zip(rotulos, esperado)):
            lida = na_tese[i] if i < len(na_tese) else None
            # a tese arredonda a 1 ou 2 casas: compara-se ao arredondamento dela
            casas = 0 if r == "núcleos" else (2 if calc < 1 else 1)
            if lida is None or abs(lida - round(calc, casas)) > 10 ** (-casas) / 2:
                problemas.append("%-16s %-20s tese=%s  registos=%s"
                                 % (rot, r, lida, round(calc, casas)))
        print("   [%2d execuções] %-16s %6.1f min  %5.1f núc-h  %5.2fM passos  "
              "%5.1f passos/s/núcleo" % (len(dados), rot, dur, nucleos_hora,
                                         passos / 1e6, debito))

    # as duas razões que o texto afirma
    if "PPO" in medidos and "GNN adaptativo" in medidos:
        g, p = medidos["GNN adaptativo"], medidos["PPO"]
        razao_custo = g[2] / p[2]
        razao_amostras = g[3] / p[3]
        for rot, calc, padrao in (
                ("razão de núcleos-hora (GNN/PPO)", razao_custo,
                 r"uma razão de \$(\d+)\{,\}(\d+)\\times\$"),
                ("razão de passos de simulação", razao_amostras,
                 r"consome \$\\approx (\d+)\\times\$ mais passos")):
            m = re.search(padrao, tex)
            if not m:
                problemas.append("%s: não encontrei a afirmação no texto" % rot)
                continue
            lido = float(".".join(m.groups())) if len(m.groups()) == 2 else float(m.group(1))
            tol = 0.05 if len(m.groups()) == 2 else 1.0
            if abs(lido - calc) > tol:
                problemas.append("%-32s tese=%s  registos=%.2f" % (rot, lido, calc))
            else:
                print("   [v] %-42s %s" % (rot, lido))

    problemas += _conferir_tamanho_das_politicas(tex)

    if problemas:
        print("\nDIVERGÊNCIAS:")
        for x in problemas:
            print("   " + x)
        return 1
    print("\nOs números da tabela batem com os registos de treino ✓")
    return 0


def _conferir_tamanho_das_politicas(tex):
    """As duas contagens de parâmetros que o parágrafo da execução afirma.

    Não vêm de registo nenhum: contam-se instanciando as redes. O ator do
    PPO/SAC é a MLP [256, 256] da Stable-Baselines3 sobre a observação de
    dimensão fixa; o do evolutivo é o `GNNAgent3D`.
    """
    if RAIZ not in sys.path:
        sys.path.append(RAIZ)
    try:
        import torch.nn as nn
        import yaml
        from src.agents.gnn_agent_3d import GNNAgent3D
    except Exception as e:                                   # pragma: no cover
        print("   (sem torch/agente disponível: %s) — parâmetros não conferidos" % e)
        return []

    cfg = yaml.safe_load(io.open(os.path.join(RAIZ, "configs", "foraging.yaml"),
                                 encoding="utf-8"))
    n_ag = cfg["environment"]["num_agents"]
    d_obs = 16 + (n_ag - 1) * 5
    arq = cfg["ppo"]["net_arch"]
    camadas, dentro = [], d_obs
    for larg in arq:
        camadas += [nn.Linear(dentro, larg), nn.ReLU()]
        dentro = larg
    camadas += [nn.Linear(dentro, 3), nn.Tanh()]
    mlp = nn.Sequential(*camadas)
    gnn = GNNAgent3D("robot_0", None,
                     config_path=os.path.join(RAIZ, "configs", "foraging.yaml"))
    milhares = {"GNN": sum(p.numel() for p in gnn.parameters()) / 1000.0,
                "MLP": sum(p.numel() for p in mlp.parameters()) / 1000.0}

    problemas = []
    for rot, padrao, esperado, casas in (
            ("parâmetros do GNN", r"usa \$\\approx (\d+)\{,\}(\d+)\$ mil parâmetros",
             milhares["GNN"], 1),
            ("parâmetros do ator MLP", r"os \$\\approx (\d+)\$ mil do ator MLP",
             milhares["MLP"], 0)):
        m = re.search(padrao, tex)
        if not m:
            problemas.append("%s: não encontrei a afirmação no texto" % rot)
            continue
        lido = float(".".join(m.groups()))
        if abs(lido - round(esperado, casas)) > 10 ** (-casas) / 2:
            problemas.append("%-24s tese=%s  contado=%s"
                             % (rot, lido, round(esperado, casas)))
        else:
            print("   [v] %-42s %s mil" % (rot, lido))
    return problemas


if __name__ == "__main__":
    sys.exit(main())
