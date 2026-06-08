"""
restaurar_modelos.py — Restaura os modelos arquivados de uma sessão de treino
=============================================================================
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
GRAFICOS_DIR = os.path.join(PROJECT_ROOT, "results", "graficos_tese")
SUBS = ("models", "models_ppo", "models_sac")


def _sessions_with_models():
    """Sessões (pasta/modelos existe), mais recente primeiro."""
    out = []
    for d in glob.glob(os.path.join(GRAFICOS_DIR, "*")):
        if os.path.isdir(os.path.join(d, "modelos")):
            out.append(d)
    return sorted(out, key=os.path.getmtime, reverse=True)


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
