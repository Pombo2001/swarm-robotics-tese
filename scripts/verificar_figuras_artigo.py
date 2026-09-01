# -*- coding: utf-8 -*-
"""As figuras do artigo acompanham as da dissertação?

Porque existe
As figuras do artigo são cópias das da tese. Quando uma figura da tese é
regenerada, a cópia do artigo não muda — e nada acusa: o artigo compila, as
legendas continuam a fazer sentido e o número lá dentro está certo, só que é o
de outra versão. Já aconteceu duas vezes neste projeto: oito figuras
desatualizadas numa revisão, e três noutra (a escalabilidade que parecia ter só
a GNN, o potencial geodésico ilegível e o mega-treino a dizer «runs»).

Três verificações:

1. Cópias sincronizadas. Uma figura do artigo com homónima na tese tem de
   ser byte a byte a mesma imagem.
2. Versões próprias. As `*_col.png` são redesenhadas para a coluna de
   8,9 cm do artigo (`scripts/figuras_artigo.py`) e por isso NÃO são iguais às
   da tese — mas não podem ser mais VELHAS do que a figura de que derivam: se
   a da tese foi regenerada depois, a do artigo ficou para trás.
3. Órfãs. Ficheiros em `Artigo/images/` que o artigo não usa.

Uso:
    python scripts/verificar_figuras_artigo.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                            # noqa: BLE001
    pass

import numpy as np
from PIL import Image, ImageChops

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(RAIZ, "Artigo")
TESE = os.path.join(RAIZ, "Tese")
PIXEIS_MINIMOS = 50

# Cada versão própria e a figura da tese de que deriva. O verificador não
# compara os pixels destas (são desenhos diferentes de propósito) — compara a
# data: a do artigo não pode ser anterior.
VERSOES_PROPRIAS = {
    "escalabilidade_zeroshot_none_col.png": "escalabilidade_zeroshot_none.png",
    "heatmap_geodesico_u_wall_col.png": "heatmap_geodesico_u_wall.png",
    "megatreino_u_wall_4bracos_col.png": "megatreino_u_wall_4bracos.png",
}


def _da_tese(base):
    for c in (os.path.join(TESE, "images", base),
              os.path.join(TESE, "images", "resultados", base)):
        if os.path.exists(c):
            return c
    return None


def main():
    print("=" * 74)
    print("FIGURAS DO ARTIGO  vs  FIGURAS DA DISSERTAÇÃO")
    print("=" * 74)

    tex_path = os.path.join(ART, "artigo.tex")
    tex = re.sub(r"(?<!\\)%[^\n]*", "", open(tex_path, encoding="utf-8").read())
    usadas = sorted(set(re.findall(
        r"\\includegraphics\[[^\]]*\]\{(images/[^}]+)\}", tex)))

    problemas, iguais, proprias = [], 0, 0
    for rel in usadas:
        base = os.path.basename(rel)
        p_art = os.path.join(ART, rel)
        if not os.path.exists(p_art):
            problemas.append("%s: o artigo cita uma imagem que não existe" % base)
            continue

        if base in VERSOES_PROPRIAS:
            origem = _da_tese(VERSOES_PROPRIAS[base])
            if origem is None:
                problemas.append("%s: não encontrei na tese a figura de que "
                                 "deriva (%s)" % (base, VERSOES_PROPRIAS[base]))
                continue
            if os.path.getmtime(p_art) < os.path.getmtime(origem) - 1:
                problemas.append(
                    "%s é ANTERIOR à figura da tese de que deriva — regenerar "
                    "com scripts/figuras_artigo.py" % base)
            else:
                proprias += 1
                print("   [v] %-44s versão própria, mais recente que a fonte"
                      % base)
            continue

        p_tese = _da_tese(base)
        if p_tese is None:
            print("   [i] %-44s só existe no artigo" % base)
            continue
        a, b = Image.open(p_art).convert("RGB"), Image.open(p_tese).convert("RGB")
        if a.size != b.size:
            problemas.append("%s: tamanhos diferentes — artigo %s, tese %s"
                             % (base, a.size, b.size))
            continue
        d = np.array(ImageChops.difference(a, b)).sum(axis=2)
        n = int((d > 10).sum())
        if n > PIXEIS_MINIMOS:
            problemas.append("%s: %d pixels diferem da versão da tese (%.1f%%)"
                             % (base, n, 100.0 * n / (a.size[0] * a.size[1])))
        else:
            iguais += 1

    print("   [i] %d cópias idênticas à tese, %d versões próprias, "
          "%d figuras usadas" % (iguais, proprias, len(usadas)))

    dir_img = os.path.join(ART, "images")
    orfas = [f for f in sorted(os.listdir(dir_img))
             if f.lower().endswith((".png", ".pdf", ".jpg"))
             and "images/" + f not in usadas]
    if orfas:
        problemas.append("em Artigo/images/ mas não usadas pelo artigo: %s"
                         % ", ".join(orfas))

    print()
    print("=" * 74)
    if problemas:
        print("%d problema(s):" % len(problemas))
        for p in problemas:
            print("   [X] " + p)
        print("=" * 74)
        return 1
    print("O artigo mostra as mesmas figuras que a dissertação ✓")
    print("NOTA: as versões `_col` são desenhadas para a coluna de 8,9 cm — não")
    print("      são iguais às da tese, e é a DATA delas que se verifica.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
