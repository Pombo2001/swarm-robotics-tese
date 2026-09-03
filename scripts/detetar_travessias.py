# -*- coding: utf-8 -*-
"""Que modelos arquivados atravessam paredes pela costura do teto — e quantos.

O defeito (3 set 2026)
O mundo é uma esfera de raio `arena_radius` e as paredes são caixas de altura
2×raio centradas em z=0: o topo da parede coincide com o teto da esfera. A
colisão (`swarm_env_3d.py`) empurra o agente pela face de MENOR penetração,
nos três eixos. Um agente a z≈14,7 m que encoste a uma parede tem menos
penetração em z do que em x/y: é empurrado para cima, a esfera devolve-o ao
teto, e ele atravessa a parede a deslizar por cima dela. O campeão A1 das
Quatro Salas fazia-o (86 posições dentro de paredes no episódio exportado,
todas entre 14,3 e 14,8 m).

O que isto mede
Reproduz episódios determinísticos com cada modelo arquivado — campeões e,
onde existem, os modelos de cada execução — e conta, passo a passo, os
agentes cujo CENTRO está dentro de uma caixa de parede (em x, y e z). Sem a
costura isso é impossível: a colisão mantém o centro a `robot_radius` da
face. A porta cooperativa conta só enquanto está fechada (lê-se `env.walls`
a cada passo, de onde o painel sai quando abre).

Saída: `results/estatisticas/travessias_paredes.csv` (uma linha por
episódio) e um resumo por célula (campanha, cenário, algoritmo) com o número
de execuções afetadas — o que a secção de Limitações precisa.

Uso:
    python scripts/detetar_travessias.py                 # campanhas da tese
    python scripts/detetar_travessias.py --episodios 5 --jobs 6
    python scripts/detetar_travessias.py --so final_7d adaptativo_A1
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
try:
    sys.stdout.reconfigure(encoding="utf-8")      # o resumo tem «⚠»; a consola do Windows não
except Exception:                                 # noqa: BLE001
    pass

CONFIG = os.path.join(RAIZ, "configs", "foraging.yaml")
SAIDA_CSV = os.path.join(RAIZ, "results", "estatisticas", "travessias_paredes.csv")
SAIDA_MD = os.path.join(RAIZ, "results", "estatisticas", "travessias_resumo.md")

CENARIOS = ["none", "u_wall", "bottleneck", "four_rooms", "cooperative_door",
            "cooperative_perception", "cooperative_door_bypass", "mapa_grande"]

# (campanha, pasta que contém models/, models_ppo/, models_sac/)
NA = os.path.join(RAIZ, "results", "novelty_adaptativo")
MEGA = os.path.join(RAIZ, "results", "mega_1mes")
CAMPANHAS = [
    ("final_7d",       os.path.join(RAIZ, "results")),
    ("adaptativo_A1",  os.path.join(NA, "week_A_fase1")),
    ("adaptativo_A2",  os.path.join(NA, "week_A_fase2")),
    ("adaptativo_B1",  os.path.join(NA, "week_B_fase1")),
    ("adaptativo_B2",  os.path.join(NA, "week_B_fase2")),
    ("adaptativo_B3",  os.path.join(NA, "week_B_fase3")),
    ("mega_A1",        os.path.join(MEGA, "mega_A_fase1")),
    ("mega_A2",        os.path.join(MEGA, "mega_A_fase2")),
    ("mega_A5",        os.path.join(MEGA, "mega_A_fase5")),
    ("mega_B1",        os.path.join(MEGA, "mega_B_fase1")),
    ("mega_B2",        os.path.join(MEGA, "mega_B_fase2")),
    ("mega_B3",        os.path.join(MEGA, "mega_B_fase3")),
    ("mega_B4",        os.path.join(MEGA, "mega_B_fase4")),
    ("mega_B5",        os.path.join(MEGA, "mega_B_fase5")),
    ("mega_B7",        os.path.join(MEGA, "mega_B_fase7")),
    ("mapa_grande_f2", os.path.join(RAIZ, "results", "graficos_tese",
                                    "16-08-2026_16h14m", "modelos")),
]


def modelos_de(raiz: str):
    """[(algo, cenário, run|None, caminho)] — só ficheiros DO cenário.

    Nunca o genérico `gnn_3d_best.pth` para outro cenário: seria avaliar o
    campeão do Sandbox no labirinto, que é outro modelo com outro rótulo.
    """
    out = []
    for cen in CENARIOS:
        suf = "" if cen == "none" else "_" + cen
        # GNN: campeão + execuções
        p = os.path.join(raiz, "models", "gnn_3d_best%s.pth" % suf)
        if os.path.exists(p):
            out.append(("gnn", cen, None, p))
        for q in sorted(glob.glob(os.path.join(raiz, "models", "gnn_3d_best%s_run*.pth" % suf))):
            m = re.search(r"_run(\d+)\.pth$", q)
            out.append(("gnn", cen, int(m.group(1)) if m else None, q))
        # PPO / SAC: só o campeão está arquivado
        for algo in ("ppo", "sac"):
            p = os.path.join(raiz, "models_" + algo, "%s_3d_final%s.zip" % (algo, suf))
            if os.path.exists(p):
                out.append((algo, cen, None, p))
    return out


def _episodio(env, algo, modelo, seed: int):
    """Uma reprodução. Devolve um dicionário com:

    * `dentro` — (passo, agente) com o centro dentro de uma caixa de parede;
    * `travessias` — vezes que um agente entrou numa parede por um lado e saiu
      pelo lado OPOSTO (atravessou-a); `travessias_teto` as que começaram com o
      agente a menos de 1 m do teto da esfera (a costura);
    * `presos` — agentes que estiveram dentro de uma parede sem a atravessar
      (entraram e saíram pelo mesmo lado, ou ficaram lá): é o que acontece nas
      junções em T, onde a saída de uma caixa empurra para dentro da vizinha;
    * `zmax`, `fracao_no_teto`, `recolhas`.

    «Dentro» e «atravessou» não são a mesma coisa, e só a segunda muda o que a
    tese conclui: um agente preso numa junção não encurta caminho nenhum.
    """
    from scripts.heatmaps import _policy_actions
    obs, _ = env.reset(seed=seed)
    r = float(env.arena_radius)
    n_ag = len(env.agents)
    zmax, no_teto, dentro_n, agentes_dentro = -1e9, 0, 0, set()
    travessias = travessias_teto = 0
    agentes_atravessam, agentes_presos = set(), set()
    # Estado por agente: parede em que está (ou -1), lado por onde entrou
    # (sinal ao longo do eixo fino), altitude à entrada.
    em = [-1] * n_ag
    lado_entrada = [0] * n_ag
    z_entrada = [0.0] * n_ag
    P_ant = np.asarray(env.agent_positions).copy()
    for i in range(env.max_steps):
        acoes = _policy_actions(env, algo, modelo, obs)
        obs, _, _, _, _ = env.step(acoes)
        P = np.asarray(env.agent_positions)
        zmax = max(zmax, float(P[:, 2].max()))
        if (P[:, 2] > r - 1.0).any():
            no_teto += 1
        paredes = [(np.asarray(w["pos"]), np.asarray(w["size"]) / 2.0) for w in env.walls]
        for a in range(n_ag):
            atual = -1
            for k, (pos, half) in enumerate(paredes):
                if np.all(np.abs(P[a] - pos) < half):
                    atual = k
                    break
            if atual >= 0:
                dentro_n += 1
                agentes_dentro.add(a)
            if atual != em[a]:
                # Saiu da parede onde estava?
                if em[a] >= 0 and em[a] < len(paredes):
                    pos, half = paredes[em[a]]
                    fino = 0 if half[0] < half[1] else 1
                    lado_saida = int(np.sign(P[a][fino] - pos[fino]))
                    if lado_saida != 0 and lado_saida != lado_entrada[a]:
                        travessias += 1
                        agentes_atravessam.add(a)
                        if z_entrada[a] > r - 1.0:
                            travessias_teto += 1
                    else:
                        agentes_presos.add(a)
                # Entrou numa parede?
                if atual >= 0:
                    pos, half = paredes[atual]
                    fino = 0 if half[0] < half[1] else 1
                    lado_entrada[a] = int(np.sign(P_ant[a][fino] - pos[fino])) or 1
                    z_entrada[a] = float(P_ant[a][2])
                em[a] = atual
        P_ant = P.copy()
    # Quem acabou o episódio dentro de uma parede também não a atravessou.
    for a in range(n_ag):
        if em[a] >= 0:
            agentes_presos.add(a)
    return dict(recolhas=int(env.total_food_collected), zmax=round(zmax, 2),
                fracao_no_teto=round(no_teto / env.max_steps, 3),
                dentro=dentro_n, agentes_dentro=len(agentes_dentro),
                travessias=travessias, travessias_teto=travessias_teto,
                agentes_atravessam=len(agentes_atravessam),
                agentes_presos=len(agentes_presos - agentes_atravessam))


def _sha1(caminho: str) -> str:
    """As pastas das fases arquivaram CÓPIAS dos mesmos modelos (o arquivamento
    entre fases copiava results/models inteiro): o resumo conta cada modelo
    uma vez, pelo conteúdo, e diz em que pastas está."""
    import hashlib
    h = hashlib.sha1()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()[:12]


def tarefa(args):
    """Um modelo, N episódios. Corre num processo próprio."""
    campanha, algo, cen, run, caminho, episodios = args
    # Um thread por processo e prioridade baixa: com 12 processos × 16 threads
    # do PyTorch a máquina ficava inutilizável, e o paralelismo já está nos
    # processos. A inferência é de 20 agentes por passo — não precisa de mais.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    import torch
    torch.set_num_threads(1)
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(
                ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)   # BELOW_NORMAL
        else:
            os.nice(10)
    except Exception:                                    # noqa: BLE001
        pass
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    from scripts.eval_all import load_model
    modelo, _ = load_model(algo, cen, CONFIG, model_path=caminho)
    if modelo is None:
        return [dict(campanha=campanha, algo=algo.upper(), cenario=cen, run=run,
                     modelo=os.path.relpath(caminho, RAIZ), erro="modelo incompatível")]
    env = SwarmForagingEnv3D(config_path=CONFIG)
    env.config["environment"]["classic_scenario"] = cen
    linhas = []
    for k in range(episodios):
        seed = 2024 + k
        m = _episodio(env, algo, modelo, seed)
        m.update(campanha=campanha, algo=algo.upper(), cenario=cen, run=run,
                 modelo=os.path.relpath(caminho, RAIZ).replace("\\", "/"),
                 sha1=_sha1(caminho), seed=seed, erro="")
        linhas.append(m)
    return linhas


def resumo(df: pd.DataFrame) -> str:
    """Por célula (cenário, algoritmo) e por modelo ÚNICO (sha1)."""
    ok = df[df["erro"] == ""].copy()
    n_ficheiros = ok["modelo"].nunique()
    campanhas_por_sha = ok.groupby(["sha1", "cenario", "algo"])["campanha"].agg(
        lambda c: "/".join(sorted(set(c))))
    # O mesmo ficheiro em várias pastas dá episódios repetidos: contam-se uma
    # vez, senão o campeão A1 (em cinco pastas) aparecia com 5× as travessias.
    ok = ok.drop_duplicates(["sha1", "cenario", "algo", "seed"], keep="first")
    # Um modelo = um ficheiro (pelo conteúdo). Afetado = atravessou em algum episódio.
    g = ok.groupby(["sha1", "cenario", "algo"])
    por_modelo = g.agg(travessias=("travessias", "sum"),
                       travessias_teto=("travessias_teto", "sum"),
                       dentro=("dentro", "sum"), zmax=("zmax", "max"),
                       recolhas=("recolhas", "mean"),
                       run=("run", "first")).reset_index()
    por_modelo["campanhas"] = [campanhas_por_sha.get((s, c, a), "")
                               for s, c, a in zip(por_modelo["sha1"], por_modelo["cenario"],
                                                  por_modelo["algo"])]
    por_modelo["atravessa"] = por_modelo["travessias"] > 0
    por_modelo["preso"] = (por_modelo["dentro"] > 0) & ~por_modelo["atravessa"]

    linhas = ["# Travessias de paredes — modelos arquivados",
              "",
              "Gerado por `scripts/detetar_travessias.py` (%d episódios determinísticos por modelo)."
              % ok.groupby("modelo")["seed"].nunique().max(),
              "Um modelo **atravessa** se um agente entrou numa parede por um lado e saiu pelo oposto; "
              "«pelo teto» quando entrou a menos de 1 m do teto da esfera. Um modelo está **preso** "
              "se teve agentes dentro de paredes sem nunca as atravessar (junções em T). "
              "Modelos idênticos em várias pastas contam uma vez.",
              ""]

    # Por célula (cenário × algoritmo), agregando campanhas: o que a tese precisa.
    cel = por_modelo.groupby(["cenario", "algo"]).agg(
        modelos=("sha1", "size"), atravessam=("atravessa", "sum"),
        pelo_teto=("travessias_teto", lambda t: int((t > 0).sum())),
        presos=("preso", "sum"), zmax=("zmax", "max")).reset_index()
    linhas += ["## Por cenário e algoritmo (todas as campanhas, modelos únicos)", "",
               "| cenário | algo | modelos | atravessam | dos quais pelo teto | só presos | z máx |",
               "|---|---|---|---|---|---|---|"]
    for _, r in cel.sort_values(["atravessam", "cenario"], ascending=[False, True]).iterrows():
        marca = " **⚠**" if r["atravessam"] else ""
        linhas.append("| %s | %s | %d | %d%s | %d | %d | %.1f |" % (
            r["cenario"], r["algo"], r["modelos"], r["atravessam"], marca,
            r["pelo_teto"], r["presos"], r["zmax"]))

    # Os modelos que atravessam, um a um.
    af = por_modelo[por_modelo["atravessa"]].sort_values(["cenario", "campanhas", "run"])
    linhas += ["", "## Modelos que atravessam", "",
               "| cenário | algo | campanha(s) | run | travessias | pelo teto | z máx | rec/ep |",
               "|---|---|---|---|---|---|---|---|"]
    for _, r in af.iterrows():
        linhas.append("| %s | %s | %s | %s | %d | %d | %.1f | %.1f |" % (
            r["cenario"], r["algo"], r["campanhas"],
            "campeão" if pd.isna(r["run"]) else int(r["run"]),
            r["travessias"], r["travessias_teto"], r["zmax"], r["recolhas"]))

    n_mod = len(por_modelo)
    linhas += ["", "**%d modelos únicos (%d ficheiros): %d atravessam paredes (%d deles pelo teto), "
               "%d só ficam presos em junções.**" % (
                   n_mod, n_ficheiros, int(por_modelo["atravessa"].sum()),
                   int((por_modelo["travessias_teto"] > 0).sum()), int(por_modelo["preso"].sum()))]
    erros = df[df["erro"] != ""]
    if len(erros):
        linhas += ["", "Modelos não avaliados (%d): %s" % (
            len(erros), ", ".join(sorted(set(erros["modelo"]))[:20]))]
    return "\n".join(linhas) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episodios", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--so", nargs="*", help="só estas campanhas (nomes de CAMPANHAS)")
    ap.add_argument("--sem-runs", action="store_true", help="só os campeões, sem os _run")
    ap.add_argument("--cenario", nargs="*", help="só estes cenários")
    a = ap.parse_args()

    tarefas = []
    for nome, raiz in CAMPANHAS:
        if a.so and nome not in a.so:
            continue
        if not os.path.isdir(raiz):
            print("[--] %s: sem pasta de modelos (%s)" % (nome, os.path.relpath(raiz, RAIZ)))
            continue
        ms = modelos_de(raiz)
        if a.sem_runs:
            ms = [m for m in ms if m[2] is None]
        if a.cenario:
            ms = [m for m in ms if m[1] in a.cenario]
        for algo, cen, run, caminho in ms:
            tarefas.append((nome, algo, cen, run, caminho, a.episodios))
        print("[i] %s: %d modelos" % (nome, len(ms)))
    print("[i] %d modelos × %d episódios, %d processos" % (len(tarefas), a.episodios, a.jobs))

    os.makedirs(os.path.dirname(SAIDA_CSV), exist_ok=True)
    linhas, t0, feitos = [], time.time(), 0
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futuros = {ex.submit(tarefa, t): t for t in tarefas}
        for f in as_completed(futuros):
            t = futuros[f]
            try:
                res = f.result()
            except Exception as e:                       # noqa: BLE001
                res = [dict(campanha=t[0], algo=t[1].upper(), cenario=t[2], run=t[3],
                            modelo=os.path.relpath(t[4], RAIZ), erro="%s: %s" % (type(e).__name__, e))]
            linhas += res
            feitos += 1
            v = sum(r.get("travessias", 0) or 0 for r in res)
            d = sum(r.get("dentro", 0) or 0 for r in res)
            print("[%3d/%d] %-15s %-4s %-24s run=%-4s %s  (%.0f s)" % (
                feitos, len(tarefas), t[0], t[1].upper(), t[2], t[3] or "-",
                ("ATRAVESSA %d" % v) if v else ("preso %d" % d if d else "ok"),
                time.time() - t0), flush=True)
            # Grava a cada modelo: o total demora e um Ctrl+C não deve perder tudo.
            pd.DataFrame(linhas).to_csv(SAIDA_CSV, index=False)

    df = pd.DataFrame(linhas)
    if "erro" not in df.columns:
        df["erro"] = ""
    df["erro"] = df["erro"].fillna("")
    df.to_csv(SAIDA_CSV, index=False)
    md = resumo(df)
    with open(SAIDA_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print()
    print(md)
    print("[v] %s" % os.path.relpath(SAIDA_CSV, RAIZ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
