"""
eval_all.py — Avalia os 3 modelos (GNN, PPO, SAC) e mostra comparação.
Uso: python scripts/eval_all.py --episodes 20 --scenario none
"""
import argparse
import os
import sys
import numpy as np
import pandas as pd
import torch
import yaml

# Windows: evita UnicodeEncodeError (cp1252) ao imprimir caracteres de caixa.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D
from src.scenarios import SCENARIO_LABELS_SHORT as SCENARIO_LABELS


def load_model(algo, scenario, config_path):
    suffix = f"_{scenario}" if scenario and scenario != "none" else ""
    if algo == "gnn":
        from src.agents.gnn_agent_3d import GNNAgent3D
        env_tmp = SwarmForagingEnv3D(config_path=config_path)
        agent = GNNAgent3D("eval", env_tmp.action_space("robot_0"), config_path)
        for p in [f"results/models/gnn_3d_best{suffix}.pth",
                  "results/models/gnn_3d_best.pth"]:
            fp = os.path.join(PROJECT_ROOT, p)
            if os.path.exists(fp):
                try:
                    agent.load_state_dict(torch.load(fp, weights_only=True))
                except RuntimeError:
                    print(f"  [!] {os.path.basename(fp)} INCOMPATÍVEL com a observação/rede "
                          f"atuais (treinado antes da mudança B1/GNN). RETREINA. — saltado")
                    return None, None
                agent.eval()
                return agent, fp
        return None, None
    elif algo in ("ppo", "sac"):
        from stable_baselines3 import PPO, SAC
        cls = PPO if algo == "ppo" else SAC
        sub = "models_ppo" if algo == "ppo" else "models_sac"
        exp_obs = SwarmForagingEnv3D(config_path=config_path).observation_space_val.shape[0]
        for p in [f"results/{sub}/{algo}_3d_final{suffix}.zip",
                  f"results/{sub}/{algo}_3d_final.zip"]:
            fp = os.path.join(PROJECT_ROOT, p)
            if os.path.exists(fp):
                model = cls.load(fp)
                got = model.observation_space.shape[0]
                if got != exp_obs:
                    print(f"  [!] {os.path.basename(fp)} INCOMPATÍVEL: obs do modelo={got} "
                          f"vs atual={exp_obs} (treinado antes da mudança B1). RETREINA. — saltado")
                    return None, None
                return model, fp
        return None, None


def run_episode(env, algo, model, seed=None):
    obs_dict, _ = env.reset(seed=seed)
    total_reward = 0.0
    steps = 0
    while True:
        actions = {}
        if algo == "gnn":
            obs_list = [obs_dict[a] for a in env.agents]
            obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)
            with torch.no_grad():
                acts = model(obs_tensor).cpu().numpy()
            actions = {a: acts[i] for i, a in enumerate(env.agents)}
        else:
            for agent_id in env.agents:
                obs = np.array(obs_dict[agent_id], dtype=np.float32)
                action, _ = model.predict(obs, deterministic=True)
                actions[agent_id] = action
        obs_dict, rewards, terms, truncs, _ = env.step(actions)
        total_reward += sum(rewards.values())
        steps += 1
        if any(terms.values()) or any(truncs.values()):
            break
    food = int(env.total_food_collected)
    return {
        "food_collected": food,
        "task_reward":    food * env.food_collected_reward,
        "total_reward":   total_reward,
        "episode_length": steps,
        "success":        food > 0,
    }


def eval_algo(algo, scenario, config_path, n_episodes, seed_base=1000):
    model, path = load_model(algo, scenario, config_path)
    if model is None:
        print(f"  [{algo.upper()}] ERRO: modelo nao encontrado — a saltar")
        return None, None

    print(f"  [{algo.upper()}] {path}")
    env = SwarmForagingEnv3D(config_path=config_path)
    if scenario:
        env.config["environment"]["classic_scenario"] = scenario

    results = []
    for ep in range(n_episodes):
        # Mesma seed_base para todos os algoritmos => avaliacao emparelhada
        # (mesmos episodios), permitindo testes estatisticos pareados.
        r = run_episode(env, algo, model, seed=seed_base + ep)
        results.append(r)
        mark = "v" if r["success"] else "-"
        print(f"    ep {ep+1:2d} [{mark}] recolhas={r['food_collected']}  "
              f"task={r['task_reward']:+.0f}  total={r['total_reward']:+.0f}")

    return pd.DataFrame(results), path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--seed-base", type=int, default=1000,
                        help="Base das seeds (igual p/ os 3 algos = avaliacao emparelhada)")
    parser.add_argument("--no-pause", action="store_true",
                        help="Nao espera ENTER no fim (para correr em background/CI)")
    args = parser.parse_args()

    def _pause():
        # Nao bloquear se nao for interativo (sem TTY) ou se --no-pause.
        if args.no_pause or not sys.stdin.isatty():
            return
        input("\nPressiona ENTER para fechar...")

    config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    scenario = args.scenario or config["environment"].get("classic_scenario", "none")
    label    = SCENARIO_LABELS.get(scenario, scenario)

    print(f"\n{'='*62}")
    print(f"  AVALIACAO COMPLETA — {label}")
    print(f"  {args.episodes} episodios por algoritmo | modo deterministico")
    print(f"{'='*62}\n")

    summary = {}
    out_dir = os.path.join(PROJECT_ROOT, "results", "evaluation")
    os.makedirs(out_dir, exist_ok=True)

    for algo in ["gnn", "ppo", "sac"]:
        print(f"\n--- {algo.upper()} ---")
        df, path = eval_algo(algo, scenario, config_path, args.episodes, args.seed_base)
        if df is None:
            continue
        summary[algo.upper()] = {
            "Recolhas/ep":    f"{df.food_collected.mean():.2f} +/- {df.food_collected.std():.2f}",
            "Task reward":    f"{df.task_reward.mean():.0f} +/- {df.task_reward.std():.0f}",
            "Total reward":   f"{df.total_reward.mean():.0f} +/- {df.total_reward.std():.0f}",
            "Taxa sucesso":   f"{df.success.mean()*100:.0f}%  ({df.success.sum()}/{args.episodes})",
            "Passos medios":  f"{df.episode_length.mean():.1f}",
        }
        out_path = os.path.join(out_dir, f"eval_{algo}_{scenario}.csv")
        df.to_csv(out_path, index=False)

    if not summary:
        print("\nNenhum modelo encontrado. Treina primeiro.")
        _pause()
        return

    # ── Tabela de comparação ─────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  RESUMO COMPARATIVO — {label}  ({args.episodes} episodios)")
    print(f"{'='*62}")
    col_w = 22
    header = f"  {'Metrica':<20}" + "".join(f"  {a:>{col_w}}" for a in summary)
    print(header)
    print("  " + "-" * (len(header) - 2))
    metrics = ["Recolhas/ep", "Task reward", "Total reward", "Taxa sucesso", "Passos medios"]
    for m in metrics:
        row = f"  {m:<20}" + "".join(
            f"  {summary[a].get(m, 'N/A'):>{col_w}}" for a in summary)
        print(row)
    print(f"{'='*62}\n")

    out_all = os.path.join(out_dir, f"eval_comparacao_{scenario}.csv")
    pd.DataFrame(summary).T.to_csv(out_all)
    print(f"[OK] Comparacao guardada: {out_all}")
    print(f"[OK] CSVs individuais em: {out_dir}")

    _pause()


if __name__ == "__main__":
    main()
