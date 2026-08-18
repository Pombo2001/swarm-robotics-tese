#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensaia os verificadores da tese contra uma tese deliberadamente estragada.

    python scripts/ensaiar_verificador.py

O `verificar_numeros_tese.py` diz «tudo bate ✓». Isso pode querer dizer duas
coisas: que os números estão certos, ou que os padrões deixaram de encontrar as
frases que deviam conferir. **As duas dão exatamente a mesma saída.** Um
verificador que passa sempre é pior do que nenhum, porque dá autorização.

Este ensaio distingue-as: pega numa cópia do `main.tex`, muda **um** número de
cada vez para um valor errado, e exige que o verificador correspondente acuse.
Se uma mutação passar despercebida, há um buraco — e o guião imprime qual.

Foi assim que se descobriu que a retenção da escalabilidade era comparada com
1 pp de folga quando a tese a escreve ao inteiro: trocar $90\\%$ por $91\\%$
não dava erro nenhum. A folga passou a ser a do arredondamento (0,5 pp).

Só lê o `main.tex` do repositório; escreve a cópia mutada no diretório
temporário do sistema e apaga-a no fim. A tese nunca é tocada.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import verificar_numeros_tese as V  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

# (rótulo, o que substituir, por quê, que verificador tem de acusar)
#
# As mutações são aplicadas a TODAS as ocorrências: a primeira versão deste
# ensaio substituía só a primeira, e duas mutações caíram em ocorrências fora
# do recorte que o verificador via — dando um falso «não apanhado». O
# $\mathbb{R}^{111}$, por exemplo, aparece em oito sítios da tese.
MUTACOES = [
    ("retenção da prosa (90% -> 91%)",
     "Porta com Alternativa $90\\%$", "Porta com Alternativa $91\\%$", "escala"),
    ("célula da tab:res_scale (127,3 -> 137,3)",
     "$100\\%$ / $127{,}3$", "$100\\%$ / $137{,}3$", "escala"),
    ("recolhas totais do Gargalo (403,6 -> 400,0)",
     "para $403{,}6$ em $N=100$", "para $400{,}0$ em $N=100$", "escala"),
    ("nº de combinações (28 -> 27)",
     "\\textbf{100\\% de sucesso nas 28 combina",
     "\\textbf{100\\% de sucesso nas 27 combina", "escala"),
    ("um N/A do PPO trocado por um valor",
     "PPO & N/A$^{\\dagger}$", "PPO & $100\\%$ / $50{,}0$", "escala"),
    ("Sandbox N=20 do SAC (71,3 -> 61,3)",
     "SAC $71{,}3$ recolhas/ep", "SAC $61{,}3$ recolhas/ep", "escala"),
    ("dimensão da observação (111 -> 112)",
     "\\mathbb{R}^{111}", "\\mathbb{R}^{112}", "simulador"),
    ("abertura do Gargalo (2,5 -> 3,0 m)",
     "passagem de $2{,}5$\\,m", "passagem de $3{,}0$\\,m", "simulador"),
    ("aberturas do Muro em U (7 -> 6 m)",
     "aberturas de $7$\\,m", "aberturas de $6$\\,m", "simulador"),
    ("horizonte da Porta Cooperativa (800 -> 900)",
     "alargado de $800$ passos", "alargado de $900$ passos", "simulador"),
    ("agentes para abrir a porta (3 -> 4)",
     "quando no mínimo 3 agentes", "quando no mínimo 4 agentes", "simulador"),
    ("LiDAR na tab:hyperparameters (8,0 -> 9,0 m)",
     "Alcance do LiDAR & $8{,}0$\\,m", "Alcance do LiDAR & $9{,}0$\\,m", "hiper"),
    ("custo energético do apêndice (-0,05 -> +0,05)",
     "\\texttt{energy\\_cost} & $-0{,}05$", "\\texttt{energy\\_cost} & $0{,}05$",
     "hiper"),
    ("net_arch do PPO no apêndice ([256,256] -> [256,128])",
     "\\texttt{net\\_arch} & $[256, 256]$", "\\texttt{net\\_arch} & $[256, 128]$",
     "hiper"),
    ("arquivo de novidade (1000 -> 500)",
     "máx.\\ $1000$ (FIFO", "máx.\\ $500$ (FIFO", "hiper"),
    ("pesos do GNN (8k -> 12k)",
     "$32$ ($\\approx 8$k pesos)", "$32$ ($\\approx 12$k pesos)", "hiper"),
    ("«superior a ambos em três cenários» (troca de cenários)",
     "(Quatro Salas, Porta Cooperativa e Perceção Cooperativa, com "
     "$\\delta \\geq +0{,}71$)",
     "(Quatro Salas, Porta Cooperativa e Gargalo, com "
     "$\\delta \\geq +0{,}71$)", "discussao"),
    ("δ mínimo dos três cenários (0,71 -> 0,80)",
     "com $\\delta \\geq +0{,}71$)", "com $\\delta \\geq +0{,}80$)", "discussao"),
    ("convergência no Muro U (2/7 a 4/7 -> 2/7 a 5/7)",
     "de $2/7$ a $4/7$", "de $2/7$ a $5/7$", "discussao"),
    ("as 28 execuções dos cenários com paredes (28 -> 27)",
     "convergem as 28 execuções", "convergem as 27 execuções", "discussao"),
    ("razão de núcleos-hora (8x -> 6x)",
     "uma razão de $\\approx 8\\times$ em núcleos-hora",
     "uma razão de $\\approx 6\\times$ em núcleos-hora", "discussao"),
    ("núcleos do evolutivo (30 -> 24)",
     "195 minutos com $\\approx 30$ núcleos",
     "195 minutos com $\\approx 24$ núcleos", "discussao"),
    ("intervalo de retenção com paredes (58--90 -> 58--95)",
     "reter $58$--$90\\%$ nos cenários com paredes",
     "reter $58$--$95\\%$ nos cenários com paredes", "discussao"),
    ("o Sandbox do GNN (5/7 -> 6/7)",
     "cenários abertos (Sandbox 5/7)", "cenários abertos (Sandbox 6/7)",
     "discussao"),
    # ── Os ecos do Capítulo 6 (17 ago) ──────────────────────────────────────
    # Estas três mutações não estragam um resultado: estragam o **eco** dele no
    # capítulo seguinte, que é o defeito que a coerência interna existe para
    # apanhar — corrigir o Capítulo 5 e esquecer o Capítulo 6.
    ("eco da QI7 nas Conclusões (4 de 21 -> 6 de 21)",
     "resolve o mapa em 4 das $21$", "resolve o mapa em 6 das $21$",
     "coerencia"),
    ("eco da retenção per capita na QI2 (58--90 -> 58--88)",
     "retém $58$--$90\\%$ nos cenários com paredes",
     "retém $58$--$88\\%$ nos cenários com paredes", "coerencia"),
    ("eco da robustez nos Contributos (92--106 -> 92--104)",
     "(retenção de 92--106\\%", "(retenção de 92--104\\%", "coerencia"),
    # ── A secção do Novelty, nas três frases que passaram a ter rede ────────
    ("T1: o limiar dos cinco p (0,21 -> 0,45)",
     "nenhuma diferença é significativa (todos $p \\geq 0{,}21$)",
     "nenhuma diferença é significativa (todos $p \\geq 0{,}45$)", "novelty"),
    ("T1: convergência do Sandbox (6/7 -> 7/7)",
     "descritivamente ($47{,}5 \\pm 28{,}1$, 6/7",
     "descritivamente ($47{,}5 \\pm 28{,}1$, 7/7", "novelty"),
    ("ablação: o topo do Muro em U (69,1 -> 71,1)",
     "e $69{,}1$ recolhas/ep no Muro em U", "e $71{,}1$ recolhas/ep no Muro em U",
     "novelty"),
    ("T4: o p do Muro em U contra o peso fixo (0,80 -> 0,40)",
     "indistinguível no Muro em U ($p=0{,}80$)",
     "indistinguível no Muro em U ($p=0{,}40$)", "novelty"),
    # ── Os TESTES do mega-treino (18 ago) ───────────────────────────────────
    # As médias e as contagens do mega-treino já tinham rede desde 3 ago; os p
    # e os δ escritos ao lado delas não tinham nenhuma. São eles que sustentam
    # a resposta à QI6 — o «$28/28$ contra $15/28$» só decide porque vem com um
    # Fisher exato — e mudar um p não muda média nenhuma: nada o apanhava.
    ("M1: o δ do adaptativo vs objetivo (0,61 -> 0,81)",
     "do objetivo puro ($p < 0{,}0001$ unilateral, $\\delta = +0{,}61$)",
     "do objetivo puro ($p < 0{,}0001$ unilateral, $\\delta = +0{,}81$)", "mega"),
    ("M1: a desigualdade do p fica falsa (1e-4 -> 1e-7)",
     "do objetivo puro ($p < 0{,}0001$ unilateral",
     "do objetivo puro ($p < 0{,}0000001$ unilateral", "mega"),
    ("M1: o p do Fisher exato sobre a convergência",
     "(Fisher exato, $p < 0{,}0001$)", "(Fisher exato, $p < 0{,}0000001$)",
     "mega"),
    ("M2: o p contra o PPO (0,0010 -> 0,0100)",
     "($14/28$; $p = 0{,}0010$, $\\delta = +0{,}51$)",
     "($14/28$; $p = 0{,}0100$, $\\delta = +0{,}51$)", "mega"),
    ("M2: o δ contra o SAC (0,99 -> 0,79)",
     "($14/28$; $p < 0{,}0001$, $\\delta = +0{,}99$)",
     "($14/28$; $p < 0{,}0001$, $\\delta = +0{,}79$)", "mega"),
    ("M2: o p do par objetivo vs PPO (0,088 -> 0,188)",
     "permanecem indistinguíveis ($p = 0{,}088$)",
     "permanecem indistinguíveis ($p = 0{,}188$)", "mega"),
    ("M3: o p entre campanhas (0,0016 -> 0,0106)",
     "do peso fixo ($p = 0{,}0016$, $\\delta = +0{,}77$)",
     "do peso fixo ($p = 0{,}0106$, $\\delta = +0{,}77$)", "mega"),
    ("M3: o δ entre campanhas (0,77 -> 0,57)",
     "do peso fixo ($p = 0{,}0016$, $\\delta = +0{,}77$)",
     "do peso fixo ($p = 0{,}0016$, $\\delta = +0{,}57$)", "mega"),
    # As percentagens viviam FIXAS dentro dos padrões do verificador: eram
    # exigidas, não conferidas.
    ("A5: a percentagem do Sandbox (95% -> 91%)",
     "para $\\mathbf{20/21}$ ($95\\%$)", "para $\\mathbf{20/21}$ ($91\\%$)",
     "mega"),
    ("A5: o braço de referência do Sandbox (5/7 -> 4/7)",
     "de $5/7$ ($71\\%$) do objetivo", "de $4/7$ ($71\\%$) do objetivo", "mega"),
    ("A5: a média do braço de referência (38,3 -> 39,3)",
     "contra $38{,}3 \\pm 31{,}0$", "contra $39{,}3 \\pm 31{,}0$", "mega"),
    ("A5: o p da comparação com o objetivo (0,14 -> 0,04)",
     "recolhas/ep ($p = 0{,}14$, $\\delta = +0{,}39$)",
     "recolhas/ep ($p = 0{,}04$, $\\delta = +0{,}39$)", "mega"),
    ("B7: a percentagem da Perceção (81% -> 87%)",
     "$17/21$ ($81\\%$) e $17{,}5", "$17/21$ ($87\\%$) e $17{,}5", "mega"),
    ("B7: o braço de referência da Perceção (6/7 -> 5/7)",
     "contra $6/7$ ($86\\%$) e $18{,}98 \\pm 8{,}7$",
     "contra $5/7$ ($86\\%$) e $18{,}98 \\pm 8{,}7$", "mega"),
    ("B7: o p da comparação (1,00 -> 0,60)",
     "do objetivo ($p = 1{,}00$, $\\delta = +0{,}01$)",
     "do objetivo ($p = 0{,}60$, $\\delta = +0{,}01$)", "mega"),
    ("B6: a percentagem do SAC no Gargalo (33% -> 30%)",
     "converge em $7/21$ ($33\\%$)", "converge em $7/21$ ($30\\%$)", "mega"),
    ("B6: o 5/7 da campanha final (5/7 -> 6/7)",
     "resolvera em apenas $5/7$", "resolvera em apenas $6/7$", "mega"),
    ("B6: a média da campanha final (41,4 -> 44,4)",
     "com os $41{,}4 \\pm 36{,}8$ da campanha final",
     "com os $44{,}4 \\pm 36{,}8$ da campanha final", "mega"),
    # ── Os ecos dos testes da QI6 no Capítulo 6 (18 ago) ────────────────────
    # Cada uma destas mutações estraga **só o eco**, deixando o Capítulo 5
    # intacto: é o defeito que a coerência interna existe para apanhar, e
    # nenhum verificador que compare com os CSV o veria — o número do sítio
    # onde o resultado é produzido continua certo.
    ("eco da QI6: o p do Muro em U com peso fixo (0,026 -> 0,036)",
     "(Mann--Whitney $p=0{,}026$, $\\delta=+0{,}71$)",
     "(Mann--Whitney $p=0{,}036$, $\\delta=+0{,}71$)", "coerencia"),
    ("eco da QI6: o δ da Porta com Alternativa (-1,00 -> -0,90)",
     "$p=0{,}0006$, $\\delta=-1{,}00$), desmascarando",
     "$p=0{,}0006$, $\\delta=-0{,}90$), desmascarando", "coerencia"),
    ("eco da QI6: o δ de T2 (0,76 -> 0,66)",
     "$p=0{,}009$, $\\delta=+0{,}76$ vs.\\ objetivo",
     "$p=0{,}009$, $\\delta=+0{,}66$ vs.\\ objetivo", "coerencia"),
    ("eco da QI6: a magnitude de T4 (77,2 -> 79,2)",
     "superou o peso fixo em magnitude no bypass ($77{,}2$",
     "superou o peso fixo em magnitude no bypass ($79{,}2$", "coerencia"),
    ("eco da QI6: o controlo de orçamento (4/7 -> 3/7)",
     "continua bimodal no Muro em U ($4/7$)",
     "continua bimodal no Muro em U ($3/7$)", "coerencia"),
    ("eco da QI6: o p do Fisher (1e-4 -> 1e-3)",
     "(Fisher exato, $p<0{,}0001$)", "(Fisher exato, $p<0{,}001$)", "coerencia"),
    ("eco da QI6: a contagem do PPO no mega-treino (14 -> 13)",
     "$14/28$ do PPO e $14/28$ do SAC, sendo a única",
     "$13/28$ do PPO e $14/28$ do SAC, sendo a única", "coerencia"),
    ("eco da QI6: o p de M3 (0,0016 -> 0,0026)",
     "($80{,}9$ vs.\\ $63{,}0$; $p=0{,}0016$, $\\delta=+0{,}77$)",
     "($80{,}9$ vs.\\ $63{,}0$; $p=0{,}0026$, $\\delta=+0{,}77$)", "coerencia"),
    # ── Os ecos do mapa composto (18 ago) ───────────────────────────────────
    # A secção do mapa entra por `\input` e vive noutro ficheiro: os números
    # dela são recontados na Discussão Global e nas Conclusões, e são os mais
    # novos da dissertação. Estas mutações estragam o eco, nunca a secção.
    ("eco do mapa: as células do F1 (84 -> 82)",
     "as $84$ células do estudo de transferência",
     "as $82$ células do estudo de transferência", "coerencia"),
    ("eco do mapa: quem resolve com treino nativo (4/21 -> 5/21)",
     "em $4$ das $21$ execuções, contra $0$ de $21$ do PPO",
     "em $5$ das $21$ execuções, contra $0$ de $21$ do PPO", "coerencia"),
    ("eco do mapa: o limiar pré-registado (15 -> 12)",
     "abaixo do limiar de $15$ execuções convergentes",
     "abaixo do limiar de $12$ execuções convergentes", "coerencia"),
    ("eco do mapa: o δ de M1 (0,19 -> 0,29)",
     "$\\delta = +0{,}19$ entre o evolutivo",
     "$\\delta = +0{,}29$ entre o evolutivo", "coerencia"),
]

