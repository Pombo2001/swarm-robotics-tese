import os
import sys
import yaml
import subprocess
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# CONFIGURAÇÕES BASE DO SCRIPT
# ==============================================================================
ALGORITHMS = {
    'GNN': 'src/training/evo_trainer_3d.py',
    'PPO': 'src/training/train_ppo_3d.py',
    'SAC': 'src/training/train_sac_3d.py'
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_PATH = os.path.join(BASE_DIR, 'configs', 'foraging.yaml')

# Raiz do projeto no sys.path para o import 'from scripts.eval_suite import ...'
# funcionar quando o script é corrido como 'python scripts/run_experiments.py'
# (senão a avaliação automática no fim do treino falha com ModuleNotFoundError).
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.scenarios import SCENARIOS  # lista canónica de cenários (treino + avaliação)

LOG_PATHS = {
    'GNN': os.path.join(BASE_DIR, 'results', 'logs', 'gnn_3d_training.csv'),
    'PPO': os.path.join(BASE_DIR, 'results', 'logs_ppo', 'training_history_ppo_3d.csv'),
    'SAC': os.path.join(BASE_DIR, 'results', 'logs_sac', 'training_history_sac_3d.csv')
}

SCORE_COLS = {
    'GNN': 'best_fitness',
    'PPO': 'ep_rew_mean',
    'SAC': 'ep_rew_mean'
}

STEP_COLS = {
    'GNN': 'timestep',
    'PPO': 'timesteps',
    'SAC': 'timesteps'
}

def set_scenario(scenario_name):
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        config['environment']['classic_scenario'] = scenario_name
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f)
        print(f"[*] Cenário configurado para: {scenario_name}")
    except Exception as e:
        print(f"[!] Erro ao configurar cenário: {e}")

# Backup/retoma: regista cada treino (cenário|algo|run) já concluído, para
# poder RETOMAR após um crash sem repetir o que já foi feito (treinos de dias).
PROGRESS_SESSION = os.path.join(BASE_DIR, 'results', 'logs', '_sessao_treino.txt')

# CSVs acumulados da campanha (curvas + melhor score por run). São gravados
# INCREMENTALMENTE após cada run — antes viviam em memória até ao fim, e um
# crash ao dia N de um treino longo perdia tudo (e o --resume, ao não reler os
# runs saltados, apagava-os do CSV final no merge por cenário/algoritmo).
STATS_DIR  = os.path.join(BASE_DIR, 'results', 'graficos_tese', 'estatisticas')
CURVES_CSV = os.path.join(STATS_DIR, 'all_curves_data.csv')
BEST_CSV   = os.path.join(STATS_DIR, 'all_best_scores.csv')

# Sentinela de CONCLUSÃO para o watchdog (launch_7d.sh). O exit code do
# processo não chega como sinal: bibliotecas nativas (ex. VTK headless nos
# mapas 3D) podem abortar o processo DEPOIS de todo o trabalho útil feito,
# e o watchdog relançava em loop uma campanha já completa (smoke de 2 jul).
DONE_SENTINEL = os.path.join(BASE_DIR, 'results', 'logs', '_campanha_concluida.txt')


def _load_done():
    if os.path.exists(PROGRESS_SESSION):
        with open(PROGRESS_SESSION, encoding='utf-8') as f:
            return set(l.strip() for l in f if l.strip())
    return set()


def _mark_done(key):
    os.makedirs(os.path.dirname(PROGRESS_SESSION), exist_ok=True)
    with open(PROGRESS_SESSION, 'a', encoding='utf-8') as f:
        f.write(key + '\n')


