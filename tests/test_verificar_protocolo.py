# -*- coding: utf-8 -*-
"""O verificador de protocolo posto à prova: uma campanha inventada tem de cair.

Os números de protocolo — «7 execuções», «195 minutos», «20 episódios» — são os
que a dissertação mais repete e os que menos tinham quem os conferisse: 124
tokens no maior grupo do `COBERTURA_VERIFICADOR.md`. Um erro neles descreve uma
campanha que não aconteceu sem desalinhar nenhuma tabela.

Estes ensaios cobrem as duas pontas: uma campanha inventada é apanhada, e as
frases legítimas (contagens de resultado, medições auxiliares) não geram
achados.
"""
import importlib.util
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_spec = importlib.util.spec_from_file_location(
    "verificar_protocolo", os.path.join(RAIZ, "scripts", "verificar_protocolo.py"))
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)


@pytest.fixture(autouse=True)
def _limpo():
    vp.falhas.clear()
    yield


def test_a_dissertacao_bate_com_as_campanhas():
    assert vp.main() == 0, vp.falhas


def test_execucoes_inventadas_sao_apanhadas():
    vp.verificar(r"A campanha correu com $9$ \textit{runs} por braço.")
    assert any("execuções = 9" in f for f in vp.falhas), vp.falhas


def test_orcamento_inventado_e_apanhado():
    """O erro que não desalinha nada: 300 minutos onde nenhum braço os teve."""
    vp.verificar("Cada execução dispôs de 300 minutos de treino.")
    assert any("minutos = 300" in f for f in vp.falhas), vp.falhas


def test_episodios_inventados_sao_apanhados():
    vp.verificar(r"A avaliação determinística usa $17$ episódios por execução.")
    assert any("episódios = 17" in f for f in vp.falhas), vp.falhas


def test_totais_que_sao_produto_do_protocolo_passam():
    """140 = 7×20, 420 = 21×20, 1680 = 21×20×4 — legítimos, e não são medidos."""
    vp.verificar(r"São $140$ episódios por célula e $1680$ episódios nas quatro "
                 r"condições, sobre $7$ \textit{runs}.")
    assert not vp.falhas, vp.falhas


def test_contagem_de_resultado_nao_e_confundida_com_a_campanha():
    """«4 execuções convergentes» é resultado, não o tamanho da campanha."""
    vp.verificar(r"Reproduzem exatamente as $4$ execuções convergentes.")
    assert not vp.falhas, vp.falhas


def test_o_n_da_revisao_sistematica_e_medido_do_screening():
    vp.verificar(r"o corpo da revisão ($n=58$)")
    assert not vp.falhas, vp.falhas
    vp.verificar(r"o corpo da revisão ($n=59$)")
    assert any("n = 59" in f for f in vp.falhas), vp.falhas


def test_comentarios_do_latex_nao_sao_lidos():
    limpo = vp.sem_comentarios(os.path.join(RAIZ, "Tese", "main.tex"))
    assert "%" not in limpo.replace("\\%", "")
