import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
import os
import pandas as pd
import glob
import time
from datetime import timedelta

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ModernDashboardV4(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔬 Swarm Robotics Controller V4.0 - Multidimensional Thesis")
        self.geometry("1100x850")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.mode = "2D"  # Modo inicial padrãooooo

        self.gnn_process = None
        self.ppo_process = None
        self.gnn_start_time = None
        self.ppo_start_time = None

        # --- CABEÇALHO ---
        self.lbl_title = ctk.CTkLabel(self, text="SISTEMA DE CONTROLO MULTIDIMENSIONAL", font=("Roboto", 26, "bold"))
        self.lbl_title.pack(pady=10)

        # --- SELETOR DE MODO (O Botão Mágico) ---
        self.mode_selector = ctk.CTkSegmentedButton(self, values=["2D", "3D"], command=self.change_mode,
                                                    font=("Roboto", 16, "bold"), height=40, dynamic_resizing=False,
                                                    width=300)
        self.mode_selector.set("2D")
        self.mode_selector.pack(pady=10)

        self.lbl_mode_status = ctk.CTkLabel(self, text="MODO ATUAL: ARENA TERRESTRE (2D)", text_color="#4FC3F7",
                                            font=("Consolas", 14))
        self.lbl_mode_status.pack(pady=5)

        # --- MAIN FRAME ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.setup_gnn_ui()
        self.setup_ppo_ui()

        # --- FOOTER ---
        self.btn_plot_thesis = ctk.CTkButton(self, text="📊 Gerar Gráfico Comparativo Final (Tese)",
                                             command=self.plot_thesis, fg_color="#8E24AA", hover_color="#6A1B9A",
                                             font=("Roboto", 16, "bold"), height=45)
        self.btn_plot_thesis.pack(fill="x", padx=30, pady=20)

        self.update_metrics()

    def change_mode(self, value):
        self.mode = value
        if value == "2D":
            self.lbl_mode_status.configure(text="MODO ATUAL: ARENA TERRESTRE (2D)", text_color="#4FC3F7")
            self.frame_gnn_title.configure(text_color="#4CAF50")
            self.frame_ppo_title.configure(text_color="#FFA726")
        else:
            self.lbl_mode_status.configure(text="MODO ATUAL: ARENA DE DRONES (3D)", text_color="#F06292")
            self.frame_gnn_title.configure(text_color="#F06292")
            self.frame_ppo_title.configure(text_color="#F06292")
        self.update_metrics()

    def get_paths(self):
        """Retorna os caminhos dos logs e modelos baseados no modo 2D ou 3D"""
        if self.mode == "2D":
            return {
                "gnn_log": os.path.join(self.base_dir, 'results/logs/gnn_fair_training.csv'),
                "ppo_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo.csv'),
                "gnn_script": "src/training/evo_trainer.py",
                "ppo_script": "src/training/train_ppo.py",
                "viz_gnn": "visualize_continuous.py",
                "viz_ppo": "visualize_ppo.py",
                "plot_script": "plot_final_thesis.py"
            }
        else:
            return {
                "gnn_log": os.path.join(self.base_dir, 'results/logs/gnn_3d_training.csv'),
                "ppo_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo_3d.csv'),
                "gnn_script": "src/training/evo_trainer_3d.py",
                "ppo_script": "src/training/train_ppo_3d.py",
                "viz_gnn": "visualize_3d.py",
                "viz_ppo": "visualize_ppo_3d.py",  # Criaremos este a seguir
                "plot_script": "plot_final_thesis_3d.py"  # Criaremos este a seguir
            }

    def setup_gnn_ui(self):
        self.frame_gnn = ctk.CTkFrame(self.main_frame)
        self.frame_gnn.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.frame_gnn_title = ctk.CTkLabel(self.frame_gnn, text="🧬 Evolutivo (GNN)", font=("Roboto", 18, "bold"),
                                            text_color="#4CAF50")
        self.frame_gnn_title.pack(pady=15)

        input_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Gerações:").pack(side="left", padx=5)
        self.entry_gnn_target = ctk.CTkEntry(input_frame, width=60);
        self.entry_gnn_target.insert(0, "50");
        self.entry_gnn_target.pack(side="left")

        self.lbl_gnn_status = ctk.CTkLabel(self.frame_gnn, text="Status: PARADO", font=("Consolas", 12))
        self.lbl_gnn_status.pack(pady=5)
        self.lbl_gnn_timer = ctk.CTkLabel(self.frame_gnn, text="Tempo: 00:00:00", font=("Consolas", 12));
        self.lbl_gnn_timer.pack()

        self.metrics_gnn = ctk.CTkFrame(self.frame_gnn, fg_color="#2b2b2b")
        self.metrics_gnn.pack(fill="x", padx=20, pady=10)
        self.lbl_gnn_gen = ctk.CTkLabel(self.metrics_gnn, text="PROGRESSO: 0%", font=("Consolas", 18, "bold"));
        self.lbl_gnn_gen.pack(pady=5)
        self.lbl_gnn_best = ctk.CTkLabel(self.metrics_gnn, text="BEST: ---", font=("Consolas", 16),
                                         text_color="#4CAF50");
        self.lbl_gnn_best.pack(pady=2)

        self.gnn_bar = ctk.CTkProgressBar(self.frame_gnn, progress_color="#4CAF50");
        self.gnn_bar.set(0);
        self.gnn_bar.pack(fill="x", padx=20, pady=15)

        self.btn_gnn_start = ctk.CTkButton(self.frame_gnn, text="▶ Iniciar Treino", command=self.start_gnn,
                                           fg_color="#4CAF50");
        self.btn_gnn_start.pack(pady=5, padx=20, fill="x")
        self.btn_gnn_stop = ctk.CTkButton(self.frame_gnn, text="⏹ Parar", command=self.stop_gnn, fg_color="#F44336");
        self.btn_gnn_stop.pack(pady=5, padx=20, fill="x")
        self.btn_gnn_viz = ctk.CTkButton(self.frame_gnn, text="🎥 Visualizar Melhor", command=self.viz_gnn,
                                         fg_color="#1F6AA5");
        self.btn_gnn_viz.pack(pady=15, padx=20, fill="x")

    def setup_ppo_ui(self):
        self.frame_ppo = ctk.CTkFrame(self.main_frame)
        self.frame_ppo.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.frame_ppo_title = ctk.CTkLabel(self.frame_ppo, text="🤖 Por Reforço (PPO)", font=("Roboto", 18, "bold"),
                                            text_color="#FFA726")
        self.frame_ppo_title.pack(pady=15)

        input_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Steps:").pack(side="left", padx=5)
        self.entry_ppo_target = ctk.CTkEntry(input_frame, width=80);
        self.entry_ppo_target.insert(0, "500000");
        self.entry_ppo_target.pack(side="left")

        self.lbl_ppo_status = ctk.CTkLabel(self.frame_ppo, text="Status: PARADO", font=("Consolas", 12))
        self.lbl_ppo_status.pack(pady=5)
        self.lbl_ppo_timer = ctk.CTkLabel(self.frame_ppo, text="Tempo: 00:00:00", font=("Consolas", 12));
        self.lbl_ppo_timer.pack()

        self.metrics_ppo = ctk.CTkFrame(self.frame_ppo, fg_color="#2b2b2b")
        self.metrics_ppo.pack(fill="x", padx=20, pady=10)
        self.lbl_ppo_steps = ctk.CTkLabel(self.metrics_ppo, text="STEPS: 0k", font=("Consolas", 18, "bold"));
        self.lbl_ppo_steps.pack(pady=5)
        self.lbl_ppo_score = ctk.CTkLabel(self.metrics_ppo, text="MEAN: ---", font=("Consolas", 16),
                                          text_color="#FFA726");
        self.lbl_ppo_score.pack(pady=2)

        self.ppo_bar = ctk.CTkProgressBar(self.frame_ppo, progress_color="#FFA726");
        self.ppo_bar.set(0);
        self.ppo_bar.pack(fill="x", padx=20, pady=15)

        self.btn_ppo_start = ctk.CTkButton(self.frame_ppo, text="▶ Iniciar Treino", command=self.start_ppo,
                                           fg_color="#FFA726", text_color="black");
        self.btn_ppo_start.pack(pady=5, padx=20, fill="x")
        self.btn_ppo_stop = ctk.CTkButton(self.frame_ppo, text="⏹ Parar", command=self.stop_ppo, fg_color="#F44336");
        self.btn_ppo_stop.pack(pady=5, padx=20, fill="x")
        self.btn_ppo_viz = ctk.CTkButton(self.frame_ppo, text="🎥 Visualizar Melhor", command=self.viz_ppo,
                                         fg_color="#1F6AA5");
        self.btn_ppo_viz.pack(pady=15, padx=20, fill="x")

    def run_script(self, script, args=[]):
        full_path = os.path.join(self.base_dir, script)
        return subprocess.Popen([sys.executable, full_path] + args)

    def start_gnn(self):
        paths = self.get_paths()
        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        self.gnn_process = self.run_script(paths["gnn_script"], ["--generations", self.entry_gnn_target.get()])
        self.gnn_start_time = time.time()

    def stop_gnn(self):
        if self.gnn_process: self.gnn_process.terminate(); self.gnn_process = None
        self.gnn_start_time = None

    def start_ppo(self):
        paths = self.get_paths()
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        self.ppo_process = self.run_script(paths["ppo_script"])
        self.ppo_start_time = time.time()

    def stop_ppo(self):
        if self.ppo_process: self.ppo_process.terminate(); self.ppo_process = None
        self.ppo_start_time = None

    def viz_gnn(self):
        self.run_script(self.get_paths()["viz_gnn"])

    def viz_ppo(self):
        self.run_script(self.get_paths()["viz_ppo"])

    def plot_thesis(self):
        self.run_script(self.get_paths()["plot_script"])

    def update_metrics(self):
        paths = self.get_paths()
        # Update GNN
        if os.path.exists(paths["gnn_log"]):
            try:
                df = pd.read_csv(paths["gnn_log"]).apply(pd.to_numeric, errors='coerce').dropna()
                if not df.empty:
                    row = df.iloc[-1]
                    # No 3D usamos timesteps, no 2D linhas. Ajustamos para mostrar %
                    target_gens = int(self.entry_gnn_target.get())
                    progress = len(df) / target_gens
                    self.lbl_gnn_gen.configure(text=f"PROGRESSO: {min(100, int(progress * 100))}%")
                    self.lbl_gnn_best.configure(text=f"BEST FIT: {row['best_fitness']:.1f}")
                    self.gnn_bar.set(min(1.0, progress))
            except:
                pass

        # Update PPO
        if os.path.exists(paths["ppo_log"]):
            try:
                df = pd.read_csv(paths["ppo_log"]).apply(pd.to_numeric, errors='coerce').dropna()
                if not df.empty:
                    row = df.iloc[-1]
                    steps = int(row['timesteps'])
                    target = int(self.entry_ppo_target.get())
                    self.lbl_ppo_steps.configure(text=f"STEPS: {steps / 1000:.0f}k")
                    self.lbl_ppo_score.configure(text=f"MEAN: {row['ep_rew_mean']:.1f}")
                    self.ppo_bar.set(min(1.0, steps / target))
            except:
                pass

        if self.gnn_start_time: self.lbl_gnn_timer.configure(
            text=f"Tempo: {str(timedelta(seconds=int(time.time() - self.gnn_start_time)))}")
        if self.ppo_start_time: self.lbl_ppo_timer.configure(
            text=f"Tempo: {str(timedelta(seconds=int(time.time() - self.ppo_start_time)))}")

        self.after(1000, self.update_metrics)


if __name__ == "__main__":
    app = ModernDashboardV4()
    app.mainloop()