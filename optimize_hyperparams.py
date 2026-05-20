import optuna
import subprocess
import pandas as pd
import os
import yaml

# --- CONFIGURAÇÕES DA OTIMIZAÇÃO ---
N_TRIALS = 50  # Número de combinações de hiperparâmetros a testar
TIMEOUT_PER_TRIAL = 600  # Segundos (10 minutos) por trial
OPTIMIZE_ALGO = "PPO" # Mudar para "SAC" para otimizar o SAC

def objective(trial):
    """
    Função que o Optuna vai tentar maximizar.
    """
    # 1. Sugerir Hiperparâmetros
    if OPTIMIZE_ALGO == "PPO":
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
        n_steps = trial.suggest_categorical("n_steps", [512, 1024, 2048, 4096])
        gamma = trial.suggest_float("gamma", 0.9, 0.9999, log=True)
        gae_lambda = trial.suggest_float("gae_lambda", 0.8, 0.99)
        clip_range = trial.suggest_categorical("clip_range", [0.1, 0.2, 0.3])
        icm_lr = trial.suggest_float("icm_learning_rate", 1e-5, 1e-3, log=True)
        icm_beta = trial.suggest_float("icm_beta", 0.1, 0.3)
        intrinsic_weight = trial.suggest_float("intrinsic_reward_weight", 1e-3, 1e-1, log=True)

        script_path = "src/training/train_ppo_3d.py"
        cmd = [
            "python", script_path,
            "--time_limit", str(TIMEOUT_PER_TRIAL / 60),
            "--learning_rate", str(learning_rate),
            "--n_steps", str(n_steps),
            "--gamma", str(gamma),
            "--gae_lambda", str(gae_lambda),
            "--clip_range", str(clip_range),
            "--icm_learning_rate", str(icm_lr),
            "--icm_beta", str(icm_beta),
            "--intrinsic_reward_weight", str(intrinsic_weight)
        ]
    elif OPTIMIZE_ALGO == "SAC":
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
        buffer_size = trial.suggest_categorical("buffer_size", [100000, 500000, 1000000])
        gamma = trial.suggest_float("gamma", 0.9, 0.9999, log=True)
        tau = trial.suggest_float("tau", 0.001, 0.02)
        train_freq = trial.suggest_categorical("train_freq", [1, 4, 8, 16])
        gradient_steps = trial.suggest_int("gradient_steps", 1, 5)
        icm_lr = trial.suggest_float("icm_learning_rate", 1e-5, 1e-3, log=True)
        icm_beta = trial.suggest_float("icm_beta", 0.1, 0.3)
        intrinsic_weight = trial.suggest_float("intrinsic_reward_weight", 1e-3, 1e-1, log=True)

        script_path = "src/training/train_sac_3d.py"
        cmd = [
            "python", script_path,
            "--time_limit", str(TIMEOUT_PER_TRIAL / 60),
            "--learning_rate", str(learning_rate),
            "--buffer_size", str(buffer_size),
            "--gamma", str(gamma),
            "--tau", str(tau),
            "--train_freq", str(train_freq),
            "--gradient_steps", str(gradient_steps),
            "--icm_learning_rate", str(icm_lr),
            "--icm_beta", str(icm_beta),
            "--intrinsic_reward_weight", str(intrinsic_weight)
        ]
    else:
        raise ValueError("OPTIMIZE_ALGO deve ser 'PPO' ou 'SAC'")

    # 2. Executar o Treino "Miniatura"
    print(f"\n--- Trial {trial.number}: A testar {OPTIMIZE_ALGO} com {trial.params} ---")
    subprocess.run(cmd, check=True)

    # 3. Ler o Resultado
    log_file = "results/logs_ppo/training_history_ppo_3d.csv" if OPTIMIZE_ALGO == "PPO" else "results/logs_ppo/training_history_sac_3d.csv"
    try:
        df = pd.read_csv(log_file)
        # Usar a média das últimas 5 recompensas para um resultado mais estável
        last_rewards = df['ep_rew_mean'].dropna().tail(5)
        if last_rewards.empty:
            return -1e6 # Penalizar se não houver recompensas
        final_performance = last_rewards.mean()
    except (FileNotFoundError, pd.errors.EmptyDataError):
        final_performance = -1e6 # Penalizar se o ficheiro não for criado ou estiver vazio

    print(f"--- Trial {trial.number} concluído. Performance: {final_performance:.2f} ---")
    
    return final_performance

if __name__ == "__main__":
    # Configurar o cenário de teste (ex: labirinto, que é um bom teste de exploração)
    config_path = 'configs/foraging.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config['environment']['classic_scenario'] = 'four_rooms'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    print(f"[*] Cenário de otimização definido para: 'four_rooms'")

    # Criar o estudo Optuna
    study = optuna.create_study(direction="maximize")
    
    try:
        study.optimize(objective, n_trials=N_TRIALS, timeout=N_TRIALS * (TIMEOUT_PER_TRIAL + 60))
    except KeyboardInterrupt:
        print("Otimização interrompida pelo utilizador.")

    # Apresentar os resultados
    print("\n======================================================")
    print("               OTIMIZAÇÃO CONCLUÍDA               ")
    print("======================================================")
    print(f"Número de trials: {len(study.trials)}")
    print(f"Melhor trial:")
    trial = study.best_trial
    print(f"  Valor (Recompensa Média): {trial.value:.4f}")
    print("  Melhores Hiperparâmetros:")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # Sugestão para copiar para o config.yaml
    print("\n--- Sugestão para config.yaml ---")
    print(f"{OPTIMIZE_ALGO.lower()}:")
    for key, value in trial.params.items():
        print(f"  {key}: {value}")
    print("------------------------------------")