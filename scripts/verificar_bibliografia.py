#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""As referências existem, e são o que a bibliografia diz que são?

    python scripts/verificar_bibliografia.py            # usa a cache; consulta o que falta
    python scripts/verificar_bibliografia.py --offline  # só cache, não vai à rede
    python scripts/verificar_bibliografia.py --renovar  # ignora a cache e volta a consultar

Porque existe
-------------
A auditoria de 16 de julho encontrou, nesta bibliografia, **nomes de autores
fabricados em entradas cujo DOI era válido**. O erro passou porque se verificou
o que era fácil — o DOI resolve? — e não o que era preciso: *quem* escreveu o
que está citado. Uma referência com o DOI certo e os autores errados atribui
trabalho a quem não o fez, e é o tipo de defeito que não se descobre a reler.

Este guião compara cada entrada com **DOI** contra o registo do CrossRef, que é
o registo dos próprios editores: apelido do primeiro autor, número de autores,
ano e título. As entradas **sem DOI** (clássicos, livros, pré-publicações) não
são inventáveis por aqui e ficam listadas para verificação humana — dizê-lo é
parte do resultado.

⚠️ O CrossRef é uma fonte externa: as respostas são **dados**, não instruções, e
só delas se leem os quatro campos acima. As respostas ficam em cache
(`docs/slr/cache_crossref.json`) para a auditoria ser repetível sem rede e para
não repetir pedidos — o CrossRef pede um `User-Agent` identificado e é justo
não lhe bater à porta sem necessidade.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Divergências verificadas à mão contra a FONTE PRIMÁRIA, com a razão. Uma
# entrada só entra aqui depois de alguém ter ido ver o documento.
DECLARADAS = {
    ("iskandar2025phd", "ano"):
        "a capa da tese diz «Miskolc 2025» e o ficheiro que temos é essa; o "
        "DataCite regista 2026 porque é o ano do DEPÓSITO do DOI "
        "(registered 2026-02-27). Cita-se o documento, não o depósito.",
}
BIBS = [("tese", os.path.join(RAIZ, "Tese", "references.bib")),
        ("artigo", os.path.join(RAIZ, "Artigo", "references.bib"))]
CACHE = os.path.join(RAIZ, "docs", "slr", "cache_crossref.json")
UA = "swarm-robotics-tese/1.0 (auditoria de bibliografia)"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def ler_bib(caminho):
    """{chave: {campo: valor}} de um .bib.

    ⚠️ O `\\n` acrescentado ao corpo não é decoração: o último campo de cada
    entrada (tipicamente o `doi`, sem vírgula final) vem colado ao `\\n}` que
    a fecha, e sem isto nunca era lido. A primeira versão deste leitor
    concluiu que «nenhuma das 45 entradas tem DOI» quando 19 têm.
    """
    if not os.path.exists(caminho):
        return {}
    txt = open(caminho, encoding="utf-8", errors="replace").read()
    entradas = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", txt, re.S):
        campos = {"__tipo__": m.group(1).lower()}
        for c in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*(?:\n|$)",
                             m.group(3) + "\n", re.S):
            campos[c.group(1).lower()] = " ".join(c.group(2).split())
        entradas[m.group(2).strip()] = campos
    return entradas


def citadas(caminho_tex):
    """As chaves citadas num `.tex` (\\cite, \\citep, \\citet, \\autocite)."""
    if not os.path.exists(caminho_tex):
        return set()
    txt = open(caminho_tex, encoding="utf-8", errors="replace").read()
    fora = set()
    for m in re.finditer(r"\\(?:auto|paren|foot)?cite[a-z]*\*?"
                         r"(?:\[[^\]]*\])*\{([^}]+)\}", txt):
        fora.update(x.strip() for x in m.group(1).split(","))
    return fora


