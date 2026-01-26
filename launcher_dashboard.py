import customtkinter as ctk  # A biblioteca moderna
from tkinter import messagebox
import subprocess
import sys
import os
import pandas as pd
import threading
import time

# Configuração do Tema
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"


class ModernDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("🔬 Swarm Robotics Controller - Thesis V2.0")
        self.geometry("1000x650")

        # Caminhos dos Logs
        self.gnn_log = os.path.join(os.path.dirname(__file__), 'results/logs/training_history.csv')
        self.ppo_log = os.path.join(os.path.dirname(__file__), 'results/logs_ppo/training_history_ppo.csv')

        # Processos
        self.gnn_process = None
        self.ppo_process = None

        # --- LAYOUT PRINCIPAL ---
        # Título
        self.lbl_title = ctk.CTkLabel(self, text="SISTEMA DE CONTROLO HÍBRIDO", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=20)

        # Container para as duas colunas
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # === COLUNA ESQUERDA: GNN ===
        self.frame_gnn = ctk.CTkFrame(self.main_frame)
        self.frame_gnn.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_gnn_ui()

        # === COLUNA DIREITA: PPO ===
        self.frame_ppo = ctk.CTkFrame(self.main_frame)
        self.frame_ppo.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.setup_ppo_ui()

        # Rodapé
        self.footer = ctk.CTkLabel(self, text="Developed for MSc Thesis • 2025", text_color="gray")
        self.footer.pack(side="bottom", pady=10)

        # Loop de atualização (Monitorização)
        self.update_metrics()

    def setup_gnn_ui(self):
        # Cabeçalho
        ctk.CTkLabel(self.frame_gnn, text="🧬 Algoritmo Genético (GNN)", font=("Roboto", 18, "bold"),
                     text_color="#4CAF50").pack(pady=15)

        # Inputs de Configuração
        input_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Target Gerações:").pack(side="left", padx=5)
        self.entry_gnn_target = ctk.CTkEntry(input_frame, width=60)
        self.entry_gnn_target.insert(0, "100")
        self.entry_gnn_target.pack(side="left")

        # Métricas Grandes
        self.lbl_gnn_status = ctk.CTkLabel(self.frame_gnn, text="Status: PARADO", text_color="#FF5555",
                                           font=("Consolas", 12))
        self.lbl_gnn_status.pack(pady=5)

        metrics_frame = ctk.CTkFrame(self.frame_gnn, fg_color="#2b2b2b")
        metrics_frame.pack(fill="x", padx=20, pady=10)

        self.lbl_gnn_gen = ctk.CTkLabel(metrics_frame, text="GEN: 0", font=("Consolas", 20, "bold"))
        self.lbl_gnn_gen.pack(pady=5)

        self.lbl_gnn_best = ctk.CTkLabel(metrics_frame, text="BEST: ---", font=("Consolas", 16), text_color="#4CAF50")
        self.lbl_gnn_best.pack(pady=2)

        # Barra de Progresso
        self.gnn_bar = ctk.CTkProgressBar(self.frame_gnn, progress_color="#4CAF50")
        self.gnn_bar.set(0)
        self.gnn_bar.pack(fill="x", padx=20, pady=15)

        # Botões de Controlo
        btn_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self.btn_gnn_start = ctk.CTkButton(btn_frame, text="▶ Iniciar", command=self.start_gnn, fg_color="#4CAF50",
                                           hover_color="#388E3C")
        self.btn_gnn_start.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_gnn_stop = ctk.CTkButton(btn_frame, text="⏹ Parar", command=self.stop_gnn, fg_color="#F44336",
                                          hover_color="#D32F2F", state="disabled")
        self.btn_gnn_stop.pack(side="left", fill="x", expand=True, padx=5)

        # Botões Extra
        ctk.CTkButton(self.frame_gnn, text="📊 Ver Gráfico GNN", command=lambda: self.plot("gnn"), fg_color="#555",
                      hover_color="#666").pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.frame_gnn, text="🎥 Visualizar Simulação", command=self.viz_gnn, fg_color="#1F6AA5",
                      hover_color="#144870").pack(fill="x", padx=20, pady=5)

    def setup_ppo_ui(self):
        # Cabeçalho
        ctk.CTkLabel(self.frame_ppo, text="🤖 Reinforcement Learning (PPO)", font=("Roboto", 18, "bold"),
                     text_color="#FFA726").pack(pady=15)

        # Inputs de Configuração
        input_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        input_frame.pack(pady=5)
        ctk.CTkLabel(input_frame, text="Target Timesteps:").pack(side="left", padx=5)
        self.entry_ppo_target = ctk.CTkEntry(input_frame, width=80)
        self.entry_ppo_target.insert(0, "500000")
        self.entry_ppo_target.pack(side="left")

        # Métricas Grandes
        self.lbl_ppo_status = ctk.CTkLabel(self.frame_ppo, text="Status: PARADO", text_color="#FF5555",
                                           font=("Consolas", 12))
        self.lbl_ppo_status.pack(pady=5)

        metrics_frame = ctk.CTkFrame(self.frame_ppo, fg_color="#2b2b2b")
        metrics_frame.pack(fill="x", padx=20, pady=10)

        self.lbl_ppo_steps = ctk.CTkLabel(metrics_frame, text="STEPS: 0k", font=("Consolas", 20, "bold"))
        self.lbl_ppo_steps.pack(pady=5)

        self.lbl_ppo_score = ctk.CTkLabel(metrics_frame, text="MEAN: ---", font=("Consolas", 16), text_color="#FFA726")
        self.lbl_ppo_score.pack(pady=2)

        # Barra de Progresso
        self.ppo_bar = ctk.CTkProgressBar(self.frame_ppo, progress_color="#FFA726")
        self.ppo_bar.set(0)
        self.ppo_bar.pack(fill="x", padx=20, pady=15)

        # Botões de Controlo
        btn_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self.btn_ppo_start = ctk.CTkButton(btn_frame, text="▶ Iniciar", command=self.start_ppo, fg_color="#FFA726",
                                           hover_color="#F57C00", text_color="black")
        self.btn_ppo_start.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_ppo_stop = ctk.CTkButton(btn_frame, text="⏹ Parar", command=self.stop_ppo, fg_color="#F44336",
                                          hover_color="#D32F2F", state="disabled")
        self.btn_ppo_stop.pack(side="left", fill="x", expand=True, padx=5)

        # Botões Extra
        ctk.CTkButton(self.frame_ppo, text="📊 Ver Gráfico PPO", command=lambda: self.plot("ppo"), fg_color="#555",
                      hover_color="#666").pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.frame_ppo, text="🎥 Visualizar Simulação", command=self.viz_ppo, fg_color="#1F6AA5",
                      hover_color="#144870").pack(fill="x", padx=20, pady=5)

    # --- LÓGICA DE PROCESSO ---
    def run_script(self, path, args=[]):
        python_exe = sys.executable
        full_path = os.path.join(os.path.dirname(__file__), path)
        return subprocess.Popen([python_exe, full_path] + args)

    def start_gnn(self):
        if self.gnn_process: return
        if os.path.exists(self.gnn_log): os.remove(self.gnn_log)  # Limpar dados velhos

        # AQUI PODERIAS PASSAR O ARGUMENTO DE GERAÇÕES SE O TEU SCRIPT SUPORTASSE ARGS
        # Por agora vamos lançar normal
        self.gnn_process = self.run_script("src/training/evo_trainer.py")

        self.btn_gnn_start.configure(state="disabled")
        self.btn_gnn_stop.configure(state="normal")
        self.lbl_gnn_status.configure(text="Status: A CORRER", text_color="#4CAF50")

    def stop_gnn(self):
        if self.gnn_process:
            self.gnn_process.terminate()
            self.gnn_process = None

        self.btn_gnn_start.configure(state="normal")
        self.btn_gnn_stop.configure(state="disabled")
        self.lbl_gnn_status.configure(text="Status: INTERROMPIDO", text_color="#FF5555")

    def start_ppo(self):
        if self.ppo_process: return
        if os.path.exists(self.ppo_log): os.remove(self.ppo_log)

        self.ppo_process = self.run_script("src/training/train_ppo.py")

        self.btn_ppo_start.configure(state="disabled")
        self.btn_ppo_stop.configure(state="normal")
        self.lbl_ppo_status.configure(text="Status: A CORRER", text_color="#FFA726")

    def stop_ppo(self):
        if self.ppo_process:
            self.ppo_process.terminate()
            self.ppo_process = None

        self.btn_ppo_start.configure(state="normal")
        self.btn_ppo_stop.configure(state="disabled")
        self.lbl_ppo_status.configure(text="Status: INTERROMPIDO", text_color="#FF5555")

    def viz_gnn(self):
        self.run_script("visualize.py", ["--model", "results/models/gnn_gen_100.pth"])

    def viz_ppo(self):
        self.run_script("visualize_ppo.py")

    def plot(self, mode):
        # Chama o novo script de plot com argumentos
        self.run_script("plot_results.py", ["--mode", mode])

    # --- MONITORIZAÇÃO EM TEMPO REAL ---
    def update_metrics(self):
        # 1. Atualizar GNN
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
            except:
                pass

        # Verificar se GNN acabou sozinho
        if self.gnn_process and self.gnn_process.poll() is not None:
            self.stop_gnn()
            self.lbl_gnn_status.configure(text="Status: CONCLUÍDO", text_color="#4CAF50")

        # 2. Atualizar PPO
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

        # Verificar se PPO acabou sozinho
        if self.ppo_process and self.ppo_process.poll() is not None:
            self.stop_ppo()
            self.lbl_ppo_status.configure(text="Status: CONCLUÍDO", text_color="#FFA726")

        # Chama a si próprio daqui a 1000ms (1 segundo)
        self.after(1000, self.update_metrics)


if __name__ == "__main__":
    app = ModernDashboard()
    app.mainloop()