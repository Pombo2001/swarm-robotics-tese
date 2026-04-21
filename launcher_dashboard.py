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


class ModernDashboardV6Pro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔬 Swarm Robotics Controller - Master Edition")
        self.geometry("1400x750")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, 'configs', 'foraging.yaml')
        self.mode = "3D"

        self.gnn_process = None
        self.ppo_process = None
        self.sac_process = None

        self.gnn_start_time = None
        self.ppo_start_time = None
        self.sac_start_time = None

        self.frame_gnn = self.lbl_gnn_status = self.lbl_gnn_timer = self.metrics_gnn = self.lbl_gnn_best = None
        self.frame_ppo = self.lbl_ppo_status = self.lbl_ppo_timer = self.metrics_ppo = self.lbl_ppo_score = None
        self.frame_sac = self.lbl_sac_status = self.lbl_sac_timer = self.metrics_sac = self.lbl_sac_score = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.lbl_title = ctk.CTkLabel(self.sidebar_frame, text="SWARM\nCONTROLLER", font=("Roboto", 28, "bold"),
                                      text_color="#E0E0E0")
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(30, 10))

        self.lbl_mode_status = ctk.CTkLabel(self.sidebar_frame, text="ARENA DE DRONES (3D)", text_color="#F06292",
                                            font=("Consolas", 14, "bold"))
        self.lbl_mode_status.grid(row=2, column=0, pady=(0, 20))

        # Cenários
        self.scenario_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#311b3b", corner_radius=10)
        self.scenario_frame.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(self.scenario_frame, text="📚 CENÁRIOS DE LITERATURA", font=("Roboto", 12, "bold"),
                     text_color="#CE93D8").pack(pady=(10, 0))

        self.combo_scenario = ctk.CTkOptionMenu(self.scenario_frame, values=[
            "Nenhum (Modo Sandbox)",
            "Beco Sem Saída (Muro U)",
            "Gargalo (Porta Estreita)",
            "Quatro Salas (Labirinto)"
        ], fg_color="#6A1B9A", button_color="#4A148C")
        self.combo_scenario.pack(padx=15, pady=10, fill="x")

        # Config Sandbox
        self.config_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1b3a20", corner_radius=10)
        self.config_frame.grid(row=4, column=0, padx=15, pady=10, sticky="ew")

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

        self.btn_plot_thesis = ctk.CTkButton(self.sidebar_frame, text="📊 Gerar Gráfico de Tese",
                                             command=self.plot_thesis, fg_color="#8E24AA", hover_color="#6A1B9A",
                                             font=("Roboto", 14, "bold"), height=40)
        self.btn_plot_thesis.grid(row=6, column=0, padx=20, pady=20, sticky="sew")

        # === MAIN AREA ===
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure((0, 1, 2), weight=1)

        self.master_frame = ctk.CTkFrame(self.main_area, fg_color="#1e1e1e", border_width=1, border_color="#D32F2F",
                                         corner_radius=10)
        self.master_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(self.master_frame, text="⏱️ TREINO MÚLTIPLO SIMULTÂNEO (BATALHA DE ALGORITMOS)",
                     font=("Roboto", 16, "bold"), text_color="#E0E0E0").pack(pady=(15, 5))

        time_panel = ctk.CTkFrame(self.master_frame, fg_color="transparent")
        time_panel.pack(pady=(0, 15))

        ctk.CTkLabel(time_panel, text="Tempo Máx (Minutos):", font=("Roboto", 14)).pack(side="left", padx=10)
        self.entry_master_time = ctk.CTkEntry(time_panel, width=80, font=("Roboto", 14))
        self.entry_master_time.insert(0, "480")
        self.entry_master_time.pack(side="left", padx=10)

        self.btn_start_all = ctk.CTkButton(time_panel, text="🚀 INICIAR OS 3 ALGORITMOS", command=self.start_all,
                                           fg_color="#D32F2F", hover_color="#B71C1C", font=("Roboto", 14, "bold"),
                                           height=35)
        self.btn_start_all.pack(side="left", padx=20)

        self._create_algo_frame("gnn", "🧬 GNN (Evolutivo)", "#4CAF50", self.start_gnn, self.stop_gnn, self.viz_gnn, 0)
        self._create_algo_frame("ppo", "🤖 PPO (Actor-Critic)", "#2196F3", self.start_ppo, self.stop_ppo, self.viz_ppo, 1)
        self._create_algo_frame("sac", "🔥 SAC (Soft Actor-Critic)", "#FF9800", self.start_sac, self.stop_sac,
                                self.viz_sac, 2, text_color="black")

        self.update_metrics()
        self.load_current_config()

    def _create_algo_frame(self, name, title, color, start_cmd, stop_cmd, viz_cmd, col, text_color=None):
        frame = ctk.CTkFrame(self.main_area, corner_radius=10)
        frame.grid(row=1, column=col, sticky="nsew", padx=5)
        ctk.CTkLabel(frame, text=title, font=("Roboto", 20, "bold"), text_color=color).pack(pady=(20, 10))

        status_label = ctk.CTkLabel(frame, text="Status: PARADO", font=("Consolas", 14))
        status_label.pack(pady=5)
        timer_label = ctk.CTkLabel(frame, text="Tempo: 00:00:00", font=("Consolas", 14))
        timer_label.pack()

        metrics_frame = ctk.CTkFrame(frame, fg_color="#2b2b2b", corner_radius=8)
        metrics_frame.pack(fill="x", padx=20, pady=20)
        metric_label = ctk.CTkLabel(metrics_frame, text="REWARD: ---", font=("Consolas", 18, "bold"), text_color=color)
        metric_label.pack(pady=15)

        ctk.CTkButton(frame, text=f"▶ Treinar Só {name.upper()}", command=start_cmd, fg_color=color,
                      text_color=text_color, height=35).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(frame, text="⏹ Parar", command=stop_cmd, fg_color="#F44336", height=35).pack(pady=5, padx=20,
                                                                                                   fill="x")
        ctk.CTkButton(frame, text="🎥 Visualizar", command=viz_cmd, fg_color="#1F6AA5", height=35).pack(pady=20,
                                                                                                        padx=20,
                                                                                                        fill="x")

        setattr(self, f"frame_{name}", frame)
        setattr(self, f"lbl_{name}_status", status_label)
        setattr(self, f"lbl_{name}_timer", timer_label)
        setattr(self, f"metrics_{name}", metrics_frame)
        if name == "gnn":
            setattr(self, f"lbl_{name}_best", metric_label)
        else:
            setattr(self, f"lbl_{name}_score", metric_label)

    def get_paths(self):
        return {
            "gnn_log": os.path.join(self.base_dir, 'results/logs/gnn_3d_training.csv'),
            "ppo_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_ppo_3d.csv'),
            "sac_log": os.path.join(self.base_dir, 'results/logs_ppo/training_history_sac_3d.csv'),

            "gnn_script": "src/training/evo_trainer_3d.py",
            "ppo_script": "src/training/train_ppo_3d.py",
            "sac_script": "src/training/train_sac_3d.py",

            "viz_gnn": "visualize_3d.py",
            "viz_ppo": "visualize_ppo_3d.py",
            "viz_sac": "visualize_sac_3d.py",

            "plot_script": "plot_final_thesis_3d.py"
        }

    def run_script(self, script, args=None):
        if args is None:
            args = []
        full_path = os.path.join(self.base_dir, script)
        return subprocess.Popen([sys.executable, full_path] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def start_all(self):
        self.save_current_config()
        paths = self.get_paths()
        target = self.entry_master_time.get()

        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        if os.path.exists(paths["sac_log"]): os.remove(paths["sac_log"])

        self.gnn_process = self.run_script(paths["gnn_script"], ["--time_limit", target])
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

        self.ppo_process = self.run_script(paths["ppo_script"], ["--time_limit", target])
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#2196F3")

        self.sac_process = self.run_script(paths["sac_script"], ["--time_limit", target])
        self.sac_start_time = time.time()
        self.lbl_sac_status.configure(text="Status: A TREINAR...", text_color="#FF9800")

    def start_gnn(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        self.gnn_process = self.run_script(paths["gnn_script"], ["--time_limit", self.entry_master_time.get()])
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

    def start_ppo(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        self.ppo_process = self.run_script(paths["ppo_script"], ["--time_limit", self.entry_master_time.get()])
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#2196F3")

    def start_sac(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["sac_log"]): os.remove(paths["sac_log"])
        self.sac_process = self.run_script(paths["sac_script"], ["--time_limit", self.entry_master_time.get()])
        self.sac_start_time = time.time()
        self.lbl_sac_status.configure(text="Status: A TREINAR...", text_color="#FF9800")

    def stop_gnn(self):
        if self.gnn_process: self.gnn_process.terminate(); self.gnn_process = None
        self.gnn_start_time = None
        self.lbl_gnn_status.configure(text="Status: PARADO", text_color="white")

    def stop_ppo(self):
        if self.ppo_process: self.ppo_process.terminate(); self.ppo_process = None
        self.ppo_start_time = None
        self.lbl_ppo_status.configure(text="Status: PARADO", text_color="white")

    def stop_sac(self):
        if self.sac_process: self.sac_process.terminate(); self.sac_process = None
        self.sac_start_time = None
        self.lbl_sac_status.configure(text="Status: PARADO", text_color="white")

    def viz_gnn(self):
        self.save_current_config()
        self.run_script(self.get_paths()["viz_gnn"])

    def viz_ppo(self):
        self.save_current_config()
        self.run_script(self.get_paths()["viz_ppo"])

    def viz_sac(self):
        self.save_current_config()
        self.run_script(self.get_paths()["viz_sac"])

    def plot_thesis(self):
        self.run_script(self.get_paths()["plot_script"])

    def update_metrics(self):
        paths = self.get_paths()

        if os.path.exists(paths["gnn_log"]):
            try:
                df = pd.read_csv(paths["gnn_log"]).dropna()
                if not df.empty: self.lbl_gnn_best.configure(text=f"FITNESS: {df.iloc[-1]['best_fitness']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                print(f"Error reading GNN log: {e}")

        if os.path.exists(paths["ppo_log"]):
            try:
                df = pd.read_csv(paths["ppo_log"]).dropna()
                if not df.empty: self.lbl_ppo_score.configure(text=f"REWARD: {df.iloc[-1]['ep_rew_mean']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                print(f"Error reading PPO log: {e}")

        if os.path.exists(paths["sac_log"]):
            try:
                df = pd.read_csv(paths["sac_log"]).dropna()
                if not df.empty: self.lbl_sac_score.configure(text=f"REWARD: {df.iloc[-1]['ep_rew_mean']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                print(f"Error reading SAC log: {e}")

        if self.gnn_start_time:
            self.lbl_gnn_timer.configure(
                text=f"Tempo: {str(timedelta(seconds=int(time.time() - self.gnn_start_time)))}")
        if self.ppo_start_time:
            self.lbl_ppo_timer.configure(
                text=f"Tempo: {str(timedelta(seconds=int(time.time() - self.ppo_start_time)))}")
        if self.sac_start_time:
            self.lbl_sac_timer.configure(
                text=f"Tempo: {str(timedelta(seconds=int(time.time() - self.sac_start_time)))}")

        self.after(1000, self.update_metrics)

    def load_current_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.entry_num_drones.delete(0, ctk.END)
                self.entry_num_drones.insert(0, str(config['environment'].get('num_agents', 20)))
                self.entry_num_obs.delete(0, ctk.END)
                self.entry_num_obs.insert(0, str(config['environment'].get('num_obstacles', 10)))
                self.entry_arena_radius.delete(0, ctk.END)
                self.entry_arena_radius.insert(0, str(config['environment'].get('arena_radius', 15.0)))

                scenario = config['environment'].get('classic_scenario', 'none')
                if scenario == 'u_wall':
                    self.combo_scenario.set("Beco Sem Saída (Muro U)")
                elif scenario == 'bottleneck':
                    self.combo_scenario.set("Gargalo (Porta Estreita)")
                elif scenario == 'four_rooms':
                    self.combo_scenario.set("Quatro Salas (Labirinto)")
                else:
                    self.combo_scenario.set("Nenhum (Modo Sandbox)")
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error loading config: {e}")

    def save_current_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            config['environment']['num_agents'] = int(self.entry_num_drones.get())
            config['environment']['num_obstacles'] = int(self.entry_num_obs.get())
            config['environment']['arena_radius'] = float(self.entry_arena_radius.get())

            combo_val = self.combo_scenario.get()
            if combo_val == "Beco Sem Saída (Muro U)":
                config['environment']['classic_scenario'] = "u_wall"
            elif combo_val == "Gargalo (Porta Estreita)":
                config['environment']['classic_scenario'] = "bottleneck"
            elif combo_val == "Quatro Salas (Labirinto)":
                config['environment']['classic_scenario'] = "four_rooms"
            else:
                config['environment']['classic_scenario'] = "none"

            with open(self.config_path, 'w') as f:
                yaml.dump(config, f)
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            print(f"Error saving config: {e}")


if __name__ == "__main__":
    app = ModernDashboardV6Pro()
    app.mainloop()