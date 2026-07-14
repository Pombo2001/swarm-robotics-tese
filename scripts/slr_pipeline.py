"""Pipeline da revisão sistemática (SLR) — ver docs/PROTOCOLO_SLR.md.

O ponto desta ferramenta é que o fluxograma PRISMA da tese passa a ser *derivado*
dos dados da triagem, e não escrito à mão. Se o CSV disser 87 registos triados, a
figura diz 87. Não há maneira de os números divergirem do que foi feito.

Fluxo:
    1. Exporta os resultados de cada base para docs/slr/raw/<base>.csv (ou .bib)
    2. python scripts/slr_pipeline.py ingest      -> cria/atualiza docs/slr/screening.csv
    3. (à mão) preenches as colunas 'decisao' e 'motivo' no screening.csv
    4. python scripts/slr_pipeline.py estado      -> mostra quanto falta triar
    5. python scripts/slr_pipeline.py prisma      -> gera Tese/prisma_gerado.tex
                                                     + Tese/apendice_slr.tex

Colunas de screening.csv:
    origem      base de dados (ou 'snowball')
    doi, titulo, autores, ano, venue
    fase        'titulo_resumo' ou 'texto_integral'
    decisao     '' (por decidir) | 'incluir' | 'excluir'
    motivo      E1..E5 (obrigatório se decisao=excluir); ver protocolo
    notas       livre
"""
import csv
import glob
import os
import re
import sys
import unicodedata

# os títulos trazem caracteres que a consola cp1252 do Windows não sabe imprimir
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_SLR = os.path.join(RAIZ, 'docs', 'slr')
DIR_RAW = os.path.join(DIR_SLR, 'raw')
SCREENING = os.path.join(DIR_SLR, 'screening.csv')

COLUNAS = ['origem', 'doi', 'titulo', 'autores', 'ano', 'venue',
           'fase', 'decisao', 'motivo', 'notas']

MOTIVOS = {
    'E1': 'Robô único / sem componente de enxame',
    'E2': 'Sem validação experimental (revisão ou artigo conceptual)',
    'E3': 'Sem dados quantitativos comparáveis',
    'E4': 'Não revisto por pares / integridade da publicação em causa',
    'E5': 'Duplicado',
    'E6': 'Método fora do âmbito (nem MARL nem otimização bio-inspirada)',
    'E7': 'Tarefa fora do âmbito da revisão (alocação/escalonamento, SLAM, '
          'comunicações, manipulação — a revisão cobre navegação, exploração, '
          'foraging, formação e coordenação de movimento em enxame)',
}


# rótulos curtos, para caberem nas caixas do fluxograma
CURTO = {
    'E1': 'Robô único (sem enxame)',
    'E2': 'Revisão / sem validação experimental',
    'E3': 'Sem dados quantitativos',
    'E4': 'Sem revisão por pares / integridade',
    'E5': 'Duplicado não detetado automaticamente',
    'E6': 'Método fora do âmbito (nem MARL nem bio-inspirado)',
    'E7': 'Tarefa fora do âmbito (alocação, SLAM, comunicações, manipulação)',
    'E8': 'Fora do núcleo (não é enxame em venue de referência)',
}


def _norm(s):
    """Título normalizado para deteção de duplicados (sem acentos/pontuação)."""
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s)


def _ler_bib(caminho):
    txt = open(caminho, encoding='utf-8', errors='replace').read()
    saida = []
    for bloco in re.split(r'\n@', '\n' + txt)[1:]:
        c = {}
        for m in re.finditer(r'(\w+)\s*=\s*[{"](.+?)[}"],?\s*\n', bloco, re.S):
            c[m.group(1).lower()] = re.sub(r'\s+', ' ', re.sub(r'[{}]', '', m.group(2))).strip()
        if c.get('title'):
            saida.append({
                'doi': c.get('doi', ''), 'titulo': c['title'],
                'autores': c.get('author', ''), 'ano': c.get('year', ''),
                'venue': c.get('journal') or c.get('booktitle', ''),
            })
    return saida


