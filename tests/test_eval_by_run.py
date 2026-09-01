# -*- coding: utf-8 -*-
"""Testes do `scripts/eval_by_run.py` — o script que produz o CSV do veredicto.

Porque este e não outro: o inventário de 5 ago classifica-o como risco médio
com a nota «são eles que produzem os CSV de toda a tese», e é ele que vai
processar o braço do GNN do mapa grande quando fechar. Um defeito aqui aparece
no pior momento possível — com a campanha fechada e dias para o hard stop.

O que se testa, e porquê:

1. `_run_models` — encontra os modelos `_run{n}`, ordena-os por número (não
   por texto, senão `run10` vem antes de `run2`) e não mistura cenários: o
   sufixo do cenário faz parte do nome, e o do Sandbox é vazio, que é o caso em
   que um glob distraído apanharia tudo.
2. A forma do CSV — uma linha por episódio, com `Run`, `Algorithm`,
   `Scenario` e `door_opened` preservados. A `door_opened` é a M3 do pré-registo
   do mapa grande, que a 5 ago se descobriu não ser calculável.
3. Um run que falha não desaparece em silêncio — o núcleo. O laço apanha a
   exceção de cada run e continua, o que está certo; o que não podia continuar é
   a falha ficar só numa linha de log. O n deste CSV é o que decide a QI7
   (limiar ⌈5/7 × n⌉ lido do ficheiro: 21 execuções pedem 15 convergentes, 19
   pedem 14), portanto um run perdido move a fasquia que a tese diz ter fixado
   de antemão. A falha tem de viajar com os dados — os CSV são copiados entre
   máquinas e um log noutro terminal não é evidência de nada.
4. O sidecar não sobrevive à sua correção — reavaliar sem falhas apaga-o.
   Um aviso obsoleto lido como atual é pior do que nenhum.
5. A análise olha para o sidecar — escrever o aviso ao lado dos dados não
   serve se o sítio onde o limiar é calculado não o ler.

Nenhum teste corre uma avaliação a sério: `eval_algo` é substituído por um duplo.
O que está sob teste é a contabilidade dos runs, não o simulador.

Uso: .venv/Scripts/python.exe tests/test_eval_by_run.py
"""
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import eval_by_run as mod  # noqa: E402


# Duplos
def _episodios(n, recolhas=0.0, porta=None):
    return pd.DataFrame([{
        "food_collected": recolhas, "success": recolhas > 0,
        "total_reward": 100.0 * (i + 1), "door_opened": porta,
    } for i in range(n)])


class EvalFalso:
    """Substitui o `eval_algo`. `rebenta` diz que runs devem falhar."""

    def __init__(self, episodios=3, rebenta=(), devolve_none=()):
        self.episodios = episodios
        self.rebenta = set(rebenta)
        self.devolve_none = set(devolve_none)
        self.chamadas = []

    def __call__(self, algo, sc, config_path, episodes, seed_base,
                 model_path=None):
        run = int(model_path.rsplit("run", 1)[1].split(".")[0])
        self.chamadas.append((algo, sc, run))
        if run in self.rebenta:
            raise RuntimeError("modelo corrompido (simulado)")
        if run in self.devolve_none:
            return None, None
        return _episodios(self.episodios, recolhas=float(run), porta=False), model_path


def _preparar(monkey_eval, tmp, runs=(1, 2, 3), algo="ppo", sc="mapa_grande"):
    """Cria os ficheiros de modelo (vazios — nunca são abertos) e redireciona as
    pastas do módulo para um diretório temporário."""
    sub, padrao = mod._RUN_GLOBS[algo]
    pasta = os.path.join(tmp, "results", sub)
    os.makedirs(pasta, exist_ok=True)
    from src.scenarios import scenario_suffix
    suf = scenario_suffix(sc)
    for r in runs:
        nome = padrao.format(suf=suf).replace("*", str(r))
        open(os.path.join(pasta, nome), "w").close()
    mod.PROJECT_ROOT = tmp
    mod.EVAL_DIR = os.path.join(tmp, "results", "evaluation")
    import scripts.eval_all as eval_all
    eval_all.eval_algo = monkey_eval
    return pasta