VERIFICADORES = {
    "escala": lambda: V.verificar_escalabilidade_prosa(0.05),
    "simulador": V.verificar_simulador,
    "hiper": V.verificar_hiperparametros,
    "discussao": lambda: V.verificar_discussao_global(0.05),
    "coerencia": V.verificar_coerencia_interna,
    "novelty": lambda: V.verificar_novelty(0.05),
    "mega": lambda: V.verificar_megatreino(0.05),
}


def correr(qual):
    """Corre um verificador calado e devolve a lista de problemas."""
    with contextlib.redirect_stdout(io.StringIO()):
        return VERIFICADORES[qual]()


def main():
    original = open(V.MAIN_TEX, encoding="utf-8").read()
    tmp = os.path.join(tempfile.gettempdir(), "main_mutado_ensaio.tex")
    V.MAIN_TEX = tmp
    shutil.copy(os.path.join(RAIZ, "Tese", "main.tex"), tmp)
    # A coerência interna junta ao `main.tex` a secção que este inclui por
    # `\input`, e procura-a AO LADO dele. Sem esta cópia, os factos do mapa
    # composto ficariam sem um dos sítios durante o ensaio — e o controlo
    # acusaria quatro problemas que a tese não tem.
    incluido = os.path.join(RAIZ, "Tese", "seccao_mapa_grande.tex")
    tmp_incluido = os.path.join(os.path.dirname(tmp), "seccao_mapa_grande.tex")
    if os.path.exists(incluido):
        shutil.copy(incluido, tmp_incluido)
    else:                                                    # pragma: no cover
        tmp_incluido = None

    print("=" * 72)
    print("ENSAIO: a tese estragada de propósito, uma mutação de cada vez")
    print("=" * 72)

    # Controlo: com a tese intacta ninguém pode acusar nada. Se acusar, o
    # ensaio não mede coisa nenhuma — as mutações passariam a «apanhadas» por
    # herança de um problema que já existia.
    base = {q: correr(q) for q in VERIFICADORES}
    for q, p in sorted(base.items()):
        print("   controlo %-10s %d problema(s)" % (q, len(p)))
    print()

    falhas = 0
    for rot, velho, novo, qual in MUTACOES:
        if velho not in original:
            print("   [ERRO DE ENSAIO] a frase mudou, não encontrei: %r"
                  % velho[:60])
            falhas += 1
            continue
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(original.replace(velho, novo))
        probs = correr(qual)
        apanhada = len(probs) > len(base[qual])
        print("   %s [%-9s] %s" % ("[v]" if apanhada else "[X] NÃO APANHADA",
                                   qual, rot))
        if not apanhada:
            falhas += 1

    os.remove(tmp)
    if tmp_incluido and os.path.exists(tmp_incluido):
        os.remove(tmp_incluido)
    print()
    if falhas or any(base.values()):
        print("%d de %d mutações NÃO foram apanhadas — há buracos."
              % (falhas, len(MUTACOES)))
        return 1
    print("As %d mutações foram todas apanhadas. Os verificadores mordem."
          % len(MUTACOES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
