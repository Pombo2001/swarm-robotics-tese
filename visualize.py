import argparse
import torch
import time
import os
import sys
import pygame

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from environment.swarm_env import SwarmForagingEnv
from agents.gnn_agent import GNNAgent


def main():
    pygame.init()  # Inicializar vídeo

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="Caminho para o modelo .pth")
    args = parser.parse_args()

    print(f"🎥 A carregar modelo: {args.model}")

    config_path = os.path.join(os.path.dirname(__file__), 'configs/foraging.yaml')
    env = SwarmForagingEnv(config_path=config_path)
    env.render_mode = "human"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    template_agent = GNNAgent("template", env.action_space("robot_0"))

    try:
        state_dict = torch.load(args.model, map_location=device, weights_only=True)
        # CÓDIGO CORRIGIDO: Carregar diretamente no agente, sem .policy
        template_agent.load_state_dict(state_dict)
    except Exception as e:
        print(f"Erro crítico ao carregar modelo: {e}")
        # Se falhar, tenta carregar à moda antiga caso seja um modelo velho
        try:
            template_agent.policy.load_state_dict(state_dict)
        except:
            print("Não foi possível carregar o modelo de nenhuma forma.")
            return

    print("🚀 Simulação GNN iniciada!")

    observations, infos = env.reset()
    env.render()

    model_name = os.path.basename(args.model)
    pygame.display.set_caption(f"Visualizador GNN: {model_name}")

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            if not running: break

            actions = {}
            for agent_id in env.agents:
                obs = observations[agent_id]
                action = template_agent.get_action(obs)
                actions[agent_id] = action

            observations, rewards, terms, truncs, infos = env.step(actions)

            if any(terms.values()) or any(truncs.values()):
                observations, infos = env.reset()
                env.render()
                pygame.display.set_caption(f"Visualizador GNN: {model_name}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 A fechar simulação...")
        env.close()
        pygame.quit()


if __name__ == "__main__":
    main()