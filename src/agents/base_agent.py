import numpy as np

class Agent:
    """
    Classe base para qualquer controlador.
    """
    def __init__(self, name, action_space):
        self.name = name
        self.action_space = action_space

    def get_action(self, observation):
        """
        Recebe o que o robô vê e decide a velocidade.
        Tem de ser implementado pelos filhos.
        """
        raise NotImplementedError