# -*- coding: utf-8 -*-
"""Gera os slides da defesa (Defesa/slides_defesa.pptx) a partir das figuras da tese.

Porquê um script e não um .pptx feito à mão
As figuras da dissertação vivem em `Tese/images/resultados/` e já derivaram das
campanhas uma vez (21 jul: oito figuras desatualizadas no PDF). Um .pptx feito
à mão é uma segunda cópia que deriva em silêncio. Aqui cada slide aponta para a
figura da tese pelo nome; regenerar é correr o script. Os números escritos nos
slides são os da dissertação — o guião de defesa (docs/DEFESA_PERGUNTAS.md)
diz porquê: nunca defender um número que a tese não diga.

Cada slide leva NOTAS DO ORADOR com o que dizer, para servir de guião e de
material de estudo (docs/RESUMO_PARA_DECORAR.md tem a versão longa).

Uso: .venv/Scripts/python.exe Defesa/gerar_slides.py
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIG = os.path.join(RAIZ, "Tese", "images", "resultados")
IMG = os.path.join(RAIZ, "Tese", "images")
SAIDA = os.path.join(RAIZ, "Defesa", "slides_defesa.pptx")

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
LINHA = RGBColor(0xD0, 0xD0, 0xD0)
GNN = RGBColor(0x2F, 0x9E, 0x44)
PPO = RGBColor(0xE8, 0x59, 0x0C)
SAC = RGBColor(0x1C, 0x7E, 0xD6)
ACENTO = RGBColor(0x0B, 0x3D, 0x91)

W, H = Inches(13.333), Inches(7.5)
MARGEM = Inches(0.6)

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BRANCO = prs.slide_layouts[6]
_n = 0


def _texto(slide, x, y, w, h, linhas, tamanho=18, cor=INK, negrito=False,
           alinhar=PP_ALIGN.LEFT, ancora=MSO_ANCHOR.TOP, espaco=6):
    """Caixa de texto. `linhas` = str ou lista de str/(str, dict) — dict com
    tamanho/cor/negrito/nivel. Uma linha que comece por «• » é um marcador."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancora
    if isinstance(linhas, str):
        linhas = [linhas]
    primeiro = True
    for item in linhas:
        txt, opc = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if primeiro else tf.add_paragraph()
        primeiro = False
        p.alignment = alinhar
        p.space_after = Pt(espaco)
        nivel = opc.get("nivel", 0)
        if nivel:
            p.level = nivel
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(opc.get("tamanho", tamanho))
        r.font.bold = opc.get("negrito", negrito)
        r.font.color.rgb = opc.get("cor", cor)
        r.font.name = "Calibri"
    return tb


def _rodape(slide):
    global _n
    _n += 1
    ln = slide.shapes.add_connector(1, MARGEM, H - Inches(0.55), W - MARGEM, H - Inches(0.55))
    ln.line.color.rgb = LINHA
    ln.line.width = Pt(0.75)
    _texto(slide, MARGEM, H - Inches(0.5), Inches(9), Inches(0.4),
           "Aprendizagem por Reforço para Controlo de Enxames · ISCTE-IUL 2026",
           tamanho=10, cor=MUTED)
    _texto(slide, W - MARGEM - Inches(1), H - Inches(0.5), Inches(1), Inches(0.4),
           str(_n), tamanho=10, cor=MUTED, alinhar=PP_ALIGN.RIGHT)


def _titulo(slide, titulo, sub=""):
    _texto(slide, MARGEM, Inches(0.35), W - 2 * MARGEM, Inches(0.8), titulo,
           tamanho=30, negrito=True)
    if sub:
        _texto(slide, MARGEM, Inches(1.05), W - 2 * MARGEM, Inches(0.5), sub,
               tamanho=15, cor=MUTED)
    ln = slide.shapes.add_connector(1, MARGEM, Inches(1.5), MARGEM + Inches(1.2), Inches(1.5))
    ln.line.color.rgb = ACENTO
    ln.line.width = Pt(3)


def _fig(slide, nome, x, y, w=None, h=None, pasta=FIG):
    p = os.path.join(pasta, nome)
    if not os.path.exists(p):
        _texto(slide, x, y, w or Inches(4), Inches(0.6), "figura em falta: %s" % nome,
               tamanho=12, cor=PPO)
        return None
    if w is not None and h is not None:
        # Cabe na caixa, sem deformar.
        from PIL import Image
        iw, ih = Image.open(p).size
        esc = min(w / iw, h / ih)
        return slide.shapes.add_picture(p, x, y, width=int(iw * esc), height=int(ih * esc))
    return slide.shapes.add_picture(p, x, y, width=w, height=h)


def _notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto.strip()


