import customtkinter as ctk
import subprocess
import sys
import os
import pandas as pd
import time
import yaml
from datetime import timedelta

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

SCENARIOS = [
    ("Nenhum (Sandbox)",                 "none"),
    ("Beco Sem Saída (Muro U)",           "u_wall"),
    ("Gargalo (Porta Estreita)",          "bottleneck"),
    ("Quatro Salas (Labirinto)",          "four_rooms"),
    ("Porta Cooperativa (3 Robôs)",       "cooperative_door"),
    ("Perceção Cooperativa (Alvo Móvel)", "cooperative_perception"),
]
SCENARIO_LABELS = [s[0] for s in SCENARIOS]
SCENARIO_KEYS   = {s[0]: s[1] for s in SCENARIOS}

ALGO_META = {
    "GNN": {"color": "#00C896", "icon": "🧬", "label": "GNN (Evolutivo)"},
    "PPO": {"color": "#3D9EFF", "icon": "🤖", "label": "PPO (Actor-Critic)"},
    "SAC": {"color": "#FF6B6B", "icon": "🔥", "label": "SAC (Soft Actor-Critic)"},
}

# Gráficos disponíveis por categoria
GRAPH_CATEGORIES = [
    ("🗺  Por Mapa", [
        ("Sandbox",           "comparacao_mapa_none.png"),
        ("Muro U",            "comparacao_mapa_u_wall.png"),
        ("Gargalo",           "comparacao_mapa_bottleneck.png"),
        ("Quatro Salas",      "comparacao_mapa_four_rooms.png"),
        ("Porta Cooperativa", "comparacao_mapa_cooperative_door.png"),
        ("Perceção Coop.",    "comparacao_mapa_cooperative_perception.png"),
    ]),
    ("📈  Por Algoritmo", [
        ("GNN – Curva Global", "desempenho_global_gnn.png"),
        ("PPO – Curva Global", "desempenho_global_ppo.png"),
        ("SAC – Curva Global", "desempenho_global_sac.png"),
    ]),
    ("📦  Boxplots", [
        ("Sandbox",           "boxplot_none.png"),
        ("Muro U",            "boxplot_u_wall.png"),
        ("Gargalo",           "boxplot_bottleneck.png"),
        ("Quatro Salas",      "boxplot_four_rooms.png"),
        ("Porta Cooperativa", "boxplot_cooperative_door.png"),
        ("Perceção Coop.",    "boxplot_cooperative_perception.png"),
    ]),
    ("🏆  Geral", [
        ("Comparação Barras", "comparacao_barras_geral.png"),
    ]),
]

# Descrição de cada gráfico: (título curto, explicação detalhada)
GRAPH_DESCRIPTIONS = {
    "comparacao_mapa_none.png": (
        "Sandbox — Arena Aberta",
        "Curva de aprendizagem dos 3 algoritmos no cenário base, sem obstáculos fixos e ninho estático. "
        "Mostra a capacidade de forrageamento pura. Valores mais altos = melhor desempenho. "
        "A sombra representa o desvio padrão entre as 5 runs independentes.",
    ),
    "comparacao_mapa_u_wall.png": (
        "Beco Sem Saída — Muro U",
        "Um muro em forma de U bloqueia o caminho direto ao ninho. "
        "Os agentes têm de aprender a explorar lateralmente em vez de avançar em linha reta. "
        "Mede adaptação a obstáculos estruturados simples.",
    ),
    "comparacao_mapa_bottleneck.png": (
        "Gargalo — Porta Estreita",
        "Duas paredes paralelas criam uma passagem de apenas 1,5m no centro da arena. "
        "Testa gestão de congestionamento: os agentes têm de se organizar para passar em fila. "
        "Cenário que favorece comportamento emergente de fila.",
    ),
    "comparacao_mapa_four_rooms.png": (
        "Quatro Salas — Labirinto",
        "A arena está dividida em 4 quadrantes com passagens estreitas nas paredes. "
        "Exige navegação estruturada e memória do caminho percorrido. "
        "O cenário mais complexo em termos de planeamento espacial.",
    ),
    "comparacao_mapa_cooperative_door.png": (
        "Porta Cooperativa — 3 Robôs",
        "Uma porta bloqueia o acesso ao ninho e só abre quando 3 robôs a empurram em simultâneo. "
        "Testa coordenação emergente: os agentes têm de convergir para o mesmo ponto ao mesmo tempo, "
        "sem comunicação explícita sobre intenções.",
    ),
    "comparacao_mapa_cooperative_perception.png": (
        "Perceção Cooperativa — Alvo Móvel",
        "Um alvo em movimento só é 'capturado' quando pelo menos 3 robôs o rodeiam a 360°. "
        "Avalia perseguição dinâmica e encirclement cooperativo. "
        "O algoritmo precisa de aprender a distribuir os agentes espacialmente em torno do alvo.",
    ),
    "desempenho_global_gnn.png": (
        "GNN — Curva em Todos os Mapas",
        "Desempenho do algoritmo GNN (evolutivo) em cada um dos 6 cenários ao longo do treino. "
        "O GNN usa uma rede neuronal de grafos com self-attention sobre vizinhos. "
        "Fitness = média de 3 episódios; cada geração avalia 30 genomas em paralelo.",
    ),
    "desempenho_global_ppo.png": (
        "PPO — Curva em Todos os Mapas",
        "Desempenho do PPO (Proximal Policy Optimization) em cada cenário. "
        "Método on-policy Actor-Critic com parameter sharing entre todos os agentes. "
        "Aprende por atualização periódica de uma policy partilhada.",
    ),
    "desempenho_global_sac.png": (
        "SAC — Curva em Todos os Mapas",
        "Desempenho do SAC (Soft Actor-Critic) em cada cenário. "
        "Método off-policy com entropia regularizada — tende a convergir mais rápido mas pode regredir "
        "se a entropia subir demasiado (problema conhecido no treino de longa duração).",
    ),
    "boxplot_none.png":                    ("Boxplot Sandbox",          "Distribuição dos melhores scores em 5 runs independentes — Sandbox."),
    "boxplot_u_wall.png":                  ("Boxplot Muro U",           "Distribuição dos melhores scores em 5 runs independentes — Beco Sem Saída."),
    "boxplot_bottleneck.png":              ("Boxplot Gargalo",          "Distribuição dos melhores scores em 5 runs independentes — Gargalo."),
    "boxplot_four_rooms.png":              ("Boxplot Quatro Salas",     "Distribuição dos melhores scores em 5 runs independentes — Labirinto."),
    "boxplot_cooperative_door.png":        ("Boxplot Porta Coop.",      "Distribuição dos melhores scores em 5 runs independentes — Porta Cooperativa."),
    "boxplot_cooperative_perception.png":  ("Boxplot Perceção Coop.",   "Distribuição dos melhores scores em 5 runs independentes — Perceção Cooperativa."),
    "comparacao_barras_geral.png": (
        "Comparação Geral — Resumo Final",
        "Visão geral de todos os algoritmos em todos os mapas. "
        "Cada barra é a média do melhor score alcançado (N=5 runs). "
        "Barras de erro = desvio padrão entre runs. "
        "NOTA: GNN usa fitness evolutiva (escala diferente de PPO/SAC).",
    ),
}

