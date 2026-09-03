# -*- coding: utf-8 -*-
"""Gera a cábula da defesa (Defesa/cabula.html) — uma página só, para ler no telemóvel.

Porquê uma página e não um PDF
A cábula é para levar no bolso e para TESTAR: o «Modo teste» tapa as respostas
das QI, os veredictos de cada cenário e as perguntas duras, e revela-as uma a
uma ao toque. Um PDF não faz isso. E o texto é o mesmo de
`docs/RESUMO_PARA_DECORAR.md` e `docs/DEFESA_PERGUNTAS.md` — a página é a forma
portátil, não uma segunda fonte.

Porquê as figuras embutidas
A página é publicada como Artifact, servida de uma origem própria e sem acesso a
ficheiros locais: uma <img src="results/..."> ficaria vazia. Por isso cada figura
é reduzida, convertida a webp e embutida como data-URI. As 16 juntas dão ~0,4 MB,
contra os ~4 MB dos PNG de impressão — vê-se bem num telemóvel e carrega de uma vez.

O conteúdo (o texto, os números, as barras) está no MODELO, que é HTML normal com
marcadores `__IMG_chave__` nos sítios das figuras. Editar a cábula é editar o
modelo e voltar a correr isto. Os números escritos nela são os da dissertação —
como nos slides, nunca defender um número que a tese não diga.

Uso:
    .venv/Scripts/python.exe Defesa/gerar_cabula.py

Depois, para publicar/atualizar o Artifact, pedir ao Claude Code:
    «republica a Defesa/cabula.html no artifact <url>»
"""
from __future__ import annotations

import base64
import io
import os
import re
import sys

from PIL import Image, ImageChops

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELO = os.path.join(RAIZ, "Defesa", "cabula.modelo.html")
SAIDA = os.path.join(RAIZ, "Defesa", "cabula.html")
SAIDA_LOCAL = os.path.join(RAIZ, "Defesa", "cabula-offline.html")

# O Artifact embrulha o ficheiro publicado num esqueleto próprio, com `<meta
# charset>` e viewport — por isso `cabula.html` NÃO os leva (levá-los duplicava
# as etiquetas do esqueleto). Mas um ficheiro aberto do disco não tem esse
# embrulho: sem o charset declarado, o Chrome assume a codificação da máquina e
# «Cábula» sai «CÃ¡bula». Daí a segunda saída, que é a mesma página com o
# esqueleto mínimo à volta — é esta que o atalho do ambiente de trabalho abre.
ESQUELETO = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html{color-scheme:light dark}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
{corpo}
</body>
</html>
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# chave usada no modelo -> (caminho a partir da raiz, largura máxima, qualidade webp).
# Os mapas de topo são pequenos porque aparecem a 78 px nos cartões dos cenários;
# os gráficos são maiores porque se ampliam ao tocar.
FIGURAS = {
    # os sete cenários, vista de topo — as âncoras visuais para decorar os nomes
    "m_none":     ("Tese/images/mapa_topo_none.png", 400, 74),
    "m_uwall":    ("Tese/images/mapa_topo_u_wall.png", 400, 74),
    "m_bottle":   ("Tese/images/mapa_topo_bottleneck.png", 400, 74),
    "m_rooms":    ("Tese/images/mapa_topo_four_rooms.png", 400, 74),
    "m_door":     ("Tese/images/mapa_topo_cooperative_door.png", 400, 74),
    "m_perc":     ("Tese/images/mapa_topo_cooperative_perception.png", 400, 74),
    "m_bypass":   ("Tese/images/mapa_topo_cooperative_door_bypass.png", 400, 74),
    # a bancada: o domínio é uma esfera e as paredes cortam-no de lado a lado —
    # a render 3D é a única figura que mostra isso, e é o que explica a costura
    # do teto declarada nas Limitações
    "m3d_uwall":  ("Tese/images/mapa_3d_u_wall.png", 700, 76),
    "geo_uwall":  ("Tese/images/resultados/heatmap_geodesico_u_wall.png", 800, 76),
    # resultados
    "barras":     ("Tese/images/resultados/comparacao_barras_geral.png", 1000, 78),
    "glob_gnn":   ("Tese/images/resultados/desempenho_global_gnn.png", 1000, 78),
    "curv_uwall": ("results/figuras_apresentacao/curvas_u_wall.png", 950, 76),
    "curv_rooms": ("results/figuras_apresentacao/curvas_four_rooms.png", 950, 76),
    "dot_none":   ("results/figuras_apresentacao/dotplot_none.png", 900, 78),
    "dot_uwall":  ("results/figuras_apresentacao/dotplot_u_wall.png", 900, 78),
    "dot_rooms":  ("results/figuras_apresentacao/dotplot_four_rooms.png", 900, 78),
    "escala":     ("results/estatisticas/escalabilidade_zeroshot_none.png", 950, 78),
    "nov_heat":   ("results/graficos_tese/adaptativo_A1/heatmap_ocupacao_gnn_u_wall.png", 800, 76),
    "mg_geo":     ("results/graficos_tese/mapa_grande_f2/heatmap_geodesico_mapa_grande.png", 1000, 76),
    "mg_gnn":     ("results/graficos_tese/mapa_grande_f2/heatmap_ocupacao_gnn_mapa_grande.png", 1000, 76),
    "mg_curv":    ("results/figuras_apresentacao/curvas_mapa_grande.png", 950, 76),
}


