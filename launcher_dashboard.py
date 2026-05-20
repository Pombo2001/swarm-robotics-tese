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

# Definir os cenários e algoritmos globalmente para fácil acesso
SCENARIOS = ['none', 'u_wall', 'bottleneck', 'four_rooms', 'cooperative_door', 'cooperative_perception']
ALGORITHMS = ['gnn', 'ppo', 'sac']

class ModernDashboardV6Pro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔬 Swarm Robotics Controller - Master Edition")
        self.geometry("1400x750")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, 'configs', 'foraging.yaml')
        self.mode = "3D"

        self.training_processes = {}
        self.training_start_times = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Ajustar para o novo layout

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
        ], fg_color="#6A1B9A", button_color="#4A148C", command=self.on_scenario_change)
        self.combo_scenario.pack(padx=15, pady=10, fill="x")
        self.combo_scenario.set("Nenhum (Modo Sandbox)")

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

        # === CENTRO DE CONTROLO DE TREINO ===
        self.training_control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#004d40", corner_radius=10)
        self.training_control_frame.grid(row=4, column=0, padx=15, pady=10, sticky="nsew")
        ctk.CTkLabel(self.training_control_frame, text="🚀 CENTRO DE CONTROLO DE TREINO", font=("Roboto", 14, "bold"),
                     text_color="#80cbc4").pack(pady=(10, 5))

        algo_selection_frame = ctk.CTkFrame(self.training_control_frame, fg_color="transparent")
        algo_selection_frame.pack(padx=10, pady=5, fill="x")
        ctk.CTkLabel(algo_selection_frame, text="Algoritmos:", font=("Roboto", 12)).grid(row=0, column=0, sticky="w")
        
        self.algo_vars = {
            'gnn': ctk.BooleanVar(value=True),
            'ppo': ctk.BooleanVar(value=True),
            'sac': ctk.BooleanVar(value=True)
        }
        ctk.CTkCheckBox(algo_selection_frame, text="GNN", variable=self.algo_vars['gnn'], command=self.update_calculated_time).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkCheckBox(algo_selection_frame, text="PPO", variable=self.algo_vars['ppo'], command=self.update_calculated_time).grid(row=0, column=2, padx=5, sticky="w")
        ctk.CTkCheckBox(algo_selection_frame, text="SAC", variable=self.algo_vars['sac'], command=self.update_calculated_time).grid(row=0, column=3, padx=5, sticky="w")

        scope_selection_frame = ctk.CTkFrame(self.training_control_frame, fg_color="transparent")
        scope_selection_frame.pack(padx=10, pady=5, fill="x")
        self.training_scope_var = ctk.StringVar(value="all_scenarios")
        ctk.CTkRadioButton(scope_selection_frame, text="Treinar em TODOS os Cenários (Tese)", variable=self.training_scope_var, value="all_scenarios", command=self.update_calculated_time).pack(anchor="w")
        ctk.CTkRadioButton(scope_selection_frame, text="Treinar apenas no Cenário Atual", variable=self.training_scope_var, value="current_scenario", command=self.update_calculated_time).pack(anchor="w")

        params_grid = ctk.CTkFrame(self.training_control_frame, fg_color="transparent")
        params_grid.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(params_grid, text="Tempo por Teste (Minutos):", font=("Roboto", 12)).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_time_per_run = ctk.CTkEntry(params_grid, width=60, height=25)
        self.entry_time_per_run.insert(0, "60")
        self.entry_time_per_run.grid(row=0, column=1, sticky="e", pady=5)
        self.entry_time_per_run.bind("<KeyRelease>", self.update_calculated_time)

        ctk.CTkLabel(params_grid, text="Nº de Repetições (Runs):", font=("Roboto", 12)).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_num_repetitions = ctk.CTkEntry(params_grid, width=60, height=25)
        self.entry_num_repetitions.insert(0, "3")
        self.entry_num_repetitions.grid(row=1, column=1, sticky="e", pady=5)
        self.entry_num_repetitions.bind("<KeyRelease>", self.update_calculated_time)

        self.lbl_total_training_time = ctk.CTkLabel(self.training_control_frame, text="Tempo Total Estimado: 0 min", font=("Roboto", 11, "italic"), text_color="#A1A1A1")
        self.lbl_total_training_time.pack(pady=(0, 10))

        self.btn_start_training = ctk.CTkButton(self.training_control_frame, text="🚀 INICIAR TREINO",
                                             command=self.start_unified_training, fg_color="#00897b", hover_color="#00695c",
                                             text_color="black", font=("Roboto", 12, "bold"), height=35)
        self.btn_start_training.pack(pady=(5, 15), padx=15, fill="x")

        self.btn_plot_thesis = ctk.CTkButton(self.sidebar_frame, text="📊 Gerar Gráficos Pós-Treino",
                                             command=self.plot_thesis, fg_color="#8E24AA", hover_color="#6A1B9A",
                                             font=("Roboto", 14, "bold"), height=40)
        self.btn_plot_thesis.grid(row=5, column=0, padx=20, pady=20, sticky="sew")

        # === MAIN AREA ===
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(self.main_area, text="MONITORIZAÇÃO DE PROCESSOS",
                     font=("Roboto", 16, "bold"), text_color="#E0E0E0").grid(row=0, column=0, columnspan=3, pady=(0, 20))

        self._create_algo_monitor_frame("gnn", "🧬 GNN (Evolutivo)", "#4CAF50", 0)
        self._create_algo_monitor_frame("ppo", "🤖 PPO (Actor-Critic)", "#2196F3", 1)
        self._create_algo_monitor_frame("sac", "🔥 SAC (Soft Actor-Critic)", "#FF9800", 2, text_color="black")

        self.load_current_config()
        self.update_calculated_time()
        self.update_metrics()

    def _create_algo_monitor_frame(self, name, title, color, col, text_color=None):
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

        ctk.CTkButton(frame, text="🎥 Visualizar com Gráficos", command=partial(self.visualize_algo, name), fg_color="#1F6AA5", height=35).pack(pady=20, padx=20, fill="x")

        setattr(self, f"lbl_{name}_status", status_label)
        setattr(self, f"lbl_{name}_timer", timer_label)
        setattr(self, f"metrics_{name}", metric_label)
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
        if args is None: args = []
        full_path = os.path.join(self.base_dir, script)
        
        if new_window:
            cmd = ['cmd', '/c', 'start', 'cmd', '/k' if keep_console_open else '/c', sys.executable, full_path] + args
            return subprocess.Popen(cmd, shell=True)
        else:
            return subprocess.Popen([sys.executable, full_path] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def update_calculated_time(self, event=None):
        try:
            time_per_run = float(self.entry_time_per_run.get())
            num_repetitions = int(self.entry_num_repetitions.get())
            selected_algos = [algo for algo, var in self.algo_vars.items() if var.get()]
            num_algos = len(selected_algos)
            num_scenarios = len(SCENARIOS) if self.training_scope_var.get() == "all_scenarios" else 1
            
            if num_algos == 0:
                self.lbl_total_training_time.configure(text="Selecione pelo menos um algoritmo.")
                return

            total_minutes = time_per_run * num_repetitions * num_algos * num_scenarios
            total_hours = total_minutes / 60
            self.lbl_total_training_time.configure(text=f"Tempo Total Estimado: {total_hours:.1f}h ({total_minutes:.0f} min)")
        except ValueError:
            self.lbl_total_training_time.configure(text="Valores inválidos")

    def start_unified_training(self):
        self.save_current_config()
        selected_algos = [algo for algo, var in self.algo_vars.items() if var.get()]
        if not selected_algos:
            print("[!] Erro: Selecione pelo menos um algoritmo para treinar.")
            return

        try:
            time_per_run = int(self.entry_time_per_run.get())
            num_repetitions = int(self.entry_num_repetitions.get())
        except ValueError:
            print("[!] Erro: Tempo e Repetições devem ser números inteiros.")
            return

        paths = self.get_paths()
        
        if self.training_scope_var.get() == "all_scenarios":
            print(f"[*] Iniciando Treino Unificado em TODOS os Cenários para: {', '.join(selected_algos).upper()}")
            algo_args = [f"--{algo}" for algo in selected_algos]
            process = self.run_script(paths["run_experiments"], ["--runs", str(num_repetitions), "--time", str(time_per_run)] + algo_args, new_window=False)
            self.training_processes['all_scenarios'] = process
            self.training_start_times['all_scenarios'] = time.time()
            for algo in ALGORITHMS:
                status_color = "#00897b" if algo in selected_algos else "white"
                status_text = "Status: A TREINAR (TODOS)" if algo in selected_algos else "Status: PARADO"
                getattr(self, f"lbl_{algo}_status").configure(text=status_text, text_color=status_color)
        else:
            current_scenario_name = self.map_scenario_name(self.combo_scenario.get(), to_config=True)
            print(f"[*] Iniciando Treino Unificado no Cenário ATUAL ({current_scenario_name.upper()}) para: {', '.join(selected_algos).upper()}")
            self.save_current_config(scenario_override=current_scenario_name)
            for algo in selected_algos:
                script_path = paths.get(f"{algo}_script")
                process = self.run_script(script_path, ["--time_limit", str(time_per_run)], new_window=False)
                self.training_processes[algo] = process
                self.training_start_times[algo] = time.time()
                getattr(self, f"lbl_{algo}_status").configure(text="Status: A TREINAR...", text_color="#00897b")

        self.btn_start_training.configure(state="disabled", text="TREINO A DECORRER...")
        self.after(2000, self._check_training_status)

    def _check_training_status(self):
        active_processes = False
        for key, process in list(self.training_processes.items()):
            if process and process.poll() is None:
                active_processes = True
                if key == 'all_scenarios':
                    elapsed_time = int(time.time() - self.training_start_times[key])
                    for algo in [a for a, v in self.algo_vars.items() if v.get()]:
                        getattr(self, f"lbl_{algo}_timer").configure(text=f"Tempo: {str(timedelta(seconds=elapsed_time))}")
                else:
                    elapsed_time = int(time.time() - self.training_start_times[key])
                    getattr(self, f"lbl_{key}_timer").configure(text=f"Tempo: {str(timedelta(seconds=elapsed_time))}")
            elif process:
                print(f"[*] Processo de treino '{key}' terminou.")
                if key == 'all_scenarios':
                    for algo in ALGORITHMS: getattr(self, f"lbl_{algo}_status").configure(text="Status: PARADO", text_color="white")
                else:
                    getattr(self, f"lbl_{key}_status").configure(text="Status: PARADO", text_color="white")
                self.training_processes.pop(key)
                self.training_start_times.pop(key, None)
                self.update_metrics()

        if active_processes:
            self.after(2000, self._check_training_status)
        else:
            print("[*] Todos os treinos terminaram.")
            self.btn_start_training.configure(state="normal", text="🚀 INICIAR TREINO")
            self.update_metrics()

    def visualize_algo(self, algo_name):
        self.save_current_config()
        paths = self.get_paths()
        visualizer_script = paths.get(f"{algo_name}_visualizer")
        if visualizer_script: self.run_script(visualizer_script, keep_console_open=True)
        plotter_script = paths.get("metrics_plotter")
        if plotter_script: self.run_script(plotter_script, args=["--algo", algo_name], keep_console_open=False)

    def plot_thesis(self):
        self.run_script(self.get_paths()["plot_script"], new_window=True, keep_console_open=False)

    def update_metrics(self):
        paths = self.get_paths()
        for algo in ALGORITHMS:
            log_path = paths.get(f"{algo}_log")
            metric_label = getattr(self, f"lbl_{algo}_best" if algo == "gnn" else f"lbl_{algo}_score")
            if os.path.exists(log_path):
                try:
                    df = pd.read_csv(log_path).dropna()
                    if not df.empty:
                        metric_key = 'best_fitness' if algo == 'gnn' else 'ep_rew_mean'
                        metric_label.configure(text=f"{'FITNESS' if algo == 'gnn' else 'REWARD'}: {df.iloc[-1][metric_key]:.1f}")
                except (FileNotFoundError, pd.errors.EmptyDataError, KeyError):
                    metric_label.configure(text=f"{'FITNESS' if algo == 'gnn' else 'REWARD'}: ---")
        self.after(5000, self.update_metrics)

    def map_scenario_name(self, name, to_config=False):
        mapping = {
            "Nenhum (Modo Sandbox)": "none", "Beco Sem Saída (Muro U)": "u_wall",
            "Gargalo (Porta Estreita)": "bottleneck", "Quatro Salas (Labirinto)": "four_rooms",
            "Porta Cooperativa (3 Robôs)": "cooperative_door", "Perceção Cooperativa (Alvo Móvel)": "cooperative_perception"
        }
        if to_config: return mapping.get(name, "none")
        reverse_mapping = {v: k for k, v in mapping.items()}
        return reverse_mapping.get(name, "Nenhum (Modo Sandbox)")

    def load_current_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            env_conf = config.get('environment', {})
            self.entry_num_drones.delete(0, ctk.END)
            self.entry_num_drones.insert(0, str(env_conf.get('num_agents', 20)))
            self.entry_num_obs.delete(0, ctk.END)
            self.entry_num_obs.insert(0, str(env_conf.get('num_obstacles', 10)))
            self.entry_arena_radius.delete(0, ctk.END)
            self.entry_arena_radius.insert(0, str(env_conf.get('arena_radius', 15.0)))
            scenario = env_conf.get('classic_scenario', 'none')
            self.combo_scenario.set(self.map_scenario_name(scenario))
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error loading config: {e}")

    def save_current_config(self, scenario_override=None):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Apenas escreve os valores do sandbox se o modo for 'none'
            if self.map_scenario_name(self.combo_scenario.get(), to_config=True) == 'none':
                config['environment']['num_agents'] = int(self.entry_num_drones.get())
                config['environment']['num_obstacles'] = int(self.entry_num_obs.get())
                config['environment']['arena_radius'] = float(self.entry_arena_radius.get())

            config['environment']['classic_scenario'] = scenario_override if scenario_override else self.map_scenario_name(self.combo_scenario.get(), to_config=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f)
            print(f"[*] Configuração salva: cenário '{config['environment']['classic_scenario']}'")
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            print(f"Error saving config: {e}")

    def on_scenario_change(self, choice):
        self.save_current_config()


if __name__ == "__main__":
    app = ModernDashboardV6Pro()
    app.mainloop()