def _sem_acentos(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# Os acentos do BibTeX têm de ser desfeitos ANTES de se limparem os comandos.
# `Rivi{\`e}re` com a limpeza pela ordem contrária fica `rivi ere`, e o
# verificador acusava o registo do CrossRef de não ter o autor que tem — dois
# falsos positivos numa auditoria cuja utilidade toda depende de não gritar
# lobo. O mesmo com `Ord{\'a}z-Rivas`.
_ACENTOS = re.compile(r"\{?\\[`'\"^~=.vHcuk]\s*\{?(?:\\([ij])|([a-zA-Z]))\}?\}?")
_LIGADURAS = {r"\\o": "o", r"\\O": "O", r"\\l": "l", r"\\L": "L",
              r"\\ss": "ss", r"\\ae": "ae", r"\\AE": "AE"}


def _limpo(s):
    """Normaliza para comparar: sem LaTeX, sem acentos, sem pontuação."""
    s = s or ""
    # `{\'\i}` (i sem pingo, como em «Rodríguez») tem por argumento um comando,
    # não uma letra: sem o segundo grupo ficava «rodr guez» e o verificador
    # acusava o CrossRef de não ter o autor que tem.
    s = _ACENTOS.sub(lambda m: m.group(1) or m.group(2), s)
    for lat, simples in _LIGADURAS.items():
        s = re.sub(lat + r"(?![a-zA-Z])", simples, s)
    s = re.sub(r"\\[a-zA-Z]+|[{}\\$]", "", s)
    s = _sem_acentos(s).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def apelidos(autor_bib):
    """['Bettini, Matteo', 'Prorok, Amanda'] -> ['bettini', 'prorok']."""
    saida = []
    for parte in re.split(r"\s+and\s+", autor_bib or ""):
        parte = parte.strip()
        if not parte:
            continue
        ap = parte.split(",")[0] if "," in parte else parte.split()[-1]
        saida.append(_limpo(ap))
    return saida


def carregar_cache():
    if os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as fh:
                return json.load(fh)
        except ValueError:
            pass
    return {}


def gravar_cache(cache):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1, sort_keys=True)


def _datacite(doi):
    """O mesmo, do DataCite — onde vivem teses e repositórios institucionais.

    O CrossRef indexa editoras; uma tese de doutoramento com DOI da própria
    universidade não está lá, e devolve 404. Isso não quer dizer que o DOI seja
    inválido — quer dizer que se perguntou à agência errada. Foi o que
    aconteceu com a tese de Iskandar (10.14750/ME.2026.007), que resolve e está
    registada no DataCite.
    """
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi)
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        at = json.load(r)["data"]["attributes"]
    autores = [c.get("familyName") or c.get("name", "")
               for c in at.get("creators", [])]
    ano = at.get("publicationYear")
    return {"autores": [a for a in autores if a], "ano": ano,
            "anos": [ano] if ano else [], "fonte": "datacite",
            "titulo": (at.get("titles") or [{}])[0].get("title", ""),
            "venue": at.get("publisher", "")}


def _por_titulo(titulo, ano=None):
    """O registo do MESMO trabalho, ou None. Nunca «o mais parecido».

    ⚠️ A primeira versão aceitava um candidato se ele contivesse 85% das
    palavras do título procurado, e isso deu oito acusações falsas de uma só
    vez: «Attention is All You Need» casou com «Is Attention All You Need?»
    (outro artigo, outro autor), «Particle swarm optimization» com
    «Introductory Chapter: Swarm Intelligence and Particle Swarm
    Optimization», e o livro do Tegmark com uma *recensão* do livro do
    Tegmark — cujo autor é, com toda a razão, o recenseador.

    Uma busca bibliográfica devolve sempre alguma coisa. Comparar autores
    contra o trabalho errado é pior do que não comparar: acusa de fabricação
    quem escreveu a referência certa. Agora exige-se
    **Jaccard ≥ 0,85 nas palavras do título** (bidirecional: nem falta nem
    sobra) e o **ano a menos de dois anos** do que a entrada declara.
    """
    q = urllib.parse.urlencode({"query.bibliographic": titulo, "rows": 5})
    pedido = urllib.request.Request("https://api.crossref.org/works?" + q,
                                    headers={"User-Agent": UA})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        itens = json.load(r)["message"].get("items", [])
    alvo = set(_limpo(titulo).split())
    if not alvo:
        return None
    for it in itens:
        t = (it.get("title") or [""])[0]
        cand = set(_limpo(t).split())
        if not cand:
            continue
        jaccard = len(alvo & cand) / float(len(alvo | cand))
        if jaccard < 0.85:
            continue
        partes = (it.get("issued", {}).get("date-parts") or [[None]])[0]
        ano_reg = partes[0] if partes else None
        if ano and ano_reg and abs(int(ano) - int(ano_reg)) > 1:
            continue
        autores = [a.get("family", "") for a in it.get("author", [])
                   if a.get("family")]
        if not autores:
            continue
        return {"autores": autores, "ano": ano_reg,
                "anos": [ano_reg] if ano_reg else [],
                "titulo": t, "venue": (it.get("container-title") or [""])[0]}
    return None