def run_experiments(num_runs, time_limit, algorithms=None, scenarios=None,
                    time_overrides=None, eval_episodes=20, resume=False):
    if algorithms is None:
        algorithms = ALGORITHMS
    if scenarios is None:
        scenarios = SCENARIOS
    if time_overrides is None:
        time_overrides = {}

    # Execução nova → a sentinela de conclusão da anterior deixa de valer.
    try:
        os.remove(DONE_SENTINEL)
    except OSError:
        pass

    # Retoma: se --resume, salta os treinos já concluídos; senão começa do zero.
    done = _load_done() if resume else set()
    if not resume and os.path.exists(PROGRESS_SESSION):
        try:
            os.remove(PROGRESS_SESSION)
        except Exception:
            pass

    print(f"Iniciando Automacao de Experiencias:")
    print(f"Runs: {num_runs} | Tempo base: {time_limit}m | Cenários: {len(scenarios)} | Algoritmos: {list(algorithms.keys())}")
    if time_overrides:
        print(f"Tempos especificos por algoritmo: {time_overrides}")
    if resume and done:
        print(f"[RETOMA] {len(done)} treinos já concluídos serão saltados.")

    for scenario in scenarios:
        set_scenario(scenario)

        for algo_name, algo_script in algorithms.items():
            script_path = os.path.join(BASE_DIR, algo_script)
            log_path = LOG_PATHS[algo_name]
            score_col = SCORE_COLS[algo_name]
            step_col = STEP_COLS[algo_name]
            algo_time = time_overrides.get(algo_name, time_limit)

            for run in range(1, num_runs + 1):
                key = f"{scenario}|{algo_name}|{run}"
                if key in done:
                    print(f"[SKIP] já concluído nesta sessão: {key}")
                    continue
                print(f"\n--- A EXECUTAR | Cenário: {scenario} | Algoritmo: {algo_name} | Run: {run}/{num_runs} | {algo_time}m ---")

                if os.path.exists(log_path):
                    try:
                        os.remove(log_path)
                    except Exception as e:
                        print(f"[!] Aviso: Nao foi possivel apagar o log antigo ({e})")

                # Seed = nº do run → runs reproduzíveis e distintos entre si.
                cmd = [sys.executable, script_path, '--time_limit', str(algo_time),
                       '--seed', str(run)]
                
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"[!] Run {run} do {algo_name} falhou: {e}")
                
                # Extração de dados do run + gravação IMEDIATA nos CSVs da
                # campanha (merge por Scenario/Algorithm/Run) — um crash mais
                # à frente não perde este run, e o --resume não o apaga.
                if os.path.exists(log_path):
                    try:
                        df = pd.read_csv(log_path)
                        df.columns = df.columns.str.strip()

                        if not df.empty and score_col in df.columns and step_col in df.columns:
                            max_score = df[score_col].max()

                            run_best = pd.DataFrame([{
                                'Scenario': scenario,
                                'Algorithm': algo_name,
                                'Run': run,
                                'BestScore': max_score
                            }])
                            run_curves = pd.DataFrame({
                                'Scenario': scenario,
                                'Algorithm': algo_name,
                                'Run': run,
                                'Step': df[step_col].values,
                                'Score': df[score_col].values,
                            })
                            os.makedirs(STATS_DIR, exist_ok=True)
                            _merge_save(run_curves, CURVES_CSV)
                            _merge_save(run_best, BEST_CSV)
                        else:
                            print(f"[!] Log vazio ou colunas nao encontradas para {algo_name} Run {run}.")
                    except Exception as e:
                        print(f"[!] Erro ao ler CSV do {algo_name} Run {run}: {e}")
                else:
                    print(f"[!] Ficheiro de log {log_path} nao encontrado apos a execucao.")

                _mark_done(key)   # treino concluído → retomável se houver crash

    generate_plots(scenarios, list(algorithms.keys()))

    # ── AVALIAÇÃO DETERMINÍSTICA no fim do treino ────────────────────────────
    # A rotina noturna treinava mas não avaliava, deixando os eval_*.csv (taxa de
    # sucesso, recolhas/ep — as métricas de TAREFA, comparáveis entre algoritmos)
    # desfasados dos modelos. Agora avalia automaticamente os 6 cenários sobre os
    # modelos acabados de treinar. eval_episodes=0 desliga este passo.
    if eval_episodes and eval_episodes > 0:
        print(f"\n--- A AVALIAR MODELOS (determinístico, {eval_episodes} ep/algo) ---")
        try:
            from scripts.eval_suite import evaluate_all
            evaluate_all(episodes=eval_episodes)  # scenarios=None => os 6 cenários
        except Exception as e:
            print(f"[!] Avaliação automática falhou (não crítico): {e}")

        # Avaliação POR RUN (modelos _run{n} preservados pelo fix da armadilha
        # nº8): gera eval_by_run.csv — boxplots de EVAL e testes estatísticos
        # com N runs por célula, em vez de scores de treino.
        try:
            from scripts.eval_by_run import evaluate_by_run
            evaluate_by_run(episodes=eval_episodes,
                            scenarios=scenarios,
                            algos=[a.lower() for a in algorithms.keys()])
        except Exception as e:
            print(f"[!] Avaliação por run falhou (não crítico): {e}")

    # RELATÓRIO COMPLETO automático: gráficos da tese + gráficos de avaliação +
    # heatmaps + mapas 3D, tudo numa pasta datada (results/graficos_tese/<sessao>/).
    # Assim, ao acabar de treinar, fica tudo gerado e organizado num só sítio.
    print("\n--- A GERAR RELATÓRIO COMPLETO (gráficos + heatmaps + mapas) ---")
    try:
        from scripts.plot_results import create_thesis_plots_3d
        create_thesis_plots_3d()
    except Exception as e:
        print(f"[!] Relatório não gerado (não crítico): {e}")

    # ── VÍDEOS dos episódios (GIF 2D top-down) ───────────────────────────────
    # Grava 1 GIF por (algoritmo × cenário) treinado, na pasta da sessão acabada
    # de gerar (results/graficos_tese/<sessao>/videos/). Robusto: falhas
    # individuais não abortam o conjunto. Desligar com SWARM_VIDEOS=0 (gera ~1
    # GIF por algo/cenário, alguns minutos no total).
    if os.environ.get("SWARM_VIDEOS", "1") != "0":
        print("\n--- A GRAVAR VÍDEOS DOS EPISÓDIOS (GIF 2D top-down) ---")
        try:
            from scripts.record_episode import generate_all, _latest_training_dir
            sess_dir = _latest_training_dir()
            if sess_dir:
                algos_lower = tuple(a.lower() for a in algorithms.keys())
                generate_all(sess_dir, algos=algos_lower, scenarios=scenarios)
            else:
                print("[!] Sem pasta de sessão para os vídeos.")
        except Exception as e:
            print(f"[!] Vídeos não gerados (não crítico): {e}")

    # Campanha completa → sentinela para o watchdog não relançar.
    os.makedirs(os.path.dirname(DONE_SENTINEL), exist_ok=True)
    with open(DONE_SENTINEL, 'w', encoding='utf-8') as f:
        f.write(str(pd.Timestamp.now()) + '\n')
    print("[OK] Campanha concluída — sentinela gravada para o watchdog.")

