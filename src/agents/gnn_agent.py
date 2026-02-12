import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class GNNAgent(nn.Module):
    def __init__(self, name, action_space):
        super(GNNAgent, self).__init__()
        self.name = name

        # --- CONFIGURAÇÃO (Input 7 = 2 Pos + 2 Ninho + 3 Pedra) ---
        self.input_dim = 7
        self.neighbor_dim = 2  # Posição relativa do vizinho (X, Y)
        self.hidden_dim = 64
        self.output_dim = action_space.shape[0]

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

        # 3. MECANISMO DE ATENÇÃO (GAT) 🧠✨
        # Query: O que eu procuro? | Key: O que o vizinho tem?
        self.attn_query = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.attn_key = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.attn_value = nn.Linear(self.hidden_dim, self.hidden_dim)

        # 4. Decisão Final (Decoder)
        # Recebe: Meu Estado + Contexto Social (Atenção)
        self.fc_final = nn.Sequential(
            nn.Linear(self.hidden_dim * 2, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.output_dim),
            nn.Tanh()  # Saída entre -1 e 1 (Velocidade)
        )

    def forward(self, x):
        # x shape: [batch_size, obs_size]
        # Separar dados
        self_data = x[:, :7]  # Meus dados
        neighbor_data = x[:, 7:]  # Dados vizinhos (flat)

        batch_size = x.shape[0]

        # A. Codificar Estado Próprio
        h_self = self.fc_self(self_data)  # [batch, 64]

        # B. Processar Vizinhos com ATENÇÃO
        num_neighbors = neighbor_data.shape[1] // 2

        if num_neighbors > 0:
            # Reshape para [batch, num_vizinhos, 2]
            neighbors = neighbor_data.view(batch_size, num_neighbors, 2)

            # Codificar cada vizinho
            h_neighbors = self.fc_neighbor(neighbors)  # [batch, N, 64]

            # --- CÁLCULO DA ATENÇÃO ---
            # Q (Eu), K (Vizinhos), V (Vizinhos)
            # Expandir Q para comparar com todos os vizinhos
            Q = self.attn_query(h_self).unsqueeze(1)  # [batch, 1, 64]
            K = self.attn_key(h_neighbors)  # [batch, N, 64]
            V = self.attn_value(h_neighbors)  # [batch, N, 64]

            # Scores de Atenção (Dot Product)
            # "Qual a relevância deste vizinho para o meu estado atual?"
            attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.hidden_dim)
            attn_weights = F.softmax(attn_scores, dim=-1)  # [batch, 1, N]

            # Contexto Social (Soma Ponderada)
            context = torch.matmul(attn_weights, V).squeeze(1)  # [batch, 64]
        else:
            context = torch.zeros_like(h_self)

        # C. Juntar Tudo e Decidir
        combined = torch.cat([h_self, context], dim=1)  # [batch, 128]
        action = self.fc_final(combined)

        return action