def slide_texto_figura(titulo, sub, bullets, figura=None, notas="", fig_w=6.2, fig_h=4.9,
                       largura_texto=None, figuras=None, tamanho=17):
    """Texto à esquerda, uma figura (ou várias empilhadas) à direita."""
    s = prs.slides.add_slide(BRANCO)
    _titulo(s, titulo, sub)
    lt = Inches(largura_texto) if largura_texto else (W - 2 * MARGEM - Inches(fig_w) - Inches(0.4)
                                                       if (figura or figuras) else W - 2 * MARGEM)
    _texto(s, MARGEM, Inches(1.75), lt, H - Inches(2.6), bullets, tamanho=tamanho, espaco=8)
    if figura:
        _fig(s, figura, W - MARGEM - Inches(fig_w), Inches(1.75), Inches(fig_w), Inches(fig_h))
    if figuras:
        n = len(figuras)
        alt = (Inches(fig_h) - Inches(0.2) * (n - 1)) / n
        y = Inches(1.75)
        for f in figuras:
            _fig(s, f, W - MARGEM - Inches(fig_w), y, Inches(fig_w), alt)
            y += alt + Inches(0.2)
    _rodape(s)
    _notas(s, notas)
    return s


def slide_figura(titulo, sub, figura, legenda="", notas="", pasta=FIG):
    s = prs.slides.add_slide(BRANCO)
    _titulo(s, titulo, sub)
    _fig(s, figura, MARGEM, Inches(1.7), W - 2 * MARGEM, H - Inches(2.9), pasta=pasta)
    if legenda:
        _texto(s, MARGEM, H - Inches(1.15), W - 2 * MARGEM, Inches(0.5), legenda,
               tamanho=13, cor=MUTED, alinhar=PP_ALIGN.CENTER)
    _rodape(s)
    _notas(s, notas)
    return s


def slide_tabela(titulo, sub, cabecalho, linhas, notas="", larguras=None, bullets=None,
                 tamanho=13):
    s = prs.slides.add_slide(BRANCO)
    _titulo(s, titulo, sub)
    y = Inches(1.75)
    if bullets:
        _texto(s, MARGEM, y, W - 2 * MARGEM, Inches(1.2), bullets, tamanho=16, espaco=6)
        y += Inches(1.3)
    n_l, n_c = len(linhas) + 1, len(cabecalho)
    altura = min(Inches(0.42) * n_l, H - y - Inches(0.8))
    tb = s.shapes.add_table(n_l, n_c, MARGEM, y, W - 2 * MARGEM, altura).table
    if larguras:
        for i, lw in enumerate(larguras):
            tb.columns[i].width = Inches(lw)
    for j, c in enumerate(cabecalho):
        cel = tb.cell(0, j)
        cel.text = c
        r = cel.text_frame.paragraphs[0].font       # `.font` do parágrafo: uma célula vazia não tem runs
        r.size, r.bold, r.color.rgb = Pt(tamanho), True, RGBColor(0xFF, 0xFF, 0xFF)
        cel.fill.solid()
        cel.fill.fore_color.rgb = ACENTO
    for i, linha in enumerate(linhas, start=1):
        for j, v in enumerate(linha):
            cel = tb.cell(i, j)
            cel.text = str(v)
            r = cel.text_frame.paragraphs[0].font
            r.size = Pt(tamanho)
            r.color.rgb = INK
            cel.fill.solid()
            cel.fill.fore_color.rgb = RGBColor(0xF7, 0xF7, 0xF7) if i % 2 else RGBColor(0xFF, 0xFF, 0xFF)
    _rodape(s)
    _notas(s, notas)
    return s


# 1. Capa
s = prs.slides.add_slide(BRANCO)
_texto(s, MARGEM, Inches(2.0), W - 2 * MARGEM, Inches(1.6),
       "Aprendizagem por Reforço para Controlo de Enxames", tamanho=40, negrito=True)
_texto(s, MARGEM, Inches(3.5), W - 2 * MARGEM, Inches(1.0),
       "Aprendizagem por reforço multiagente por gradiente vs. neuroevolução com atenção "
       "sobre grafo, em oito cenários de dificuldade crescente", tamanho=20, cor=MUTED)
_texto(s, MARGEM, Inches(5.0), W - 2 * MARGEM, Inches(1.2), [
    ("Gonçalo Pombo", {"tamanho": 20, "negrito": True}),
    ("Orientador: Prof. Doutor Luís Nunes", {"tamanho": 16, "cor": MUTED}),
    ("Mestrado em Inteligência Artificial · ISCTE-IUL · 2026", {"tamanho": 16, "cor": MUTED}),
])
if os.path.exists(os.path.join(IMG, "iscte.png")):
    _fig(s, "iscte.png", W - MARGEM - Inches(2.4), Inches(0.5), Inches(2.4), Inches(1.0), pasta=IMG)
