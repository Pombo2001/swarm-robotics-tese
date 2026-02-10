import os
import sys
import torch
import numpy as np
import glob
import time

# Adicionar a pasta 'src' ao caminho para conseguir importar os módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


def find_config_file():
    """Procura o ficheiro foraging.yaml em vários locais possíveis"""
    base_dir = os.path.dirname(__file__)

    # Lista de sítios prováveis onde o ficheiro pode estar
    possible_paths = [
        os.path.join(base_dir, 'src', 'configs', 'foraging.yaml'),  # Dentro de src/configs
        os.path.join(base_dir, 'configs', 'foraging.yaml'),  # Na raiz/configs
        os.path.join(base_dir, 'src', 'config', 'foraging.yaml'),  # Singular
        os.path.join(base_dir, 'config', 'foraging.yaml'),  # Singular raiz
    ]

    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Configuração encontrada em: {path}")
            return path

    return None


def main():
    # 1. Encontrar ficheiros
    project_root = os.path.dirname(__file__)
    models_dir = os.path.join(project_root, 'results/models')

    # A. Encontrar Configuração
    config_path = find_config_file()
    if config_path is None:
        print("❌ ERRO CRÍTICO: Não foi possível encontrar o ficheiro 'foraging.yaml'.")
        print("Verifica se tens a pasta 'configs' criada.")
        return

    # B. Encontrar Modelo
    list_of_files = glob.glob(os.path.join(models_dir, '*.pth'))
    if not list_of_files:
        print("❌ Erro: Nenhum modelo encontrado na pasta results/models/")
        return

    # Escolhe o último ficheiro modificado
    latest_model = max(list_of_files, key=os.path.getctime)
    print(f"🎥 A carregar modelo: {latest_model}")

    # 2. Inicializar Ambiente
    try:
        env = SwarmForagingEnv(config_path)
    except Exception as e:
        print(f"❌ Erro ao criar ambiente: {e}")
        return

    # 3. Inicializar Agente
    agent = GNNAgent("vis_agent", env.action_space("robot_0"))

    try:
        agent.load_state_dict(torch.load(latest_model, map_location=torch.device('cpu')))
        agent.eval()
    except Exception as e:
        print(f"❌ Erro ao carregar pesos: {e}")
        return

    # 4. Loop de Simulação
    obs_dict, _ = env.reset()
    done = False

    print("🚀 Simulação Visual iniciada! (Prime Ctrl+C no terminal para parar)")

    try:
        while not done:
            # Preparar dados
            obs_list = [obs_dict[agent_id] for agent_id in env.agents]
            obs_tensor = torch.tensor(np.array(obs_list), dtype=torch.float32)

            # Ação (CORREÇÃO DO GET_ACTION APLICADA AQUI)
            with torch.no_grad():
                actions_tensor = agent(obs_tensor)
                actions_np = actions_tensor.numpy()

            actions = {id: act for id, act in zip(env.agents, actions_np)}

            # Passo
            obs_dict, _, terms, truncs, _ = env.step(actions)

            # Renderizar
            env.render()

            if any(terms.values()) or any(truncs.values()):
                obs_dict, _ = env.reset()

            time.sleep(1 / 30)  # 30 FPS

    except KeyboardInterrupt:
        print("\n🛑 A fechar simulação...")
        env.close()


if __name__ == "__main__":
    main()