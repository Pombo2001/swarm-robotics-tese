import pygame
import torch
import numpy as np
import sys
import os
import time  # <--- A LINHA MÁGICA QUE FALTAVA!

# Forçar o Python a reconhecer a pasta RAIZ
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.environment.swarm_env import SwarmForagingEnv
from src.agents.gnn_agent import GNNAgent

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')


def visualize_best_continuous():
    print("🎥 A iniciar o Visualizador...")

    # 1. Carrega o YAML
    config_path = os.path.join(os.path.dirname(__file__), 'configs/foraging.yaml')

    # 2. IGNORA O YAML E FORÇA O MODO GRÁFICO!
    env = SwarmForagingEnv(config_path)
    env.render_mode = "human"  # <--- ESTA É A LINHA MÁGICA

    # ... resto do código mantém-se igual ...

    # Preparar os cérebros
    brains = []
    for i in range(env.num_agents):
        agent_name = f"robot_{i}"
        brains.append(GNNAgent(agent_name, env.action_space(agent_name)))

    # Carregar o "Super Cérebro"
    model_path = os.path.join(os.path.dirname(__file__), 'results', 'models', 'gnn_fair_best.pth')

    try:
        best_weights = torch.load(model_path)
        # Aplicar o mesmo cérebro de elite a todos os robôs para o teste final
        for brain in brains:
            brain.load_state_dict(best_weights)
        print(f"✅ Modelo de elite carregado: {model_path}")
        # Garantir permissões de leitura/escrita no ficheiro do modelo, caso precises de o partilhar
        os.chmod(model_path, 0o666)
    except FileNotFoundError:
        print(f"❌ Erro: Não foi encontrado o ficheiro {model_path}")
        return

    obs_dict, _ = env.reset()

    print("🚀 Simulação a correr! (Prime Ctrl+C no terminal para fechar)")

    try:
        for step in range(1000):  # Mostrar 1000 steps de pura eficiência
            actions = {}
            for i, agent_name in enumerate(env.agents):
                obs_tensor = torch.tensor(obs_dict[agent_name], dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    action = brains[i](obs_tensor).squeeze(0).numpy()
                actions[agent_name] = action

            obs_dict, rewards, terms, truncs, _ = env.step(actions)
            env.render()

            # Abrandar um pouco para o vídeo ficar suave
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n🛑 Visualização terminada pelo utilizador.")
    finally:
        env.close()


if __name__ == "__main__":
    visualize_best_continuous()