def _load_campaign(path, scenarios, algorithms):
    """Lê um CSV acumulado e devolve só as combinações desta campanha.
    Ler do disco (e não da memória) permite que os gráficos incluam runs
    feitos ANTES de um crash+--resume, que já lá estão gravados."""
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        return df[df['Scenario'].isin(scenarios) & df['Algorithm'].isin(algorithms)]
    except Exception as e:
        print(f"[!] Falha a ler {path} ({e}); gráficos sem esses dados.")
        return pd.DataFrame()


def generate_plots(scenarios, algorithms):
    print("\n--- A GERAR GRÁFICOS AVANÇADOS ---")
    out_dir = STATS_DIR
    os.makedirs(out_dir, exist_ok=True)

    df_curves = _load_campaign(CURVES_CSV, scenarios, algorithms)
    df_best   = _load_campaign(BEST_CSV, scenarios, algorithms)

    sns.set_theme(style="whitegrid")

    if not df_curves.empty:
        for scenario in df_curves['Scenario'].unique():
            plt.figure(figsize=(10, 6))
            data_scen = df_curves[df_curves['Scenario'] == scenario]
            sns.lineplot(data=data_scen, x='Step', y='Score', hue='Algorithm', errorbar='sd')
            plt.title(f'Curva de Aprendizagem - Cenário: {scenario.upper()}', fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f'curva_aprendizagem_{scenario}.png'), dpi=300)
            plt.close()

    if not df_best.empty:
        for scenario in df_best['Scenario'].unique():
            plt.figure(figsize=(8, 6))
            data_scen = df_best[df_best['Scenario'] == scenario]
            sns.boxplot(data=data_scen, x='Algorithm', y='BestScore', palette='Set2')
            plt.title(f'Distribuição de Melhores Scores - Cenário: {scenario.upper()}', fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f'boxplot_{scenario}.png'), dpi=300)
            plt.close()

        plt.figure(figsize=(12, 6))
        sns.barplot(data=df_best, x='Scenario', y='BestScore', hue='Algorithm', errorbar='sd', palette='Set2')
        plt.title('Comparação Geral de Desempenho por Cenário', fontweight='bold')
        plt.ylabel('Recompensa Média Final (Max Score)')
        plt.xlabel('Cenário')
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, 'comparacao_barras_geral.png'), dpi=300)
        plt.close()

    print(f"[*] Gráficos gerados com sucesso em: {out_dir} "
          f"(CSVs acumulados gravados run-a-run durante o treino)")