def _restaurar(raiz_real, eval_dir_real, eval_algo_real):
    mod.PROJECT_ROOT = raiz_real
    mod.EVAL_DIR = eval_dir_real
    import scripts.eval_all as eval_all
    eval_all.eval_algo = eval_algo_real


class Ambiente:
    """Isola cada teste: pastas temporárias e `eval_algo` reposto no fim."""

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        import tempfile
        import scripts.eval_all as eval_all
        self._tmpdir = tempfile.TemporaryDirectory()
        self._raiz, self._evaldir = mod.PROJECT_ROOT, mod.EVAL_DIR
        self._eval_algo = eval_all.eval_algo
        self.falso = EvalFalso(**self.kw)
        self.tmp = self._tmpdir.name
        return self

    def prepara(self, **kw):
        return _preparar(self.falso, self.tmp, **kw)

    def __exit__(self, *exc):
        _restaurar(self._raiz, self._evaldir, self._eval_algo)
        self._tmpdir.cleanup()


# 1. _run_models
def test_run_models_ordena_por_numero():
    """`run10` tem de vir DEPOIS de `run2`. Com ordenação de texto, a coluna Run
    do CSV sairia baralhada — e os rótulos não são identificadores (28 jul)."""
    with Ambiente() as amb:
        amb.prepara(runs=(1, 2, 3, 10, 21))
        achados = mod._run_models("ppo", "mapa_grande")
        assert [r for r, _ in achados] == [1, 2, 3, 10, 21], achados
        print("OK  _run_models ordena 1, 2, 3, 10, 21 (numérico, não textual)")


def test_run_models_nao_mistura_cenarios():
    """O sufixo do Sandbox é vazio (`ppo_3d_final_run*.zip`), o que o torna o
    caso perigoso: um padrão descuidado apanharia `..._final_u_wall_run3.zip`.
    """
    with Ambiente() as amb:
        pasta = amb.prepara(runs=(1, 2), sc="none")
        for extra in ("ppo_3d_final_u_wall_run7.zip",
                      "ppo_3d_final_mapa_grande_run8.zip"):
            open(os.path.join(pasta, extra), "w").close()
        achados = mod._run_models("ppo", "none")
        assert [r for r, _ in achados] == [1, 2], achados
        outros = mod._run_models("ppo", "u_wall")
        assert [r for r, _ in outros] == [7], outros
        print("OK  o sufixo vazio do Sandbox não apanha os outros cenários")


# 2. Forma do CSV
def test_csv_tem_uma_linha_por_episodio_e_as_colunas():
    with Ambiente(episodios=4) as amb:
        amb.prepara(runs=(1, 2, 3))
        out = mod.evaluate_by_run(episodes=4, scenarios=["mapa_grande"],
                                  algos=["ppo"])
        assert len(out) == 3 * 4, len(out)
        assert out.Run.nunique() == 3, out.Run.unique()
        for col in ("Scenario", "ScenarioLabel", "Algorithm", "Run",
                    "food_collected", "success", "total_reward", "door_opened"):
            assert col in out.columns, col
        assert set(out.Algorithm) == {"PPO"}
        # door_opened preservado (M3): False é um valor, não um vazio.
        assert out.door_opened.notna().all(), "door_opened perdeu-se"
        print("OK  CSV com 1 linha por episódio, colunas e door_opened intactos")


# 3, 4. Falhas
def test_run_falhado_deixa_rasto_ao_lado_do_csv():
    """O teste que justifica o ficheiro: com um run a rebentar, o CSV sai com 2
    execuções em vez de 3 — e isso tem de ficar escrito ONDE os dados estão."""
    with Ambiente(rebenta=(2,)) as amb:
        amb.prepara(runs=(1, 2, 3))
        out = mod.evaluate_by_run(episodes=3, scenarios=["mapa_grande"],
                                  algos=["ppo"])
        assert sorted(out.Run.unique()) == [1, 3], out.Run.unique()

        sidecar = os.path.join(mod.EVAL_DIR, "eval_by_run_FALHAS.txt")
        assert os.path.exists(sidecar), "a falha não deixou rasto nenhum"
        texto = open(sidecar, encoding="utf-8").read()
        assert "run 2" in texto, texto
        assert "1 de 3" in texto, texto
        assert "5/7" in texto, "o sidecar não explica porque é que o n importa"
        print("OK  run falhado -> sidecar com o run, a contagem e o porquê")


