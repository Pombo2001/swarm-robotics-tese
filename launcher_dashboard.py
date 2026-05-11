import customtkinter as ctk
import subprocess
import sys
import os
import pandas as pd
import time
import yaml
from datetime import timedelta
from functools import partial

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
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.lbl_title = ctk.CTkLabel(self.sidebar_frame, text="SWARM\nCONTROLLER", font=("Roboto", 28, "bold"),
                                      text_color="#E0E0E0")
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(30, 10))

        self.lbl_mode_status = ctk.CTkLabel(self.sidebar_frame, text="ARENA DE DRONES (3D)", text_color="#F06292",
                                            font=("Consolas", 14, "bold"))
        self.lbl_mode_status.grid(row=1, column=0, pady=(0, 20))

        # Cenários
        self.scenario_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#311b3b", corner_radius=10)
        self.scenario_frame.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(self.scenario_frame, text="📚 CENÁRIOS DE LITERATURA", font=("Roboto", 12, "bold"),
                     text_color="#CE93D8").pack(pady=(10, 0))

        self.combo_scenario = ctk.CTkOptionMenu(self.scenario_frame, values=[
            "Nenhum (Modo Sandbox)",
            "Beco Sem Saída (Muro U)",
            "Gargalo (Porta Estreita)",
            "Quatro Salas (Labirinto)",
            "Porta Cooperativa (3 Robôs)",
            "Perceção Cooperativa (Alvo Móvel)"
        ], fg_color="#6A1B9A", button_color="#4A148C")
        self.combo_scenario.pack(padx=15, pady=10, fill="x")

        # Config Sandbox
        self.config_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1b3a20", corner_radius=10)
        self.config_frame.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

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

        # === NOVA SECÇÃO: TREINO NOTURNO ===
        self.night_train_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#4b2c00", corner_radius=10)
        self.night_train_frame.grid(row=4, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(self.night_train_frame, text="🌙 TREINO NOTURNO (TESE)", font=("Roboto", 14, "bold"),
                     text_color="#FFB300").pack(pady=(10, 5))
        night_grid = ctk.CTkFrame(self.night_train_frame, fg_color="transparent")
        night_grid.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(night_grid, text="Horas de Treino (Total):", font=("Roboto", 12)).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_night_hours = ctk.CTkEntry(night_grid, width=60, height=25)
        self.entry_night_hours.insert(0, "8")
        self.entry_night_hours.grid(row=0, column=1, sticky="e", pady=5)

        ctk.CTkLabel(night_grid, text="Nº de Runs/Cenário:", font=("Roboto", 12)).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_night_runs = ctk.CTkEntry(night_grid, width=60, height=25)
        self.entry_night_runs.insert(0, "5")
        self.entry_night_runs.grid(row=1, column=1, sticky="e", pady=5)

        self.lbl_calculated_time = ctk.CTkLabel(self.night_train_frame, text="Ex: ~6.4 min por run", font=("Roboto", 11, "italic"), text_color="#A1A1A1")
        self.lbl_calculated_time.pack(pady=(0, 10))

        self.btn_start_night_train = ctk.CTkButton(self.night_train_frame, text="🚀 Iniciar Rotina de Testes",
                                             command=self.start_night_training, fg_color="#FF8F00", hover_color="#FF6F00",
                                             text_color="black", font=("Roboto", 12, "bold"), height=35)
        self.btn_start_night_train.pack(pady=(5, 15), padx=15, fill="x")

        self.entry_night_hours.bind("<KeyRelease>", self.update_calculated_time)
        self.entry_night_runs.bind("<KeyRelease>", self.update_calculated_time)
        
        self.btn_plot_thesis = ctk.CTkButton(self.sidebar_frame, text="📊 Gerar Gráficos Pós-Treino",
                                             command=self.plot_thesis, fg_color="#8E24AA", hover_color="#6A1B9A",
                                             font=("Roboto", 14, "bold"), height=40)
        self.btn_plot_thesis.grid(row=7, column=0, padx=20, pady=20, sticky="sew")

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

        self._create_algo_frame("gnn", "🧬 GNN (Evolutivo)", "#4CAF50", self.start_gnn, self.stop_gnn, 0)
        self._create_algo_frame("ppo", "🤖 PPO (Actor-Critic)", "#2196F3", self.start_ppo, self.stop_ppo, 1)
        self._create_algo_frame("sac", "🔥 SAC (Soft Actor-Critic)", "#FF9800", self.start_sac, self.stop_sac, 2, text_color="black")

        self.update_metrics()
        self.load_current_config()
        self.update_calculated_time()

    def _create_algo_frame(self, name, title, color, start_cmd, stop_cmd, col, text_color=None):
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
        
        ctk.CTkButton(frame, text="🎥 Visualizar com Gráficos", command=partial(self.visualize_algo, name), fg_color="#1F6AA5", height=35).pack(pady=20,
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

            "gnn_visualizer": "visualization/visualize_3d.py",
            "ppo_visualizer": "visualization/visualize_ppo_3d.py",
            "sac_visualizer": "visualization/visualize_sac_3d.py",
            
            "metrics_plotter": "visualization/plot_live_metrics.py",

            "plot_script": "plot_final_thesis_3d.py",
            "run_experiments": "run_experiments.py"
        }

    def run_script(self, script, args=None, keep_console_open=False, new_window=True):
        if args is None:
            args = []
        full_path = os.path.join(self.base_dir, script)
        
        # A flag 'new_window' controla se o script corre numa nova janela ou em background
        if new_window:
            if keep_console_open:
                # Lança uma nova janela de terminal que se mantém aberta (para Ursina)
                cmd = ['cmd', '/c', 'start', 'cmd', '/k', sys.executable, full_path] + args
                return subprocess.Popen(cmd, shell=True)
            else:
                # Lança uma nova janela de terminal que fecha no fim (para gráficos Matplotlib)
                cmd = ['cmd', '/c', 'start', sys.executable, full_path] + args
                return subprocess.Popen(cmd, shell=True)
        else:
            # Corre o script em background (para treino)
            return subprocess.Popen([sys.executable, full_path] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def update_calculated_time(self, event=None):
        try:
            horas = float(self.entry_night_hours.get())
            runs = int(self.entry_night_runs.get())
            
            total_runs = 6 * 3 * runs
            minutos_totais = horas * 60
            
            if total_runs > 0:
                minutos_por_run = minutos_totais / total_runs
                self.lbl_calculated_time.configure(text=f"Aprox. {minutos_por_run:.1f} min/run ({total_runs} testes)")
            else:
                self.lbl_calculated_time.configure(text="Aprox. --- min/run")
        except ValueError:
            self.lbl_calculated_time.configure(text="Valores inválidos")

    def start_night_training(self):
        try:
            horas = float(self.entry_night_hours.get())
            runs = int(self.entry_night_runs.get())
            
            total_runs = 6 * 3 * runs
            minutos_totais = horas * 60
            time_limit_por_run = max(1, int(minutos_totais / total_runs))
            
            paths = self.get_paths()
            print(f"[*] Iniciando Treino Noturno: {horas} horas totais")
            print(f"[*] Dividido de forma justa: {runs} runs por cenario ({total_runs} testes no total)")
            print(f"[*] Tempo atribuído: {time_limit_por_run} min/run")
            
            self.btn_start_night_train.configure(text="Executando Testes...", fg_color="#388E3C", hover_color="#2E7D32")
            self.run_script(paths["run_experiments"], ["--runs", str(runs), "--time", str(time_limit_por_run)], new_window=False)
            self.after(3000, lambda: self.btn_start_night_train.configure(
                text="🚀 Iniciar Rotina de Testes", fg_color="#FF8F00", hover_color="#FF6F00"))
                
        except ValueError:
            print("[!] Erro: Por favor insere valores inteiros/decimais válidos para o treino noturno.")

    def start_all(self):
        self.save_current_config()
        paths = self.get_paths()
        target = self.entry_master_time.get()

        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        if os.path.exists(paths["sac_log"]): os.remove(paths["sac_log"])

        self.gnn_process = self.run_script(paths["gnn_script"], ["--time_limit", target], new_window=False)
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

        self.ppo_process = self.run_script(paths["ppo_script"], ["--time_limit", target], new_window=False)
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#2196F3")

        self.sac_process = self.run_script(paths["sac_script"], ["--time_limit", target], new_window=False)
        self.sac_start_time = time.time()
        self.lbl_sac_status.configure(text="Status: A TREINAR...", text_color="#FF9800")

    def start_gnn(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["gnn_log"]): os.remove(paths["gnn_log"])
        self.gnn_process = self.run_script(paths["gnn_script"], ["--time_limit", self.entry_master_time.get()], new_window=False)
        self.gnn_start_time = time.time()
        self.lbl_gnn_status.configure(text="Status: A TREINAR...", text_color="#4CAF50")

    def start_ppo(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["ppo_log"]): os.remove(paths["ppo_log"])
        self.ppo_process = self.run_script(paths["ppo_script"], ["--time_limit", self.entry_master_time.get()], new_window=False)
        self.ppo_start_time = time.time()
        self.lbl_ppo_status.configure(text="Status: A TREINAR...", text_color="#2196F3")

    def start_sac(self):
        self.save_current_config()
        paths = self.get_paths()
        if os.path.exists(paths["sac_log"]): os.remove(paths["sac_log"])
        self.sac_process = self.run_script(paths["sac_script"], ["--time_limit", self.entry_master_time.get()], new_window=False)
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

    def visualize_algo(self, algo_name):
        self.save_current_config()
        paths = self.get_paths()
        
        # Lançar o visualizador 3D
        visualizer_script = paths.get(f"{algo_name}_visualizer")
        if visualizer_script:
            print(f"INFO: Lançando visualizador 3D '{visualizer_script}' para '{algo_name}'.")
            self.run_script(visualizer_script, keep_console_open=True)
        else:
            print(f"ERRO: Script de visualização 3D para '{algo_name}' não encontrado!")

        # Lançar o plotter de métricas
        plotter_script = paths.get("metrics_plotter")
        if plotter_script:
            # O script `plot_live_metrics` agora lê o cenário do config, então só precisa do algo
            print(f"INFO: Lançando gráfico de métricas para '{algo_name}'.")
            self.run_script(plotter_script, args=["--algo", algo_name], keep_console_open=False)
        else:
            print(f"ERRO: Script de plotagem de métricas não encontrado!")

    def plot_thesis(self):
        try:
            horas = self.entry_night_hours.get()
        except:
            horas = "N"
        self.run_script(self.get_paths()["plot_script"], [horas])

    def update_metrics(self):
        paths = self.get_paths()

        if os.path.exists(paths["gnn_log"]):
            try:
                df = pd.read_csv(paths["gnn_log"]).dropna()
                if not df.empty: self.lbl_gnn_best.configure(text=f"FITNESS: {df.iloc[-1]['best_fitness']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                pass

        if os.path.exists(paths["ppo_log"]):
            try:
                df = pd.read_csv(paths["ppo_log"]).dropna()
                if not df.empty: self.lbl_ppo_score.configure(text=f"REWARD: {df.iloc[-1]['ep_rew_mean']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                pass

        if os.path.exists(paths["sac_log"]):
            try:
                df = pd.read_csv(paths["sac_log"]).dropna()
                if not df.empty: self.lbl_sac_score.configure(text=f"REWARD: {df.iloc[-1]['ep_rew_mean']:.1f}")
            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
                pass

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
                elif scenario == 'cooperative_door':
                    self.combo_scenario.set("Porta Cooperativa (3 Robôs)")
                elif scenario == 'cooperative_perception':
                    self.combo_scenario.set("Perceção Cooperativa (Alvo Móvel)")
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
            elif combo_val == "Porta Cooperativa (3 Robôs)":
                config['environment']['classic_scenario'] = "cooperative_door"
            elif combo_val == "Perceção Cooperativa (Alvo Móvel)":
                config['environment']['classic_scenario'] = "cooperative_perception"
            else:
                config['environment']['classic_scenario'] = "none"

            with open(self.config_path, 'w') as f:
                yaml.dump(config, f)
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            print(f"Error saving config: {e}")


if __name__ == "__main__":
    app = ModernDashboardV6Pro()
    app.mainloop()
