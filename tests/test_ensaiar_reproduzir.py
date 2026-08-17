# -*- coding: utf-8 -*-
"""O ensaio do `REPRODUZIR.md`, ele próprio ensaiado.

Este verificador tem duas maneiras de ser inútil, e as duas apareceram enquanto
o escrevia: dar por em falta o que existe (os marcadores `{algo}` e `[_fail10]`
do documento tratados à letra, 36 falsos achados) e dar por presente o que não
existe. Os testes prendem as duas pontas.
"""
import importlib.util
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_spec = importlib.util.spec_from_file_location(
    "ensaiar_reproduzir", os.path.join(RAIZ, "scripts", "ensaiar_reproduzir.py"))
er = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(er)


@pytest.fixture(autouse=True)
def _limpo():
    er.falhas.clear()
    er.notas.clear()
    yield


def test_o_documento_real_bate_com_o_disco():
    assert er.main() == 0, er.falhas


def test_um_caminho_inventado_e_apanhado():
    er.caminhos("Ver `results/uma_pasta_que_nao_existe/x.csv` para o detalhe.")
    assert any("não existe" in f for f in er.falhas)


def test_um_script_inventado_e_apanhado():
    er.scripts("Correr `python scripts/analise_inventada.py` no fim.")
    assert any("analise_inventada.py" in f for f in er.falhas)


def test_marcadores_de_posicao_nao_dao_falsos_achados():
    """`{algo}` e `[_fail10]` são marcadores do documento, não sintaxe de shell."""
    er.caminhos("`results/evaluation/eval_{algo}_{cen}[_fail10].csv`")
    assert not er.falhas, er.falhas


def test_chavetas_com_virgula_continuam_a_ser_alternativas():
    assert set(er.expandir_chavetas("a/{x,y}/b")) == {"a/x/b", "a/y/b"}
    er.caminhos("`results/novelty_final/{uwall,bypass}/`")
    assert not er.falhas, er.falhas


def test_estado_desatualizado_e_apanhado():
    """Uma campanha que fechou e uma linha que continua a dizer «a correr»."""
    er.estado("A QI7 está ⏳ **a correr desde 3 ago** — GNN ~16 ago.")
    assert any("desatualizado" in f for f in er.falhas)


def test_um_script_que_nao_compila_e_apanhado(tmp_path, monkeypatch):
    mau = tmp_path / "scripts"
    mau.mkdir()
    (mau / "partido_de_proposito.py").write_text("def f(:\n", encoding="utf-8")
    monkeypatch.setattr(er, "RAIZ", str(tmp_path))
    er.scripts("Correr `partido_de_proposito.py`.")
    assert any("não compila" in f for f in er.falhas), er.falhas
