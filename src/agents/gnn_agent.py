import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from .base_agent import Agent


class GNNPolicy(nn.Module):
    """
    A Rede Neuronal (O Cérebro).
    Usa uma arquitetura simples inspirada em GNNs/DeepSets:
    1. Processa a informação do Ninho.
    2. Processa cada Vizinho individualmente com a mesma rede (Encoder).
    3. Soma tudo (Agregação).
    4. Decide a ação (Decoder).
    """

    def __init__(self, input_size=20, hidden_size=64, action_size=2):
        super(GNNPolicy, self).__init__()

        # 1. Encoder para o Ninho (Input: dx, dy)
        self.nest_encoder = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU()
        )

        # 2. Encoder para Vizinhos (Input: dx, dy)
        # Processa cada vizinho da mesma maneira (pesos partilhados)
        self.neighbor_encoder = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU()
        )

        # 3. Cabeça de Decisão (Recebe Ninho + Soma dos Vizinhos)
        # 32 (ninho) + 32 (vizinhos agregados) = 64
        self.head = nn.Sequential(
            nn.Linear(64, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, action_size),
            nn.Tanh()  # Força a saída a ficar entre -1 e 1 (velocidade motores)
        )

    def forward(self, x):
        # x shape: [batch_size, 20]
        # O input x vem com [Ninho(2), Vizinho1(2), Vizinho2(2)...]

        # Separar Ninho e Vizinhos
        nest_input = x[:, 0:2]  # Primeiros 2 valores
        neighbors_input = x[:, 2:]  # Resto (18 valores = 9 vizinhos)

        # Processar Ninho
        nest_features = self.nest_encoder(nest_input)

        # Processar Vizinhos (GNN Agregation)
        # Vamos remodelar para processar pares (dx, dy)
        # De [Batch, 18] para [Batch, 9, 2]
        batch_size = x.shape[0]
        neighbors_reshaped = neighbors_input.view(batch_size, -1, 2)

        # Aplicar encoder a cada vizinho
        neighbor_features = self.neighbor_encoder(neighbors_reshaped)  # [Batch, 9, 32]

        # AGREGAÇÃO (A magia das GNNs):
        # Somamos as features de todos os vizinhos.
        # Assim, não interessa se temos 1 ou 5 vizinhos, o tamanho final é igual.
        total_neighbor_features = torch.sum(neighbor_features, dim=1)  # [Batch, 32]

        # Juntar Ninho + Vizinhos
        combined = torch.cat([nest_features, total_neighbor_features], dim=1)  # [Batch, 64]

        # Decidir Ação
        action = self.head(combined)
        return action


class GNNAgent(Agent):
    def __init__(self, name, action_space, model_path=None):
        super().__init__(name, action_space)
        self.device = torch.device("cpu")  # Usamos CPU para inferência rápida no teste

        # Inicializar a Rede
        self.policy = GNNPolicy()
        self.policy.to(self.device)

        # Se tivermos um modelo treinado, carregamos (para o futuro)
        if model_path:
            self.policy.load_state_dict(torch.load(model_path))
            self.policy.eval()

    def get_action(self, observation):
        # 1. Preparar dados (Numpy -> Tensor)
        obs_tensor = torch.tensor(observation, dtype=torch.float32).unsqueeze(0).to(self.device)

        # 2. Perguntar à rede (Forward pass)
        with torch.no_grad():
            action_tensor = self.policy(obs_tensor)

        # 3. Converter de volta (Tensor -> Numpy)
        return action_tensor.cpu().numpy()[0]