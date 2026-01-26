import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class GNNAgent(nn.Module):
    def __init__(self, name, action_space, hidden_dim=64):
        super(GNNAgent, self).__init__()
        self.name = name

        # --- A CORREÇÃO CRÍTICA ---
        # Antes era 6 ou 2. Agora é 9 por causa dos sensores de obstáculos!
        # (VelX, VelY, DistNinho, DirNinhoX, DirNinhoY, DistObs, DirObsX, DirObsY, State)
        self.own_feat_dim = 9
        # --------------------------

        self.neighbor_feat_dim = 2  # (Pos Relativa X, Pos Relativa Y)
        self.action_dim = action_space.shape[0]

        # 1. Processador de Vizinhos (Message Passing)
        # Transforma a posição (x,y) do vizinho num vetor de 'hidden_dim'
        self.neighbor_mlp = nn.Sequential(
            nn.Linear(self.neighbor_feat_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )

        # 2. Cérebro Principal (Processa Tudo)
        # Junta: (O que eu sinto) + (O que os vizinhos me dizem)
        self.final_mlp = nn.Sequential(
            nn.Linear(self.own_feat_dim + hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.action_dim),
            nn.Tanh()  # Tanh mete a saida entre -1 e 1 (velocidade)
        )

    def forward(self, obs):
        # Garantir que é Tensor e tem Batch
        if not isinstance(obs, torch.Tensor):
            obs = torch.tensor(obs, dtype=torch.float32)

        if len(obs.shape) == 1:
            obs = obs.unsqueeze(0)  # Adicionar batch dimension [1, N]

        batch_size = obs.shape[0]

        # 1. Separar os dados (Fatiar o bolo)
        # Os primeiros 9 numeros sou eu. O resto são os vizinhos.
        own_feats = obs[:, :self.own_feat_dim]  # Shape: [Batch, 9]
        neighbors_flat = obs[:, self.own_feat_dim:]  # Shape: [Batch, Resto]

        # 2. Processar Vizinhos (GNN)
        # Validar se temos vizinhos para processar
        if neighbors_flat.shape[1] > 0:
            # Reformata o vetor raso para [Batch, Num_Vizinhos, 2]
            # O '-1' diz ao PyTorch: "Calcula tu quantos vizinhos são"
            neighbors_reshaped = neighbors_flat.view(batch_size, -1, self.neighbor_feat_dim)

            # Aplica a MLP a CADA vizinho individualmente
            embeddings = self.neighbor_mlp(neighbors_reshaped)  # [Batch, N_Viz, Hidden]

            # Aggregation (Soma ou Max): Resume todos os vizinhos num só vetor
            # "Qual é a 'vibe' geral à minha volta?"
            neighbor_summary, _ = torch.max(embeddings, dim=1)  # [Batch, Hidden]
        else:
            # Se não houver vizinhos (caso raro ou teste), usa zeros
            neighbor_summary = torch.zeros(batch_size, 64, device=obs.device)

        # 3. Juntar e Decidir
        combined = torch.cat([own_feats, neighbor_summary], dim=1)  # [Batch, 9 + 64]
        action = self.final_mlp(combined)

        return action

    def get_action(self, obs):
        # Função auxiliar para usar sem pensar em tensores
        with torch.no_grad():
            action = self.forward(obs)
            return action.cpu().numpy()[0]