def _ler_csv(caminho):
    """Aceita exports do Scopus/IEEE/ACM: procura as colunas por nome aproximado."""
    saida = []
    with open(caminho, encoding='utf-8-sig', errors='replace', newline='') as f:
        for linha in csv.DictReader(f):
            baixo = {(k or '').strip().lower(): (v or '').strip()
                     for k, v in linha.items()}

            def pega(*nomes):
                for n in nomes:
                    for k, v in baixo.items():
                        if k == n or k.startswith(n):
                            if v:
                                return v
                return ''

            titulo = pega('title', 'document title', 'item title')
            if not titulo:
                continue
            saida.append({
                'doi': pega('doi'),
                'titulo': titulo,
                'autores': pega('authors', 'author'),
                'ano': pega('year', 'publication year'),
                'venue': pega('source title', 'publication title', 'proceedings title'),
            })
    return saida


def ingest():
    os.makedirs(DIR_RAW, exist_ok=True)
    ficheiros = sorted(glob.glob(os.path.join(DIR_RAW, '*.csv')) +
                       glob.glob(os.path.join(DIR_RAW, '*.bib')))
    if not ficheiros:
        sys.exit(f'[!] Sem exports em {DIR_RAW}/ — ver docs/PROTOCOLO_SLR.md §5.')

    # o que já foi triado NÃO se perde ao re-ingerir
    ja = {}
    if os.path.exists(SCREENING):
        with open(SCREENING, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                ja[r.get('doi') or _norm(r.get('titulo'))] = r

    registos, brutos, duplicados = [], 0, 0
    vistos = {}
    for caminho in ficheiros:
        base = os.path.splitext(os.path.basename(caminho))[0]
        lidos = _ler_bib(caminho) if caminho.endswith('.bib') else _ler_csv(caminho)
        brutos += len(lidos)
        for r in lidos:
            # tem de verificar DOI *e* título: um registo com DOI numa base e sem DOI
            # noutra escapava à deteção quando só se usava a primeira chave disponível
            chaves = [k for k in (r['doi'].lower(), _norm(r['titulo'])) if k]
            if any(k in vistos for k in chaves):
                duplicados += 1
                continue
            for k in chaves:
                vistos[k] = True
            anterior = ja.get(r['doi'].lower()) or ja.get(_norm(r['titulo'])) or {}
            registos.append({
                'origem': anterior.get('origem') or base,
                'doi': r['doi'], 'titulo': r['titulo'], 'autores': r['autores'],
                'ano': r['ano'], 'venue': r['venue'],
                'fase': anterior.get('fase', 'titulo_resumo'),
                'decisao': anterior.get('decisao', ''),
                'motivo': anterior.get('motivo', ''),
                'notas': anterior.get('notas', ''),
            })

    os.makedirs(DIR_SLR, exist_ok=True)
    with open(SCREENING, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(registos)

    print(f'Ficheiros lidos:        {len(ficheiros)}')
    print(f'Registos identificados: {brutos}')
    print(f'Duplicados removidos:   {duplicados}')
    print(f'Registos únicos:        {len(registos)}  -> {SCREENING}')
    print('\nPróximo passo: preencher "decisao" (incluir/excluir) e "motivo" (E1..E5).')


def _carregar():
    if not os.path.exists(SCREENING):
        sys.exit('[!] Corre primeiro: python scripts/slr_pipeline.py ingest')
    with open(SCREENING, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _contas(regs):
    """Números REAIS do PRISMA, derivados do screening.csv."""
    pesquisa = [r for r in regs if r['origem'] != 'snowball']
    unicos = len(pesquisa)
    tr = [r for r in pesquisa if r['fase'] == 'titulo_resumo']
    excl_tr = [r for r in tr if r['decisao'] == 'excluir']
    integral = [r for r in pesquisa if r['fase'] == 'texto_integral']
    excl_int = [r for r in integral if r['decisao'] == 'excluir']
    incluidos = [r for r in regs if r['decisao'] == 'incluir']
    por_motivo, por_motivo_tr = {}, {}
    for r in excl_int:
        por_motivo[r['motivo']] = por_motivo.get(r['motivo'], 0) + 1
    for r in excl_tr:
        por_motivo_tr[r['motivo']] = por_motivo_tr.get(r['motivo'], 0) + 1
    return {
        'unicos': unicos,
        'triados': len(tr) + len(integral),
        'excluidos_triagem': len(excl_tr),
        'texto_integral': len(integral),
        'excluidos_integral': len(excl_int),
        'incluidos': len(incluidos),
        'por_motivo': por_motivo,
        'por_motivo_triagem': por_motivo_tr,
        'lista': sorted(incluidos, key=lambda r: (r['ano'], r['autores'])),
        'por_decidir': [r for r in regs if not r['decisao']],
    }


def _abstracts():
    """Mapa {chave -> resumo} construído a partir dos exports em bruto.

    O screening.csv não guarda os resumos (ficaria ilegível para edição manual);
    vão-se buscar aos raw/ quando são precisos para triar.
    """
    mapa = {}
    for caminho in sorted(glob.glob(os.path.join(DIR_RAW, '*.csv'))):
        with open(caminho, encoding='utf-8-sig', errors='replace', newline='') as f:
            for linha in csv.DictReader(f):
                baixo = {(k or '').strip().lower(): (v or '').strip()
                         for k, v in linha.items()}
                titulo = baixo.get('title') or baixo.get('document title') or ''
                doi = baixo.get('doi', '')
                resumo = baixo.get('abstract', '')
                if not resumo:
                    continue
                if doi:
                    mapa[doi.lower()] = resumo
                mapa[_norm(titulo)] = resumo
    return mapa


def lote():
    """Mostra os próximos N registos por decidir, com resumo, para triagem."""
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    chars = int(sys.argv[3]) if len(sys.argv) > 3 else 700
    regs = _carregar()
    resumos = _abstracts()
    pendentes = [(i, r) for i, r in enumerate(regs) if not r['decisao']][:n]
    for i, r in pendentes:
        chave = r['doi'].lower() if r['doi'] else _norm(r['titulo'])
        resumo = resumos.get(chave) or resumos.get(_norm(r['titulo'])) or '(sem resumo)'
        print(f"[{i}] {r['ano']} | {r['titulo']}")
        print(f"    {resumo[:chars]}")
    print(f"--- {len(pendentes)} registos mostrados; {len(regs) - len([r for r in regs if r['decisao']])} por decidir no total")


def promover():
    """Passa os incluídos na triagem para a fase de texto integral.

    O PRISMA distingue as duas fases: quem for excluído a partir daqui conta como
    'excluído em texto integral', e não como excluído na triagem.
    """
    regs = _carregar()
    n = 0
    for r in regs:
        if r['decisao'] == 'incluir' and r['fase'] == 'titulo_resumo':
            r['fase'] = 'texto_integral'
            r['decisao'] = ''          # volta a estar por decidir, agora na 2.ª fase
            n += 1
    with open(SCREENING, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(regs)
    print(f'{n} registos promovidos a texto_integral (por decidir na 2.ª fase).')


def aplicar():
    """Aplica decisões de um ficheiro 'idx|decisao|motivo' (uma por linha).

    A fase de cada registo é preservada: os que já estão em 'texto_integral'
    continuam lá, e as suas exclusões contam para a fase de elegibilidade.
    """
    if len(sys.argv) < 3:
        sys.exit('uso: aplicar <ficheiro_de_decisoes>')
    regs = _carregar()
    n = 0
    for linha in open(sys.argv[2], encoding='utf-8'):
        linha = linha.strip()
        if not linha or linha.startswith('#'):
            continue
        partes = [p.strip() for p in linha.split('|')]
        idx, decisao = int(partes[0]), partes[1]
        motivo = partes[2] if len(partes) > 2 else ''
        if decisao not in ('incluir', 'excluir'):
            sys.exit(f'[!] decisão inválida na linha: {linha}')
        if decisao == 'excluir' and not motivo:
            sys.exit(f'[!] exclusão sem motivo (E1..E7): {linha}')
        regs[idx]['decisao'] = decisao
        regs[idx]['motivo'] = motivo
        if not regs[idx]['fase']:
            regs[idx]['fase'] = 'titulo_resumo'
        n += 1
    with open(SCREENING, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(regs)
    print(f'{n} decisões aplicadas -> {SCREENING}')


def estado():
    c = _contas(_carregar())
    print(f"Registos únicos:      {c['unicos']}")
    print(f"Já decididos:         {c['unicos'] - len(c['por_decidir'])}")
    print(f"POR DECIDIR:          {len(c['por_decidir'])}")
    print(f"Incluídos até agora:  {c['incluidos']}")
    if c['por_decidir']:
        print('\nPor triar (primeiros 10):')
        for r in c['por_decidir'][:10]:
            print(f"  - [{r['ano']}] {r['titulo'][:80]}")


def _esc(s):
    s = s or ''
    # o Scopus anexa a tradução do título no idioma original entre parênteses retos
    # ("Título em inglês; [中文标题]"); o pdfLaTeX não sabe compor cirílico nem CJK
    s = re.sub(r';?\s*\[[^\]]*\]\s*$', '', s)
    s = ''.join(c for c in s if ord(c) < 0x250)   # deixa só latino + diacríticos
    for a, b in (('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('_', r'\_'),
                 ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def _autores(raw):
    """'Silva A.; Costa R.' (Scopus) ou 'A. Silva; R. Costa' (IEEE) -> 'Silva et al.'

    As duas bases exportam em formatos distintos: o Scopus põe o apelido primeiro
    ('Hasselmann K.'), o IEEE põe as iniciais primeiro ('K. Hasselmann'). Distinguem-se
    procurando qual dos tokens *não* é uma inicial. Uma inicial não tem minúsculas
    ('K.', 'H.', '-S.' nos nomes compostos do IEEE, como em 'H. -S. Liu'), um apelido tem.
    """
    def apelido(a):
        toks = [t for t in a.replace(',', ' ').split() if t]
        reais = [t for t in toks if re.search(r'[a-zà-ÿ]', t)]
        return reais[0] if reais else (toks[0] if toks else '')

    autores = [a.strip() for a in re.split(r'\s+and\s+|;', raw or '') if a.strip()]
    ape = [_esc(apelido(a)) for a in autores]
    ape = [a for a in ape if a]
    if not ape:
        return '---'
    if len(ape) == 1:
        return ape[0]
    if len(ape) == 2:
        return f'{ape[0]} \\& {ape[1]}'
    return f'{ape[0]} et al.'


def prisma():
    regs = _carregar()
    c = _contas(regs)
    if c['por_decidir']:
        print(f"[!] Ainda há {len(c['por_decidir'])} registos por decidir. "
              f"O PRISMA gerado seria incompleto — tria-os primeiro.")
        sys.exit(1)

    # fase de identificação: contam-se os registos EM BRUTO nos exports das bases
    brutos, por_base = 0, {}
    for caminho in sorted(glob.glob(os.path.join(DIR_RAW, '*.csv')) +
                          glob.glob(os.path.join(DIR_RAW, '*.bib'))):
        base = os.path.splitext(os.path.basename(caminho))[0]
        n = len(_ler_bib(caminho) if caminho.endswith('.bib') else _ler_csv(caminho))
        por_base[base] = n
        brutos += n
    duplicados = brutos - c['unicos']
    fontes = ' + '.join(f'{b.capitalize()} {n}' for b, n in sorted(por_base.items()))

    def _lista(dic):
        return ' \\\\ '.join(f"$\\bullet$ {_esc(CURTO.get(m, m))}: {n}"
                             for m, n in sorted(dic.items())) or '---'

    tex = os.path.join(RAIZ, 'Tese', 'prisma_gerado.tex')
    with open(tex, 'w', encoding='utf-8') as f:
        f.write(f"""% GERADO por scripts/slr_pipeline.py a partir de docs/slr/screening.csv
% NÃO editar à mão: os números vêm da triagem real. Ver docs/PROTOCOLO_SLR.md
\\begin{{figure}}[H]
    \\centering
    \\begin{{tikzpicture}}[node distance=1.2cm]
    \\tikzstyle{{process}} = [rectangle, minimum width=5.2cm, minimum height=1.1cm,
        text centered, draw=black, fill=white, text width=5.2cm, font=\\small]
    \\tikzstyle{{saida}} = [rectangle, minimum height=1.1cm, draw=black, fill=black!3,
        text width=5.4cm, font=\\scriptsize, align=left]
    \\tikzstyle{{arrow}} = [thick,->,>=stealth]
    \\tikzstyle{{lado}} = [rotate=90, anchor=south, font=\\bfseries\\footnotesize,
        color=black!60]

    \\node (id) [process] {{Registos identificados nas bases de dados \\\\
        \\scriptsize ({fontes}) \\\\ \\textbf{{(n = {brutos})}}}};
    \\node (dup) [saida, right=1.3cm of id] {{Duplicados removidos \\\\
        (DOI ou título normalizado) \\\\ \\textbf{{(n = {duplicados})}}}};

    \\node (screen) [process, below=1.2cm of id] {{Registos únicos triados
        (título e resumo) \\\\ \\textbf{{(n = {c['triados']})}}}};
    \\node (exc1) [saida, right=1.3cm of screen] {{Excluídos na triagem
        \\textbf{{(n = {c['excluidos_triagem']})}} \\\\ {_lista(c['por_motivo_triagem'])}}};

    \\node (full) [process, below=2.1cm of screen] {{Avaliados em texto integral \\\\
        \\textbf{{(n = {c['texto_integral']})}}}};
    \\node (exc2) [saida, right=1.3cm of full] {{Excluídos na elegibilidade
        \\textbf{{(n = {c['excluidos_integral']})}} \\\\ {_lista(c['por_motivo'])}}};

    \\node (inc) [process, below=1.6cm of full, fill=black!5]
        {{\\textbf{{Estudos incluídos na revisão}} \\\\ \\textbf{{(n = {c['incluidos']})}}}};

    \\draw [arrow] (id) -- (screen);
    \\draw [arrow] (id) -- (dup);
    \\draw [arrow] (screen) -- (full);
    \\draw [arrow] (screen) -- (exc1);
    \\draw [arrow] (full) -- (inc);
    \\draw [arrow] (full) -- (exc2);

    \\node [lado] at (-3.6, 0) {{Identificação}};
    \\node [lado] at (-3.6, -2.4) {{Triagem}};
    \\node [lado] at (-3.6, -5.4) {{Elegibilidade}};
    \\node [lado] at (-3.6, -7.6) {{Inclusão}};
    \\end{{tikzpicture}}
    \\caption[Fluxograma PRISMA 2020 da revisão conduzida]{{Fluxograma PRISMA 2020 da
    revisão conduzida. Os números são gerados automaticamente a partir do registo de
    triagem (\\texttt{{docs/slr/screening.csv}} no repositório, Apêndice~\\ref{{apx:resources}}),
    onde cada decisão está associada ao respetivo critério de exclusão.}}
    \\label{{fig:prisma}}
\\end{{figure}}
""")

    apx = os.path.join(RAIZ, 'Tese', 'apendice_slr.tex')
    with open(apx, 'w', encoding='utf-8') as f:
        f.write('% GERADO por scripts/slr_pipeline.py — não editar à mão.\n')
        f.write(r'\begin{longtable}{@{}rp{2.4cm}rp{5.4cm}p{3.2cm}@{}}' + '\n')
        f.write(r'\caption{Estudos incluídos na revisão sistemática ($n = '
                + str(c['incluidos']) + r'$), resultantes do fluxo PRISMA '
                r'(Figura~\ref{fig:prisma}).}\label{tab:slr_incluidos}\\' + '\n')
        f.write(r'\hline' + '\n')
        f.write(r'\# & Autores & Ano & Título & Publicação \\ \hline' + '\n')
        f.write(r'\endfirsthead' + '\n')
        f.write(r'\hline \# & Autores & Ano & Título & Publicação \\ \hline \endhead'
                + '\n')
        for i, r in enumerate(c['lista'], 1):
            nome = _autores(r['autores'])
            f.write(f"{i} & {nome} & {r['ano']} & {_esc(r['titulo'])} & "
                    f"{_esc(r['venue'])} \\\\\n")
        f.write(r'\hline' + '\n' + r'\end{longtable}' + '\n')

    print(f"PRISMA gerado com números REAIS:")
    print(f"  identificados (únicos): {c['unicos']}")
    print(f"  triados:                {c['triados']}")
    print(f"  excluídos na triagem:   {c['excluidos_triagem']}")
    print(f"  texto integral:         {c['texto_integral']}")
    print(f"  excluídos no integral:  {c['excluidos_integral']}")
    print(f"  INCLUÍDOS:              {c['incluidos']}")
    print(f"\n  -> {tex}\n  -> {apx}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'ingest':
        ingest()
    elif cmd == 'lote':
        lote()
    elif cmd == 'promover':
        promover()
    elif cmd == 'aplicar':
        aplicar()
    elif cmd == 'estado':
        estado()
    elif cmd == 'prisma':
        prisma()
    else:
        sys.exit(__doc__)
