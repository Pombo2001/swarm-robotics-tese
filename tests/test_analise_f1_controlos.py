"""
test_analise_f1_controlos.py — o veredicto do F1 não pode mudar por acidente
O `analise_f1_controlos.py` produz a leitura oficial da QI7: pega nas quatro
condições do F1 e decide, por cada controlo, se a causa está excluída ou se o
zero-shot de topologia está confundido com ela. Essa decisão não é um juízo
do script — é a regra que o `PRE_REGISTO_MAPA_GRANDE.md` §3 fixou antes de haver
dados:

  · controlo igual à natural  ⇒ causa excluída, reporta-se só a natural;
  · controlo diferente        ⇒ é isso que se reporta;
  · e, textualmente: *"um controlo que ressuscite os campeões NÃO salva a leitura
    'a topologia é dura': desmente-a."*

Um script que decide isto é exatamente o género de coisa que ninguém volta a ler
depois de funcionar uma vez. Estes testes prendem os três veredictos a exemplos
onde a resposta certa é conhecida por construção, para que uma alteração futura
que os troque falhe em vez de passar despercebida.

Testa também a guarda de `--saida`, que nasceu de um erro real: a 28 jul 2026, ao
validar o próprio script com um CSV sintético, o veredicto falso foi escrito
na pasta que a tese cita. Apagado a seguir — mas a lição é que um script de
análise com destino fixo não distingue um ensaio de uma corrida boa.

Corre como os outros testes do projeto (script autónomo, também vale por pytest):
    .venv/Scripts/python.exe tests/test_analise_f1_controlos.py
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.analise_f1_controlos import (  # noqa: E402
    NATURAL, comparar, grelha, verificar, veredicto)
from src.scenarios import THESIS_SCENARIOS  # noqa: E402

ALGOS = ("GNN", "PPO", "SAC")
DIGITAL_BASE = "267a7b547aed"        # a real, medida na torre e no servidor
DIGITAL_SEM_OBST = "dd557291eaa5"    # a real da condição sem obstáculos


def _episodios(valores, norm="mapa", controlo="base", digital=DIGITAL_BASE,
               n=20, data="2026-07-03T10:48:00"):
    """CSV sintético no formato do eval_zeroshot.

    `valores` é {(algo, origem): recolhas/ep}; cada célula vira n episódios com
    esse valor exato, para a média por célula ser previsível ao cêntimo.
    """
    linhas = []
    for (algo, origem), v in valores.items():
        for _ in range(n):
            linhas.append({
                "food_collected": float(v), "task_reward": 0.0,
                "total_reward": 0.0, "episode_length": 2000,
                "success": bool(v > 0), "Algorithm": algo, "Origem": origem,
                "Mapa": "mapa_grande", "NormObs": norm, "Controlo": controlo,
                "env_hash": digital,
                "ModeloPath": "results/models_7d/models/gnn_3d_best.pth",
                "ModeloData": data, "ModeloFonte": "meta"})
    return pd.DataFrame(linhas)


def _grelha_realista():
    """Uma condição natural com o padrão do F1 real: poucas células vivas."""
    v = {}
    for algo in ALGOS:
        for origem in THESIS_SCENARIOS:
            v[(algo, origem)] = 0.0
    v[("GNN", "none")] = 7.2
    v[("SAC", "none")] = 19.6
    v[("SAC", "cooperative_door")] = 21.6
    v[("GNN", "cooperative_perception")] = 17.3
    v[("SAC", "cooperative_perception")] = 15.8
    v[("GNN", "cooperative_door_bypass")] = 2.5
    v[("SAC", "cooperative_door_bypass")] = 20.2
    return v


def _mudo(f, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = f(*a, **k)
    return r, buf.getvalue()


# os três veredictos

def test_controlo_que_ressuscita_diverge():
    """Uma célula a zero que passa a recolher DESMENTE 'a topologia é dura'."""
    nat = _grelha_realista()
    ctl = dict(nat)
    ctl[("GNN", "bottleneck")] = 15.0      # estava a zero
    ctl[("PPO", "u_wall")] = 11.0          # idem
    d = pd.concat([_episodios(nat),
                   _episodios(ctl, norm="treino")], ignore_index=True)

    r = comparar(d, ("treino", "base"), "escala")
    assert r["ressuscitadas"] == 2, r["ressuscitadas"]
    assert r["mortas"] == 0, r["mortas"]
    texto = veredicto(r)
    assert texto.startswith("DIVERGE"), texto
    assert "desmente" in texto, texto
    print("OK  controlo que ressuscita células ⇒ DIVERGE (e desmente a leitura)")


def test_controlo_identico_exclui_a_causa():
    """Igual à natural ⇒ causa excluída, o controlo vai para apêndice."""
    nat = _grelha_realista()
    d = pd.concat([_episodios(nat),
                   _episodios(nat, controlo="sem_obstaculos",
                              digital=DIGITAL_SEM_OBST)], ignore_index=True)

    r = comparar(d, ("mapa", "sem_obstaculos"), "sem obstáculos")
    assert r["ressuscitadas"] == 0 and r["mortas"] == 0
    assert abs(r["media_natural"] - r["media_controlo"]) < 1e-9
    texto = veredicto(r)
    assert "EXCLUÍDA" in texto, texto
    print("OK  controlo idêntico ⇒ causa EXCLUÍDA")


def test_divergencia_so_em_magnitude():
    """Sem ressuscitar nada, mas com as células vivas a mudar de valor:
    a causa afeta o QUANTO se recolhe, não o SE se recolhe."""
    nat = _grelha_realista()
    ctl = {k: (v * 2.5 if v > 0 else 0.0) for k, v in nat.items()}
    d = pd.concat([_episodios(nat),
                   _episodios(ctl, controlo="sem_porta_obs")], ignore_index=True)

    r = comparar(d, ("mapa", "sem_porta_obs"), "sem features da porta")
    assert r["ressuscitadas"] == 0, "não devia ressuscitar nenhuma"
    assert r["media_controlo"] > r["media_natural"]
    texto = veredicto(r)
    assert "magnitude" in texto, texto
    print("OK  só a magnitude muda ⇒ DIVERGE em magnitude, sem ressuscitar")


def test_celula_que_morre_conta_como_divergencia():
    """O caso simétrico: o controlo MATA uma célula viva. Também é divergir —
    e é o sinal de que o controlo mexeu em mais do que devia."""
    nat = _grelha_realista()
    ctl = dict(nat)
    ctl[("SAC", "cooperative_door")] = 0.0
    d = pd.concat([_episodios(nat),
                   _episodios(ctl, norm="treino")], ignore_index=True)

    r = comparar(d, ("treino", "base"), "escala")
    assert r["mortas"] == 1, r["mortas"]
    assert r["ressuscitadas"] == 0
    print("OK  célula que morre no controlo é contada (mortas=1)")


# integridade: o que tem de ser visto ANTES dos números

def test_avisa_se_a_condicao_tem_duas_digitais():
    """Dois mapas no mesmo ficheiro deixam de ser comparação emparelhada."""
    nat = _grelha_realista()
    a = _episodios(nat)
    b = _episodios(nat, digital="outra_digital")
    avisos, _ = _mudo(verificar, pd.concat([a, b], ignore_index=True))
    assert any("impressões digitais" in x for x in avisos), avisos
    print("OK  duas digitais na mesma condição ⇒ aviso")


def test_avisa_se_sem_obstaculos_nao_mudou_o_mundo():
    """Tirar 106 obstáculos TEM de mudar a digital. Se não mudou, o controlo
    não foi aplicado — e a conclusão 'igual à natural' seria trivialmente
    verdadeira pela pior razão possível."""
    nat = _grelha_realista()
    d = pd.concat([_episodios(nat),
                   _episodios(nat, controlo="sem_obstaculos",
                              digital=DIGITAL_BASE)],   # <- a mesma, errado
                  ignore_index=True)
    avisos, _ = _mudo(verificar, d)
    assert any("obstáculos não foram removidos" in x for x in avisos), avisos
    print("OK  'sem obstáculos' com a digital da natural ⇒ aviso")


def test_avisa_se_a_escala_mudou_o_mundo():
    """O inverso: a escala só muda a LEITURA do mundo, nunca o mundo."""
    nat = _grelha_realista()
    d = pd.concat([_episodios(nat),
                   _episodios(nat, norm="treino", digital=DIGITAL_SEM_OBST)],
                  ignore_index=True)
    avisos, _ = _mudo(verificar, d)
    assert any("MESMA digital da natural" in x for x in avisos), avisos
    print("OK  'escala' com digital diferente ⇒ aviso")


def test_avisa_campeoes_de_fora_da_campanha():
    """A armadilha nº9 outra vez: modelos de 24 jun anulam a corrida."""
    nat = _grelha_realista()
    d = _episodios(nat, data="2026-06-24T23:01:00")
    avisos, _ = _mudo(verificar, d)
    assert any("FORA da campanha" in x for x in avisos), avisos
    print("OK  campeões de fora da campanha de 7 dias ⇒ aviso")


def test_avisa_celulas_incompletas():
    nat = {("GNN", "none"): 7.2}
    d = _episodios(nat, n=13)
    avisos, _ = _mudo(verificar, d)
    assert any("menos de 20" in x for x in avisos), avisos
    print("OK  célula com menos de 20 episódios ⇒ aviso")


def test_grelha_reproduz_medias_e_sucesso():
    nat = _grelha_realista()
    g = grelha(_episodios(nat), NATURAL)
    assert abs(g.loc["Sandbox", "GNN"] - 7.2) < 1e-9
    assert abs(g.loc["Sandbox", "GNN_sucesso"] - 100.0) < 1e-9
    assert abs(g.loc["Gargalo", "PPO"]) < 1e-9
    assert abs(g.loc["Gargalo", "PPO_sucesso"]) < 1e-9
    print("OK  a grelha reproduz médias e taxas de sucesso por célula")


# a guarda que nasceu de um erro real

def test_csv_de_fora_exige_saida():
    """Correr com um CSV de teste NÃO pode escrever na pasta que a tese cita."""
    tmp = tempfile.mkdtemp(prefix="f1teste_")
    try:
        fp = os.path.join(tmp, "zeroshot_sintetico.csv")
        _episodios(_grelha_realista()).to_csv(fp, index=False)
        r = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "scripts",
                                          "analise_f1_controlos.py"),
             "--csv", fp, "--sem-figura"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
            encoding="utf-8", errors="replace")
        assert r.returncode != 0, "devia ter abortado"
        saida = (r.stdout + r.stderr)
        assert "--saida" in saida, saida[-400:]

        # e com --saida corre, escrevendo no sítio indicado
        out = os.path.join(tmp, "out")
        r2 = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "scripts",
                                          "analise_f1_controlos.py"),
             "--csv", fp, "--saida", out, "--sem-figura"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
            encoding="utf-8", errors="replace")
        assert r2.returncode == 0, (r2.stdout + r2.stderr)[-400:]
        assert os.path.exists(os.path.join(out, "f1_veredicto.txt"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK  CSV de fora da pasta canónica exige --saida (e respeita-o)")


if __name__ == "__main__":
    testes = [test_controlo_que_ressuscita_diverge,
              test_controlo_identico_exclui_a_causa,
              test_divergencia_so_em_magnitude,
              test_celula_que_morre_conta_como_divergencia,
              test_avisa_se_a_condicao_tem_duas_digitais,
              test_avisa_se_sem_obstaculos_nao_mudou_o_mundo,
              test_avisa_se_a_escala_mudou_o_mundo,
              test_avisa_campeoes_de_fora_da_campanha,
              test_avisa_celulas_incompletas,
              test_grelha_reproduz_medias_e_sucesso,
              test_csv_de_fora_exige_saida]
    for t in testes:
        t()
    print(f"\n{len(testes)}/{len(testes)} testes da análise do F1 passaram ✅")