def consultar(doi):
    """Os campos que interessam, do registo do editor. Tenta CrossRef, depois
    DataCite — são agências diferentes, com catálogos diferentes."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            msg = json.load(r)["message"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return _datacite(doi)
    autores = [a.get("family", "") for a in msg.get("author", []) if a.get("family")]
    titulo = (msg.get("title") or [""])[0]

    # Dois anos, e ambos legítimos: `issued` é a primeira publicação (muitas
    # vezes *online first*) e `published-print` é a da edição em que o artigo
    # saiu. O Bredeche & Fontbonne saiu online em 2021 e na edição de 2022 —
    # citar 2022 está certo, e o verificador acusava-o com o `issued`.
    anos = []
    for chave in ("issued", "published-print", "published-online"):
        partes = (msg.get(chave, {}) or {}).get("date-parts") or []
        if partes and partes[0] and partes[0][0]:
            anos.append(partes[0][0])
    return {"autores": autores, "ano": anos[0] if anos else None,
            "anos": sorted(set(anos)), "titulo": titulo,
            "venue": (msg.get("container-title") or [""])[0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="não vai à rede; usa só o que está em cache")
    ap.add_argument("--renovar", action="store_true",
                    help="ignora a cache e volta a consultar tudo")
    a = ap.parse_args()

    tese = ler_bib(BIBS[0][1])
    artigo = ler_bib(BIBS[1][1])
    cit = citadas(os.path.join(RAIZ, "Tese", "main.tex")) | \
        citadas(os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex"))
    cit_art = citadas(os.path.join(RAIZ, "Artigo", "artigo.tex"))

    print("=" * 78)
    print("BIBLIOGRAFIA — as entradas citadas contra o registo dos editores")
    print("=" * 78)
    print("  tese: %d entradas, %d citadas | artigo: %d entradas, %d citadas"
          % (len(tese), len(cit), len(artigo), len(cit_art)))

    problemas = []

    # ── os dois .bib têm de dizer o mesmo sobre a mesma referência ──────────
    comuns = sorted(set(tese) & set(artigo))
    difs = []
    for k in comuns:
        for campo in sorted(set(tese[k]) | set(artigo[k])):
            if tese[k].get(campo, "") != artigo[k].get(campo, ""):
                difs.append("%s / %s: tese=%r artigo=%r"
                            % (k, campo, tese[k].get(campo, ""),
                               artigo[k].get(campo, "")))
    print("\n  %d entradas comuns aos dois .bib · %d divergências"
          % (len(comuns), len(difs)))
    for d in difs:
        print("     [X] " + d)
    problemas += difs

    for k in sorted(cit - set(tese)):
        problemas.append("a tese cita %s, que não existe no .bib" % k)
    for k in sorted(cit_art - set(artigo)):
        problemas.append("o artigo cita %s, que não existe no .bib dele" % k)

    # ── cada entrada citada com DOI, contra o CrossRef ──────────────────────
    cache = {} if a.renovar else carregar_cache()
    com_doi = sorted(k for k in cit if tese.get(k, {}).get("doi"))
    sem_doi = sorted(k for k in cit if k in tese and not tese[k].get("doi"))

    print("\n  citadas com DOI: %d · sem DOI: %d" % (len(com_doi), len(sem_doi)))
    print()
    novos = 0
    for k in com_doi:
        e = tese[k]
        doi = e["doi"]
        if doi not in cache:
            if a.offline:
                print("  [ ] %-24s sem cache e em modo offline" % k[:24])
                continue
            try:
                cache[doi] = consultar(doi)
                novos += 1
                time.sleep(0.4)          # não martelar a API pública
            except (urllib.error.URLError, ValueError, KeyError) as exc:
                print("  [X] %-24s DOI não resolve: %s (%s)"
                      % (k[:24], doi, type(exc).__name__))
                problemas.append("%s: o DOI %s não resolve no CrossRef"
                                 % (k, doi))
                continue
        reg = cache[doi]

        falhas = []
        aps = apelidos(e.get("author", ""))
        reg_aps = [_limpo(x) for x in reg["autores"]]
        if aps and reg_aps and aps[0] != reg_aps[0]:
            falhas.append("1.º autor: .bib diz «%s», o registo diz «%s»"
                          % (aps[0], reg_aps[0]))
        if aps and reg_aps and len(aps) != len(reg_aps):
            falhas.append("nº de autores: .bib %d, registo %d"
                          % (len(aps), len(reg_aps)))
        # Um apelido do .bib que não exista no registo é o defeito de julho.
        estranhos = [x for x in aps if x and x not in reg_aps]
        if estranhos:
            falhas.append("autores que o registo não tem: %s"
                          % ", ".join(estranhos))
        anos_reg = [str(x) for x in (reg.get("anos") or
                                     ([reg["ano"]] if reg.get("ano") else []))]
        if e.get("year") and anos_reg and str(e["year"]) not in anos_reg:
            falhas.append("ano: .bib %s, registo %s"
                          % (e["year"], "/".join(anos_reg)))
        t_bib, t_reg = _limpo(e.get("title", "")), _limpo(reg["titulo"])
        if t_bib and t_reg and t_bib not in t_reg and t_reg not in t_bib:
            comuns_pal = set(t_bib.split()) & set(t_reg.split())
            if len(comuns_pal) < 0.6 * len(set(t_bib.split())):
                falhas.append("título:\n          .bib    : %s\n"
                              "          registo : %s" % (e.get("title"),
                                                          reg["titulo"]))
        # As que já foram ao documento original ficam a informação, não falha.
        restantes = []
        for f in falhas:
            razao = DECLARADAS.get((k, f.split(":")[0]))
            if razao:
                print("  [i] %-26s %s" % (k[:26], f.split("\n")[0]))
                print("        declarada: %s" % razao)
            else:
                restantes.append(f)
        falhas = restantes

        if falhas:
            print("  [X] %s" % k)
            for f in falhas:
                print("        %s" % f)
            problemas += ["%s: %s" % (k, f.split(":")[0]) for f in falhas]
        else:
            print("  [v] %-26s %s (%s)" % (k[:26], (reg_aps[0] if reg_aps
                                                    else "?"), reg["ano"]))

    if novos:
        gravar_cache(cache)
        print("\n  (%d registos novos guardados em %s)"
              % (novos, os.path.relpath(CACHE, RAIZ)))

    # ── as que não têm DOI: procura-se o título no CrossRef ─────────────────
    #
    # Sem DOI não há registo para consultar diretamente, mas há busca. Uma
    # entrada cujo título exista e cujos autores NÃO correspondam é o defeito
    # de 16 jul — nomes fabricados sobre uma referência real. Uma entrada cujo
    # título não apareça de todo pode ser um clássico que o CrossRef não
    # indexa (livros, pré-publicações do arXiv, atas antigas), e por isso a
    # ausência aqui **não** é acusação: é um «vai ver à mão».
    if sem_doi:
        print("\n  SEM DOI — procurados pelo título no CrossRef:")
        for k in sem_doi:
            e = tese[k]
            titulo = e.get("title", "")
            chave_cache = "titulo:" + _limpo(titulo)[:80]
            if chave_cache not in cache and not a.offline:
                try:
                    cache[chave_cache] = _por_titulo(titulo, e.get("year"))
                    novos += 1
                    time.sleep(0.4)
                except Exception:                            # noqa: BLE001
                    cache[chave_cache] = None
            reg = cache.get(chave_cache)
            aps = apelidos(e.get("author", ""))
            if not reg:
                print("     [ ] %-24s %-30s (%s)  não indexado — ler à mão"
                      % (k[:24], (aps[0] if aps else "?")[:30],
                         e.get("year", "?")))
                continue
            reg_aps = [_limpo(x) for x in reg["autores"]]
            if aps and reg_aps and aps[0] == reg_aps[0]:
                print("     [v] %-24s %-30s (%s)"
                      % (k[:24], reg_aps[0][:30], reg["ano"]))
            else:
                print("     [X] %-24s .bib diz «%s», o registo do mesmo título "
                      "diz «%s»" % (k[:24], aps[0] if aps else "?",
                                    reg_aps[0] if reg_aps else "?"))
                print("           título encontrado: %s" % reg["titulo"][:70])
                problemas.append(
                    "%s: o 1.º autor não corresponde ao registo do título "
                    "(«%s» vs «%s»)" % (k, aps[0] if aps else "?",
                                        reg_aps[0] if reg_aps else "?"))
        if novos:
            gravar_cache(cache)

    print()
    print("=" * 78)
    if problemas:
        print("%d PROBLEMA(S):" % len(problemas))
        for p in problemas:
            print("   · %s" % p)
        print("=" * 78)
        return 1
    print("As %d entradas com DOI batem com o registo dos editores; os dois "
          ".bib estão sincronizados." % len(com_doi))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
