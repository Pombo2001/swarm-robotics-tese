import torch
import torch.nn as nn
import torch.nn.functional as F


class GNNAgent3D(nn.Module):
    def __init__(self, agent_id, action_space):
        super(GNNAgent3D, self).__init__()
        self.agent_id = agent_id

        # --- A NOVA BÚSSOLA INTERNA ---
        # Ninho (4) + Obstáculo (4) = 8 features base do ambiente
        # Vizinhos (5) = Frente, Direita, Cima, Distância, Sinalização
        self.env_feats_dim = 8
        self.neighbor_dim = 5

        self.hidden_dim = 64

        # Encoder do Ambiente Local (O que o drone "vê")
        self.encoder = nn.Sequential(
            nn.Linear(self.env_feats_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        # O "Comunicador" (O que o drone "ouve" dos vizinhos)
        self.msg_net = nn.Sequential(
            nn.Linear(self.neighbor_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        # O "Cérebro" que junta a visão com a comunicação para decidir os 3 Motores
        self.actor = nn.Sequential(
            nn.Linear(self.hidden_dim * 2, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, 3),  # 3 Eixos de movimento
            nn.Tanh()
        )

    def forward(self, obs):
        batch_size = obs.shape[0] if len(obs.shape) > 1 else 1

        if len(obs.shape) == 1:
            obs = obs.unsqueeze(0)

        env_data = obs[:, :self.env_feats_dim]
        neighbor_data = obs[:, self.env_feats_dim:]

        # Descobrir quantos vizinhos existem dinamicamente (19 vizinhos se num_agents for 20)
        num_neighbors = neighbor_data.shape[1] // self.neighbor_dim

        h_env = self.encoder(env_data)

        if num_neighbors > 0:
            # Aqui é onde o erro batia! Agora está preparado para receber (20, 19, 5)
            neighbors = neighbor_data.view(batch_size, num_neighbors, self.neighbor_dim)
            msg = self.msg_net(neighbors)
            msg_pool = msg.mean(dim=1)
        else:
            msg_pool = torch.zeros((batch_size, self.hidden_dim), device=obs.device)

        combined = torch.cat([h_env, msg_pool], dim=1)
        action = self.actor(combined)

        if batch_size == 1:
            return action.squeeze(0)

        return action