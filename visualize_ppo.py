import os
import sys
import argparse
import numpy as np
from stable_baselines3 import PPO

# Ajustar caminhos para encontrar o src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from environment.swarm_env import SwarmForagingEnv


def visualize_ppo(model_path):
    print(f"🎥 A carregar modelo PPO: {model_path}")

    # 1. Configurar Ambiente
    config_path = os.path.join(os.path.dirname(__file__), 'configs/foraging.yaml')
    env = SwarmForagingEnv(config_path=config_path)
    env.render_mode = "human"  # Forçar modo visual

    # 2. Carregar o Cérebro PPO
    if not os.path.exists(model_path + ".zip") and not os.path.exists(model_path):
        print(f"❌ Erro: Não encontro o ficheiro {model_path}")
        return

    try:
        model = PPO.load(model_path)
    except Exception as e:
        print(f"Erro ao carregar PPO: {e}")
        return

    print("🚀 Simulação PPO iniciada! (Ctrl+C para sair)")

    observations, infos = env.reset()

    try:
        while True:
            actions = {}
            # O PPO foi treinado para agir individualmente.
            # Vamos pedir-lhe uma ação para cada robô.
            for agent_id in env.agents:
                obs = observations[agent_id]

                # deterministic=True faz o robô usar a melhor jogada que conhece (sem explorar)
                action, _states = model.predict(obs, deterministic=True)

                actions[agent_id] = action

            observations, rewards, terms, truncs, infos = env.step(actions)

            # Debug de sucesso no terminal
            for agent_id, reward in rewards.items():
                # Nota: No PPO a reward pode vir escalada, mas se for alta avisamos
                if reward > 5.0:
                    print(f"✨ {agent_id} (PPO) entregou comida!")

            # Verificar se precisamos de resetar (se o episódio acabar)
            if any(terms.values()) or any(truncs.values()):
                observations, infos = env.reset()

    except KeyboardInterrupt:
        print("\n🛑 A fechar simulação...")
    finally:
        env.close()


if __name__ == "__main__":
    # Caminho por defeito para o modelo que acabaste de treinar
    default_model = os.path.join(os.path.dirname(__file__), 'results/models_ppo/ppo_final')
    visualize_ppo(default_model)