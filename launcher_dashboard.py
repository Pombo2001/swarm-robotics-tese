import customtkinter as ctk
import subprocess
import sys
import os
import pandas as pd
import time
import yaml
from datetime import timedelta

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

SCENARIOS = [
    ("Nenhum (Sandbox)",                "none"),
    ("Beco Sem Saída (Muro U)",          "u_wall"),
    ("Gargalo (Porta Estreita)",         "bottleneck"),
    ("Quatro Salas (Labirinto)",         "four_rooms"),
    ("Porta Cooperativa (3 Robôs)",      "cooperative_door"),
    ("Perceção Cooperativa (Alvo Móvel)","cooperative_perception"),
]
SCENARIO_LABELS = [s[0] for s in SCENARIOS]
SCENARIO_KEYS   = {s[0]: s[1] for s in SCENARIOS}

ALGO_META = {
    "GNN": {"color": "#00C896", "icon": "🧬", "label": "GNN (Evolutivo)"},
    "PPO": {"color": "#3D9EFF", "icon": "🤖", "label": "PPO (Actor-Critic)"},
    "SAC": {"color": "#FF6B6B", "icon": "🔥", "label": "SAC (Soft Actor-Critic)"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ─────────────────────────────────────────────────────────────────────────────

def section(parent, title, **kwargs):
    f = ctk.CTkFrame(parent, fg_color="#1E2128", corner_radius=10, **kwargs)
    ctk.CTkLabel(f, text=title, font=("Roboto", 11, "bold"), text_color="#6B7280").pack(
        anchor="w", padx=14, pady=(10, 4))
    return f

def labeled_entry(parent, label, default, width=70):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=3)
    ctk.CTkLabel(row, text=label, font=("Roboto", 12), text_color="#D1D5DB").pack(side="left")
    e = ctk.CTkEntry(row, width=width, height=28, font=("Roboto", 12),
                     fg_color="#2A2D35", border_color="#3A3F4C")
    e.insert(0, str(default))
    e.pack(side="right")
    return e

def primary_btn(parent, text, command, color="#3D9EFF", height=38, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=color, hover_color=_darken(color),
                         text_color="#FFFFFF", font=("Roboto", 13, "bold"),
                         height=height, corner_radius=8, **kwargs)

def ghost_btn(parent, text, command, color="#F44336", height=33, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color="transparent", border_width=1,
                         border_color=color, text_color=color,
                         hover_color=color, font=("Roboto", 12, "bold"),
                         height=height, corner_radius=8, **kwargs)

def _darken(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{max(0,r-30):02X}{max(0,g-30):02X}{max(0,b-30):02X}"


# ─────────────────────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────────────────────

class SwarmController(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Swarm Robotics Controller")
        self.geometry("1480x820")
        self.minsize(1200, 700)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "configs", "foraging.yaml")

        # Process handles & timers
        self.procs   = {"GNN": None, "PPO": None, "SAC": None}
        self.t_start = {"GNN": None, "PPO": None, "SAC": None}
        self.tour_process = None
        self.tour_start   = None

        self._build_layout()
        self._load_config()
        self._tick()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sb = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color="#13151A")
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(10, weight=1)
        self._build_sidebar(sb)

        # Main (tabbed)
        main = ctk.CTkFrame(self, fg_color="#0F1117", corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self._build_main(main)

    def _build_sidebar(self, sb):
        # Title
        ctk.CTkLabel(sb, text="SWARM\nCONTROLLER",
                     font=("Roboto Black", 24, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=20, pady=(28, 4))
        ctk.CTkLabel(sb, text="● ARENA DE DRONES 3D",
                     font=("Consolas", 11, "bold"), text_color="#00C896"
                     ).grid(row=1, column=0, pady=(0, 20))

        # Cenário
        f_scen = section(sb, "CENÁRIO ATIVO")
        f_scen.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.combo_scenario = ctk.CTkOptionMenu(
            f_scen, values=SCENARIO_LABELS,
            fg_color="#2A2D35", button_color="#3A3F4C",
            button_hover_color="#454A59", font=("Roboto", 11),
            command=self._on_scenario_change)
        self.combo_scenario.pack(padx=12, pady=(0, 12), fill="x")

        # Config
        f_cfg = section(sb, "CONFIGURAÇÃO DA ARENA")
        f_cfg.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.e_drones  = labeled_entry(f_cfg, "Drones:",    20)
        self.e_obs     = labeled_entry(f_cfg, "Obstáculos:", 50)
        self.e_radius  = labeled_entry(f_cfg, "Raio Arena:", 15.0)
        ctk.CTkFrame(f_cfg, height=8, fg_color="transparent").pack()

        # Botão guardar config
        primary_btn(f_cfg, "💾  Guardar Config", self._save_config,
                    color="#374151", height=32).pack(padx=12, pady=(0, 12), fill="x")

        # Separador
        ctk.CTkFrame(sb, height=1, fg_color="#2A2D35").grid(
            row=4, column=0, padx=12, pady=8, sticky="ew")

        # Plot
        primary_btn(sb, "📊  Gerar Gráficos da Tese",
                    self._plot_thesis, color="#0D7377", height=40
                    ).grid(row=9, column=0, padx=12, pady=6, sticky="ew")

        # Viz buttons
        f_viz = section(sb, "VISUALIZAÇÃO 3D")
        f_viz.grid(row=10, column=0, padx=12, pady=(0, 12), sticky="sew")
        for algo, meta in ALGO_META.items():
            primary_btn(f_viz, f"{meta['icon']}  Ver {algo}",
                        lambda a=algo: self._viz(a),
                        color=meta["color"], height=32
                        ).pack(padx=12, pady=3, fill="x")
        ctk.CTkFrame(f_viz, height=8, fg_color="transparent").pack()

    def _build_main(self, main):
        # Tab bar
        tab_bar = ctk.CTkFrame(main, fg_color="#13151A", height=50, corner_radius=0)
        tab_bar.grid(row=0, column=0, sticky="ew")
        self._tab_btns = {}
        self._active_tab = ctk.StringVar(value="rapido")
        tabs = [
            ("rapido",   "⚡  Treino Rápido"),
            ("tour",     "🗺  Tour de Mapas"),
            ("noturno",  "🌙  Rotina Noturna"),
        ]
        for key, label in tabs:
            b = ctk.CTkButton(
                tab_bar, text=label, width=200, height=50,
                fg_color="transparent", hover_color="#1E2128",
                text_color="#9CA3AF", font=("Roboto", 13, "bold"),
                corner_radius=0,
                command=lambda k=key: self._switch_tab(k))
            b.pack(side="left")
            self._tab_btns[key] = b

        # Content area
        self._content = ctk.CTkFrame(main, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._pages = {}
        self._pages["rapido"]  = self._build_page_rapido(self._content)
        self._pages["tour"]    = self._build_page_tour(self._content)
        self._pages["noturno"] = self._build_page_noturno(self._content)

        self._switch_tab("rapido")

    def _switch_tab(self, key):
        for k, p in self._pages.items():
            p.grid_remove()
        self._pages[key].grid(row=0, column=0, sticky="nsew")
        for k, b in self._tab_btns.items():
            if k == key:
                b.configure(text_color="#FFFFFF", fg_color="#1E2128")
            else:
                b.configure(text_color="#9CA3AF", fg_color="transparent")
        self._active_tab.set(key)

    # ── Page: Treino Rápido ─────────────────────────────────────────────────

    def _build_page_rapido(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure((0, 1, 2), weight=1)

        # Top bar: Start All
        top = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        top.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))

        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(pady=14, padx=20)

        ctk.CTkLabel(inner, text="⏱  Tempo Máx. por Algoritmo (minutos):",
                     font=("Roboto", 13), text_color="#D1D5DB").pack(side="left", padx=(0, 10))
        self.e_time = ctk.CTkEntry(inner, width=80, height=32, font=("Roboto", 13),
                                   fg_color="#2A2D35", border_color="#3A3F4C")
        self.e_time.insert(0, "480")
        self.e_time.pack(side="left", padx=(0, 20))

        primary_btn(inner, "🚀  INICIAR OS 3 ALGORITMOS",
                    self._start_all, color="#DC2626", height=40
                    ).pack(side="left")

        # Algo cards
        for col, (algo, meta) in enumerate(ALGO_META.items()):
            self._build_algo_card(page, algo, meta, col)

        return page

    def _build_algo_card(self, parent, algo, meta, col):
        card = ctk.CTkFrame(parent, fg_color="#1E2128", corner_radius=12,
                            border_width=1, border_color="#2A2D35")
        card.grid(row=1, column=col, sticky="nsew", padx=6)
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(card, fg_color="#13151A", corner_radius=10,
                           height=60)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text=f"{meta['icon']}  {meta['label']}",
                     font=("Roboto", 16, "bold"), text_color=meta["color"]
                     ).place(relx=0.5, rely=0.5, anchor="center")

        # Status / timer
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        lbl_st = ctk.CTkLabel(info, text="● PARADO",
                               font=("Consolas", 12), text_color="#6B7280")
        lbl_st.pack()
        lbl_tm = ctk.CTkLabel(info, text="00:00:00",
                               font=("Consolas", 20, "bold"), text_color="#D1D5DB")
        lbl_tm.pack()

        # Metric box
        metric_box = ctk.CTkFrame(card, fg_color="#13151A", corner_radius=8)
        metric_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        lbl_metric = ctk.CTkLabel(metric_box, text="—",
                                   font=("Consolas", 22, "bold"), text_color=meta["color"])
        lbl_metric.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(metric_box, text="FITNESS" if algo == "GNN" else "EP REWARD",
                     font=("Roboto", 10), text_color="#4B5563"
                     ).place(relx=0.5, rely=0.72, anchor="center")

        # Buttons
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 14))

        primary_btn(btns, f"▶  Treinar só {algo}",
                    lambda a=algo: self._start_one(a),
                    color=meta["color"], height=38).pack(fill="x", pady=3)
        ghost_btn(btns, "⏹  Parar",
                  lambda a=algo: self._stop_one(a),
                  color="#F44336", height=32).pack(fill="x", pady=2)

        # Store refs
        setattr(self, f"lbl_{algo}_status", lbl_st)
        setattr(self, f"lbl_{algo}_timer",  lbl_tm)
        setattr(self, f"lbl_{algo}_metric", lbl_metric)

    # ── Page: Tour de Mapas ─────────────────────────────────────────────────

    def _build_page_tour(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        # Header card
        hdr = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(hdr,
                     text="🗺  Tour de Mapas — Treinar um Algoritmo em Todos os Cenários",
                     font=("Roboto", 15, "bold"), text_color="#FFFFFF"
                     ).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(hdr,
                     text="Corre o algoritmo escolhido sequencialmente em cada um dos 6 cenários.",
                     font=("Roboto", 12), text_color="#6B7280"
                     ).pack(pady=(0, 14), padx=20, anchor="w")

        # Body: 2 columns
        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Left: config
        left = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="CONFIGURAÇÃO DO TOUR",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

        # Algorithm selector
        ctk.CTkLabel(left, text="Algoritmo a treinar:",
                     font=("Roboto", 13), text_color="#D1D5DB"
                     ).pack(anchor="w", padx=16, pady=(8, 2))
        self.tour_algo_var = ctk.StringVar(value="GNN")
        algo_frame = ctk.CTkFrame(left, fg_color="transparent")
        algo_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._tour_algo_btns = {}
        for algo, meta in ALGO_META.items():
            b = ctk.CTkButton(
                algo_frame, text=f"{meta['icon']} {algo}",
                width=80, height=36,
                fg_color=meta["color"] if algo == "GNN" else "#2A2D35",
                hover_color=meta["color"],
                text_color="#FFFFFF" if algo == "GNN" else "#9CA3AF",
                font=("Roboto", 12, "bold"),
                corner_radius=8,
                command=lambda a=algo: self._select_tour_algo(a))
            b.pack(side="left", padx=3)
            self._tour_algo_btns[algo] = b

        # Params
        params = ctk.CTkFrame(left, fg_color="transparent")
        params.pack(fill="x", padx=16)
        self.e_tour_runs = labeled_entry(params, "Runs por cenário:", 3)
        self.e_tour_time = labeled_entry(params, "Minutos por run:", 20)

        # Estimated time label
        self.lbl_tour_est = ctk.CTkLabel(
            left, text="", font=("Roboto", 11, "italic"), text_color="#6B7280")
        self.lbl_tour_est.pack(padx=16, pady=(8, 0))
        self.e_tour_runs.bind("<KeyRelease>", self._update_tour_est)
        self.e_tour_time.bind("<KeyRelease>", self._update_tour_est)

        ctk.CTkFrame(left, height=1, fg_color="#2A2D35").pack(fill="x", padx=16, pady=16)

        # Start / Stop tour
        primary_btn(left, "🚀  INICIAR TOUR",
                    self._start_tour, color="#7C3AED", height=44
                    ).pack(padx=16, pady=4, fill="x")
        ghost_btn(left, "⏹  Cancelar Tour",
                  self._stop_tour, color="#F44336", height=36
                  ).pack(padx=16, pady=(4, 16), fill="x")

        # Right: status / progress
        right = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="PROGRESSO DO TOUR",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

        # Status row
        sr = ctk.CTkFrame(right, fg_color="#13151A", corner_radius=8)
        sr.pack(fill="x", padx=16, pady=(0, 12))
        self.lbl_tour_status = ctk.CTkLabel(
            sr, text="● INATIVO", font=("Consolas", 13), text_color="#6B7280")
        self.lbl_tour_status.pack(side="left", padx=16, pady=10)
        self.lbl_tour_timer = ctk.CTkLabel(
            sr, text="00:00:00", font=("Consolas", 18, "bold"), text_color="#D1D5DB")
        self.lbl_tour_timer.pack(side="right", padx=16, pady=10)

        # Scenario checklist
        ctk.CTkLabel(right, text="Cenários incluídos:",
                     font=("Roboto", 12), text_color="#9CA3AF"
                     ).pack(anchor="w", padx=16, pady=(4, 6))

        self.tour_scenario_checks = {}
        self.tour_scenario_status = {}
        for label, key in SCENARIOS:
            row = ctk.CTkFrame(right, fg_color="#13151A", corner_radius=6)
            row.pack(fill="x", padx=16, pady=2)

            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(row, text="", variable=var, width=24,
                                 checkbox_width=18, checkbox_height=18,
                                 fg_color="#7C3AED", hover_color="#6D28D9")
            cb.pack(side="left", padx=(8, 4), pady=8)
            ctk.CTkLabel(row, text=label, font=("Roboto", 12),
                         text_color="#D1D5DB").pack(side="left", pady=8)
            lbl_s = ctk.CTkLabel(row, text="", font=("Consolas", 11),
                                  text_color="#6B7280")
            lbl_s.pack(side="right", padx=12, pady=8)

            self.tour_scenario_checks[key] = var
            self.tour_scenario_status[key] = lbl_s

        self._update_tour_est()
        return page

    def _select_tour_algo(self, algo):
        self.tour_algo_var.set(algo)
        for a, b in self._tour_algo_btns.items():
            meta = ALGO_META[a]
            if a == algo:
                b.configure(fg_color=meta["color"], text_color="#FFFFFF")
            else:
                b.configure(fg_color="#2A2D35", text_color="#9CA3AF")
        self._update_tour_est()

    def _update_tour_est(self, event=None):
        try:
            runs = int(self.e_tour_runs.get())
            mins = int(self.e_tour_time.get())
            selected = sum(1 for v in self.tour_scenario_checks.values() if v.get())
            total_mins = runs * mins * selected
            h, m = divmod(total_mins, 60)
            self.lbl_tour_est.configure(
                text=f"Duração estimada: {h}h {m}m  ({runs * selected} runs no total)")
        except (ValueError, AttributeError):
            if hasattr(self, "lbl_tour_est"):
                self.lbl_tour_est.configure(text="")

    # ── Page: Rotina Noturna ────────────────────────────────────────────────

    def _build_page_noturno(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(hdr, text="🌙  Rotina Noturna — Benchmark Completo (3 Algoritmos × 6 Mapas)",
                     font=("Roboto", 15, "bold"), text_color="#FFFFFF"
                     ).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(hdr,
                     text="Corre automaticamente todos os algoritmos em todos os cenários. Ideal para deixar a correr de noite.",
                     font=("Roboto", 12), text_color="#6B7280"
                     ).pack(pady=(0, 14), padx=20, anchor="w")

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Config
        left = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(left, text="PARÂMETROS",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

        params = ctk.CTkFrame(left, fg_color="transparent")
        params.pack(fill="x", padx=16)
        self.e_night_hours = labeled_entry(params, "Horas totais de treino:", 8)
        self.e_night_runs  = labeled_entry(params, "Runs por cenário:", 5)
        self.e_night_hours.bind("<KeyRelease>", self._update_night_est)
        self.e_night_runs.bind("<KeyRelease>",  self._update_night_est)

        self.lbl_night_est = ctk.CTkLabel(
            left, text="", font=("Roboto", 11, "italic"), text_color="#6B7280")
        self.lbl_night_est.pack(padx=16, pady=(10, 0))

        ctk.CTkFrame(left, height=1, fg_color="#2A2D35").pack(fill="x", padx=16, pady=16)

        self.btn_night = primary_btn(
            left, "🚀  INICIAR ROTINA NOTURNA",
            self._start_night, color="#D97706", height=46)
        self.btn_night.pack(padx=16, pady=4, fill="x")

        ctk.CTkLabel(left,
                     text="Nota: este processo corre em background.\nO terminal mostra o progresso.",
                     font=("Roboto", 11, "italic"), text_color="#6B7280",
                     justify="left").pack(padx=16, pady=(12, 0), anchor="w")

        # Info panel
        right = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(right, text="O QUE SERÁ EXECUTADO",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

        for label, _ in SCENARIOS:
            row = ctk.CTkFrame(right, fg_color="#13151A", corner_radius=6)
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=f"📍 {label}",
                         font=("Roboto", 12), text_color="#D1D5DB"
                         ).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(row, text="GNN  PPO  SAC",
                         font=("Consolas", 10), text_color="#4B5563"
                         ).pack(side="right", padx=12, pady=8)

        self._update_night_est()
        return page

    def _update_night_est(self, event=None):
        try:
            horas = float(self.e_night_hours.get())
            runs = int(self.e_night_runs.get())
            total = 6 * 3 * runs
            min_per_run = max(1, int(horas * 60 / total))
            self.lbl_night_est.configure(
                text=f"~{min_per_run} min/run  ·  {total} runs no total  ·  {horas}h distribuídas")
        except (ValueError, AttributeError):
            if hasattr(self, "lbl_night_est"):
                self.lbl_night_est.configure(text="")

    # ── Config helpers ───────────────────────────────────────────────────────

    def _get_paths(self):
        b = self.base_dir
        return {
            "gnn_log": os.path.join(b, "results/logs/gnn_3d_training.csv"),
            "ppo_log": os.path.join(b, "results/logs_ppo/training_history_ppo_3d.csv"),
            "sac_log": os.path.join(b, "results/logs_ppo/training_history_sac_3d.csv"),
            "GNN": "src/training/evo_trainer_3d.py",
            "PPO": "src/training/train_ppo_3d.py",
            "SAC": "src/training/train_sac_3d.py",
            "viz_GNN": "visualize_3d.py",
            "viz_PPO": "visualize_ppo_3d.py",
            "viz_SAC": "visualize_sac_3d.py",
            "plot":    "plot_final_thesis_3d.py",
            "run_exp": "run_experiments.py",
        }

    def _run_script(self, script, args=None, console=True):
        full = os.path.join(self.base_dir, script)
        flags = 0 if console else subprocess.CREATE_NO_WINDOW
        return subprocess.Popen(
            [sys.executable, full] + (args or []),
            creationflags=flags | subprocess.CREATE_NEW_CONSOLE if console else flags)

    def _load_config(self):
        try:
            with open(self.config_path) as f:
                cfg = yaml.safe_load(f)
            env = cfg.get("environment", {})
            self.e_drones.delete(0, "end"); self.e_drones.insert(0, str(env.get("num_agents", 20)))
            self.e_obs.delete(0, "end");    self.e_obs.insert(0, str(env.get("num_obstacles", 50)))
            self.e_radius.delete(0, "end"); self.e_radius.insert(0, str(env.get("arena_radius", 15.0)))
            sc = env.get("classic_scenario", "none")
            label = next((s[0] for s in SCENARIOS if s[1] == sc), SCENARIO_LABELS[0])
            self.combo_scenario.set(label)
        except Exception:
            pass

    def _save_config(self):
        try:
            with open(self.config_path) as f:
                cfg = yaml.safe_load(f)
            cfg["environment"]["num_agents"]      = int(self.e_drones.get())
            cfg["environment"]["num_obstacles"]   = int(self.e_obs.get())
            cfg["environment"]["arena_radius"]    = float(self.e_radius.get())
            cfg["environment"]["classic_scenario"] = SCENARIO_KEYS[self.combo_scenario.get()]
            with open(self.config_path, "w") as f:
                yaml.dump(cfg, f)
        except Exception as e:
            print(f"[!] Erro a guardar config: {e}")

    def _on_scenario_change(self, _=None):
        self._save_config()

    # ── Training actions ─────────────────────────────────────────────────────

    def _start_all(self):
        self._save_config()
        t = self.e_time.get()
        for algo in ("GNN", "PPO", "SAC"):
            self._launch_algo(algo, t)

    def _start_one(self, algo):
        self._save_config()
        self._launch_algo(algo, self.e_time.get())

    def _launch_algo(self, algo, time_limit):
        p = self._get_paths()
        log_key = f"{algo.lower()}_log"
        if log_key in p and os.path.exists(p[log_key]):
            try: os.remove(p[log_key])
            except: pass
        self.procs[algo]   = self._run_script(p[algo], ["--time_limit", str(time_limit)])
        self.t_start[algo] = time.time()
        meta = ALGO_META[algo]
        getattr(self, f"lbl_{algo}_status").configure(
            text=f"● A TREINAR...", text_color=meta["color"])

    def _stop_one(self, algo):
        if self.procs[algo]:
            self.procs[algo].terminate()
            self.procs[algo] = None
        self.t_start[algo] = None
        getattr(self, f"lbl_{algo}_status").configure(
            text="● PARADO", text_color="#6B7280")

    def _start_tour(self):
        self._save_config()
        algo = self.tour_algo_var.get()
        try:
            runs = int(self.e_tour_runs.get())
            mins = int(self.e_tour_time.get())
        except ValueError:
            return

        selected = [key for key, var in self.tour_scenario_checks.items() if var.get()]
        if not selected:
            return

        # Reset status labels
        for key, lbl in self.tour_scenario_status.items():
            lbl.configure(text="⏳ pendente" if key in selected else "", text_color="#6B7280")

        # Build a small inline runner script via run_experiments with algo filter
        # We create a temp script that only runs the chosen algorithm
        self.tour_process = self._run_tour_process(algo, selected, runs, mins)
        self.tour_start   = time.time()
        self.lbl_tour_status.configure(text=f"● A CORRER — {algo}", text_color=ALGO_META[algo]["color"])

    def _run_tour_process(self, algo, scenarios, runs, time_limit):
        script = os.path.join(self.base_dir, "run_experiments.py")
        args = [
            sys.executable, script,
            "--runs", str(runs),
            "--time", str(time_limit),
            "--algo", algo,
            "--scenarios", ",".join(scenarios),
        ]
        return subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def _stop_tour(self):
        if self.tour_process:
            self.tour_process.terminate()
            self.tour_process = None
        self.tour_start = None
        self.lbl_tour_status.configure(text="● CANCELADO", text_color="#F44336")
        self.lbl_tour_timer.configure(text="00:00:00")

    def _start_night(self):
        self._save_config()
        try:
            horas = float(self.e_night_hours.get())
            runs  = int(self.e_night_runs.get())
            total = 6 * 3 * runs
            mins_per_run = max(1, int(horas * 60 / total))
        except ValueError:
            return
        self._run_script(self._get_paths()["run_exp"],
                         ["--runs", str(runs), "--time", str(mins_per_run)])
        self.btn_night.configure(text="✔  Rotina Iniciada (background)", fg_color="#065F46")
        self.after(4000, lambda: self.btn_night.configure(
            text="🚀  INICIAR ROTINA NOTURNA", fg_color="#D97706"))

    # ── Visualization / Plot ─────────────────────────────────────────────────

    def _viz(self, algo):
        self._save_config()
        self._run_script(self._get_paths()[f"viz_{algo}"], console=False)

    def _plot_thesis(self):
        self._run_script(self._get_paths()["plot"])

    # ── Tick / Metrics ───────────────────────────────────────────────────────

    def _tick(self):
        self._update_algo_metrics()
        self._update_timers()
        self.after(1000, self._tick)

    def _update_algo_metrics(self):
        p = self._get_paths()
        pairs = [
            ("GNN", p["gnn_log"], "best_fitness"),
            ("PPO", p["ppo_log"], "ep_rew_mean"),
            ("SAC", p["sac_log"], "ep_rew_mean"),
        ]
        for algo, log, col in pairs:
            if not os.path.exists(log):
                continue
            try:
                df = pd.read_csv(log).dropna()
                if not df.empty and col in df.columns:
                    val = df.iloc[-1][col]
                    getattr(self, f"lbl_{algo}_metric").configure(text=f"{val:.1f}")
            except Exception:
                pass

    def _update_timers(self):
        for algo in ("GNN", "PPO", "SAC"):
            t0 = self.t_start[algo]
            proc = self.procs[algo]
            if t0 and proc:
                if proc.poll() is not None:
                    # finished
                    self.procs[algo]   = None
                    self.t_start[algo] = None
                    getattr(self, f"lbl_{algo}_status").configure(
                        text="● CONCLUÍDO", text_color="#00C896")
                else:
                    elapsed = str(timedelta(seconds=int(time.time() - t0)))
                    getattr(self, f"lbl_{algo}_timer").configure(text=elapsed)

        if self.tour_start and self.tour_process:
            if self.tour_process.poll() is not None:
                self.tour_process  = None
                self.tour_start    = None
                self.lbl_tour_status.configure(text="● CONCLUÍDO", text_color="#00C896")
                for lbl in self.tour_scenario_status.values():
                    if lbl.cget("text") == "⏳ pendente":
                        lbl.configure(text="")
            else:
                elapsed = str(timedelta(seconds=int(time.time() - self.tour_start)))
                self.lbl_tour_timer.configure(text=elapsed)


if __name__ == "__main__":
    app = SwarmController()
    app.mainloop()
