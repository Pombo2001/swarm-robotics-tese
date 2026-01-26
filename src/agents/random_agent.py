from .base_agent import Agent

class RandomAgent(Agent):
    def get_action(self, observation):
        # Retorna uma velocidade aleatória válida [-1, 1] para X e Y
        return self.action_space.sample()