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


def test_a_defesa_mostra_a_pergunta_e_so_a_pergunta():
    """Cada ecrã da Defesa mostra uma PERGUNTA, e nada além dela.

    O irmão do teste acima, e nasceu do defeito simétrico. A vista lê as
    perguntas do `main.tex` e tirava o `%` do início de cada linha, porque a
    QI7 viveu meses inteira em comentário e era assim que se lia. Quando a QI7
    foi descomentada a 17 de agosto ficou lá a NOTA que explicava a mudança —
    quatro linhas de comentário entre a QI6 e a QI7 —, e a mesma regra que
    salvava a QI7 promoveu essa nota a texto: a QI6 passou a ler-se, no ecrã
    projetado, «...face à otimização puramente objetiva? ── QI7: a PERGUNTA,
    não a resposta. Esteve aqui em comentário desde 6 de agosto (...) Reposta
    na ordem a 18 de agosto.»

    O que se exige é o que distingue uma pergunta de uma pergunta com um
    bilhete colado: acaba em ponto de interrogação. Nenhuma nota do autor
    sobrevive a esta régua, porque nenhuma nota acaba a perguntar.
    """
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import defesa

    perguntas, respostas = defesa._questoes(), defesa._respostas()
    assert perguntas, "nenhuma questão lida do main.tex"

    # As perguntas e as respostas vivem em capítulos diferentes do `.tex` e são
    # lidas por expressões regulares diferentes. Exigir que os dois conjuntos
    # coincidam é a única verificação aqui que não depende de nenhum dos dois
    # parsers estar certo — e é a que apanha uma pergunta que se PERDEU, que
    # nenhuma régua sobre o texto das perguntas lidas pode apanhar. Sem o
    # `re.S` no regex das perguntas, por exemplo, a QI6 e a QI7 (as duas
    # escritas em várias linhas) desaparecem e a Defesa projeta dois ecrãs com
    # resposta e sem pergunta.
    assert set(perguntas) == set(respostas), (
        "perguntas e respostas não coincidem — perguntas sem resposta: %s; "
        "respostas sem pergunta: %s"
        % (sorted(set(perguntas) - set(respostas)),
           sorted(set(respostas) - set(perguntas))))
    assert sorted(perguntas) == list(range(1, len(perguntas) + 1)), (
        "as questões lidas não são QI1..QI%d: %s"
        % (len(perguntas), sorted(perguntas)))

    nao_perguntam, latex, curtas = [], [], []
    for n, (p, _declarada) in sorted(perguntas.items()):
        if not p.rstrip().endswith("?"):
            nao_perguntam.append("QI%d acaba em «%s»" % (n, p[-60:]))
        if "\\" in p or "{" in p or "}" in p:
            latex.append("QI%d: %s" % (n, p[:60]))
        if len(p) < 60:
            curtas.append("QI%d (%d caracteres): %s" % (n, len(p), p))
    assert not nao_perguntam, (
        "perguntas que não acabam a perguntar (nota do autor colada?):\n"
        + "\n".join(nao_perguntam))
    assert not latex, "restos de LaTeX na pergunta:\n" + "\n".join(latex)
    assert not curtas, "perguntas curtas de mais (cortadas?):\n" + "\n".join(curtas)
    print("OK  %d perguntas inteiras na vista Defesa (a mais longa tem %d caracteres)"
          % (len(perguntas), max(len(p) for p, _ in perguntas.values())))


def test_a_defesa_so_admite_a_qi4_sem_numero_em_destaque():
    """A QI4 é a única questão que pode aparecer sem número em destaque.

    O ecrã tem dois textos para a ausência de número: «a QI4 sintetiza as
    outras» (verdade, e por desenho) e «número não disponível no disco» (uma
    avaria). Até 24 de agosto a QI6 caía no segundo, e era falso: o mega-treino
    de um mês está em `results/mega_1mes/` desde 3 de agosto, é dele que a tese
    tira o 28/28 contra 15/28, e é o resultado mais forte da dissertação — a
    única condição sem uma única execução falhada no Muro em U.

    Esta régua fixa a lista das isentas em {QI4}. Qualquer outra questão sem
    número passa a ser um erro, seja porque um CSV desapareceu, seja porque um
    parser partiu, seja porque a questão é nova e ninguém lhe deu fonte.
    """
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import defesa

    perguntas, numeros = defesa._questoes(), defesa._numeros()
    assert perguntas, "nenhuma questão lida do main.tex"

    ISENTAS = {4}
    sem_numero = set(perguntas) - set(numeros) - ISENTAS
    assert not sem_numero, (
        "questões sem número em destaque, e nenhuma delas é a QI4: %s "
        "— o ecrã vai dizer «número não disponível no disco»"
        % sorted(sem_numero))
    a_mais = ISENTAS & set(numeros)
    assert not a_mais, (
        "a QI%s passou a ter número: tirá-la da lista das isentas, senão o "
        "ecrã continua a explicar uma ausência que já não existe"
        % sorted(a_mais))

    vazios = ["QI%d" % n for n, (v, leg) in numeros.items()
              if not str(v).strip() or not str(leg).strip()]
    assert not vazios, "número ou legenda em branco: %s" % vazios
    print("OK  %d das %d questões com número em destaque (isenta: QI4)"
          % (len(numeros), len(perguntas)))


