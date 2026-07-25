"""
gerar_figuras_mapa_grande.py — Figuras do MAPA GRANDE (8.º cenário)
====================================================================
Produz, para o mapa grande, o mesmo conjunto de figuras que os 7 cenários já
têm — mais as que só fazem sentido num mapa composto.

Segue o estilo do `gerar_figuras_7d.py` (mesmas cores por algoritmo, mesmas
legendas de rodapé a explicar a métrica, 300 dpi) para as figuras da tese terem
todas o mesmo aspeto.

**Cada figura só é gerada se os dados que ela precisa existirem.** Um mapa por
treinar produz apenas as figuras geométricas (planta, campo geodésico) — e é
isso que se espera antes da campanha. Nada é inventado nem preenchido a zeros.

Figuras:
  A. GEOMETRIA (não precisa de treino nenhum)
     1. mapa_grande_planta.png ......... planta com as 5 zonas e o percurso
     2. (o campo geodésico vem do heatmaps.py --mode geodesic, já existente)
  B. ZERO-SHOT DE TOPOLOGIA (precisa de results/evaluation/zeroshot_mapa_grande.csv)
     3. mapa_grande_zeroshot_heatmap.png  matriz origem x algoritmo
     4. mapa_grande_zeroshot_barras.png   recolhas/ep por algoritmo
  C. CAMPANHA NATIVA (precisa de eval_by_run com o cenário — fase F2)
     5. mapa_grande_boxplot.png ........ fiabilidade entre runs
     6. mapa_grande_curvas.png ......... curvas de treino por algoritmo
     7. mapa_grande_conclusoes.png ..... painel-síntese (a figura de conclusões)

Uso:
    .venv/Scripts/python.exe scripts/gerar_figuras_mapa_grande.py
    .venv/Scripts/python.exe scripts/gerar_figuras_mapa_grande.py --mapa mapa_grande
"""
import argparse
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.scenarios import SCENARIO_LABELS, SCENARIO_LABELS_SHORT, ALGO_COLORS

OUT = os.path.join(PROJECT_ROOT, "results", "graficos_tese", "mapa_grande")
EVAL_DIR = os.path.join(PROJECT_ROOT, "results", "evaluation")
ALGOS = ["GNN", "PPO", "SAC"]

RODAPE = ("Métrica de TAREFA (recolhas por episódio em avaliação determinística): "
          "mesma unidade para os três algoritmos, diretamente comparável.")


def _rodape(fig, texto=RODAPE):
    fig.text(0.5, 0.01, texto, ha="center", va="bottom", fontsize=8.5,
             color="#555555", style="italic")


