import sys
import os
import torch
import numpy as np
import time
import argparse

# Configurar caminhos para encontrar o src
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))

from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


def visualize(model_path):
    print(f"🎥 A carregar modelo: {model_path}")

    config_file = os.path.join(current_dir, 'configs/foraging.yaml')
    # Forçar render mode human
    env = SwarmForagingEnv(config_path=config_file)
    env.render_mode = "human"

    if not os.path.exists(model_path):
        print(f"❌ Erro: Não encontro o ficheiro {model_path}")
        return

    # Carregar pesos (CPU safe)
    try:
        trained_weights = torch.load(model_path, map_location=torch.device('cpu'), weights_only=True)
    except:
        trained_weights = torch.load(model_path, map_location=torch.device('cpu'))

    # Criar Agentes
    agents_map = {}
    for agent_id in env.agents:
        agent = GNNAgent(agent_id, env.action_space(agent_id))
        agent.policy.load_state_dict(trained_weights)
        agent.policy.eval()
        agents_map[agent_id] = agent

    print("🚀 Simulação iniciada! (Ctrl+C para sair)")

    observations, infos = env.reset()

    try:
        while True:
            actions = {}
            for agent_id in env.agents:
                obs = observations[agent_id]
                actions[agent_id] = agents_map[agent_id].get_action(obs)

            observations, rewards, terms, truncs, infos = env.step(actions)

            # Debug de sucesso
            for agent_id, reward in rewards.items():
                if reward > 5.0:
                    print(f"✨ {agent_id} entregou comida!")

    except KeyboardInterrupt:
        print("\n🛑 A fechar simulação...")
    finally:
        env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="Caminho para o ficheiro .pth")
    args = parser.parse_args()
    visualize(args.model)