def test_a_defesa_diz_do_f2_o_que_o_instantaneo_diz(tmp_path):
    """«Parado» e «concluído» não são a mesma frase, e nem tudo é ISO.

    A legenda do número da QI7 — o ÚLTIMO ecrã da defesa — acaba com uma frase
    sobre o estado do F2, lida do instantâneo em `results/estado_f2.json`. A
    versão anterior distinguia dois estados, «a correr» e tudo o resto, e para
    tudo o resto escrevia «F2 sem sessões vivas em 2026-08-17T08:37Z»:

      · «sessões vivas» é jargão de tmux, e num ecrã de defesa lê-se como
        avaria. O F2 fechou — 21 execuções do GNN e 21 de cada gradiente —, e
        estar sem sessões vivas é ali o fim do trabalho, não a interrupção
        dele. É o defeito nº3 da segunda passagem, que tinha sido corrigido na
        vista do mapa composto e sobreviveu aqui, em texto;
      · o carimbo ISO/UTC é a forma certa de gravar a hora e não é a de a
        mostrar. É o defeito que o cartão Prontidão teve com o `%b` a escrever
        «22 Aug» num painel em português.

    Exercitam-se os três estados com instantâneos sintéticos, porque o real só
    tem um deles — e é o estado que NÃO está no disco que volta a partir.
    """
    import json
    import re
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import defesa

    def frase(estado):
        p = tmp_path / "estado.json"
        p.write_text(json.dumps(estado), encoding="utf-8")
        original = defesa.ESTADO_F2
        try:
            defesa.ESTADO_F2 = str(p)
            return defesa._estado_f2_curto()
        finally:
            defesa.ESTADO_F2 = original

    cheio = {"medido_utc": "2026-08-17T08:37Z", "tmux_vivos": [],
             "grad": {"runs_previstos": 21, "ppo_runs_concluidos": 21,
                      "sac_runs_concluidos": 21},
             "gnn": {"fechados": 21, "fechados_com_recolha": 4}}
    meio = json.loads(json.dumps(cheio))
    meio["gnn"]["fechados"] = 9
    correr = json.loads(json.dumps(cheio))
    correr["tmux_vivos"] = ["f2gnn"]

    concluido, parado, a_correr = frase(cheio), frase(meio), frase(correr)

    assert "concluído" in concluido, (
        "com tudo fechado, a QI7 tem de dizer que o F2 concluiu: %r" % concluido)
    assert "parado" in parado and "por fechar" in parado, (
        "com execuções por fechar, a QI7 tem de o dizer: %r" % parado)
    assert "a correr" in a_correr, (
        "com sessões vivas, a QI7 tem de dizer que corre: %r" % a_correr)
    assert concluido != parado, (
        "concluído e parado a meio dão a MESMA frase — foi este colapso dos "
        "dois estados num só que pôs «sem sessões vivas» no ecrã de defesa")

    for f in (concluido, parado, a_correr):
        assert not re.search(r"\d{4}-\d{2}-\d{2}T", f), (
            "carimbo ISO/UTC num ecrã em português: %r" % f)
        assert "tmux" not in f and "sessões vivas" not in f, (
            "jargão de operação no ecrã de defesa: %r" % f)
        assert "17 ago" in f, (
            "a data do instantâneo perdeu-se ou não está em português: %r" % f)
    print("OK  os três estados do F2 dão três frases, em português: %r" % concluido)


