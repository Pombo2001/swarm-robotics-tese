"""Testes da agregação de curvas entre runs (scripts/curvas_agregadas.py).

O que estes testes protegem: que a linha desenhada nas curvas de aprendizagem é
mesmo a média dos runs em cada ponto. A versão anterior (sns.lineplot sobre os x
crus) desenhava um run de cada vez sempre que as grelhas não coincidiam — o
teste `test_media_e_dos_runs_e_nao_de_um_deles` falha nessa versão.
"""
import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.curvas_agregadas import (  # noqa: E402
    curva_media_entre_runs,
    desenhar_curva_media,
    resolucao_grelha,
)


def _runs_desalinhados():
    """Dois runs com grelhas de x SEM um único ponto em comum (o caso real)."""
    a = pd.DataFrame({"Run": 1, "TrainingProgress": [0.0, 33.0, 67.0, 100.0],
                      "Score": [0.0, 30.0, 60.0, 90.0]})
    b = pd.DataFrame({"Run": 2, "TrainingProgress": [0.0, 25.0, 50.0, 75.0, 100.0],
                      "Score": [10.0, 20.0, 30.0, 40.0, 50.0]})
    return pd.concat([a, b], ignore_index=True)


def test_media_e_dos_runs_e_nao_de_um_deles():
    d = _runs_desalinhados()
    x, media, desvio, n_runs, _ = curva_media_entre_runs(d)
    assert n_runs == 2
    # Em x=50 o run 1 vale 45 (interpolado) e o run 2 vale 30 → média 37.5.
    i = int(np.argmin(np.abs(x - 50.0)))
    assert x[i] == 50.0, "a grelha deve conter o ponto médio"
    assert media[i] == 45.0 / 2 + 30.0 / 2
    # E o desvio nesse ponto não pode ser zero: os dois runs discordam.
    assert desvio[i] > 0


def test_nenhum_ponto_da_grelha_vem_de_um_run_so():
    """Todos os pontos da linha agregam TODOS os runs — era isto que faltava."""
    d = _runs_desalinhados()
    x, media, _, _, _ = curva_media_entre_runs(d)
    r1 = np.interp(x, [0, 33, 67, 100], [0, 30, 60, 90])
    r2 = np.interp(x, [0, 25, 50, 75, 100], [10, 20, 30, 40, 50])
    assert np.allclose(media, (r1 + r2) / 2)


def test_runs_identicos_dao_desvio_zero():
    a = pd.DataFrame({"Run": 1, "TrainingProgress": [0.0, 50.0, 100.0],
                      "Score": [1.0, 2.0, 3.0]})
    b = a.assign(Run=2)
    _, media, desvio, n_runs, _ = curva_media_entre_runs(
        pd.concat([a, b], ignore_index=True))
    assert n_runs == 2
    assert np.allclose(desvio, 0.0)
    assert np.isclose(media[0], 1.0) and np.isclose(media[-1], 3.0)


def test_run_com_um_unico_ponto_e_ignorado():
    """Um ponto não define curva; incluí-lo puxaria a média para um patamar."""
    bons = pd.DataFrame({"Run": 1, "TrainingProgress": [0.0, 100.0],
                         "Score": [0.0, 10.0]})
    coxo = pd.DataFrame({"Run": 2, "TrainingProgress": [50.0], "Score": [999.0]})
    _, media, _, n_runs, _ = curva_media_entre_runs(
        pd.concat([bons, coxo], ignore_index=True))
    assert n_runs == 1
    assert media.max() <= 10.0


def test_dataframe_vazio_nao_rebenta():
    vazio = pd.DataFrame(columns=["Run", "TrainingProgress", "Score"])
    x, media, desvio, n_runs, n_grelha = curva_media_entre_runs(vazio)
    assert x.size == 0 and n_runs == 0 and n_grelha == 0


def test_resolucao_segue_a_mediana_dos_runs_presa_aos_limites():
    # SAC real: ~9 pontos por run → grelha no mínimo, não 51.
    assert resolucao_grelha([9, 10, 9, 11, 9, 10, 9]) == 11
    # GNN real: centenas de pontos → grelha no máximo.
    assert resolucao_grelha([459, 474, 460, 466, 470, 461, 468]) == 51
    # PPO real: ~20 pontos → grelha a acompanhar.
    assert resolucao_grelha([19, 21, 20, 20, 21, 19, 20]) == 20
    assert resolucao_grelha([]) == 11


def test_banda_nao_desce_abaixo_de_zero_em_metrica_nao_negativa():
    """Runs bimodais dão desvio > média; a banda descia a fitness negativa."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    zeros = pd.DataFrame({"Run": 1, "TrainingProgress": [0.0, 100.0], "Score": [0.0, 0.0]})
    altos = pd.DataFrame({"Run": 2, "TrainingProgress": [0.0, 100.0], "Score": [0.0, 800.0]})
    fig, ax = plt.subplots()
    desenhar_curva_media(ax, pd.concat([zeros, altos], ignore_index=True), cor="#2e7d32")
    minimos = [c.get_paths()[0].vertices[:, 1].min() for c in ax.collections]
    assert min(minimos) >= 0.0
    plt.close(fig)


def test_banda_desce_quando_a_metrica_admite_negativos():
    """A recompensa episódica pode ser negativa (custo de energia) — não truncar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a = pd.DataFrame({"Run": 1, "TrainingProgress": [0.0, 100.0], "Score": [-50.0, 10.0]})
    b = pd.DataFrame({"Run": 2, "TrainingProgress": [0.0, 100.0], "Score": [-50.0, 900.0]})
    fig, ax = plt.subplots()
    desenhar_curva_media(ax, pd.concat([a, b], ignore_index=True), cor="#1565c0")
    minimos = [c.get_paths()[0].vertices[:, 1].min() for c in ax.collections]
    assert min(minimos) < 0.0
    plt.close(fig)


def test_grelha_cobre_o_orcamento_todo():
    d = _runs_desalinhados()
    x, _, _, _, n_grelha = curva_media_entre_runs(d, n_grelha=51)
    assert n_grelha == 51 and x[0] == 0.0 and x[-1] == 100.0


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            fn()
            print(f"[OK] {nome}")
    print("todos os testes passaram")