def test_run_que_devolve_none_tambem_conta_como_falha():
    """`eval_algo` pode devolver `None` em vez de levantar (é o que faz quando
    não encontra o modelo). Um `continue` silencioso ali dava exatamente o mesmo
    resultado que uma exceção: menos uma execução no CSV."""
    with Ambiente(devolve_none=(3,)) as amb:
        amb.prepara(runs=(1, 2, 3))
        out = mod.evaluate_by_run(episodes=3, scenarios=["mapa_grande"],
                                  algos=["ppo"])
        assert sorted(out.Run.unique()) == [1, 2], out.Run.unique()
        sidecar = os.path.join(mod.EVAL_DIR, "eval_by_run_FALHAS.txt")
        assert os.path.exists(sidecar), "o None passou sem rasto"
        assert "None" in open(sidecar, encoding="utf-8").read()
        print("OK  eval_algo a devolver None conta como falha, não como zero runs")


def test_sem_falhas_nao_fica_sidecar_velho():
    """Reavaliar sem falhas tem de APAGAR o sidecar anterior. Um aviso de uma
    corrida antiga, lido como se fosse desta, é pior do que não haver aviso."""
    with Ambiente(rebenta=(2,)) as amb:
        amb.prepara(runs=(1, 2, 3))
        mod.evaluate_by_run(episodes=3, scenarios=["mapa_grande"], algos=["ppo"])
        sidecar = os.path.join(mod.EVAL_DIR, "eval_by_run_FALHAS.txt")
        assert os.path.exists(sidecar)

        amb.falso.rebenta = set()          # a falha foi corrigida
        out = mod.evaluate_by_run(episodes=3, scenarios=["mapa_grande"],
                                  algos=["ppo"])
        assert sorted(out.Run.unique()) == [1, 2, 3]
        assert not os.path.exists(sidecar), "o sidecar sobreviveu à correção"
        print("OK  reavaliar sem falhas apaga o sidecar antigo")


# 5. A análise lê o sidecar
def test_analise_do_mapa_grande_mostra_o_sidecar(capsys=None):
    """Escrever o aviso ao lado dos dados não serve se o sítio onde o limiar é
    calculado não olhar para ele."""
    import io
    import tempfile
    from contextlib import redirect_stdout
    from scripts import analise_mapa_grande as ana

    with tempfile.TemporaryDirectory() as tmp:
        csv = os.path.join(tmp, "eval_by_run.csv")
        pd.DataFrame([{"Algorithm": "GNN", "Run": 1, "food_collected": 0.0}]
                     ).to_csv(csv, index=False)
        with open(csv.replace(".csv", "_FALHAS.txt"), "w", encoding="utf-8") as fh:
            fh.write("2 de 21 modelos por run NÃO entraram no eval_by_run.csv.\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            ana._avisar_falhas([csv])
        saida = buf.getvalue()
        assert "2 de 21" in saida, saida
        assert "AVISO" in saida, saida
        print("OK  a análise do mapa grande imprime o sidecar de falhas")


TESTES = [
    test_run_models_ordena_por_numero,
    test_run_models_nao_mistura_cenarios,
    test_csv_tem_uma_linha_por_episodio_e_as_colunas,
    test_run_falhado_deixa_rasto_ao_lado_do_csv,
    test_run_que_devolve_none_tambem_conta_como_falha,
    test_sem_falhas_nao_fica_sidecar_velho,
    test_analise_do_mapa_grande_mostra_o_sidecar,
]


if __name__ == "__main__":
    for t in TESTES:
        t()
    print("\n%d/%d testes do eval_by_run passaram ✅" % (len(TESTES), len(TESTES)))
