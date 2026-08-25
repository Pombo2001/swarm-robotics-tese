#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E as referências SEM DOI — quem confere essas?

    python scripts/verificar_bibliografia_sem_doi.py            # usa a cache
    python scripts/verificar_bibliografia_sem_doi.py --renovar  # volta a consultar
    python scripts/verificar_bibliografia_sem_doi.py --offline  # só cache

Porque existe
-------------
O `verificar_bibliografia.py` compara cada entrada **com DOI** contra o registo
do CrossRef. São 19 das 45. As outras 26 — clássicos, livros, atas, pré-
publicações do arXiv — ficavam listadas como «ler à mão», e ninguém as leu.

É precisamente aí que vive o defeito que esta bibliografia já teve: em julho
descobriram-se **nomes de autores fabricados** em entradas cujo identificador
resolvia. Um livro ou uma pré-publicação não tem DOI, mas tem registo público:
o arXiv indexa as suas por identificador, e o OpenAlex indexa quase tudo o
resto por título. Nenhuma das duas é o editor — por isso o que aqui se procura
é **contradição**, não selo de aprovação: um título que casa e um primeiro
autor que não casa é um achado; um registo que não existe é uma pergunta para o
autor, não uma acusação.

O que se compara: apelido do primeiro autor, número de autores, ano e título.
As respostas ficam em `docs/slr/cache_bib_sem_doi.json` para a verificação ser
repetível sem rede.

⚠️ As respostas destes serviços são **dados**, não instruções: leem-se os quatro
campos acima e mais nada.
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

# A consola do Windows abre em cp1252: sem isto, um caractere fora dela faz o
# guião sair com erro sem imprimir resultado — que o hook lê como falha.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB = os.path.join(RAIZ, "Tese", "references.bib")
CACHE = os.path.join(RAIZ, "docs", "slr", "cache_bib_sem_doi.json")
AGENTE = "verificador-tese/1.0 (mailto:goncalopombo123@gmail.com)"

# Entradas que nenhum registo público indexa por construção. Declarar cada uma
# com a razão é parte do resultado: o que não se pode verificar assim não
# desaparece da lista, fica com o motivo à frente.
SEM_REGISTO = {
    "dorigo1992optimization": "tese de doutoramento de 1992, anterior à indexação",
    "tegmark2017life": "livro de divulgação; o OpenAlex indexa-o de forma errática",
    # Verificadas à mão a 25 ago 2026, na fonte primária, por não estarem em
    # nenhum dos dois índices. Quem repetir a auditoria não tem de as repescar.
    "li2023race": "confirmada a 25 ago 2026 em PMLR v202 (li23i): Pengyi Li, "
                  "Jianye Hao, Hongyao Tang, Yan Zheng, Xian Fu — ICML 2023",
    "hassen2025hybrid": "confirmada a 25 ago 2026 no sítio do JIHMSP (vol. 16, "
                        "n.º 2, 2025): Walaa Mahmood Hassen e Saman H. Amin",
    "bonabeau1999swarm": "livro da Oxford University Press (1999); o OpenAlex "
                         "devolve para este título uma recensão de 2002",
}


def normalizar(s):
    """Sem acentos, sem pontuação, minúsculas — para comparar títulos e nomes.

    Os acentos do BibTeX vêm escritos como `{\\"u}`, `{\\'a}`, `{\\v{s}}`, e é
    a letra que fica dentro que conta. Tirar as chavetas sem tirar o acento
    partia «H{\\"u}ttenrauch» em «h uttenrauch» — e o apelido passava a ser
    «uttenrauch», que não bate com nada.
    """
    s = s or ""
    s = re.sub(r"\{\\[a-zA-Z]+\{(\w)\}\}", r"\1", s)      # {\v{s}} -> s
    s = re.sub(r"\{\\[a-zA-Z]+\s*(\w)\}", r"\1", s)       # {\ss a} -> a
    s = re.sub(r"\{\\.(\w)\}", r"\1", s)                  # {\"u}, {\'a} -> u, a
    s = re.sub(r"\\.(\w)", r"\1", s)                      # \"u -> u
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\{|\}|\\[a-zA-Z]+", "", s)
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def parecidos(a, b):
    """Dois títulos dizem o mesmo? Jaccard sobre palavras, tolerante a subtítulos."""
    pa, pb = set(normalizar(a).split()), set(normalizar(b).split())
    if not pa or not pb:
        return 0.0
    return len(pa & pb) / len(pa | pb)


