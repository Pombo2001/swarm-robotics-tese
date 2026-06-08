"""
gerar_pdf_reuniao.py — Compila os gráficos-chave num PDF para a reunião
=======================================================================
Junta, por ordem narrativa, os gráficos mais importantes da pasta de relatório
mais recente (results/graficos_tese/<sessao>/) com títulos e legendas em
português, prontos para apresentar ao orientador.

Uso: python scripts/gerar_pdf_reuniao.py
Saída: results/Reuniao_orientador.pdf
"""
import os
import sys
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _latest_report_dir():
    base = os.path.join(PROJECT_ROOT, "results", "graficos_tese")
    dirs = [d for d in glob.glob(os.path.join(base, "*")) if os.path.isdir(d)
            and os.path.basename(d) != "estatisticas"]
    if not dirs:
        return None
    return max(dirs, key=os.path.getmtime)


def _page_text(pdf, title, lines):
    """Página de texto (capa / secção)."""
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 retrato
    fig.text(0.5, 0.88, title, ha="center", va="top", fontsize=20, fontweight="bold")
    y = 0.78
    for ln in lines:
        bold = ln.startswith("**")
        txt = ln.replace("**", "")
        fig.text(0.10, y, txt, ha="left", va="top", fontsize=12.5,
                 fontweight="bold" if bold else "normal", color="#111827", wrap=True)
        y -= 0.045 if not bold else 0.055
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def _page_image(pdf, path, title, caption):
    """Página com uma imagem + título + legenda."""
    if not os.path.exists(path):
        return
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.5, 0.95, title, ha="center", va="top", fontsize=15, fontweight="bold")
    ax = fig.add_axes([0.06, 0.18, 0.88, 0.72])
    ax.imshow(plt.imread(path))
    ax.axis("off")
    fig.text(0.5, 0.12, caption, ha="center", va="top", fontsize=10.5,
             color="#374151", wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def _page_grid(pdf, paths, title, caption, cols=3):
    """Página com uma grelha de imagens (ex.: heatmaps lado a lado)."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return
    rows = (len(paths) + cols - 1) // cols
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.5, 0.95, title, ha="center", va="top", fontsize=15, fontweight="bold")
    for i, p in enumerate(paths):
        ax = fig.add_subplot(rows, cols, i + 1)
        ax.imshow(plt.imread(p))
        ax.axis("off")
    fig.text(0.5, 0.07, caption, ha="center", va="top", fontsize=10.5,
             color="#374151", wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    rep = _latest_report_dir()
    if rep is None:
        print("[!] Sem pasta de relatório. Corre o 'Gerar Relatório Completo' primeiro.")
        return
    print(f"[*] A usar relatório: {os.path.basename(rep)}")

    def P(name):
        return os.path.join(rep, name)

    out = os.path.join(PROJECT_ROOT, "results", "Reuniao_orientador.pdf")
    with PdfPages(out) as pdf:
        # ── Capa ────────────────────────────────────────────────────────────
        _page_text(pdf, "Controlo de Enxames por RL\nResumo para reunião", [
            "**Progresso desde 21 de maio",
            "",
            "**1. Diagnóstico do bloqueio nas paredes",
            "A causa não era a física, mas a função de recompensa:",
            "  • progresso euclidiano criava mínimos locais (contornar = afastar = penalizado);",
            "  • um mecanismo de respawn permitia acumular recompensa sem cumprir a tarefa.",
            "",
            "**2. Correção principal: recompensa de progresso GEODÉSICA",
            "Distância que contorna as paredes (Dijkstra) em vez da linha reta.",
            "PBRS (Ng et al., 1999) — não altera a política ótima. É sinal de treino,",
            "não observação (sem 'batota': o robô só tem bússola + LiDAR local).",
            "",
            "**3. Avaliação separada do treino (pedido do orientador)",
            "Métrica de TAREFA (recolhas/sucesso), determinística, sem o bónus de shaping.",
            "Nota: NÃO há ICM — a exploração é só reward shaping (progresso + count-based).",
            "",
            "**4. Lição do treino de 8h",
            "5 runs x 6 cenários x 3 algos -> ~4-5 min/treino (subtreino). Solução:",
            "escolher menos cenários -> mais tempo por treino (agora no menu).",
        ])

        # ── Cenários ────────────────────────────────────────────────────────
        _page_grid(pdf, [P(f"mapa_3d_{s}.png") for s in
                         ["none", "u_wall", "bottleneck", "four_rooms",
                          "cooperative_door", "cooperative_perception"]],
                   "Os 6 cenários de teste (geometria 3D)",
                   "Sandbox, Muro em U, Gargalo, Quatro Salas, Porta Cooperativa e "
                   "Perceção (alvo móvel). A esfera verde é o ninho/alvo.", cols=2)

        # ── Métrica principal ───────────────────────────────────────────────
        _page_image(pdf, P("taxa_sucesso_por_cenario.png"),
                    "Resultado-chave: taxa de sucesso por cenário",
                    "Avaliação determinística (métrica de tarefa). PPO 100% em 5/6 cenários; "
                    "SAC forte nos cenários abertos mas subtreinado nos labirintos (4-5 min/treino); "
                    "GNN limitado pela eficiência da neuroevolução. Muro U é o caso-limite (todos falham).")

        _page_image(pdf, P("recolhas_por_cenario.png"),
                    "Recolhas por episódio (magnitude do desempenho)",
                    "Complementa a taxa de sucesso: mede quantas recolhas, não só sucesso/falha.")

        # ── Reward enganador ────────────────────────────────────────────────
        _page_image(pdf, P("comparacao_barras_geral.png"),
                    "Porque avaliamos pela tarefa, não pelo reward",
                    "O reward de treino é ENGANADOR: o GNN atinge ~98.000 de fitness no Muro U "
                    "com ZERO recolhas reais (acumula shaping sem cumprir a tarefa). Daí medir o "
                    "desempenho pela métrica de tarefa (recolhas), como pedido pelo orientador.")

        # ── A correção (geodésico) ──────────────────────────────────────────
        _page_image(pdf, P("heatmap_geodesico_u_wall.png"),
                    "A correção: potencial euclidiano vs geodésico (Muro U)",
                    "Esquerda (euclidiano): as linhas de nível atravessam a parede e puxam o robô "
                    "para dentro do beco. Direita (geodésico): contornam a parede, recompensando o "
                    "desvio correto. Elimina o mínimo local que prendia os robôs.")

        # ── Comportamento (heatmaps de ocupação) ────────────────────────────
        _page_grid(pdf, [P("heatmap_ocupacao_ppo_four_rooms.png"),
                         P("heatmap_ocupacao_sac_bottleneck.png"),
                         P("heatmap_ocupacao_gnn_u_wall.png")],
                   "Onde os robôs passam (heatmaps de ocupação)",
                   "Diagnóstico visual: PPO contorna o labirinto de 4 salas e o SAC atravessa o "
                   "gargalo até ao ninho; o GNN (subtreinado) fica preso contra a parede do Muro U. "
                   "Zonas brilhantes coladas a uma parede = robôs presos.", cols=3)

        # ── Curvas de aprendizagem (exemplo) ────────────────────────────────
        _page_image(pdf, P("comparacao_mapa_four_rooms.png"),
                    "Curvas de aprendizagem — Quatro Salas (exemplo)",
                    "Eixo X normalizado (0-100% do treino de cada algoritmo) para comparação justa "
                    "entre paradigmas (GNN evolutivo vs PPO/SAC com gradiente).")

    print(f"[OK] PDF gerado: {out}")
    if os.name == "nt":
        try:
            os.startfile(out)
        except Exception:
            pass


if __name__ == "__main__":
    main()
