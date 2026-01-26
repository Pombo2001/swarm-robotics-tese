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


class ModernDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔬 Swarm Robotics Controller - Thesis V2.2")
        self.geometry("1050x700")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.gnn_log = os.path.join(self.base_dir, 'results/logs/training_history.csv')
        self.ppo_log = os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo.csv')

        self.gnn_process = None
        self.ppo_process = None

        # --- VARIÁVEIS DE TEMPO ---
        self.gnn_start_time = None
        self.ppo_start_time = None

        # --- LAYOUT ---
        self.lbl_title = ctk.CTkLabel(self, text="SISTEMA DE CONTROLO HÍBRIDO", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=20)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.frame_gnn = ctk.CTkFrame(self.main_frame)
        self.frame_gnn.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_gnn_ui()

        self.frame_ppo = ctk.CTkFrame(self.main_frame)
        self.frame_ppo.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.setup_ppo_ui()

        self.footer = ctk.CTkLabel(self, text="Developed for MSc Thesis • 2025", text_color="gray")
        self.footer.pack(side="bottom", pady=10)

        self.update_metrics()

    def get_latest_gnn_model(self):
        models_dir = os.path.join(self.base_dir, "results/models")
        if not os.path.exists(models_dir): return None, "Nenhum modelo"
        list_of_files = glob.glob(os.path.join(models_dir, "*.pth"))
        if not list_of_files: return None, "Nenhum modelo"
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file, os.path.basename(latest_file)

    def setup_gnn_ui(self):
        ctk.CTkLabel(self.frame_gnn, text="🧬 Algoritmo Genético (GNN)", font=("Roboto", 18, "bold"),
                     text_color="#4CAF50").pack(pady=15)

        input_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Target Gerações:").pack(side="left", padx=5)
        self.entry_gnn_target = ctk.CTkEntry(input_frame, width=60)
        self.entry_gnn_target.insert(0, "100")
        self.entry_gnn_target.pack(side="left")

        # Status
        self.lbl_gnn_status = ctk.CTkLabel(self.frame_gnn, text="Status: PARADO", text_color="#FF5555",
                                           font=("Consolas", 12))
        self.lbl_gnn_status.pack(pady=5)

        # --- NOVO: TEMPORIZADOR ---
        self.lbl_gnn_timer = ctk.CTkLabel(self.frame_gnn, text="Tempo: 00:00:00", font=("Consolas", 12),
                                          text_color="white")
        self.lbl_gnn_timer.pack(pady=0)
        # --------------------------

        metrics_frame = ctk.CTkFrame(self.frame_gnn, fg_color="#2b2b2b")
        metrics_frame.pack(fill="x", padx=20, pady=10)
        self.lbl_gnn_gen = ctk.CTkLabel(metrics_frame, text="GEN: 0", font=("Consolas", 20, "bold"))
        self.lbl_gnn_gen.pack(pady=5)
        self.lbl_gnn_best = ctk.CTkLabel(metrics_frame, text="BEST: ---", font=("Consolas", 16), text_color="#4CAF50")
        self.lbl_gnn_best.pack(pady=2)

        self.gnn_bar = ctk.CTkProgressBar(self.frame_gnn, progress_color="#4CAF50")
        self.gnn_bar.set(0)
        self.gnn_bar.pack(fill="x", padx=20, pady=15)

        btn_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        self.btn_gnn_start = ctk.CTkButton(btn_frame, text="▶ Iniciar", command=self.start_gnn, fg_color="#4CAF50",
                                           hover_color="#388E3C")
        self.btn_gnn_start.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_gnn_stop = ctk.CTkButton(btn_frame, text="⏹ Parar", command=self.stop_gnn, fg_color="#F44336",
                                          hover_color="#D32F2F", state="disabled")
        self.btn_gnn_stop.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(self.frame_gnn, text="📊 Ver Gráfico GNN", command=lambda: self.plot("gnn"), fg_color="#555",
                      hover_color="#666").pack(fill="x", padx=20, pady=5)

        _, model_name = self.get_latest_gnn_model()
        self.btn_gnn_viz = ctk.CTkButton(self.frame_gnn, text=f"🎥 Visualizar ({model_name})", command=self.viz_gnn,
                                         fg_color="#1F6AA5", hover_color="#144870")
        self.btn_gnn_viz.pack(fill="x", padx=20, pady=5)

    def setup_ppo_ui(self):
        ctk.CTkLabel(self.frame_ppo, text="🤖 Reinforcement Learning (PPO)", font=("Roboto", 18, "bold"),
                     text_color="#FFA726").pack(pady=15)

        input_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Target Timesteps:").pack(side="left", padx=5)
        self.entry_ppo_target = ctk.CTkEntry(input_frame, width=80)
        self.entry_ppo_target.insert(0, "500000")
        self.entry_ppo_target.pack(side="left")

        self.lbl_ppo_status = ctk.CTkLabel(self.frame_ppo, text="Status: PARADO", text_color="#FF5555",
                                           font=("Consolas", 12))
        self.lbl_ppo_status.pack(pady=5)

        # --- NOVO: TEMPORIZADOR ---
        self.lbl_ppo_timer = ctk.CTkLabel(self.frame_ppo, text="Tempo: 00:00:00", font=("Consolas", 12),
                                          text_color="white")
        self.lbl_ppo_timer.pack(pady=0)
        # --------------------------

        metrics_frame = ctk.CTkFrame(self.frame_ppo, fg_color="#2b2b2b")
        metrics_frame.pack(fill="x", padx=20, pady=10)
        self.lbl_ppo_steps = ctk.CTkLabel(metrics_frame, text="STEPS: 0k", font=("Consolas", 20, "bold"))
        self.lbl_ppo_steps.pack(pady=5)
        self.lbl_ppo_score = ctk.CTkLabel(metrics_frame, text="MEAN: ---", font=("Consolas", 16), text_color="#FFA726")
        self.lbl_ppo_score.pack(pady=2)

        self.ppo_bar = ctk.CTkProgressBar(self.frame_ppo, progress_color="#FFA726")
        self.ppo_bar.set(0)
        self.ppo_bar.pack(fill="x", padx=20, pady=15)

        btn_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        self.btn_ppo_start = ctk.CTkButton(btn_frame, text="▶ Iniciar", command=self.start_ppo, fg_color="#FFA726",
                                           hover_color="#F57C00", text_color="black")
        self.btn_ppo_start.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_ppo_stop = ctk.CTkButton(btn_frame, text="⏹ Parar", command=self.stop_ppo, fg_color="#F44336",
                                          hover_color="#D32F2F", state="disabled")
        self.btn_ppo_stop.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(self.frame_ppo, text="📊 Ver Gráfico PPO", command=lambda: self.plot("ppo"), fg_color="#555",
                      hover_color="#666").pack(fill="x", padx=20, pady=5)

        self.btn_ppo_viz = ctk.CTkButton(self.frame_ppo, text="🎥 Visualizar (ppo_final)", command=self.viz_ppo,
                                         fg_color="#1F6AA5", hover_color="#144870")
        self.btn_ppo_viz.pack(fill="x", padx=20, pady=5)

    def run_script(self, path, args=[]):
        full_path = os.path.join(self.base_dir, path)
        return subprocess.Popen([sys.executable, full_path] + args)

    def start_gnn(self):
        if self.gnn_process: return
        if os.path.exists(self.gnn_log): os.remove(self.gnn_log)

        # --- MUDANÇA AQUI: Ler o valor da caixa de texto ---
        try:
            gens = int(self.entry_gnn_target.get())
        except:
            gens = 100  # Valor default se der erro

        # Passar o argumento --generations para o script
        self.gnn_process = self.run_script("src/training/evo_trainer.py", ["--generations", str(gens)])
        # ---------------------------------------------------

        self.gnn_start_time = time.time()
        self.btn_gnn_start.configure(state="disabled")
        self.btn_gnn_stop.configure(state="normal")
        self.lbl_gnn_status.configure(text=f"Status: A CORRER ({gens} GENs)", text_color="#4CAF50")

    def stop_gnn(self):
        if self.gnn_process:
            self.gnn_process.terminate()
            self.gnn_process = None
        self.gnn_start_time = None
        self.btn_gnn_start.configure(state="normal")
        self.btn_gnn_stop.configure(state="disabled")
        self.lbl_gnn_status.configure(text="Status: INTERROMPIDO", text_color="#FF5555")

    def start_ppo(self):
        if self.ppo_process: return
        if os.path.exists(self.ppo_log): os.remove(self.ppo_log)
        self.ppo_process = self.run_script("src/training/train_ppo.py")

        self.ppo_start_time = time.time()  # Guardar hora de inicio

        self.btn_ppo_start.configure(state="disabled")
        self.btn_ppo_stop.configure(state="normal")
        self.lbl_ppo_status.configure(text="Status: A CORRER", text_color="#FFA726")

    def stop_ppo(self):
        if self.ppo_process:
            self.ppo_process.terminate()
            self.ppo_process = None
        self.ppo_start_time = None
        self.btn_ppo_start.configure(state="normal")
        self.btn_ppo_stop.configure(state="disabled")
        self.lbl_ppo_status.configure(text="Status: INTERROMPIDO", text_color="#FF5555")

    def viz_gnn(self):
        model_path, _ = self.get_latest_gnn_model()
        if model_path: self.run_script("visualize.py", ["--model", model_path])

    def viz_ppo(self):
        self.run_script("visualize_ppo.py")

    def plot(self, mode):
        self.run_script("plot_results.py", ["--mode", mode])

    def update_metrics(self):
        # 1. GNN
        if os.path.exists(self.gnn_log):
            try:
                df = pd.read_csv(self.gnn_log)
                if not df.empty:
                    row = df.iloc[-1]
                    gen = int(row['generation'])
                    target = int(self.entry_gnn_target.get())
                    self.lbl_gnn_gen.configure(text=f"GEN: {gen} / {target}")
                    self.lbl_gnn_best.configure(text=f"BEST: {row['best_score']:.1f}")
                    self.gnn_bar.set(gen / target)
                    _, name = self.get_latest_gnn_model()
                    if name: self.btn_gnn_viz.configure(text=f"🎥 Visualizar ({name})")
            except:
                pass

        # --- ATUALIZAR TEMPORIZADOR GNN ---
        if self.gnn_start_time:
            elapsed = int(time.time() - self.gnn_start_time)
            self.lbl_gnn_timer.configure(text=f"Tempo: {str(timedelta(seconds=elapsed))}")

        if self.gnn_process and self.gnn_process.poll() is not None:
            self.stop_gnn()
            self.lbl_gnn_status.configure(text="Status: CONCLUÍDO", text_color="#4CAF50")

        # 2. PPO
        if os.path.exists(self.ppo_log):
            try:
                df = pd.read_csv(self.ppo_log)
                if not df.empty:
                    row = df.iloc[-1]
                    steps = int(row['timesteps'])
                    target = int(self.entry_ppo_target.get())
                    self.lbl_ppo_steps.configure(text=f"STEPS: {steps / 1000:.0f}k")
                    self.lbl_ppo_score.configure(text=f"MEAN: {row['ep_rew_mean']:.1f}")
                    self.ppo_bar.set(steps / target)
            except:
                pass

        # --- ATUALIZAR TEMPORIZADOR PPO ---
        if self.ppo_start_time:
            elapsed = int(time.time() - self.ppo_start_time)
            self.lbl_ppo_timer.configure(text=f"Tempo: {str(timedelta(seconds=elapsed))}")

        if self.ppo_process and self.ppo_process.poll() is not None:
            self.stop_ppo()
            self.lbl_ppo_status.configure(text="Status: CONCLUÍDO", text_color="#FFA726")

        self.after(1000, self.update_metrics)


if __name__ == "__main__":
    app = ModernDashboard()
    app.mainloop()