def _merge_save(df_new, path):
    """Substitui no CSV existente apenas as combinações presentes em df_new;
    mantém todas as outras intactas. A chave inclui o Run (quando existe nos
    dois lados) para que gravar um run NÃO apague os runs anteriores da mesma
    combinação — essencial na gravação incremental e na retoma pós-crash."""
    if df_new.empty:
        return
    if os.path.exists(path):
        try:
            df_old = pd.read_csv(path)
            keycols = ['Scenario', 'Algorithm']
            if 'Run' in df_new.columns and 'Run' in df_old.columns:
                keycols.append('Run')
            new_keys = set(zip(*(df_new[c] for c in keycols)))
            mask = df_old.apply(
                lambda r: tuple(r[c] for c in keycols) not in new_keys, axis=1)
            df_old_kept = df_old[mask]
            df_merged = pd.concat([df_old_kept, df_new], ignore_index=True)
        except Exception as e:
            print(f"[!] Falha no merge de {path} ({e}); a escrever só dados novos.")
            df_merged = df_new
    else:
        df_merged = df_new
    tmp = path + '.tmp'
    df_merged.to_csv(tmp, index=False)
    os.replace(tmp, path)   # escrita atómica: um crash a meio não corrompe o CSV

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automação de Experiências para a Tese")
    parser.add_argument("--runs",      type=int,   default=5,   help="Nº de Runs por Cenário")
    parser.add_argument("--time",      type=int,   default=60,  help="Minutos por Run (base)")
    parser.add_argument("--time-gnn",  type=int,   default=None,
                        help="Minutos por Run só para o GNN (override; evolutivo precisa de mais)")
    parser.add_argument("--time-ppo",  type=int,   default=None,
                        help="Minutos por Run só para o PPO (override; on-policy precisa de mais)")
    parser.add_argument("--algo",      type=str,   default=None,
                        help="Algoritmo único a correr (GNN, PPO ou SAC). Omitir = todos.")
    parser.add_argument("--scenarios", type=str,   default=None,
                        help="Cenários separados por vírgula. Omitir = todos.")
    parser.add_argument("--eval-episodes", type=int, default=20,
                        help="Episódios de avaliação no fim do treino (0 = não avaliar)")
    parser.add_argument("--resume", action="store_true",
                        help="Retomar: salta os treinos (cenário|algo|run) já concluídos "
                             "registados em results/logs/_sessao_treino.txt (útil após crash)")
    args = parser.parse_args()

    # Filter algorithms
    algos = ALGORITHMS
    if args.algo:
        key = args.algo.upper()
        if key in ALGORITHMS:
            algos = {key: ALGORITHMS[key]}
        else:
            print(f"[!] Algoritmo desconhecido: {args.algo}. Opções: {list(ALGORITHMS.keys())}")
            sys.exit(1)

    # Filter scenarios
    scenarios = SCENARIOS
    if args.scenarios:
        requested = [s.strip() for s in args.scenarios.split(",")]
        scenarios = [s for s in SCENARIOS if s in requested]
        unknown = [s for s in requested if s not in SCENARIOS]
        if unknown:
            print(f"[!] Cenários desconhecidos ignorados: {unknown}")

    overrides = {}
    if args.time_gnn is not None:
        overrides["GNN"] = args.time_gnn
    if args.time_ppo is not None:
        overrides["PPO"] = args.time_ppo

    run_experiments(num_runs=args.runs, time_limit=args.time,
                    algorithms=algos, scenarios=scenarios,
                    time_overrides=overrides, eval_episodes=args.eval_episodes,
                    resume=args.resume)