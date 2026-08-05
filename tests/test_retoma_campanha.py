# -*- coding: utf-8 -*-
"""A retoma de uma campanha não apaga o que já estava feito.

Porque importa agora: o `mapa_streamF2.sh` relança com `--resume` até duas vezes
se a sentinela de conclusão não aparecer. O F2 do GNN são 21 runs × 13 h; um
crash ao run 15 seguido de uma retoma que apagasse os 14 anteriores custaria a
campanha — e o hard stop é 22 ago.

O `_merge_save` é a peça que garante isto: substitui no CSV apenas as combinações
presentes nos dados novos e mantém as outras. O docstring diz-se «essencial na
gravação incremental e na retoma pós-crash»; nunca tinha sido testado.
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from scripts.run_experiments import _merge_save  # noqa: E402


def _linhas(cenario, algo, runs, valor=1.0):
    return pd.DataFrame([{"Scenario": cenario, "Algorithm": algo, "Run": r,
                          "BestScore": valor + r} for r in runs])


def test_gravar_um_run_nao_apaga_os_anteriores(tmp_path):
    p = str(tmp_path / "all_best_scores.csv")
    _merge_save(_linhas("mapa_grande", "GNN", [1, 2, 3]), p)
    _merge_save(_linhas("mapa_grande", "GNN", [4]), p)
    d = pd.read_csv(p)
    assert sorted(d["Run"]) == [1, 2, 3, 4], f"perdeu runs: {d['Run'].tolist()}"


def test_regravar_o_mesmo_run_substitui_em_vez_de_duplicar(tmp_path):
    p = str(tmp_path / "all_best_scores.csv")
    _merge_save(_linhas("mapa_grande", "GNN", [1, 2], valor=1.0), p)
    _merge_save(_linhas("mapa_grande", "GNN", [2], valor=100.0), p)
    d = pd.read_csv(p)
    assert len(d) == 2, f"duplicou linhas: {d.to_dict('records')}"
    assert float(d[d["Run"] == 2]["BestScore"].iloc[0]) == 102.0, "não substituiu"


def test_algoritmos_e_cenarios_nao_se_pisam(tmp_path):
    p = str(tmp_path / "all_best_scores.csv")
    _merge_save(_linhas("mapa_grande", "GNN", [1, 2]), p)
    _merge_save(_linhas("mapa_grande", "PPO", [1, 2]), p)
    _merge_save(_linhas("u_wall", "GNN", [1]), p)
    d = pd.read_csv(p)
    assert len(d) == 5
    assert set(d["Algorithm"]) == {"GNN", "PPO"}
    assert set(d["Scenario"]) == {"mapa_grande", "u_wall"}


def test_a_escrita_e_atomica(tmp_path):
    """Grava por ficheiro temporário + `os.replace`: um crash a meio não deixa
    um CSV truncado no sítio do bom."""
    p = str(tmp_path / "all_best_scores.csv")
    _merge_save(_linhas("mapa_grande", "GNN", [1]), p)
    assert os.path.exists(p)
    assert not os.path.exists(p + ".tmp"), "ficou um temporário para trás"


def test_dados_vazios_nao_apagam_o_ficheiro(tmp_path):
    """Um run que não produza linhas não pode levar o CSV à frente."""
    p = str(tmp_path / "all_best_scores.csv")
    _merge_save(_linhas("mapa_grande", "GNN", [1, 2]), p)
    _merge_save(pd.DataFrame(), p)
    d = pd.read_csv(p)
    assert len(d) == 2, "um DataFrame vazio apagou dados"


def test_csv_corrompido_nao_perde_os_dados_novos(tmp_path):
    """Se o CSV antigo não for legível, os dados novos gravam na mesma.

    É o ramo `except` do `_merge_save` — o que resta depois de um disco cheio ou
    de uma escrita interrompida por um `kill`.
    """
    p = str(tmp_path / "all_best_scores.csv")
    with open(p, "w", encoding="utf-8") as f:
        f.write("isto\nnão\né,um,csv,válido\n\x00\x00")
    _merge_save(_linhas("mapa_grande", "GNN", [1]), p)
    d = pd.read_csv(p)
    assert len(d) == 1 and int(d["Run"].iloc[0]) == 1
