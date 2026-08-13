# -*- coding: utf-8 -*-
"""Reproduz os números da limitação «sobreposição entre spawn e barreira» (Gargalo).

Porque existe
-------------
A tese passou a afirmar sete coisas sobre o nascimento dos agentes no Gargalo:
que a faixa de sorteio é $y \\in [-12,-2]$ e a barreira ocupa $y \\in [-4,4]$;
que $17{,}9\\%$ das posições iniciais caem dentro do volume da barreira ($179$ de
$1000$); que a separação as resolve ao primeiro passo; que a resolução empurra
$159$ para sul, $20$ para a abertura e **nenhuma** para o lado oposto; e que a
distância geodésica ao ninho depois do primeiro passo é $45{,}3$\\,m para esses
agentes contra $21{,}2$\\,m para os restantes.

Cada um desses números é uma medição — e o que o plano de qualidade repete é que
os números têm rede e as afirmações sobre eles não. Esta é a rede: mede tudo no
simulador e compara com o que está escrito no `main.tex`, lendo os valores
esperados **do próprio ficheiro**. Um número mudado à mão na tese, ou uma
alteração à geometria do Gargalo, param aqui.

⚠️ A régua da distância é `env._potential` — a mesma que paga o `progress` da
recompensa, e portanto a que decide o que é «estar mais perto». Medir com a
euclidiana daria outro número (atravessa a barreira) e a afirmação da tese
deixaria de ser sobre o mundo em que os agentes treinaram.

Uso: .venv/Scripts/python.exe scripts/verificar_spawn_gargalo.py
"""
import os
import re
import sys
import tempfile

import numpy as np
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

from src.environment.swarm_env_3d import SwarmForagingEnv3D  # noqa: E402

TESE = os.path.join(RAIZ, "tese", "main.tex")
CFG = os.path.join(RAIZ, "configs", "foraging.yaml")
EPISODIOS = 50            # × 20 agentes = as 1000 posições que a tese cita
FALHAS = []


def compara(rotulo, medido, esperado, tol=0.05):
    ok = esperado is not None and abs(medido - esperado) <= tol
    print("  [%s] %-46s medido %8.2f   tese %8.2f"
          % ("v" if ok else "X", rotulo, medido,
             esperado if esperado is not None else float("nan")))
    if not ok:
        FALHAS.append(rotulo)


def _do_tex(padrao, texto):
    """Lê um número da tese. Devolve None se a frase mudou — que é uma falha,
    não um sucesso silencioso: um verificador que não encontra o que procura tem
    de dar erro, senão passa a verificar o vazio."""
    m = re.search(padrao, texto)
    return float(m.group(1).replace("{,}", ".").replace(",", ".")) if m else None


def medir():
    with open(CFG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["environment"]["classic_scenario"] = "bottleneck"
    tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                      encoding="utf-8")
    yaml.safe_dump(cfg, tmp)
    tmp.close()
    try:
        env = SwarmForagingEnv3D(tmp.name)
        # As paredes e os agentes só existem depois do primeiro reset — é lá que
        # o cenário se constrói.
        env.reset(seed=0)

        # Geometria: a faixa de nascimento está no código (não é configurável) e
        # a barreira mede-se nas paredes que o cenário constrói.
        y_barreira = max(w["size"][1] for w in env.walls) / 2.0

        dentro_total = agentes_total = 0
        norte = sul = abertura = presos = 0
        d_dentro, d_livres = [], []
        acoes = {a: np.zeros(env.action_space_val.shape[0]) for a in env.agents}

        for seed in range(EPISODIOS):
            env.reset(seed=seed)
            dentro = set()
            for i, p in enumerate(env.agent_positions):
                agentes_total += 1
                if any(np.all(np.abs(p - w["pos"]) < w["size"] / 2.0)
                       for w in env.walls):
                    dentro.add(i)
            dentro_total += len(dentro)

            env.step(acoes)
            for i in range(env.num_agents):
                d = env._potential(env.agent_positions[i])
                (d_dentro if i in dentro else d_livres).append(d)
            for i in dentro:
                p = env.agent_positions[i]
                if any(np.all(np.abs(p - w["pos"]) < w["size"] / 2.0)
                       for w in env.walls):
                    presos += 1
                elif p[1] > y_barreira:
                    norte += 1
                elif p[1] < -y_barreira:
                    sul += 1
                else:
                    abertura += 1
        return dict(
            y_barreira=y_barreira,
            pct=100.0 * dentro_total / agentes_total,
            dentro=dentro_total, total=agentes_total,
            norte=norte, sul=sul, abertura=abertura, presos=presos,
            d_dentro=float(np.median(d_dentro)),
            d_livres=float(np.median(d_livres)))
    finally:
        os.unlink(tmp.name)


def main():
    with open(TESE, encoding="utf-8") as fh:
        texto = fh.read()
    if "sobreposição entre a zona de nascimento" not in texto.lower() and \
       "Sobreposição entre a zona de nascimento" not in texto:
        print("[i] a limitação do spawn não está no main.tex — nada a verificar.")
        return 0

    m = medir()
    print("=" * 74)
    print("SPAWN vs BARREIRA no Gargalo  —  %d episódios × %d agentes"
          % (EPISODIOS, m["total"] // EPISODIOS))
    print("=" * 74)

    compara("semi-espessura da barreira em y (m)", m["y_barreira"],
            _do_tex(r"barreira ocupa \$y \\in \[-(\d+), \d+\]\$", texto), tol=0.01)
    compara("% de posições dentro da barreira", m["pct"],
            _do_tex(r"\\textbf\{\$(\d+\{,\}\d+)\\%\$\} das posições iniciais",
                    texto), tol=0.05)
    compara("posições dentro (contagem)", m["dentro"],
            _do_tex(r"\(\$(\d+)\$ de \$1000\$", texto), tol=0.5)
    compara("total de posições", m["total"],
            _do_tex(r"de \$(\d+)\$: \$50\$ episódios", texto), tol=0.5)
    compara("empurrados para sul", m["sul"],
            _do_tex(r"\$(\d+)\$ para sul", texto), tol=0.5)
    compara("empurrados para a abertura", m["abertura"],
            _do_tex(r"\$(\d+)\$ para a abertura central", texto), tol=0.5)
    compara("distância ao ninho, nasceram dentro (m)", m["d_dentro"],
            _do_tex(r"é de \$(\d+\{,\}\d+)\$\\,m \(mediana\)", texto), tol=0.05)
    compara("distância ao ninho, restantes (m)", m["d_livres"],
            _do_tex(r"contra \$(\d+\{,\}\d+)\$\\,m para os restantes", texto),
            tol=0.05)

    # As duas afirmações QUALITATIVAS da tese, que não são números mas são o que
    # sustenta a conclusão de que a sobreposição não favorece ninguém.
    ok_norte = m["norte"] == 0
    print("  [%s] %-46s medido %8d   tese %8d"
          % ("v" if ok_norte else "X", "empurrados para o lado oposto", m["norte"], 0))
    if not ok_norte:
        FALHAS.append("empurrados para o lado oposto")
    ok_presos = m["presos"] == 0
    print("  [%s] %-46s medido %8d   tese %8d"
          % ("v" if ok_presos else "X", "ainda dentro da barreira ao passo 1",
             m["presos"], 0))
    if not ok_presos:
        FALHAS.append("ainda dentro da barreira ao passo 1")

    print("=" * 74)
    if FALHAS:
        print("%d valor(es) NÃO batem: %s" % (len(FALHAS), ", ".join(FALHAS)))
        return 1
    print("Os 10 valores da limitação do spawn batem com o simulador ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
