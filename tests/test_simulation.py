import sys
import os
import time
import numpy as np


# 1. Configurar caminhos de forma robusta
# Pega na pasta onde ESTE ficheiro está (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Define o caminho para a pasta src (uma acima, depois src)
src_path = os.path.join(current_dir, '../src')
sys.path.append(src_path)

# Define o caminho ABSOLUTO para o ficheiro de config
config_path = os.path.join(current_dir, '../configs/foraging.yaml')

from environment.swarm_env import SwarmForagingEnv

from agents.gnn_agent import GNNAgent

def test_visual():
    print(f"🎥 A iniciar teste visual...")
    print(f"   Config file: {os.path.abspath(config_path)}")

    # 2. Criar Ambiente (usando o caminho absoluto)
    if not os.path.exists(config_path):
        print(f"❌ ERRO CRÍTICO: Não encontro o ficheiro em: {config_path}")
        return

    env = SwarmForagingEnv(config_path=config_path)

    # Guardar as primeiras observações
    observations, infos = env.reset()

    # 3. Criar os "Cérebros" (Agentes)
    # 3. Criar os "Cérebros" (Agentes)
    agents_map = {}
    for agent_id in env.agents:
        # AGORA USAMOS GNN!
        agents_map[agent_id] = GNNAgent(agent_id, env.action_space(agent_id))

    print("Janela deve abrir agora. Pressiona Ctrl+C no terminal para parar.")

    try:
        for i in range(1000):  # Loop da simulação
            actions = {}

            for agent_id in env.agents:
                obs = observations[agent_id]
                actions[agent_id] = agents_map[agent_id].get_action(obs)

                # --- DEBUG TEMPORÁRIO ---
                if agent_id == "robot_0" and i % 50 == 0:
                    dist_ninho = np.linalg.norm(obs[0:2])
                    vizinho_x = obs[2]
                    vizinho_y = obs[3]
                    print(
                        f"🤖 Robot_0 vê -> Ninho a {dist_ninho:.2f}m | Vizinho +próximo: ({vizinho_x:.1f}, {vizinho_y:.1f})")
                # ------------------------

            observations, rewards, terms, truncs, infos = env.step(actions)

    except KeyboardInterrupt:
        print("A fechar...")
    finally:
        env.close()
        print("Fechado.")


if __name__ == "__main__":
    test_visual()