"""
run_eval.py — Avaliação sistemática de modelos treinados
=========================================================
Corre N episódios de teste sem exploração (modo determinístico),
reporta estatísticas e guarda CSV em results/evaluation/.

Uso:
    python run_eval.py --algo gnn --episodes 20
    python run_eval.py --algo ppo --episodes 20 --scenario u_wall
    python run_eval.py --algo sac --episodes 30 --scenario none
"""
import argparse
import os
import sys
import numpy as np
import pandas as pd
import torch
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env_3d import SwarmForagingEnv3D

SCENARIO_LABELS = {
    "none":                   "Sandbox",
    "u_wall":                 "Beco Sem Saida (U)",
    "bottleneck":             "Gargalo",
    "four_rooms":             "Quatro Salas",
    "cooperative_door":       "Porta Cooperativa",
    "cooperative_perception": "Percepcao Cooperativa",
}


def load_model(algo, scenario, config_path):
    suffix = f"_{scenario}" if scenario and scenario != "none" else ""

    if algo == "gnn":
        from src.agents.gnn_agent_3d import GNNAgent3D
        env_tmp = SwarmForagingEnv3D(config_path=config_path)
        agent = GNNAgent3D("eval", env_tmp.action_space("robot_0"), config_path)
        for path in [
            os.path.join(PROJECT_ROOT, "results", "models", f"gnn_3d_best{suffix}.pth"),
            os.path.join(PROJECT_ROOT, "results", "models", "gnn_3d_best.pth"),
        ]:
            if os.path.exists(path):
                agent.load_state_dict(torch.load(path, weights_only=True))
                agent.eval()
                print(f"[OK] GNN carregado: {path}")
                return agent
        raise FileNotFoundError("Modelo GNN nao encontrado em results/models/")

    elif algo == "ppo":
        from stable_baselines3 import PPO
        for path in [
            os.path.join(PROJECT_ROOT, "results", "models_ppo", f"ppo_3d_final{suffix}.zip"),
            os.path.join(PROJECT_ROOT, "results", "models_ppo", "ppo_3d_final.zip"),
        ]:
            if os.path.exists(path):
                print(f"[OK] PPO carregado: {path}")
                return PPO.load(path)
        raise FileNotFoundError("Modelo PPO nao encontrado em results/models_ppo/")

    elif algo == "sac":
        from stable_baselines3 import SAC
        for path in [
            os.path.join(PROJECT_ROOT, "results", "models_sac", f"sac_3d_final{suffix}.zip"),
            os.path.join(PROJECT_ROOT, "results", "models_sac", "sac_3d_final.zip"),
        ]:
            if os.path.exists(path):
                print(f"[OK] SAC carregado: {path}")
                return SAC.load(path)
        raise FileNotFoundError("Modelo SAC nao encontrado em results/models_sac/")


def run_episode(env, algo, model):
    obs_dict, _ = env.reset()
    total_reward = 0.0
    steps = 0

    while True:
        actions = {}

        if algo == "gnn":
            obs_list   = [obs_dict[a] for a in env.agents]
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

    food        = int(env.total_food_collected)
    task_reward = food * env.food_collected_reward
    return {
        "food_collected":  food,
        "task_reward":     task_reward,
        "total_reward":    total_reward,
        "shaping_reward":  total_reward - task_reward,
        "episode_length":  steps,
        "success":         food > 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Avaliacao de modelos treinados")
    parser.add_argument("--algo",     required=True, choices=["gnn", "ppo", "sac"])
    parser.add_argument("--episodes", type=int, default=20,
                        help="Numero de episodios de teste (default: 20)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Forccar cenario (sobrepoe o config)")
    parser.add_argument("--fail-frac", type=float, default=0.0,
                        help="Rrobust: fracao de agentes que falha a meio do episodio "
                             "(ex: 0.1 = 10%%). Compara com 0.0 para medir resiliencia.")
    args = parser.parse_args()

    config_path = os.path.join(PROJECT_ROOT, "configs", "foraging.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    scenario = args.scenario or config["environment"].get("classic_scenario", "none")
    label    = SCENARIO_LABELS.get(scenario, scenario)

    print(f"\n{'='*58}")
    print(f"  AVALIACAO: {args.algo.upper():<5}  |  {label}")
    print(f"  {args.episodes} episodios  |  modo deterministico (sem exploracao)")
    print(f"{'='*58}\n")

    model = load_model(args.algo, scenario, config_path)

    env = SwarmForagingEnv3D(config_path=config_path)
    if args.scenario:
        env.config["environment"]["classic_scenario"] = args.scenario
    env.agent_failure_fraction = args.fail_frac
    if args.fail_frac > 0:
        print(f"  [Rrobust] {args.fail_frac*100:.0f}% dos agentes falham a meio do episodio\n")

    results = []
    for ep in range(args.episodes):
        r = run_episode(env, args.algo, model)
        results.append(r)
        status = "OK" if r["success"] else "--"
        print(f"  [{status}] ep {ep+1:2d}: "
              f"recolhas={r['food_collected']}  "
              f"task={r['task_reward']:+.0f}  "
              f"total={r['total_reward']:+.0f}  "
              f"passos={r['episode_length']}")

    df = pd.DataFrame(results)

    print(f"\n{'─'*58}")
    print(f"  Algoritmo     : {args.algo.upper()}")
    print(f"  Cenario       : {label}")
    print(f"  Episodios     : {args.episodes}")
    print(f"{'─'*58}")
    print(f"  Recolhas/ep   : {df.food_collected.mean():.2f} +/- {df.food_collected.std():.2f}")
    print(f"  Task reward   : {df.task_reward.mean():.1f}  +/- {df.task_reward.std():.1f}")
    print(f"  Total reward  : {df.total_reward.mean():.1f}  +/- {df.total_reward.std():.1f}")
    print(f"  Shaping       : {df.shaping_reward.mean():.1f}  +/- {df.shaping_reward.std():.1f}")
    print(f"  Taxa sucesso  : {df.success.mean()*100:.0f}%  ({df.success.sum()}/{args.episodes})")
    print(f"  Passos medios : {df.episode_length.mean():.1f}")
    print(f"{'─'*58}\n")

    out_dir  = os.path.join(PROJECT_ROOT, "results", "evaluation")
    os.makedirs(out_dir, exist_ok=True)
    fail_tag = f"_fail{int(args.fail_frac*100)}" if args.fail_frac > 0 else ""
    out_path = os.path.join(out_dir, f"eval_{args.algo}_{scenario}{fail_tag}.csv")
    df.to_csv(out_path, index=False)
    print(f"[OK] Resultados guardados: {out_path}")


if __name__ == "__main__":
    main()
