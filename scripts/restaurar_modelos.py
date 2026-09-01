"""
restaurar_modelos.py — Restaura os modelos arquivados de uma sessão de treino
Fluxo servidor → local:
  1. Treinas no servidor; ao fim, a pasta results/graficos_tese/<sessão>/ fica
     auto-contida (gráficos + heatmaps + mapas + subpasta 'modelos/').
  2. Copias essa pasta inteira para o teu PC (para dentro de results/graficos_tese/).
  3. Corres este script → copia os modelos de volta para results/models*,
     ficando prontos para o visualizador 3D e a avaliação.

Uso:
    python scripts/restaurar_modelos.py                 # usa a sessão mais recente
    python scripts/restaurar_modelos.py --sessao "results/graficos_tese/08-06-2026_07h48m"
    python scripts/restaurar_modelos.py --listar        # lista sessões com modelos
"""
import argparse
import glob
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Preciso para o `from scripts.verificar_sessao import ...` funcionar quando este
# ficheiro é corrido diretamente (`python scripts/restaurar_modelos.py`).
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
GRAFICOS_DIR = os.path.join(PROJECT_ROOT, "results", "graficos_tese")
SUBS = ("models", "models_ppo", "models_sac")


def _sessions_with_models():
    """Sessões com modelos arquivados, a mais recente primeiro.

    Ordenava por `os.path.getmtime`, e isso decide que modelos ficam
    ativos — é a armadilha nº9 na sua forma mais direta. O mtime de uma pasta
    muda quando lhe regeneram as figuras ou lhe copiam um CSV (é o que o
    `pos_campanha.py` faz no passo 2), e a partir daí uma campanha de meses atrás
    passa a ser «a mais recente». A 5 ago o mesmo defeito foi encontrado em
    `verificar_sessao.ultima_sessao()`, que devolvia uma campanha de maio.

    Ordena-se pela data no NOME (`DD-MM-AAAA_HHhMMm`), que é a data do treino e
    não muda quando alguém mexe na pasta. A regra vive no `verificar_sessao` para
    não haver duas — foi ter duas réguas que causou os erros deste dia.
    """
    from scripts.verificar_sessao import chave_de_recencia

    out = [d for d in glob.glob(os.path.join(GRAFICOS_DIR, "*"))
           if os.path.isdir(os.path.join(d, "modelos"))]
    return sorted(out, key=chave_de_recencia, reverse=True)


def restaurar(sessao_dir):
    src_root = os.path.join(sessao_dir, "modelos")
    if not os.path.isdir(src_root):
        print(f"[!] A sessão não tem pasta 'modelos': {sessao_dir}")
        return False
    total = 0
    for sub in SUBS:
        src = os.path.join(src_root, sub)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(PROJECT_ROOT, "results", sub)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith((".pth", ".zip")):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
                total += 1
    print(f"[OK] {total} modelos restaurados de '{os.path.basename(sessao_dir)}' -> results/models*")
    print("     Já podes visualizar/avaliar no launcher (usam results/models*).")
    return True


def main():
    parser = argparse.ArgumentParser(description="Restaura modelos arquivados de uma sessão")
    parser.add_argument("--sessao", default=None,
                        help="Caminho da pasta da sessão (default: a mais recente com modelos)")
    parser.add_argument("--listar", action="store_true", help="Lista sessões com modelos e sai")
    args = parser.parse_args()

    sessoes = _sessions_with_models()
    if args.listar:
        if not sessoes:
            print("Nenhuma sessão com modelos arquivados.")
        for s in sessoes:
            print(f"  {os.path.basename(s)}")
        return

    if args.sessao:
        sessao = args.sessao if os.path.isabs(args.sessao) else os.path.join(PROJECT_ROOT, args.sessao)
    elif sessoes:
        sessao = sessoes[0]
        print(f"[*] Sessão mais recente com modelos: {os.path.basename(sessao)}")
    else:
        print("[!] Nenhuma sessão com modelos arquivados. Treina (ou copia uma pasta do servidor) primeiro.")
        return

    restaurar(sessao)


if __name__ == "__main__":
    main()