_notas(s, """
Bom dia. Vou apresentar a dissertação «Aprendizagem por Reforço para Controlo de
Enxames»: uma comparação, no mesmo simulador e com o mesmo protocolo, entre dois
paradigmas de controlo descentralizado — aprendizagem por reforço multiagente por
gradiente (PPO e SAC) e neuroevolução de uma rede de grafos com atenção — em oito
cenários. Quinze minutos: o problema, o método, sete perguntas e as respostas.
""")

# 2. Problema
slide_texto_figura(
    "O problema", "duas escolas, e nenhuma comparação direta em cenários difíceis",
    [
        "• Robótica de enxame: muitos agentes simples, controlo descentralizado, "
        "inteligência nas interações locais",
        "• Duas escolas para desenhar o controlador:",
        ("Otimização bio-inspirada — robustez offline, controladores estáticos", {"nivel": 1, "tamanho": 15}),
        ("MARL — adaptabilidade online, não-estacionaridade, recompensas esparsas", {"nivel": 1, "tamanho": 15}),
        "• Lacuna (Majid et al., 2024; Bettini et al., 2024): faltam benchmarks diretos, "
        "com estatística, em cenários dinâmicos e difíceis",
        "• Hipótese de partida: a inteligência adaptativa (MARL) supera a robustez "
        "estática bio-inspirada em cenários de stress?",
        ("A resposta curta: só em parte — e não onde a hipótese a punha.", {"negrito": True, "cor": ACENTO}),
    ],
    figura="viz_u_wall.png", fig_w=5.6, fig_h=4.6,
    notas="""
O campo organiza-se em duas escolas. A bio-inspirada trata o controlador como um
problema de otimização offline — robusto, mas estático. O MARL aprende online,
mas paga a não-estacionaridade e as recompensas esparsas. A literatura diz que
faltam comparações diretas, rigorosas, em cenários difíceis. Esta tese é essa
comparação. A hipótese de partida era que a adaptabilidade do MARL ganharia em
stress; a resposta vai ser «só em parte» — e a parte que se confirma não está
onde a hipótese a punha.
""")

# 3. Questões
slide_texto_figura(
    "Sete questões de investigação", "quatro de comparação entre paradigmas, três sobre os mecanismos",
    [
        ("Nível 1 — comparação", {"negrito": True, "cor": ACENTO}),
        "• QI1  Desempenho de tarefa: qual paradigma é mais eficaz, e em que cenários?",
        "• QI2  Escalabilidade: uma política treinada com N=20 transfere-se para N=10…100 sem retreino?",
        "• QI3  Robustez: o que acontece quando 10 % dos agentes falham a meio?",
        "• QI4  Critério de escolha: quando preferir um ao outro?",
        ("Nível 2 — mecanismos", {"negrito": True, "cor": ACENTO}),
        "• QI5  Desenho da fitness: um shaping de homing desbloqueia o que a fitness pura não resolve?",
        "• QI6  Deceção: a procura por novidade ajuda onde o gradiente engana?",
        "• QI7  Composição: as conclusões transferem-se para um mapa que junta as dificuldades?",
    ],
    notas="""
Sete questões em dois níveis. As quatro primeiras comparam paradigmas:
desempenho, escalabilidade, robustez e critério de escolha. As três seguintes
descem aos mecanismos — o sinal de treino, a pressão de exploração e a
topologia — e só se tornam formuláveis depois das primeiras. Vou respondê-las
todas, pela ordem em que os resultados as desbloqueiam.
""")

# 4. Simulador e cenários
s = prs.slides.add_slide(BRANCO)
_titulo(s, "O simulador e os oito cenários",
        "forrageamento cooperativo em 3D, 20 agentes, observação local (LiDAR 8 m)")
_texto(s, MARGEM, Inches(1.75), Inches(5.2), Inches(4.8), [
    "• Tarefa: recolher itens e entregá-los no ninho; perceção cooperativa com alvo móvel",
    "• Observação local e parcial: LiDAR, bússola ao ninho, vizinhos",
    "• Sete cenários de dificuldade isolada:",
    ("Sandbox · Muro em U (deceção espacial) · Gargalo · Quatro Salas", {"nivel": 1, "tamanho": 14}),
    ("Porta Cooperativa (3 robôs) · Perceção Cooperativa · Porta com Alternativa", {"nivel": 1, "tamanho": 14}),
    "• Oitavo: o mapa composto, 103 × 62 m, que junta quatro dificuldades em série",
    "• Falhas súbitas de agentes e dimensão do enxame variável, para a robustez e a escala",
], tamanho=16, espaco=8)
grelha = ["mapa_3d_none.png", "mapa_3d_u_wall.png", "mapa_3d_bottleneck.png", "mapa_3d_four_rooms.png",
          "mapa_3d_cooperative_door.png", "mapa_3d_cooperative_perception.png",
          "mapa_3d_cooperative_door_bypass.png"]