def aparar(im: Image.Image) -> Image.Image:
    """Corta a moldura de cor uniforme que o matplotlib deixa à volta da figura.

    Sem isto, metade dos bytes de um dotplot é margem branca — e num ecrã de
    telemóvel a margem come a altura útil.
    """
    rgb = im.convert("RGB")
    fundo = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    caixa = ImageChops.difference(rgb, fundo).getbbox()
    if not caixa:
        return im
    x0, y0, x1, y1 = caixa
    pad = 6
    return im.crop((max(0, x0 - pad), max(0, y0 - pad),
                    min(rgb.width, x1 + pad), min(rgb.height, y1 + pad)))


def codificar(rel: str, largura: int, qualidade: int) -> tuple[str, int]:
    im = aparar(Image.open(os.path.join(RAIZ, rel)))
    if im.width > largura:
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "WEBP", quality=qualidade, method=6)
    dados = buf.getvalue()
    return "data:image/webp;base64," + base64.b64encode(dados).decode(), len(dados)


def main() -> int:
    html = open(MODELO, encoding="utf-8").read()
    pedidas = set(re.findall(r"__IMG_([a-z0-9_]+)__", html))

    em_falta = pedidas - set(FIGURAS)
    if em_falta:
        print("ERRO: o modelo pede figuras que este script não conhece: "
              + ", ".join(sorted(em_falta)))
        return 1

    total = 0
    for chave in sorted(pedidas):
        rel, largura, qualidade = FIGURAS[chave]
        caminho = os.path.join(RAIZ, rel)
        if not os.path.isfile(caminho):
            print(f"ERRO: falta a figura {rel} — correr as campanhas primeiro")
            return 1
        uri, tamanho = codificar(rel, largura, qualidade)
        total += tamanho
        html = html.replace(f"__IMG_{chave}__", uri)
        print(f"  {chave:10s} {tamanho / 1024:6.1f} KB  {rel}")

    # O `replace` é silencioso: se um marcador tivesse um erro de escrita, ficava
    # no HTML e o telemóvel mostrava a caixa partida sem dizer porquê.
    sobra = re.findall(r"__IMG_[a-z0-9_]+__", html)
    if sobra:
        print("ERRO: ficaram marcadores por substituir: " + ", ".join(sorted(set(sobra))))
        return 1

    nao_usadas = set(FIGURAS) - pedidas
    if nao_usadas:
        print("  (aviso: definidas mas não usadas no modelo: "
              + ", ".join(sorted(nao_usadas)) + ")")

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(html)
    with open(SAIDA_LOCAL, "w", encoding="utf-8") as f:
        f.write(ESQUELETO.replace("{corpo}", html))

    print(f"\n{len(pedidas)} figuras, {total / 1024:.0f} KB de webp")
    print(f"publicar:  {SAIDA}  ({os.path.getsize(SAIDA) / 1024 / 1024:.2f} MB)")
    print(f"do disco:  {SAIDA_LOCAL}  ({os.path.getsize(SAIDA_LOCAL) / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