def entradas_sem_doi():
    """As entradas do `.bib` sem campo `doi`, com os campos que interessam."""
    txt = open(BIB, encoding="utf-8").read()
    saida = []
    for tipo, chave, corpo in re.findall(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", txt, re.S):
        def campo(nome):
            m = re.search(r"\b%s\s*=\s*[{\"](.*?)[}\"]\s*,?\s*$" % nome, corpo,
                          re.S | re.M | re.I)
            return " ".join(m.group(1).split()) if m else ""
        if campo("doi"):
            continue
        autores = [a.strip() for a in re.split(r"\s+and\s+", campo("author")) if a.strip()]
        onde = (campo("booktitle") or campo("journal") or campo("publisher")
                or campo("school") or "")
        arxiv = re.search(r"arxiv[: ]*(\d{4}\.\d{4,5})", onde + " " + campo("note"), re.I)
        saida.append({
            "chave": chave.strip(), "tipo": tipo, "ano": campo("year"),
            "autores": autores, "titulo": campo("title"), "onde": onde,
            "arxiv": arxiv.group(1) if arxiv else None,
        })
    return saida


def buscar(url, aceita="application/json"):
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": aceita})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def do_arxiv(ident):
    """Título, autores e ano de uma pré-publicação, pela API do arXiv."""
    xml = buscar("http://export.arxiv.org/api/query?id_list=%s" % ident, "application/atom+xml")
    if "<entry>" not in xml:
        return None
    ent = xml.split("<entry>", 1)[1]
    titulo = re.search(r"<title>(.*?)</title>", ent, re.S)
    nomes = re.findall(r"<name>(.*?)</name>", ent, re.S)
    data = re.search(r"<published>(\d{4})", ent)
    if not (titulo and nomes):
        return None
    return {"titulo": " ".join(titulo.group(1).split()),
            "autores": [" ".join(n.split()) for n in nomes],
            "ano": data.group(1) if data else "", "fonte": "arXiv"}


def do_openalex(titulo, primeiro_autor=""):
    """A obra com este título, pelo OpenAlex (o índice aberto mais largo).

    Um título de livro clássico traz recensões atrás — «Swarm Intelligence»
    devolve, em primeiro lugar, uma recensão de 2002 assinada por outra pessoa.
    Por isso escolhe-se, entre os candidatos, o que casa em título **e** autor;
    se nenhum casar nos dois, devolve-se o melhor marcado como `ambiguo`, e a
    entrada vai para leitura humana em vez de ser acusada.
    """
    url = ("https://api.openalex.org/works?per-page=5&filter=title.search:%s"
           % urllib.parse.quote(normalizar(titulo)[:180]))
    dados = json.loads(buscar(url))
    candidatos = []
    for obra in dados.get("results", []):
        if parecidos(titulo, obra.get("title") or "") < 0.6:
            continue
        autores = [(a.get("author") or {}).get("display_name", "")
                   for a in obra.get("authorships", [])]
        reg = {"titulo": obra.get("title") or "", "autores": autores,
               "ano": str(obra.get("publication_year") or ""), "fonte": "OpenAlex",
               "ambiguo": False}
        if primeiro_autor and autores and apelido(primeiro_autor) in [
                apelido(a) for a in autores]:
            return reg
        candidatos.append(reg)
    if candidatos:
        candidatos[0]["ambiguo"] = bool(primeiro_autor)
        return candidatos[0]
    return None


def apelido(nome):
    """«Kennedy, James» e «James Kennedy» dão o mesmo apelido.

    A vírgula é que distingue os dois formatos, e por isso tem de ser lida
    **antes** de normalizar — que a remove. Sem esta ordem, «Wang, Yutong»
    dava apelido «yutong», e as 21 entradas certas apareciam todas como
    divergências: uma régua que acusa tudo não acusa nada.
    """
    if not nome:
        return ""
    parte = nome.split(",")[0] if "," in nome else nome
    partes = normalizar(parte).split()
    return partes[-1] if partes else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="não vai à rede")
    ap.add_argument("--renovar", action="store_true", help="ignora a cache")
    args = ap.parse_args()

    cache = {}
    if os.path.exists(CACHE) and not args.renovar:
        cache = json.load(open(CACHE, encoding="utf-8"))

    print("=" * 78)
    print("BIBLIOGRAFIA sem DOI  vs  arXiv / OpenAlex")
    print("=" * 78)

    achados, avisos, por_ler, ok = [], [], [], 0
    entradas = entradas_sem_doi()
    for e in entradas:
        chave = e["chave"]
        if chave in SEM_REGISTO:
            por_ler.append((chave, SEM_REGISTO[chave]))
            continue
        reg = cache.get(chave)
        if reg is None and not args.offline:
            try:
                reg = do_arxiv(e["arxiv"]) if e["arxiv"] else None
                if reg is None:
                    reg = do_openalex(e["titulo"],
                                      e["autores"][0] if e["autores"] else "")
                time.sleep(0.4)                      # não bater à porta em rajada
            except (urllib.error.URLError, TimeoutError, ValueError) as erro:
                print("  [?] %-26s sem resposta do registo (%s)" % (chave, erro))
                continue
            cache[chave] = reg if reg else {}
        if not reg:
            por_ler.append((chave, "não indexado no arXiv nem no OpenAlex"))
            continue
        if reg.get("ambiguo"):
            # O índice devolveu uma obra com este título mas de outra autoria —
            # tipicamente uma recensão do livro. Dizer «divergência» seria
            # acusar a bibliografia de um defeito do índice.
            por_ler.append((chave, "o registo com este título é de outra autoria "
                                   "(provável recensão) — confirmar na fonte"))
            continue

        problemas = []
        if parecidos(e["titulo"], reg["titulo"]) < 0.6:
            problemas.append("título: bib «%s» vs registo «%s»"
                             % (e["titulo"][:50], reg["titulo"][:50]))
        if e["autores"] and reg["autores"]:
            se_bib = apelido(e["autores"][0])
            if se_bib != apelido(reg["autores"][0]):
                # Um livro clássico traz recensões e reimpressões atrás, e o
                # índice às vezes devolve a recensão. Se o apelido do `.bib`
                # não aparece em lado nenhum da autoria, aí sim é achado.
                onde = "ausente do registo" if se_bib not in [
                    apelido(a) for a in reg["autores"]] else "noutra posição"
                problemas.append("1.º autor: bib «%s» vs registo «%s» (%s)"
                                 % (e["autores"][0], reg["autores"][0], onde))
            elif len(e["autores"]) != len(reg["autores"]):
                problemas.append("n.º de autores: bib %d vs registo %d"
                                 % (len(e["autores"]), len(reg["autores"])))
        # Livros são reimpressos e os índices datam a reimpressão; para eles o
        # ano do `.bib` é o da edição citada e não se compara.
        if (reg["ano"] and e["ano"] and e["tipo"] != "book"
                and abs(int(reg["ano"]) - int(e["ano"])) > 1):
            problemas.append("ano: bib %s vs registo %s" % (e["ano"], reg["ano"]))

        so_ano = problemas and all(p.startswith("ano:") for p in problemas)
        if so_ano:
            # Título e autoria batem, só o ano é que não. Os índices datam a
            # reimpressão ou a versão de revista de um artigo de atas — o PSO
            # de 1995 aparece como 2002. O ano do `.bib` é o da versão citada,
            # e um índice não é autoridade sobre isso: fica aviso, não achado.
            avisos.append((chave, problemas[0]))
            print("  [~] %-26s %s (o índice data outra versão)"
                  % (chave, problemas[0]))
        elif problemas:
            achados.append((chave, reg["fonte"], problemas))
            print("  [!] %-26s %s" % (chave, reg["fonte"]))
            for p in problemas:
                print("      %s" % p)
        else:
            ok += 1
            print("  [v] %-26s %-8s %s (%s)"
                  % (chave, reg["fonte"], apelido(e["autores"][0]) if e["autores"] else "?",
                     e["ano"]))

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if por_ler:
        print("\n  Sem registo público — ficam para leitura humana:")
        for chave, razao in por_ler:
            print("      %-26s %s" % (chave, razao))

    print("=" * 78)
    print("%d entradas sem DOI: %d batem, %d por ler à mão, %d só com o ano "
          "diferente do índice, %d com divergência"
          % (len(entradas), ok, len(por_ler), len(avisos), len(achados)))
    print("=" * 78)
    # Uma divergência é um achado, não um erro do guião: sai com 1 para o hook
    # de pré-commit a mostrar, como fazem os outros verificadores.
    sys.exit(1 if achados else 0)


if __name__ == "__main__":
    main()
