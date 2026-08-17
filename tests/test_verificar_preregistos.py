# -*- coding: utf-8 -*-
"""O verificador de pré-registos posto à prova: cada mutação tem de o fazer cair.

Um verificador que nunca falhou não está provado — está por ensaiar. O de
figuras deu por boa uma figura com um quadrado de 40x40 pixels pintado por cima,
e só um ensaio o revelou. Aqui muta-se o texto que ele lê e exige-se que acuse:
se uma mutação passar, é ela que descreve o que ele deixa passar em produção.

As mutações são todas de **texto** (os três documentos entram nas funções como
argumentos); os CSV das campanhas continuam a ser lidos do disco, que é o que
mantém o ensaio honesto — o desenho executado não é simulável.
"""
import importlib.util
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_spec = importlib.util.spec_from_file_location(
    "verificar_preregistos", os.path.join(RAIZ, "scripts", "verificar_preregistos.py"))
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)


def _correr(tex_sec, tex_main, pre):
    """Corre o bloco do mapa grande e devolve {id: estado}."""
    vp.linhas.clear()
    vp.falhas.clear()
    vp.mapa_grande(tex_sec, tex_main, pre)
    return {l[1]: l[4] for l in vp.linhas}


@pytest.fixture(scope="module")
def originais():
    return (vp.sem_comentarios(vp.SECCAO),
            vp.sem_comentarios(vp.MAIN),
            vp._ler(vp.PRE_MG))


def test_sem_mutacao_nao_ha_falhas(originais):
    estados = _correr(*originais)
    assert [k for k, v in estados.items() if v == "FALHA"] == []


def test_comentar_a_M2_e_apanhado(originais):
    """A armadilha da QI7: escrita, mas dentro de um comentário LaTeX."""
    sec, main, pre = originais
    mutado = sec.replace(r"\textbf{M2 (convergência, descritivo)",
                         r"% \textbf{M2 (convergência, descritivo)")
    assert mutado != sec
    # o verificador lê texto já sem comentários; simula-se o que ele veria
    mutado = vp.sem_comentarios_de_texto(mutado)
    estados = _correr(mutado, main, pre)
    assert estados["MG-M2"] == "FALHA"


def test_o_mapa_a_entrar_na_tabela_dos_sete_e_apanhado(originais):
    """Compromisso 3: o oitavo cenário não entra em tab:res_eval."""
    sec, main, pre = originais
    mutado = main.replace(r"\label{tab:res_eval}",
                          "Mapa Grande & 1,7 \\\\\n\\label{tab:res_eval}", 1)
    assert mutado != main
    estados = _correr(sec, mutado, pre)
    assert estados["MG-rep-3"] == "FALHA"


def test_emenda_do_cancelamento_em_falta_e_apanhada(originais):
    """Compromisso 5: um braço sem dados exige declaração datada."""
    sec, main, pre = originais
    mutado = pre.split("### 13 ago 2026 — o braço EXPLORATÓRIO")[0]
    assert "CANCELADO" not in mutado
    estados = _correr(sec, main, mutado)
    assert estados["MG-expl"] == "FALHA"


def test_invocar_o_braco_sem_ressalva_e_apanhado(originais):
    """A secção não pode falar do braço longo como se ele tivesse corrido."""
    sec, main, pre = originais
    mutado = sec.replace("não chegou a ser lançado", "produziu três execuções")
    assert mutado != sec
    estados = _correr(mutado, main, pre)
    assert estados["MG-expl-tex"] == "FALHA"


def test_numeracao_de_emendas_com_buraco_e_apanhada(originais):
    sec, main, pre = originais
    mutado = pre.replace("\n23. **O stream GNN", "\n42. **O stream GNN")
    assert mutado != pre
    estados = _correr(sec, main, mutado)
    assert estados["MG-rep-5a"] == "FALHA"


def test_M3_com_valor_errado_e_apanhado(originais):
    """O número da M3 na secção contra a coluna do eval_by_run.csv."""
    sec, main, pre = originais
    mutado = sec.replace("porta é aberta: GNN $43", "porta é aberta: GNN $73")
    assert mutado != sec
    estados = _correr(mutado, main, pre)
    assert estados["MG-M3-valor"] == "FALHA"


def test_comentarios_do_latex_nao_contam_como_texto():
    """`%` comenta; `\\%` é um por-cento e tem de sobreviver."""
    limpo = vp.sem_comentarios_de_texto(
        "visivel \\% ainda visivel % isto nao\n% linha inteira comentada\nfim")
    assert "ainda visivel" in limpo
    assert "isto nao" not in limpo
    assert "linha inteira" not in limpo
    assert "fim" in limpo