x0, y0, cw, ch = W - MARGEM - Inches(7.2), Inches(1.75), Inches(1.7), Inches(1.45)
for k, f in enumerate(grelha):
    _fig(s, f, x0 + (k % 4) * (cw + Inches(0.13)), y0 + (k // 4) * (ch + Inches(0.13)), cw, ch, pasta=IMG)
# O oitavo, a planta do mapa composto, ocupa a linha de baixo inteira.
_fig(s, "mapa_grande_planta.png", x0, y0 + 2 * (ch + Inches(0.13)), Inches(7.2), Inches(2.0))
_rodape(s)
_notas(s, """
O simulador foi construído de raiz em Python: tridimensional, com física de
colisões e deslizamento nos muros, LiDAR horizontal de 8 metros e observação
egocêntrica. A tarefa é o forrageamento cooperativo. Sete cenários isolam uma
dificuldade cada — um beco enganador, um gargalo, quatro salas, uma porta que só
abre com três robôs — e o oitavo compõe quatro delas num labirinto quatro vezes
maior. Tudo é reproduzível: sementes fixas, avaliação determinística.
""")

# 5. Controladores
slide_tabela(
    "Os três controladores", "o mesmo espaço de observação e ação; execução descentralizada com partilha de parâmetros",
    ["", "PPO / SAC (framework RS2C)", "Neuroevolução (GNN)"],
    [
        ["Paradigma", "MARL por gradiente (on-policy / off-policy)", "Otimização bio-inspirada, sem gradientes"],
        ["Política", "MLP sobre observação de vizinhança densa (entrada fixa, ℝ¹¹¹)", "Rede de grafos com atenção sobre os vizinhos (invariante a N)"],
        ["Sinal de treino", "Recompensa por passo com shaping geodésico", "Fitness: recolhas + homing terminal no potencial geodésico"],
        ["Orçamento por execução", "48 min, 16 ambientes vetorizados", "195 min, população de 30 genomas em paralelo"],
        ["Custo em núcleos-hora", "12,8", "97,6  (≈ 8×)"],
    ],
    larguras=[2.4, 4.9, 4.9],
    bullets=[("A arquitetura difere entre paradigmas — é uma limitação declarada, e é o que permite atribuir "
              "a escalabilidade à representação e não ao otimizador.", {"cor": MUTED, "tamanho": 15})],
    notas="""
Os dois lados partilham o simulador, a observação e o protocolo de avaliação.
O PPO e o SAC usam as implementações de referência da Stable-Baselines3 — uma
MLP de entrada fixa. O controlador evolutivo otimiza os pesos de uma rede de
grafos com atenção sobre os vizinhos, invariante ao número de agentes. A
assimetria é declarada como primeira limitação: por isso mesmo, a conclusão
sobre escalabilidade é atribuída à representação, não ao algoritmo. O evolutivo
custa cerca de oito vezes mais núcleos-hora por execução.
""")

# 6. Protocolo
slide_texto_figura(
    "O protocolo", "o que impede esta tese de mentir",
    [
        "• 3 algoritmos × 7 cenários × 7 execuções independentes = 147 treinos",
        "• Avaliação determinística: 20 episódios emparelhados por modelo (sementes comuns) — "
        "2 940 episódios na campanha principal",
        "• A unidade estatística é a execução, não o episódio: Mann-Whitney U sobre as médias "
        "por execução (n = 7), δ de Cliff como tamanho de efeito",
        "• Métrica de tarefa pura: recolhas por episódio e taxa de sucesso — comparável entre paradigmas",
        "• Três campanhas pré-registadas (hipótese, testes e regra de decisão fixados antes dos dados)",
        "• Dezoito verificadores automáticos: cada número da dissertação é conferido contra os CSV "
        "a cada commit",
    ],
    figura="comparacao_barras_geral.png", fig_w=5.8, fig_h=4.4,
    notas="""
Cento e quarenta e sete treinos, cada modelo avaliado em vinte episódios
determinísticos com as mesmas sementes para os três algoritmos. A unidade
estatística é a execução: sete por célula, Mann-Whitney com delta de Cliff. As
campanhas decisivas foram pré-registadas — hipótese, testes e regra de decisão
escritos antes de haver dados. E cada número da tese é conferido por um
verificador contra os ficheiros de avaliação, a cada commit. Isto é o que me
permite dizer que os números são os dos dados.
""")

# 7. QI1
slide_texto_figura(
    "QI1 — Desempenho de tarefa", "não há paradigma dominante; há cenários de cada um",
    [
        "• 15 das 21 células a 100 % de sucesso em todas as execuções",
        ("GNN evolutivo — especialista em navegação estruturada:", {"negrito": True, "cor": GNN}),
        "  superior em 3 cenários (Quatro Salas 59,8 vs 33,6 · Porta Cooperativa · Perceção Cooperativa, "
        "δ ≥ +0,71); empata com o PPO no Gargalo (121,4 vs 123,2) e na Porta com Alternativa",
        ("PPO — o generalista fiável:", {"negrito": True, "cor": PPO}),
        "  100 % em seis cenários, a menor variância; ganha o Sandbox (71,5 vs 38,3 do GNN, δ = −1,00)",
        ("SAC — fiável em espaço aberto, frágil nos gargalos físicos:", {"negrito": True, "cor": SAC}),
        "  o único que falha execuções no Gargalo (5/7, 41,4 ± 36,8)",
        ("Muro em U: ninguém o resolve de forma fiável — bimodal nos três (3/7, 4/7, 2/7).",
         {"negrito": True}),
    ],
    figuras=["taxa_sucesso_por_cenario.png", "recolhas_por_cenario.png"], fig_w=5.6, fig_h=5.0, tamanho=15,
    notas="""
Primeira resposta: não há vencedor universal. Quinze das vinte e uma células
estão a cem por cento. O evolutivo, com a fitness de homing, é o especialista em
navegação estruturada — significativamente superior em três cenários, incluindo
os dois cooperativos, e empatado com o PPO nos gargalos. O PPO é o generalista:
converge em tudo menos no Muro em U, com a variância mais baixa, e ganha o
Sandbox onde o evolutivo degenera. O SAC é o mais sensível aos gargalos. E o
Muro em U não é resolvido de forma fiável por nenhum: cada execução ou aprende
o desvio ou não aprende nada.
""")

# 8. Fiabilidade / bimodalidade
slide_texto_figura(
    "A unidade é a execução — e a forma da distribuição conta", "porque se reportam pontos e não caixas",
    [
        "• Com n = 7, os quartis de um boxplot são ruído; a caixa cheia sugere densidade onde não há nenhuma",
        "• Muro em U: 4 execuções do GNN a zero e 3 entre 43 e 80 — bimodal, não «média 24,5»",
        "• Sandbox: o cenário mais simples é o menos fiável para o evolutivo — 2 execuções degeneram "
        "(sem paredes, não há gradiente geodésico que canalize o homing)",
        "• A convergência tudo-ou-nada é o padrão em 6 das 21 células — e é o que as QI5 e QI6 explicam",
    ],
    figuras=["dotplot_eval_u_wall.png", "dotplot_eval_none.png"], fig_w=5.4, fig_h=5.0,
    notas="""
Um ponto de método que muda a leitura. Com sete execuções, um boxplot esconde a
forma. No Muro em U, o GNN tem quatro execuções a zero e três a resolver o
cenário por completo: a média de vinte e quatro recolhas não descreve nenhuma
delas. No Sandbox, o cenário mais simples, o evolutivo é o menos fiável: sem
paredes não há gradiente geodésico que o guie, e duas execuções degeneram. Este
padrão tudo-ou-nada é o fio condutor das duas questões seguintes.
""")

# 9. QI5
slide_texto_figura(
    "QI5 — O desenho da fitness decide", "o «colapso do evolutivo» era um artefacto do sinal de treino",
    [
        "• Fitness inicial: recolhas + retorno acumulado do episódio — farmável por deambulação; a população "
        "satura num planalto sem pressão seletiva (fitness exploitation)",
        "• Cura: substituir o retorno pelo homing terminal — proximidade ao ninho no fim do episódio, medida "
        "no potencial geodésico (contorna paredes; o euclidiano atrai para dentro do beco)",
        ("Resultado: de 0 % para 100 % de sucesso nas 28 execuções dos quatro cenários de gargalo.",
         {"negrito": True, "cor": GNN}),
        "• Necessário, não suficiente: resolve a atribuição de crédito, não a descoberta do desvio comprido "
        "— o Muro em U continua bimodal (3/7), como nos métodos de gradiente",
    ],
    figura="heatmap_geodesico_u_wall.png", fig_w=6.0, fig_h=4.6,
    notas="""
A primeira das questões de mecanismo. Nas campanhas exploratórias o evolutivo
colapsava nos labirintos, e a leitura fácil era «limitação do paradigma». Não
era. A fitness inicial somava o retorno acumulado, que se farma a deambular; a
população saturava. Substituí esse termo pelo homing terminal — estar perto do
ninho no fim, medido num potencial geodésico que contorna as paredes. Vinte e
oito execuções de zero para cem por cento. Mas é condição necessária, não
suficiente: o Muro em U continuou bimodal. Faltava a descoberta.
""")

# 10. QI6
slide_texto_figura(
    "QI6 — Deceção e procura por novidade", "a exploração tem preço; doseada, deixa de ter",
    [
        "• Novidade com peso fixo (w = 0,5), orçamento igualado: Muro em U passa de 3/7 para 7/7 "
        "(69,8 vs 24,5; p = 0,026, δ = +0,71) — mas custa na Porta com Alternativa (63,0 vs 86,7; δ = −1,00)",
        "• Dosagem adaptativa (pré-registada): w decai após a descoberta sustentada → mantém 7/7 no Muro em U, "
        "sem custo significativo em nenhum dos outros seis; com o dobro do orçamento, 88,7 ± 0,6 — "
        "o melhor resultado da dissertação",
        "• O ganho não se compra com orçamento: o objetivo puro com 390 min continua bimodal (4/7)",
        ("Replicação a n = 28: 28/28 execuções resolvidas, contra 15/28 do objetivo puro e 14/28 do PPO "
         "e do SAC (Fisher exato, p < 0,0001).", {"negrito": True, "cor": ACENTO}),
        "• GNN objetivo e PPO indistinguíveis (p = 0,088): o que separa os braços é a dosagem da exploração, "
        "não o paradigma",
    ],
    figura="megatreino_u_wall_4bracos.png", fig_w=5.6, fig_h=5.0, tamanho=15,
    notas="""
A hibridização com procura por novidade, com orçamento igualado, resolve o
Muro em U em sete de sete execuções — a única configuração que o faz. Mas com
peso fixo degrada o cenário onde o gradiente já bastava. A campanha
pré-registada de dosagem adaptativa — pagar novidade só enquanto ela compra
descoberta — removeu o custo e deu o melhor resultado da tese. E a replicação
com vinte e oito execuções por braço fecha a questão: vinte e oito em vinte e
oito, contra quinze do objetivo puro e catorze de cada método de gradiente. O
GNN objetivo e o PPO são indistinguíveis; o que decide é a dosagem da
exploração, não o paradigma.
""")

# 11. QI2
slide_tabela(
    "QI2 — Escalabilidade Zero-Shot", "só a arquitetura de grafo transfere de N = 10 a N = 100 sem retreino",
    ["Cenário", "N=10", "N=20", "N=50", "N=100", "Retenção per capita"],
    [
        ["Sandbox", "3,74", "3,29", "1,95", "1,27", "39 %"],
        ["Perceção Cooperativa", "1,64", "1,30", "0,83", "0,59", "45 %"],
        ["Gargalo", "6,92", "6,93", "5,96", "4,04", "58 %"],
        ["Quatro Salas", "3,60", "3,86", "3,26", "2,54", "66 %"],
        ["Muro em U", "3,84", "4,01", "3,81", "3,14", "78 %"],
        ["Porta Cooperativa", "3,40", "3,54", "3,41", "3,12", "88 %"],
        ["Porta com Alternativa", "4,31", "4,50", "4,44", "4,06", "90 %"],
    ],
    larguras=[3.2, 1.6, 1.6, 1.6, 1.6, 2.5],
    bullets=[
        "• 100 % de sucesso nas 28 combinações cenário × dimensão (recolhas por agente na tabela)",
        "• PPO/SAC: a MLP de entrada fixa (ℝ¹¹¹) é estruturalmente incompatível com N ≠ 20 — não é um "
        "resultado fraco, é o resultado",
        ("• A retenção é maior nos cenários com paredes: a estrutura atenua a diluição do recurso, "
         "não a agrava. Zero-shot é uma propriedade da representação, não do otimizador.", {"negrito": True}),
    ],
    notas="""
Escalabilidade. A política do controlador de grafo, treinada com vinte agentes,
transfere para dez, cinquenta e cem — cem por cento de sucesso nas vinte e oito
combinações, incluindo labirintos e tarefas cooperativas, onde a objeção do
congestionamento seria mais plausível. A retenção per capita é mais alta nos
cenários com paredes do que nos abertos: o que se perde no Sandbox é diluição
de um recurso finito, não coordenação. O PPO e o SAC nem sequer podem ser
avaliados fora de N igual a vinte. A vantagem de escala está na representação.
""")

# 12. QI3
slide_texto_figura(
    "QI3 — Robustez a falhas", "10 % dos agentes ficam inertes a meio do episódio",
    [
        "• Retenção de recolhas entre 92 % e 106 % nas 21 combinações algoritmo–cenário",
        "• Inclui a Porta Cooperativa, que exige três agentes simultâneos: o enxame redistribui-se",
        "• Transversal aos paradigmas: a redundância vem do parameter sharing e da observação local — "
        "nenhum agente é insubstituível",
        "• Consequência para a QI4: a robustez não é critério de escolha entre paradigmas",
    ],
    figura="robustez_falhas.png", fig_w=6.6, fig_h=4.6,
    notas="""
Robustez: dez por cento dos agentes falham a meio do episódio e ficam inertes.
Os três paradigmas retêm entre noventa e dois e cento e seis por cento das
recolhas, em todas as vinte e uma combinações — mesmo na porta que precisa de
três robôs. A redundância vem da partilha de parâmetros e da observação local.
Sendo transversal, a robustez não discrimina entre paradigmas — e isso é uma
resposta, não uma ausência de resposta.
""")

# 13. QI7
slide_texto_figura(
    "QI7 — Composição de dificuldades", "um labirinto de 103 × 62 m que junta quatro dificuldades em série",
    [
        "• Transferência sem retreino: zero recolhas em 84 de 84 células (1 680 episódios, 4 condições "
        "de controlo) — mas o mapa é resolúvel: um navegador geodésico sem aprendizagem faz 53,0 rec/ep",
        "• Treino nativo, 21 execuções por algoritmo: só o evolutivo passa — em 4 de 21, abaixo do "
        "limiar de 15 fixado antes dos dados",
        ("A resposta à QI7 é negativa, e reporta-se como tal.", {"negrito": True, "cor": ACENTO}),
        "• O que a composição degrada é a fiabilidade, não a magnitude: a assinatura bimodal do Muro em U, "
        "à escala de um mapa quatro vezes maior",
        "• Condicionada ao orçamento: em 19 das 21 execuções o fitness ainda subia no último quinto",
    ],
    figuras=["mapa_grande_planta.png", "mapa_grande_rastos.png"], fig_w=6.0, fig_h=5.0, tamanho=15,
    notas="""
A última pergunta testa a objeção mais natural a um benchmark por cenários
isolados. Sem retreino, nenhum controlador faz uma única recolha no mapa
composto — em oitenta e quatro células, com controlos que excluem a escala da
observação e os obstáculos como causa. E o mapa é resolúvel: um navegador
geodésico sem aprendizagem faz cinquenta e três recolhas. Com treino nativo, só
o evolutivo o resolve, em quatro de vinte e uma execuções — abaixo do limiar
pré-registado. A resposta é negativa e está reportada como negativa. O que a
composição degrada é a fiabilidade: é a bimodalidade do Muro em U em ponto
grande.
""")

# 14. QI4 — mapa de escolha
slide_tabela(
    "QI4 — Critério de escolha", "não há vencedor universal; há um mapa de escolha",
    ["Se a missão…", "Então…", "Porquê"],
    [
        ["tem enxame de dimensão fixa e conhecida, e prioriza eficiência e cómputo",
         "MARL por gradiente (PPO)", "100 % em seis cenários, menor variância, ≈ 8× mais barato (12,8 vs 97,6 núcleos-hora)"],
        ["tem dimensão variável ou desconhecida, ou exige escalar sem retreino",
         "arquitetura de grafo com atenção (aqui, evolutiva)", "única a transferir de N=10 a N=100: 100 % em 28/28"],
        ["tem navegação estruturada (gargalos, salas, portas cooperativas)",
         "evolutivo com fitness de homing", "superior em 3 cenários, empate nos outros gargalos"],
        ["tem deceção espacial (gradiente enganador)",
         "neuroevolução + novidade doseada adaptativamente", "28/28 no Muro em U; sem custo nos outros seis"],
        ["exige tolerância a falhas de agentes", "qualquer dos três", "92–106 % de retenção — não discrimina"],
    ],
    larguras=[4.4, 3.6, 4.2],
    notas="""
A síntese prática. Dimensão fixa e cómputo barato: PPO. Dimensão variável ou
escala sem retreino: a arquitetura de grafo é a única opção entre as
estudadas. Navegação estruturada: o evolutivo com homing. Deceção espacial:
novidade doseada adaptativamente. Robustez a falhas não separa ninguém. Em vez
de um vencedor, a tese entrega os eixos que devem ditar a escolha.
""")

# 15. Limitações
slide_texto_figura(
    "Limitações — as que admito primeiro", "declaradas na dissertação, com os números",
    [
        "• Arquitetura assimétrica: atenção sobre grafo só no evolutivo; PPO/SAC com MLP — a comparação "
        "combina otimizador e representação (trabalho futuro n.º 1: a mesma arquitetura por gradiente)",
        "• Sete execuções por célula: onde a leitura depende de contagens, replicou-se a n = 28",
        "• Orçamento: 7 das 21 células ainda subiam no fim — o SAC nos gargalos lê-se como limite inferior "
        "(temperatura fixa, α = 0,1)",
        "• Só simulação: o fosso de implantação fica por validar",
        "• Dimensão vertical não observada mas usada; duas costuras na física das paredes "
        "(11 de 343 modelos atravessam-nas; nenhuma conclusão depende deles)",
        "• QI7 sobre um único mapa composto",
    ],
    figura="dotplot_eval_bottleneck.png", fig_w=5.2, fig_h=4.6, tamanho=15,
    notas="""
As limitações vêm antes das perguntas. A arquitetura difere entre paradigmas —
é a primeira, e é deliberadamente lida como o que permite isolar a
representação. Sete execuções são poucas onde a leitura é de contagens; por
isso o Muro em U foi replicado com vinte e oito. Sete células ainda subiam no
fim do orçamento; o SAC nos gargalos é limite inferior. Tudo é simulação. E a
física tem duas costuras nas paredes que uma minoria de modelos explora — medi
todos os modelos arquivados; nenhuma conclusão depende disso.
""")

# 16. Contributos
slide_texto_figura(
    "Contributos", "",
    [
        ("1. O desenho da fitness como causa e cura do colapso evolutivo", {"negrito": True}),
        "  o homing terminal no potencial geodésico levou 28 execuções de 0 % a 100 % — o principal contributo metodológico",
        ("2. Caracterização condicional da procura por novidade", {"negrito": True}),
        "  resolve a deceção espacial (28/28) e, doseada adaptativamente, deixa de custar onde o gradiente basta",
        ("3. Um mapa de escolha para engenharia de enxames", {"negrito": True}),
        "  estrutura do cenário, variabilidade de N e cómputo, em vez de um vencedor universal",
        ("4. Uma implementação de referência aberta e verificável", {"negrito": True}),
        "  simulador, oito cenários, RS2C e neuroevolução; 18 verificadores ligam cada número aos dados",
    ],
    figura="escalabilidade_zeroshot_none.png", fig_w=5.4, fig_h=4.4,
    notas="""
Quatro contributos. O primeiro é metodológico: o colapso do evolutivo era o
sinal de treino, não o paradigma. O segundo é a caracterização da novidade como
instrumento direcionado — e a dosagem adaptativa que remove o seu custo. O
terceiro é o mapa de escolha. O quarto é o repositório: simulador, cenários,
controladores e os verificadores que ligam cada número da tese aos ficheiros de
avaliação.
""")

# 17. Conclusão
s = prs.slides.add_slide(BRANCO)
_titulo(s, "Conclusão", "a hipótese confirma-se só em parte — e não onde a punha")
_texto(s, MARGEM, Inches(1.9), W - 2 * MARGEM, Inches(4.5), [
    ("A vantagem de escala reside na representação — o grafo com atenção —, não no algoritmo de otimização.",
     {"tamanho": 22, "negrito": True, "cor": ACENTO}),
    ("Nos cenários de gradiente enganador, o que decide é o desenho do sinal de treino e a exploração "
     "doseada adaptativamente — não o paradigma.", {"tamanho": 22, "negrito": True, "cor": ACENTO}),
    ("Os métodos de gradiente ficam com a fiabilidade em espaço aberto e com ≈ 8× menos cómputo.",
     {"tamanho": 20}),
    ("A composição de dificuldades degrada a fiabilidade antes da magnitude — e isso está reportado "
     "como resultado negativo, com o número à vista.", {"tamanho": 20}),
], espaco=16)
_rodape(s)
_notas(s, """
A hipótese de que a inteligência adaptativa supera a robustez estática
confirma-se só em parte. A vantagem de escala existe — mas está na
representação, não no otimizador. Nos cenários enganadores, o que decide é o
sinal de treino e a exploração doseada. Os métodos de gradiente ficam com a
fiabilidade em espaço aberto e o cómputo barato. E a composição degrada a
fiabilidade antes da magnitude — um resultado negativo, reportado como tal.
""")

# 18. Fim
s = prs.slides.add_slide(BRANCO)
_texto(s, MARGEM, Inches(2.4), W - 2 * MARGEM, Inches(1.2), "Obrigado.", tamanho=40, negrito=True)
_texto(s, MARGEM, Inches(3.6), W - 2 * MARGEM, Inches(2.5), [
    ("Painel interativo (campanhas, vídeos, episódios 3D, proveniência de cada número):", {"cor": MUTED, "tamanho": 16}),
    ("http://swarmroboticsgs.duckdns.org", {"tamanho": 18, "cor": ACENTO}),
    ("Página de resultados:  https://pombo2001.github.io/swarm-robotics-tese/", {"tamanho": 16}),
    ("Código, dados e verificadores:  https://github.com/Pombo2001/swarm-robotics-tese", {"tamanho": 16}),
], espaco=8)
_notas(s, """
Obrigado. O painel tem as trinta campanhas, os vídeos, os episódios em 3D e a
proveniência de cada número — posso mostrar qualquer célula ao vivo. Estou à
disposição para perguntas.
""")

prs.save(SAIDA)
print("[v] %s (%d slides)" % (os.path.relpath(SAIDA, RAIZ), len(prs.slides)))
