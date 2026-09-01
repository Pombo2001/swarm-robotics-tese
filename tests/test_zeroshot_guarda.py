"""
test_zeroshot_guarda.py — a guarda de campanha do F1 (eval_zeroshot_mapa)
Escrito na noite de 25 jul 2026, depois de o F1 desse dia (18 células, ~6 h) ter
de ser deitado fora: correu com os `results/models*` deste PC, de 24 jun — campeões
de ANTES da fitness de homing, que dão 0,0 até no cenário deles — quando a
campanha que a tese reporta é a de 2-9 jul. O script carregava o que estivesse
no caminho esperado e não tinha opinião nenhuma sobre a data.

O que torna este erro caro é ser MUDO: o sintoma nos dados são zeros, que é
exatamente um dos resultados que o F1 procura. Não há como o apanhar a olhar
para o CSV — só por arqueologia às datas das pastas, e três semanas depois.

Cada teste corresponde a um modo de falha concreto:
  · a data vem do sítio certo (sidecar > mtime);
  · um campeão anterior à campanha ABORTA antes da primeira célula;
  · um posterior avisa mas deixa correr (campanha repetida é legítima);
  · o CSV da corrida errada não é dado como bom nem apagado por cima;
  · repetir o F1 com os modelos certos NÃO salta as células da corrida errada.

Corre como os outros testes do projeto (script autónomo, também vale por pytest):
    .venv/Scripts/python.exe tests/test_zeroshot_guarda.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import scenario_suffix
from scripts.eval_zeroshot_mapa import (
    CAMPANHA_FIM, CAMPANHA_INICIO, CONTROLOS, _CAMPEAO, _caminho_campeao,
    _carregar_parciais, _data_modelo, _inventario, _verificar_campanha)

# Datas das três campanhas que se cruzam neste projeto (é este cruzamento que a
# guarda existe para desfazer).
VELHA = datetime(2026, 6, 24, 10, 14)     # antes da fitness de homing
CERTA = datetime(2026, 7, 5, 3, 21)       # campanha 7d — a que a tese reporta
MEGA = datetime(2026, 7, 24, 18, 30)      # mega-treino a reescrever a pasta

ORIGEM = "u_wall"
DIGITAL = "267a7b547aed"                  # a digital da base, como no plano


def _fabricar(raiz, quando, algos=("gnn", "ppo", "sac"), origem=ORIGEM,
              com_meta=True):
    """Cria campeões falsos com uma data — o mínimo que a guarda lê."""
    caminhos = {}
    for algo in algos:
        sub, padrao = _CAMPEAO[algo]
        d = os.path.join(raiz, sub)
        os.makedirs(d, exist_ok=True)
        fp = os.path.join(d, padrao.format(suf=scenario_suffix(origem)))
        with open(fp, "wb") as f:
            f.write(b"modelo a fingir")
        ts = quando.timestamp()
        os.utime(fp, (ts, ts))
        # Só a GNN tem sidecar: o evo_trainer escreve-o, o stable-baselines3 não.
        if com_meta and algo == "gnn":
            with open(os.path.splitext(fp)[0] + ".meta.json", "w") as f:
                json.dump({"fitness": 62.5, "seed": 3,
                           "saved_at": quando.isoformat(timespec="seconds")}, f)
        caminhos[algo] = fp
    return caminhos


@contextlib.contextmanager
def _pasta():
    d = tempfile.mkdtemp(prefix="zeroshot_guarda_")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _capturar(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a, **kw)
    return buf.getvalue()


# A data de um modelo

def test_data_vem_do_sidecar():
    """O sidecar ganha ao mtime: diz quando o TREINO gravou o campeão, e viaja
    com o ficheiro. O mtime muda com uma cópia mal feita."""
    with _pasta() as raiz:
        fp = _fabricar(raiz, VELHA, algos=("gnn",))["gnn"]
        # mtime de 24 jun, sidecar de 5 jul: o modelo é da campanha certa e foi
        # copiado sem preservar timestamps.
        with open(os.path.splitext(fp)[0] + ".meta.json", "w") as f:
            json.dump({"saved_at": CERTA.isoformat(timespec="seconds")}, f)
        quando, fonte = _data_modelo(fp)
        assert fonte == "meta", f"leu do {fonte}, devia ler do sidecar"
        assert quando == CERTA, quando
    print("OK  data: o sidecar .meta.json ganha ao mtime do ficheiro")


def test_data_cai_para_mtime_sem_sidecar():
    """PPO/SAC são .zip do stable-baselines3 e não têm sidecar nenhum."""
    with _pasta() as raiz:
        fp = _fabricar(raiz, CERTA, algos=("ppo",), com_meta=False)["ppo"]
        quando, fonte = _data_modelo(fp)
        assert fonte == "mtime", fonte
        assert abs((quando - CERTA).total_seconds()) < 2, quando
    print("OK  data: sem sidecar cai para o mtime, e diz que foi isso que fez")


def test_sidecar_ilegivel_nao_rebenta():
    """Um sidecar truncado não pode derrubar a corrida — cai para o mtime."""
    with _pasta() as raiz:
        fp = _fabricar(raiz, CERTA, algos=("gnn",))["gnn"]
        with open(os.path.splitext(fp)[0] + ".meta.json", "w") as f:
            f.write("{isto não é json")
        quando, fonte = _data_modelo(fp)
        assert fonte == "mtime", fonte
        assert abs((quando - CERTA).total_seconds()) < 2
    print("OK  data: sidecar corrompido cai para o mtime em vez de rebentar")


# A guarda de campanha

def test_guarda_rejeita_campeoes_anteriores():
    """O caso de 25 jul, exatamente: modelos de 24 jun, campanha de 2-9 jul."""
    with _pasta() as raiz:
        _fabricar(raiz, VELHA)
        inv, em_falta = _inventario(["gnn", "ppo", "sac"], [ORIGEM], raiz)
        assert len(inv) == 3 and not em_falta
        try:
            _capturar(_verificar_campanha, inv, CAMPANHA_INICIO, CAMPANHA_FIM)
        except SystemExit as e:
            msg = str(e)
            assert "ANTERIORES" in msg, msg
            assert "2026-06-24" in msg, "a mensagem não diz a data que encontrou"
            assert "--models-dir" in msg, "a mensagem não diz como corrigir"
        else:
            raise AssertionError("a guarda DEIXOU passar campeões de 24 jun — é "
                                 "exatamente o erro que custou 6 h a 25 jul")
    print("OK  guarda: campeões anteriores à campanha abortam antes de avaliar")


def test_guarda_aceita_a_campanha_certa():
    with _pasta() as raiz:
        _fabricar(raiz, CERTA)
        inv, _ = _inventario(["gnn", "ppo", "sac"], [ORIGEM], raiz)
        saida = _capturar(_verificar_campanha, inv, CAMPANHA_INICIO, CAMPANHA_FIM)
        assert "[!!]" not in saida, saida
    print("OK  guarda: os campeões de 2-9 jul passam sem aviso nenhum")


def test_guarda_avisa_mas_deixa_passar_posteriores():
    """Modelos mais recentes que a janela: pode ser uma campanha repetida de
    propósito — mas é também o aspeto de estar a ler uma pasta que um treino
    está a reescrever (armadilha nº9). Avisa; não aborta."""
    with _pasta() as raiz:
        _fabricar(raiz, MEGA)
        inv, _ = _inventario(["gnn", "ppo", "sac"], [ORIGEM], raiz)
        saida = _capturar(_verificar_campanha, inv, CAMPANHA_INICIO, CAMPANHA_FIM)
        assert "[!!]" in saida and "POSTERIORES" in saida, saida
        assert "2026-07-24" in saida, saida
    print("OK  guarda: campeões posteriores à janela avisam com estrondo, sem abortar")


def test_guarda_desligavel_nao_rebenta():
    """--sem-guarda-data passa inicio=fim=None. Tem de ser um no-op, não um erro."""
    with _pasta() as raiz:
        _fabricar(raiz, VELHA)
        inv, _ = _inventario(["gnn"], [ORIGEM], raiz)
        _capturar(_verificar_campanha, inv, None, None)
    print("OK  guarda: desligada (--sem-guarda-data) não levanta nada")


def test_models_dir_isolado():
    """Os campeões de uma campanha vivem numa pasta própria — nunca por cima dos
    results/models* ativos, que um treino a decorrer reescreve."""
    with _pasta() as raiz:
        esperado = _fabricar(raiz, CERTA, algos=("gnn",))["gnn"]
        achado = _caminho_campeao("gnn", ORIGEM, raiz)
        assert achado == esperado, f"{achado} != {esperado}"
        assert os.path.commonpath([achado, raiz]) == os.path.abspath(raiz)
        # E uma pasta sem campeões devolve None em vez de cair nos results/.
        with _pasta() as vazia:
            assert _caminho_campeao("gnn", ORIGEM, vazia) is None
    print("OK  models-dir: os campeões são lidos da pasta isolada, e só de lá")


# O CSV: o que já lá está não é dado como bom nem apagado por cima

def _csv(dest, quando=None, caminho="results/models/gnn_3d_best_u_wall.pth",
         n=20, com_colunas_de_modelo=True):
    linhas = {"Algorithm": ["GNN"] * n, "Origem": [ORIGEM] * n,
              "Mapa": ["mapa_grande"] * n, "NormObs": ["mapa"] * n,
              "Controlo": ["base"] * n, "env_hash": [DIGITAL] * n,
              "food_collected": [0.0] * n, "success": [0] * n}
    if com_colunas_de_modelo:
        linhas["ModeloPath"] = [caminho] * n
        linhas["ModeloData"] = [(quando or CERTA).isoformat(timespec="seconds")] * n
        linhas["ModeloFonte"] = ["meta"] * n
    pd.DataFrame(linhas).to_csv(dest, index=False)


def _digitais():
    return {c: DIGITAL for c in CONTROLOS}


def test_csv_sem_colunas_de_modelo_vai_para_antigo():
    """O CSV do F1 de 25 jul não regista que modelos avaliou. Não há como
    validá-lo linha a linha, e ele não pode ser retomado como se fosse bom."""
    with _pasta() as d:
        dest = os.path.join(d, "zeroshot_mapa_grande.csv")
        _csv(dest, com_colunas_de_modelo=False)
        esperado = {("GNN", ORIGEM): ("results/models/gnn_3d_best_u_wall.pth",
                                      CERTA.isoformat(timespec="seconds"))}
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            linhas, feitas = _carregar_parciais(dest, _digitais(), "mapa", "base",
                                                20, esperado)
        assert (linhas, feitas) == ([], set()), "retomou um CSV de proveniência desconhecida"
        assert not os.path.exists(dest), "o CSV velho ficou no sítio do novo"
        assert os.path.exists(dest.replace(".csv", "_ANTIGO.csv")), "não arquivou nada"
        assert "ModeloPath" in saida.getvalue(), saida.getvalue()
    print("OK  CSV: sem ModeloPath/ModeloData vai para _ANTIGO, não é retomado")


def test_antigo_existente_nao_e_sobrescrito():
    """Arquivar duas vezes não pode apagar o primeiro arquivo — é lá que estão
    os dados que se quer poder reexaminar (o F1 de 24 jul já lá está)."""
    with _pasta() as d:
        dest = os.path.join(d, "zeroshot_mapa_grande.csv")
        antigo = dest.replace(".csv", "_ANTIGO.csv")
        with open(antigo, "w", encoding="utf-8") as f:
            f.write("o arquivo de 24 jul\n")
        _csv(dest, com_colunas_de_modelo=False)
        _capturar(_carregar_parciais, dest, _digitais(), "mapa", "base", 20, {})
        with open(antigo, encoding="utf-8") as f:
            assert f.read().startswith("o arquivo de 24 jul"), \
                "o _ANTIGO anterior foi escrito por cima"
        novos = [n for n in os.listdir(d) if "_ANTIGO_" in n]
        assert len(novos) == 1, f"esperava 1 arquivo datado, encontrei {novos}"
    print("OK  CSV: o _ANTIGO que já existia é preservado (o novo leva carimbo)")


def test_celula_de_outro_modelo_volta_a_correr():
    """O teste que fecha o buraco: repetir o F1 com os campeões certos NÃO pode
    dar as células da corrida errada como feitas — o CSV tem lá 20 episódios
    completos, só que produzidos por outro modelo."""
    with _pasta() as d:
        dest = os.path.join(d, "zeroshot_mapa_grande.csv")
        _csv(dest, quando=VELHA)                       # a corrida de 25 jul
        esperado = {("GNN", ORIGEM): ("results/models/gnn_3d_best_u_wall.pth",
                                      CERTA.isoformat(timespec="seconds"))}
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            linhas, feitas = _carregar_parciais(dest, _digitais(), "mapa", "base",
                                                20, esperado)
        assert feitas == set(), f"saltou uma célula do modelo errado: {feitas}"
        assert "OUTRO modelo" in saida.getvalue(), saida.getvalue()
        # E as linhas velhas não são arrastadas para o ficheiro novo.
        assert not linhas or all(df.empty for df in linhas), \
            "manteve os episódios do modelo errado no CSV"
    print("OK  retoma: células avaliadas com outro modelo voltam a correr")


def test_celula_do_mesmo_modelo_e_saltada():
    """O contrário também tem de valer, ou a guarda torna a retoma inútil e uma
    corrida interrompida às 17 células recomeça do zero."""
    with _pasta() as d:
        dest = os.path.join(d, "zeroshot_mapa_grande.csv")
        _csv(dest, quando=CERTA)
        esperado = {("GNN", ORIGEM): ("results/models/gnn_3d_best_u_wall.pth",
                                      CERTA.isoformat(timespec="seconds"))}
        linhas, feitas = _capturar_retorno(dest, esperado)
        assert feitas == {("GNN", ORIGEM)}, feitas
        assert linhas and len(linhas[0]) == 20, "perdeu os 20 episódios válidos"
    print("OK  retoma: células do MESMO modelo continuam a ser saltadas")


def _capturar_retorno(dest, esperado):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return _carregar_parciais(dest, _digitais(), "mapa", "base", 20, esperado)


if __name__ == "__main__":
    testes = [test_data_vem_do_sidecar, test_data_cai_para_mtime_sem_sidecar,
              test_sidecar_ilegivel_nao_rebenta,
              test_guarda_rejeita_campeoes_anteriores,
              test_guarda_aceita_a_campanha_certa,
              test_guarda_avisa_mas_deixa_passar_posteriores,
              test_guarda_desligavel_nao_rebenta, test_models_dir_isolado,
              test_csv_sem_colunas_de_modelo_vai_para_antigo,
              test_antigo_existente_nao_e_sobrescrito,
              test_celula_de_outro_modelo_volta_a_correr,
              test_celula_do_mesmo_modelo_e_saltada]
    for t in testes:
        t()
    print(f"\n{len(testes)}/{len(testes)} testes da guarda de campanha passaram ✅")
