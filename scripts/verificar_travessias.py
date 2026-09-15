# -*- coding: utf-8 -*-
"""Reproduz os números da limitação «duas costuras na física das paredes».

Porque existe
A tese passou a afirmar, nas Limitações, quantos modelos arquivados atravessam
paredes e onde: 343 modelos únicos em 771 ficheiros, 3 episódios cada, 11 a
atravessar (3 pelo teto), 12 presos, 8 dos 16 do GNN nas Quatro Salas, 3 dos
70 da campanha final (execuções 1, 4 e 6), 55,7 contra 60,3 recolhas/ep, 335
travessias do campeão adaptativo. Cada um é uma medição do
`scripts/detetar_travessias.py`, e este verificador recalcula-os todos a
partir do CSV que ele grava e compara-os com o que o `main.tex` diz — lendo
os valores esperados do próprio ficheiro, como o verificador do spawn no
Gargalo. Um número mudado à mão, ou o detetor corrido de novo com outro
resultado, param aqui.

Não reproduz os episódios (são ~20 min): confere o texto contra o CSV. Se o
CSV faltar, diz o que falta e falha.

Uso: .venv/Scripts/python.exe scripts/verificar_travessias.py
"""
from __future__ import annotations

import os
import re
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESE = os.path.join(RAIZ, "Tese", "main.tex")
CSV = os.path.join(RAIZ, "results", "estatisticas", "travessias_paredes.csv")
FALHAS: list[str] = []


def compara(rotulo, medido, esperado, tol=0.05):
    ok = esperado is not None and abs(medido - esperado) <= tol
    print("  [%s] %-52s medido %8.1f   tese %8s"
          % ("v" if ok else "X", rotulo, medido,
             ("%.1f" % esperado) if esperado is not None else "—"))
    if not ok:
        FALHAS.append(rotulo)


def _num(txt: str) -> float:
    return float(txt.replace("{,}", ".").replace(",", "."))


def _do_tex(padrao: str, texto: str):
    m = re.search(padrao, texto, flags=re.S)
    return _num(m.group(1)) if m else None


def medir() -> dict:
    d = pd.read_csv(CSV)
    d["erro"] = d["erro"].fillna("")
    ok = d[d["erro"] == ""].copy()
    n_ep = int(ok.groupby("modelo")["seed"].nunique().max())
    # O mesmo ficheiro em várias pastas (as fases copiavam results/models) dá
    # linhas repetidas; somá-las inflacionava as travessias 5× no campeão A1.
    ok = ok.drop_duplicates(["sha1", "cenario", "algo", "seed"], keep="first")
    # Um modelo = um ficheiro pelo conteúdo, num cenário.
    m = ok.groupby(["sha1", "cenario", "algo"]).agg(
        trav=("travessias", "sum"), teto=("travessias_teto", "sum"),
        dentro=("dentro", "sum")).reset_index()
    m["atravessa"] = m["trav"] > 0
    m["preso"] = (m["dentro"] > 0) & ~m["atravessa"]
    fr = m[(m["cenario"] == "four_rooms") & (m["algo"] == "GNN")]
    uw = m[(m["cenario"] == "u_wall") & m["atravessa"]]
    by = m[(m["cenario"] == "cooperative_door_bypass") & m["atravessa"]]

    # A campanha final, por modelo (ficheiro).
    f = ok[ok["campanha"] == "final_7d"].groupby(["modelo", "cenario", "algo", "run"],
                                                 dropna=False).agg(
        trav=("travessias", "sum"), rec=("recolhas", "mean")).reset_index()
    f_fr = f[(f["cenario"] == "four_rooms") & (f["algo"] == "GNN") & f["run"].notna()]
    afetadas = f_fr[f_fr["trav"] > 0]
    limpas = f_fr[f_fr["trav"] == 0]

    # O campeão adaptativo das Quatro Salas (o mesmo ficheiro em várias pastas).
    camp = ok[(ok["campanha"] == "adaptativo_A1") & (ok["cenario"] == "four_rooms")
              & (ok["algo"] == "GNN") & ok["run"].isna()]
    return {
        "modelos_unicos": int(len(m)),
        "ficheiros": int(d[d["erro"] == ""]["modelo"].nunique()),
        "episodios": n_ep,
        "atravessam": int(m["atravessa"].sum()),
        "pelo_teto": int((m["teto"] > 0).sum()),
        "presos": int(m["preso"].sum()),
        "ppo_sac_atravessam": int(m[m["algo"].isin(["PPO", "SAC"])]["atravessa"].sum()),
        "fr_gnn_modelos": int(len(fr)),
        "fr_gnn_atravessam": int(fr["atravessa"].sum()),
        "uw_modelos": int(len(uw)), "uw_travessias": int(uw["trav"].sum()),
        "by_modelos": int(len(by)), "by_travessias": int(by["trav"].sum()),
        "final_modelos": int(len(f)),
        "final_atravessam": int((f["trav"] > 0).sum()),
        "final_runs": sorted(int(r) for r in afetadas["run"]),
        "rec_afetadas": float(afetadas["rec"].mean()) if len(afetadas) else float("nan"),
        "rec_limpas": float(limpas["rec"].mean()) if len(limpas) else float("nan"),
        "n_limpas": int(len(limpas)),
        "campeao_adaptativo": int(camp["travessias"].sum()),
        "cenarios_limpos": [c for c in ("none", "bottleneck", "cooperative_door",
                                        "cooperative_perception", "mapa_grande")
                            if int(m[m["cenario"] == c]["atravessa"].sum()) == 0],
    }


