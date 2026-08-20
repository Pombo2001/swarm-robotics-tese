# -*- coding: utf-8 -*-
"""O dashboard MOSTRA alguma coisa — não basta construir sem rebentar.

O `auditar_dashboard.py` corre-se à mão antes de publicar no Pi. Isso apanha o
que estiver partido no dia em que alguém se lembra de o correr; não apanha a
regressão que entra numa tarde e só se vê em frente ao júri. Estes testes põem a
mesma auditoria na suite, para o `pytest tests/` a arrastar consigo.

A lógica NÃO é duplicada aqui de propósito: o auditor é o único produtor destas
verificações, e um teste que reimplementasse os mesmos critérios passaria a ser
uma segunda régua para a mesma grandeza — o defeito que este projeto já catalogou
seis vezes.

O que se garante:

1. **Todas as vistas constroem**, nos dois modos (completo e o de leitura, que é
   o que o orientador abre no Pi).
2. **Nenhuma vista mostra um estado vazio inesperado.** As mensagens de «não há
   nada» são extraídas do próprio código por AST e procuradas no que a vista
   renderiza; as que são legítimas nesta máquina estão declaradas com a razão em
   `VAZIO_ESPERADO`.
3. **Nenhuma referência de imagem aponta para um ficheiro que não existe** — um
   `src` errado não rebenta nada, dá um ícone partido que numa galeria de mil
   imagens ninguém vê a tempo.
4. **Nenhuma função de `dashboard/data.py` devolve vazio ou rebenta** — são elas
   que alimentam tudo o que se desenha.

Uso: .venv/Scripts/python.exe tests/test_dashboard_conteudo.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import auditar_dashboard as aud  # noqa: E402


def _correr(*auditorias):
    """Corre auditorias com os acumuladores limpos e devolve os problemas."""
    aud.problemas.clear()
    aud.notas.clear()
    for a in auditorias:
        a()
    return list(aud.problemas)


def test_todas_as_vistas_constroem():
    p = _correr(aud.audita_vistas)
    assert not p, "vistas que não constroem: %s" % p
    print("OK  as %d vistas constroem" % len(aud.VISTAS))


def test_nenhuma_vista_mostra_estado_vazio_inesperado():
    """Um painel que diz «Ainda não há dados» está, para quem o abre, tão
    partido como um que rebenta — e a auditoria antiga deixava-o passar."""
    p = _correr(aud.audita_vistas_vazias)
    assert not p, "estados vazios não declarados: %s" % p
    print("OK  nenhum estado vazio por explicar")


def test_todas_as_imagens_referenciadas_existem():
    p = _correr(aud.audita_imagens_referenciadas)
    assert not p, "referências partidas: %s" % p
    print("OK  todas as imagens que as vistas pedem existem no disco")


def test_funcoes_de_dados_respondem():
    p = _correr(aud.audita_funcoes_data)
    assert not p, "funções de data.py com problema: %s" % p
    print("OK  as funções de dashboard/data.py respondem e não vêm vazias")


def test_modo_leitura_do_pi():
    """O modo do Pi tem menos botões e é o que o orientador vê. Uma vista que só
    rebente aí é uma vista que só rebenta em frente a quem avalia."""
    antes = os.environ.get("SWARM_DASH_READONLY")
    os.environ["SWARM_DASH_READONLY"] = "1"
    try:
        p = _correr(aud.audita_vistas, aud.audita_vistas_vazias,
                    aud.audita_imagens_referenciadas)
        assert not p, "problemas exclusivos do modo de leitura: %s" % p
    finally:
        if antes is None:
            os.environ.pop("SWARM_DASH_READONLY", None)
        else:
            os.environ["SWARM_DASH_READONLY"] = antes
    print("OK  o modo de leitura (Pi) constrói e mostra o mesmo")


def test_mensagens_de_vazio_sao_encontradas_no_codigo():
    """A extração por AST tem de continuar a encontrar mensagens.

    Se um dia devolver zero — porque as vistas mudaram de forma, porque o AST
    deixou de ver as literais —, os testes acima passariam todos sem verificar
    nada. Um verificador que não encontra o que procura tem de dar erro, não
    silêncio.
    """
    msgs = aud._mensagens_de_vazio()
    assert len(msgs) >= 10, "só %d mensagens extraídas: a extração partiu-se?" % len(msgs)
    print("OK  %d mensagens de estado vazio extraídas do código" % len(msgs))


def test_os_numeros_do_dashboard_sao_os_da_tese():
    """Um número que aparece nos dois sítios tem de ser o mesmo número.

    Corre o `scripts/verificar_dashboard.py`: a tabela científica contra a
    `tab:res_eval` do `.tex`, os KPIs contra as suas fontes, e o inventário de
    horas contra as campanhas que fecharam. Falhou uma vez de verdade — o F2 do
    mapa grande fechou a 16 ago com 407 h e ninguém as somou.
    """
    import importlib.util
    caminho = os.path.join(os.path.dirname(__file__), "..", "scripts",
                           "verificar_dashboard.py")
    spec = importlib.util.spec_from_file_location("verificar_dashboard", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0, "dashboard vs tese: %s" % mod.falhas
    print("OK  %d valores do dashboard batem com as fontes da tese"
          % mod.conferidos)


TESTES = [
    test_todas_as_vistas_constroem,
    test_nenhuma_vista_mostra_estado_vazio_inesperado,
    test_todas_as_imagens_referenciadas_existem,
    test_funcoes_de_dados_respondem,
    test_modo_leitura_do_pi,
    test_mensagens_de_vazio_sao_encontradas_no_codigo,
    test_os_numeros_do_dashboard_sao_os_da_tese,
]


if __name__ == "__main__":
    for t in TESTES:
        t()
    print("\n%d/%d testes de conteúdo do dashboard passaram ✅"
          % (len(TESTES), len(TESTES)))


def test_os_numeros_do_dashboard_levam_virgula():
    """PT-PT: `38,3`, não `38.3` — e não os dois no mesmo ecrã.

    A 18 de agosto a vista Ciência mostrava «δ = +0.77» na linha abaixo de
    «δ = +0,61», e a tabela por cenário dizia «38.3 rec/ep» ao lado de médias
    com vírgula. Não é um erro de valor: é um ecrã que se lê a duas velocidades,
    e este vai ser projetado numa defesa.

    A formatação passou a sair do `theme.num()`. Este teste guarda a regra:
    nenhuma vista volta a formatar um número decimal à mão.
    """
    import glob
    import re as _re

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    padrao = _re.compile(r"(:\.\d+f\}|%\.\d+f)")
    faltas = []
    for f in sorted(glob.glob(os.path.join(raiz, "dashboard", "views", "*.py"))):
        for n, linha in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
            if not padrao.search(linha):
                continue
            # `.replace(".", ",")` na própria linha é a formatação à mão que já
            # estava certa; `theme.num` é o caminho novo. As percentagens
            # inteiras (`%.0f`) e as opacidades CSS (`{alfa:.3f}`) não são
            # números que o leitor compare.
            if ('replace(".", ",")' in linha or "theme.num" in linha
                    or "%.0f" in linha or ":.0f}" in linha
                    or "rgba" in linha or "alfa" in linha or "style" in linha):
                continue
            faltas.append("%s:%d %s" % (os.path.basename(f), n, linha.strip()[:70]))
    assert not faltas, "números formatados com ponto decimal:\n" + "\n".join(faltas)


def test_a_defesa_mostra_a_resposta_inteira_a_cada_questao():
    """Cada ecrã da Defesa mostra a resposta COMPLETA, não a primeira linha.

    A vista lê as respostas do `main.tex` com uma expressão regular. Enquanto
    todas as respostas couberam numa linha do `.tex`, um `(.+)` bastou; a da
    QI7, escrita pelo `fechar_qi7.py` com o parágrafo mudado de linha, passou a
    aparecer no ecrã como «Parcialmente, e ao preço» — meia frase, e é o ÚLTIMO
    ecrã da apresentação.

    O que se exige: uma resposta por questão perguntada, cada uma acabada em
    ponto final e sem restos de LaTeX. É o mínimo que distingue uma frase
    inteira de uma frase cortada a meio.
    """
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import defesa

    perguntas, respostas = defesa._questoes(), defesa._respostas()
    assert perguntas, "nenhuma questão lida do main.tex"
    faltam = sorted(set(perguntas) - set(respostas))
    assert not faltam, "questões sem resposta na vista: %s" % faltam

    curtas, cortadas, latex = [], [], []
    for n, r in sorted(respostas.items()):
        if len(r) < 80:
            curtas.append("QI%d (%d caracteres): %s" % (n, len(r), r))
        if not r.rstrip().endswith((".", "!", "?")):
            cortadas.append("QI%d acaba em «%s»" % (n, r[-40:]))
        if "\\" in r or "{" in r or "}" in r:
            latex.append("QI%d: %s" % (n, r[:60]))
    assert not curtas, "respostas curtas de mais (cortadas?):\n" + "\n".join(curtas)
    assert not cortadas, "respostas sem pontuação final:\n" + "\n".join(cortadas)
    assert not latex, "restos de LaTeX na resposta:\n" + "\n".join(latex)
    print("OK  %d respostas inteiras na vista Defesa (a mais curta tem %d caracteres)"
          % (len(respostas), min(len(r) for r in respostas.values())))
