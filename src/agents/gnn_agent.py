import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class GNNAgent(nn.Module):
    def __init__(self, name, action_space):
        super(GNNAgent, self).__init__()
        self.name = name

        # --- ATUALIZADO PARA FASE 2 ---
        # 4 (Nav) + 3 (Pedra) = 7
        self.input_dim = 7
        self.neighbor_dim = 2
        self.hidden_dim = 64
        self.output_dim = action_space.shape[0]

        # Camadas
        self.fc1 = nn.Linear(self.input_dim, self.hidden_dim)
        self.fc_neighbor = nn.Linear(self.neighbor_dim, self.hidden_dim)
        self.fc2 = nn.Linear(self.hidden_dim * 2, self.hidden_dim)
        self.fc3 = nn.Linear(self.hidden_dim, self.output_dim)

    def forward(self, x):
        # 1. Separar dados (Agora os primeiros 7 são do robô)
        self_data = x[:, :7]
        neighbor_data = x[:, 7:]

        # 2. Processar o robô
        self_feat = F.relu(self.fc1(self_data))

        # 3. Processar os vizinhos (GNN)
        batch_size = x.shape[0]
        num_neighbors = neighbor_data.shape[1] // 2

        if num_neighbors > 0:
            neighbor_data = neighbor_data.view(batch_size, num_neighbors, 2)
            neighbor_feat = F.relu(self.fc_neighbor(neighbor_data))
            neighbor_summary = torch.mean(neighbor_feat, dim=1)
        else:
            neighbor_summary = torch.zeros_like(self_feat)

        # 4. Juntar e Decidir
        combined = torch.cat([self_feat, neighbor_summary], dim=1)
        x = F.relu(self.fc2(combined))
        action = torch.tanh(self.fc3(x))

        return action