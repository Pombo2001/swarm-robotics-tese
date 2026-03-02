import pygame
import torch
import numpy as np
import sys
import os
from stable_baselines3 import PPO

# Forçar o Python a reconhecer a pasta RAIZ
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# A LINHA CORRIGIDA: Importar a versão 2D (sem o "3D" no fim)
from src.environment.swarm_env import SwarmForagingEnv

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'configs', 'foraging.yaml')

def visualize_ppo(model_path):
    # 1. INICIALIZAR PYGAME E AMBIENTE
    pygame.init()

    print(f"🎥 A carregar PPO: {model_path}")

    config_path = os.path.join(os.path.dirname(__file__), 'configs/foraging.yaml')
    env = SwarmForagingEnv(config_path=config_path)
    env.render_mode = "human" # Garante que o modo gráfico está ativado

    # Adicionar o .zip que o StableBaselines3 usa por defeito
    if not os.path.exists(model_path + ".zip") and not os.path.exists(model_path):
        print(f"❌ Erro: Ficheiro não existe em {model_path}")
        return

    try:
        model = PPO.load(model_path)
    except Exception as e:
        print(f"Erro a carregar modelo PPO: {e}")
        return

    print("🚀 Simulação PPO iniciada!")
    observations, infos = env.reset()

    # 2. JANELA E RELÓGIO
    env.render()
    model_name = os.path.basename(model_path)
    pygame.display.set_caption(f"Visualizador PPO: {model_name}")

    clock = pygame.time.Clock()

    running = True
    try:
        while running:
            # Eventos (para poderes fechar no X da janela)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            if not running: break

            # Pensar e Agir
            actions = {}
            for agent_id in env.agents:
                obs = observations[agent_id]
                action, _states = model.predict(obs, deterministic=True)
                actions[agent_id] = action

            observations, rewards, terms, truncs, infos = env.step(actions)

            # ---> A LINHA MÁGICA QUE FALTAVA PARA DESCONGELAR O ECRÃ <---
            env.render()

            # Lógica de Reset
            if any(terms.values()) or any(truncs.values()):
                observations, infos = env.reset()
                env.render()
                pygame.display.set_caption(f"Visualizador PPO: {model_name}")

            # 3. CONTROLAR VELOCIDADE (30 FPS)
            clock.tick(30)

    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 A fechar...")
        env.close()
        pygame.quit()


if __name__ == "__main__":
    # Garante que aponta para o sítio onde o dashboard grava o PPO final
    default_model = os.path.join(os.path.dirname(__file__), 'results', 'models_ppo', 'ppo_final')
    visualize_ppo(default_model)