def test_o_mapa_composto_nao_legenda_o_veredicto_como_projecao(tmp_path):
    """A frase e o rodapé têm de nomear a MESMA fonte — e falhar tem de doer.

    A vista do mapa composto tem duas contas por cima uma da outra: a projeção
    do limiar, que conta execuções de TREINO a partir do instantâneo, e o
    veredicto, que as conta na AVALIAÇÃO determinística. Quando o veredicto
    existe, é ele que se mostra — mas o rodapé continuava a dizer «Projeção
    sobre o instantâneo de …», nomeando por baixo a fonte que não produziu o
    número de cima.

    E, atrás disso, o defeito que o deixou passar: `_veredicto_final()` tinha um
    `except` mudo. A 25 de agosto o `scipy` faltava no venv do Raspberry Pi, a
    leitura rebentava, a função devolvia `None` sem uma palavra, e a vista caía
    na prosa da projeção — anunciava «a avaliação do GNN, que ainda não existe»
    a um palmo da tabela que já a mostrava, no painel que o orientador tinha
    para abrir. Uma avaliação que não existe e uma avaliação que não se
    conseguiu ler não são o mesmo estado, e agora não dão a mesma frase.
    """
    import json
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import mapa

    class _Label:
        """Duplo do `ui.label` — encadeável, e guarda o que lhe passaram."""

        def __init__(self, texto, caixa):
            caixa.append(str(texto))

        def classes(self, *_a, **_k):
            return self

        def style(self, *_a, **_k):
            return self

    def ecra(veredicto):
        """As linhas que a vista escreveria, com o F2 fechado e a zero."""
        caixa = []
        # Instantâneo sintético: 21 execuções fechadas, 4 com recolha. O limiar
        # é ⌈5/7 × 21⌉ = 15, logo o estado é «inalcançável» — o ramo em que a
        # prosa da projeção vivia.
        est = tmp_path / "estado.json"
        est.write_text(json.dumps({
            "medido_utc": "2026-08-17T08:37Z",
            "gnn": {"runs_previstos": 21,
                    "runs_fechados": [{"recolhas": 6.0}] * 4 + [{"recolhas": 0.0}] * 17},
        }), encoding="utf-8")
        orig_estado, orig_ver, orig_ui = mapa.ESTADO_F2, mapa._veredicto_final, mapa.ui
        try:
            mapa.ESTADO_F2 = str(est)
            mapa._veredicto_final = lambda: veredicto
            mapa.ui = type("_UI", (), {"label": staticmethod(
                lambda t: _Label(t, caixa))})
            mapa._limiar_projetado()
        finally:
            mapa.ESTADO_F2, mapa._veredicto_final, mapa.ui = (
                orig_estado, orig_ver, orig_ui)
        return caixa

    medida = {"max_convergentes": 4, "n_runs": 21, "limiar": 15, "leitura": "C"}
    fechado = ecra((medida, None))
    assert any("QI7 FECHADA" in l for l in fechado), (
        "com veredicto no disco, a vista tem de o dizer: %r" % fechado)
    assert not any("ainda não existe" in l for l in fechado), (
        "a vista manda esperar por uma avaliação que já leu: %r" % fechado)
    assert not any(l.startswith("Projeção sobre o instantâneo") for l in fechado), (
        "o rodapé legenda como PROJEÇÃO um número que veio da avaliação "
        "determinística — as duas contas não contam a mesma coisa: %r" % fechado)
    assert any("medir_f2" in l for l in fechado), (
        "o rodapé tem de nomear a fonte real do número: %r" % fechado)

    # A avaliação AINDA não existe: a prosa da projeção é a certa.
    aberto = ecra((None, None))
    assert any("ainda não existe" in l for l in aberto), (
        "sem avaliação, a vista tem de dizer que a decisão está por tomar: %r"
        % aberto)

    # A avaliação existe e não se conseguiu ler: nem uma coisa nem outra.
    partido = ecra((None, "ModuleNotFoundError: No module named 'scipy'"))
    assert any("scipy" in l for l in partido), (
        "o erro que impede a leitura desapareceu do ecrã — foi assim que o Pi "
        "passou oito dias a negar uma avaliação que tinha no disco: %r" % partido)
    assert partido != aberto, (
        "«não existe» e «não consegui ler» dão a MESMA frase: %r" % partido)
    # E o `except` propriamente dito, não um duplo dele: com a leitura a
    # rebentar — que foi o que o `scipy` em falta fez —, a função tem de
    # devolver a razão, e não o `None` mudo que mandou a vista mentir.
    import types
    falso = types.ModuleType("analise_mapa_grande")

    def _rebenta():
        raise ModuleNotFoundError("No module named 'scipy'")

    falso.medir_f2 = _rebenta
    anterior = sys.modules.get("analise_mapa_grande")
    sys.modules["analise_mapa_grande"] = falso
    try:
        medida_nula, razao = mapa._veredicto_final()
    finally:
        if anterior is None:
            sys.modules.pop("analise_mapa_grande", None)
        else:
            sys.modules["analise_mapa_grande"] = anterior
    assert medida_nula is None, (
        "com a leitura rebentada não há medida: %r" % (medida_nula,))
    assert razao and "scipy" in razao, (
        "o `except` voltou a ser mudo: engoliu %r e devolveu %r"
        % ("ModuleNotFoundError: No module named 'scipy'", razao))

    print("OK  o rodapé segue a fonte do número, e o erro chega ao ecrã")

