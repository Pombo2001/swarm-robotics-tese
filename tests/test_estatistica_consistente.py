# -*- coding: utf-8 -*-
"""As SEIS implementações do δ de Cliff no repositório dão o mesmo número?

Porque existe
-------------
O δ de Cliff está escrito seis vezes, em seis ficheiros diferentes — e são esses
ficheiros que produzem os tamanhos de efeito da tese (`tab:res_signif`, 21
comparações), os do mega-treino, os do adaptativo e os que a análise do mapa
grande vai produzir. Nenhuma das seis tem teste.

Duas implementações da mesma grandeza não divergem com estrondo: divergem em
silêncio, e a tese passa a reportar dois números para a mesma coisa consoante o
script que a gerou. A 5 ago aconteceu a versão branda disto — medi um percurso
com uma régua diferente da do simulador e publiquei 13,4% onde o valor era 17,0%.

Este teste não escolhe uma implementação nem as unifica (mexer em código que já
produziu números publicados é pior do que a duplicação): fixa a invariante de que
todas concordam, e verifica as propriedades matemáticas que definem a estatística.
"""
import importlib.util
import os
import sys

import numpy as np
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

FICHEIROS = [
    "scripts/analise_adaptativo.py",
    "scripts/analise_exploratoria_megatreino.py",
    "scripts/analise_mapa_grande.py",
    "scripts/analise_megatreino.py",
    "scripts/gerar_figuras_7d.py",
    "scripts/statistical_tests.py",
]


def _carregar(caminho):
    """Importa o módulo isoladamente, só para lhe tirar a função.

    Sem `sys.modules`: estes scripts têm nomes de módulo que colidem entre si e
    alguns fazem trabalho no import, que não interessa aqui.
    """
    nome = "cliff_" + os.path.basename(caminho).replace(".py", "")
    spec = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.cliffs_delta


@pytest.fixture(scope="module")
def implementacoes():
    saida = {}
    for f in FICHEIROS:
        try:
            saida[f] = _carregar(f)
        except Exception as exc:                       # pragma: no cover
            pytest.fail(f"{f}: não consegui carregar cliffs_delta ({exc})")
    return saida


def test_existem_seis(implementacoes):
    """Se aparecer uma sétima cópia, este teste obriga a incluí-la aqui."""
    import subprocess
    r = subprocess.run(["git", "grep", "-l", "def cliffs_delta", "--", "*.py"],
                       cwd=RAIZ, capture_output=True, text=True)
    encontrados = {l.replace("\\", "/") for l in r.stdout.split() if l.strip()}
    encontrados = {f for f in encontrados if not f.startswith("out/")}
    assert encontrados == set(FICHEIROS), (
        "o conjunto de ficheiros com cliffs_delta mudou; acrescenta ou remove "
        f"da lista deste teste.\nencontrados: {sorted(encontrados)}")


def test_todas_concordam(implementacoes):
    """Em 200 amostras aleatórias, as seis dão o mesmo valor."""
    rng = np.random.default_rng(20260805)
    for _ in range(200):
        na, nb = rng.integers(2, 12), rng.integers(2, 12)
        a = rng.normal(50, 20, na).round(1)
        b = rng.normal(45, 25, nb).round(1)
        valores = {f: fn(a, b) for f, fn in implementacoes.items()}
        distintos = set(round(v, 12) for v in valores.values())
        assert len(distintos) == 1, (
            f"as implementações divergiram: {valores}\na={a.tolist()}\nb={b.tolist()}")


@pytest.mark.parametrize("a,b,esperado", [
    ([10, 11, 12], [1, 2, 3], +1.0),      # A domina B por completo
    ([1, 2, 3], [10, 11, 12], -1.0),      # e o simétrico
    ([1, 2, 3], [1, 2, 3], 0.0),          # amostras iguais
    ([1, 3], [2, 2], 0.0),                # um acima, um abaixo
])
def test_propriedades_conhecidas(implementacoes, a, b, esperado):
    for f, fn in implementacoes.items():
        assert fn(a, b) == pytest.approx(esperado), f"{f} deu {fn(a, b)}"


def test_antissimetria(implementacoes):
    """δ(a,b) = −δ(b,a) — a propriedade que define o sinal do efeito."""
    rng = np.random.default_rng(7)
    for _ in range(50):
        a = rng.normal(0, 1, rng.integers(2, 9))
        b = rng.normal(0.5, 1, rng.integers(2, 9))
        for f, fn in implementacoes.items():
            assert fn(a, b) == pytest.approx(-fn(b, a)), f"{f} não é antissimétrica"


def test_intervalo(implementacoes):
    """δ vive em [−1, 1], empates incluídos."""
    rng = np.random.default_rng(11)
    for _ in range(100):
        a = rng.integers(0, 5, rng.integers(2, 10))
        b = rng.integers(0, 5, rng.integers(2, 10))
        for f, fn in implementacoes.items():
            d = fn(a, b)
            assert -1.0 <= d <= 1.0, f"{f} devolveu {d}"


def test_empates_nao_contam_como_diferenca(implementacoes):
    """Os empates puxam o δ para zero — não contam como diferença.

    É o que separa o δ de Cliff de uma comparação de médias, e o sítio onde uma
    implementação distraída (contar `>=` em vez de `>`) daria mais.

    Contas: 4×4 = 16 pares. Os dois `1` de `a` ganham aos dois `0` de `b` (4
    pares) e empatam com os dois `1` (4 pares); os dois `2` ganham a tudo (8
    pares). Logo 12 vitórias, 0 derrotas, 4 empates ⇒ δ = 12/16 = 0,75.
    """
    a = [1, 1, 2, 2]
    b = [1, 1, 0, 0]
    for f, fn in implementacoes.items():
        assert fn(a, b) == pytest.approx(0.75), f"{f} deu {fn(a, b)}"


def test_aceitam_arrays_numpy(implementacoes):
    """Aceitar arrays não é luxo: é o tipo que sai de qualquer `.values`.

    Três das seis faziam `(x > y) - (x < y)` com escalares NumPy, o que desde o
    NumPy 2 é `TypeError: numpy boolean subtract`. Só não rebentava porque todos
    os chamadores embrulhavam os dados em `list()` — uma convenção, não uma
    garantia, e a análise do F2 depende dela.
    """
    a = np.array([10.0, 11.0, 12.0])
    b = np.array([1.0, 2.0, 30.0])
    for f, fn in implementacoes.items():
        d = fn(a, b)
        assert d == pytest.approx(1.0 / 3.0), f"{f} deu {d}"
