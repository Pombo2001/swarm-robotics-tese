import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class GNNAgent3D(nn.Module):
    def __init__(self, name, action_space):
        super(GNNAgent3D, self).__init__()
        self.name = name

        # --- CONFIGURAÇÃO 3D ---
        self.input_dim = 10  # 3 Pos + 3 Ninho + 1 Sensor + 3 Dir_Pedra
        self.neighbor_dim = 4  # Rel X, Rel Y, Rel Z, SINAL
        self.hidden_dim = 64
        self.output_dim = action_space.shape[0]  # Agora é 3 (X, Y, Z)

        # 1. Processamento Próprio (Encoder)
        self.fc_self = nn.Sequential(
            nn.Linear(self.input_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        # 2. Processamento de Vizinhos (Encoder)
        self.fc_neighbor = nn.Sequential(
            nn.Linear(self.neighbor_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        # 3. MECANISMO DE ATENÇÃO (GAT)
        self.attn_query = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.attn_key = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.attn_value = nn.Linear(self.hidden_dim, self.hidden_dim)

        # 4. Decisão Final (Decoder)
        self.fc_final = nn.Sequential(
            nn.Linear(self.hidden_dim * 2, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.output_dim),
            nn.Tanh()  # Saída entre -1 e 1 para os 3 motores (X, Y, Z)
        )

    def forward(self, x):
        # x shape: [batch_size, obs_size]
        # Cortamos no índice 10 porque agora temos 10 inputs próprios
        self_data = x[:, :10]
        neighbor_data = x[:, 10:]

        batch_size = x.shape[0]

        # A. Codificar Estado Próprio
        h_self = self.fc_self(self_data)

        # B. Processar Vizinhos com ATENÇÃO
        num_neighbors = neighbor_data.shape[1] // self.neighbor_dim

        if num_neighbors > 0:
            # Reshape para [batch, num_vizinhos, 4]
            neighbors = neighbor_data.view(batch_size, num_neighbors, self.neighbor_dim)

            # Codificar cada vizinho
            h_neighbors = self.fc_neighbor(neighbors)

            # Cálculo da Atenção
            Q = self.attn_query(h_self).unsqueeze(1)
            K = self.attn_key(h_neighbors)
            V = self.attn_value(h_neighbors)

            attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.hidden_dim)
            attn_weights = F.softmax(attn_scores, dim=-1)

            # Contexto Social
            context = torch.matmul(attn_weights, V).squeeze(1)
        else:
            context = torch.zeros_like(h_self)

        # C. Juntar Tudo e Decidir
        combined = torch.cat([h_self, context], dim=1)
        action = self.fc_final(combined)

        return action

# Assegurar as permissões read/write ao criar o módulo
try:
    os.chmod(__file__, 0o666)
except Exception:
    pass