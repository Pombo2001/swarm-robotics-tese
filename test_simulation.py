import sys
import os
import time

# Adiciona a pasta src ao caminho
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from environment.swarm_env import SwarmForagingEnv


def test_visual():
    print("🎥 A iniciar teste visual...")

    # Render mode "human" ativa o PyGame
    try:
        env = SwarmForagingEnv(config_path="configs/foraging.yaml")
    except:
        env = SwarmForagingEnv(config_path="../configs/foraging.yaml")

    env.reset()

    print("Janela deve abrir agora. Pressiona Ctrl+C no terminal para parar.")

    try:
        for i in range(500):  # Corre durante 500 frames
            # Agentes a "tremer" aleatoriamente
            actions = {agent: env.action_space(agent).sample() for agent in env.agents}

            env.step(actions)

            # O render já é chamado dentro do step() se render_mode="human"

    except KeyboardInterrupt:
        print("A fechar...")
    finally:
        env.close()
        print("Fechado.")


if __name__ == "__main__":
    test_visual()