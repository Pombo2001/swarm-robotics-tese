"""Verifica se uma sessão de treino produziu TODOS os artefactos esperados.

Motivação: os passos pós-treino (avaliação, gráficos, heatmaps, vídeos) corriam dentro
de `try/except` que imprimiam "(não crítico)" e seguiam em frente. Uma falha no meio de
um log de centenas de MB passava despercebida, e a pasta da campanha ficava incompleta —
umas sessões com heatmaps, outras sem; umas com vídeos, outras sem. O resultado era
impossível de comparar entre campanhas.

Este módulo define o CONTRATO de uma sessão completa e verifica-o. Escreve na própria
pasta um MANIFESTO.md (o que existe / o que falta) e devolve código de saída != 0 se
faltar algo essencial — para que a falha seja visível ao fim do treino, e não três
semanas depois, quando se procura um heatmap para a tese.

Uso:
    python scripts/verificar_sessao.py                      # última sessão
    python scripts/verificar_sessao.py results/graficos_tese/09-07-2026_12h52m
"""
import os
import sys

# a consola do Windows é cp1252 e rebenta com os símbolos do relatório
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from src.scenarios import SCENARIOS, MAZE_SCENARIOS  # noqa: E402

SESSOES = os.path.join(BASE, 'results', 'graficos_tese')

# ── CONTRATO: o que uma sessão completa TEM de conter ────────────────────────
# (padrão, é_essencial, descrição)
def contrato(algos, scenarios):
    itens = [
        ('dados_historicos.csv',      True,  'curvas de treino'),
        ('dados_melhores_scores.csv', True,  'melhores scores'),
        # a avaliação TEM de viver dentro da sessão: é o que a torna auto-contida e
        # comparável no dashboard depois de a pasta global ser sobrescrita
        ('eval_summary.csv',          True,  'avaliação determinística (auto-contida)'),
        ('info_treino.yaml',          False, 'metadados da sessão'),
        ('comparacao_barras_geral.png', True, 'barras globais'),
        ('recolhas_por_cenario.png',  True,  'recolhas por cenário'),
        ('taxa_sucesso_por_cenario.png', True, 'taxa de sucesso'),
    ]
    for s in scenarios:
        itens.append((f'comparacao_mapa_{s}.png', True, f'curvas — {s}'))
        # O nome canónico do boxplot é `boxplot_eval_<cenário>` — o que a tese e o
        # artigo citam no \includegraphics. Este contrato exigia `boxplot_<cenário>`
        # (o nome antigo, do gerador de junho), e por isso dava a campanha CANÓNICA
        # da tese como incompleta enquanto aceitava figuras de uma campanha morta.
        # Ver scripts/figuras_campanha.py:NOMES, a fonte única.
        itens.append((f'boxplot_eval_{s}.png', False, f'boxplot — {s}'))
        itens.append((f'dotplot_eval_{s}.png', False, f'dot plot por run — {s}'))
        # heatmap de ocupação: um por algoritmo × cenário
        for a in algos:
            itens.append((f'heatmap_ocupacao_{a}_{s}.png', True,
                          f'heatmap de ocupação — {a}/{s}'))
    # heatmap geodésico: só faz sentido nos cenários com paredes
    for s in scenarios:
        if s in MAZE_SCENARIOS:
            itens.append((f'heatmap_geodesico_{s}.png', True, f'heatmap geodésico — {s}'))
    for a in algos:
        itens.append((f'desempenho_global_{a}.png', False, f'desempenho global — {a}'))
    return itens


def verificar(pasta, algos=('gnn', 'ppo', 'sac'), scenarios=None):
    scenarios = scenarios or SCENARIOS
    itens = contrato(algos, scenarios)

    existentes, faltam, faltam_essenciais = [], [], []
    for nome, essencial, desc in itens:
        if os.path.exists(os.path.join(pasta, nome)):
            existentes.append(nome)
        else:
            faltam.append((nome, essencial, desc))
            if essencial:
                faltam_essenciais.append((nome, desc))

    # vídeos: contam-se, mas nunca são essenciais (podem ser desligados)
    dir_vid = os.path.join(pasta, 'videos')
    n_videos = len([f for f in os.listdir(dir_vid)
                    if f.endswith('.gif')]) if os.path.isdir(dir_vid) else 0

    linhas = [
        f'# Manifesto da sessão `{os.path.basename(pasta)}`',
        '',
        f'- Artefactos esperados: **{len(itens)}**',
        f'- Presentes: **{len(existentes)}**',
        f'- Em falta: **{len(faltam)}** (dos quais **{len(faltam_essenciais)} essenciais**)',
        f'- Vídeos (GIF): {n_videos}',
        '',
    ]
    if faltam_essenciais:
        linhas += ['## ⚠️ EM FALTA (essenciais)', '']
        linhas += [f'- `{n}` — {d}' for n, d in faltam_essenciais] + ['']
    opcionais = [(n, d) for n, e, d in faltam if not e]
    if opcionais:
        linhas += ['## Em falta (opcionais)', '']
        linhas += [f'- `{n}` — {d}' for n, d in opcionais] + ['']
    if not faltam:
        linhas += ['✅ Sessão **completa**: todos os artefactos do contrato estão presentes.', '']

    with open(os.path.join(pasta, 'MANIFESTO.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas))

    return faltam_essenciais, len(existentes), len(itens), n_videos


def ultima_sessao():
    if not os.path.isdir(SESSOES):
        return None
    cands = [os.path.join(SESSOES, d) for d in os.listdir(SESSOES)
             if os.path.isdir(os.path.join(SESSOES, d)) and d[:2].isdigit()]
    return max(cands, key=os.path.getmtime) if cands else None


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else ultima_sessao()
    if not pasta or not os.path.isdir(pasta):
        print('[!] Sessão não encontrada.')
        return 1

    faltam, n_ok, n_tot, n_vid = verificar(pasta)
    print(f'\nSESSÃO: {os.path.basename(pasta)}')
    print(f'  artefactos: {n_ok}/{n_tot}   vídeos: {n_vid}')
    if faltam:
        print(f'\n  ⚠️  {len(faltam)} ARTEFACTOS ESSENCIAIS EM FALTA:')
        for n, d in faltam[:12]:
            print(f'      - {n}  ({d})')
        if len(faltam) > 12:
            print(f'      ... e mais {len(faltam) - 12}')
        print(f'\n  Detalhe em {os.path.join(pasta, "MANIFESTO.md")}')
        return 1
    print('  ✅ sessão completa\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