def main() -> int:
    if not os.path.exists(CSV):
        print("[X] falta %s — correr scripts/detetar_travessias.py" % os.path.relpath(CSV, RAIZ))
        return 1
    with open(TESE, encoding="utf-8") as fh:
        tex = fh.read()
    if "costuras na física das paredes" not in tex:
        print("[i] a limitação das travessias não está no main.tex — nada a verificar.")
        return 0
    ini = tex.index("costuras na física das paredes")
    par = tex[ini:ini + 6000]
    r = medir()
    print("Limitação «duas costuras na física das paredes» vs travessias_paredes.csv")
    compara("episódios por modelo", r["episodios"], _do_tex(r"reproduziram-se \$(\d+)\$ episódios", par))
    compara("modelos únicos", r["modelos_unicos"], _do_tex(r"cada um dos \$(\d+)\$ modelos", par))
    compara("ficheiros", r["ficheiros"], _do_tex(r"os \$(\d+)\$ ficheiros", par))
    compara("modelos que atravessam", r["atravessam"], _do_tex(r"\$(\d+)\$ modelos atravessam", par))
    compara("dos quais pelo teto", r["pelo_teto"], _do_tex(r"\(\$(\d+)\$ deles pelo teto\)", par))
    compara("modelos presos", r["presos"], _do_tex(r"e \$(\d+)\$ apenas ficam presos", par))
    compara("PPO/SAC a atravessar (a tese diz nenhum)", r["ppo_sac_atravessam"], 0)
    compara("cenários sem travessias (5 nomeados)", len(r["cenarios_limpos"]), 5)
    compara("GNN Quatro Salas: atravessam", r["fr_gnn_atravessam"],
            _do_tex(r"\$(\d+)\$ dos \$\d+\$ modelos únicos do GNN", par))
    compara("GNN Quatro Salas: modelos únicos", r["fr_gnn_modelos"],
            _do_tex(r"\$\d+\$ dos \$(\d+)\$ modelos únicos do GNN", par))
    compara("Muro em U: modelos", r["uw_modelos"], _do_tex(r"Muro em U \(\$(\d+)\$ modelos", par))
    compara("Muro em U: travessias", r["uw_travessias"], _do_tex(r"Muro em U \(\$\d+\$ modelos, \$(\d+)\$ travessias", par))
    compara("Porta com Alternativa: modelos", r["by_modelos"], _do_tex(r"Porta com Alternativa \(\$(\d+)\$ modelo", par))
    compara("Porta com Alternativa: travessias", r["by_travessias"], _do_tex(r"Porta com Alternativa \(\$\d+\$ modelo, \$(\d+)\$ travessia", par))
    compara("campanha final: modelos", r["final_modelos"], _do_tex(r"\$\d+\$ dos \$(\d+)\$ modelos atravessam", par))
    compara("campanha final: atravessam", r["final_atravessam"], _do_tex(r"\$(\d+)\$ dos \$\d+\$ modelos atravessam", par))
    m = re.search(r"as execuções \$(\d+)\$, \$(\d+)\$ e \$(\d+)\$ do GNN", par)
    runs_tese = sorted(int(x) for x in m.groups()) if m else None
    okr = runs_tese == r["final_runs"]
    print("  [%s] %-52s medido %8s   tese %8s" % ("v" if okr else "X", "campanha final: execuções afetadas",
                                                    r["final_runs"], runs_tese))
    if not okr:
        FALHAS.append("execuções afetadas")
    compara("recolhas/ep das execuções afetadas", r["rec_afetadas"],
            _do_tex(r"em média \$([\d{,}]+)\$ chegadas/ep", par), tol=0.06)
    compara("recolhas/ep das execuções limpas", r["rec_limpas"],
            _do_tex(r"contra \$([\d{,}]+)\$ das", par), tol=0.06)
    compara("número de execuções limpas", r["n_limpas"], _do_tex(r"das (\w+) execuções limpas", par.replace("quatro", "4")))
    compara("campeão adaptativo: travessias", r["campeao_adaptativo"],
            _do_tex(r"\(\$(\d+)\$ travessias em \$\d+\$\)", par))
    if FALHAS:
        print("%d divergência(s): %s" % (len(FALHAS), "; ".join(FALHAS)))
        return 1
    print("OK — os números da limitação batem com o CSV do detetor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
