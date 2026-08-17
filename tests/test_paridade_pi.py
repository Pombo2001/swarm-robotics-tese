# -*- coding: utf-8 -*-
"""A paridade Pi ↔ local, e o instrumento que a mede, postos à prova.

O verificador falha de uma maneira perigosa: se a instrumentação deixar de ver
as leituras, ele anuncia «tudo coberto» sobre um conjunto vazio. E falha de
outra, mais subtil: o array de caminhos do `atualizar_pi.sh` está enterrado em
trinta linhas de comentário que **citam caminhos**, e a primeira versão contava
esses como enviados.
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_spec = importlib.util.spec_from_file_location(
    "verificar_paridade_pi", os.path.join(RAIZ, "scripts", "verificar_paridade_pi.py"))
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)


_SCRIPT_FALSO = """#!/usr/bin/env bash
if [ $# -gt 0 ]; then
    CAMINHOS=("$@")
else
    # Um comentário que fala de results/inventado, com toda a boa intenção:
    #   · results/tambem_inventado — explicado aqui, mas NÃO enviado
    CAMINHOS=(dashboard results/estatisticas
              results/mega_1mes/*/evaluation
              Tese/main.tex "${FIGS[@]}")
fi
"""


def _script(tmp_path, texto=_SCRIPT_FALSO):
    p = tmp_path / "atualizar_pi.sh"
    p.write_text(texto, encoding="utf-8")
    return str(p)


def test_comentarios_nao_contam_como_caminhos_enviados(tmp_path, monkeypatch):
    monkeypatch.setattr(vp, "SCRIPT_PI", _script(tmp_path))
    caminhos = vp.caminhos_do_script()
    assert "results/inventado" not in caminhos
    assert "results/tambem_inventado" not in caminhos
    assert "results/estatisticas" in caminhos
    assert vp.coberto("results/inventado/x.csv", caminhos) is None


def test_globs_do_array_sao_expandidos(tmp_path, monkeypatch):
    monkeypatch.setattr(vp, "SCRIPT_PI", _script(tmp_path))
    caminhos = vp.caminhos_do_script()
    reais = [c for c in caminhos if c.startswith("results/mega_1mes/")]
    assert reais, "o glob results/mega_1mes/*/evaluation não foi expandido"
    assert vp.coberto("results/mega_1mes/mega_A_fase1/evaluation/eval_by_run.csv",
                      caminhos)


def test_uma_leitura_fora_do_delta_e_apanhada(tmp_path, monkeypatch):
    monkeypatch.setattr(vp, "SCRIPT_PI", _script(tmp_path))
    caminhos = vp.caminhos_do_script()
    assert vp.coberto("results/estado_f2.json", caminhos) is None
    assert vp.isento("results/estado_f2.json") is None


def test_modelos_de_qualquer_campanha_ficam_isentos():
    """`models`, `models_7d`, `models_ppo`, `models_f2_gnn` — a mesma isenção."""
    for pasta in ("results/models/gnn.pth", "results/models_7d/x.pth",
                  "results/models_ppo/ppo.zip", "results/models_f2_gnn/a.pth"):
        assert vp.isento(pasta), pasta
    assert vp.isento("results/estatisticas/x.csv") is None


def test_a_instrumentacao_ve_mesmo_as_leituras():
    """A guarda contra o «tudo coberto» sobre um conjunto vazio."""
    lidos = vp.recolher_leituras()
    assert len(lidos) >= 100, ("só %d leituras: o patching de open/exists/glob "
                               "deixou de ver o que as vistas fazem" % len(lidos))
    assert any(c.endswith(".csv") for c in lidos)


def test_o_delta_cobre_tudo_o_que_as_vistas_leem():
    assert vp.main() == 0