# Nomes alternativos (formatos antigos) para fallback
GRAPH_FALLBACKS = {
    "comparacao_mapa_none.png":                    ["comparacao_none.png"],
    "comparacao_mapa_u_wall.png":                  ["comparacao_u_wall.png"],
    "comparacao_mapa_bottleneck.png":              ["comparacao_bottleneck.png"],
    "comparacao_mapa_four_rooms.png":              ["comparacao_four_rooms.png"],
    "comparacao_mapa_cooperative_door.png":        ["comparacao_cooperative_door.png"],
    "comparacao_mapa_cooperative_perception.png":  ["comparacao_cooperative_perception.png"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ─────────────────────────────────────────────────────────────────────────────

def section(parent, title, **kwargs):
    f = ctk.CTkFrame(parent, fg_color="#1E2128", corner_radius=10, **kwargs)
    ctk.CTkLabel(f, text=title, font=("Roboto", 11, "bold"),
                 text_color="#6B7280").pack(anchor="w", padx=14, pady=(10, 4))
    return f

def labeled_entry(parent, label, default, width=70):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=3)
    ctk.CTkLabel(row, text=label, font=("Roboto", 12),
                 text_color="#D1D5DB").pack(side="left")
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
        self.geometry("1500x860")
        self.minsize(1200, 700)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "configs", "foraging.yaml")

        self.procs   = {"GNN": None, "PPO": None, "SAC": None}
        self.t_start = {"GNN": None, "PPO": None, "SAC": None}
        self.tour_process = None
        self.tour_start   = None

        self._current_session_path = None
        self._current_img_ref      = None
        self._active_graph_btn     = None
        self._session_btns         = {}
        self._session_dir_map      = {}
        self._graph_btns           = {}

        self._build_layout()
        self._load_config()
        self._tick()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sb = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color="#13151A")
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(10, weight=1)
        self._build_sidebar(sb)

        main = ctk.CTkFrame(self, fg_color="#0F1117", corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self._build_main(main)

    def _build_sidebar(self, sb):
        ctk.CTkLabel(sb, text="SWARM\nCONTROLLER",
                     font=("Roboto Black", 24, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=20, pady=(28, 4))
        ctk.CTkLabel(sb, text="● ARENA DE DRONES 3D",
                     font=("Consolas", 11, "bold"), text_color="#00C896"
                     ).grid(row=1, column=0, pady=(0, 20))

        f_scen = section(sb, "CENÁRIO ATIVO")
        f_scen.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.combo_scenario = ctk.CTkOptionMenu(
            f_scen, values=SCENARIO_LABELS,
            fg_color="#2A2D35", button_color="#3A3F4C",
            button_hover_color="#454A59", font=("Roboto", 11),
            command=self._on_scenario_change)
        self.combo_scenario.pack(padx=12, pady=(0, 12), fill="x")

        f_cfg = section(sb, "CONFIGURAÇÃO DA ARENA")
        f_cfg.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.e_drones = labeled_entry(f_cfg, "Drones:",     20)
        self.e_obs    = labeled_entry(f_cfg, "Obstáculos:", 50)
        self.e_radius = labeled_entry(f_cfg, "Raio Arena:", 15.0)
        ctk.CTkFrame(f_cfg, height=8, fg_color="transparent").pack()
        primary_btn(f_cfg, "💾  Guardar Config", self._save_config,
                    color="#374151", height=32).pack(padx=12, pady=(0, 12), fill="x")

        ctk.CTkFrame(sb, height=1, fg_color="#2A2D35").grid(
            row=4, column=0, padx=12, pady=8, sticky="ew")

        primary_btn(sb, "📊  Gerar Gráficos da Tese",
                    self._plot_thesis, color="#0D7377", height=40
                    ).grid(row=9, column=0, padx=12, pady=6, sticky="ew")

        f_viz = section(sb, "VISUALIZAÇÃO 3D")
        f_viz.grid(row=10, column=0, padx=12, pady=(0, 12), sticky="sew")
        for algo, meta in ALGO_META.items():
            primary_btn(f_viz, f"{meta['icon']}  Ver {algo}",
                        lambda a=algo: self._viz(a),
                        color=meta["color"], height=32
                        ).pack(padx=12, pady=3, fill="x")
        ctk.CTkFrame(f_viz, height=4, fg_color="transparent").pack()
        primary_btn(f_viz, "📊  Avaliar Modelo",
                    self._eval_model, color="#6B4FA0", height=32
                    ).pack(padx=12, pady=(0, 6), fill="x")
        primary_btn(f_viz, "🗺️  Ver Mapas (3D + Topo)",
                    self._render_maps, color="#0E7490", height=32
                    ).pack(padx=12, pady=(0, 6), fill="x")
        primary_btn(f_viz, "🔥  Gerar Heatmaps",
                    self._render_heatmaps, color="#B45309", height=32
                    ).pack(padx=12, pady=(0, 6), fill="x")
        ctk.CTkFrame(f_viz, height=4, fg_color="transparent").pack()

    def _build_main(self, main):
        tab_bar = ctk.CTkFrame(main, fg_color="#13151A", height=50, corner_radius=0)
        tab_bar.grid(row=0, column=0, sticky="ew")
        self._tab_btns   = {}
        self._active_tab = ctk.StringVar(value="rapido")
        tabs = [
            ("rapido",     "⚡  Treino Rápido"),
            ("tour",       "🗺  Tour de Mapas"),
            ("noturno",    "🌙  Rotina Noturna"),
            ("resultados", "📈  Resultados"),
        ]
        for key, label in tabs:
            b = ctk.CTkButton(
                tab_bar, text=label, width=190, height=50,
                fg_color="transparent", hover_color="#1E2128",
                text_color="#9CA3AF", font=("Roboto", 13, "bold"),
                corner_radius=0,
                command=lambda k=key: self._switch_tab(k))
            b.pack(side="left")
            self._tab_btns[key] = b

        self._content = ctk.CTkFrame(main, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._pages = {}
        self._pages["rapido"]     = self._build_page_rapido(self._content)
        self._pages["tour"]       = self._build_page_tour(self._content)
        self._pages["noturno"]    = self._build_page_noturno(self._content)
        self._pages["resultados"] = self._build_page_resultados(self._content)

        self._switch_tab("rapido")

    def _switch_tab(self, key):
        for k, p in self._pages.items():
            p.grid_remove()
        self._pages[key].grid(row=0, column=0, sticky="nsew")
        for k, b in self._tab_btns.items():
            b.configure(
                text_color="#FFFFFF" if k == key else "#9CA3AF",
                fg_color="#1E2128"   if k == key else "transparent")
        self._active_tab.set(key)

    # ── Page: Treino Rápido ─────────────────────────────────────────────────

    def _build_page_rapido(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure((0, 1, 2), weight=1)

        top = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        top.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(top, text="⚡  Treino Rápido — um algoritmo, um cenário",
                     font=("Roboto", 15, "bold"), text_color="#FFFFFF"
                     ).pack(anchor="w", padx=20, pady=(14, 2))
        self.lbl_rapido_hint = ctk.CTkLabel(
            top, text="Treina o algoritmo escolhido no cenário selecionado na barra lateral. "
                      "Ideal para testar rapidamente um caso específico.",
            font=("Roboto", 12), text_color="#6B7280")
        self.lbl_rapido_hint.pack(anchor="w", padx=20, pady=(0, 10))

        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(anchor="w", padx=20, pady=(0, 14))
        ctk.CTkLabel(inner, text="⏱  Tempo máx. (min):",
                     font=("Roboto", 13), text_color="#D1D5DB").pack(side="left", padx=(0, 10))
        self.e_time = ctk.CTkEntry(inner, width=80, height=32, font=("Roboto", 13),
                                   fg_color="#2A2D35", border_color="#3A3F4C")
        self.e_time.insert(0, "480")
        self.e_time.pack(side="left")

        for col, (algo, meta) in enumerate(ALGO_META.items()):
            self._build_algo_card(page, algo, meta, col)

        return page

    def _build_algo_card(self, parent, algo, meta, col):
        card = ctk.CTkFrame(parent, fg_color="#1E2128", corner_radius=12,
                            border_width=1, border_color="#2A2D35")
        card.grid(row=1, column=col, sticky="nsew", padx=6)
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="#13151A", corner_radius=10, height=60)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text=f"{meta['icon']}  {meta['label']}",
                     font=("Roboto", 16, "bold"), text_color=meta["color"]
                     ).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        lbl_st = ctk.CTkLabel(info, text="● PARADO",
                               font=("Consolas", 12), text_color="#6B7280")
        lbl_st.pack()
        lbl_tm = ctk.CTkLabel(info, text="00:00:00",
                               font=("Consolas", 20, "bold"), text_color="#D1D5DB")
        lbl_tm.pack()

        metric_box = ctk.CTkFrame(card, fg_color="#13151A", corner_radius=8)
        metric_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        lbl_metric = ctk.CTkLabel(metric_box, text="—",
                                   font=("Consolas", 22, "bold"), text_color=meta["color"])
        lbl_metric.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(metric_box, text="FITNESS" if algo == "GNN" else "EP REWARD",
                     font=("Roboto", 10), text_color="#4B5563"
                     ).place(relx=0.5, rely=0.72, anchor="center")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 14))
        primary_btn(btns, f"▶  Treinar só {algo}",
                    lambda a=algo: self._start_one(a),
                    color=meta["color"], height=38).pack(fill="x", pady=3)
        ghost_btn(btns, "⏹  Parar",
                  lambda a=algo: self._stop_one(a),
                  color="#F44336", height=32).pack(fill="x", pady=2)

        setattr(self, f"lbl_{algo}_status", lbl_st)
        setattr(self, f"lbl_{algo}_timer",  lbl_tm)
        setattr(self, f"lbl_{algo}_metric", lbl_metric)

    # ── Page: Tour de Mapas ─────────────────────────────────────────────────

    def _build_page_tour(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(hdr, text="🗺  Tour de Mapas — Treinar um Algoritmo em Todos os Cenários",
                     font=("Roboto", 15, "bold"), text_color="#FFFFFF"
                     ).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(hdr, text="Corre o algoritmo escolhido sequencialmente em cada um dos 6 cenários.",
                     font=("Roboto", 12), text_color="#6B7280"
                     ).pack(pady=(0, 14), padx=20, anchor="w")

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="CONFIGURAÇÃO DO TOUR",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

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
                font=("Roboto", 12, "bold"), corner_radius=8,
                command=lambda a=algo: self._select_tour_algo(a))
            b.pack(side="left", padx=3)
            self._tour_algo_btns[algo] = b

        params = ctk.CTkFrame(left, fg_color="transparent")
        params.pack(fill="x", padx=16)
        self.e_tour_runs = labeled_entry(params, "Runs por cenário:", 3)
        self.e_tour_time = labeled_entry(params, "Minutos por run:", 20)

        self.lbl_tour_est = ctk.CTkLabel(
            left, text="", font=("Roboto", 11, "italic"), text_color="#6B7280")
        self.lbl_tour_est.pack(padx=16, pady=(8, 0))
        self.e_tour_runs.bind("<KeyRelease>", self._update_tour_est)
        self.e_tour_time.bind("<KeyRelease>", self._update_tour_est)

        ctk.CTkFrame(left, height=1, fg_color="#2A2D35").pack(fill="x", padx=16, pady=16)
        primary_btn(left, "🚀  INICIAR TOUR",
                    self._start_tour, color="#7C3AED", height=44
                    ).pack(padx=16, pady=4, fill="x")
        ghost_btn(left, "⏹  Cancelar Tour",
                  self._stop_tour, color="#F44336", height=36
                  ).pack(padx=16, pady=(4, 16), fill="x")

        right = ctk.CTkFrame(body, fg_color="#1E2128", corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="PROGRESSO DO TOUR",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=16, pady=(16, 8))

        sr = ctk.CTkFrame(right, fg_color="#13151A", corner_radius=8)
        sr.pack(fill="x", padx=16, pady=(0, 12))
        self.lbl_tour_status = ctk.CTkLabel(
            sr, text="● INATIVO", font=("Consolas", 13), text_color="#6B7280")
        self.lbl_tour_status.pack(side="left", padx=16, pady=10)
        self.lbl_tour_timer = ctk.CTkLabel(
            sr, text="00:00:00", font=("Consolas", 18, "bold"), text_color="#D1D5DB")
        self.lbl_tour_timer.pack(side="right", padx=16, pady=10)

        ctk.CTkLabel(right, text="Cenários incluídos:",
                     font=("Roboto", 12), text_color="#9CA3AF"
                     ).pack(anchor="w", padx=16, pady=(4, 6))

        self.tour_scenario_checks = {}
        self.tour_scenario_status = {}
        for label, key in SCENARIOS:
            row = ctk.CTkFrame(right, fg_color="#13151A", corner_radius=6)
            row.pack(fill="x", padx=16, pady=2)
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(row, text="", variable=var, width=24,
                            checkbox_width=18, checkbox_height=18,
                            fg_color="#7C3AED", hover_color="#6D28D9"
                            ).pack(side="left", padx=(8, 4), pady=8)
            ctk.CTkLabel(row, text=label, font=("Roboto", 12),
                         text_color="#D1D5DB").pack(side="left", pady=8)
            lbl_s = ctk.CTkLabel(row, text="", font=("Consolas", 11), text_color="#6B7280")
            lbl_s.pack(side="right", padx=12, pady=8)
            self.tour_scenario_checks[key] = var
            self.tour_scenario_status[key] = lbl_s

        self._update_tour_est()
        return page

    def _select_tour_algo(self, algo):
        self.tour_algo_var.set(algo)
        for a, b in self._tour_algo_btns.items():
            meta = ALGO_META[a]
            b.configure(
                fg_color=meta["color"] if a == algo else "#2A2D35",
                text_color="#FFFFFF"   if a == algo else "#9CA3AF")
        self._update_tour_est()

    def _update_tour_est(self, event=None):
        try:
            runs     = int(self.e_tour_runs.get())
            mins     = int(self.e_tour_time.get())
            selected = sum(1 for v in self.tour_scenario_checks.values() if v.get())
            total_mins = runs * mins * selected
            h, m = divmod(total_mins, 60)
            self.lbl_tour_est.configure(
                text=f"Duração estimada: {h}h {m}m  ({runs * selected} runs no total)")
        except (ValueError, AttributeError):
            pass

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
                     text="Nota: corre em background; o terminal mostra o progresso.\n"
                          "O GNN (evolutivo) recebe ~1.4× mais tempo por run que\n"
                          "o PPO/SAC. Os dados fazem merge — podes interromper e\n"
                          "retomar sem perder os algoritmos já treinados.",
                     font=("Roboto", 11, "italic"), text_color="#6B7280",
                     justify="left").pack(padx=16, pady=(12, 0), anchor="w")

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

    # Pesos de tempo por algoritmo. O SAC (off-policy) converge rápido; o PPO
    # (on-policy) e o GNN (evolutivo) precisam de mais tempo por run.
    PPO_TIME_WEIGHT = 1.4
    GNN_TIME_WEIGHT = 1.4
    SAC_TIME_WEIGHT = 1.0

    def _update_night_est(self, event=None):
        try:
            horas = float(self.e_night_hours.get())
            runs  = int(self.e_night_runs.get())
            total = 6 * 3 * runs
            # Distribuição ponderada por cada 6 cenários × runs
            w_sum = self.PPO_TIME_WEIGHT + self.SAC_TIME_WEIGHT + self.GNN_TIME_WEIGHT
            weighted_slots = 6 * runs * w_sum
            min_base = max(1, int(horas * 60 / weighted_slots))
            min_sac  = max(1, int(min_base * self.SAC_TIME_WEIGHT))
            min_ppo  = max(1, int(min_base * self.PPO_TIME_WEIGHT))
            min_gnn  = max(1, int(min_base * self.GNN_TIME_WEIGHT))
            self.lbl_night_est.configure(
                text=f"SAC ~{min_sac} min  ·  PPO ~{min_ppo} min  ·  GNN ~{min_gnn} min  ·  "
                     f"{total} runs  ·  {horas}h")
        except (ValueError, AttributeError):
            pass

    # ── Page: Resultados ────────────────────────────────────────────────────

    def _build_page_resultados(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(1, weight=1)

        # ── Top action bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(pady=10, padx=16, fill="x")

        ctk.CTkLabel(inner, text="VISUALIZAÇÃO 3D:",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(side="left", padx=(0, 8))
        for algo, meta in ALGO_META.items():
            primary_btn(inner, f"{meta['icon']} {algo}",
                        lambda a=algo: self._viz(a),
                        color=meta["color"], height=34
                        ).pack(side="left", padx=3)

        ctk.CTkFrame(inner, width=1, height=36, fg_color="#3A3F4C").pack(side="left", padx=14)
        primary_btn(inner, "📊  Gerar Gráficos",
                    self._plot_thesis, color="#0D7377", height=34
                    ).pack(side="left", padx=3)
        primary_btn(inner, "🔄  Recarregar Sessões",
                    self._refresh_sessions, color="#374151", height=34
                    ).pack(side="left", padx=3)

        # ── Left: session list + graph selector ────────────────────────────
        self._left_scroll = ctk.CTkScrollableFrame(
            page, width=268, fg_color="#1E2128", corner_radius=10,
            scrollbar_button_color="#2A2D35", scrollbar_button_hover_color="#3A3F4C")
        self._left_scroll.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self._populate_session_list()
        self._populate_graph_list()

        # ── Right: image viewer ─────────────────────────────────────────────
        self._img_frame = ctk.CTkFrame(page, fg_color="#1E2128", corner_radius=10)
        self._img_frame.grid(row=1, column=1, sticky="nsew")
        self._img_frame.grid_rowconfigure(0, weight=1)
        self._img_frame.grid_columnconfigure(0, weight=1)

        # Placeholder
        self._img_placeholder = ctk.CTkLabel(
            self._img_frame,
            text="📈\n\nSeleciona uma sessão e um gráfico.",
            font=("Roboto", 16), text_color="#374151")
        self._img_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Image label (hidden until used)
        self._img_label = ctk.CTkLabel(self._img_frame, text="", image=None)
        self._img_label.place(relx=0.5, rely=0.46, anchor="center")

        # Description panel (bottom strip)
        self._desc_panel = ctk.CTkFrame(
            self._img_frame, fg_color="#13151A", corner_radius=8, height=72)
        self._desc_panel.place(relx=0.01, rely=0.97, anchor="sw",
                               relwidth=0.98)
        self._desc_panel.grid_propagate(False)
        self._desc_panel.grid_columnconfigure(0, weight=1)

        self._desc_title = ctk.CTkLabel(
            self._desc_panel, text="",
            font=("Roboto", 12, "bold"), text_color="#D1D5DB",
            anchor="w", justify="left")
        self._desc_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(6, 0))

        self._desc_body = ctk.CTkLabel(
            self._desc_panel, text="",
            font=("Roboto", 10), text_color="#6B7280",
            anchor="w", justify="left", wraplength=860)
        self._desc_body.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 6))

        # Caption (filename)
        self._img_caption = ctk.CTkLabel(
            self._img_frame, text="",
            font=("Roboto", 9, "italic"), text_color="#374151")
        self._img_caption.place(relx=0.99, rely=0.005, anchor="ne")

        # Auto-load most recent session
        sessions = self._discover_sessions()
        if sessions:
            first_label, first_path = sessions[0]
            self._select_session(first_label, first_path, update_list=False)
            self.after(300, lambda: self._show_graph("comparacao_barras_geral.png"))

        return page

    def _populate_session_list(self):
        scroll = self._left_scroll

        # Header + refresh label
        hdr_row = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr_row.pack(fill="x", padx=4, pady=(12, 4))
        ctk.CTkLabel(hdr_row, text="SESSÃO DE TREINO",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(side="left", padx=8)

        sessions = self._discover_sessions()
        self._session_btns.clear()
        self._session_dir_map.clear()

        if not sessions:
            ctk.CTkLabel(scroll, text="Nenhuma sessão encontrada.\nGera gráficos primeiro.",
                         font=("Roboto", 11, "italic"), text_color="#4B5563",
                         justify="center").pack(pady=12)
            return

        for sess_label, sess_path in sessions:
            is_first = (sess_label == sessions[0][0])
            b = ctk.CTkButton(
                scroll, text=f"  {sess_label}",
                anchor="w", height=32,
                fg_color="#374151" if is_first else "#2A2D35",
                hover_color="#374151",
                text_color="#FFFFFF" if is_first else "#9CA3AF",
                font=("Consolas", 10), corner_radius=6,
                command=lambda sl=sess_label, sp=sess_path: self._select_session(sl, sp))
            b.pack(fill="x", padx=6, pady=1)
            self._session_btns[sess_label] = b
            self._session_dir_map[sess_label] = sess_path

    def _populate_graph_list(self):
        scroll = self._left_scroll
        ctk.CTkFrame(scroll, height=1, fg_color="#2A2D35").pack(fill="x", padx=8, pady=(12, 6))
        ctk.CTkLabel(scroll, text="TIPO DE GRÁFICO",
                     font=("Roboto", 11, "bold"), text_color="#6B7280"
                     ).pack(anchor="w", padx=12, pady=(0, 4))

        self._graph_btns.clear()
        for cat_label, items in GRAPH_CATEGORIES:
            ctk.CTkLabel(scroll, text=cat_label,
                         font=("Roboto", 10, "bold"), text_color="#4B5563"
                         ).pack(anchor="w", padx=12, pady=(10, 2))
            for item_label, filename in items:
                b = ctk.CTkButton(
                    scroll, text=f"   {item_label}",
                    anchor="w", height=28,
                    fg_color="transparent", hover_color="#2A2D35",
                    text_color="#9CA3AF", font=("Roboto", 11),
                    corner_radius=6,
                    command=lambda fn=filename: self._show_graph(fn))
                b.pack(fill="x", padx=6, pady=1)
                self._graph_btns[filename] = b

        ctk.CTkFrame(scroll, height=16, fg_color="transparent").pack()

    def _discover_sessions(self):
        from datetime import datetime

        def _parse_date(d):
            for fmt in ("%d-%m-%Y_%Hh%Mm", "%Y-%m-%d_%H%M%S"):
                try:
                    return datetime.strptime(d, fmt)
                except ValueError:
                    continue
            return datetime.min   # pastas sem data vão para o fundo

        base = os.path.join(self.base_dir, "results", "graficos_tese")
        sessions = []
        if not os.path.exists(base):
            return sessions

        dirs = [d for d in os.listdir(base)
                if d != "estatisticas"
                and os.path.isdir(os.path.join(base, d))]
        # Ordena por data real (mais recente primeiro)
        for d in sorted(dirs, key=_parse_date, reverse=True):
            path = os.path.join(base, d)
            if [f for f in os.listdir(path) if f.endswith(".png")]:
                sessions.append((d, path))

        est_dir = os.path.join(base, "estatisticas")
        if os.path.exists(est_dir):
            est_dirs = [d for d in os.listdir(est_dir)
                        if os.path.isdir(os.path.join(est_dir, d))]
            for d in sorted(est_dirs, key=_parse_date, reverse=True):
                path = os.path.join(est_dir, d)
                if [f for f in os.listdir(path) if f.endswith(".png")]:
                    sessions.append((f"[stats] {d}", path))

        return sessions

    def _refresh_sessions(self):
        for widget in self._left_scroll.winfo_children():
            widget.destroy()
        self._populate_session_list()
        self._populate_graph_list()

    def _select_session(self, label, path, update_list=True):
        self._current_session_path = path
        if update_list:
            for lbl, btn in self._session_btns.items():
                btn.configure(
                    fg_color="#374151" if lbl == label else "#2A2D35",
                    text_color="#FFFFFF" if lbl == label else "#9CA3AF")
        # Re-show current graph in new session if one was active
        if self._active_graph_btn and self._active_graph_btn in self._graph_btns:
            self._show_graph(self._active_graph_btn)

    def _show_graph(self, filename):
        self._active_graph_btn = filename

        # Highlight active graph button
        for fn, btn in self._graph_btns.items():
            btn.configure(
                fg_color="#2A2D35"   if fn == filename else "transparent",
                text_color="#FFFFFF" if fn == filename else "#9CA3AF")

        if not self._current_session_path:
            return

        # Try primary filename then fallbacks
        candidates = [filename] + GRAPH_FALLBACKS.get(filename, [])
        path = None
        for c in candidates:
            p = os.path.join(self._current_session_path, c)
            if os.path.exists(p):
                path = p
                break

        if path is None:
            self._img_placeholder.configure(
                text=f"📭\n\nGráfico não disponível nesta sessão:\n{filename}",
                text_color="#4B5563")
            self._img_placeholder.lift()
            self._img_label.configure(image=None, text="")
            self._img_caption.configure(text="")
            return

        # Show descriptiono que
        desc_info = GRAPH_DESCRIPTIONS.get(filename)
        if not desc_info:
            # Try to match via fallback names
            for fn, alts in GRAPH_FALLBACKS.items():
                if filename in alts:
                    desc_info = GRAPH_DESCRIPTIONS.get(fn)
                    break
        if desc_info:
            self._desc_title.configure(text=desc_info[0])
            self._desc_body.configure(text=desc_info[1])
            self._desc_panel.configure(height=72)
        else:
            self._desc_title.configure(text="")
            self._desc_body.configure(text="")
            self._desc_panel.configure(height=0)

        if not PIL_AVAILABLE:
            self._img_placeholder.configure(
                text="⚠️  Pillow não instalado.\n\nInstala com:  pip install pillow",
                text_color="#F59E0B")
            self._img_placeholder.lift()
            return

        try:
            pil_img = Image.open(path).convert("RGBA")

            fw = self._img_frame.winfo_width()  - 40
            # Reserve space for description panel (~80px) and caption
            desc_h  = 80 if desc_info else 20
            fh = self._img_frame.winfo_height() - desc_h - 40
            if fw < 200: fw = 880
            if fh < 200: fh = 500

            iw, ih = pil_img.size
            scale   = min(fw / iw, fh / ih, 1.0)
            new_w   = max(1, int(iw * scale))
            new_h   = max(1, int(ih * scale))
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

            ctk_img = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
            self._current_img_ref = ctk_img  # prevent GC

            self._img_placeholder.lower()
            # Position image above the description panel
            rely = 0.44 if desc_info else 0.5
            self._img_label.place(relx=0.5, rely=rely, anchor="center")
            self._img_label.configure(image=ctk_img, text="")
            self._img_caption.configure(text=os.path.basename(path))
        except Exception as e:
            self._img_placeholder.configure(
                text=f"⚠️  Erro ao carregar imagem:\n{e}", text_color="#F59E0B")
            self._img_placeholder.lift()

    # ── Config helpers ───────────────────────────────────────────────────────

    def _get_paths(self):
        b = self.base_dir
        return {
            "gnn_log": os.path.join(b, "results/logs/gnn_3d_training.csv"),
            "ppo_log": os.path.join(b, "results/logs_ppo/training_history_ppo_3d.csv"),
            "sac_log": os.path.join(b, "results/logs_sac/training_history_sac_3d.csv"),
            "GNN":     "src/training/evo_trainer_3d.py",
            "PPO":     "src/training/train_ppo_3d.py",
            "SAC":     "src/training/train_sac_3d.py",
            "viz_GNN": "visualization/visualize_gnn.py",
            "viz_PPO": "visualization/visualize_ppo.py",
            "viz_SAC": "visualization/visualize_sac.py",
            "plot":    "scripts/plot_results.py",
            "run_exp": "scripts/run_experiments.py",
            "eval":    "scripts/eval_all.py",
            "render_maps": "scripts/render_maps.py",
            "heatmaps": "scripts/heatmaps.py",
        }

    def _run_script(self, script, args=None, console=True):
        full  = os.path.join(self.base_dir, script)
        flags = (subprocess.CREATE_NEW_CONSOLE if console
                 else subprocess.CREATE_NO_WINDOW)
        return subprocess.Popen(
            [sys.executable, full] + (args or []), creationflags=flags)

    def _load_config(self):
        try:
            with open(self.config_path) as f:
                cfg = yaml.safe_load(f)
            env = cfg.get("environment", {})
            self.e_drones.delete(0, "end"); self.e_drones.insert(0, str(env.get("num_agents", 20)))
            self.e_obs.delete(0, "end");    self.e_obs.insert(0, str(env.get("num_obstacles", 50)))
            self.e_radius.delete(0, "end"); self.e_radius.insert(0, str(env.get("arena_radius", 15.0)))
            sc    = env.get("classic_scenario", "none")
            label = next((s[0] for s in SCENARIOS if s[1] == sc), SCENARIO_LABELS[0])
            self.combo_scenario.set(label)
        except Exception:
            pass

    def _save_config(self):
        try:
            with open(self.config_path) as f:
                cfg = yaml.safe_load(f)
            cfg["environment"]["num_agents"]       = int(self.e_drones.get())
            cfg["environment"]["num_obstacles"]    = int(self.e_obs.get())
            cfg["environment"]["arena_radius"]     = float(self.e_radius.get())
            cfg["environment"]["classic_scenario"] = SCENARIO_KEYS[self.combo_scenario.get()]
            with open(self.config_path, "w") as f:
                yaml.dump(cfg, f)
        except Exception as e:
            print(f"[!] Erro a guardar config: {e}")

    def _on_scenario_change(self, _=None):
        self._save_config()

    # ── Training actions ─────────────────────────────────────────────────────

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
        ALGO_META[algo]  # just reference
        getattr(self, f"lbl_{algo}_status").configure(
            text="● A TREINAR...", text_color=ALGO_META[algo]["color"])

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
        selected = [k for k, v in self.tour_scenario_checks.items() if v.get()]
        if not selected:
            return
        for k, lbl in self.tour_scenario_status.items():
            lbl.configure(text="⏳" if k in selected else "", text_color="#6B7280")
        self.tour_process = self._run_tour_process(algo, selected, runs, mins)
        self.tour_start   = time.time()
        self.lbl_tour_status.configure(
            text=f"● A CORRER — {algo}", text_color=ALGO_META[algo]["color"])

    def _run_tour_process(self, algo, scenarios, runs, time_limit):
        return subprocess.Popen(
            [sys.executable,
             os.path.join(self.base_dir, self._get_paths()["run_exp"]),
             "--runs", str(runs),
             "--time", str(time_limit),
             "--algo", algo,
             "--scenarios", ",".join(scenarios)],
            creationflags=subprocess.CREATE_NEW_CONSOLE)

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
            w_sum = self.PPO_TIME_WEIGHT + self.SAC_TIME_WEIGHT + self.GNN_TIME_WEIGHT
            weighted_slots = 6 * runs * w_sum
            min_base = max(1, int(horas * 60 / weighted_slots))
            min_sac  = max(1, int(min_base * self.SAC_TIME_WEIGHT))
            min_ppo  = max(1, int(min_base * self.PPO_TIME_WEIGHT))
            min_gnn  = max(1, int(min_base * self.GNN_TIME_WEIGHT))
        except ValueError:
            return
        self._run_script(self._get_paths()["run_exp"],
                         ["--runs", str(runs), "--time", str(min_sac),
                          "--time-ppo", str(min_ppo), "--time-gnn", str(min_gnn)])
        self.btn_night.configure(text="✔  Rotina Iniciada (background)", fg_color="#065F46")
        self.after(4000, lambda: self.btn_night.configure(
            text="🚀  INICIAR ROTINA NOTURNA", fg_color="#D97706"))

    # ── Viz / Plot / Eval ────────────────────────────────────────────────────

    def _viz(self, algo):
        self._save_config()
        self._run_script(self._get_paths()[f"viz_{algo}"], console=False)

    def _plot_thesis(self):
        self._run_script(self._get_paths()["plot"])

    def _render_maps(self):
        # Gera as duas vistas (isométrica + topo) dos 6 mapas e abre a pasta no fim.
        self._run_script(self._get_paths()["render_maps"], ["--camera", "both", "--open"])

    def _render_heatmaps(self):
        # Gera todos os heatmaps (ocupação + geodésico) e abre a pasta. Lento
        # (corre os modelos), por isso está separado do "Gerar Gráficos".
        self._save_config()
        self._run_script(self._get_paths()["heatmaps"], ["--mode", "all", "--open"])

    def _eval_model(self):
        self._save_config()
        try:
            with open(self.config_path) as f:
                cfg = yaml.safe_load(f)
            scenario = cfg["environment"].get("classic_scenario", "none")
        except Exception:
            scenario = "none"
        self._run_script(self._get_paths()["eval"],
                         ["--episodes", "20", "--scenario", scenario])

    # ── Tick ─────────────────────────────────────────────────────────────────

    def _tick(self):
        self._update_algo_metrics()
        self._update_timers()
        self.after(1000, self._tick)

    def _update_algo_metrics(self):
        p = self._get_paths()
        for algo, log, col in [
            ("GNN", p["gnn_log"], "best_fitness"),
            ("PPO", p["ppo_log"], "ep_rew_mean"),
            ("SAC", p["sac_log"], "ep_rew_mean"),
        ]:
            if not os.path.exists(log):
                continue
            try:
                df = pd.read_csv(log).dropna()
                if not df.empty and col in df.columns:
                    getattr(self, f"lbl_{algo}_metric").configure(
                        text=f"{df.iloc[-1][col]:.1f}")
            except Exception:
                pass

    def _update_timers(self):
        for algo in ("GNN", "PPO", "SAC"):
            t0   = self.t_start[algo]
            proc = self.procs[algo]
            if t0 and proc:
                if proc.poll() is not None:
                    self.procs[algo]   = None
                    self.t_start[algo] = None
                    getattr(self, f"lbl_{algo}_status").configure(
                        text="● CONCLUÍDO", text_color="#00C896")
                else:
                    elapsed = str(timedelta(seconds=int(time.time() - t0)))
                    getattr(self, f"lbl_{algo}_timer").configure(text=elapsed)

        if self.tour_start and self.tour_process:
            if self.tour_process.poll() is not None:
                self.tour_process = None
                self.tour_start   = None
                self.lbl_tour_status.configure(text="● CONCLUÍDO", text_color="#00C896")
            else:
                elapsed = str(timedelta(seconds=int(time.time() - self.tour_start)))
                self.lbl_tour_timer.configure(text=elapsed)


if __name__ == "__main__":
    app = SwarmController()
    app.mainloop()
