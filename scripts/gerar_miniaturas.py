#!/usr/bin/env python3
"""Gera as miniaturas da Galeria em `results/graficos_tese/<campanha>/.thumbs/`.

PORQUÊ. As figuras são exportadas em resolução de impressão — 2400×1800 a
4200×2100, 347 KB de média — e a Galeria mostra-as numa grelha, a poucas dezenas
de píxeis de largura. Medido no dashboard em modo leitura, num telemóvel: o
primeiro ecrã da Galeria descarregava 7,4 MB, e isso já com `loading=lazy`
a impedir que as outras 21 imagens fossem pedidas. Uma figura de 4200 px a ser
desenhada a 72 px é um fator de 58×.

Isto não custa quase nada na torre, onde o browser e os ficheiros estão na mesma
máquina. Custa no Raspberry Pi, que serve pela internet a partir do upload de
uma casa — é lá que a Galeria demora, e é o orientador que espera.

Uma miniatura WebP de 600 px da mesma figura ocupa 9 KB: 42 vezes menos.

O QUE FAZ. Para cada `.png` de cada campanha, escreve `.thumbs/<nome>.webp`
com a largura pedida. Não toca nos originais: a Galeria passa a mostrar a
miniatura na grelha e continua a abrir o PNG inteiro no zoom, que é onde a
resolução serve para alguma coisa.

Os `.gif` ficam de fora de propósito — a vista Vídeos precisa da animação, e uma
miniatura estática deixaria de mostrar aquilo que ali interessa ver.

QUANDO CORRER. Antes do `scripts/atualizar_pi.sh`. Esse leva as figuras tocadas
na janela do `-newermt`, e as miniaturas são ficheiros dentro das campanhas —
entram no delta sozinhas, desde que existam antes de o pacote ser feito.

USO
    python scripts/gerar_miniaturas.py                # só o que falta ou está velho
    python scripts/gerar_miniaturas.py --forcar       # refaz tudo
    python scripts/gerar_miniaturas.py --largura 900  # mais nítidas, ~18 KB cada
    python scripts/gerar_miniaturas.py --simular      # diz o que faria, sem escrever
"""
import argparse
import os
import sys

from PIL import Image

# A consola do Windows abre em cp1252 e rebenta a imprimir «→» ou um «ç». Este
# script corre na torre (Windows) e no Pi (Linux); sem isto, morria no fim, com
# as miniaturas já escritas e um traceback a dar a entender que não tinham sido.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFICOS = os.path.join(RAIZ, "results", "graficos_tese")

# O nome da pasta vive AQUI e no dashboard/views/resultados.py. São os dois
# únicos sítios; se mudar, mudam-se os dois.
PASTA = ".thumbs"

LARGURA_OMISSAO = 600
QUALIDADE = 82


def miniatura_de(png: str) -> str:
    """Onde vive a miniatura de um PNG: `<pasta do png>/.thumbs/<nome>.webp`."""
    pasta, nome = os.path.split(png)
    return os.path.join(pasta, PASTA, os.path.splitext(nome)[0] + ".webp")


def esta_em_dia(png: str, thumb: str) -> bool:
    """A miniatura existe e é mais recente do que o original?

    Compara mtime porque as figuras são REGENERADAS por cima das antigas: o
    nome não muda e o tamanho pode não mudar, mas o conteúdo muda. Foi
    exatamente essa a armadilha que o `atualizar_pi.sh` documenta.
    """
    if not os.path.exists(thumb):
        return False
    return os.path.getmtime(thumb) >= os.path.getmtime(png)


def pngs_da_galeria():
    """Todos os PNG das campanhas, saltando as próprias miniaturas."""
    for pasta, dirs, ficheiros in os.walk(GRAFICOS):
        # Não descer para dentro do `.thumbs` — senão fazia miniaturas de
        # miniaturas em cada execução.
        dirs[:] = [d for d in dirs if d != PASTA]
        for f in ficheiros:
            if f.lower().endswith(".png"):
                yield os.path.join(pasta, f)


def gerar(png: str, largura: int, simular: bool):
    """Devolve `(bytes_antes, bytes_depois)`, ou None se falhar."""
    thumb = miniatura_de(png)
    if simular:
        return os.path.getsize(png), 0
    os.makedirs(os.path.dirname(thumb), exist_ok=True)
    with Image.open(png) as im:
        # A transparência PRESERVA-SE. As figuras são RGBA e a Galeria desenha-as
        # sobre cartões escuros; achatar para RGB punha fundo preto por baixo de
        # texto preto, e as figuras ficavam ilegíveis sem dar erro nenhum.
        im.thumbnail((largura, largura * 10), Image.LANCZOS)
        im.save(thumb, "WEBP", quality=QUALIDADE, method=6)
    return os.path.getsize(png), os.path.getsize(thumb)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--largura", type=int, default=LARGURA_OMISSAO,
                   help="largura máxima da miniatura (omissão: %d)" % LARGURA_OMISSAO)
    p.add_argument("--forcar", action="store_true",
                   help="refaz mesmo as que já estão em dia")
    p.add_argument("--simular", action="store_true",
                   help="diz o que faria, sem escrever nada")
    args = p.parse_args()

    if not os.path.isdir(GRAFICOS):
        print("results/graficos_tese/ não existe — nada a fazer.", file=sys.stderr)
        return 1

    feitas = saltadas = falhadas = 0
    antes = depois = 0
    for png in sorted(pngs_da_galeria()):
        thumb = miniatura_de(png)
        if not args.forcar and esta_em_dia(png, thumb):
            saltadas += 1
            continue
        try:
            a, d = gerar(png, args.largura, args.simular)
        except Exception as erro:                                # noqa: BLE001
            # Uma figura corrompida não pode parar as outras 1098 — mas também
            # não pode desaparecer em silêncio, que é como se descobre tarde.
            print("  FALHOU %s: %s" % (os.path.relpath(png, RAIZ), erro),
                  file=sys.stderr)
            falhadas += 1
            continue
        antes += a
        depois += d
        feitas += 1

    verbo = "a gerar (simulação)" if args.simular else "geradas"
    print("%s: %d · em dia: %d · falhadas: %d" % (verbo, feitas, saltadas, falhadas))
    if feitas and not args.simular:
        print("originais: %.1f MB → miniaturas: %.1f MB  (%.0f× menos)"
              % (antes / 1048576, depois / 1048576, antes / max(depois, 1)))
    elif feitas:
        print("originais abrangidos: %.1f MB" % (antes / 1048576))
    return 1 if falhadas else 0


if __name__ == "__main__":
    sys.exit(main())
