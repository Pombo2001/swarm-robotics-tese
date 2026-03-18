import customtkinter as ctk
import subprocess
import sys
import os
import pandas as pd
import time
import yaml
from datetime import timedelta

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ModernDashboardV6_Pro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔬 Swarm Robotics Controller - Pro Edition")
        # Formato Panorâmico: Mais largo, muito mais baixo (cabe em qualquer ecrã)
        self.geometry("1250x700")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, 'configs', 'foraging.yaml')
        self.mode = "2D"

        self.gnn_process = None
        self.ppo_process = None
        self.gnn_start_time = None
        self.ppo_start_time = None

        # ==========================================
        # ESTRUTURA PRINCIPAL (2 COLUNAS)
        # ==========================================
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- SIDEBAR (Esquerda): Configurações e Controlos Globais ---
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)  # Empurra o botão de gráficos para o fundo

        self.lbl_title = ctk.CTkLabel(self.sidebar_frame, text="SWARM\nCONTROLLER", font=("Roboto", 28, "bold"),
                                      text_color="#E0E0E0")
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(30, 10))

        self.mode_selector = ctk.CTkSegmentedButton(self.sidebar_frame, values=["2D", "3D"], command=self.change_mode,
                                                    font=("Roboto", 14, "bold"))
        self.mode_selector.set("2D")
        self.mode_selector.grid(row=1, column=0, padx=20, pady=10,
                                sticky="ew")  # CORRIGIDO: sticky="ew" em vez de fill="x"

        self.lbl_mode_status = ctk.CTkLabel(self.sidebar_frame, text="ARENA TERRESTRE (2D)", text_color="#4FC3F7",
                                            font=("Consolas", 12, "bold"))
        self.lbl_mode_status.grid(row=2, column=0, pady=(0, 20))

        # Painel Sandbox (Dentro da Sidebar)
        self.config_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1b3a20", corner_radius=10)
        self.config_frame.grid(row=3, column=0, padx=15, pady=10, sticky="ew")  # CORRIGIDO

        ctk.CTkLabel(self.config_frame, text="⚙️ CONFIGURAÇÃO SANDBOX", font=("Roboto", 14, "bold"),
                     text_color="#A5D6A7").pack(pady=(10, 5))

        cfg_grid = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        cfg_grid.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(cfg_grid, text="Drones:", font=("Roboto", 12)).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_num_drones = ctk.CTkEntry(cfg_grid, width=60, height=25)
        self.entry_num_drones.grid(row=0, column=1, sticky="e", pady=5)

        ctk.CTkLabel(cfg_grid, text="Obstáculos:", font=("Roboto", 12)).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_num_obs = ctk.CTkEntry(cfg_grid, width=60, height=25)
        self.entry_num_obs.grid(row=1, column=1, sticky="e", pady=5)

        ctk.CTkLabel(cfg_grid, text="Raio Arena:", font=("Roboto", 12)).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_arena_radius = ctk.CTkEntry(cfg_grid, width=60, height=25)
        self.entry_arena_radius.grid(row=2, column=1, sticky="e", pady=5)

        self.switch_moving_obs = ctk.CTkSwitch(self.config_frame, text="Obstáculos Móveis", progress_color="#4CAF50",
                                               font=("Roboto", 12))
        self.switch_moving_obs.pack(pady=(5, 5), padx=20, anchor="w")

        self.switch_moving_nest = ctk.CTkSwitch(self.config_frame, text="Ninho Móvel", progress_color="#FFA726",
                                                font=("Roboto", 12))
        self.switch_moving_nest.pack(pady=(0, 15), padx=20, anchor="w")

        # Botão Gráficos (Fica sempre preso ao fundo da Sidebar)
        self.btn_plot_thesis = ctk.CTkButton(self.sidebar_frame, text="📊 Gerar Gráficos", command=self.plot_thesis,
                                             fg_color="#8E24AA", hover_color="#6A1B9A", font=("Roboto", 14, "bold"),
                                             height=40)
        self.btn_plot_thesis.grid(row=5, column=0, padx=20, pady=20, sticky="sew")  # CORRIGIDO

        # --- MAIN AREA (Direita): Treino e Monitorização ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure((0, 1), weight=1)

        # Painel Mestre Simultâneo (Topo)
        self.master_frame = ctk.CTkFrame(self.main_area, fg_color="#1e1e1e", border_width=1, border_color="#D32F2F",
                                         corner_radius=10)
        self.master_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        self.master_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(self.master_frame, text="⏱️ TREINO JUSTO SIMULTÂNEO (ORÇAMENTO DE TEMPO)",
                     font=("Roboto", 16, "bold"), text_color="#E0E0E0").grid(row=0, column=0, columnspan=3,
                                                                             pady=(15, 5))

        time_panel = ctk.CTkFrame(self.master_frame, fg_color="transparent")
        time_panel.grid(row=1, column=0, columnspan=3, pady=(0, 15))

        ctk.CTkLabel(time_panel, text="Tempo Máx (Min):", font=("Roboto", 14)).pack(side="left", padx=10)
        self.entry_master_time = ctk.CTkEntry(time_panel, width=80, font=("Roboto", 14))
        self.entry_master_time.insert(0, "480")
        self.entry_master_time.pack(side="left", padx=10)

        self.btn_start_both = ctk.CTkButton(time_panel, text="🚀 INICIAR GNN + PPO", command=self.start_both,
                                            fg_color="#D32F2F", hover_color="#B71C1C", font=("Roboto", 14, "bold"),
                                            height=35)
        self.btn_start_both.pack(side="left", padx=20)

        # Painéis Individuais (Lado a Lado)
        self.setup_gnn_ui()
        self.setup_ppo_ui()

        self.update_metrics()
        self.load_current_config()

    def load_current_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.entry_num_drones.delete(0, ctk.END);
                self.entry_num_drones.insert(0, str(config['environment'].get('num_agents', 20)))
                self.entry_num_obs.delete(0, ctk.END);
                self.entry_num_obs.insert(0, str(config['environment'].get('num_obstacles', 10)))
                self.entry_arena_radius.delete(0, ctk.END);
                self.entry_arena_radius.insert(0, str(config['environment'].get('arena_radius', 2.0)))

                if config['environment'].get('dynamic_obstacles', False):
                    self.switch_moving_obs.select()
                else:
                    self.switch_moving_obs.deselect()
                if config['environment'].get('dynamic_nest', False):
                    self.switch_moving_nest.select()
                else:
                    self.switch_moving_nest.deselect()
        except Exception as e:
            print("Erro a ler o YAML:", e)

    def save_current_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            config['environment']['num_agents'] = int(self.entry_num_drones.get())
            config['environment']['num_obstacles'] = int(self.entry_num_obs.get())
            config['environment']['arena_radius'] = float(self.entry_arena_radius.get())
            config['environment']['dynamic_obstacles'] = bool(self.switch_moving_obs.get())
            config['environment']['dynamic_nest'] = bool(self.switch_moving_nest.get())
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f)
            os.chmod(self.config_path, 0o666)
        except Exception as e:
            print("Erro a guardar YAML:", e)

    def change_mode(self, value):
        self.mode = value
        if value == "2D":
            self.lbl_mode_status.configure(text="ARENA TERRESTRE (2D)", text_color="#4FC3F7")
            self.lbl_gnn_target.configure(text="Alvo (Gens):")
            self.lbl_ppo_target.configure(text="Alvo (Steps):")
        else:
            self.lbl_mode_status.configure(text="ARENA DE DRONES (3D)", text_color="#F06292")
            self.lbl_gnn_target.configure(text="Alvo (Mins):")
            self.lbl_ppo_target.configure(text="Alvo (Mins):")

    def get_paths(self):
        if self.mode == "2D":
            return {"gnn_log": os.path.join(self.base_dir, 'results/logs/gnn_fair_training.csv'),
                    "ppo_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo.csv'),
                    "gnn_script": "src/training/evo_trainer.py", "ppo_script": "src/training/train_ppo.py",
                    "viz_gnn": "visualize_continuous.py", "viz_ppo": "visualize_ppo.py",
                    "plot_script": "plot_final_thesis.py"}
        else:
            return {"gnn_log": os.path.join(self.base_dir, 'results/logs/gnn_3d_training.csv'),
                    "ppo_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo_3d.csv'),
                    "gnn_script": "src/training/evo_trainer_3d.py", "ppo_script": "src/training/train_ppo_3d.py",
                    "viz_gnn": "visualize_3d.py", "viz_ppo": "visualize_ppo_3d.py",
                    "plot_script": "plot_final_thesis_3d.py"}

    def setup_gnn_ui(self):
        self.frame_gnn = ctk.CTkFrame(self.main_area, corner_radius=10)
        self.frame_gnn.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(self.frame_gnn, text="🧬 Evolutivo (GNN)", font=("Roboto", 20, "bold"), text_color="#4CAF50").pack(
            pady=(20, 10))

        inp_frame = ctk.CTkFrame(self.frame_gnn, fg_color="transparent")
        inp_frame.pack(pady=10)
        self.lbl_gnn_target = ctk.CTkLabel(inp_frame, text="Alvo (Gens):")
        self.lbl_gnn_target.pack(side="left", padx=5)
        self.entry_gnn_target = ctk.CTkEntry(inp_frame, width=80)
        self.entry_gnn_target.insert(0, "50")
        self.entry_gnn_target.pack(side="left")

        self.lbl_gnn_status = ctk.CTkLabel(self.frame_gnn, text="Status: PARADO", font=("Consolas", 14))
        self.lbl_gnn_status.pack(pady=5)
        self.lbl_gnn_timer = ctk.CTkLabel(self.frame_gnn, text="Tempo: 00:00:00", font=("Consolas", 14))
        self.lbl_gnn_timer.pack()

        self.metrics_gnn = ctk.CTkFrame(self.frame_gnn, fg_color="#2b2b2b", corner_radius=8)
        self.metrics_gnn.pack(fill="x", padx=30, pady=20)
        self.lbl_gnn_best = ctk.CTkLabel(self.metrics_gnn, text="BEST FIT: ---", font=("Consolas", 20, "bold"),
                                         text_color="#4CAF50")
        self.lbl_gnn_best.pack(pady=15)

        self.btn_gnn_start = ctk.CTkButton(self.frame_gnn, text="▶ Iniciar GNN", command=self.start_gnn,
                                           fg_color="#4CAF50", height=35)
        self.btn_gnn_start.pack(pady=5, padx=40, fill="x")
        self.btn_gnn_stop = ctk.CTkButton(self.frame_gnn, text="⏹ Parar", command=self.stop_gnn, fg_color="#F44336",
                                          height=35)
        self.btn_gnn_stop.pack(pady=5, padx=40, fill="x")
        self.btn_gnn_viz = ctk.CTkButton(self.frame_gnn, text="🎥 Visualizar Melhor", command=self.viz_gnn,
                                         fg_color="#1F6AA5", height=35)
        self.btn_gnn_viz.pack(pady=20, padx=40, fill="x")

    def setup_ppo_ui(self):
        self.frame_ppo = ctk.CTkFrame(self.main_area, corner_radius=10)
        self.frame_ppo.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(self.frame_ppo, text="🤖 Por Reforço (PPO)", font=("Roboto", 20, "bold"),
                     text_color="#FFA726").pack(pady=(20, 10))

        inp_frame = ctk.CTkFrame(self.frame_ppo, fg_color="transparent")
        inp_frame.pack(pady=10)
        self.lbl_ppo_target = ctk.CTkLabel(inp_frame, text="Alvo (Steps):")
        self.lbl_ppo_target.pack(side="left", padx=5)
        self.entry_ppo_target = ctk.CTkEntry(inp_frame, width=80)
        self.entry_ppo_target.insert(0, "500000")
        self.entry_ppo_target.pack(side="left")

        self.lbl_ppo_status = ctk.CTkLabel(self.frame_ppo, text="Status: PARADO", font=("Consolas", 14))
        self.lbl_ppo_status.pack(pady=5)
        self.lbl_ppo_timer = ctk.CTkLabel(self.frame_ppo, text="Tempo: 00:00:00", font=("Consolas", 14))
        self.lbl_ppo_timer.pack()

        self.metrics_ppo = ctk.CTkFrame(self.frame_ppo, fg_color="#2b2b2b", corner_radius=8)
        self.metrics_ppo.pack(fill="x", padx=30, pady=20)
        self.lbl_ppo_score = ctk.CTkLabel(self.metrics_ppo, text="MEAN REW: ---", font=("Consolas", 20, "bold"),
                                          text_color="#FFA726")
        self.lbl_ppo_score.pack(pady=15)

        self.btn_ppo_start = ctk.CTkButton(self.frame_ppo, text="▶ Iniciar PPO", command=self.start_ppo,
                                           fg_color="#FFA726", text_color="black", height=35)
        self.btn_ppo_start.pack(pady=5, padx=40, fill="x")
        self.btn_ppo_stop = ctk.CTkButton(self.frame_ppo, text="⏹ Parar", command=self.stop_ppo, fg_color="#F44336",
                                          height=35)
        self.btn_ppo_stop.pack(pady=5, padx=40, fill="x")
        self.btn_ppo_viz = ctk.CTkButton(self.frame_ppo, text="🎥 Visualizar Melhor", command=self.viz_ppo,
                                         fg_color="#1F6AA5", height=35)
        self.btn_ppo_viz.pack(pady=20, padx=40, fill="x")

    def run_script(self, script, args=[]):
        full_path = os.path.join(self.base_dir, script)
        return subprocess.Popen([sys.executable, full_path] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def start_both(self):
        self.save_current_config()
        paths = self.get_paths()
        target_minutes = self.entry_master_time.get()
        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])

        self.gnn_process = self.run_script(paths["gnn_script"], ["--time_limit", target_minutes])
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

        self.ppo_process = self.run_script(paths["ppo_script"], ["--time_limit", target_minutes])
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#FFA726")

    def start_gnn(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        target = self.entry_gnn_target.get()
        arg_type = "--time_limit" if self.mode == "3D" else "--generations"
        self.gnn_process = self.run_script(paths["gnn_script"], [arg_type, target])
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

    def start_ppo(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        target = self.entry_ppo_target.get()
        arg_type = "--time_limit" if self.mode == "3D" else "--timesteps"
        self.ppo_process = self.run_script(paths["ppo_script"], [arg_type, target])
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#FFA726")

    def stop_gnn(self):
        if self.gnn_process: self.gnn_process.terminate(); self.gnn_process = None
        self.gnn_start_time = None
        self.lbl_gnn_status.configure(text="Status: PARADO", text_color="white")

    def stop_ppo(self):
        if self.ppo_process: self.ppo_process.terminate(); self.ppo_process = None
        self.ppo_start_time = None
        self.lbl_ppo_status.configure(text="Status: PARADO", text_color="white")

    def viz_gnn(self):
        self.save_current_config()
        self.run_script(self.get_paths()["viz_gnn"])

    def viz_ppo(self):
        self.save_current_config()
        self.run_script(self.get_paths()["viz_ppo"])

    def plot_thesis(self):
        self.run_script(self.get_paths()["plot_script"])

    def update_metrics(self):
        paths = self.get_paths()
        if os.path.exists(paths["gnn_log"]):
            try:
                df = pd.read_csv(paths["gnn_log"]).apply(pd.to_numeric, errors='coerce').dropna()
                if not df.empty: self.lbl_gnn_best.configure(text=f"BEST FIT: {df.iloc[-1]['best_fitness']:.1f}")
            except:
                pass
        if os.path.exists(paths["ppo_log"]):
            try:
                df = pd.read_csv(paths["ppo_log"]).apply(pd.to_numeric, errors='coerce').dropna()
                if not df.empty: self.lbl_ppo_score.configure(text=f"MEAN REW: {df.iloc[-1]['ep_rew_mean']:.1f}")
            except:
                pass

        if self.gnn_start_time:
            elapsed = int(time.time() - self.gnn_start_time)
            self.lbl_gnn_timer.configure(text=f"Tempo: {str(timedelta(seconds=elapsed))}")
        if self.ppo_start_time:
            elapsed = int(time.time() - self.ppo_start_time)
            self.lbl_ppo_timer.configure(text=f"Tempo: {str(timedelta(seconds=elapsed))}")

        self.after(1000, self.update_metrics)


if __name__ == "__main__":
    app = ModernDashboardV6_Pro()
    app.mainloop()