def test_a_prontidao_nao_manda_recompilar_uma_tese_compilada(tmp_path):
    """Tocar no `.tex` sem lhe mudar uma vírgula não torna o PDF obsoleto.

    A vista comparava as datas e mais nada. Qualquer coisa que reescreva o
    ficheiro com o mesmo texto — um ensaio de mutação que repõe o original, um
    editor a gravar sem alterar, um `git checkout` — punha o `.tex` à frente do
    PDF e a Prontidão mandava recompilar uma tese que estava compilada. Um
    alarme que dispara sem motivo ensina quem o lê a ignorá-lo, e é o mesmo
    ecrã que tem de avisar quando o PDF estiver MESMO velho.

    Exercitam-se os dois casos com um par `.tex`/`.fdb_latexmk` sintético: o
    conteúdo que o `latexmk` registou (só a data mudou) e outro que ele nunca
    viu (o texto mudou).
    """
    import hashlib
    import os as _os
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from dashboard.views import prontidao

    tex = tmp_path / "main.tex"
    tex.write_text(r"\documentclass{article}\begin{document}oi\end{document}",
                   encoding="utf-8")
    md5 = hashlib.md5(tex.read_bytes()).hexdigest()
    (tmp_path / "main.fdb_latexmk").write_text(
        '["pdflatex"] 1787656709 "main.tex" "main.pdf" "main" 1787656720 0\n'
        '  "main.tex" 1787656696.14798 %d %s ""\n' % (len(tex.read_bytes()), md5),
        encoding="utf-8")

    assert prontidao._tex_igual_ao_compilado(str(tex)), (
        "o .tex tem o md5 que o latexmk registou e a vista diz que mudou — "
        "vai mandar recompilar uma tese compilada")

    tex.write_text(r"\documentclass{article}\begin{document}outra coisa\end{document}",
                   encoding="utf-8")
    assert not prontidao._tex_igual_ao_compilado(str(tex)), (
        "o .tex mudou de conteúdo e a vista diz que está compilado — este é o "
        "caso perigoso: enviar um PDF que já não é o do texto")

    # E sem registo do latexmk não se inventa: cai na comparação de datas.
    _os.remove(str(tmp_path / "main.fdb_latexmk"))
    assert not prontidao._tex_igual_ao_compilado(str(tex)), (
        "sem fdb_latexmk a vista não tem como saber, e tem de ser conservadora")
    print("OK  a Prontidão distingue «mudou de data» de «mudou de conteúdo»")

if __name__ == "__main__":
    # Os testes descobrem-se por introspeção, e não de uma lista escrita à mão.
    # A lista existiu, ficou a meio do ficheiro — antes de metade dos testes
    # sequer estarem definidos — e nunca mais foi atualizada: `python
    # tests/test_dashboard_conteudo.py`, que é o uso que o cabeçalho documenta,
    # corria 7 de 12 e imprimia «7/7 passaram OK». Um verde falso num ficheiro
    # cujo trabalho é apanhar verdes falsos.
    #
    # `globals()` preserva a ordem de definição, que é a ordem por que foram
    # escritos. Os que pedem uma fixture do pytest (têm parâmetros) só correm
    # sob o pytest, e são anunciados aqui para não passarem por esquecidos.
    import inspect

    testes, com_fixture = [], []
    for nome, fn in list(globals().items()):
        if not (nome.startswith("test_") and callable(fn)):
            continue
        (com_fixture if inspect.signature(fn).parameters else testes).append(fn)

    for t in testes:
        t()
    if com_fixture:
        print("\n(%d teste(s) só sob o pytest, por pedirem fixtures: %s)"
              % (len(com_fixture), ", ".join(f.__name__ for f in com_fixture)))
    print("\n%d/%d testes de conteúdo do dashboard passaram ✅"
          % (len(testes), len(testes)))
