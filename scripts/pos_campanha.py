"""Checklist de chegada de uma campanha: um comando, três garantias.

Sempre que se traz uma campanha do servidor (ou se acaba um treino local), há três
coisas que TÊM de acontecer — e que, por não estarem num só sítio, foram esquecidas:

  1. RESTAURAR OS MODELOS para results/models*. Sem isto, tudo o que se corre depois
     (escalabilidade, vídeos, visualizador) usa os modelos da campanha ANTERIOR. Foi o
     que aconteceu com o treino de 7 dias: os modelos ficaram arquivados na sessão, a
     pasta ativa manteve os de junho, e a avaliação de escalabilidade deu 0 recolhas no
     bottleneck (contra as 121 reportadas) — durante dias, sem ninguém notar.

  2. TORNAR A SESSÃO AUTO-CONTIDA, copiando a avaliação para dentro da pasta. Sem isto,
     a campanha não aparece na comparação de treinos do dashboard, e perde-se quando a
     pasta global de avaliação for sobrescrita pela campanha seguinte.

  3. VERIFICAR O CONTRATO de artefactos. Uma campanha a que faltem heatmaps ou gráficos
     não é uma campanha — é uma armadilha para daqui a três semanas.

Uso:
    python scripts/pos_campanha.py                  # última sessão
    python scripts/pos_campanha.py results/graficos_tese/09-07-2026_12h52m
"""
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from scripts.verificar_sessao import ultima_sessao, verificar  # noqa: E402

EVAL_DIR = os.path.join(BASE, 'results', 'evaluation')


def copiar_eval_para_sessao(sess):
    copiados = []
    for nome in ('eval_summary.csv', 'eval_by_run.csv'):
        orig = os.path.join(EVAL_DIR, nome)
        if os.path.exists(orig):
            shutil.copy2(orig, os.path.join(sess, nome))
            copiados.append(nome)
    return copiados


def main():
    sess = sys.argv[1] if len(sys.argv) > 1 else ultima_sessao()
    if not sess or not os.path.isdir(sess):
        print('[!] Sessão não encontrada.')
        return 1
    nome = os.path.basename(sess)
    print(f'\n=== PÓS-CAMPANHA: {nome} ===\n')

    # 1. modelos
    print('[1/3] Restaurar modelos para results/models*')
    r = subprocess.run([sys.executable, os.path.join(BASE, 'scripts', 'restaurar_modelos.py'),
                        '--sessao', sess], capture_output=True, text=True)
    print('   ' + (r.stdout.strip().splitlines() or ['(sem modelos arquivados)'])[-1])

    # 2. sessão auto-contida
    print('\n[2/3] Copiar avaliação para dentro da sessão')
    cop = copiar_eval_para_sessao(sess)
    print(f'   {", ".join(cop) if cop else "(sem eval em results/evaluation/)"}')

    # 3. contrato
    print('\n[3/3] Verificar contrato de artefactos')
    faltam, n_ok, n_tot, n_vid = verificar(sess)
    print(f'   {n_ok}/{n_tot} artefactos · {n_vid} vídeos')
    if faltam:
        print(f'\n   ⚠️  {len(faltam)} ARTEFACTOS ESSENCIAIS EM FALTA:')
        for n, d in faltam[:10]:
            print(f'       - {n}  ({d})')
        print(f'\n   Detalhe em {os.path.join(sess, "MANIFESTO.md")}')
        return 1

    print('\n✅ Campanha pronta: modelos ativos, sessão auto-contida, artefactos completos.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