# ────────────────────────────── A. GEOMETRIA ──────────────────────────────
def fig_planta(mapa, raio=60.0):
    """Planta do mapa com as 5 zonas, lendo a geometria do AMBIENTE real."""
    import copy
    import yaml
    from matplotlib.patches import Rectangle, Circle
    from src.environment.swarm_env_3d import SwarmForagingEnv3D

    with open(os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")) as f:
        cfg = copy.deepcopy(yaml.safe_load(f))
    cfg["environment"]["classic_scenario"] = mapa
    env = SwarmForagingEnv3D(config=cfg)
    np.random.seed(7)
    env.reset(seed=7)

    R = env.arena_radius
    fig, ax = plt.subplots(figsize=(13, 13))
    ax.add_patch(Circle((0, 0), R, facecolor="#EAEDF2", edgecolor="#94A3B8",
                        lw=2, ls="--", zorder=0))
    for i, w in enumerate(env.walls):
        cor = "#F59E0B" if i == env.door_wall_index else "#3B4252"
        ax.add_patch(Rectangle((w["pos"][0] - w["size"][0] / 2,
                                w["pos"][1] - w["size"][1] / 2),
                               w["size"][0], w["size"][1],
                               facecolor=cor, zorder=3))
    for o in env.obstacles:
        ax.add_patch(Circle(o[:2], 0.6, facecolor="#B45309", alpha=0.85, zorder=4))
    ax.add_patch(Circle(env.nest_pos[:2], 1.5, facecolor="#22C55E",
                        edgecolor="white", lw=2, zorder=6))
    ax.text(env.nest_pos[0], env.nest_pos[1] + 3, "NINHO", ha="center",
            fontsize=12, fontweight="bold", color="#166534", zorder=6)
    for p in env.agent_positions:
        ax.add_patch(Circle(p[:2], 0.5, facecolor="#3D9EFF",
                            edgecolor="white", lw=0.8, zorder=6))

    k = 2 * R / np.sqrt(34)
    W, H = 5 * k, 3 * k
    for frac, txt in [(0.10, "S · Partida"), (0.32, "A · Gargalo + U"),
                      (0.53, "B · Quatro Salas"), (0.73, "C · Porta coop."),
                      (0.93, "D · Ninho")]:
        ax.text(-W / 2 + frac * W, H / 2 - 0.05 * H, txt, ha="center",
                fontsize=10.5, fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#CBD5E1"))

    # barra de escala
    ax.plot([-R * 0.95, -R * 0.95 + 10], [-R * 0.93] * 2, color="#0F172A", lw=4)
    ax.text(-R * 0.95 + 5, -R * 0.90, "10 m", ha="center", fontsize=10,
            fontweight="bold")

    dmax = np.nanmax(env.geo_field[np.isfinite(env.geo_field)])
    ax.set_title(f"{SCENARIO_LABELS.get(mapa, mapa)} — arena r={R:.0f} m, "
                 f"labirinto {W:.0f}×{H:.0f} m\n"
                 f"pior percurso ao ninho: {dmax:.0f} m  ·  "
                 f"{len(env.obstacles)} obstáculos  ·  {env.num_agents} robôs",
                 fontsize=14, fontweight="bold", pad=14)
    ax.set_xlim(-R * 1.02, R * 1.02)
    ax.set_ylim(-R * 1.02, R * 1.02)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(alpha=0.12)
    _rodape(fig, "Geometria lida do simulador (classic_scenario: %s) — é o mapa "
                 "que os robôs treinam, não um esquema à parte." % mapa)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(OUT, f"{mapa}_planta.png"), dpi=300)
    plt.close(fig)
    print(f"[OK] {mapa}_planta.png")


# ─────────────────────── B. ZERO-SHOT DE TOPOLOGIA ───────────────────────
def figs_zeroshot(mapa):
    fp = os.path.join(EVAL_DIR, f"zeroshot_{mapa}.csv")
    if not os.path.exists(fp):
        print(f"[--] {os.path.basename(fp)} não existe — F1 por correr "
              f"(scripts/eval_zeroshot_mapa.py). Figuras de zero-shot saltadas.")
        return
    df = pd.read_csv(fp)

    # ── PRIMEIRO filtrar a condição, SÓ DEPOIS validar a geometria ───────────
    # O CSV tem várias condições a conviver (--norm-obs e --controlo). Misturá-las
    # num gráfico faria a média de experiências diferentes sem dar sinal disso; e
    # validar o env_hash do ficheiro INTEIRO rejeitava tudo por causa do controlo
    # 'sem_obstaculos', que tem outra digital de propósito (muda o mundo).
    if "Controlo" not in df.columns:
        df["Controlo"] = "base"      # CSVs anteriores a 25 jul: só havia a base
    if "NormObs" not in df.columns:
        df["NormObs"] = "mapa"
    presentes = sorted(set(zip(df["NormObs"], df["Controlo"])))
    df = df[(df["NormObs"] == "mapa") & (df["Controlo"] == "base")]
    if df.empty:
        print("[--] só há dados de condições de CONTROLO — figuras de zero-shot "
              "saltadas (a figura oficial é a condição natural).")
        return
    if len(presentes) > 1:
        print(f"[i] condições no CSV: {presentes} — as figuras usam ('mapa','base'). "
              f"O contraste com os controlos vive no pré-registo, não nestas figuras.")

    # A condição natural é de ESTE mapa? Uma figura publicada a partir de uma
    # avaliação feita noutra geometria é pior do que figura nenhuma: parece um
    # resultado. Sem env_hash o CSV é anterior à digital e não se pode verificar.
    import copy
    import yaml
    from scripts.eval_zeroshot_mapa import _impressao_digital
    with open(os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")) as f:
        _cfg = copy.deepcopy(yaml.safe_load(f))
    _cfg["environment"]["classic_scenario"] = mapa
    atual = _impressao_digital(_cfg, mapa)
    if "env_hash" not in df.columns:
        print("[--] o zeroshot_%s.csv não tem env_hash (é de uma versão anterior) — "
              "não se pode confirmar que é deste mapa. Figuras de zero-shot saltadas." % mapa)
        return
    if (df["env_hash"] != atual).any():
        print("[--] o zeroshot_%s.csv foi produzido NOUTRA geometria (%s != %s) — "
              "figuras de zero-shot saltadas. Voltar a correr eval_zeroshot_mapa.py."
              % (mapa, df["env_hash"].iloc[0], atual))
        return

    piv = (df.groupby(["Origem", "Algorithm"])["food_collected"].mean()
           .unstack("Algorithm").reindex(columns=ALGOS))
    piv.index = [SCENARIO_LABELS_SHORT.get(i, i) for i in piv.index]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(piv.values, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(piv.columns)), piv.columns)
    ax.set_yticks(range(len(piv.index)), piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                        color="white" if v < np.nanmax(piv.values) * 0.6 else "black",
                        fontweight="bold")
    fig.colorbar(im, ax=ax, label="recolhas/ep (média)")
    ax.set_title(f"Zero-Shot de TOPOLOGIA — campeões avaliados em\n"
                 f"{SCENARIO_LABELS.get(mapa, mapa)}, sem retreino",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Algoritmo")
    ax.set_ylabel("Cenário onde o campeão foi TREINADO")
    _rodape(fig, "Cada célula: campeão treinado noutro cenário, avaliado neste mapa "
                 "sem qualquer retreino. Zero = não chega ao ninho.")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(os.path.join(OUT, f"{mapa}_zeroshot_heatmap.png"), dpi=300)
    plt.close(fig)
    print(f"[OK] {mapa}_zeroshot_heatmap.png")

    fig, ax = plt.subplots(figsize=(9, 6))
    med = df.groupby("Algorithm")["food_collected"].agg(["mean", "std"]).reindex(ALGOS)
    ax.bar(med.index, med["mean"], yerr=med["std"].fillna(0), capsize=6,
           color=[ALGO_COLORS.get(a, "#888") for a in med.index])
    ax.set_title(f"Zero-Shot de topologia — agregado por algoritmo",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Recolhas por episódio (± dp)")
    ax.grid(True, ls="--", alpha=0.4, axis="y")
    _rodape(fig)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(os.path.join(OUT, f"{mapa}_zeroshot_barras.png"), dpi=300)
    plt.close(fig)
    print(f"[OK] {mapa}_zeroshot_barras.png")


# ───────────────────────── C. CAMPANHA NATIVA (F2) ─────────────────────────
def figs_campanha(mapa):
    fp = os.path.join(EVAL_DIR, "eval_by_run.csv")
    if not os.path.exists(fp):
        print("[--] eval_by_run.csv não existe — campanha nativa (F2) por correr.")
        return
    ev = pd.read_csv(fp)
    ev = ev[ev["Scenario"] == mapa]
    if ev.empty:
        print(f"[--] eval_by_run.csv não tem linhas de '{mapa}' — F2 por correr. "
              f"Figuras de campanha saltadas.")
        return

    import seaborn as sns
    rm = (ev.groupby(["Algorithm", "Run"])
          .agg(recolhas=("food_collected", "mean"), sucesso=("success", "mean"))
          .reset_index())

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(data=rm, x="Algorithm", y="recolhas", order=ALGOS,
                palette=ALGO_COLORS, ax=ax)
    sns.stripplot(data=rm, x="Algorithm", y="recolhas", order=ALGOS,
                  color="black", size=5, alpha=0.6, jitter=0.12, ax=ax)
    ax.set_title(f"Fiabilidade entre Runs — {SCENARIO_LABELS.get(mapa, mapa)}",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Recolhas por episódio (média do run)")
    ax.grid(True, ls="--", alpha=0.4, axis="y")
    _rodape(fig, f"Cada ponto = 1 run independente "
                 f"({rm.groupby('Algorithm')['Run'].nunique().max()} runs/algoritmo).")
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(os.path.join(OUT, f"{mapa}_boxplot.png"), dpi=300)
    plt.close(fig)
    print(f"[OK] {mapa}_boxplot.png")

    fig_conclusoes(mapa, ev, rm)


def fig_conclusoes(mapa, ev, rm):
    """Painel-síntese: a figura de conclusões do mapa.

    Junta num só quadro o que a campanha responde: magnitude, fiabilidade,
    convergência e (quando existir) uso da porta cooperativa. É a figura para a
    defesa — uma só imagem que conta a história toda.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    med = rm.groupby("Algorithm")["recolhas"].agg(["mean", "std"]).reindex(ALGOS)
    axes[0].bar(med.index, med["mean"], yerr=med["std"].fillna(0), capsize=6,
                color=[ALGO_COLORS.get(a, "#888") for a in med.index])
    axes[0].set_title("Magnitude", fontweight="bold")
    axes[0].set_ylabel("Recolhas/ep (média ± dp entre runs)")
    axes[0].grid(True, ls="--", alpha=0.4, axis="y")

    conv = rm.assign(ok=rm["recolhas"] > 0).groupby("Algorithm")["ok"].mean().reindex(ALGOS)
    axes[1].bar(conv.index, 100 * conv.values,
                color=[ALGO_COLORS.get(a, "#888") for a in conv.index])
    axes[1].set_title("Convergência (descritivo)", fontweight="bold")
    axes[1].set_ylabel("% de runs com ≥1 recolha")
    axes[1].set_ylim(0, 105)
    axes[1].grid(True, ls="--", alpha=0.4, axis="y")

    suc = rm.groupby("Algorithm")["sucesso"].mean().reindex(ALGOS)
    axes[2].bar(suc.index, 100 * suc.values,
                color=[ALGO_COLORS.get(a, "#888") for a in suc.index])
    axes[2].set_title("Taxa de sucesso", fontweight="bold")
    axes[2].set_ylabel("% de episódios com sucesso")
    axes[2].set_ylim(0, 105)
    axes[2].grid(True, ls="--", alpha=0.4, axis="y")

    fig.suptitle(f"Síntese — {SCENARIO_LABELS.get(mapa, mapa)}",
                 fontsize=15, fontweight="bold")
    _rodape(fig, "Convergência e taxa de sucesso são DESCRITIVOS; a inferência "
                 "faz-se sobre a magnitude (Mann-Whitney + δ de Cliff sobre médias por run).")
    plt.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(os.path.join(OUT, f"{mapa}_conclusoes.png"), dpi=300)
    plt.close(fig)
    print(f"[OK] {mapa}_conclusoes.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapa", default="mapa_grande")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    print(f"Figuras de '{a.mapa}' -> {os.path.relpath(OUT, PROJECT_ROOT)}\n")
    fig_planta(a.mapa)
    figs_zeroshot(a.mapa)
    figs_campanha(a.mapa)
    print("\nNota: as figuras que dependem de dados inexistentes são SALTADAS, "
          "não preenchidas a zeros.")


if __name__ == "__main__":
    main()
