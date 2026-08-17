# -*- coding: utf-8 -*-
"""`ultima_sessao()` escolhe pela data do TREINO, não por quem lhe tocou por último.

Porque existe: escolhia com `max(..., key=os.path.getmtime)`, e o passo 2 do
`pos_campanha.py` copia a avaliação para dentro da sessão — o que atualiza o
mtime da pasta. A partir daí, essa passava a ser «a última» para sempre. A 5 ago
devolvia uma campanha de maio enquanto a da tese era de julho.

Isto interessa porque o passo 1 do `pos_campanha.py` RESTAURA OS MODELOS da
sessão escolhida para `results/models*`. Apontar à sessão errada é exatamente a
armadilha nº9 que o script existe para evitar.
"""
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import scripts.verificar_sessao as vs  # noqa: E402


def _montar(tmp_path, nomes):
    """Cria as pastas por ordem, para que o mtime cresça com a criação."""
    base = tmp_path / "graficos_tese"
    base.mkdir()
    for n in nomes:
        (base / n).mkdir()
        time.sleep(0.01)
    return base


def test_escolhe_a_data_mais_recente(tmp_path, monkeypatch):
    # A de julho é criada PRIMEIRO: pelo mtime perderia para a de maio.
    base = _montar(tmp_path, ["09-07-2026_12h52m", "27-05-2026_11h18m"])
    monkeypatch.setattr(vs, "SESSOES", str(base))
    assert os.path.basename(vs.ultima_sessao()) == "09-07-2026_12h52m"


def test_mexer_numa_pasta_antiga_nao_a_torna_a_ultima(tmp_path, monkeypatch):
    """O caso real: o pos_campanha escreve na pasta e atualiza-lhe o mtime."""
    base = _montar(tmp_path, ["09-07-2026_12h52m", "27-05-2026_11h18m"])
    monkeypatch.setattr(vs, "SESSOES", str(base))
    (base / "27-05-2026_11h18m" / "eval_summary.csv").write_text("x", encoding="utf-8")
    os.utime(base / "27-05-2026_11h18m", None)      # como se lhe tivessem tocado agora
    assert os.path.basename(vs.ultima_sessao()) == "09-07-2026_12h52m"


def test_mesma_data_dias_diferentes(tmp_path, monkeypatch):
    base = _montar(tmp_path, ["01-08-2026_09h00m", "01-08-2026_23h30m",
                              "31-07-2026_23h59m"])
    monkeypatch.setattr(vs, "SESSOES", str(base))
    assert os.path.basename(vs.ultima_sessao()) == "01-08-2026_23h30m"


def test_pasta_sem_data_no_nome_nao_ganha(tmp_path, monkeypatch):
    """`final_7d` e afins existem, mas não são candidatas a «a última»."""
    base = _montar(tmp_path, ["09-07-2026_12h52m"])
    (base / "9final_7d").mkdir()                    # começa por dígito, entra na lista
    os.utime(base / "9final_7d", None)
    monkeypatch.setattr(vs, "SESSOES", str(base))
    assert os.path.basename(vs.ultima_sessao()) == "09-07-2026_12h52m"


def test_sem_sessoes_devolve_none(tmp_path, monkeypatch):
    base = _montar(tmp_path, [])
    monkeypatch.setattr(vs, "SESSOES", str(base))
    assert vs.ultima_sessao() is None


# ── O contrato aplica-se ao que a campanha treinou, não a sete cenários ──────
def _sessao_com_eval(tmp_path, linhas):
    pasta = tmp_path / "16-08-2026_16h14m"
    pasta.mkdir()
    (pasta / "eval_by_run.csv").write_text(
        "Scenario,ScenarioLabel,Algorithm,Run,food_collected,success\n" + linhas,
        encoding="utf-8")
    return pasta


def test_escopo_vem_dos_dados_da_propria_sessao(tmp_path):
    """Uma campanha de 1 cenário × 1 algoritmo não deve o contrato dos sete.

    O caso real: correr o verificador à mão na sessão do mapa grande escrevia-lhe
    «30 artefactos essenciais em falta» — e o manifesto ficava no disco a acusar
    de incompleta uma campanha que estava completa.
    """
    pasta = _sessao_com_eval(tmp_path, "mapa_grande,Mapa Grande,GNN,1,0.0,False\n")
    algos, cens = vs.escopo_da_sessao(str(pasta))
    assert algos == ("gnn",)
    assert cens == ("mapa_grande",)
    itens = vs.contrato(algos, cens)
    essenciais = [n for n, e, _ in itens if e]
    assert not any("u_wall" in str(n) or "ppo" in str(n) for n in essenciais)


def test_sem_dados_para_inferir_devolve_none(tmp_path):
    pasta = tmp_path / "01-08-2026_09h00m"
    pasta.mkdir()
    assert vs.escopo_da_sessao(str(pasta)) == (None, None)


# ── E a mesma regra onde ela decide que modelos ficam ATIVOS ────────────────
import scripts.restaurar_modelos as rm  # noqa: E402


def _com_modelos(tmp_path, nomes):
    base = tmp_path / "graficos_tese"
    base.mkdir()
    for n in nomes:
        (base / n / "modelos").mkdir(parents=True)
        time.sleep(0.01)
    return base


def test_restaurar_escolhe_a_campanha_mais_recente(tmp_path, monkeypatch):
    base = _com_modelos(tmp_path, ["09-07-2026_12h52m", "04-07-2026_15h53m"])
    monkeypatch.setattr(rm, "GRAFICOS_DIR", str(base))
    assert os.path.basename(rm._sessions_with_models()[0]) == "09-07-2026_12h52m"


def test_tocar_numa_campanha_antiga_nao_lhe_da_os_modelos(tmp_path, monkeypatch):
    """O caso que interessa: isto decide o que fica em `results/models*`.

    Regenerar figuras ou copiar um CSV para dentro de uma campanha antiga
    atualiza-lhe o mtime — e com a ordenação antiga passava a ser ela a fornecer
    os modelos ativos. É a armadilha nº9: tudo o que se corre a seguir
    (escalabilidade, vídeos, visualizador) passaria a usar a campanha errada.
    """
    base = _com_modelos(tmp_path, ["09-07-2026_12h52m", "04-07-2026_15h53m"])
    monkeypatch.setattr(rm, "GRAFICOS_DIR", str(base))
    antiga = base / "04-07-2026_15h53m"
    (antiga / "eval_summary.csv").write_text("x", encoding="utf-8")
    os.utime(antiga, None)
    assert os.path.basename(rm._sessions_with_models()[0]) == "09-07-2026_12h52m"
