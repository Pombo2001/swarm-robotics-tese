#!/usr/bin/env python3
"""Auditoria do dashboard — corre isto ANTES de publicar no Pi.

Porquê
------
Olhar para o ecrã apanha o que salta à vista. Não apanha um PNG de 0 bytes, uma
vista que só rebenta em modo de leitura, ou — o caso que motivou este ficheiro —
uma retenção de **563%** na vista da robustez, porque o numerador vinha de uma
campanha e o denominador de outra.

Corre nos DOIS modos: o completo (torre) e o de leitura (`SWARM_DASH_READONLY=1`,
que é o que o orientador vê no Raspberry Pi).

Uso
---
    python scripts/auditar_dashboard.py
    SWARM_DASH_READONLY=1 python scripts/auditar_dashboard.py

Sai com código 1 se houver problemas — dá para pôr num hook.
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import sys
import traceback

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(RAIZ)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

problemas: list[tuple[str, str]] = []
notas: list[tuple[str, str]] = []


def X(vista: str, msg: str) -> None:
    problemas.append((vista, msg))


def I(vista: str, msg: str) -> None:
    notas.append((vista, msg))


VISTAS = ["overview", "treinar", "servidor", "ciencia", "resultados", "curvas",
          "videos", "aovivo", "arquivo", "proveniencia", "prontidao",
          "defesa", "mapa", "escala", "vitrine", "viz3d"]

ALGOS = ("gnn", "ppo", "sac")
CENARIOS_TESE = ("none", "u_wall", "bottleneck", "four_rooms",
                 "cooperative_door", "cooperative_perception",
                 "cooperative_door_bypass")


def audita_vistas() -> None:
    """Cada vista constrói-se sem exceção, no modo em que este script corre."""
    from nicegui import ui

    from dashboard.jobs import JobQueue

    fila = JobQueue()
    ok = 0
    for nome in VISTAS:
        mod = importlib.import_module("dashboard.views." + nome)
        if not hasattr(mod, "build"):
            X(nome, "não tem build()")
            continue
        try:
            with ui.element("div"):
                try:
                    mod.build(fila)          # as que gerem treinos recebem a fila
                except TypeError as e:
                    if "positional argument" not in str(e):
                        raise
                    mod.build()
            ok += 1
        except Exception as e:               # noqa: BLE001
            X(nome, "build() rebentou: %s: %s" % (type(e).__name__, e))
            traceback.print_exc(limit=4)
    I("vistas", "%d de %d construíram" % (ok, len(VISTAS)))


# ── Estados vazios ───────────────────────────────────────────────────────────
# Uma vista que constrói perfeitamente e escreve «Ainda não há dados» está tão
# partida, aos olhos de quem a abre, como uma que rebenta — e a auditoria
# original, que só verificava que as vistas CONSTROEM, deixava-a passar sem uma
# palavra.
#
# A primeira tentativa procurou marcas soltas («não há», «nenhum») no texto
# renderizado, e apanhou sobretudo PROSA: «Não há domínio de paradigma» é uma
# conclusão da tese, não um painel vazio. Seis dos seis achados eram falsos.
#
# Agora as mensagens saem do CÓDIGO. Extraem-se por AST as literais curtas das
# vistas que falam de ausência — que são, por construção, exatamente as que
# alguém escreveu para o caso de não haver o que mostrar — e depois procura-se
# no que a vista renderizou. Uma mensagem nova entra sozinha; uma frase de prosa
# não entra porque nunca é uma literal curta e isolada.
MARCAS_VAZIO = (
    "sem dados", "sem csv", "sem gráfico", "sem graficos", "sem figuras",
    "sem vídeos", "não há", "ainda não", "indisponível", "sem seleção",
    "sem configs", "nenhum treino", "sem instantâneo", "sem coluna",
)

# Vistas onde um estado vazio é ESPERADO nesta máquina, com a razão escrita. Uma
# isenção sem razão é uma forma educada de não corrigir.
VAZIO_ESPERADO = {
    "videos": "os GIF dos episódios não são versionados (SWARM_VIDEOS=1 gera-os)",
    "prontidao": "os testes correm a pedido, dentro da própria vista",
    "curvas": "não há treinos locais por decisão do projeto — o treino é no servidor",
}


def _mensagens_de_vazio() -> dict:
    """{mensagem: (ficheiro, linha)} — as literais de ausência do código das vistas."""
    import ast

    base = os.path.join("dashboard", "views")
    # `data.py` também conta: a frase «Nenhum treino local a decorrer» é
    # construída lá e devolvida à vista já pronta. Procurar só nas vistas
    # deixava-a de fora — e é a mensagem que mais aparece nesta máquina.
    ficheiros = [(f, os.path.join(base, f)) for f in sorted(os.listdir(base))
                 if f.endswith(".py")]
    ficheiros.append(("data.py", os.path.join("dashboard", "data.py")))
    achadas = {}
    for f, caminho in ficheiros:
        with open(caminho, encoding="utf-8") as fh:
            try:
                arvore = ast.parse(fh.read())
            except SyntaxError as e:
                X("vistas", "%s não faz parse: %s" % (f, e))
                continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                v = no.value.strip()
                if 3 < len(v) < 90 and any(m in v.lower() for m in MARCAS_VAZIO):
                    achadas.setdefault(v, (f, no.lineno))
    return achadas


def _percorre(elemento, profundidade=0):
    """Todos os elementos da árvore construída, em profundidade."""
    yield elemento, profundidade
    for slot in getattr(elemento, "slots", {}).values():
        for filho in slot.children:
            yield from _percorre(filho, profundidade + 1)


def _constroi(nome, fila):
    """Constrói uma vista dentro de um contentor e devolve-o (ou None)."""
    from nicegui import ui
    mod = importlib.import_module("dashboard.views." + nome)
    if not hasattr(mod, "build"):
        return None
    with ui.element("div") as raiz:
        try:
            mod.build(fila)
        except TypeError as e:
            if "positional argument" not in str(e):
                raise
            mod.build()
    return raiz


def audita_vistas_vazias() -> None:
    """Cada vista MOSTRA alguma coisa — e diz-se quais mostram um estado vazio.

    Duas medidas por vista: quantos elementos produziu (uma vista com meia dúzia
    está vazia, construa ou não) e que textos de «não há nada» escreveu.
    """
    from dashboard.jobs import JobQueue

    fila = JobQueue()
    mensagens = _mensagens_de_vazio()
    magras, mostrados = [], 0
    for nome in VISTAS:
        try:
            raiz = _constroi(nome, fila)
        except Exception:                    # já reportado por audita_vistas
            continue
        if raiz is None:
            continue
        elementos = list(_percorre(raiz))
        renderizados = [t for t in (getattr(el, "text", None) for el, _ in elementos)
                        if isinstance(t, str) and t.strip()]
        encontradas = [m for m in mensagens
                       if any(m in t for t in renderizados)]
        if len(elementos) < 8:
            magras.append((nome, len(elementos)))
        if encontradas:
            mostrados += len(encontradas)
            razao = VAZIO_ESPERADO.get(nome)
            registar = I if razao else X
            registar(nome, "mostra %d estado(s) vazio(s): %s%s"
                     % (len(encontradas),
                        " | ".join("«%s» (%s:%d)"
                                   % (m, mensagens[m][0], mensagens[m][1])
                                   for m in encontradas)[:240],
                        "  [esperado: %s]" % razao if razao else ""))
    if magras:
        X("vistas", "vistas com quase nada construído: %s"
          % ", ".join("%s (%d elementos)" % m for m in magras))
    I("vistas", "%d vistas inspecionadas; %d mensagens de vazio no código, "
                "%d a aparecer" % (len(VISTAS), len(mensagens), mostrados))


def audita_imagens_referenciadas() -> None:
    """Todo o `src` que uma vista cria aponta para um ficheiro que existe.

    A auditoria antiga verificava que as PASTAS servidas existem e que os PNG do
    disco não estão vazios. Faltava o cruzamento que interessa: a figura que a
    vista pede é a figura que lá está. Um `src` errado não rebenta nada — dá um
    ícone partido, que numa galeria de mil imagens ninguém vê a tempo.
    """
    from dashboard.jobs import JobQueue

    # As rotas estáticas do app, para traduzir URL -> caminho no disco.
    ROTAS = {"/graficos": "results/graficos_tese",
             "/estatico": "dashboard/estatico",
             "/episodios": "results/episodios_3d",
             "/figuras_tese": "Tese/images/resultados"}

    fila = JobQueue()
    total = partidas = externas = 0
    exemplos = []
    for nome in VISTAS:
        try:
            raiz = _constroi(nome, fila)
        except Exception:                    # noqa: BLE001
            continue
        if raiz is None:
            continue
        for el, _ in _percorre(raiz):
            src = getattr(el, "_props", {}).get("src")
            if not isinstance(src, str) or not src:
                continue
            total += 1
            if src.startswith(("http://", "https://", "data:")):
                externas += 1
                continue
            caminho = None
            for rota, base in ROTAS.items():
                if src.startswith(rota + "/"):
                    caminho = os.path.join(base, src[len(rota) + 1:])
                    break
            if caminho is None:
                continue                     # rota que não servimos: fora do âmbito
            caminho = caminho.split("?")[0]
            if not os.path.isfile(caminho):
                partidas += 1
                if len(exemplos) < 5:
                    exemplos.append("%s -> %s" % (nome, src))
    if partidas:
        X("imagens", "%d referências para ficheiros que não existem: %s"
          % (partidas, "; ".join(exemplos)))
    I("imagens", "%d referências verificadas (%d externas, %d partidas)"
      % (total, externas, partidas))


def audita_funcoes_data() -> None:
    """Todas as funções públicas de `dashboard/data.py` respondem — e com quê.

    São 697 linhas e ~30 funções: é delas que sai tudo o que as vistas desenham.
    Uma que passe a devolver vazio não estoira nada; a vista limita-se a mostrar
    menos, e a diferença entre «não há dados» e «a função partiu-se» não se vê
    do lado de fora. Aqui chamam-se todas, com argumentos derivados dos próprios
    dados quando precisam de um.
    """
    import inspect as _inspect

    from dashboard import data

    # Argumentos derivados dos dados: nada fixo à mão, senão a auditoria começa
    # a testar um mundo que já não existe.
    sessoes = data.list_sessions() or []
    com_eval = data.sessions_with_eval() or []
    cenarios = data.scalability_scenarios() or []
    pngs = data.list_pngs(sessoes[0]) if sessoes else []
    videos = data.video_sessions() or []
    ARGS = {
        "session_metrics": (com_eval[:1] or sessoes[:1]),
        "descricao_sessao": sessoes[:1],
        "list_pngs": sessoes[:1],
        "session_datetime": sessoes[:1],
        "session_is_evaluated": sessoes[:1],
        "session_manifesto": sessoes[:1],
        "list_videos": videos[:1] or sessoes[:1],
        "scenarios_with_video": videos[:1] or sessoes[:1],
        "scalability_table": cenarios[:1],
        "graph_type": [pngs[0]] if pngs else ["desempenho_global.png"],
        "idade_legivel": [os.path.getmtime("configs/foraging.yaml")],
        "proveniencia": ["configs/foraging.yaml"],
        "parse_video": ["gnn_u_wall.gif"],
        "video_for": (videos[:1] or sessoes[:1]) + ["gnn", "u_wall"],
    }
    # `send_to_thesis` COPIA ficheiros para a tese: não se chama numa auditoria.
    NAO_CHAMAR = {"send_to_thesis"}

    vazias, rebentaram, chamadas = [], [], 0
    for nome, fn in sorted(vars(data).items()):
        if nome.startswith("_") or not _inspect.isfunction(fn):
            continue
        if fn.__module__ != data.__name__ or nome in NAO_CHAMAR:
            continue
        sig = _inspect.signature(fn)
        obrigatorios = [p for p in sig.parameters.values()
                        if p.default is _inspect.Parameter.empty
                        and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
        args = ARGS.get(nome, [])
        if len(args) < len(obrigatorios):
            I("data", "%s: sem argumento derivável — não chamada" % nome)
            continue
        try:
            r = fn(*args[:max(len(obrigatorios), 0)] if obrigatorios else [])
            chamadas += 1
        except Exception as e:               # noqa: BLE001
            rebentaram.append("%s: %s: %s" % (nome, type(e).__name__, e))
            continue
        vazio = r is None or (hasattr(r, "__len__") and len(r) == 0)
        if vazio:
            vazias.append(nome)
    if rebentaram:
        X("data", "%d funções rebentaram: %s" % (len(rebentaram),
                                                 "; ".join(rebentaram[:4])))
    if vazias:
        X("data", "%d funções devolvem vazio (a vista que as usa mostra "
                  "«sem dados»): %s" % (len(vazias), ", ".join(vazias)))
    I("data", "%d funções chamadas, %d vazias, %d rebentaram"
      % (chamadas, len(vazias), len(rebentaram)))


def audita_imagens() -> None:
    """Nenhuma figura vazia ou ilegível — a galeria serve-as todas.

    O Pi não tem Pillow: a cópia publicada instala só `nicegui pandas plotly
    numpy pyyaml`, e não é para lhe acrescentar uma dependência por causa de um
    auditor. Sem Pillow verifica-se o que dá sem ele — ficheiros de 0 bytes, que
    é a falha que de facto acontece quando um gerador morre a meio.
    """
    try:
        from PIL import Image
    except ImportError:
        Image = None

    vazios, corruptos, total = [], [], 0
    for raiz, _, fs in os.walk(os.path.join("results", "graficos_tese")):
        for f in fs:
            if not f.lower().endswith((".png", ".gif")):
                continue
            total += 1
            caminho = os.path.join(raiz, f)
            if os.path.getsize(caminho) == 0:
                vazios.append(caminho)
                continue
            if Image is None:
                continue
            try:
                with Image.open(caminho) as im:
                    im.verify()
            except Exception:                # noqa: BLE001
                corruptos.append(caminho)
    if vazios:
        X("figuras", "%d ficheiros de 0 bytes: %s" % (len(vazios), vazios[:3]))
    if corruptos:
        X("figuras", "%d imagens ilegíveis: %s" % (len(corruptos), corruptos[:3]))
    I("figuras", "%d imagens, %d vazias%s"
      % (total, len(vazios),
         ", %d corruptas" % len(corruptos) if Image is not None
         else " (sem Pillow: não se verificou se abrem)"))


def audita_3d() -> None:
    """Os episódios 3D têm a estrutura que o viz3d.js lê, e a grelha está cheia."""
    base = os.path.join("results", "episodios_3d")
    if not os.path.isdir(base):
        X("3D", "não existe results/episodios_3d")
        return
    chaves = ("meta", "geometria", "quadros", "ninho", "recolhas")
    meta_ok = ("algo", "cenario", "rotulo", "passos", "quadros", "agentes",
               "raio_arena", "raio_robo", "raio_ninho", "raio_obstaculo")
    eps = sorted(f for f in os.listdir(base) if f.endswith(".json"))
    for f in eps:
        with open(os.path.join(base, f), encoding="utf-8") as fh:
            d = json.load(fh)
        faltam = [k for k in chaves if k not in d]
        if faltam:
            X("3D", "%s sem %s" % (f, faltam))
            continue
        m = d["meta"]
        em_falta = [k for k in meta_ok if k not in m]
        if em_falta:
            X("3D", "%s: meta sem %s" % (f, em_falta))
        n = len(d["quadros"])
        if not (n == len(d["ninho"]) == len(d["recolhas"]) == m["quadros"]):
            X("3D", "%s: séries de comprimentos diferentes" % f)
    esperados = {"%s_%s" % (a, c) for a in ALGOS for c in CENARIOS_TESE}
    faltam = sorted(esperados - {f[:-5] for f in eps})
    if faltam:
        X("3D", "faltam %d episódios: %s" % (len(faltam), faltam))
    I("3D", "%d episódios (grelha %d×%d)"
      % (len(eps), len(CENARIOS_TESE), len(ALGOS)))


def audita_estaticos() -> None:
    """As rotas que o app serve existem no disco."""
    for rota, caminho in (("/graficos", "results/graficos_tese"),
                          ("/estatico", "dashboard/estatico"),
                          ("/episodios", "results/episodios_3d"),
                          ("/figuras_tese", "Tese/images/resultados")):
        if not os.path.isdir(caminho):
            X("estáticos", "%s serve %s, que não existe" % (rota, caminho))
    if not os.path.isfile("Tese/images/resultados/mapa_grande_planta.png"):
        X("mapa", "a planta do mapa grande não está no disco")


def audita_campanhas() -> None:
    """Nenhuma campanha com dados e sem figuras; nenhuma pasta vazia no seletor."""
    from dashboard import data

    no_seletor = set(data.list_sessions())
    raiz = os.path.join("results", "graficos_tese")
    for d in sorted(os.listdir(raiz)):
        caminho = os.path.join(raiz, d)
        if not os.path.isdir(caminho) or d.startswith("_"):
            continue
        pngs = glob.glob(os.path.join(caminho, "**", "*.png"), recursive=True)
        csvs = glob.glob(os.path.join(caminho, "**", "*.csv"), recursive=True)
        if csvs and not pngs:
            X("galeria", "%s tem %d CSV e ZERO figuras" % (d, len(csvs)))
        if not csvs and not pngs and d in no_seletor:
            X("galeria", "%s está vazia e aparece no seletor" % d)
    I("galeria", "%d campanhas no seletor" % len(no_seletor))


def audita_robustez() -> None:
    """Retenção com 10% de falhas: base e falhas da MESMA corrida.

    O bug que este teste fixa: a base vinha do `eval_summary.csv` (campanha de 7
    dias, 140 ep/célula, 10 jul) e as falhas dos `eval_*_fail10.csv` (2 jul, 20
    ep). No Muro em U dava 303%; no SAC, 563%. Uma retenção acima de ~110% não é
    plausível — falhar 10% dos robôs não melhora a recolha — e é o sinal de que
    os dois lados da divisão são de campanhas diferentes.
    """
    from dashboard import data

    rt = data.robustness_table()
    if not rt:
        X("robustez", "a tabela veio vazia")
        return
    valores = [i["retencao"] for a in rt.values() for i in a.values()
               if i["retencao"] is not None]
    if not valores:
        X("robustez", "nenhuma retenção calculada")
        return
    fora = [v for v in valores if v > 110.0 or v < 50.0]
    if fora:
        X("robustez", "%d retenções implausíveis (%.0f%% a %.0f%%) — base e "
                      "falhas da mesma corrida?"
          % (len(fora), min(fora), max(fora)))
    I("robustez", "%d células, retenção de %.1f%% a %.1f%%"
      % (len(valores), min(valores), max(valores)))


def audita_numeros() -> None:
    """Os números do cartaz saem dos dados, não da memória de quem escreveu."""
    import pandas as pd

    from src.scenarios import SCENARIOS

    ev = "results/graficos_tese/final_7d/eval_by_run_7d.csv"
    if os.path.isfile(ev):
        n = len(pd.read_csv(ev))
        if n != 2940:
            X("overview", "o cartaz diz 2940 episódios; o CSV tem %d" % n)
        else:
            I("overview", "2940 episódios confirmados")
    else:
        X("overview", "falta %s — é de lá que vem o 2940" % ev)
    if len(SCENARIOS) != 8:
        X("overview", "o cartaz diz 8 cenários; scenarios.py tem %d" % len(SCENARIOS))

    # A vitrine é o que se mostra na defesa: nenhuma figura pode faltar.
    import yaml
    fp = os.path.join("configs", "vitrine.yaml")
    if os.path.isfile(fp):
        cfg = yaml.safe_load(open(fp, encoding="utf-8")) or {}
        total = falta = 0
        for bloco in cfg.get("blocos", []):
            cb = bloco.get("campanha")
            for it in bloco.get("itens", []) or []:
                total += 1
                camp = it.get("campanha", cb) or ""
                if not os.path.isfile(os.path.join("results", "graficos_tese",
                                                   camp, it.get("figura", ""))):
                    falta += 1
                    X("vitrine", "figura em falta: %s/%s" % (camp, it.get("figura")))
        I("vitrine", "%d itens, %d em falta" % (total, falta))


def main() -> int:
    leitura = os.environ.get("SWARM_DASH_READONLY") == "1"
    audita_vistas()
    audita_vistas_vazias()
    audita_imagens_referenciadas()
    audita_funcoes_data()
    audita_imagens()
    audita_3d()
    audita_estaticos()
    audita_campanhas()
    audita_robustez()
    audita_numeros()

    print("=" * 74)
    print("AUDITORIA DO DASHBOARD — modo %s"
          % ("LEITURA (a cópia do Pi)" if leitura else "completo (torre)"))
    print("=" * 74)
    for vista, msg in problemas:
        print("[X] %-12s %s" % (vista, msg))
    for vista, msg in notas:
        print("[i] %-12s %s" % (vista, msg))
    print("-" * 74)
    print("%d problema(s)" % len(problemas))
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
